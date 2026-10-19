package com.skala.capstone.common.security;

import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.skala.capstone.common.web.TraceIdFilter;

/**
 * app.audit_logs 기록. 실패한 요청(로그인 실패, 403)도 남아야 하므로 별도 트랜잭션으로 커밋한다.
 * detail 에 개인정보를 넣을 때는 호출 측에서 마스킹한다.
 */
@Component
@Transactional(propagation = Propagation.REQUIRES_NEW)
public class AuditLogger {

	private static final Logger log = LoggerFactory.getLogger(AuditLogger.class);

	private final JdbcClient jdbc;
	private final ObjectMapper objectMapper;

	public AuditLogger(JdbcClient jdbc, ObjectMapper objectMapper) {
		this.jdbc = jdbc;
		this.objectMapper = objectMapper;
	}

	public void log(Long actorId, Role actorRole, String action, String target, Map<String, Object> detail) {
		try {
			jdbc.sql("""
					INSERT INTO app.audit_logs (trace_id, actor_id, actor_role, action, target, detail)
					VALUES (:traceId, :actorId, :actorRole, :action, :target, CAST(:detail AS jsonb))
					""")
					.param("traceId", TraceIdFilter.current())
					.param("actorId", actorId)
					.param("actorRole", actorRole == null ? null : actorRole.name())
					.param("action", action)
					.param("target", target)
					.param("detail", objectMapper.writeValueAsString(detail == null ? Map.of() : detail))
					.update();
		} catch (JsonProcessingException | RuntimeException e) {
			// 감사 로그 실패가 본 요청을 깨뜨리지 않게 한다
			log.warn("audit log failed: action={} target={}", action, target, e);
		}
	}

	public void log(CurrentUser actor, String action, String target, Map<String, Object> detail) {
		log(actor == null ? null : actor.id(), actor == null ? null : actor.role(), action, target, detail);
	}

	/** "customer.en1@demo.local" → "cu***@demo.local" */
	public static String maskEmail(String email) {
		if (email == null) {
			return null;
		}
		int at = email.indexOf('@');
		if (at <= 0) {
			return "***";
		}
		return email.substring(0, Math.min(2, at)) + "***" + email.substring(at);
	}
}
