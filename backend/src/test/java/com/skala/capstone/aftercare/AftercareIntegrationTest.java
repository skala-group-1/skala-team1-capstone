package com.skala.capstone.aftercare;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
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
import com.skala.capstone.common.messaging.Queues;

/** 사후관리 대화방: 확정 예약 1건당 1개, 첫 안내 요청, 상담 종료 후 AFTERCARE 복귀. 고객 1(customer.en1)의 예약을 쓴다 */
class AftercareIntegrationTest extends IntegrationTest {

	@Test
	void opensOneRoomPerConfirmedReservationAndRequestsIntro() throws Exception {
		String customer = accessToken("customer.en1@demo.local");

		// 확정 예약 1 → 새 방(201) + 첫 안내 작업이 AFTERCARE 모드로 큐에 들어간다
		JsonNode room = body(mvc.perform(post("/api/reservations/{id}/aftercare-conversation", 1)
				.header(HttpHeaders.AUTHORIZATION, customer))
				.andExpect(status().isCreated()).andReturn());
		String conversationId = room.get("conversationId").asText();
		assertThat(room.get("mode").asText()).isEqualTo("AFTERCARE");
		assertThat(room.get("procedureCode").asText()).isEqualTo("SHURINK");
		assertThat(room.at("/hospital/id").asLong()).isEqualTo(1);
		assertThat(room.get("startAt").asText()).endsWith("+09:00");
		assertThat(room.get("activeTaskId").isNull()).isFalse();
		JsonNode intro = receiveFrom(Queues.AI_TASK_REQUESTED, b -> conversationId.equals(b.path("conversationId").asText()));
		assertThat(intro.at("/conversation/mode").asText()).isEqualTo("AFTERCARE");
		assertThat(intro.at("/conversation/hospitalId").asLong()).isEqualTo(1);
		assertThat(intro.at("/action/type").asText()).isEqualTo("AFTERCARE_INTRO");
		assertThat(intro.at("/action/reservationId").asLong()).isEqualTo(1);

		// 다시 열면 같은 방(200), 첫 안내는 다시 요청하지 않는다
		mvc.perform(post("/api/reservations/{id}/aftercare-conversation", 1).header(HttpHeaders.AUTHORIZATION, customer))
				.andExpect(status().isOk()).andExpect(jsonPath("$.conversationId").value(conversationId));
		assertThat(jdbc.sql("SELECT count(*) FROM app.ai_tasks WHERE conversation_id = :c")
				.param("c", UUID.fromString(conversationId)).query(Long.class).single()).isEqualTo(1);

		// 목록과 공통 대화 API 에서도 보인다
		mvc.perform(get("/api/aftercare/conversations").header(HttpHeaders.AUTHORIZATION, customer))
				.andExpect(jsonPath("$[?(@.conversationId == '" + conversationId + "')].reservationId").value(1));
		mvc.perform(get("/api/ai/conversations/{id}", conversationId).header(HttpHeaders.AUTHORIZATION, customer))
				.andExpect(jsonPath("$.mode").value("AFTERCARE"));

		// 확정이 아닌 예약 → 409, 남의 예약 → 403, 상담사 → 403
		mvc.perform(post("/api/reservations/{id}/aftercare-conversation", 7).header(HttpHeaders.AUTHORIZATION, customer))
				.andExpect(status().isConflict()).andExpect(jsonPath("$.code").value("INVALID_STATE_TRANSITION"));
		mvc.perform(post("/api/reservations/{id}/aftercare-conversation", 4).header(HttpHeaders.AUTHORIZATION, customer))
				.andExpect(status().isForbidden());
		mvc.perform(post("/api/reservations/{id}/aftercare-conversation", 1)
				.header(HttpHeaders.AUTHORIZATION, accessToken("counselor.h2@demo.local")))
				.andExpect(status().isForbidden());
	}

	@Test
	void consultationFromAftercareRoomReturnsToAftercare() throws Exception {
		String customer = accessToken("customer.en1@demo.local");
		String conversationId = body(mvc.perform(post("/api/reservations/{id}/aftercare-conversation", 16)
				.header(HttpHeaders.AUTHORIZATION, customer)).andReturn()).get("conversationId").asText();
		UUID cid = UUID.fromString(conversationId);
		// 첫 안내 작업을 끝난 것으로 둔다 (가짜 agent 없이 상담 요청만 확인)
		jdbc.sql("UPDATE app.ai_tasks SET status = 'DONE' WHERE conversation_id = :c").param("c", cid).update();

		long consultationId = body(mvc.perform(post("/internal/consultations")
				.header("X-Service-Token", "test-service-token").header("X-Acting-User-Id", "1")
				.contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("hospitalId", 3, "conversationId", conversationId,
						"summaryCard", Map.of("procedure", "Jaw Botox", "questions", List.of("Is swelling normal?")),
						"consent", true))))
				.andExpect(status().isCreated()).andReturn()).get("id").asLong();
		assertThat(mode(cid)).isEqualTo("HUMAN");

		// 상담 중인 사후관리 방은 '이 병원에 물어보기'의 병원 방으로 재사용되지 않는다
		JsonNode hospitalRoom = body(mvc.perform(post("/api/ai/conversations").header(HttpHeaders.AUTHORIZATION, customer)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("hospitalId", 3)))).andReturn());
		assertThat(hospitalRoom.get("id").asText()).isNotEqualTo(conversationId);

		mvc.perform(post("/api/consultations/{id}/close", consultationId).header(HttpHeaders.AUTHORIZATION, customer))
				.andExpect(status().isOk());
		assertThat(mode(cid)).isEqualTo("AFTERCARE");
	}

	private String mode(UUID conversationId) {
		return jdbc.sql("SELECT mode FROM app.conversations WHERE id = :id").param("id", conversationId)
				.query(String.class).single();
	}
}
