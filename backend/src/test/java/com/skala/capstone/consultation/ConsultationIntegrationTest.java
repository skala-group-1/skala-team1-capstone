package com.skala.capstone.consultation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.lang.reflect.Type;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.messaging.converter.SimpleMessageConverter;
import org.springframework.messaging.simp.stomp.StompFrameHandler;
import org.springframework.messaging.simp.stomp.StompHeaders;
import org.springframework.messaging.simp.stomp.StompSession;
import org.springframework.messaging.simp.stomp.StompSessionHandlerAdapter;
import org.springframework.web.socket.WebSocketHttpHeaders;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.messaging.WebSocketStompClient;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.IntegrationTest;
import com.skala.capstone.common.messaging.Queues;

/**
 * 상담사 연결·통역 채팅 (16 명세 7장, 데모 시나리오 C, 11 문서 STOMP 권한).
 * 병원 2(상담사 counselor.h2 = 9번)와 고객 customer.en1(1번)을 쓴다.
 */
class ConsultationIntegrationTest extends IntegrationTest {

	@Test
	void fullConsultationFlowWithTranslationOverStomp() throws Exception {
		String customer = accessToken("customer.en1@demo.local");
		String counselor = accessToken("counselor.h2@demo.local");
		String conversationId = body(mvc.perform(post("/api/ai/conversations").header(HttpHeaders.AUTHORIZATION, customer)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("hospitalId", 2))))
				.andReturn()).get("id").asText();
		Map<String, Object> card = Map.of("procedure", "Jaw Botox", "questions", List.of("How long does it last?"));

		// 동의 없으면 거부
		internalConsultation(conversationId, card, false).andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("CONSENT_REQUIRED"));
		JsonNode c = body(internalConsultation(conversationId, card, true).andExpect(status().isCreated()).andReturn());
		long id = c.get("id").asLong();
		assertThat(c.get("status").asText()).isEqualTo("WAITING");
		assertThat(c.at("/customer/name").asText()).isEqualTo("E** C**");
		// 같은 요청 재전송 → 같은 상담 (200)
		assertThat(body(internalConsultation(conversationId, card, true).andExpect(status().isOk()).andReturn())
				.get("id").asLong()).isEqualTo(id);
		assertThat(jdbc.sql("SELECT mode FROM app.conversations WHERE id = :id").param("id", UUID.fromString(conversationId))
				.query(String.class).single()).isEqualTo("HUMAN");

		// 요약 카드 한국어 번역 요청 → 가짜 번역 워커 응답 → 상담사는 한국어본을 본다
		JsonNode summaryReq = receiveFrom(Queues.SUMMARY_TRANSLATE, b -> b.path("consultationId").asLong() == id);
		assertThat(summaryReq.get("to").asText()).isEqualTo("ko");
		rabbit.convertAndSend(Queues.EXCHANGE, Queues.SUMMARY_TRANSLATED,
				Map.of("consultationId", id, "ok", true, "summaryCardKo", Map.of("procedure", "사각턱 보톡스")));
		await(() -> jdbc.sql("SELECT summary_card_ko IS NOT NULL FROM app.consultations WHERE id = :id").param("id", id)
				.query(Boolean.class).single(), "summary_card_ko");
		mvc.perform(get("/api/consultations/{id}", id).header(HttpHeaders.AUTHORIZATION, counselor))
				.andExpect(jsonPath("$.summaryCard.procedure").value("사각턱 보톡스"));
		mvc.perform(get("/api/consultations/{id}", id).header(HttpHeaders.AUTHORIZATION, customer))
				.andExpect(jsonPath("$.summaryCard.procedure").value("Jaw Botox"));

		// 다른 병원 상담사는 접근 불가
		mvc.perform(get("/api/consultations/{id}", id).header(HttpHeaders.AUTHORIZATION, accessToken("counselor.h3@demo.local")))
				.andExpect(status().isForbidden());

		// 상담사 문의함 → 수락
		mvc.perform(get("/api/counselor/consultations").param("status", "WAITING").header(HttpHeaders.AUTHORIZATION, counselor))
				.andExpect(jsonPath("$[?(@.id == " + id + ")]").exists());
		mvc.perform(post("/api/counselor/consultations/{id}/accept", id).header(HttpHeaders.AUTHORIZATION, counselor))
				.andExpect(status().isOk()).andExpect(jsonPath("$.status").value("ACTIVE"));
		// 고객 알림에 대화창 id 가 있어야 FE 가 /chat/{conversationId} 로 이동시킬 수 있다
		await(() -> jdbc.sql("""
				SELECT count(*) FROM app.notifications
				WHERE type = 'CONSULTATION_ACCEPTED' AND payload->>'consultationId' = :id
				  AND payload->>'conversationId' = :c
				""").param("id", String.valueOf(id)).param("c", conversationId).query(Long.class).single() > 0, "accept notification");

		// 상담사가 STOMP 로 상담방 구독
		BlockingQueue<JsonNode> received = new LinkedBlockingQueue<>();
		StompSession session = connect(counselor);
		subscribe(session, "/topic/consultations/" + id, received);
		Thread.sleep(300);

		// 고객 메시지(영어) → 원문 즉시 표시 → 번역 요청(en→ko)
		UUID clientMsgId = UUID.randomUUID();
		JsonNode sent = body(mvc.perform(post("/api/consultations/{id}/messages", id).header(HttpHeaders.AUTHORIZATION, customer)
				.contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("text", "Is it 150,000 won?", "clientMsgId", clientMsgId))))
				.andExpect(status().isCreated()).andReturn());
		assertThat(sent.get("translationStatus").asText()).isEqualTo("PENDING");
		JsonNode created = received.poll(5, TimeUnit.SECONDS);
		assertThat(created).isNotNull();
		assertThat(created.get("type").asText()).isEqualTo("MESSAGE_CREATED");

		JsonNode translateReq = receiveFrom(Queues.CHAT_TRANSLATE, b -> b.path("messageId").asLong() == sent.get("id").asLong());
		assertThat(translateReq.get("from").asText()).isEqualTo("en");
		assertThat(translateReq.get("to").asText()).isEqualTo("ko");
		rabbit.convertAndSend(Queues.EXCHANGE, Queues.CHAT_TRANSLATED, Map.of("messageId", sent.get("id").asLong(),
				"ok", true, "translatedText", "15만 원인가요?", "flags", List.of("NUMBER_MISMATCH")));
		JsonNode translated = received.poll(5, TimeUnit.SECONDS);
		assertThat(translated.get("type").asText()).isEqualTo("MESSAGE_TRANSLATED");
		assertThat(translated.at("/data/translatedText").asText()).isEqualTo("15만 원인가요?");
		assertThat(translated.at("/data/flags/0").asText()).isEqualTo("NUMBER_MISMATCH");

		// 같은 clientMsgId 재전송 → 중복 저장 없음 (200)
		mvc.perform(post("/api/consultations/{id}/messages", id).header(HttpHeaders.AUTHORIZATION, customer)
				.contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("text", "Is it 150,000 won?", "clientMsgId", clientMsgId))))
				.andExpect(status().isOk()).andExpect(jsonPath("$.id").value(sent.get("id").asLong()));

		// 상담사 메시지 → DLQ 로 번역 실패 → 재시도
		long counselorMsg = body(mvc.perform(post("/api/consultations/{id}/messages", id)
				.header(HttpHeaders.AUTHORIZATION, counselor).contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("text", "네, 15만 원입니다.", "clientMsgId", UUID.randomUUID()))))
				.andExpect(status().isCreated()).andReturn()).get("id").asLong();
		receiveFrom(Queues.CHAT_TRANSLATE, b -> b.path("messageId").asLong() == counselorMsg);
		rabbit.convertAndSend(Queues.EXCHANGE, Queues.CHAT_TRANSLATE_DLQ, Map.of("messageId", counselorMsg));
		await(() -> "FAILED".equals(jdbc.sql("SELECT translation_status FROM app.chat_messages WHERE id = :id")
				.param("id", counselorMsg).query(String.class).single()), "translation FAILED");
		mvc.perform(post("/api/consultations/{id}/messages/{m}/retry-translation", id, counselorMsg)
				.header(HttpHeaders.AUTHORIZATION, counselor))
				.andExpect(status().isAccepted()).andExpect(jsonPath("$.translationStatus").value("PENDING"));
		JsonNode retry = receiveFrom(Queues.CHAT_TRANSLATE, b -> b.path("messageId").asLong() == counselorMsg);
		assertThat(retry.get("to").asText()).isEqualTo("en");

		mvc.perform(get("/api/consultations/{id}/messages", id).header(HttpHeaders.AUTHORIZATION, customer))
				.andExpect(jsonPath("$.length()").value(2));

		// 종료 → 대화창은 AI 로 복귀, 이후 메시지는 409
		mvc.perform(post("/api/counselor/consultations/{id}/close", id).header(HttpHeaders.AUTHORIZATION, counselor))
				.andExpect(status().isOk()).andExpect(jsonPath("$.status").value("CLOSED"));
		assertThat(jdbc.sql("SELECT mode FROM app.conversations WHERE id = :id").param("id", UUID.fromString(conversationId))
				.query(String.class).single()).isEqualTo("HOSPITAL");
		mvc.perform(post("/api/consultations/{id}/messages", id).header(HttpHeaders.AUTHORIZATION, customer)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("text", "bye", "clientMsgId", UUID.randomUUID()))))
				.andExpect(status().isConflict());
		session.disconnect();
	}

	/** 고객이 직접 종료: WAITING(요청 취소)·ACTIVE → CLOSED, 대화창은 AI 로 복귀. 병원 3(counselor.h3)을 쓴다 */
	@Test
	void customerClosesWaitingAndActiveConsultation() throws Exception {
		String customer = accessToken("customer.en1@demo.local");
		String counselor = accessToken("counselor.h3@demo.local");
		String conversationId = body(mvc.perform(post("/api/ai/conversations").header(HttpHeaders.AUTHORIZATION, customer)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("hospitalId", 3))))
				.andReturn()).get("id").asText();
		Map<String, Object> card = Map.of("procedure", "Jaw Botox", "questions", List.of("How long does it last?"));

		// WAITING → 고객 종료(요청 취소)
		long waiting = body(internalConsultation(3, conversationId, card, true).andExpect(status().isCreated()).andReturn())
				.get("id").asLong();
		// 다른 고객·상담사는 고객 종료 API 를 쓸 수 없다
		mvc.perform(post("/api/consultations/{id}/close", waiting)
				.header(HttpHeaders.AUTHORIZATION, accessToken("customer.en2@demo.local")))
				.andExpect(status().isForbidden());
		mvc.perform(post("/api/consultations/{id}/close", waiting).header(HttpHeaders.AUTHORIZATION, counselor))
				.andExpect(status().isForbidden());
		mvc.perform(post("/api/consultations/{id}/close", waiting).header(HttpHeaders.AUTHORIZATION, customer))
				.andExpect(status().isOk()).andExpect(jsonPath("$.status").value("CLOSED"));
		assertThat(jdbc.sql("SELECT mode FROM app.conversations WHERE id = :id").param("id", UUID.fromString(conversationId))
				.query(String.class).single()).isEqualTo("HOSPITAL");
		// 이미 종료된 상담 → 409
		mvc.perform(post("/api/consultations/{id}/close", waiting).header(HttpHeaders.AUTHORIZATION, customer))
				.andExpect(status().isConflict()).andExpect(jsonPath("$.code").value("INVALID_STATE_TRANSITION"));

		// 다시 요청 → 상담사 수락(ACTIVE) → 고객 종료 → 상담사도 더 보낼 수 없다
		long active = body(internalConsultation(3, conversationId, card, true).andExpect(status().isCreated()).andReturn())
				.get("id").asLong();
		assertThat(active).isNotEqualTo(waiting);
		mvc.perform(post("/api/counselor/consultations/{id}/accept", active).header(HttpHeaders.AUTHORIZATION, counselor))
				.andExpect(status().isOk());
		mvc.perform(post("/api/consultations/{id}/close", active).header(HttpHeaders.AUTHORIZATION, customer))
				.andExpect(status().isOk()).andExpect(jsonPath("$.status").value("CLOSED"));
		assertThat(jdbc.sql("SELECT mode FROM app.conversations WHERE id = :id").param("id", UUID.fromString(conversationId))
				.query(String.class).single()).isEqualTo("HOSPITAL");
		mvc.perform(post("/api/consultations/{id}/messages", active).header(HttpHeaders.AUTHORIZATION, counselor)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("text", "안녕하세요", "clientMsgId", UUID.randomUUID()))))
				.andExpect(status().isConflict());
	}

	/** 11 문서 7장: 병원 2 상담사가 병원 1 상담방을 구독 → 거부(연결 끊김) + 감사 로그 */
	@Test
	void stompSubscribeToOtherHospitalRoomIsDenied() throws Exception {
		long before = jdbc.sql("SELECT count(*) FROM app.audit_logs WHERE target LIKE 'STOMP SUBSCRIBE%'")
				.query(Long.class).single();
		StompSession session = connect(accessToken("counselor.h2@demo.local"));
		subscribe(session, "/topic/consultations/1", new LinkedBlockingQueue<>()); // 상담 1 = 병원 1
		await(() -> !session.isConnected(), "session closed by server");
		assertThat(jdbc.sql("SELECT count(*) FROM app.audit_logs WHERE target LIKE 'STOMP SUBSCRIBE%'")
				.query(Long.class).single()).isGreaterThan(before);
	}

	@Test
	void stompConnectWithoutTokenFails() {
		WebSocketStompClient client = new WebSocketStompClient(new StandardWebSocketClient());
		var future = client.connectAsync("ws://localhost:" + port + "/ws", new WebSocketHttpHeaders(), new StompHeaders(),
				new StompSessionHandlerAdapter() {
				});
		boolean connected;
		try {
			StompSession s = future.get(3, TimeUnit.SECONDS);
			Thread.sleep(500);
			connected = s.isConnected();
		} catch (Exception e) {
			connected = false;
		}
		assertThat(connected).isFalse();
	}

	// ------------------------------------------------------------------ helpers

	private org.springframework.test.web.servlet.ResultActions internalConsultation(String conversationId,
			Map<String, Object> card, boolean consent) throws Exception {
		return internalConsultation(2, conversationId, card, consent);
	}

	private org.springframework.test.web.servlet.ResultActions internalConsultation(long hospitalId, String conversationId,
			Map<String, Object> card, boolean consent) throws Exception {
		return mvc.perform(post("/internal/consultations")
				.header("X-Service-Token", "test-service-token").header("X-Acting-User-Id", "1")
				.contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("hospitalId", hospitalId, "conversationId", conversationId, "summaryCard", card,
						"consent", consent))));
	}

	private StompSession connect(String bearer) throws Exception {
		WebSocketStompClient client = new WebSocketStompClient(new StandardWebSocketClient());
		client.setMessageConverter(new SimpleMessageConverter()); // 프레임 본문(JSON 바이트)을 그대로 받는다
		StompHeaders headers = new StompHeaders();
		headers.add("Authorization", bearer);
		return client.connectAsync("ws://localhost:" + port + "/ws", new WebSocketHttpHeaders(), headers,
				new StompSessionHandlerAdapter() {
				}).get(5, TimeUnit.SECONDS);
	}

	private void subscribe(StompSession session, String destination, BlockingQueue<JsonNode> sink) {
		session.subscribe(destination, new StompFrameHandler() {
			@Override
			public Type getPayloadType(StompHeaders headers) {
				return byte[].class;
			}

			@Override
			public void handleFrame(StompHeaders headers, Object payload) {
				try {
					sink.add(objectMapper.readTree((byte[]) payload));
				} catch (Exception e) {
					throw new IllegalStateException(e);
				}
			}
		});
	}
}
