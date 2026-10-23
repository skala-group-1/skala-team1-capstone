package com.skala.capstone.staff;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.skala.capstone.catalog.ReviewTranslations;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.security.AuditLogger;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.web.AfterCommit;
import com.skala.capstone.common.web.Times;
import com.skala.capstone.staff.ReviewAdminDtos.AdminReview;
import com.skala.capstone.staff.ReviewAdminDtos.AdminReviewPage;
import com.skala.capstone.staff.ReviewAdminDtos.Hidden;
import com.skala.capstone.staff.ReviewAdminDtos.HideRequest;
import com.skala.capstone.staff.ReviewAdminDtos.Reply;
import com.skala.capstone.staff.ReviewAdminDtos.ReviewSummary;

/**
 * 병원 관리자 리뷰 관리: 답글(리뷰당 1개, 고객 언어로 번역) + 숨김(운영팀 검토 없이 바로, 삭제 아님).
 * 항상 토큰의 hospitalId 리뷰만 다룬다 (다른 병원 리뷰는 NOT_FOUND). 취소된 예약으로 쓴 리뷰는 고객 화면과 같이 뺀다.
 */
@Service
public class ReviewAdminService {

	/** 목록 탭: 숨기지 않은 리뷰 전체 / 답글 없음 / 낮은 평점(2점 이하) / 숨긴 리뷰 */
	public enum Filter { ALL, UNREPLIED, LOW, HIDDEN }

	public enum Sort { LATEST, RATING_LOW, RATING_HIGH }

	private static final String FROM = """
			FROM app.reviews r
			LEFT JOIN app.review_replies rp ON rp.review_id = r.id
			""";

	private static final String WHERE = """
			WHERE r.hospital_id = :h
			  AND NOT EXISTS (SELECT 1 FROM app.reservations x WHERE x.id = r.reservation_id AND x.status = 'CANCELLED')
			""";

	private static final String BASE = FROM + WHERE;

	private static final String SELECT = """
			SELECT r.*, t.content AS translated_content,
			       CASE WHEN :loc = 'en' THEN p.name_en ELSE p.name_ko END AS procedure_name,
			       rp.content AS reply_content, rp.lang AS reply_lang,
			       rp.created_at AS reply_created_at, rp.updated_at AS reply_updated_at
			""";

	private static final String JOINS = """
			LEFT JOIN app.procedures p ON p.code = r.procedure_code
			LEFT JOIN app.review_translations t ON t.review_id = r.id AND t.lang = :loc
			""";

	private final JdbcClient jdbc;
	private final ReviewTranslations translations;
	private final AuditLogger audit;

	public ReviewAdminService(JdbcClient jdbc, ReviewTranslations translations, AuditLogger audit) {
		this.jdbc = jdbc;
		this.translations = translations;
		this.audit = audit;
	}

	@Transactional(readOnly = true)
	public AdminReviewPage list(CurrentUser admin, Filter filter, String lang, Sort sort, int page, int size,
			String locale) {
		String where = switch (filter) {
			case ALL -> " AND r.hidden_at IS NULL";
			case UNREPLIED -> " AND r.hidden_at IS NULL AND rp.review_id IS NULL";
			case LOW -> " AND r.hidden_at IS NULL AND r.rating <= 2";
			case HIDDEN -> " AND r.hidden_at IS NOT NULL";
		} + (lang != null ? " AND r.lang = :lang" : "");
		String order = switch (sort) {
			case LATEST -> " ORDER BY r.created_at DESC, r.id DESC";
			case RATING_LOW -> " ORDER BY r.rating, r.created_at DESC, r.id DESC";
			case RATING_HIGH -> " ORDER BY r.rating DESC, r.created_at DESC, r.id DESC";
		};
		Map<String, Object> params = new HashMap<>();
		params.put("h", admin.hospitalId());
		if (lang != null) {
			params.put("lang", lang);
		}
		long total = jdbc.sql("SELECT count(*) " + BASE + where).params(params).query(Long.class).single();
		params.put("loc", locale);
		params.put("limit", size);
		params.put("offset", (long) page * size);
		List<Row> rows = jdbc.sql(SELECT + FROM + JOINS + WHERE + where + order
				+ " LIMIT :limit OFFSET :offset").params(params).query(ReviewAdminService::row).list();
		return new AdminReviewPage(withTranslations(rows), page, size, total, summary(admin));
	}

	/** 답글 등록·수정 (리뷰당 1개). 고치면 이전 번역을 지우고 다시 번역을 요청한다 */
	@Transactional
	public AdminReview reply(CurrentUser admin, long id, String content, String locale) {
		requireOwn(admin, id);
		String text = content.trim();
		jdbc.sql("""
				INSERT INTO app.review_replies (review_id, author_id, lang, content)
				VALUES (:id, :me, :lang, :c)
				ON CONFLICT (review_id) DO UPDATE
				SET author_id = EXCLUDED.author_id, lang = EXCLUDED.lang, content = EXCLUDED.content, updated_at = now()
				""").param("id", id).param("me", admin.id()).param("lang", locale).param("c", text).update();
		jdbc.sql("DELETE FROM app.review_reply_translations WHERE review_id = :id").param("id", id).update();
		translations.requestReplyAfterCommit(id, text, locale);
		AfterCommit.run(() -> audit.log(admin, "REVIEW_REPLIED", "review:" + id, Map.of()));
		return get(admin, id, locale);
	}

	@Transactional
	public void deleteReply(CurrentUser admin, long id) {
		requireOwn(admin, id);
		int n = jdbc.sql("DELETE FROM app.review_replies WHERE review_id = :id").param("id", id).update();
		if (n > 0) {
			AfterCommit.run(() -> audit.log(admin, "REVIEW_REPLY_DELETED", "review:" + id, Map.of()));
		}
	}

	/** 숨김 (운영팀 검토 없이 바로). 이미 숨겼으면 사유만 바꾼다 */
	@Transactional
	public AdminReview hide(CurrentUser admin, long id, HideRequest req, String locale) {
		requireOwn(admin, id);
		String detail = req.detail() == null || req.detail().isBlank() ? null : req.detail().trim();
		if ("OTHER".equals(req.reason()) && detail == null) {
			throw new ApiException(ErrorCode.VALIDATION_FAILED,
					Map.of("fields", List.of(Map.of("field", "detail", "reason", "required when reason is OTHER"))));
		}
		jdbc.sql("""
				UPDATE app.reviews SET hidden_at = COALESCE(hidden_at, now()), hidden_by = :me,
				    hidden_reason = :reason, hidden_detail = :detail
				WHERE id = :id
				""").param("me", admin.id()).param("reason", req.reason()).param("detail", detail).param("id", id)
				.update();
		AfterCommit.run(() -> audit.log(admin, "REVIEW_HIDDEN", "review:" + id, Map.of("reason", req.reason())));
		return get(admin, id, locale);
	}

	@Transactional
	public AdminReview unhide(CurrentUser admin, long id, String locale) {
		requireOwn(admin, id);
		jdbc.sql("""
				UPDATE app.reviews SET hidden_at = NULL, hidden_by = NULL, hidden_reason = NULL, hidden_detail = NULL
				WHERE id = :id
				""").param("id", id).update();
		AfterCommit.run(() -> audit.log(admin, "REVIEW_UNHIDDEN", "review:" + id, Map.of()));
		return get(admin, id, locale);
	}

	private ReviewSummary summary(CurrentUser admin) {
		return jdbc.sql("SELECT count(*) FILTER (WHERE r.hidden_at IS NULL) AS total,"
				+ " round(avg(r.rating) FILTER (WHERE r.hidden_at IS NULL)::numeric, 2) AS avg_rating,"
				+ " count(*) FILTER (WHERE r.hidden_at IS NULL AND r.rating = 1) AS r1,"
				+ " count(*) FILTER (WHERE r.hidden_at IS NULL AND r.rating = 2) AS r2,"
				+ " count(*) FILTER (WHERE r.hidden_at IS NULL AND r.rating = 3) AS r3,"
				+ " count(*) FILTER (WHERE r.hidden_at IS NULL AND r.rating = 4) AS r4,"
				+ " count(*) FILTER (WHERE r.hidden_at IS NULL AND r.rating = 5) AS r5,"
				+ " count(*) FILTER (WHERE r.hidden_at IS NULL AND rp.review_id IS NULL) AS unreplied,"
				+ " count(*) FILTER (WHERE r.hidden_at IS NULL AND r.rating <= 2) AS low,"
				+ " count(*) FILTER (WHERE r.hidden_at IS NOT NULL) AS hidden,"
				+ " count(*) FILTER (WHERE r.hidden_at IS NULL AND r.created_at >= :monthStart) AS this_month "
				+ BASE)
				.param("h", admin.hospitalId()).param("monthStart", monthStart())
				.query((rs, i) -> {
					Map<String, Long> byRating = new LinkedHashMap<>();
					for (int s = 5; s >= 1; s--) {
						byRating.put(String.valueOf(s), rs.getLong("r" + s));
					}
					Number avg = (Number) rs.getObject("avg_rating");
					return new ReviewSummary(rs.getLong("total"), avg == null ? null : avg.doubleValue(), byRating,
							rs.getLong("unreplied"), rs.getLong("low"), rs.getLong("hidden"), rs.getLong("this_month"));
				}).single();
	}

	private AdminReview get(CurrentUser admin, long id, String locale) {
		List<Row> rows = jdbc.sql(SELECT + FROM + JOINS + WHERE + " AND r.id = :id")
				.param("h", admin.hospitalId()).param("loc", locale).param("id", id)
				.query(ReviewAdminService::row).list();
		return withTranslations(rows).get(0);
	}

	/** 우리 병원 리뷰인지 확인하고 행을 잠근다 */
	private void requireOwn(CurrentUser admin, long id) {
		boolean own = jdbc.sql("SELECT 1 FROM app.reviews WHERE id = :id AND hospital_id = :h FOR UPDATE")
				.param("id", id).param("h", admin.hospitalId()).query(Integer.class).optional().isPresent();
		if (!own) {
			throw ApiException.notFound("review");
		}
	}

	/** 답글 번역은 페이지에 나온 리뷰 것만 한 번에 가져온다 */
	private List<AdminReview> withTranslations(List<Row> rows) {
		List<Long> ids = rows.stream().filter(r -> r.replyContent() != null).map(Row::id).toList();
		Map<Long, Map<String, String>> byReview = new HashMap<>();
		if (!ids.isEmpty()) {
			jdbc.sql("SELECT review_id, lang, content FROM app.review_reply_translations WHERE review_id IN (:ids)"
					+ " ORDER BY lang").param("ids", ids).query((ResultSet rs) -> {
						byReview.computeIfAbsent(rs.getLong("review_id"), k -> new LinkedHashMap<>())
								.put(rs.getString("lang"), rs.getString("content"));
					});
		}
		return rows.stream().map(r -> new AdminReview(r.id(), r.procedureCode(), r.procedureName(), r.rating(),
				r.ageGroup(), r.gender(), r.nationality(), r.lang(), r.content(), r.translatedContent(), r.createdAt(),
				r.replyContent() == null ? null
						: new Reply(r.replyContent(), r.replyLang(), byReview.getOrDefault(r.id(), Map.of()),
								r.replyCreatedAt(), r.replyUpdatedAt()),
				r.hiddenAt() == null ? null : new Hidden(r.hiddenReason(), r.hiddenDetail(), r.hiddenAt()))).toList();
	}

	private record Row(long id, String procedureCode, String procedureName, int rating, String ageGroup, String gender,
			String nationality, String lang, String content, String translatedContent, OffsetDateTime createdAt,
			String replyContent, String replyLang, OffsetDateTime replyCreatedAt, OffsetDateTime replyUpdatedAt,
			OffsetDateTime hiddenAt, String hiddenReason, String hiddenDetail) {
	}

	private static Row row(ResultSet rs, int i) throws SQLException {
		return new Row(rs.getLong("id"), rs.getString("procedure_code"), rs.getString("procedure_name"),
				rs.getInt("rating"), rs.getString("age_group"), rs.getString("gender"),
				rs.getString("reviewer_nationality"), rs.getString("lang"), rs.getString("content"),
				rs.getString("translated_content"), Times.kst(rs.getObject("created_at", OffsetDateTime.class)),
				rs.getString("reply_content"), rs.getString("reply_lang"),
				Times.kst(rs.getObject("reply_created_at", OffsetDateTime.class)),
				Times.kst(rs.getObject("reply_updated_at", OffsetDateTime.class)),
				Times.kst(rs.getObject("hidden_at", OffsetDateTime.class)), rs.getString("hidden_reason"),
				rs.getString("hidden_detail"));
	}

	private static OffsetDateTime monthStart() {
		return Times.startOfDay(OffsetDateTime.now(Times.SEOUL).toLocalDate().withDayOfMonth(1));
	}
}
