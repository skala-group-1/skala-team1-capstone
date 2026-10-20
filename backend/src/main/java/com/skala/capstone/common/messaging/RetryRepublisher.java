package com.skala.capstone.common.messaging;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;

/**
 * 소비자 공통 재시도 규약 (16 명세 10장): 처리 실패 시
 * 1회차 → {q}.retry.5s, 2회차 → {q}.retry.15s (TTL 후 원래 큐로 복귀), 3번째 실패 → {q}.dlq.
 */
@Component
public class RetryRepublisher {

	private static final Logger log = LoggerFactory.getLogger(RetryRepublisher.class);

	private final RabbitTemplate rabbit;

	public RetryRepublisher(RabbitTemplate rabbit) {
		this.rabbit = rabbit;
	}

	public void retryOrDeadLetter(String queue, Message message, Exception cause) {
		Object raw = message.getMessageProperties().getHeader(Queues.HEADER_ATTEMPT);
		int attempt = raw instanceof Number n ? n.intValue() : 0;
		String target = switch (attempt) {
			case 0 -> Queues.retry5s(queue);
			case 1 -> Queues.retry15s(queue);
			default -> Queues.dlqOf(queue);
		};
		message.getMessageProperties().setHeader(Queues.HEADER_ATTEMPT, attempt + 1);
		log.warn("message on {} failed (attempt {}), moving to {}: {}", queue, attempt, target, cause.toString());
		rabbit.send(Queues.EXCHANGE, target, message);
	}
}
