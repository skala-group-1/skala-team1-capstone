package com.skala.capstone.aftercare;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import com.skala.capstone.aftercare.AftercareDtos.AftercareConversation;
import com.skala.capstone.ai.AiDtos.CreateTaskRequest;
import com.skala.capstone.ai.AiTaskService;
import com.skala.capstone.catalog.CatalogDtos.Procedure;
import com.skala.capstone.catalog.CatalogService;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.security.Role;
import com.skala.capstone.common.web.Times;
import com.skala.capstone.reservation.ReservationDtos.HospitalRef;

/**
 * 시술 사후관리 대화방 (시술 전 준비 안내 포함).
 * - 승인 대기(PENDING)·확정(CONFIRMED) 예약 1건당 대화 1개 (mode AFTERCARE, selected_hospital_id = 예약 병원)
 * - 방을 열 때 그날 안내가 아직 없으면 AI 안내를 요청한다: 처음은 AFTERCARE_INTRO, 다른 날은 AFTERCARE_DAILY
 * - 정해진 시간(AftercareDailyGuides)·운영자 버튼으로도 같은 하루 한 번 기준의 안내를 보낸다
 * - 예약이 반려·취소·만료되면 방과 기록은 남기고 새 안내는 요청하지 않는다
 * - 이후 질문은 기존 /api/ai/tasks 로 보낸다
 */
@Service
public class AftercareService {

	private static final Logger log = LoggerFactory.getLogger(AftercareService.class);

	/** 방을 새로 열거나 안내를 받을 수 있는 예약 상태 */
	static final Set<String> ACTIVE = Set.of("PENDING", "CONFIRMED");

	public record Opened(AftercareConversation conversation, boolean created) {
	}

	record Row(UUID conversationId, long reservationId, String reservationStatus, String mode, String procedureCode,
			long hospitalId, OffsetDateTime startAt, OffsetDateTime createdAt) {
	}

	private record Reservation(long userId, long hospitalId, String status) {
	}

	private record GuideState(boolean anyTask, boolean busy, boolean guidedToday) {
	}

	private static final String SELECT = """
			SELECT a.conversation_id, a.reservation_id, r.status AS reservation_status, c.mode, r.procedure_code,
			       r.hospital_id, s.start_at, a.created_at
			FROM app.aftercare_rooms a
			JOIN app.conversations c ON c.id = a.conversation_id
			JOIN app.reservations r ON r.id = a.reservation_id
			JOIN app.slots s ON s.id = r.slot_id
			""";

	private final JdbcClient jdbc;
	private final TransactionTemplate tx;
	private final CatalogService catalog;
	private final AiTaskService tasks;

	public AftercareService(JdbcClient jdbc, TransactionTemplate tx, CatalogService catalog, AiTaskService tasks) {
		this.jdbc = jdbc;
		this.tx = tx;
		this.catalog = catalog;
		this.tasks = tasks;
	}

	/** 사후관리 방 열기: 있으면 그 방(200), 없으면 만든다(201). 열 때마다 그날 안내가 없으면 요청한다. */
	public Opened open(CurrentUser user, long reservationId, String locale) {
		Reservation r = jdbc.sql("SELECT user_id, hospital_id, status FROM app.reservations WHERE id = :id")
				.param("id", reservationId)
				.query((rs, i) -> new Reservation(rs.getLong("user_id"), rs.getLong("hospital_id"), rs.getString("status")))
				.optional().orElseThrow(() -> ApiException.notFound("reservation"));
		if (r.userId() != user.id()) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
		boolean created = roomOf(reservationId).isEmpty();
		if (created && !ACTIVE.contains(r.status())) {
			throw new ApiException(ErrorCode.INVALID_STATE_TRANSITION, Map.of("from", r.status(), "to", "AFTERCARE"));
		}
		Row room = ensureRoom(user.id(), r.hospitalId(), reservationId);
		requestGuideIfDue(user, room);
		return new Opened(toDto(room, locale), created);
	}

	public record DailyGuides(int checked, int requested) {
	}

	/**
	 * 정해진 시간(스케줄러)·운영자 버튼용: 시술 7일 전 ~ 30일 후인 승인 대기·확정 예약에 그날 안내를 보낸다.
	 * 방이 없으면 만들고, 오늘 이미 안내했거나 진행 중이면 건너뛴다 (방을 열 때와 같은 하루 한 번 기준).
	 * 고객이 보고 있지 않으므로 답변이 끝나면 AftercareNotifier 가 알림을 보낸다.
	 */
	public DailyGuides sendDailyGuides() {
		record Target(long reservationId, long userId, long hospitalId, String locale) {
		}
		List<Target> targets = jdbc.sql("""
				SELECT r.id, r.user_id, r.hospital_id, u.locale
				FROM app.reservations r
				JOIN app.users u ON u.id = r.user_id
				JOIN app.slots s ON s.id = r.slot_id
				WHERE r.status IN ('PENDING','CONFIRMED')
				  AND (s.start_at AT TIME ZONE 'Asia/Seoul')::date
				      BETWEEN (now() AT TIME ZONE 'Asia/Seoul')::date - 30 AND (now() AT TIME ZONE 'Asia/Seoul')::date + 7
				ORDER BY r.id
				""").query((rs, i) -> new Target(rs.getLong("id"), rs.getLong("user_id"), rs.getLong("hospital_id"),
						rs.getString("locale"))).list();
		int requested = 0;
		for (Target t : targets) {
			try {
				Row room = ensureRoom(t.userId(), t.hospitalId(), t.reservationId());
				if (requestGuideIfDue(new CurrentUser(t.userId(), Role.CUSTOMER, null, t.locale()), room)) {
					requested++;
				}
			} catch (RuntimeException e) {
				// 한 예약이 실패해도 나머지는 보낸다
				log.warn("daily aftercare guide failed for reservation {}: {}", t.reservationId(), e.getMessage());
			}
		}
		return new DailyGuides(targets.size(), requested);
	}

	/** 예약의 사후관리 방 (없으면 만든다. 동시에 만들어지면 먼저 만든 방을 쓴다) */
	private Row ensureRoom(long userId, long hospitalId, long reservationId) {
		Optional<UUID> existing = roomOf(reservationId);
		if (existing.isEmpty()) {
			try {
				existing = Optional.of(tx.execute(status -> insert(userId, hospitalId, reservationId)));
			} catch (DuplicateKeyException e) {
				existing = roomOf(reservationId);
			}
		}
		return require(existing.orElseThrow(() -> ApiException.notFound("conversation")));
	}

	/** 내 사후관리 방 목록 (최신순) */
	public List<AftercareConversation> mine(CurrentUser user, String locale) {
		return jdbc.sql(SELECT + " WHERE c.user_id = :u ORDER BY a.created_at DESC").param("u", user.id())
				.query((rs, i) -> row(rs)).list().stream().map(row -> toDto(row, locale)).toList();
	}

	private UUID insert(long userId, long hospitalId, long reservationId) {
		UUID id = UUID.randomUUID();
		jdbc.sql("""
				INSERT INTO app.conversations (id, user_id, mode, selected_hospital_id)
				VALUES (:id, :u, 'AFTERCARE', :h)
				""").param("id", id).param("u", userId).param("h", hospitalId).update();
		jdbc.sql("INSERT INTO app.aftercare_rooms (conversation_id, reservation_id) VALUES (:c, :r)")
				.param("c", id).param("r", reservationId).update();
		return id;
	}

	/**
	 * 하루 한 번(Asia/Seoul 날짜 기준) 그날 안내를 요청한다. 진행 중인 작업이 있거나, 상담사 연결 중이거나,
	 * 예약이 끝났으면 요청하지 않는다. 큐 발행에 실패하면 다음에 방을 열 때 다시 시도된다.
	 * 안내 작업을 만들었으면 true.
	 */
	private boolean requestGuideIfDue(CurrentUser user, Row room) {
		if (!ACTIVE.contains(room.reservationStatus()) || !"AFTERCARE".equals(room.mode())) {
			return false;
		}
		GuideState state = jdbc.sql("""
				SELECT EXISTS (SELECT 1 FROM app.ai_tasks WHERE conversation_id = :c) AS any_task,
				       EXISTS (SELECT 1 FROM app.ai_tasks WHERE conversation_id = :c
				               AND status IN ('QUEUED','RUNNING','WAITING_APPROVAL')) AS busy,
				       EXISTS (SELECT 1 FROM app.ai_tasks WHERE conversation_id = :c
				               AND action->>'type' IN ('AFTERCARE_INTRO','AFTERCARE_DAILY')
				               AND (created_at AT TIME ZONE 'Asia/Seoul')::date = (now() AT TIME ZONE 'Asia/Seoul')::date
				               ) AS guided_today
				""").param("c", room.conversationId())
				.query((rs, i) -> new GuideState(rs.getBoolean("any_task"), rs.getBoolean("busy"),
						rs.getBoolean("guided_today")))
				.single();
		if (state.busy() || state.guidedToday()) {
			return false;
		}
		String type = state.anyTask() ? "AFTERCARE_DAILY" : "AFTERCARE_INTRO";
		try {
			tasks.create(user, new CreateTaskRequest(room.conversationId(), null,
					Map.of("type", type, "reservationId", room.reservationId())));
			return true;
		} catch (ApiException e) {
			// 방은 열어 주고, 고객이 질문하면 그때 답한다
			log.warn("aftercare guide not requested for {}: {}", room.conversationId(), e.code());
			return false;
		}
	}

	private Optional<UUID> roomOf(long reservationId) {
		return jdbc.sql("SELECT conversation_id FROM app.aftercare_rooms WHERE reservation_id = :r")
				.param("r", reservationId).query(UUID.class).optional();
	}

	private Row require(UUID conversationId) {
		return jdbc.sql(SELECT + " WHERE a.conversation_id = :c").param("c", conversationId)
				.query((rs, i) -> row(rs)).single();
	}

	private static Row row(ResultSet rs) throws SQLException {
		return new Row(rs.getObject("conversation_id", UUID.class), rs.getLong("reservation_id"),
				rs.getString("reservation_status"), rs.getString("mode"), rs.getString("procedure_code"),
				rs.getLong("hospital_id"), Times.kst(rs.getObject("start_at", OffsetDateTime.class)),
				Times.kst(rs.getObject("created_at", OffsetDateTime.class)));
	}

	/** 시술일 기준 오늘이 며칠째인지 (시술일 = 0, 시술 전은 음수) — Asia/Seoul 날짜 기준 */
	static int daysFromProcedure(OffsetDateTime startAt, LocalDate today) {
		return (int) ChronoUnit.DAYS.between(startAt.atZoneSameInstant(Times.SEOUL).toLocalDate(), today);
	}

	private AftercareConversation toDto(Row r, String locale) {
		UUID active = jdbc.sql("""
				SELECT id FROM app.ai_tasks WHERE conversation_id = :c AND status IN ('QUEUED','RUNNING','WAITING_APPROVAL')
				ORDER BY created_at DESC LIMIT 1
				""").param("c", r.conversationId()).query(UUID.class).optional().orElse(null);
		return new AftercareConversation(r.conversationId(), r.reservationId(), r.reservationStatus(), r.mode(),
				r.procedureCode(), catalog.procedure(r.procedureCode(), locale).map(Procedure::name).orElse(null),
				new HospitalRef(r.hospitalId(), catalog.hospitalName(r.hospitalId(), locale).orElse(null)),
				r.startAt(), daysFromProcedure(r.startAt(), LocalDate.now(Times.SEOUL)), active, r.createdAt());
	}
}
