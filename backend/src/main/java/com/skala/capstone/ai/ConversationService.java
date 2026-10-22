package com.skala.capstone.ai;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.skala.capstone.ai.AiDtos.Conversation;
import com.skala.capstone.ai.AiDtos.ConversationMessage;
import com.skala.capstone.catalog.CatalogService;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.security.Role;
import com.skala.capstone.common.web.Json;
import com.skala.capstone.common.web.Times;
import com.skala.capstone.reservation.ReservationDtos.HospitalRef;

/**
 * AI 대화창 (conversationId = LangGraph thread_id).
 * - 메인 대화(MAIN): 조건 정리·병원 검색
 * - 병원 대화(HOSPITAL): 병원을 고르면 새로 열린다 (D-20). 같은 고객·병원의 대화가 이미 있으면 그것을 쓴다
 * - 상담사 연결 중(HUMAN): 이 동안 AI 는 답하지 않는다 (D-09)
 * 대화 본문은 agent 의 checkpointer 에 있고, backend 는 화면 복원용으로 작업(ai_tasks) 기록에서 메시지를 다시 만든다.
 */
@Service
public class ConversationService {

	public record Created(Conversation conversation, boolean created) {
	}

	record Row(UUID id, long userId, UUID parentId, String mode, Long hospitalId, Long consultationId,
			String conditions, OffsetDateTime createdAt) {
	}

	private final JdbcClient jdbc;
	private final CatalogService catalog;
	private final Json json;

	public ConversationService(JdbcClient jdbc, CatalogService catalog, Json json) {
		this.jdbc = jdbc;
		this.catalog = catalog;
		this.json = json;
	}

	@Transactional
	public Created create(CurrentUser user, Long hospitalId, UUID parentId, String locale) {
		if (user.role() != Role.CUSTOMER) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
		Row parent = parentId == null ? null : requireOwned(user, parentId);
		if (hospitalId != null) {
			catalog.requireHospital(hospitalId);
			Optional<Row> existing = rows("user_id = :u AND selected_hospital_id = :h AND mode IN ('HOSPITAL','HUMAN')"
					+ " AND id NOT IN (SELECT conversation_id FROM app.aftercare_rooms)",
					user.id(), hospitalId).stream().findFirst();
			if (existing.isPresent()) {
				return new Created(toDto(existing.get(), locale, false), false);
			}
		}
		UUID id = UUID.randomUUID();
		jdbc.sql("""
				INSERT INTO app.conversations (id, user_id, parent_conversation_id, mode, selected_hospital_id, conditions)
				VALUES (:id, :u, :p, :mode, :h, CAST(:c AS jsonb))
				""").param("id", id).param("u", user.id()).param("p", parentId)
				.param("mode", hospitalId == null ? "MAIN" : "HOSPITAL").param("h", hospitalId)
				.param("c", parent == null ? null : parent.conditions()).update();
		return new Created(toDto(require(id), locale, false), true);
	}

	@Transactional(readOnly = true)
	public List<Conversation> mine(CurrentUser user, String locale) {
		return rows("user_id = :u", user.id(), null).stream().map(r -> toDto(r, locale, false)).toList();
	}

	@Transactional(readOnly = true)
	public Conversation get(CurrentUser user, UUID id, String locale) {
		return toDto(requireOwned(user, id), locale, true);
	}

	/** 본인 대화만 (아니면 403, 없으면 404) */
	Row requireOwned(CurrentUser user, UUID id) {
		Row row = require(id);
		if (row.userId() != user.id()) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
		return row;
	}

	Row require(UUID id) {
		return jdbc.sql("SELECT *, conditions::text AS conditions_json FROM app.conversations WHERE id = :id")
				.param("id", id).query((rs, i) -> row(rs)).optional()
				.orElseThrow(() -> ApiException.notFound("conversation"));
	}

	private List<Row> rows(String where, long userId, Long hospitalId) {
		var spec = jdbc.sql("SELECT *, conditions::text AS conditions_json FROM app.conversations WHERE " + where
				+ " ORDER BY created_at DESC").param("u", userId);
		if (hospitalId != null) {
			spec = spec.param("h", hospitalId);
		}
		return spec.query((rs, i) -> row(rs)).list();
	}

	private static Row row(ResultSet rs) throws SQLException {
		return new Row(rs.getObject("id", UUID.class), rs.getLong("user_id"),
				rs.getObject("parent_conversation_id", UUID.class), rs.getString("mode"),
				(Long) rs.getObject("selected_hospital_id"), (Long) rs.getObject("consultation_id"),
				rs.getString("conditions_json"), Times.kst(rs.getObject("created_at", OffsetDateTime.class)));
	}

	private Conversation toDto(Row r, String locale, boolean withMessages) {
		HospitalRef hospital = r.hospitalId() == null ? null
				: new HospitalRef(r.hospitalId(), catalog.hospitalName(r.hospitalId(), locale).orElse(null));
		return new Conversation(r.id(), r.mode(), hospital, r.parentId(), r.consultationId(),
				json.read(r.conditions()), r.createdAt(), withMessages ? messages(r.id()) : null);
	}

	/** 작업 기록 → 화면용 메시지: 사용자 입력 + (완료된 경우) AI 답변·근거·카드 */
	private List<ConversationMessage> messages(UUID conversationId) {
		List<ConversationMessage> out = new ArrayList<>();
		jdbc.sql("""
				SELECT input, status, answer, sources::text AS sources, result_cards::text AS cards, created_at, finished_at
				FROM app.ai_tasks WHERE conversation_id = :c ORDER BY created_at, id
				""").param("c", conversationId).query(rs -> {
			OffsetDateTime created = Times.kst(rs.getObject("created_at", OffsetDateTime.class));
			String input = rs.getString("input");
			if (input != null && !input.isBlank()) {
				out.add(new ConversationMessage("user", input, null, null, created));
			}
			if ("DONE".equals(rs.getString("status"))) {
				OffsetDateTime finished = Times.kst(rs.getObject("finished_at", OffsetDateTime.class));
				out.add(new ConversationMessage("assistant", rs.getString("answer"), json.read(rs.getString("sources")),
						json.read(rs.getString("cards")), finished != null ? finished : created));
			}
		});
		return out;
	}
}
