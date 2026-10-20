package com.skala.capstone.ai;

import java.util.List;
import java.util.UUID;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import com.skala.capstone.ai.AiDtos.AiTask;
import com.skala.capstone.ai.AiDtos.ApprovalRequest;
import com.skala.capstone.ai.AiDtos.Conversation;
import com.skala.capstone.ai.AiDtos.CreateConversationRequest;
import com.skala.capstone.ai.AiDtos.CreateTaskRequest;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.web.RequestLocale;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/** AI 상담 API — 고객만 (11 문서 권한 매트릭스). 16 명세 6장. */
@Tag(name = "AI")
@PreAuthorize("hasRole('CUSTOMER')")
@RestController
@RequestMapping("/api/ai")
public class AiController {

	private final ConversationService conversations;
	private final AiTaskService tasks;

	public AiController(ConversationService conversations, AiTaskService tasks) {
		this.conversations = conversations;
		this.tasks = tasks;
	}

	@Operation(summary = "새 대화창. hospitalId 가 있으면 병원 대화(이미 있으면 기존 것 200), parent 조건 복사")
	@PostMapping("/conversations")
	public ResponseEntity<Conversation> createConversation(@AuthenticationPrincipal CurrentUser user,
			@RequestBody(required = false) CreateConversationRequest req, HttpServletRequest request) {
		var r = conversations.create(user, req == null ? null : req.hospitalId(),
				req == null ? null : req.parentConversationId(), RequestLocale.resolve(request));
		return ResponseEntity.status(r.created() ? HttpStatus.CREATED : HttpStatus.OK).body(r.conversation());
	}

	@Operation(summary = "내 대화창 목록 (최신순)")
	@GetMapping("/conversations")
	public List<Conversation> conversations(@AuthenticationPrincipal CurrentUser user, HttpServletRequest request) {
		return conversations.mine(user, RequestLocale.resolve(request));
	}

	@Operation(summary = "대화창 + 메시지 기록")
	@GetMapping("/conversations/{id}")
	public Conversation conversation(@AuthenticationPrincipal CurrentUser user, @PathVariable UUID id,
			HttpServletRequest request) {
		return conversations.get(user, id, RequestLocale.resolve(request));
	}

	@Operation(summary = "AI 작업 접수 → 202. 진행 상황은 /stream (SSE)")
	@PostMapping("/tasks")
	public ResponseEntity<AiTask> createTask(@AuthenticationPrincipal CurrentUser user,
			@Valid @RequestBody CreateTaskRequest req) {
		return ResponseEntity.accepted().body(tasks.create(user, req));
	}

	@Operation(summary = "내 작업 이력 (최근 50)")
	@GetMapping("/tasks")
	public List<AiTask> myTasks(@AuthenticationPrincipal CurrentUser user) {
		return tasks.mine(user);
	}

	@GetMapping("/tasks/{id}")
	public AiTask task(@AuthenticationPrincipal CurrentUser user, @PathVariable UUID id) {
		return tasks.get(user, id);
	}

	@Operation(summary = "작업 진행 스트림 (SSE). 재연결 시 Last-Event-ID 이후만 다시 받음")
	@GetMapping(value = "/tasks/{id}/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
	public SseEmitter stream(@AuthenticationPrincipal CurrentUser user, @PathVariable UUID id,
			@RequestHeader(value = "Last-Event-ID", required = false) String lastEventId,
			HttpServletResponse response) {
		response.setHeader("X-Accel-Buffering", "no"); // nginx 가 SSE 를 모아 보내지 않도록
		response.setHeader("Cache-Control", "no-cache");
		return tasks.stream(user, id, lastEventId);
	}

	@Operation(summary = "승인 카드 응답 (승인/수정/거절) → 같은 작업 재개, 202")
	@PostMapping("/tasks/{id}/approval")
	public ResponseEntity<AiTask> approval(@AuthenticationPrincipal CurrentUser user, @PathVariable UUID id,
			@Valid @RequestBody ApprovalRequest req) {
		return ResponseEntity.accepted()
				.body(tasks.approve(user, id, req.approved(), req.editedArgs(), req.reason()));
	}
}
