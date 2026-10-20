package com.skala.capstone.consultation;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.skala.capstone.catalog.CatalogService;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.messaging.MessagePublisher;
import com.skala.capstone.common.messaging.Queues;
import com.skala.capstone.common.security.AuditLogger;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.security.Role;
import com.skala.capstone.common.web.AfterCommit;
import com.skala.capstone.common.web.Json;
import com.skala.capstone.common.web.Masking;
import com.skala.capstone.common.web.Times;
import com.skala.capstone.consultation.ConsultationDtos.Consultation;
import com.skala.capstone.consultation.ConsultationDtos.ConsultationStatus;
import com.skala.capstone.consultation.ConsultationDtos.StompEvent;
import com.skala.capstone.consultation.ConsultationDtos.SummaryTranslate;
import com.skala.capstone.consultation.ConsultationDtos.SummaryTranslated;
import com.skala.capstone.notification.NotificationService;
import com.skala.capstone.reservation.ReservationDtos.CustomerRef;
import com.skala.capstone.reservation.ReservationDtos.HospitalRef;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;

/**
 * 상담사 연결 (02 문서 3-4, 16 명세 7장).
 * 1) 병원 대화창에서 에이전트가 요약 카드 + 고객 동의로 상담 요청 → WAITING, 대화는 HUMAN(AI 정지)
 * 2) 상담사가 문의함에서 수락 → ACTIVE, 같은 채팅창에서 통역 채팅
 * 3) 상담사가 종료 → CLOSED, 대화는 다시 HOSPITAL(AI 응답 재개)
 */
@Service
public class ConsultationService {

	private static final Logger log = LoggerFactory.getLogger(ConsultationService.class);

	public record Created(Consultation consultation, boolean created) {
	}

	private final JdbcClient jdbc;
	private final ConsultationAccess access;
	private final CatalogService catalog;
	private final NotificationService notifications;
	private final MessagePublisher publisher;
	private final SimpMessagingTemplate stomp;
	private final AuditLogger audit;
	private final Json json;

	public ConsultationService(JdbcClient jdbc, ConsultationAccess access, CatalogService catalog,
			NotificationService notifications, MessagePublisher publisher, SimpMessagingTemplate stomp,
			AuditLogger audit, Json json) {
		this.jdbc = jdbc;
		this.access = access;
		this.catalog = catalog;
		this.notifications = notifications;
		this.publisher = publisher;
		this.stomp = stomp;
		this.audit = audit;
		this.json = json;
	}

	/** 에이전트(acting 고객)의 상담 요청. 동의가 없으면 409 CONSENT_REQUIRED, 열린 상담이 있으면 그대로 반환. */
	@Transactional
	public Created request(CurrentUser user, long hospitalId, UUID conversationId, Map<String, Object> summaryCard,
			Boolean consent, String locale) {
		if (user.role() != Role.CUSTOMER) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
		if (!Boolean.TRUE.equals(consent)) {
			throw new ApiException(ErrorCode.CONSENT_REQUIRED);
		}
		var conv = jdbc.sql("SELECT user_id, selected_hospital_id FROM app.conversations WHERE id = :id FOR UPDATE")
				.param("id", conversationId)
				.query((rs, i) -> new long[] { rs.getLong("user_id"), rs.getLong("selected_hospital_id") }).optional()
				.orElseThrow(() -> ApiException.notFound("conversation"));
		if (conv[0] != user.id()) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
		if (conv[1] != hospitalId) {
			throw new ApiException(ErrorCode.VALIDATION_FAILED, Map.of("fields",
					List.of(Map.of("field", "hospitalId", "reason", "conversation is not for this hospital"))));
		}
		Optional<Long> open = jdbc.sql("""
				SELECT id FROM app.consultations WHERE conversation_id = :c AND status IN ('WAITING','ACTIVE')
				ORDER BY id DESC LIMIT 1
				""").param("c", conversationId).query(Long.class).optional();
		if (open.isPresent()) {
			return new Created(toDto(open.get(), user, locale), false);
		}
		long id = jdbc.sql("""
				INSERT INTO app.consultations (user_id, hospital_id, conversation_id, status, customer_locale,
				    summary_card, consent_at)
				VALUES (:u, :h, :c, 'WAITING', :loc, CAST(:card AS jsonb), now())
				RETURNING id
				""").param("u", user.id()).param("h", hospitalId).param("c", conversationId)
				.param("loc", user.locale()).param("card", json.write(summaryCard)).query(Long.class).single();
		jdbc.sql("UPDATE app.conversations SET mode = 'HUMAN', consultation_id = :id WHERE id = :c")
				.param("id", id).param("c", conversationId).update();

		// 상담사가 읽을 한국어 요약 카드 → agent 번역 워커 (실패해도 원본으로 표시)
		publisher.publishAfterCommit(Queues.SUMMARY_TRANSLATE,
				new SummaryTranslate(id, summaryCard, user.locale(), "ko"), null);
		notifications.notify(notifications.hospitalStaff(hospitalId, Role.COUNSELOR), "CONSULTATION_REQUESTED",
				Map.of("consultationId", id));
		AfterCommit.run(() -> audit.log(user, "CONSULTATION_REQUESTED", "consultation:" + id, Map.of()));
		return new Created(toDto(id, user, locale), true);
	}

	@Transactional(readOnly = true)
	public Consultation get(CurrentUser user, long id, String locale) {
		access.require(user, id);
		return toDto(id, user, locale);
	}

	/** 상담사 문의함: 자기 병원 상담만 (token.hospitalId), 최신순 */
	@Transactional(readOnly = true)
	public List<Consultation> inbox(CurrentUser counselor, String status, String locale) {
		var spec = jdbc.sql("SELECT id FROM app.consultations WHERE hospital_id = :h"
				+ (status != null ? " AND status = :s" : "") + " ORDER BY created_at DESC, id DESC")
				.param("h", counselor.hospitalId());
		if (status != null) {
			spec = spec.param("s", status);
		}
		return spec.query(Long.class).list().stream().map(id -> toDto(id, counselor, locale)).toList();
	}

	/** 상담사 수락: WAITING → ACTIVE, 담당 = 나 */
	@Transactional
	public Consultation accept(CurrentUser counselor, long id, String locale) {
		var p = requireCounselorOf(counselor, id);
		if (!"WAITING".equals(p.status())) {
			throw new ApiException(ErrorCode.INVALID_STATE_TRANSITION, Map.of("from", p.status(), "to", "ACTIVE"));
		}
		int n = jdbc.sql("UPDATE app.consultations SET status = 'ACTIVE', counselor_id = :me WHERE id = :id AND status = 'WAITING'")
				.param("me", counselor.id()).param("id", id).update();
		if (n == 0) {
			throw new ApiException(ErrorCode.CONCURRENT_UPDATE);
		}
		notifications.notify(List.of(p.customerId()), "CONSULTATION_ACCEPTED",
				Map.of("consultationId", id, "conversationId", conversationIdOf(id)));
		pushStatus(id, "ACTIVE", counselor.id());
		AfterCommit.run(() -> audit.log(counselor, "CONSULTATION_ACCEPTED", "consultation:" + id, Map.of()));
		return toDto(id, counselor, locale);
	}

	/** 상담 종료: WAITING·ACTIVE → CLOSED, 대화창은 AI 응답 재개(HOSPITAL) */
	@Transactional
	public Consultation close(CurrentUser counselor, long id, String locale) {
		var p = requireCounselorOf(counselor, id);
		if (!"WAITING".equals(p.status()) && !"ACTIVE".equals(p.status())) {
			throw new ApiException(ErrorCode.INVALID_STATE_TRANSITION, Map.of("from", p.status(), "to", "CLOSED"));
		}
		int n = jdbc.sql("""
				UPDATE app.consultations SET status = 'CLOSED', closed_at = now() WHERE id = :id AND status = :from
				""").param("id", id).param("from", p.status()).update();
		if (n == 0) {
			throw new ApiException(ErrorCode.CONCURRENT_UPDATE);
		}
		jdbc.sql("UPDATE app.conversations SET mode = 'HOSPITAL' WHERE consultation_id = :id AND mode = 'HUMAN'")
				.param("id", id).update();
		notifications.notify(List.of(p.customerId()), "CONSULTATION_CLOSED",
				Map.of("consultationId", id, "conversationId", conversationIdOf(id)));
		pushStatus(id, "CLOSED", p.counselorId());
		AfterCommit.run(() -> audit.log(counselor, "CONSULTATION_CLOSED", "consultation:" + id, Map.of()));
		return toDto(id, counselor, locale);
	}

	/** summary.translated: 한국어 요약 카드 저장 */
	@Transactional
	public void onSummaryTranslated(SummaryTranslated msg) {
		if (msg.consultationId() == null || !msg.ok() || msg.summaryCardKo() == null) {
			log.warn("summary translation failed for consultation {}", msg.consultationId());
			return;
		}
		jdbc.sql("UPDATE app.consultations SET summary_card_ko = CAST(:c AS jsonb) WHERE id = :id")
				.param("c", json.write(msg.summaryCardKo())).param("id", msg.consultationId()).update();
	}

	private ConsultationAccess.Party requireCounselorOf(CurrentUser counselor, long id) {
		var p = access.find(id).orElseThrow(() -> ApiException.notFound("consultation"));
		if (counselor.role() != Role.COUNSELOR || !Objects.equals(counselor.hospitalId(), p.hospitalId())) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
		return p;
	}

	private void pushStatus(long id, String status, Long counselorId) {
		AfterCommit.run(() -> stomp.convertAndSend("/topic/consultations/" + id,
				new StompEvent("CONSULTATION_STATUS", new ConsultationStatus(id, status, counselorId))));
	}

	/** 알림을 눌렀을 때 고객 화면이 바로 그 대화창(/chat/{conversationId})으로 갈 수 있도록 알림에 같이 싣는다. */
	private String conversationIdOf(long consultationId) {
		return jdbc.sql("SELECT conversation_id::text FROM app.consultations WHERE id = :id")
				.param("id", consultationId).query(String.class).single();
	}

	/**
	 * 요약 카드를 「공통 계약서」 SummaryCard 모양으로 맞춘다.
	 * 정상 경로(business-mcp)는 이미 계약 모양이지만, mock seed 의 카드는 예전 모양(snake_case: procedure_name,
	 * preferred_dates, concerns, language …)이라 화면이 깨진다. 계약 키가 있으면 그대로 쓰고, 없으면 예전 키에서 옮겨 담는다.
	 * 나머지 키는 그대로 둔다.
	 */
	static JsonNode summaryCard(JsonNode raw, String customerLocale) {
		ObjectNode card = raw instanceof ObjectNode o ? o.deepCopy() : JsonNodeFactory.instance.objectNode();
		if (!card.hasNonNull("procedure")) {
			card.put("procedure", text(card, "procedure_name", text(card, "procedureName", text(card, "procedure_code", ""))));
		}
		if (!card.hasNonNull("preferredDates")) {
			JsonNode dates = card.has("preferred_dates") ? card.get("preferred_dates") : card.get("preferredDates");
			card.put("preferredDates", joinDistinct(dates));
		} else if (card.get("preferredDates").isArray()) {
			card.put("preferredDates", joinDistinct(card.get("preferredDates")));
		}
		if (!card.has("stayDays")) {
			JsonNode stay = card.get("stay_days");
			if (stay != null && stay.canConvertToInt()) {
				card.put("stayDays", stay.asInt());
			} else {
				card.putNull("stayDays");
			}
		}
		if (!card.has("budget")) {
			JsonNode budget = card.get("budget_krw");
			if (budget != null && !budget.isNull()) {
				card.put("budget", budget.asText());
			} else {
				card.putNull("budget");
			}
		}
		if (!card.path("questions").isArray()) {
			JsonNode concerns = card.get("concerns");
			card.set("questions", concerns != null && concerns.isArray() ? concerns.deepCopy()
					: JsonNodeFactory.instance.arrayNode());
		}
		if (!card.hasNonNull("customerLocale")) {
			card.put("customerLocale", text(card, "language", customerLocale));
		}
		return card;
	}

	private static String text(JsonNode node, String field, String fallback) {
		JsonNode v = node.get(field);
		return v != null && !v.isNull() && !v.asText().isBlank() ? v.asText() : fallback;
	}

	/** ["2026-10-23","2026-10-23"] → "2026-10-23" (중복 제거, 순서 유지, " ~ " 로 연결) */
	private static String joinDistinct(JsonNode dates) {
		if (dates == null || dates.isNull()) {
			return "";
		}
		if (!dates.isArray()) {
			return dates.asText();
		}
		var seen = new LinkedHashSet<String>();
		dates.forEach(d -> seen.add(d.asText()));
		return String.join(" ~ ", seen);
	}

	private Consultation toDto(long id, CurrentUser viewer, String locale) {
		return jdbc.sql("""
				SELECT c.*, c.summary_card::text AS card, c.summary_card_ko::text AS card_ko,
				       u.name AS customer_name, u.nationality, u.locale AS user_locale
				FROM app.consultations c JOIN app.users u ON u.id = c.user_id WHERE c.id = :id
				""").param("id", id).query((rs, i) -> dto(rs, viewer, locale)).single();
	}

	private Consultation dto(ResultSet rs, CurrentUser viewer, String locale) throws SQLException {
		long hospitalId = rs.getLong("hospital_id");
		String card = rs.getString("card");
		String cardKo = rs.getString("card_ko");
		boolean staff = viewer.role() == Role.COUNSELOR;
		return new Consultation(rs.getLong("id"), rs.getString("status"),
				new HospitalRef(hospitalId, catalog.hospitalName(hospitalId, locale).orElse(null)),
				new CustomerRef(rs.getLong("user_id"), Masking.name(rs.getString("customer_name")),
						rs.getString("nationality"), rs.getString("customer_locale") != null
								? rs.getString("customer_locale") : rs.getString("user_locale")),
				(Long) rs.getObject("counselor_id"), rs.getObject("conversation_id", UUID.class),
				summaryCard(json.read(staff && cardKo != null ? cardKo : card), rs.getString("customer_locale")),
				Times.kst(rs.getObject("created_at", OffsetDateTime.class)),
				Times.kst(rs.getObject("closed_at", OffsetDateTime.class)));
	}
}
