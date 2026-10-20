package com.skala.capstone.ai;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import com.fasterxml.jackson.annotation.JsonUnwrapped;
import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.reservation.ReservationDtos.HospitalRef;

/** AI 대화·작업 DTO (12 계약서 5장 AI, 16 명세 6장) 와 큐 메시지 (12 계약서 7장). */
public final class AiDtos {

	private AiDtos() {
	}

	// ------------------------------------------------------------------ REST

	public record CreateConversationRequest(Long hospitalId, UUID parentConversationId) {
	}

	public record ConversationMessage(String role, String text, JsonNode sources, JsonNode cards,
			OffsetDateTime createdAt) {
	}

	/** messages 는 단건 조회 때만 채운다 (목록·생성 응답은 null) */
	public record Conversation(UUID id, String mode, HospitalRef hospital, UUID parentConversationId,
			Long consultationId, JsonNode conditions, OffsetDateTime createdAt, List<ConversationMessage> messages) {
	}

	public record CreateTaskRequest(
			@NotNull UUID conversationId,
			@Size(max = 2000) String message,
			Map<String, Object> action) {
	}

	public record ApprovalRequest(@NotNull Boolean approved, Map<String, Object> editedArgs,
			@Size(max = 500) String reason) {
	}

	public record AiTask(UUID id, UUID conversationId, String status, String message, String answer,
			JsonNode sources, JsonNode pendingAction, JsonNode error, OffsetDateTime createdAt,
			OffsetDateTime finishedAt) {
	}

	/** POST /api/ai/tasks 202 응답 (「공통 계약서」 CreateTaskResponse) */
	public record CreateTaskResponse(UUID taskId) {
	}

	/** 운영자 화면용: AiTask 필드에 userId 를 더한 평평한 객체 (13-2 OpsAiTask) */
	public record AiTaskWithUser(long userId, @JsonUnwrapped AiTask task) {
	}

	// ------------------------------------------------------------------ RabbitMQ

	public record TaskUser(long id, String role, String locale) {
	}

	/** agent 가 새 thread 의 초기 state 를 만들 때 쓰는 대화 정보 (16 명세 6-2, 계약서 추가 필드) */
	public record TaskConversation(String mode, Long hospitalId, UUID parentConversationId) {
	}

	public record TaskRequested(UUID taskId, UUID conversationId, TaskUser user, String message,
			Map<String, Object> action, OffsetDateTime requestedAt, TaskConversation conversation) {
	}

	public record TaskResume(UUID taskId, UUID conversationId, TaskUser user, boolean approved,
			Map<String, Object> editedArgs, String reason) {
	}

	/** agent → backend 진행 이벤트. seq 는 작업별로 1부터 증가 (승인 후 재개해도 이어서 증가) */
	public record TaskEvent(UUID taskId, int seq, String event, JsonNode data, OffsetDateTime at) {
	}
}
