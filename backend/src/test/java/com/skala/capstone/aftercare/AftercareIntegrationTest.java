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
		assertThat(room.get("reservationStatus").asText()).isEqualTo("CONFIRMED");
		assertThat(room.get("daysFromProcedure").isInt()).isTrue();
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

		// 반려된 예약 → 409, 남의 예약 → 403, 상담사 → 403
		mvc.perform(post("/api/reservations/{id}/aftercare-conversation", 11).header(HttpHeaders.AUTHORIZATION, customer))
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

	/** 승인 대기 예약 7: 방 생성, 하루 한 번 안내(INTRO → 다음 날 DAILY), 답변 알림, 예약 취소 후 안내 중단 */
	@Test
	void pendingReservationGetsOneGuidePerDayAndNotifications() throws Exception {
		String customer = accessToken("customer.en1@demo.local");
		JsonNode room = body(mvc.perform(post("/api/reservations/{id}/aftercare-conversation", 7)
				.header(HttpHeaders.AUTHORIZATION, customer)).andExpect(status().isCreated()).andReturn());
		assertThat(room.get("reservationStatus").asText()).isEqualTo("PENDING");
		String conversationId = room.get("conversationId").asText();
		UUID cid = UUID.fromString(conversationId);
		String intro = room.get("activeTaskId").asText();
		receiveFrom(Queues.AI_TASK_REQUESTED, b -> intro.equals(b.path("taskId").asText()));

		// agent 가 답을 끝냈는데 보고 있는 브라우저가 없으면 → 사후관리 알림
		rabbit.convertAndSend(Queues.EXCHANGE, Queues.AI_TASK_EVENT, Map.of("taskId", intro, "seq", 1, "event", "DONE",
				"data", Map.of("answer", "guide", "sources", List.of()), "at", "2026-10-22T10:00:00+09:00"));
		await(() -> "DONE".equals(taskStatus(intro)), "intro done");
		await(() -> jdbc.sql("""
				SELECT count(*) FROM app.notifications WHERE user_id = 1 AND type = 'AFTERCARE_MESSAGE'
				AND payload->>'conversationId' = :c
				""").param("c", conversationId).query(Long.class).single() == 1, "aftercare notification");

		// 같은 날 다시 열면 새 안내 없음
		mvc.perform(post("/api/reservations/{id}/aftercare-conversation", 7).header(HttpHeaders.AUTHORIZATION, customer))
				.andExpect(status().isOk()).andExpect(jsonPath("$.activeTaskId").doesNotExist());
		assertThat(guideCount(cid)).isEqualTo(1);

		// 어제 안내였던 것으로 바꾸면, 오늘 처음 열 때 DAILY 안내를 요청한다
		jdbc.sql("UPDATE app.ai_tasks SET created_at = created_at - interval '1 day' WHERE conversation_id = :c")
				.param("c", cid).update();
		JsonNode again = body(mvc.perform(post("/api/reservations/{id}/aftercare-conversation", 7)
				.header(HttpHeaders.AUTHORIZATION, customer)).andExpect(status().isOk()).andReturn());
		String daily = again.get("activeTaskId").asText();
		JsonNode sent = receiveFrom(Queues.AI_TASK_REQUESTED, b -> daily.equals(b.path("taskId").asText()));
		assertThat(sent.at("/action/type").asText()).isEqualTo("AFTERCARE_DAILY");
		assertThat(guideCount(cid)).isEqualTo(2);

		// 예약이 취소되면 방과 기록은 남고 새 안내는 요청하지 않는다
		jdbc.sql("UPDATE app.ai_tasks SET status = 'DONE', created_at = created_at - interval '1 day' WHERE conversation_id = :c")
				.param("c", cid).update();
		jdbc.sql("UPDATE app.reservations SET status = 'CANCELLED' WHERE id = 7").update();
		try {
			mvc.perform(post("/api/reservations/{id}/aftercare-conversation", 7).header(HttpHeaders.AUTHORIZATION, customer))
					.andExpect(status().isOk()).andExpect(jsonPath("$.reservationStatus").value("CANCELLED"))
					.andExpect(jsonPath("$.activeTaskId").doesNotExist());
			assertThat(guideCount(cid)).isEqualTo(2);
		} finally {
			jdbc.sql("UPDATE app.reservations SET status = 'PENDING' WHERE id = 7").update();
		}
	}

	/** 운영자 버튼(=매일 스케줄러 작업): 방이 없던 확정 예약 13 에도 방을 만들고 안내, 같은 날 두 번째 실행은 건너뜀 */
	@Test
	void operatorSendsDailyGuidesOncePerDay() throws Exception {
		jdbc.sql("""
				UPDATE app.slots SET start_at = date_trunc('minute', now()) + interval '2 days 3 minutes',
				    end_at = date_trunc('minute', now()) + interval '2 days 33 minutes'
				WHERE id = (SELECT slot_id FROM app.reservations WHERE id = 13)
				""").update();
		mvc.perform(post("/api/ops/aftercare/daily-guides").header(HttpHeaders.AUTHORIZATION,
				accessToken("customer.en2@demo.local"))).andExpect(status().isForbidden());

		String operator = accessToken("operator@demo.local");
		JsonNode first = body(mvc.perform(post("/api/ops/aftercare/daily-guides").header(HttpHeaders.AUTHORIZATION, operator))
				.andExpect(status().isOk()).andReturn());
		assertThat(first.get("checked").asInt()).isPositive();
		UUID room = jdbc.sql("SELECT conversation_id FROM app.aftercare_rooms WHERE reservation_id = 13")
				.query(UUID.class).single();
		assertThat(guideCount(room)).isEqualTo(1);
		String task = jdbc.sql("SELECT id::text FROM app.ai_tasks WHERE conversation_id = :c").param("c", room)
				.query(String.class).single();
		JsonNode sent = receiveFrom(Queues.AI_TASK_REQUESTED, b -> task.equals(b.path("taskId").asText()));
		assertThat(sent.at("/action/type").asText()).isEqualTo("AFTERCARE_INTRO");
		assertThat(sent.at("/user/role").asText()).isEqualTo("CUSTOMER");

		mvc.perform(post("/api/ops/aftercare/daily-guides").header(HttpHeaders.AUTHORIZATION, operator))
				.andExpect(status().isOk());
		assertThat(guideCount(room)).isEqualTo(1);
	}

	private long guideCount(UUID conversationId) {
		return jdbc.sql("""
				SELECT count(*) FROM app.ai_tasks WHERE conversation_id = :c
				AND action->>'type' IN ('AFTERCARE_INTRO','AFTERCARE_DAILY')
				""").param("c", conversationId).query(Long.class).single();
	}

	private String taskStatus(String taskId) {
		return jdbc.sql("SELECT status FROM app.ai_tasks WHERE id = :id").param("id", UUID.fromString(taskId))
				.query(String.class).single();
	}

	private String mode(UUID conversationId) {
		return jdbc.sql("SELECT mode FROM app.conversations WHERE id = :id").param("id", conversationId)
				.query(String.class).single();
	}
}
