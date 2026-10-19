package com.skala.capstone.notification;

import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Component;

import com.skala.capstone.common.messaging.Queues;
import com.skala.capstone.common.messaging.RetryRepublisher;
import com.skala.capstone.notification.NotificationService.NotifyMessage;

/** notify 큐 소비 → 알림 저장·푸시. 실패하면 5초·15초 뒤 재시도, 그래도 실패하면 notify.dlq. */
@Component
public class NotifyListener {

	private final NotificationService notifications;
	private final RetryRepublisher retry;

	public NotifyListener(NotificationService notifications, RetryRepublisher retry) {
		this.notifications = notifications;
		this.retry = retry;
	}

	@RabbitListener(queues = Queues.NOTIFY)
	public void onNotify(@Payload NotifyMessage body, Message raw) {
		try {
			notifications.store(body);
		} catch (RuntimeException e) {
			retry.retryOrDeadLetter(Queues.NOTIFY, raw, e);
		}
	}
}
