package com.skala.capstone.consultation;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.messaging.MessagePublisher;
import com.skala.capstone.common.messaging.Queues;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.security.Role;
import com.skala.capstone.common.web.AfterCommit;
import com.skala.capstone.common.web.Json;
import com.skala.capstone.common.web.Times;
import com.skala.capstone.consultation.ConsultationDtos.ChatMessage;
import com.skala.capstone.consultation.ConsultationDtos.ChatTranslate;
import com.skala.capstone.consultation.ConsultationDtos.ChatTranslated;
import com.skala.capstone.consultation.ConsultationDtos.StompEvent;

/**
 * 통역 채팅 (02 문서 3-3, 16 명세 7장).
 * 1) 메시지 저장(번역 대기) → 양쪽 화면에 원문 즉시 표시(MESSAGE_CREATED)
 * 2) chat.translate 로 agent 번역 워커에 위임 (backend 는 LLM 을 부르지 않는다)
 * 3) chat.translated 수신 → 번역문·플래그 저장 → MESSAGE_TRANSLATED (실패면 TRANSLATION_FAILED + 재시도 버튼)
 * 언어: 고객 → 한국어(상담사), 상담사 → 고객 언어. 같은 언어면 번역 없이 바로 완료.
 */
@Service
public class ChatService {

	private static final Logger log = LoggerFactory.getLogger(ChatService.class);

	public record Sent(ChatMessage message, boolean created) {
	}

	private final JdbcClient jdbc;
	private final ConsultationAccess access;
	private final MessagePublisher publisher;
	private final SimpMessagingTemplate stomp;
	private final Json json;

	public ChatService(JdbcClient jdbc, ConsultationAccess access, MessagePublisher publisher,
			SimpMessagingTemplate stomp, Json json) {
		this.jdbc = jdbc;
		this.access = access;
		this.publisher = publisher;
		this.stomp = stomp;
		this.json = json;
	}

	/** 메시지 전송 (STOMP SEND 와 REST 공용). 같은 clientMsgId 재전송은 기존 메시지를 돌려준다. */
	@Transactional
	public Sent send(CurrentUser user, long consultationId, String text, UUID clientMsgId) {
		var party = access.require(user, consultationId);
		if (!access.canSend(user, party)) {
			boolean statusAllows = "ACTIVE".equals(party.status())
					|| (user.role() == Role.CUSTOMER && "WAITING".equals(party.status()));
			// 상태는 맞는데 못 보내면 = 배정되지 않은 상담사 → 403, 상태가 아니면(대기·종료) → 409
			throw statusAllows ? new ApiException(ErrorCode.ACCESS_DENIED)
					: new ApiException(ErrorCode.INVALID_STATE_TRANSITION, Map.of("from", party.status(), "to", "MESSAGE"));
		}
		String body = text == null ? "" : text.trim();
		if (body.isEmpty() || body.length() > 2000) {
			throw new ApiException(ErrorCode.VALIDATION_FAILED,
					Map.of("fields", List.of(Map.of("field", "text", "reason", "1~2000 characters"))));
		}
		if (clientMsgId == null) {
			throw new ApiException(ErrorCode.VALIDATION_FAILED,
					Map.of("fields", List.of(Map.of("field", "clientMsgId", "reason", "required (UUID)"))));
		}
		Optional<ChatMessage> existing = find("consultation_id = :c AND client_msg_id = :k",
				Map.of("c", consultationId, "k", clientMsgId));
		if (existing.isPresent()) {
			return new Sent(existing.get(), false);
		}
		boolean fromCustomer = user.role() == Role.CUSTOMER;
		String customerLocale = party.customerLocale() != null ? party.customerLocale() : "en";
		String from = fromCustomer ? customerLocale : "ko";
		String to = fromCustomer ? "ko" : customerLocale;
		boolean sameLanguage = from.equals(to);

		long id = jdbc.sql("""
				INSERT INTO app.chat_messages (consultation_id, sender_id, sender_role, original_text, original_lang,
				    translated_text, translated_lang, translation_status, flags, client_msg_id)
				VALUES (:c, :u, :role, :text, :from, :tt, :to, :st, '[]'::jsonb, :k)
				RETURNING id
				""").param("c", consultationId).param("u", user.id()).param("role", fromCustomer ? "CUSTOMER" : "COUNSELOR")
				.param("text", body).param("from", from).param("tt", sameLanguage ? body : null).param("to", to)
				.param("st", sameLanguage ? "DONE" : "PENDING").param("k", clientMsgId).query(Long.class).single();
		ChatMessage saved = require(id);
		push(consultationId, "MESSAGE_CREATED", saved);
		if (!sameLanguage) {
			requestTranslation(saved);
		}
		return new Sent(saved, true);
	}

	@Transactional(readOnly = true)
	public List<ChatMessage> history(CurrentUser user, long consultationId, Long afterId, int size) {
		access.require(user, consultationId);
		return jdbc.sql(select() + " WHERE consultation_id = :c AND id > :after ORDER BY id LIMIT :size")
				.param("c", consultationId).param("after", afterId == null ? 0L : afterId).param("size", size)
				.query((rs, i) -> row(rs)).list();
	}

	/** 번역 실패 메시지 재시도: FAILED → PENDING + chat.translate 재발행 */
	@Transactional
	public ChatMessage retryTranslation(CurrentUser user, long consultationId, long messageId) {
		access.require(user, consultationId);
		ChatMessage m = find("id = :id AND consultation_id = :c", Map.of("id", messageId, "c", consultationId))
				.orElseThrow(() -> ApiException.notFound("message"));
		if (!"FAILED".equals(m.translationStatus())) {
			throw new ApiException(ErrorCode.INVALID_STATE_TRANSITION,
					Map.of("from", m.translationStatus(), "to", "PENDING"));
		}
		jdbc.sql("UPDATE app.chat_messages SET translation_status = 'PENDING' WHERE id = :id").param("id", messageId)
				.update();
		ChatMessage pending = require(messageId);
		requestTranslation(pending);
		return pending;
	}

	/** chat.translated 처리. 이미 번역 완료된 메시지면 무시(중복 수신). */
	@Transactional
	public void onTranslated(ChatTranslated msg) {
		if (msg.messageId() == null) {
			return;
		}
		Optional<ChatMessage> current = find("id = :id", Map.of("id", msg.messageId()));
		if (current.isEmpty() || "DONE".equals(current.get().translationStatus())) {
			return;
		}
		if (msg.ok() && msg.translatedText() != null) {
			jdbc.sql("""
					UPDATE app.chat_messages SET translated_text = :t, flags = CAST(:f AS jsonb), translation_status = 'DONE'
					WHERE id = :id
					""").param("t", msg.translatedText())
					.param("f", json.write(msg.flags() == null ? List.of() : msg.flags())).param("id", msg.messageId())
					.update();
			ChatMessage done = require(msg.messageId());
			push(done.consultationId(), "MESSAGE_TRANSLATED", done);
		} else {
			markFailed(msg.messageId());
		}
	}

	/** chat.translate.dlq: 번역 워커가 재시도 끝에 포기 → 실패 표시 */
	@Transactional
	public void markFailed(long messageId) {
		int n = jdbc.sql("""
				UPDATE app.chat_messages SET translation_status = 'FAILED' WHERE id = :id AND translation_status = 'PENDING'
				""").param("id", messageId).update();
		if (n > 0) {
			ChatMessage failed = require(messageId);
			push(failed.consultationId(), "TRANSLATION_FAILED", failed);
		}
	}

	private void requestTranslation(ChatMessage m) {
		publisher.publishAfterCommit(Queues.CHAT_TRANSLATE,
				new ChatTranslate(m.id(), m.consultationId(), m.originalText(), m.originalLang(), m.translatedLang()),
				() -> {
					log.warn("translation request not sent for message {}", m.id());
					markFailedNow(m.id());
				});
	}

	/** 큐 발행 실패 시(커밋 이후) 바로 실패 처리 */
	private void markFailedNow(long messageId) {
		int n = jdbc.sql("""
				UPDATE app.chat_messages SET translation_status = 'FAILED' WHERE id = :id AND translation_status = 'PENDING'
				""").param("id", messageId).update();
		if (n > 0) {
			ChatMessage failed = require(messageId);
			stomp.convertAndSend("/topic/consultations/" + failed.consultationId(),
					new StompEvent("TRANSLATION_FAILED", failed));
		}
	}

	private void push(long consultationId, String type, ChatMessage m) {
		AfterCommit.run(() -> stomp.convertAndSend("/topic/consultations/" + consultationId, new StompEvent(type, m)));
	}

	private ChatMessage require(long id) {
		return find("id = :id", Map.of("id", id)).orElseThrow(() -> ApiException.notFound("message"));
	}

	private Optional<ChatMessage> find(String where, Map<String, Object> params) {
		return jdbc.sql(select() + " WHERE " + where).params(params).query((rs, i) -> row(rs)).optional();
	}

	private static String select() {
		return "SELECT *, flags::text AS flags_json FROM app.chat_messages";
	}

	private ChatMessage row(ResultSet rs) throws SQLException {
		return new ChatMessage(rs.getLong("id"), rs.getLong("consultation_id"), rs.getString("sender_role"),
				(Long) rs.getObject("sender_id"), rs.getString("original_text"), rs.getString("original_lang"),
				rs.getString("translated_text"), rs.getString("translated_lang"), rs.getString("translation_status"),
				flags(json.read(rs.getString("flags_json"))), rs.getObject("client_msg_id", UUID.class),
				Times.kst(rs.getObject("created_at", OffsetDateTime.class)));
	}

	/**
	 * flags 는 계약상 배열(NUMBER_MISMATCH, MEDICAL_QUESTION).
	 * mock 데이터의 객체형({"medical_content": true, ...})은 의미가 같은 플래그로 바꿔 준다.
	 */
	static List<String> flags(JsonNode node) {
		List<String> out = new ArrayList<>();
		if (node == null) {
			return out;
		}
		if (node.isArray()) {
			node.forEach(n -> out.add(n.asText()));
		} else if (node.isObject()) {
			if (node.path("medical_content").asBoolean(false) || node.path("medical_question").asBoolean(false)) {
				out.add("MEDICAL_QUESTION");
			}
			if (node.path("number_mismatch").asBoolean(false)) {
				out.add("NUMBER_MISMATCH");
			}
		}
		return out;
	}
}
