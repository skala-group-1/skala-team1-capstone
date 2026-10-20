package com.skala.capstone.common.messaging;

import java.util.List;

/**
 * RabbitMQ 큐 이름 (12 계약서 7장, 16 명세 10장). 라우팅 키 = 큐 이름, exchange 는 하나(capstone.direct).
 *
 * <pre>
 * backend → agent : ai.task.requested, ai.task.resume, chat.translate, summary.translate
 * agent → backend : ai.task.event, chat.translated, summary.translated
 * backend → backend: notify (알림 저장·푸시)
 * </pre>
 */
public final class Queues {

	public static final String EXCHANGE = "capstone.direct";

	public static final String AI_TASK_REQUESTED = "ai.task.requested";
	public static final String AI_TASK_RESUME = "ai.task.resume";
	public static final String AI_TASK_EVENT = "ai.task.event";
	public static final String AI_TASK_DLQ = "ai.task.dlq";

	public static final String CHAT_TRANSLATE = "chat.translate";
	public static final String CHAT_TRANSLATED = "chat.translated";
	public static final String CHAT_TRANSLATE_DLQ = "chat.translate.dlq";

	public static final String SUMMARY_TRANSLATE = "summary.translate";
	public static final String SUMMARY_TRANSLATED = "summary.translated";
	public static final String SUMMARY_TRANSLATE_DLQ = "summary.translate.dlq";

	public static final String NOTIFY = "notify";
	public static final String NOTIFY_DLQ = "notify.dlq";

	public static final String HEADER_TRACE_ID = "x-trace-id";
	public static final String HEADER_ATTEMPT = "x-attempt";

	/** 실패 시 5초·15초 뒤 다시 처리할 수 있도록 지연 재시도 큐를 두는 작업 큐들 */
	public static final List<String> RETRYABLE = List.of(AI_TASK_REQUESTED, AI_TASK_RESUME, CHAT_TRANSLATE,
			SUMMARY_TRANSLATE, NOTIFY);

	private Queues() {
	}

	public static String retry5s(String queue) {
		return queue + ".retry.5s";
	}

	public static String retry15s(String queue) {
		return queue + ".retry.15s";
	}

	/** 작업 큐가 최종 실패했을 때 가는 DLQ 이름 */
	public static String dlqOf(String queue) {
		return switch (queue) {
			case AI_TASK_REQUESTED, AI_TASK_RESUME -> AI_TASK_DLQ;
			case CHAT_TRANSLATE -> CHAT_TRANSLATE_DLQ;
			case SUMMARY_TRANSLATE -> SUMMARY_TRANSLATE_DLQ;
			case NOTIFY -> NOTIFY_DLQ;
			default -> null;
		};
	}
}
