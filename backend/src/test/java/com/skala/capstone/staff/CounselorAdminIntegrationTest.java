package com.skala.capstone.staff;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.IntegrationTest;

/** 병원 관리자 상담사 관리. 시드 상담사는 다른 테스트가 쓰므로 비활성·새 문의 끄기는 새로 만든 상담사로만 한다. */
class CounselorAdminIntegrationTest extends IntegrationTest {

	private JsonNode create(String admin, String email, List<String> languages) throws Exception {
		return body(mvc.perform(post("/api/hospital-admin/counselors").header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("name", "테스트 상담사", "email", email, "password", DEMO_PASSWORD,
						"languages", languages))))
				.andExpect(status().isCreated()).andReturn());
	}

	private static String email() {
		return "counselor." + UUID.randomUUID().toString().substring(0, 8) + "@test.local";
	}

	@Test
	void listIsScopedToOwnHospitalAndRoleChecked() throws Exception {
		JsonNode roster = body(mvc.perform(get("/api/hospital-admin/counselors")
				.header(HttpHeaders.AUTHORIZATION, accessToken("admin.h1@demo.local")))
				.andExpect(status().isOk()).andReturn());
		assertThat(roster.get("items")).isNotEmpty();
		roster.get("items").forEach(c -> assertThat(c.get("email").asText()).doesNotContain(".h2@"));
		JsonNode seed = roster.get("items").get(0);
		assertThat(seed.get("email").asText()).isEqualTo("counselor.h1@demo.local");
		assertThat(seed.get("languages")).isNotEmpty();
		assertThat(roster.has("waitingConsultations")).isTrue();

		mvc.perform(get("/api/hospital-admin/counselors")
				.header(HttpHeaders.AUTHORIZATION, accessToken("counselor.h1@demo.local")))
				.andExpect(status().isForbidden());
	}

	@Test
	void createUpdateAndLogin() throws Exception {
		String admin = accessToken("admin.h2@demo.local");
		String email = email();
		JsonNode created = create(admin, email, List.of("zh", "ko", "zh"));
		long id = created.get("id").asLong();
		assertThat(created.get("languages").toString()).isEqualTo("[\"ko\",\"zh\"]");
		assertThat(created.get("active").asBoolean()).isTrue();
		assertThat(created.get("acceptingNew").asBoolean()).isTrue();
		assertThat(created.get("lastLoginAt").isNull()).isTrue();

		// 새 상담사로 로그인 → 상담사 역할·같은 병원
		JsonNode login = body(login(email));
		assertThat(login.at("/user/role").asText()).isEqualTo("COUNSELOR");
		assertThat(login.at("/user/hospitalId").asLong()).isEqualTo(2);

		// 이메일 중복(대소문자 무시)
		mvc.perform(post("/api/hospital-admin/counselors").header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("name", "중복", "email", email.toUpperCase(), "password", DEMO_PASSWORD,
						"languages", List.of("ko")))))
				.andExpect(status().isConflict()).andExpect(jsonPath("$.code").value("EMAIL_DUPLICATED"));

		// 보낸 필드만 수정
		mvc.perform(patch("/api/hospital-admin/counselors/{id}", id).header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("languages", List.of("ja", "en")))))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.name").value("테스트 상담사"))
				.andExpect(jsonPath("$.languages[0]").value("en"))
				.andExpect(jsonPath("$.languages[1]").value("ja"))
				.andExpect(jsonPath("$.lastLoginAt").isNotEmpty());

		// 다른 병원 관리자는 못 본다
		mvc.perform(patch("/api/hospital-admin/counselors/{id}", id)
				.header(HttpHeaders.AUTHORIZATION, accessToken("admin.h3@demo.local"))
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("name", "x"))))
				.andExpect(status().isNotFound());
	}

	@Test
	void validationErrors() throws Exception {
		String admin = accessToken("admin.h2@demo.local");
		mvc.perform(post("/api/hospital-admin/counselors").header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("name", " ", "email", "not-an-email", "password", "short",
						"languages", List.of("fr")))))
				.andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("VALIDATION_FAILED"));
		mvc.perform(patch("/api/hospital-admin/counselors/{id}", 1).header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("languages", List.of()))))
				.andExpect(status().isBadRequest());
		// 고객 id 는 상담사가 아니므로 404
		mvc.perform(post("/api/hospital-admin/counselors/{id}/deactivate", 1).header(HttpHeaders.AUTHORIZATION, admin))
				.andExpect(status().isNotFound());
	}

	@Test
	void deactivatedCounselorCannotLoginUntilActivated() throws Exception {
		String admin = accessToken("admin.h3@demo.local");
		String email = email();
		long id = create(admin, email, List.of("ko")).get("id").asLong();
		login(email);

		mvc.perform(post("/api/hospital-admin/counselors/{id}/deactivate", id).header(HttpHeaders.AUTHORIZATION, admin))
				.andExpect(status().isOk()).andExpect(jsonPath("$.active").value(false));
		assertThat(jdbc.sql("SELECT count(*) FROM app.refresh_tokens WHERE user_id = :id AND revoked_at IS NULL")
				.param("id", id).query(Integer.class).single()).isZero();
		mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("email", email, "password", DEMO_PASSWORD))))
				.andExpect(status().isUnauthorized()).andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"));

		mvc.perform(post("/api/hospital-admin/counselors/{id}/activate", id).header(HttpHeaders.AUTHORIZATION, admin))
				.andExpect(status().isOk()).andExpect(jsonPath("$.active").value(true));
		login(email);
	}

	@Test
	void cannotDeactivateWithOngoingConsultation() throws Exception {
		Integer ongoing = jdbc.sql("SELECT count(*) FROM app.consultations WHERE counselor_id = 7 AND status = 'ACTIVE'")
				.query(Integer.class).single();
		if (ongoing == 0) {
			return; // 다른 테스트가 시드 상담을 닫은 경우
		}
		mvc.perform(post("/api/hospital-admin/counselors/{id}/deactivate", 7)
				.header(HttpHeaders.AUTHORIZATION, accessToken("admin.h1@demo.local")))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("INVALID_STATE_TRANSITION"))
				.andExpect(jsonPath("$.details.activeConsultations").value(ongoing));
	}

	@Test
	void notAcceptingNewHidesWaitingInquiries() throws Exception {
		String admin = accessToken("admin.h1@demo.local");
		String email = email();
		long id = create(admin, email, List.of("ko", "en")).get("id").asLong();
		mvc.perform(patch("/api/hospital-admin/counselors/{id}", id).header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("acceptingNew", false))))
				.andExpect(status().isOk()).andExpect(jsonPath("$.acceptingNew").value(false));

		String counselor = accessToken(email);
		JsonNode inbox = body(mvc.perform(get("/api/counselor/consultations").header(HttpHeaders.AUTHORIZATION, counselor))
				.andExpect(status().isOk()).andReturn());
		inbox.forEach(c -> assertThat(c.get("status").asText()).isNotEqualTo("WAITING"));
		Long waitingId = jdbc.sql("SELECT id FROM app.consultations WHERE hospital_id = 1 AND status = 'WAITING' LIMIT 1")
				.query(Long.class).optional().orElse(null);
		if (waitingId != null) {
			mvc.perform(post("/api/counselor/consultations/{id}/accept", waitingId).header(HttpHeaders.AUTHORIZATION, counselor))
					.andExpect(status().isForbidden());
		}

		mvc.perform(patch("/api/hospital-admin/counselors/{id}", id).header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("acceptingNew", true))))
				.andExpect(status().isOk());
		int waiting = jdbc.sql("SELECT count(*) FROM app.consultations WHERE hospital_id = 1 AND status = 'WAITING'")
				.query(Integer.class).single();
		JsonNode again = body(mvc.perform(get("/api/counselor/consultations").param("status", "WAITING")
				.header(HttpHeaders.AUTHORIZATION, counselor)).andExpect(status().isOk()).andReturn());
		assertThat(again.size()).isEqualTo(waiting);
	}
}
