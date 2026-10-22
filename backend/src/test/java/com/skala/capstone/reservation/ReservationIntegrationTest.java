package com.skala.capstone.reservation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MvcResult;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.IntegrationTest;
import com.skala.capstone.common.config.AppProperties;

/**
 * 예약 상태 전이·동시성·권한 (16 명세 4장, 11 문서 7장).
 * 테스트끼리 같은 DB 를 쓰므로 {@link #takeFreeSlot} 으로 매번 아직 안 쓴 슬롯을 고른다.
 */
class ReservationIntegrationTest extends IntegrationTest {

	@Autowired
	AppProperties app;

	@Autowired
	ReservationExpiry expiry;

	record FreeSlot(long hospitalId, long slotId, String procedureCode) {
	}

	@Test
	void createIsIdempotentAndHoldsSlot() throws Exception {
		String token = accessToken("customer.en1@demo.local");
		FreeSlot s = takeFreeSlot(1);
		String key = UUID.randomUUID().toString();

		JsonNode first = body(create(token, key, s).andExpect(status().isCreated()).andReturn());
		assertThat(first.get("status").asText()).isEqualTo("PENDING");
		assertThat(first.get("source").asText()).isEqualTo("DIRECT");
		assertThat(first.get("holdExpiresAt").asText()).endsWith("+09:00");
		assertThat(first.get("customer").isNull()).isTrue();

		JsonNode again = body(create(token, key, s).andExpect(status().isOk()).andReturn());
		assertThat(again.get("id").asLong()).isEqualTo(first.get("id").asLong());
		assertThat(slotStatus(s.slotId())).isEqualTo("HELD");

		// 병원 1 관리자(id 8)에게 알림이 notify 큐를 거쳐 저장된다
		awaitNotification(8, "RESERVATION_REQUESTED", first.get("id").asLong());
	}

	@Test
	void concurrentRequestsForSameSlotOnlyOneSucceeds() throws Exception {
		FreeSlot s = takeFreeSlot(4);
		String a = accessToken("customer.zh2@demo.local");
		String b = accessToken("customer.ja2@demo.local");
		ExecutorService pool = Executors.newFixedThreadPool(2);
		List<Callable<Integer>> calls = List.of(
				() -> create(a, UUID.randomUUID().toString(), s).andReturn().getResponse().getStatus(),
				() -> create(b, UUID.randomUUID().toString(), s).andReturn().getResponse().getStatus());
		List<Integer> codes = new ArrayList<>();
		for (Future<Integer> f : pool.invokeAll(calls)) {
			codes.add(f.get());
		}
		pool.shutdown();
		assertThat(codes).containsExactlyInAnyOrder(201, 409);

		// 이미 잡힌 슬롯 → 409 SLOT_UNAVAILABLE + 대안 슬롯
		create(a, UUID.randomUUID().toString(), s)
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("SLOT_UNAVAILABLE"))
				.andExpect(jsonPath("$.details.alternatives.length()").value(3));
	}

	@Test
	void hospitalAdminApprovesOnlyOwnHospital() throws Exception {
		FreeSlot s = takeFreeSlot(2);
		long id = body(create(accessToken("customer.en2@demo.local"), UUID.randomUUID().toString(), s)
				.andExpect(status().isCreated()).andReturn()).get("id").asLong();

		// 병원 1 관리자가 병원 2 예약 승인 → 403
		mvc.perform(post("/api/hospital-admin/reservations/{id}/approve", id)
				.header(HttpHeaders.AUTHORIZATION, accessToken("admin.h1@demo.local")))
				.andExpect(status().isForbidden());

		JsonNode approved = body(mvc.perform(post("/api/hospital-admin/reservations/{id}/approve", id)
				.header(HttpHeaders.AUTHORIZATION, accessToken("admin.h2@demo.local")))
				.andExpect(status().isOk()).andReturn());
		assertThat(approved.get("status").asText()).isEqualTo("CONFIRMED");
		assertThat(approved.at("/customer/name").asText()).isEqualTo("J** W**");
		assertThat(slotStatus(s.slotId())).isEqualTo("BOOKED");
		awaitNotification(2, "RESERVATION_CONFIRMED", id);

		// 이미 확정된 예약을 다시 승인 → 409
		mvc.perform(post("/api/hospital-admin/reservations/{id}/approve", id)
				.header(HttpHeaders.AUTHORIZATION, accessToken("admin.h2@demo.local")))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("INVALID_STATE_TRANSITION"));
	}

	@Test
	void rejectWithAlternativesThenAcceptOne() throws Exception {
		String customer = accessToken("customer.ja1@demo.local");
		String admin = accessToken("admin.h3@demo.local");
		FreeSlot s = takeFreeSlot(3);
		long id = body(create(customer, UUID.randomUUID().toString(), s).andReturn()).get("id").asLong();
		List<Long> alternatives = List.of(takeFreeSlot(3, s.procedureCode()).slotId(),
				takeFreeSlot(3, s.procedureCode()).slotId());

		mvc.perform(post("/api/hospital-admin/reservations/{id}/reject", id).header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("alternativeSlotIds", alternatives))))
				.andExpect(status().isBadRequest()); // 사유 필수
		JsonNode rejected = body(mvc.perform(post("/api/hospital-admin/reservations/{id}/reject", id)
				.header(HttpHeaders.AUTHORIZATION, admin).contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("reason", "의사 일정 변경", "alternativeSlotIds", alternatives))))
				.andExpect(status().isOk()).andReturn());
		assertThat(rejected.get("status").asText()).isEqualTo("REJECTED");
		assertThat(rejected.get("alternatives")).hasSize(2);
		assertThat(slotStatus(s.slotId())).isEqualTo("AVAILABLE");

		// 제안되지 않은 슬롯 → 400, 제안된 슬롯 → 새 PENDING
		mvc.perform(post("/api/reservations/{id}/accept-alternative", id).header(HttpHeaders.AUTHORIZATION, customer)
				.header("Idempotency-Key", UUID.randomUUID().toString())
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("slotId", s.slotId()))))
				.andExpect(status().isBadRequest());
		JsonNode accepted = body(mvc.perform(post("/api/reservations/{id}/accept-alternative", id)
				.header(HttpHeaders.AUTHORIZATION, customer).header("Idempotency-Key", UUID.randomUUID().toString())
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("slotId", alternatives.get(0)))))
				.andExpect(status().isCreated()).andReturn());
		assertThat(accepted.get("status").asText()).isEqualTo("PENDING");
		assertThat(accepted.at("/slot/id").asLong()).isEqualTo(alternatives.get(0));
		assertThat(accepted.at("/procedure/code").asText()).isEqualTo(s.procedureCode());
	}

	@Test
	void onlyOwnerCanCancelAndOnlyOnce() throws Exception {
		String owner = accessToken("customer.en1@demo.local");
		FreeSlot s = takeFreeSlot(5);
		long id = body(create(owner, UUID.randomUUID().toString(), s).andReturn()).get("id").asLong();

		// 고객 A 의 예약을 고객 B 가 취소 → 403 + 감사 로그
		long deniedBefore = count("SELECT count(*) FROM app.audit_logs WHERE action = 'ACCESS_DENIED'");
		mvc.perform(post("/api/reservations/{id}/cancel", id)
				.header(HttpHeaders.AUTHORIZATION, accessToken("customer.zh1@demo.local")))
				.andExpect(status().isForbidden());
		assertThat(count("SELECT count(*) FROM app.audit_logs WHERE action = 'ACCESS_DENIED'")).isGreaterThan(deniedBefore);

		mvc.perform(post("/api/reservations/{id}/cancel", id).header(HttpHeaders.AUTHORIZATION, owner)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("reason", "plan changed"))))
				.andExpect(status().isOk()).andExpect(jsonPath("$.status").value("CANCELLED"));
		assertThat(slotStatus(s.slotId())).isEqualTo("AVAILABLE");
		mvc.perform(post("/api/reservations/{id}/cancel", id).header(HttpHeaders.AUTHORIZATION, owner))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("INVALID_STATE_TRANSITION"))
				.andExpect(jsonPath("$.details.from").value("CANCELLED"));
	}

	@Test
	void expiredHoldIsReleasedByScheduler() throws Exception {
		FreeSlot s = takeFreeSlot(6);
		long id = body(create(accessToken("customer.zh1@demo.local"), UUID.randomUUID().toString(), s).andReturn())
				.get("id").asLong();
		jdbc.sql("UPDATE app.reservations SET hold_expires_at = now() - interval '1 minute' WHERE id = :id")
				.param("id", id).update();
		expiry.expireDue();
		assertThat(jdbc.sql("SELECT status FROM app.reservations WHERE id = :id").param("id", id)
				.query(String.class).single()).isEqualTo("EXPIRED");
		assertThat(slotStatus(s.slotId())).isEqualTo("AVAILABLE");
	}

	@Test
	void validationErrors() throws Exception {
		String token = accessToken("customer.en1@demo.local");
		FreeSlot s = takeFreeSlot(7);
		mvc.perform(post("/api/reservations").header(HttpHeaders.AUTHORIZATION, token)
				.contentType(MediaType.APPLICATION_JSON).content(json(requestBody(s))))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.details.fields[0].field").value("Idempotency-Key"));
		// 다른 병원의 슬롯 → 404
		create(token, UUID.randomUUID().toString(), new FreeSlot(1, s.slotId(), s.procedureCode()))
				.andExpect(status().isNotFound());
		// 상담사는 예약 생성 불가
		create(accessToken("counselor.h1@demo.local"), UUID.randomUUID().toString(), s)
				.andExpect(status().isForbidden());
	}

	@Test
	void internalApiActsAsCustomerAndCannotTouchOthers() throws Exception {
		FreeSlot s = takeFreeSlot(8);
		MvcResult created = mvc.perform(post("/internal/reservations")
				.header("X-Service-Token", app.serviceToken()).header("X-Acting-User-Id", "6")
				.header("Idempotency-Key", UUID.randomUUID().toString())
				.contentType(MediaType.APPLICATION_JSON).content(json(requestBody(s))))
				.andExpect(status().isCreated()).andReturn();
		long id = body(created).get("id").asLong();
		assertThat(body(created).get("source").asText()).isEqualTo("AI");

		// 프롬프트 주입으로 다른 사용자(1번)로 취소 시도 → 403
		mvc.perform(post("/internal/reservations/{id}/cancel", id)
				.header("X-Service-Token", app.serviceToken()).header("X-Acting-User-Id", "1"))
				.andExpect(status().isForbidden());
		mvc.perform(get("/internal/reservations/mine").header("X-Service-Token", app.serviceToken())
				.header("X-Acting-User-Id", "6"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$[?(@.id == " + id + ")]").exists());
	}

	@Test
	void dashboardAndListAreScopedToOwnHospital() throws Exception {
		String admin = accessToken("admin.h1@demo.local");
		mvc.perform(get("/api/hospital-admin/dashboard").header(HttpHeaders.AUTHORIZATION, admin))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.pendingReservations").isNumber())
				.andExpect(jsonPath("$.recentRequests").isArray());
		JsonNode page = body(mvc.perform(get("/api/hospital-admin/reservations")
				.header(HttpHeaders.AUTHORIZATION, admin).param("hospitalId", "2"))
				.andExpect(status().isOk()).andReturn());
		for (JsonNode r : page.get("items")) {
			assertThat(r.at("/hospital/id").asLong()).isEqualTo(1);
		}
	}

	@Test
	void reviewOnlyForOwnConfirmedReservationOnce() throws Exception {
		String owner = accessToken("customer.ko1@demo.local");
		FreeSlot s = takeFreeSlot(3);
		long id = body(create(owner, UUID.randomUUID().toString(), s).andExpect(status().isCreated()).andReturn())
				.get("id").asLong();
		Map<String, Object> review = Map.of("rating", 4, "content", "  상담이 친절했고 통역도 정확했어요.  ");

		// PENDING → 아직 못 쓴다
		JsonNode pending = body(mvc.perform(get("/api/reservations/{id}", id).header(HttpHeaders.AUTHORIZATION, owner))
				.andExpect(status().isOk()).andReturn());
		assertThat(pending.get("reviewable").asBoolean()).isFalse();
		writeReview(owner, id, review).andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("REVIEW_NOT_ALLOWED"));

		mvc.perform(post("/api/hospital-admin/reservations/{id}/approve", id)
				.header(HttpHeaders.AUTHORIZATION, accessToken("admin.h3@demo.local")))
				.andExpect(status().isOk());
		JsonNode confirmed = body(mvc.perform(get("/api/reservations/{id}", id).header(HttpHeaders.AUTHORIZATION, owner))
				.andExpect(status().isOk()).andReturn());
		assertThat(confirmed.get("reviewable").asBoolean()).isTrue();
		assertThat(confirmed.get("reviewId").isNull()).isTrue();

		// 남의 예약 → 403, 입력 검증 → 400
		writeReview(accessToken("customer.zh1@demo.local"), id, review).andExpect(status().isForbidden());
		writeReview(owner, id, Map.of("rating", 6, "content", "short"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("VALIDATION_FAILED"));

		JsonNode created = body(writeReview(owner, id, review).andExpect(status().isCreated()).andReturn());
		long reviewId = created.get("id").asLong();
		assertThat(created.get("rating").asInt()).isEqualTo(4);
		assertThat(created.get("procedureCode").asText()).isEqualTo(s.procedureCode());
		assertThat(created.get("content").asText()).isEqualTo("상담이 친절했고 통역도 정확했어요.");
		assertThat(created.get("createdAt").asText()).endsWith("+09:00");

		// DB: 예약·병원·작성자 프로필(1997-07-14, F, KR, ko)에서 채워진 값
		Map<String, Object> row = jdbc.sql("SELECT * FROM app.reviews WHERE id = :id").param("id", reviewId)
				.query().singleRow();
		assertThat(row.get("reservation_id")).isEqualTo(id);
		assertThat(row.get("hospital_id")).isEqualTo(3L);
		assertThat(row.get("user_id")).isEqualTo(14L);
		assertThat(row.get("age_group")).isEqualTo("20s");
		assertThat(row.get("gender")).isEqualTo("F");
		assertThat(row.get("reviewer_nationality")).isEqualTo("KR");
		assertThat(row.get("lang")).isEqualTo("ko");

		JsonNode after = body(mvc.perform(get("/api/reservations/{id}", id).header(HttpHeaders.AUTHORIZATION, owner))
				.andExpect(status().isOk()).andReturn());
		assertThat(after.get("reviewable").asBoolean()).isFalse();
		assertThat(after.get("reviewId").asLong()).isEqualTo(reviewId);

		// 예약당 1회
		writeReview(owner, id, review).andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("REVIEW_ALREADY_EXISTS"));

		// 병원 리뷰 목록(최신순) 맨 위에 보인다
		mvc.perform(get("/api/hospitals/{id}/reviews", 3).param("lang", "ko").header(HttpHeaders.AUTHORIZATION, owner))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.items[0].id").value(reviewId));

		// 예약을 취소하면 리뷰는 남지만 목록·통계에서 숨겨진다
		long countBefore = reviewCount(3);
		mvc.perform(post("/api/reservations/{id}/cancel", id).header(HttpHeaders.AUTHORIZATION, owner))
				.andExpect(status().isOk());
		assertThat(count("SELECT count(*) FROM app.reviews WHERE id = " + reviewId)).isEqualTo(1);
		assertThat(reviewCount(3)).isEqualTo(countBefore - 1);
		JsonNode list = body(mvc.perform(get("/api/hospitals/{id}/reviews", 3).param("lang", "ko").param("size", "50")
				.header(HttpHeaders.AUTHORIZATION, owner)).andExpect(status().isOk()).andReturn());
		list.get("items").forEach(item -> assertThat(item.get("id").asLong()).isNotEqualTo(reviewId));
		JsonNode cancelled = body(mvc.perform(get("/api/reservations/{id}", id).header(HttpHeaders.AUTHORIZATION, owner))
				.andExpect(status().isOk()).andReturn());
		assertThat(cancelled.get("reviewable").asBoolean()).isFalse();
	}

	private long reviewCount(long hospitalId) {
		return jdbc.sql("SELECT review_count FROM app.hospital_review_stats WHERE hospital_id = :h")
				.param("h", hospitalId).query(Long.class).single();
	}

	// ------------------------------------------------------------------ helpers

	private org.springframework.test.web.servlet.ResultActions writeReview(String token, long reservationId,
			Map<String, Object> body) throws Exception {
		return mvc.perform(post("/api/reservations/{id}/review", reservationId).header(HttpHeaders.AUTHORIZATION, token)
				.contentType(MediaType.APPLICATION_JSON).content(json(body)));
	}

	private org.springframework.test.web.servlet.ResultActions create(String token, String key, FreeSlot s)
			throws Exception {
		return mvc.perform(post("/api/reservations").header(HttpHeaders.AUTHORIZATION, token)
				.header("Idempotency-Key", key).contentType(MediaType.APPLICATION_JSON).content(json(requestBody(s))));
	}

	private static Map<String, Object> requestBody(FreeSlot s) {
		return Map.of("hospitalId", s.hospitalId(), "slotId", s.slotId(), "procedureCode", s.procedureCode(),
				"note", "test");
	}

	private FreeSlot takeFreeSlot(long hospitalId) {
		return takeFreeSlot(hospitalId, null);
	}

	/** 그 병원에서 시술 담당 의사가 있는, 아직 아무도 안 쓴 미래 AVAILABLE 슬롯 (테스트 간 충돌 방지를 위해 무작위) */
	private synchronized FreeSlot takeFreeSlot(long hospitalId, String procedureCode) {
		return jdbc.sql("""
				SELECT s.id, po.procedure_code FROM app.slots s
				JOIN app.doctors d ON d.id = s.doctor_id
				JOIN app.price_options po ON po.hospital_id = s.hospital_id AND po.procedure_code = ANY(d.specialties)
				WHERE s.hospital_id = :h AND s.status = 'AVAILABLE' AND s.start_at > now() + interval '1 day'
				  AND (CAST(:p AS varchar) IS NULL OR po.procedure_code = CAST(:p AS varchar))
				  AND NOT EXISTS (SELECT 1 FROM app.reservations r WHERE r.slot_id = s.id)
				ORDER BY random() LIMIT 1
				""").param("h", hospitalId).param("p", procedureCode)
				.query((rs, i) -> new FreeSlot(hospitalId, rs.getLong("id"), rs.getString("procedure_code")))
				.single();
	}

	private String slotStatus(long slotId) {
		return jdbc.sql("SELECT status FROM app.slots WHERE id = :id").param("id", slotId).query(String.class).single();
	}

	private long count(String sql) {
		return jdbc.sql(sql).query(Long.class).single();
	}

	/** notify 큐 → 저장은 비동기이므로 최대 10초 기다린다 */
	private void awaitNotification(long userId, String type, long reservationId) throws InterruptedException {
		for (int i = 0; i < 100; i++) {
			long n = jdbc.sql("""
					SELECT count(*) FROM app.notifications
					WHERE user_id = :u AND type = :t AND payload->>'reservationId' = :r
					""").param("u", userId).param("t", type).param("r", String.valueOf(reservationId))
					.query(Long.class).single();
			if (n > 0) {
				return;
			}
			Thread.sleep(100);
		}
		throw new AssertionError("notification " + type + " for user " + userId + " not stored");
	}
}
