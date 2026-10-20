package com.skala.capstone.consultation;

import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.common.messaging.Queues;
import com.skala.capstone.consultation.ConsultationDtos.ChatTranslated;
import com.skala.capstone.consultation.ConsultationDtos.SummaryTranslated;

/**
 * agent 번역 워커 결과 소비.
 * - chat.translated: 번역문 저장 + 화면 갱신
 * - chat.translate.dlq: 번역이 재시도 끝에 실패 → "번역 실패, 재시도" 표시 (데모 C)
 * - summary.translated: 상담사용 한국어 요약 카드 저장
 */
@Component
public class TranslationListener {

	private final ChatService chat;
	private final ConsultationService consultations;

	public TranslationListener(ChatService chat, ConsultationService consultations) {
		this.chat = chat;
		this.consultations = consultations;
	}

	@RabbitListener(queues = Queues.CHAT_TRANSLATED)
	public void onTranslated(ChatTranslated msg) {
		chat.onTranslated(msg);
	}

	@RabbitListener(queues = Queues.CHAT_TRANSLATE_DLQ)
	public void onTranslateDeadLetter(JsonNode body) {
		if (body != null && body.hasNonNull("messageId")) {
			chat.markFailed(body.get("messageId").asLong());
		}
	}

	@RabbitListener(queues = Queues.SUMMARY_TRANSLATED)
	public void onSummaryTranslated(SummaryTranslated msg) {
		consultations.onSummaryTranslated(msg);
	}
}
