package com.skala.capstone.ai;

import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.ai.AiDtos.TaskEvent;
import com.skala.capstone.common.messaging.Queues;

/**
 * agent → backend 큐 소비.
 * - ai.task.event: 진행 이벤트 → DB 반영 + SSE 중계
 * - ai.task.dlq: agent 가 재시도 끝에 포기한 작업 요청 → 작업 FAILED 처리 (화면에 재시도 버튼)
 */
@Component
public class AiEventListener {

	private static final Logger log = LoggerFactory.getLogger(AiEventListener.class);

	private final AiTaskService tasks;

	public AiEventListener(AiTaskService tasks) {
		this.tasks = tasks;
	}

	@RabbitListener(queues = Queues.AI_TASK_EVENT)
	public void onEvent(TaskEvent event) {
		tasks.handleEvent(event);
	}

	@RabbitListener(queues = Queues.AI_TASK_DLQ)
	public void onDeadLetter(JsonNode body) {
		JsonNode id = body == null ? null : body.get("taskId");
		if (id == null) {
			log.warn("ai.task.dlq message without taskId: {}", body);
			return;
		}
		try {
			tasks.fail(UUID.fromString(id.asText()), "AI_UNAVAILABLE", "AI task failed after retries");
		} catch (IllegalArgumentException e) {
			log.warn("ai.task.dlq message with invalid taskId: {}", id);
		}
	}
}
