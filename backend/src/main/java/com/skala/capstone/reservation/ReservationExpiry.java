package com.skala.capstone.reservation;

import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.skala.capstone.common.security.AuditLogger;
import com.skala.capstone.common.web.AfterCommit;
import com.skala.capstone.notification.NotificationService;

/**
 * 30분 홀드 만료 처리 (12 계약서 4장: PENDING → EXPIRED, 슬롯 반환).
 * 1분마다 홀드가 지난 PENDING 예약을 찾아 한 건씩 별도 트랜잭션으로 만료시킨다.
 */
@Component
public class ReservationExpiry {

	private static final Logger log = LoggerFactory.getLogger(ReservationExpiry.class);

	private final JdbcClient jdbc;
	private final NotificationService notifications;
	private final AuditLogger audit;

	public ReservationExpiry(JdbcClient jdbc, NotificationService notifications, AuditLogger audit) {
		this.jdbc = jdbc;
		this.notifications = notifications;
		this.audit = audit;
	}

	@Scheduled(fixedDelayString = "PT1M", initialDelayString = "PT10S")
	public void expireDue() {
		List<Long> due = jdbc.sql("""
				SELECT id FROM app.reservations WHERE status = 'PENDING' AND hold_expires_at < now() ORDER BY id
				""").query(Long.class).list();
		for (Long id : due) {
			try {
				expireOne(id);
			} catch (RuntimeException e) {
				log.warn("failed to expire reservation {}", id, e);
			}
		}
	}

	/** 홀드가 지난 PENDING 예약 1건을 만료. 이미 다른 상태면 아무것도 안 함. */
	@Transactional(propagation = Propagation.REQUIRES_NEW)
	public void expireOne(long reservationId) {
		var row = jdbc.sql("""
				UPDATE app.reservations SET status = 'EXPIRED', hold_expires_at = NULL, updated_at = now()
				WHERE id = :id AND status = 'PENDING' AND hold_expires_at < now()
				RETURNING user_id, slot_id
				""").param("id", reservationId)
				.query((rs, i) -> new long[] { rs.getLong("user_id"), rs.getLong("slot_id") }).optional();
		if (row.isEmpty()) {
			return;
		}
		jdbc.sql("""
				UPDATE app.slots SET status = 'AVAILABLE', hold_expires_at = NULL, version = version + 1
				WHERE id = :id AND status = 'HELD'
				""").param("id", row.get()[1]).update();
		notifications.notify(List.of(row.get()[0]), "RESERVATION_EXPIRED", Map.of("reservationId", reservationId));
		AfterCommit.run(() -> audit.log(null, null, "RESERVATION_EXPIRED", "reservation:" + reservationId, Map.of()));
	}
}
