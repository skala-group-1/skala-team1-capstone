package com.skala.capstone.staff;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.IntegrationTest;
import com.skala.capstone.common.messaging.Queues;

/** 병원 관리자 병원 정보 수정. 다른 테스트가 병원 3 을 읽으므로 끝나면 원래 값으로 되돌린다. */
class HospitalInfoAdminIntegrationTest extends IntegrationTest {

	private Map<String, Object> snapshot;

	@BeforeEach
	void save() {
		snapshot = jdbc.sql("""
				SELECT phone, address_ko, address_en, description_ko, description_en, description_zh, description_ja,
				       supported_languages::text AS langs, has_interpreter, open_hours::text AS hours
				FROM app.hospitals WHERE id = 3
				""").query().singleRow();
	}

	@AfterEach
	void restore() {
		jdbc.sql("""
				UPDATE app.hospitals SET phone = :phone, address_ko = :address_ko, address_en = :address_en,
				    description_ko = :description_ko, description_en = :description_en, description_zh = :description_zh,
				    description_ja = :description_ja, supported_languages = CAST(:langs AS text[]),
				    has_interpreter = :has_interpreter, open_hours = CAST(:hours AS jsonb)
				WHERE id = 3
				""").params(snapshot).update();
		jdbc.sql("DELETE FROM app.doctors WHERE hospital_id = 3 AND name_ko LIKE '테스트%'").update();
	}

	private static Map<String, Object> hours(String sunClose) {
		Map<String, Object> h = new LinkedHashMap<>();
		for (String d : List.of("mon", "tue", "wed", "thu", "fri")) {
			h.put(d, Map.of("open", "10:00", "close", "19:00"));
		}
		h.put("sat", Map.of("open", "10:00", "close", "16:00"));
		h.put("sun", sunClose == null ? null : Map.of("open", "11:00", "close", sunClose));
		return h;
	}

	@Test
	void updateIsAppliedAndDescriptionTranslated() throws Exception {
		String admin = accessToken("admin.h3@demo.local");
		JsonNode info = body(mvc.perform(get("/api/hospital-admin/hospital").header(HttpHeaders.AUTHORIZATION, admin))
				.andExpect(status().isOk()).andReturn());
		assertThat(info.get("id").asLong()).isEqualTo(3);
		assertThat(info.get("openHours").size()).isEqualTo(7);
		assertThat(info.get("procedures")).isNotEmpty();

		Map<String, Object> req = new HashMap<>();
		req.put("phone", "02-555-1234");
		req.put("descriptionKo", "테스트 소개입니다.");
		req.put("languages", List.of("en", "ko"));
		req.put("hasInterpreter", false);
		req.put("openHours", hours(null));
		mvc.perform(patch("/api/hospital-admin/hospital").header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(req)))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.phone").value("02-555-1234"))
				.andExpect(jsonPath("$.languages[0]").value("ko"))
				.andExpect(jsonPath("$.openHours.sun").isEmpty())
				.andExpect(jsonPath("$.addressKo").value((String) snapshot.get("address_ko")));

		// 고객 화면에 바로 반영 (ko 고객은 새 소개, 휴무)
		JsonNode detail = body(mvc.perform(get("/api/hospitals/3").header(HttpHeaders.AUTHORIZATION, accessToken("customer.ko1@demo.local")))
				.andExpect(status().isOk()).andReturn());
		assertThat(detail.get("description").asText()).isEqualTo("테스트 소개입니다.");
		assertThat(detail.at("/openHours/sun").isNull()).isTrue();
		assertThat(detail.get("hasInterpreter").asBoolean()).isFalse();

		// 소개 번역 요청 (kind = HOSPITAL) → 결과 저장
		receiveFrom(Queues.REVIEW_TRANSLATE, m -> m.get("reviewId").asLong() == 3 && "HOSPITAL".equals(m.path("kind").asText()));
		rabbit.convertAndSend(Queues.EXCHANGE, Queues.REVIEW_TRANSLATED, Map.of("reviewId", 3, "ok", true, "kind", "HOSPITAL",
				"detectedLang", "ko", "translations", Map.of("en", "Test introduction.", "zh", "测试介绍。", "ja", "テスト紹介です。")));
		await(() -> "Test introduction.".equals(jdbc.sql("SELECT description_en FROM app.hospitals WHERE id = 3")
				.query(String.class).single()), "hospital description translated");
		assertThat(jdbc.sql("SELECT description_ko FROM app.hospitals WHERE id = 3").query(String.class).single())
				.isEqualTo("테스트 소개입니다.");
	}

	@Test
	void validationAndScope() throws Exception {
		String admin = accessToken("admin.h3@demo.local");
		Map<String, Object> bad = hours("10:00"); // 11:00 ~ 10:00
		mvc.perform(patch("/api/hospital-admin/hospital").header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("openHours", bad))))
				.andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("VALIDATION_FAILED"));
		mvc.perform(patch("/api/hospital-admin/hospital").header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("openHours", Map.of("mon", Map.of("open", "10:00", "close", "19:00"))))))
				.andExpect(status().isBadRequest());
		mvc.perform(patch("/api/hospital-admin/hospital").header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("phone", "call me"))))
				.andExpect(status().isBadRequest());
		mvc.perform(get("/api/hospital-admin/hospital").header(HttpHeaders.AUTHORIZATION, accessToken("counselor.h3@demo.local")))
				.andExpect(status().isForbidden());

		// 다른 병원 의사는 못 고친다
		long otherDoctor = jdbc.sql("SELECT id FROM app.doctors WHERE hospital_id = 1 LIMIT 1").query(Long.class).single();
		mvc.perform(put("/api/hospital-admin/hospital/doctors/{id}", otherDoctor).header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(doctor("테스트 다른병원"))))
				.andExpect(status().isNotFound());
	}

	@Test
	void addAndUpdateDoctorShownToCustomer() throws Exception {
		String admin = accessToken("admin.h3@demo.local");
		JsonNode created = body(mvc.perform(post("/api/hospital-admin/hospital/doctors").header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(doctor("테스트 의사"))))
				.andExpect(status().isCreated()).andReturn());
		long id = created.get("id").asLong();
		assertThat(created.get("languages").toString()).isEqualTo("[\"ko\",\"en\"]");

		Map<String, Object> edit = doctor("테스트 의사2");
		edit.put("title", "부원장");
		edit.put("specialties", List.of("NOT_A_CODE"));
		mvc.perform(put("/api/hospital-admin/hospital/doctors/{id}", id).header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(edit)))
				.andExpect(status().isBadRequest());
		edit.put("specialties", List.of());
		mvc.perform(put("/api/hospital-admin/hospital/doctors/{id}", id).header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(edit)))
				.andExpect(status().isOk()).andExpect(jsonPath("$.title").value("부원장"));

		JsonNode doctors = body(mvc.perform(get("/api/hospitals/3").header(HttpHeaders.AUTHORIZATION, accessToken("customer.en1@demo.local")))
				.andExpect(status().isOk()).andReturn()).get("doctors");
		assertThat(doctors.findValues("id").stream().map(JsonNode::asLong)).contains(id);
	}

	private Map<String, Object> doctor(String nameKo) {
		Map<String, Object> d = new HashMap<>();
		d.put("nameKo", nameKo);
		d.put("nameEn", "Dr. Test");
		d.put("title", "원장");
		d.put("careerYears", 3);
		d.put("languages", List.of("en", "ko"));
		d.put("specialties", jdbc.sql("SELECT procedure_code FROM app.price_options WHERE hospital_id = 3 LIMIT 1")
				.query(String.class).list());
		return d;
	}
}
