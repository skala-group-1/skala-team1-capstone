package com.skala.capstone.consultation;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.reservation.ReservationDtos.CustomerRef;
import com.skala.capstone.reservation.ReservationDtos.HospitalRef;

/** 상담·채팅 DTO (12 계약서 5장 상담·채팅, 16 명세 7장) 와 번역 큐 메시지 (12 계약서 7장). */
public final class ConsultationDtos {

	private ConsultationDtos() {
	}

	/** business-mcp request_consultation → POST /internal/consultations */
	public record CreateConsultationRequest(@NotNull Long hospitalId, @NotNull UUID conversationId,
			@NotNull Map<String, Object> summaryCard, Boolean consent) {
	}

	/** summaryCard: 고객에게는 고객 언어 원본, 상담사에게는 한국어 번역본(없으면 원본) */
	public record Consultation(long id, String status, HospitalRef hospital, CustomerRef customer, Long counselorId,
			UUID conversationId, JsonNode summaryCard, OffsetDateTime createdAt, OffsetDateTime closedAt) {
	}

	public record SendMessageRequest(@NotBlank @Size(max = 2000) String text, @NotNull UUID clientMsgId) {
	}

	public record ChatMessage(long id, long consultationId, String senderRole, Long senderId, String originalText,
			String originalLang, String translatedText, String translatedLang, String translationStatus,
			List<String> flags, UUID clientMsgId, OffsetDateTime createdAt) {
	}

	/** /topic/consultations/{id} 로 보내는 봉투: type = MESSAGE_CREATED | MESSAGE_TRANSLATED | TRANSLATION_FAILED | CONSULTATION_STATUS */
	public record StompEvent(String type, Object data) {
	}

	public record ConsultationStatus(long consultationId, String status, Long counselorId) {
	}

	/** /user/queue/errors 로 보내는 STOMP 오류 */
	public record StompError(String code, String message, String clientMsgId) {
	}

	// ------------------------------------------------------------------ RabbitMQ

	public record ChatTranslate(long messageId, long consultationId, String text, String from, String to) {
	}

	public record ChatTranslated(Long messageId, boolean ok, String translatedText, List<String> flags,
			String error) {
	}

	public record SummaryTranslate(long consultationId, Map<String, Object> summaryCard, String from, String to) {
	}

	public record SummaryTranslated(Long consultationId, boolean ok, JsonNode summaryCardKo) {
	}
}
