package com.skala.capstone.reservation;

import java.sql.Array;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.Period;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;

import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.skala.capstone.catalog.CatalogDtos.Review;
import com.skala.capstone.catalog.CatalogDtos.Slot;
import com.skala.capstone.catalog.CatalogService;
import com.skala.capstone.common.config.AppProperties;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.security.AuditLogger;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.security.Role;
import com.skala.capstone.common.web.AfterCommit;
import com.skala.capstone.common.web.Masking;
import com.skala.capstone.common.web.PageResponse;
import com.skala.capstone.common.web.Times;
import com.skala.capstone.notification.NotificationService;
import com.skala.capstone.reservation.ReservationDtos.CreateReservationRequest;
import com.skala.capstone.reservation.ReservationDtos.CreateReviewRequest;
import com.skala.capstone.reservation.ReservationDtos.CustomerRef;
import com.skala.capstone.reservation.ReservationDtos.HospitalDashboard;
import com.skala.capstone.reservation.ReservationDtos.HospitalRef;
import com.skala.capstone.reservation.ReservationDtos.Reservation;

/**
 * 예약 업무 규칙 (12 계약서 4장 상태 전이, 16 명세 4장).
 *
 * <pre>
 *   요청 ──▶ PENDING ──병원 승인──▶ CONFIRMED ──고객 취소──▶ CANCELLED
 *              │  └──병원 반려──▶ REJECTED ──대안 수락──▶ (새 PENDING)
 *              │  └──30분 경과──▶ EXPIRED
 *              └──고객 취소──▶ CANCELLED
 * </pre>
 *
 * 동시성: 슬롯 선점은 "AVAILABLE 일 때만 HELD 로" 조건부 UPDATE, 승인은 슬롯 version 조건부 UPDATE.
 * 조건이 안 맞아 0건이 바뀌면 다른 요청이 먼저 처리한 것이므로 409 로 돌려준다.
 * 공개 API(/api)와 에이전트 대리 호출(/internal)이 이 서비스 하나를 같이 쓴다.
 */
@Service
public class ReservationService {

	private final JdbcClient jdbc;
	private final CatalogService catalog;
	private final NotificationService notifications;
	private final AuditLogger audit;
	private final ReservationExpiry expiry;
	private final AppProperties app;

	public ReservationService(JdbcClient jdbc, CatalogService catalog, NotificationService notifications,
			AuditLogger audit, ReservationExpiry expiry, AppProperties app) {
		this.jdbc = jdbc;
		this.catalog = catalog;
		this.notifications = notifications;
		this.audit = audit;
		this.expiry = expiry;
		this.app = app;
	}

	/** 생성 결과: created=false 면 같은 멱등키의 기존 예약을 돌려준 것 (HTTP 200) */
	public record Created(Reservation reservation, boolean created) {
	}

	/** DB 한 행 */
	record Row(long id, long userId, long hospitalId, long slotId, String procedureCode, Long priceOptionId,
			String status, String source, UUID idempotencyKey, String note, String rejectReason,
			List<Long> alternativeSlotIds, OffsetDateTime holdExpiresAt, OffsetDateTime createdAt,
			OffsetDateTime decidedAt, String customerName, String customerNationality, String customerLocale,
			Long reviewId) {
	}

	// ------------------------------------------------------------------ 생성

	@Transactional
	public Created create(CurrentUser user, String idempotencyKey, CreateReservationRequest req, String source,
			String locale) {
		UUID key = parseKey(idempotencyKey);
		Optional<Row> existing = findByKey(key);
		if (existing.isPresent()) {
			if (existing.get().userId() != user.id()) {
				throw fieldError("Idempotency-Key", "already used");
			}
			return new Created(toDto(existing.get(), locale, false), false);
		}

		catalog.requireHospital(req.hospitalId());
		SlotRow slot = slotRow(req.slotId()).filter(s -> s.hospitalId() == req.hospitalId())
				.orElseThrow(() -> ApiException.notFound("slot"));
		catalog.requireProcedure(req.procedureCode(), locale);
		Integer offered = jdbc.sql("SELECT count(*) FROM app.price_options WHERE hospital_id = :h AND procedure_code = :p")
				.param("h", req.hospitalId()).param("p", req.procedureCode()).query(Integer.class).single();
		if (offered == 0) {
			throw fieldError("procedureCode", "not offered by this hospital");
		}
		if (req.priceOptionId() != null) {
			Integer ok = jdbc.sql("""
					SELECT count(*) FROM app.price_options WHERE id = :id AND hospital_id = :h AND procedure_code = :p
					""").param("id", req.priceOptionId()).param("h", req.hospitalId()).param("p", req.procedureCode())
					.query(Integer.class).single();
			if (ok == 0) {
				throw fieldError("priceOptionId", "not an option of this hospital and procedure");
			}
		}
		if (slot.doctorSpecialties() != null && !slot.doctorSpecialties().contains(req.procedureCode())) {
			throw fieldError("slotId", "the doctor of this slot does not perform the procedure");
		}

		// 슬롯 선점: AVAILABLE 이고 미래일 때만 HELD 로 바뀐다. 동시에 두 명이 요청하면 한 명만 성공
		int held = jdbc.sql("""
				UPDATE app.slots SET status = 'HELD', hold_expires_at = :hold, version = version + 1
				WHERE id = :id AND status = 'AVAILABLE' AND start_at > now()
				""").param("id", slot.id()).param("hold", OffsetDateTime.now().plus(app.reservation().hold()))
				.update();
		if (held == 0) {
			throw slotUnavailable(req.hospitalId(), req.procedureCode(), slot, locale);
		}
		long id = jdbc.sql("""
				INSERT INTO app.reservations (user_id, hospital_id, slot_id, procedure_code, price_option_id, status,
				    source, idempotency_key, customer_note, hold_expires_at)
				SELECT :u, :h, :s, :p, :po, 'PENDING', :src, :key, :note, hold_expires_at FROM app.slots WHERE id = :s
				RETURNING id
				""").param("u", user.id()).param("h", req.hospitalId()).param("s", slot.id())
				.param("p", req.procedureCode()).param("po", req.priceOptionId()).param("src", source)
				.param("key", key).param("note", req.note()).query(Long.class).single();

		notifications.notify(notifications.hospitalStaff(req.hospitalId(), Role.HOSPITAL_ADMIN),
				"RESERVATION_REQUESTED", Map.of("reservationId", id));
		AfterCommit.run(() -> audit.log(user, "RESERVATION_CREATED", "reservation:" + id,
				Map.of("slotId", slot.id(), "source", source)));
		return new Created(toDto(requireRow(id), locale, false), true);
	}

	// ------------------------------------------------------------------ 조회

	@Transactional(readOnly = true)
	public Reservation get(CurrentUser user, long id, String locale) {
		Row row = requireRow(id);
		requireView(user, row);
		return toDto(row, locale, user.role() != Role.CUSTOMER);
	}

	@Transactional(readOnly = true)
	public List<Reservation> mine(CurrentUser user, String status, String locale) {
		return rows("r.user_id = :u" + (status != null ? " AND r.status = :st" : ""),
				params("u", user.id(), "st", status), " ORDER BY r.created_at DESC, r.id DESC", null)
				.stream().map(r -> toDto(r, locale, false)).toList();
	}

	/** 병원관리자: 자기 병원 예약만 (token.hospitalId 강제) */
	@Transactional(readOnly = true)
	public PageResponse<Reservation> forHospital(CurrentUser admin, String status, LocalDate date, int page,
			int size, String locale) {
		StringBuilder where = new StringBuilder("r.hospital_id = :h");
		Map<String, Object> p = params("h", admin.hospitalId(), "st", status);
		if (status != null) {
			where.append(" AND r.status = :st");
		}
		if (date != null) {
			where.append(" AND s.start_at >= :from AND s.start_at < :to");
			p.put("from", Times.startOfDay(date));
			p.put("to", Times.startOfDay(date.plusDays(1)));
		}
		long total = jdbc.sql("SELECT count(*) FROM app.reservations r JOIN app.slots s ON s.id = r.slot_id WHERE "
				+ where).params(p).query(Long.class).single();
		p.put("limit", size);
		p.put("offset", (long) page * size);
		List<Reservation> items = rows(where.toString(), p, " ORDER BY s.start_at, r.id", " LIMIT :limit OFFSET :offset")
				.stream().map(r -> toDto(r, locale, true)).toList();
		return new PageResponse<>(items, page, size, total);
	}

	@Transactional(readOnly = true)
	public HospitalDashboard dashboard(CurrentUser admin, String locale) {
		long h = admin.hospitalId();
		LocalDate today = LocalDate.now(Times.SEOUL);
		long todayCount = jdbc.sql("""
				SELECT count(*) FROM app.reservations r JOIN app.slots s ON s.id = r.slot_id
				WHERE r.hospital_id = :h AND r.status IN ('PENDING','CONFIRMED') AND s.start_at >= :from AND s.start_at < :to
				""").param("h", h).param("from", Times.startOfDay(today)).param("to", Times.startOfDay(today.plusDays(1)))
				.query(Long.class).single();
		long pending = jdbc.sql("SELECT count(*) FROM app.reservations WHERE hospital_id = :h AND status = 'PENDING'")
				.param("h", h).query(Long.class).single();
		long active = jdbc.sql("SELECT count(*) FROM app.consultations WHERE hospital_id = :h AND status = 'ACTIVE'")
				.param("h", h).query(Long.class).single();
		List<Reservation> recent = rows("r.hospital_id = :h AND r.status = 'PENDING'", params("h", h),
				" ORDER BY r.created_at DESC, r.id DESC", " LIMIT 5").stream().map(r -> toDto(r, locale, true)).toList();
		return new HospitalDashboard(todayCount, pending, active, recent);
	}

	// ------------------------------------------------------------------ 상태 전이

	/** 고객 취소: PENDING·CONFIRMED → CANCELLED, 슬롯 반환. 본인 예약만. */
	@Transactional
	public Reservation cancel(CurrentUser user, long id, String reason, String locale) {
		Row row = requireRow(id);
		if (user.role() != Role.CUSTOMER || row.userId() != user.id()) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
		requireStatus(row, "CANCELLED", "PENDING", "CONFIRMED");
		int n = jdbc.sql("""
				UPDATE app.reservations SET status = 'CANCELLED', cancelled_at = now(), hold_expires_at = NULL,
				    updated_at = now()
				WHERE id = :id AND status = :from
				""").param("id", id).param("from", row.status()).update();
		if (n == 0) {
			throw new ApiException(ErrorCode.CONCURRENT_UPDATE);
		}
		releaseSlot(row.slotId());
		notifications.notify(notifications.hospitalStaff(row.hospitalId(), Role.HOSPITAL_ADMIN),
				"RESERVATION_CANCELLED", Map.of("reservationId", id));
		Map<String, Object> detail = new LinkedHashMap<>();
		detail.put("from", row.status());
		detail.put("reason", reason);
		AfterCommit.run(() -> audit.log(user, "RESERVATION_CANCELLED", "reservation:" + id, detail));
		return toDto(requireRow(id), locale, false);
	}

	/** 병원관리자 승인: PENDING → CONFIRMED, 슬롯 HELD → BOOKED (version 조건). 홀드가 지났으면 만료 처리 후 409. */
	@Transactional
	public Reservation approve(CurrentUser admin, long id, String locale) {
		Row row = requireRow(id);
		requireOwnHospital(admin, row);
		requireStatus(row, "CONFIRMED", "PENDING");
		if (row.holdExpiresAt() != null && row.holdExpiresAt().isBefore(OffsetDateTime.now())) {
			expiry.expireOne(id); // 별도 트랜잭션으로 확정
			throw new ApiException(ErrorCode.INVALID_STATE_TRANSITION, Map.of("from", "EXPIRED", "to", "CONFIRMED"));
		}
		int slotVersion = jdbc.sql("SELECT version FROM app.slots WHERE id = :id").param("id", row.slotId())
				.query(Integer.class).single();
		int r = jdbc.sql("""
				UPDATE app.reservations SET status = 'CONFIRMED', decided_by = :by, decided_at = now(),
				    hold_expires_at = NULL, updated_at = now()
				WHERE id = :id AND status = 'PENDING'
				""").param("id", id).param("by", admin.id()).update();
		int s = jdbc.sql("""
				UPDATE app.slots SET status = 'BOOKED', hold_expires_at = NULL, version = version + 1
				WHERE id = :id AND status = 'HELD' AND version = :v
				""").param("id", row.slotId()).param("v", slotVersion).update();
		if (r == 0 || s == 0) {
			// 다른 요청(취소·만료·동시 승인)이 먼저 바꿨다 → 이 트랜잭션은 롤백
			throw new ApiException(ErrorCode.CONCURRENT_UPDATE);
		}
		notifications.notify(List.of(row.userId()), "RESERVATION_CONFIRMED", Map.of("reservationId", id));
		AfterCommit.run(() -> audit.log(admin, "RESERVATION_APPROVED", "reservation:" + id, Map.of()));
		return toDto(requireRow(id), locale, true);
	}

	/** 병원관리자 반려: PENDING → REJECTED, 슬롯 반환, 대안 슬롯(같은 병원 미래 AVAILABLE, 최대 3) 제시 */
	@Transactional
	public Reservation reject(CurrentUser admin, long id, String reason, List<Long> alternativeSlotIds,
			String locale) {
		Row row = requireRow(id);
		requireOwnHospital(admin, row);
		requireStatus(row, "REJECTED", "PENDING");
		List<Long> alternatives = alternativeSlotIds == null ? List.of()
				: alternativeSlotIds.stream().distinct().toList();
		if (!alternatives.isEmpty()) {
			Integer valid = jdbc.sql("""
					SELECT count(*) FROM app.slots
					WHERE id IN (:ids) AND hospital_id = :h AND status = 'AVAILABLE' AND start_at > now() AND id <> :own
					""").param("ids", alternatives).param("h", row.hospitalId()).param("own", row.slotId())
					.query(Integer.class).single();
			if (valid != alternatives.size()) {
				throw fieldError("alternativeSlotIds", "must be future AVAILABLE slots of this hospital");
			}
		}
		int n = jdbc.sql("""
				UPDATE app.reservations SET status = 'REJECTED', reject_reason = :reason,
				    alternative_slot_ids = CAST(:alts AS bigint[]), decided_by = :by, decided_at = now(),
				    hold_expires_at = NULL, updated_at = now()
				WHERE id = :id AND status = 'PENDING'
				""").param("id", id).param("reason", reason.trim()).param("alts", pgArray(alternatives))
				.param("by", admin.id()).update();
		if (n == 0) {
			throw new ApiException(ErrorCode.CONCURRENT_UPDATE);
		}
		releaseSlot(row.slotId());
		notifications.notify(List.of(row.userId()), "RESERVATION_REJECTED", Map.of("reservationId", id));
		AfterCommit.run(() -> audit.log(admin, "RESERVATION_REJECTED", "reservation:" + id,
				Map.of("alternatives", alternatives)));
		return toDto(requireRow(id), locale, true);
	}

	/** 반려된 예약의 대안 슬롯으로 새 예약(PENDING) 생성. 시술·가격옵션·메모는 원래 예약에서 복사. */
	@Transactional
	public Created acceptAlternative(CurrentUser user, long id, long slotId, String idempotencyKey, String locale) {
		Row row = requireRow(id);
		if (user.role() != Role.CUSTOMER || row.userId() != user.id()) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
		if (!"REJECTED".equals(row.status())) {
			throw new ApiException(ErrorCode.INVALID_STATE_TRANSITION, Map.of("from", row.status(), "to", "PENDING"));
		}
		if (!row.alternativeSlotIds().contains(slotId)) {
			throw fieldError("slotId", "not one of the suggested alternatives");
		}
		return create(user, idempotencyKey, new CreateReservationRequest(row.hospitalId(), slotId,
				row.procedureCode(), row.priceOptionId(), row.note()), row.source(), locale);
	}

	// ------------------------------------------------------------------ 리뷰

	/**
	 * 리뷰 작성: 본인의 CONFIRMED 예약만, 예약당 1회. 병원·시술은 예약에서, 연령대·성별·국적은 프로필에서 채운다.
	 * 동시에 두 번 요청하면 reservation_id UNIQUE 인덱스가 한 건만 남긴다.
	 */
	@Transactional
	public Review writeReview(CurrentUser user, long id, CreateReviewRequest req, String locale) {
		Row row = requireRow(id);
		if (user.role() != Role.CUSTOMER || row.userId() != user.id()) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
		if (!"CONFIRMED".equals(row.status())) {
			throw new ApiException(ErrorCode.REVIEW_NOT_ALLOWED, Map.of("status", row.status()));
		}
		if (row.reviewId() != null) {
			throw new ApiException(ErrorCode.REVIEW_ALREADY_EXISTS, Map.of("reviewId", row.reviewId()));
		}
		Review review;
		try {
			review = jdbc.sql("""
					INSERT INTO app.reviews (hospital_id, user_id, procedure_code, rating, age_group, gender,
					    reviewer_nationality, lang, content, reservation_id)
					SELECT :h, u.id, :p, :rating, :age, u.gender, u.nationality, :lang, :content, :rid
					FROM app.users u WHERE u.id = :u
					RETURNING *
					""").param("h", row.hospitalId()).param("p", row.procedureCode()).param("rating", req.rating())
					.param("age", ageGroup(user.id())).param("lang", locale).param("content", req.content().trim())
					.param("rid", id).param("u", user.id())
					.query((rs, i) -> new Review(rs.getLong("id"), rs.getString("procedure_code"), rs.getInt("rating"),
							rs.getString("age_group"), rs.getString("gender"), rs.getString("reviewer_nationality"),
							rs.getString("lang"), rs.getString("content"),
							Times.kst(rs.getObject("created_at", OffsetDateTime.class))))
					.single();
		} catch (DuplicateKeyException e) {
			throw new ApiException(ErrorCode.REVIEW_ALREADY_EXISTS);
		}
		long reviewId = review.id();
		AfterCommit.run(() -> audit.log(user, "REVIEW_CREATED", "reservation:" + id,
				Map.of("reviewId", reviewId, "rating", req.rating())));
		return review;
	}

	/** 생년월일 → '20s'~'50s' (reviews.age_group CHECK 범위 밖이거나 생일이 없으면 null) */
	private String ageGroup(long userId) {
		LocalDate birth = jdbc.sql("SELECT birth_date FROM app.users WHERE id = :id").param("id", userId)
				.query(LocalDate.class).optional().orElse(null);
		if (birth == null) {
			return null;
		}
		int age = Period.between(birth, LocalDate.now(Times.SEOUL)).getYears();
		return age >= 20 && age < 60 ? (age / 10 * 10) + "s" : null;
	}

	// ------------------------------------------------------------------ 내부 도우미

	private void releaseSlot(long slotId) {
		jdbc.sql("""
				UPDATE app.slots SET status = 'AVAILABLE', hold_expires_at = NULL, version = version + 1
				WHERE id = :id AND status IN ('HELD','BOOKED')
				""").param("id", slotId).update();
	}

	private static void requireStatus(Row row, String to, String... allowedFrom) {
		if (!Arrays.asList(allowedFrom).contains(row.status())) {
			throw new ApiException(ErrorCode.INVALID_STATE_TRANSITION, Map.of("from", row.status(), "to", to));
		}
	}

	private static void requireOwnHospital(CurrentUser admin, Row row) {
		if (admin.role() != Role.HOSPITAL_ADMIN || !Objects.equals(admin.hospitalId(), row.hospitalId())) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
	}

	/** 조회 권한: 본인 고객 / 같은 병원 관리자 / 운영자 */
	private static void requireView(CurrentUser u, Row r) {
		boolean ok = switch (u.role()) {
			case CUSTOMER -> r.userId() == u.id();
			case HOSPITAL_ADMIN -> Objects.equals(u.hospitalId(), r.hospitalId());
			case OPERATOR -> true;
			default -> false;
		};
		if (!ok) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
	}

	private ApiException slotUnavailable(long hospitalId, String procedureCode, SlotRow slot, String locale) {
		List<Slot> alternatives = catalog.nearestAvailableSlots(hospitalId, procedureCode, slot.startAt(), slot.id(),
				3, locale);
		return new ApiException(ErrorCode.SLOT_UNAVAILABLE, Map.of("alternatives", alternatives));
	}

	private static ApiException fieldError(String field, String reason) {
		return new ApiException(ErrorCode.VALIDATION_FAILED,
				Map.of("fields", List.of(Map.of("field", field, "reason", reason))));
	}

	private static UUID parseKey(String key) {
		if (key == null || key.isBlank()) {
			throw fieldError("Idempotency-Key", "required header (UUID)");
		}
		try {
			return UUID.fromString(key.trim());
		} catch (IllegalArgumentException e) {
			throw fieldError("Idempotency-Key", "must be a UUID");
		}
	}

	Row requireRow(long id) {
		return rows("r.id = :id", params("id", id), "", null).stream().findFirst()
				.orElseThrow(() -> ApiException.notFound("reservation"));
	}

	private Optional<Row> findByKey(UUID key) {
		return rows("r.idempotency_key = :key", params("key", key), "", null).stream().findFirst();
	}

	private List<Row> rows(String where, Map<String, Object> params, String orderBy, String limit) {
		String sql = """
				SELECT r.*, u.name AS customer_name, u.nationality AS customer_nationality, u.locale AS customer_locale,
				    rv.id AS review_id
				FROM app.reservations r
				JOIN app.users u ON u.id = r.user_id
				JOIN app.slots s ON s.id = r.slot_id
				LEFT JOIN app.reviews rv ON rv.reservation_id = r.id
				WHERE """ + " " + where + orderBy + (limit == null ? "" : limit);
		return jdbc.sql(sql).params(params).query((rs, i) -> row(rs)).list();
	}

	private static Row row(ResultSet rs) throws SQLException {
		return new Row(rs.getLong("id"), rs.getLong("user_id"), rs.getLong("hospital_id"), rs.getLong("slot_id"),
				rs.getString("procedure_code"), (Long) rs.getObject("price_option_id"), rs.getString("status"),
				rs.getString("source"), rs.getObject("idempotency_key", UUID.class), rs.getString("customer_note"),
				rs.getString("reject_reason"), longs(rs.getArray("alternative_slot_ids")),
				Times.kst(rs.getObject("hold_expires_at", OffsetDateTime.class)),
				Times.kst(rs.getObject("created_at", OffsetDateTime.class)),
				Times.kst(rs.getObject("decided_at", OffsetDateTime.class)),
				rs.getString("customer_name"), rs.getString("customer_nationality"), rs.getString("customer_locale"),
				(Long) rs.getObject("review_id"));
	}

	private Reservation toDto(Row r, String locale, boolean includeCustomer) {
		String hospitalName = catalog.hospitalName(r.hospitalId(), locale).orElse(null);
		return new Reservation(r.id(), r.status(), r.source(), new HospitalRef(r.hospitalId(), hospitalName),
				catalog.slot(r.slotId(), locale).orElse(null),
				catalog.procedure(r.procedureCode(), locale).orElse(null),
				r.priceOptionId() == null ? null : catalog.priceOption(r.priceOptionId(), locale).orElse(null),
				"PENDING".equals(r.status()) ? r.holdExpiresAt() : null,
				r.rejectReason(),
				"REJECTED".equals(r.status()) ? catalog.slotsByIds(r.alternativeSlotIds(), locale) : List.of(),
				includeCustomer ? new CustomerRef(r.userId(), Masking.name(r.customerName()), r.customerNationality(),
						r.customerLocale()) : null,
				r.note(), r.createdAt(), r.decidedAt(),
				"CONFIRMED".equals(r.status()) && r.reviewId() == null, r.reviewId());
	}

	record SlotRow(long id, long hospitalId, OffsetDateTime startAt, List<String> doctorSpecialties) {
	}

	private Optional<SlotRow> slotRow(long slotId) {
		return jdbc.sql("""
				SELECT s.id, s.hospital_id, s.start_at, d.specialties
				FROM app.slots s LEFT JOIN app.doctors d ON d.id = s.doctor_id WHERE s.id = :id
				""").param("id", slotId).query((rs, i) -> {
			Array a = rs.getArray("specialties");
			return new SlotRow(rs.getLong("id"), rs.getLong("hospital_id"),
					rs.getObject("start_at", OffsetDateTime.class),
					a == null ? null : List.of((String[]) a.getArray()));
		}).optional();
	}

	private static List<Long> longs(Array array) throws SQLException {
		if (array == null) {
			return List.of();
		}
		List<Long> out = new ArrayList<>();
		for (Object o : (Object[]) array.getArray()) {
			out.add(((Number) o).longValue());
		}
		return out;
	}

	/** bigint[] 리터럴 ("{1,2,3}") — JdbcClient 에 배열을 바로 넘기면 IN 목록으로 펼쳐지므로 문자열로 넘긴다 */
	private static String pgArray(List<Long> values) {
		return values.stream().map(String::valueOf).collect(java.util.stream.Collectors.joining(",", "{", "}"));
	}

	private static Map<String, Object> params(Object... kv) {
		Map<String, Object> m = new LinkedHashMap<>();
		for (int i = 0; i < kv.length; i += 2) {
			if (kv[i + 1] != null) {
				m.put((String) kv[i], kv[i + 1]);
			}
		}
		return m;
	}
}
