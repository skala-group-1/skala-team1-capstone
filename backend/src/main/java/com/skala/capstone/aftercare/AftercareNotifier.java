package com.skala.capstone.aftercare;

import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.event.EventListener;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import com.skala.capstone.ai.AiTaskDone;
import com.skala.capstone.notification.NotificationService;

/**
 * 사후관리 방의 AI 답변이 끝났는데 고객이 그 답변을 보고 있지 않으면 AFTERCARE_MESSAGE 알림을 보낸다.
 * (보고 있으면 화면에 바로 나오므로 알림을 쌓지 않는다)
 */
@Component
public class AftercareNotifier {

	private static final Logger log = LoggerFactory.getLogger(AftercareNotifier.class);
	static final String TYPE = "AFTERCARE_MESSAGE";

	private final JdbcClient jdbc;
	private final NotificationService notifications;

	public AftercareNotifier(JdbcClient jdbc, NotificationService notifications) {
		this.jdbc = jdbc;
		this.notifications = notifications;
	}

	@EventListener
	public void onDone(AiTaskDone done) {
		if (done.watched()) {
			return;
		}
		try {
			notifyIfAftercare(done);
		} catch (RuntimeException e) {
			// 알림 실패가 AI 작업 이벤트 처리(답변 저장·SSE 중계)를 막으면 안 된다
			log.warn("aftercare notification failed for task {}: {}", done.taskId(), e.getMessage());
		}
	}

	private void notifyIfAftercare(AiTaskDone done) {
		jdbc.sql("""
				SELECT t.user_id, a.conversation_id, a.reservation_id, r.procedure_code
				FROM app.ai_tasks t
				JOIN app.aftercare_rooms a ON a.conversation_id = t.conversation_id
				JOIN app.reservations r ON r.id = a.reservation_id
				WHERE t.id = :id
				""").param("id", done.taskId()).query((rs, i) -> {
			notifications.notify(List.of(rs.getLong("user_id")), TYPE, Map.of(
					"conversationId", rs.getObject("conversation_id").toString(),
					"reservationId", rs.getLong("reservation_id"),
					"procedureCode", rs.getString("procedure_code")));
			return true;
		}).list();
	}
}
