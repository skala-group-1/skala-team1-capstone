package com.skala.capstone.common.messaging;

import java.util.ArrayList;
import java.util.List;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Declarables;
import org.springframework.amqp.core.DirectExchange;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * RabbitMQ 구성: exchange·큐·DLQ·지연 재시도 큐를 backend 기동 시 선언한다 (16 명세 10장).
 * infra 의 definitions.json 이 같은 큐를 선언하려면 인자가 완전히 같아야 한다.
 */
@Configuration
public class RabbitConfig {

	@Bean
	MessageConverter rabbitMessageConverter(ObjectMapper objectMapper) {
		// 큐 메시지 본문은 JSON(camelCase). 받는 쪽 타입 힌트(__TypeId__)에 의존하지 않는다
		Jackson2JsonMessageConverter converter = new Jackson2JsonMessageConverter(objectMapper);
		converter.setAlwaysConvertToInferredType(true);
		return converter;
	}

	@Bean
	Declarables rabbitTopology() {
		DirectExchange exchange = new DirectExchange(Queues.EXCHANGE, true, false);
		List<org.springframework.amqp.core.Declarable> all = new ArrayList<>();
		all.add(exchange);

		// 실패하면 DLQ 로 보내는 작업 큐
		for (String q : Queues.RETRYABLE) {
			addBound(all, exchange, QueueBuilder.durable(q)
					.deadLetterExchange(Queues.EXCHANGE)
					.deadLetterRoutingKey(Queues.dlqOf(q))
					.build());
			// 지연 재시도 큐: TTL 이 지나면 원래 큐로 돌아간다
			addBound(all, exchange, QueueBuilder.durable(Queues.retry5s(q)).ttl(5_000)
					.deadLetterExchange(Queues.EXCHANGE).deadLetterRoutingKey(q).build());
			addBound(all, exchange, QueueBuilder.durable(Queues.retry15s(q)).ttl(15_000)
					.deadLetterExchange(Queues.EXCHANGE).deadLetterRoutingKey(q).build());
		}
		// agent → backend 결과 큐와 DLQ (인자 없음)
		for (String q : List.of(Queues.AI_TASK_EVENT, Queues.CHAT_TRANSLATED, Queues.SUMMARY_TRANSLATED,
				Queues.AI_TASK_DLQ, Queues.CHAT_TRANSLATE_DLQ, Queues.SUMMARY_TRANSLATE_DLQ, Queues.NOTIFY_DLQ)) {
			addBound(all, exchange, QueueBuilder.durable(q).build());
		}
		return new Declarables(all);
	}

	private static void addBound(List<org.springframework.amqp.core.Declarable> all, DirectExchange exchange,
			Queue queue) {
		Binding binding = BindingBuilder.bind(queue).to(exchange).with(queue.getName());
		all.add(queue);
		all.add(binding);
	}
}
