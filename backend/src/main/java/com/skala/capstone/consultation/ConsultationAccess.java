package com.skala.capstone.consultation;

import java.util.Objects;
import java.util.Optional;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.security.Role;

/**
 * 상담방 접근 권한 (11 문서 3장): 그 상담의 고객 본인, 또는 같은 병원 상담사만.
 * REST·STOMP SUBSCRIBE·SEND 가 모두 이 규칙을 쓴다.
 */
@Component
public class ConsultationAccess {

	/** 권한 판단에 필요한 상담 정보 */
	public record Party(long consultationId, long customerId, long hospitalId, Long counselorId, String status,
			String customerLocale) {
	}

	private final JdbcClient jdbc;

	public ConsultationAccess(JdbcClient jdbc) {
		this.jdbc = jdbc;
	}

	public Optional<Party> find(long consultationId) {
		return jdbc.sql("""
				SELECT id, user_id, hospital_id, counselor_id, status, customer_locale
				FROM app.consultations WHERE id = :id
				""").param("id", consultationId).query((rs, i) -> new Party(rs.getLong("id"), rs.getLong("user_id"),
				rs.getLong("hospital_id"), (Long) rs.getObject("counselor_id"), rs.getString("status"),
				rs.getString("customer_locale"))).optional();
	}

	public boolean canAccess(CurrentUser user, Party p) {
		return switch (user.role()) {
			case CUSTOMER -> p.customerId() == user.id();
			case COUNSELOR -> Objects.equals(user.hospitalId(), p.hospitalId());
			default -> false;
		};
	}

	/** 없으면 404, 당사자가 아니면 403 (감사 로그는 오류 처리기가 남김) */
	public Party require(CurrentUser user, long consultationId) {
		Party p = find(consultationId).orElseThrow(() -> ApiException.notFound("consultation"));
		if (!canAccess(user, p)) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
		return p;
	}

	/** 메시지 전송 가능 여부: 고객은 WAITING·ACTIVE, 상담사는 ACTIVE 이고 배정된 본인 */
	public boolean canSend(CurrentUser user, Party p) {
		if (user.role() == Role.CUSTOMER) {
			return p.customerId() == user.id() && ("WAITING".equals(p.status()) || "ACTIVE".equals(p.status()));
		}
		return user.role() == Role.COUNSELOR && Objects.equals(user.hospitalId(), p.hospitalId())
				&& "ACTIVE".equals(p.status()) && Objects.equals(p.counselorId(), user.id());
	}
}
