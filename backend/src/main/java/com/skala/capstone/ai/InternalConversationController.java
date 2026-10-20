package com.skala.capstone.ai;

import jakarta.servlet.http.HttpServletRequest;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.ai.AiDtos.Conversation;
import com.skala.capstone.ai.AiDtos.CreateConversationRequest;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.web.RequestLocale;

import io.swagger.v3.oas.annotations.tags.Tag;

/** 에이전트의 select_hospital 노드가 병원 대화창을 열 때 사용 (03 문서 1장, D-20) */
@Tag(name = "Internal (business-mcp)")
@RestController
@RequestMapping("/internal/conversations")
public class InternalConversationController {

	private final ConversationService conversations;

	public InternalConversationController(ConversationService conversations) {
		this.conversations = conversations;
	}

	@PostMapping
	public ResponseEntity<Conversation> create(@AuthenticationPrincipal CurrentUser user,
			@RequestBody CreateConversationRequest req, @RequestParam(required = false) String locale,
			HttpServletRequest request) {
		var r = conversations.create(user, req.hospitalId(), req.parentConversationId(),
				RequestLocale.resolve(locale, request));
		return ResponseEntity.status(r.created() ? HttpStatus.CREATED : HttpStatus.OK).body(r.conversation());
	}
}
