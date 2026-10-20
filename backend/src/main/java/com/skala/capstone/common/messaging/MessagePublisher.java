package com.skala.capstone.common.messaging;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.core.MessagePostProcessor;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;

import com.skala.capstone.common.web.AfterCommit;
import com.skala.capstone.common.web.TraceIdFilter;

/**
 * RabbitMQ 발행 도우미.
 * - {@link #publishAfterCommit}: DB 변경이 커밋된 뒤에만 보낸다 (롤백된 변경을 다른 서비스에 알리지 않기 위해)
 * - 헤더: x-trace-id(추적), x-attempt(재시도 횟수, 처음 0)
 */
@Component
public class MessagePublisher {

	private static final Logger log = LoggerFactory.getLogger(MessagePublisher.class);

	private final RabbitTemplate rabbit;

	public MessagePublisher(RabbitTemplate rabbit) {
		this.rabbit = rabbit;
	}

	/** 즉시 발행. 브로커가 없으면 AmqpException. */
	public void publish(String queue, Object body, String traceId, int attempt) {
		rabbit.convertAndSend(Queues.EXCHANGE, queue, body, headers(traceId, attempt));
	}

	public void publish(String queue, Object body) {
		publish(queue, body, TraceIdFilter.current(), 0);
	}

	/**
	 * 현재 트랜잭션이 커밋되면 발행. 트랜잭션 밖이면 즉시 발행.
	 * 발행 실패는 로그로 남기고 onFailure 를 실행한다 (예: 알림 직접 저장, 작업 실패 처리).
	 */
	public void publishAfterCommit(String queue, Object body, Runnable onFailure) {
		String traceId = TraceIdFilter.current();
		Runnable send = () -> {
			try {
				publish(queue, body, traceId, 0);
			} catch (AmqpException e) {
				log.warn("publish failed: queue={} traceId={} ({})", queue, traceId, e.getMessage());
				if (onFailure != null) {
					onFailure.run();
				}
			}
		};
		AfterCommit.run(send);
	}

	private static MessagePostProcessor headers(String traceId, int attempt) {
		return message -> {
			if (traceId != null) {
				message.getMessageProperties().setHeader(Queues.HEADER_TRACE_ID, traceId);
			}
			message.getMessageProperties().setHeader(Queues.HEADER_ATTEMPT, attempt);
			return message;
		};
	}
}
