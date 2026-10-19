package com.skala.capstone.consultation;

import java.security.Principal;
import java.util.Map;

import org.springframework.messaging.handler.annotation.DestinationVariable;
import org.springframework.messaging.handler.annotation.MessageExceptionHandler;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.stereotype.Controller;

import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.consultation.ConsultationDtos.SendMessageRequest;
import com.skala.capstone.consultation.ConsultationDtos.StompError;

/**
 * STOMP SEND /app/consultations/{id}/send {text, clientMsgId}.
 * 처리 결과는 /topic/consultations/{id} 로 모두에게, 오류는 보낸 사람의 /user/queue/errors 로만 간다.
 */
@Controller
public class ChatStompController {

	private final ChatService chat;
	private final SimpMessagingTemplate stomp;

	public ChatStompController(ChatService chat, SimpMessagingTemplate stomp) {
		this.chat = chat;
		this.stomp = stomp;
	}

	@MessageMapping("/consultations/{id}/send")
	public void send(@DestinationVariable long id, @Payload SendMessageRequest req, Principal principal) {
		try {
			chat.send(user(principal), id, req.text(), req.clientMsgId());
		} catch (ApiException e) {
			stomp.convertAndSendToUser(principal.getName(), "/queue/errors",
					new StompError(e.code().name(), e.code().name(),
							req.clientMsgId() == null ? null : req.clientMsgId().toString()));
		}
	}

	@MessageExceptionHandler
	public void onError(Exception e, Principal principal) {
		if (principal != null) {
			stomp.convertAndSendToUser(principal.getName(), "/queue/errors",
					new StompError(ErrorCode.VALIDATION_FAILED.name(), String.valueOf(e.getMessage()), null));
		}
	}

	private static CurrentUser user(Principal principal) {
		if (principal instanceof UsernamePasswordAuthenticationToken t && t.getPrincipal() instanceof CurrentUser u) {
			return u;
		}
		throw new ApiException(ErrorCode.UNAUTHENTICATED, Map.of());
	}
}
