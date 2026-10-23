package com.skala.capstone.staff;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

/** 계정 상태 (V105): 비활성 계정 로그인 차단, 마지막 로그인 기록. 로그인·토큰 갱신에서 부른다. */
@Component
public class StaffAccounts {

	private final JdbcClient jdbc;

	public StaffAccounts(JdbcClient jdbc) {
		this.jdbc = jdbc;
	}

	public boolean isActive(long userId) {
		return jdbc.sql("SELECT active FROM app.users WHERE id = :id").param("id", userId)
				.query(Boolean.class).optional().orElse(false);
	}

	public void recordLogin(long userId) {
		jdbc.sql("UPDATE app.users SET last_login_at = now() WHERE id = :id").param("id", userId).update();
	}
}
