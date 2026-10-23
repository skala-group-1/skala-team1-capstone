package com.skala.capstone.staff;

import java.sql.Array;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.security.AuditLogger;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.web.AfterCommit;
import com.skala.capstone.common.web.Times;
import com.skala.capstone.staff.CounselorAdminDtos.Counselor;
import com.skala.capstone.staff.CounselorAdminDtos.CounselorRoster;
import com.skala.capstone.staff.CounselorAdminDtos.CreateCounselorRequest;
import com.skala.capstone.staff.CounselorAdminDtos.UpdateCounselorRequest;

/**
 * 병원 관리자의 상담사 관리. 항상 토큰의 hospitalId 소속 상담사만 다룬다 (다른 병원 상담사는 NOT_FOUND).
 * 초대 메일 없이 관리자가 초기 비밀번호로 바로 만든다. 비활성 계정은 로그인·토큰 갱신이 막힌다 (StaffAccounts).
 */
@Service
public class CounselorAdminService {

	private static final List<String> LANGUAGE_ORDER = List.of("ko", "en", "zh", "ja");

	private static final String SELECT = """
			SELECT u.id, u.name, u.email, u.languages, u.accepting_new, u.active, u.last_login_at, u.created_at,
			       (SELECT count(*) FROM app.consultations c
			        WHERE c.counselor_id = u.id AND c.status = 'ACTIVE') AS active_consultations,
			       (SELECT count(*) FROM app.consultations c
			        WHERE c.counselor_id = u.id AND c.status = 'CLOSED' AND c.closed_at >= :monthStart) AS closed_this_month
			FROM app.users u
			WHERE u.role = 'COUNSELOR' AND u.hospital_id = :h
			""";

	private final JdbcClient jdbc;
	private final PasswordEncoder passwordEncoder;
	private final AuditLogger audit;

	public CounselorAdminService(JdbcClient jdbc, PasswordEncoder passwordEncoder, AuditLogger audit) {
		this.jdbc = jdbc;
		this.passwordEncoder = passwordEncoder;
		this.audit = audit;
	}

	/** 우리 병원 상담사 전부 (활성 먼저, 그다음 가입순) + 대기 문의 수 */
	@Transactional(readOnly = true)
	public CounselorRoster roster(CurrentUser admin) {
		List<Counselor> items = jdbc.sql(SELECT + " ORDER BY u.active DESC, u.created_at, u.id")
				.param("h", admin.hospitalId()).param("monthStart", monthStart())
				.query(CounselorAdminService::map).list();
		int waiting = jdbc.sql("SELECT count(*) FROM app.consultations WHERE hospital_id = :h AND status = 'WAITING'")
				.param("h", admin.hospitalId()).query(Integer.class).single();
		return new CounselorRoster(items, waiting);
	}

	@Transactional
	public Counselor create(CurrentUser admin, CreateCounselorRequest req) {
		String email = req.email().trim();
		boolean taken = jdbc.sql("SELECT EXISTS (SELECT 1 FROM app.users WHERE lower(email) = lower(:e))")
				.param("e", email).query(Boolean.class).single();
		if (taken) {
			throw new ApiException(ErrorCode.EMAIL_DUPLICATED);
		}
		long id = jdbc.sql("""
				INSERT INTO app.users (email, password_hash, name, locale, role, hospital_id, languages, created_at)
				VALUES (:e, :p, :n, 'ko', 'COUNSELOR', :h, string_to_array(:l, ','), now())
				RETURNING id
				""")
				.param("e", email).param("p", passwordEncoder.encode(req.password())).param("n", req.name().trim())
				.param("h", admin.hospitalId()).param("l", languages(req.languages()))
				.query(Long.class).single();
		AfterCommit.run(() -> audit.log(admin, "COUNSELOR_CREATED", "user:" + id, Map.of()));
		return get(admin, id);
	}

	@Transactional
	public Counselor update(CurrentUser admin, long id, UpdateCounselorRequest req) {
		requireOwn(admin, id);
		jdbc.sql("""
				UPDATE app.users SET
				    name = COALESCE(CAST(:n AS varchar), name),
				    languages = COALESCE(string_to_array(CAST(:l AS text), ','), languages),
				    accepting_new = COALESCE(CAST(:a AS boolean), accepting_new)
				WHERE id = :id
				""")
				.param("n", req.name() == null ? null : req.name().trim())
				.param("l", req.languages() == null ? null : languages(req.languages()))
				.param("a", req.acceptingNew()).param("id", id).update();
		AfterCommit.run(() -> audit.log(admin, "COUNSELOR_UPDATED", "user:" + id, Map.of()));
		return get(admin, id);
	}

	/** 진행 중 상담이 있으면 409. 비활성으로 바꾸면 refresh 토큰을 모두 폐기한다 (access 토큰은 만료까지 최대 30분 유효). */
	@Transactional
	public Counselor deactivate(CurrentUser admin, long id) {
		boolean active = requireOwn(admin, id);
		if (active) {
			int ongoing = jdbc.sql("SELECT count(*) FROM app.consultations WHERE counselor_id = :id AND status = 'ACTIVE'")
					.param("id", id).query(Integer.class).single();
			if (ongoing > 0) {
				throw new ApiException(ErrorCode.INVALID_STATE_TRANSITION,
						Map.of("from", "ACTIVE", "to", "INACTIVE", "activeConsultations", ongoing));
			}
			jdbc.sql("UPDATE app.users SET active = false WHERE id = :id").param("id", id).update();
			jdbc.sql("UPDATE app.refresh_tokens SET revoked_at = now() WHERE user_id = :id AND revoked_at IS NULL")
					.param("id", id).update();
			AfterCommit.run(() -> audit.log(admin, "COUNSELOR_DEACTIVATED", "user:" + id, Map.of()));
		}
		return get(admin, id);
	}

	@Transactional
	public Counselor activate(CurrentUser admin, long id) {
		if (!requireOwn(admin, id)) {
			jdbc.sql("UPDATE app.users SET active = true WHERE id = :id").param("id", id).update();
			AfterCommit.run(() -> audit.log(admin, "COUNSELOR_ACTIVATED", "user:" + id, Map.of()));
		}
		return get(admin, id);
	}

	/** 우리 병원 상담사인지 확인하고 행을 잠근다. 반환값 = 현재 active */
	private boolean requireOwn(CurrentUser admin, long id) {
		return jdbc.sql("SELECT active FROM app.users WHERE id = :id AND role = 'COUNSELOR' AND hospital_id = :h FOR UPDATE")
				.param("id", id).param("h", admin.hospitalId())
				.query(Boolean.class).optional().orElseThrow(() -> ApiException.notFound("counselor"));
	}

	private Counselor get(CurrentUser admin, long id) {
		return jdbc.sql(SELECT + " AND u.id = :id")
				.param("h", admin.hospitalId()).param("monthStart", monthStart()).param("id", id)
				.query(CounselorAdminService::map).single();
	}

	/** 중복 제거 + ko·en·zh·ja 순서로 저장 */
	private static String languages(List<String> requested) {
		return String.join(",", LANGUAGE_ORDER.stream().filter(requested::contains).toList());
	}

	private static OffsetDateTime monthStart() {
		return Times.startOfDay(OffsetDateTime.now(Times.SEOUL).toLocalDate().withDayOfMonth(1));
	}

	private static Counselor map(ResultSet rs, int row) throws SQLException {
		Array langs = rs.getArray("languages");
		return new Counselor(
				rs.getLong("id"),
				rs.getString("name"),
				rs.getString("email"),
				langs == null ? List.of() : List.of((String[]) langs.getArray()),
				rs.getBoolean("accepting_new"),
				rs.getBoolean("active"),
				rs.getInt("active_consultations"),
				rs.getInt("closed_this_month"),
				Times.kst(rs.getObject("last_login_at", OffsetDateTime.class)),
				Times.kst(rs.getObject("created_at", OffsetDateTime.class)));
	}
}
