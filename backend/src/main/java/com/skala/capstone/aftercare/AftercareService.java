package com.skala.capstone.aftercare;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
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
import com.skala.capstone.common.web.Times;
import com.skala.capstone.reservation.ReservationDtos.HospitalRef;

/**
 * 시술 사후관리 대화방.
 * - 확정(CONFIRMED) 예약 1건당 대화 1개 (mode AFTERCARE, selected_hospital_id = 예약 병원)
 * - 방을 처음 열면 AI 첫 안내를 요청한다 (action AFTERCARE_INTRO, 사용자 입력 없음)
 * - 이후 질문은 기존 /api/ai/tasks 로 보낸다
 */
@Service
public class AftercareService {

	private static final Logger log = LoggerFactory.getLogger(AftercareService.class);

	public record Opened(AftercareConversation conversation, boolean created) {
	}

	record Row(UUID conversationId, long reservationId, String mode, String procedureCode, long hospitalId,
			OffsetDateTime startAt, OffsetDateTime createdAt) {
	}

	private record Reservation(long userId, long hospitalId, String status) {
	}

	private static final String SELECT = """
			SELECT a.conversation_id, a.reservation_id, c.mode, r.procedure_code, r.hospital_id, s.start_at, a.created_at
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

	/** 사후관리 방 열기: 있으면 그 방(200), 없으면 만들고 첫 안내 요청(201). 본인 확정 예약만. */
	public Opened open(CurrentUser user, long reservationId, String locale) {
		Reservation r = jdbc.sql("SELECT user_id, hospital_id, status FROM app.reservations WHERE id = :id")
				.param("id", reservationId)
				.query((rs, i) -> new Reservation(rs.getLong("user_id"), rs.getLong("hospital_id"), rs.getString("status")))
				.optional().orElseThrow(() -> ApiException.notFound("reservation"));
		if (r.userId() != user.id()) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
		Optional<UUID> existing = roomOf(reservationId);
		boolean created = false;
		if (existing.isEmpty()) {
			if (!"CONFIRMED".equals(r.status())) {
				throw new ApiException(ErrorCode.INVALID_STATE_TRANSITION, Map.of("from", r.status(), "to", "AFTERCARE"));
			}
			try {
				existing = Optional.of(tx.execute(status -> insert(user.id(), r.hospitalId(), reservationId)));
				created = true;
			} catch (DuplicateKeyException e) {
				// 동시에 두 번 눌렀으면 먼저 만든 방을 쓴다
				existing = roomOf(reservationId);
			}
		}
		UUID conversationId = existing.orElseThrow(() -> ApiException.notFound("conversation"));
		requestIntroIfEmpty(user, conversationId, reservationId);
		return new Opened(toDto(require(conversationId), locale), created);
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

	/** 아직 작업이 하나도 없는 방이면 첫 안내를 요청한다 (큐 발행 실패 후 다시 열 때도 재시도됨) */
	private void requestIntroIfEmpty(CurrentUser user, UUID conversationId, long reservationId) {
		boolean empty = jdbc.sql("SELECT NOT EXISTS (SELECT 1 FROM app.ai_tasks WHERE conversation_id = :c)")
				.param("c", conversationId).query(Boolean.class).single();
		if (!empty) {
			return;
		}
		try {
			tasks.create(user, new CreateTaskRequest(conversationId, null,
					Map.of("type", "AFTERCARE_INTRO", "reservationId", reservationId)));
		} catch (ApiException e) {
			// 방은 열어 주고, 고객이 질문하면 그때 답한다
			log.warn("aftercare intro not requested for {}: {}", conversationId, e.code());
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
		return new Row(rs.getObject("conversation_id", UUID.class), rs.getLong("reservation_id"), rs.getString("mode"),
				rs.getString("procedure_code"), rs.getLong("hospital_id"),
				Times.kst(rs.getObject("start_at", OffsetDateTime.class)),
				Times.kst(rs.getObject("created_at", OffsetDateTime.class)));
	}

	private AftercareConversation toDto(Row r, String locale) {
		UUID active = jdbc.sql("""
				SELECT id FROM app.ai_tasks WHERE conversation_id = :c AND status IN ('QUEUED','RUNNING','WAITING_APPROVAL')
				ORDER BY created_at DESC LIMIT 1
				""").param("c", r.conversationId()).query(UUID.class).optional().orElse(null);
		return new AftercareConversation(r.conversationId(), r.reservationId(), r.mode(), r.procedureCode(),
				catalog.procedure(r.procedureCode(), locale).map(Procedure::name).orElse(null),
				new HospitalRef(r.hospitalId(), catalog.hospitalName(r.hospitalId(), locale).orElse(null)),
				r.startAt(), active, r.createdAt());
	}
}
