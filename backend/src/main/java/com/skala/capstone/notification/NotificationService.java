package com.skala.capstone.notification;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.messaging.MessagePublisher;
import com.skala.capstone.common.messaging.Queues;
import com.skala.capstone.common.security.Role;
import com.skala.capstone.common.web.AfterCommit;
import com.skala.capstone.common.web.Json;
import com.skala.capstone.common.web.PageResponse;
import com.skala.capstone.common.web.Times;

/**
 * 인앱 알림 (16 명세 5장).
 * 업무 변경(예약·상담)이 커밋되면 notify 큐로 보내고, 같은 backend 의 {@link NotifyListener} 가 받아
 * notifications 테이블에 저장한 뒤 STOMP /user/queue/notifications 로 실시간 푸시한다.
 * 큐가 죽어 있으면 바로 저장해서 알림이 사라지지 않게 한다.
 */
@Service
public class NotificationService {

	public record NotifyMessage(List<Long> userIds, String type, Map<String, Object> payload) {
	}

	public record Notification(long id, String type, JsonNode payload, OffsetDateTime readAt,
			OffsetDateTime createdAt) {
	}

	private final JdbcClient jdbc;
	private final Json json;
	private final MessagePublisher publisher;
	private final SimpMessagingTemplate stomp;

	public NotificationService(JdbcClient jdbc, Json json, MessagePublisher publisher, SimpMessagingTemplate stomp) {
		this.jdbc = jdbc;
		this.json = json;
		this.publisher = publisher;
		this.stomp = stomp;
	}

	/** 알림 요청. 현재 트랜잭션이 커밋된 뒤 notify 큐로 발행된다. */
	public void notify(List<Long> userIds, String type, Map<String, Object> payload) {
		if (userIds.isEmpty()) {
			return;
		}
		NotifyMessage message = new NotifyMessage(userIds, type, payload);
		publisher.publishAfterCommit(Queues.NOTIFY, message, () -> store(message));
	}

	/** 병원 스태프(상담사 또는 병원관리자) 전원의 id */
	public List<Long> hospitalStaff(long hospitalId, Role role) {
		return jdbc.sql("SELECT id FROM app.users WHERE hospital_id = :h AND role = :r ORDER BY id")
				.param("h", hospitalId).param("r", role.name()).query(Long.class).list();
	}

	/** notify 메시지 처리: 저장 + 실시간 푸시 */
	@Transactional
	public void store(NotifyMessage message) {
		for (Long userId : message.userIds()) {
			Notification n = jdbc.sql("""
					INSERT INTO app.notifications (user_id, type, payload) VALUES (:u, :t, CAST(:p AS jsonb))
					RETURNING id, type, payload::text AS payload, read_at, created_at
					""").param("u", userId).param("t", message.type()).param("p", json.write(message.payload()))
					.query((rs, i) -> new Notification(rs.getLong("id"), rs.getString("type"),
							json.read(rs.getString("payload")), null,
							Times.kst(rs.getObject("created_at", OffsetDateTime.class))))
					.single();
			AfterCommit.run(() -> stomp.convertAndSendToUser(String.valueOf(userId), "/queue/notifications", n));
		}
	}

	@Transactional(readOnly = true)
	public PageResponse<Notification> list(long userId, boolean unreadOnly, int page, int size) {
		String where = " WHERE user_id = :u" + (unreadOnly ? " AND read_at IS NULL" : "");
		long total = jdbc.sql("SELECT count(*) FROM app.notifications" + where).param("u", userId)
				.query(Long.class).single();
		List<Notification> items = jdbc.sql("SELECT id, type, payload::text AS payload, read_at, created_at"
				+ " FROM app.notifications" + where + " ORDER BY created_at DESC, id DESC LIMIT :l OFFSET :o")
				.param("u", userId).param("l", size).param("o", (long) page * size)
				.query((rs, i) -> new Notification(rs.getLong("id"), rs.getString("type"),
						json.read(rs.getString("payload")),
						Times.kst(rs.getObject("read_at", OffsetDateTime.class)),
						Times.kst(rs.getObject("created_at", OffsetDateTime.class))))
				.list();
		return new PageResponse<>(items, page, size, total);
	}

	@Transactional
	public void markRead(long userId, long notificationId) {
		Long owner = jdbc.sql("SELECT user_id FROM app.notifications WHERE id = :id").param("id", notificationId)
				.query(Long.class).optional().orElseThrow(() -> ApiException.notFound("notification"));
		if (owner != userId) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
		jdbc.sql("UPDATE app.notifications SET read_at = now() WHERE id = :id AND read_at IS NULL")
				.param("id", notificationId).update();
	}

	@Transactional
	public void markAllRead(long userId) {
		jdbc.sql("UPDATE app.notifications SET read_at = now() WHERE user_id = :u AND read_at IS NULL")
				.param("u", userId).update();
	}
}
