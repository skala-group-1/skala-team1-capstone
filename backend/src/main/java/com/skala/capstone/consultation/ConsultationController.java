package com.skala.capstone.consultation;

import java.util.List;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.web.RequestLocale;
import com.skala.capstone.consultation.ConsultationDtos.ChatMessage;
import com.skala.capstone.consultation.ConsultationDtos.Consultation;
import com.skala.capstone.consultation.ConsultationDtos.SendMessageRequest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/** 상담방 (고객 본인 또는 같은 병원 상담사만). 실시간은 STOMP, 이 REST 는 기록 조회·재시도·폴백 전송용. */
@Tag(name = "Consultation")
@Validated
@RestController
@RequestMapping("/api/consultations")
public class ConsultationController {

	private final ConsultationService consultations;
	private final ChatService chat;

	public ConsultationController(ConsultationService consultations, ChatService chat) {
		this.consultations = consultations;
		this.chat = chat;
	}

	@Operation(summary = "상담 정보 + 요약 카드 (상담사는 한국어본)")
	@GetMapping("/{id}")
	public Consultation get(@AuthenticationPrincipal CurrentUser user, @PathVariable long id,
			HttpServletRequest request) {
		return consultations.get(user, id, RequestLocale.resolve(request));
	}

	@Operation(summary = "고객이 상담 종료 (WAITING·ACTIVE → CLOSED, 대화창은 AI 응답 재개)")
	@PostMapping("/{id}/close")
	public Consultation close(@AuthenticationPrincipal CurrentUser user, @PathVariable long id,
			HttpServletRequest request) {
		return consultations.closeByCustomer(user, id, RequestLocale.resolve(request));
	}

	@Operation(summary = "메시지 기록 (오래된 순, afterId 이후)")
	@GetMapping("/{id}/messages")
	public List<ChatMessage> messages(@AuthenticationPrincipal CurrentUser user, @PathVariable long id,
			@RequestParam(required = false) Long afterId,
			@RequestParam(defaultValue = "100") @Min(1) @Max(500) int size) {
		return chat.history(user, id, afterId, size);
	}

	@Operation(summary = "메시지 보내기 (STOMP 와 같은 처리, 테스트·폴백용)")
	@PostMapping("/{id}/messages")
	public ResponseEntity<ChatMessage> send(@AuthenticationPrincipal CurrentUser user, @PathVariable long id,
			@Valid @RequestBody SendMessageRequest req) {
		var sent = chat.send(user, id, req.text(), req.clientMsgId());
		return ResponseEntity.status(sent.created() ? HttpStatus.CREATED : HttpStatus.OK).body(sent.message());
	}

	@Operation(summary = "번역 실패 메시지 재시도")
	@PostMapping("/{id}/messages/{msgId}/retry-translation")
	public ResponseEntity<ChatMessage> retry(@AuthenticationPrincipal CurrentUser user, @PathVariable long id,
			@PathVariable long msgId) {
		return ResponseEntity.accepted().body(chat.retryTranslation(user, id, msgId));
	}
}
