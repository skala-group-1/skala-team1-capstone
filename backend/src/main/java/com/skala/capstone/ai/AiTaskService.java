package com.skala.capstone.ai;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.skala.capstone.ai.AiDtos.AiTask;
import com.skala.capstone.ai.AiDtos.AiTaskWithUser;
import com.skala.capstone.ai.AiDtos.CreateTaskRequest;
import com.skala.capstone.ai.AiDtos.TaskConversation;
import com.skala.capstone.ai.AiDtos.TaskEvent;
import com.skala.capstone.ai.AiDtos.TaskRequested;
import com.skala.capstone.ai.AiDtos.TaskResume;
import com.skala.capstone.ai.AiDtos.TaskUser;
import com.skala.capstone.common.config.AppProperties;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.messaging.MessagePublisher;
import com.skala.capstone.common.messaging.Queues;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.security.Role;
import com.skala.capstone.common.web.AfterCommit;
import com.skala.capstone.common.web.Json;
import com.skala.capstone.common.web.PageResponse;
import com.skala.capstone.common.web.Times;

/**
 * AI 작업 (02 문서 3-1 흐름, 16 명세 6장).
 *
 * <pre>
 * 브라우저 ─POST /api/ai/tasks─▶ backend: ai_tasks(QUEUED) 저장 → ai.task.requested 발행 → 202
 * 브라우저 ─GET .../stream──────▶ backend: SSE 연결
 * agent ──ai.task.event─────────▶ backend: DB 반영 → SSE 로 중계 (TOKEN, TOOL_START ... DONE)
 * 승인 카드 ─POST .../approval──▶ backend: ai.task.resume 발행 → 같은 작업 이어서 진행
 * </pre>
 * backend 는 LLM 을 부르지 않는다 (계층 금지 사항). 모든 AI 처리는 큐를 통해 agent 가 한다.
 */
@Service
public class AiTaskService {

	private static final Logger log = LoggerFactory.getLogger(AiTaskService.class);
	private static final Set<String> ACTIVE = Set.of("QUEUED", "RUNNING", "WAITING_APPROVAL");

	record Row(UUID id, UUID conversationId, long userId, String input, String status, String answer,
			String sources, String pendingAction, String error, int lastSeq, OffsetDateTime createdAt,
			OffsetDateTime finishedAt) {
	}

	private final JdbcClient jdbc;
	private final ConversationService conversations;
	private final MessagePublisher publisher;
	private final SseHub hub;
	private final Json json;
	private final TransactionTemplate tx;
	private final AppProperties app;

	public AiTaskService(JdbcClient jdbc, ConversationService conversations, MessagePublisher publisher, SseHub hub,
			Json json, TransactionTemplate tx, AppProperties app) {
		this.jdbc = jdbc;
		this.conversations = conversations;
		this.publisher = publisher;
		this.hub = hub;
		this.json = json;
		this.tx = tx;
		this.app = app;
	}

	// ------------------------------------------------------------------ 작업 생성·승인

	/** 작업 접수: 저장(커밋) → 큐 발행. 발행이 실패하면 작업을 FAILED 로 바꾸고 503 AI_UNAVAILABLE. */
	public AiTask create(CurrentUser user, CreateTaskRequest req) {
		String message = req.message() == null ? "" : req.message().trim();
		if (message.isEmpty() && req.action() == null) {
			throw new ApiException(ErrorCode.VALIDATION_FAILED,
					Map.of("fields", List.of(Map.of("field", "message", "reason", "message or action is required"))));
		}
		if (req.action() != null && !(req.action().get("type") instanceof String)) {
			throw new ApiException(ErrorCode.VALIDATION_FAILED,
					Map.of("fields", List.of(Map.of("field", "action.type", "reason", "required"))));
		}
		UUID taskId = UUID.randomUUID();
		ConversationService.Row conv = tx.execute(status -> {
			ConversationService.Row c = conversations.requireOwned(user, req.conversationId());
			if ("HUMAN".equals(c.mode())) {
				// 상담사 연결 중에는 AI 가 답하지 않는다 (D-09). FE 는 STOMP 로 상담사에게 보내야 한다
				throw new ApiException(ErrorCode.INVALID_STATE_TRANSITION, Map.of("from", "HUMAN", "to", "AI"));
			}
			// 같은 대화(thread)에서 동시에 두 작업을 돌리지 않는다
			jdbc.sql("SELECT id FROM app.conversations WHERE id = :id FOR UPDATE").param("id", c.id())
					.query(UUID.class).single();
			Optional<UUID> active = jdbc.sql("""
					SELECT id FROM app.ai_tasks WHERE conversation_id = :c AND status IN ('QUEUED','RUNNING','WAITING_APPROVAL')
					ORDER BY created_at DESC LIMIT 1
					""").param("c", c.id()).query(UUID.class).optional();
			if (active.isPresent()) {
				throw new ApiException(ErrorCode.INVALID_STATE_TRANSITION,
						Map.of("from", "BUSY", "to", "QUEUED", "activeTaskId", active.get().toString()));
			}
			jdbc.sql("""
					INSERT INTO app.ai_tasks (id, conversation_id, user_id, input, action, status)
					VALUES (:id, :c, :u, :input, CAST(:action AS jsonb), 'QUEUED')
					""").param("id", taskId).param("c", c.id()).param("u", user.id()).param("input", message)
					.param("action", json.write(req.action())).update();
			return c;
		});
		TaskRequested body = new TaskRequested(taskId, conv.id(), taskUser(user), message, req.action(),
				OffsetDateTime.now(Times.SEOUL),
				new TaskConversation(conv.mode(), conv.hospitalId(), conv.parentId()));
		dispatch(Queues.AI_TASK_REQUESTED, taskId, body);
		return toDto(require(taskId));
	}

	/** 승인 카드 응답 → ai.task.resume. 승인 대기 상태가 아니면 409 TASK_NOT_WAITING_APPROVAL. */
	public AiTask approve(CurrentUser user, UUID taskId, boolean approved, Map<String, Object> editedArgs,
			String reason) {
		Row row = requireOwned(user, taskId);
		if (!"WAITING_APPROVAL".equals(row.status())) {
			throw new ApiException(ErrorCode.TASK_NOT_WAITING_APPROVAL);
		}
		if (editedArgs != null && !editedArgs.isEmpty()) {
			JsonNode editable = Optional.ofNullable(json.read(row.pendingAction())).map(p -> p.get("editable"))
					.orElse(null);
			for (String key : editedArgs.keySet()) {
				boolean allowed = editable != null && editable.isArray()
						&& java.util.stream.StreamSupport.stream(editable.spliterator(), false)
								.anyMatch(n -> key.equals(n.asText()));
				if (!allowed) {
					throw new ApiException(ErrorCode.VALIDATION_FAILED, Map.of("fields",
							List.of(Map.of("field", "editedArgs." + key, "reason", "not editable"))));
				}
			}
		}
		int n = jdbc.sql("""
				UPDATE app.ai_tasks SET status = 'QUEUED', updated_at = now()
				WHERE id = :id AND status = 'WAITING_APPROVAL'
				""").param("id", taskId).update();
		if (n == 0) {
			throw new ApiException(ErrorCode.TASK_NOT_WAITING_APPROVAL);
		}
		dispatch(Queues.AI_TASK_RESUME, taskId, new TaskResume(taskId, row.conversationId(), taskUser(user), approved,
				editedArgs == null ? Map.of() : editedArgs, reason));
		return toDto(require(taskId));
	}

	private void dispatch(String queue, UUID taskId, Object body) {
		try {
			publisher.publish(queue, body, taskId.toString(), 0);
		} catch (AmqpException e) {
			log.warn("cannot publish {} for task {}: {}", queue, taskId, e.getMessage());
			fail(taskId, "AI_UNAVAILABLE", "AI service is temporarily unavailable");
			throw new ApiException(ErrorCode.AI_UNAVAILABLE);
		}
	}

	private static TaskUser taskUser(CurrentUser user) {
		// agent 는 JWT 를 받지 않는다. 사용자 정보는 backend 가 토큰에서 꺼내 넣은 값만 쓴다 (11 문서)
		return new TaskUser(user.id(), user.role().name(), user.locale());
	}

	// ------------------------------------------------------------------ 조회·SSE

	public AiTask get(CurrentUser user, UUID taskId) {
		return toDto(requireOwned(user, taskId));
	}

	public List<AiTask> mine(CurrentUser user) {
		return jdbc.sql(select() + " WHERE user_id = :u ORDER BY created_at DESC LIMIT 50").param("u", user.id())
				.query((rs, i) -> row(rs)).list().stream().map(this::toDto).toList();
	}

	public PageResponse<AiTaskWithUser> forOperator(String status, int page, int size) {
		String where = status == null ? "" : " WHERE status = :s";
		Map<String, Object> p = new LinkedHashMap<>();
		if (status != null) {
			p.put("s", status);
		}
		long total = jdbc.sql("SELECT count(*) FROM app.ai_tasks" + where).params(p).query(Long.class).single();
		p.put("l", size);
		p.put("o", (long) page * size);
		List<AiTaskWithUser> items = jdbc.sql(select() + where + " ORDER BY created_at DESC LIMIT :l OFFSET :o")
				.params(p).query((rs, i) -> row(rs)).list().stream()
				.map(r -> new AiTaskWithUser(r.userId(), toDto(r))).toList();
		return new PageResponse<>(items, page, size, total);
	}

	public SseEmitter stream(CurrentUser user, UUID taskId, String lastEventIdHeader) {
		Row row = requireOwned(user, taskId);
		int lastEventId = 0;
		try {
			lastEventId = lastEventIdHeader == null ? 0 : Integer.parseInt(lastEventIdHeader.trim());
		} catch (NumberFormatException ignored) {
			// 잘못된 값이면 처음부터
		}
		boolean running = "QUEUED".equals(row.status()) || "RUNNING".equals(row.status());
		return hub.subscribe(taskId, lastEventId, running, finalEvent(row));
	}

	/** 버퍼가 없을 때(backend 재기동 등) DB 값으로 만드는 마지막 이벤트 */
	private SseHub.Event finalEvent(Row r) {
		ObjectNode data = json.mapper().createObjectNode();
		switch (r.status()) {
			case "DONE" -> {
				data.put("answer", r.answer());
				data.set("sources", Optional.ofNullable(json.read(r.sources())).orElse(json.mapper().createArrayNode()));
				return new SseHub.Event(r.lastSeq(), "DONE", data);
			}
			case "FAILED" -> {
				JsonNode err = json.read(r.error());
				data.put("code", err != null && err.has("code") ? err.get("code").asText() : "AI_UNAVAILABLE");
				data.put("message", err != null && err.has("message") ? err.get("message").asText() : r.error());
				data.put("traceId", r.id().toString());
				return new SseHub.Event(r.lastSeq(), "FAILED", data);
			}
			case "WAITING_APPROVAL" -> {
				return new SseHub.Event(r.lastSeq(), "APPROVAL_REQUIRED", json.read(r.pendingAction()));
			}
			default -> {
				return null;
			}
		}
	}

	// ------------------------------------------------------------------ agent 이벤트 처리

	/** ai.task.event 1건: 순서 번호(seq)로 중복을 거르고, 상태를 DB 에 반영한 뒤 SSE 로 중계 */
	public void handleEvent(TaskEvent e) {
		if (e.taskId() == null || e.event() == null) {
			log.warn("ignored malformed ai.task.event: {}", e);
			return;
		}
		Boolean applied = tx.execute(status -> {
			Optional<Row> found = jdbc.sql(select() + " WHERE id = :id FOR UPDATE").param("id", e.taskId())
					.query((rs, i) -> row(rs)).optional();
			if (found.isEmpty()) {
				log.warn("ai.task.event for unknown task {}", e.taskId());
				return false;
			}
			Row r = found.get();
			if (e.seq() <= r.lastSeq()) {
				return false; // 이미 받은 이벤트 (재전송)
			}
			apply(r, e);
			jdbc.sql("UPDATE app.ai_tasks SET last_seq = :seq, updated_at = now() WHERE id = :id")
					.param("seq", e.seq()).param("id", e.taskId()).update();
			return true;
		});
		if (Boolean.TRUE.equals(applied)) {
			hub.publish(e.taskId(), new SseHub.Event(e.seq(), e.event(), e.data()));
		}
	}

	private void apply(Row r, TaskEvent e) {
		JsonNode d = e.data();
		switch (e.event()) {
			case "STATUS" -> {
				String s = d != null && d.has("status") ? d.get("status").asText() : "RUNNING";
				if (Set.of("QUEUED", "RUNNING").contains(s)) {
					setStatus(r.id(), s);
				}
			}
			case "CONDITIONS" -> jdbc.sql("UPDATE app.conversations SET conditions = CAST(:c AS jsonb) WHERE id = :id")
					.param("c", json.write(d == null ? null : d.get("conditions"))).param("id", r.conversationId())
					.update();
			case "RESULT_CARDS" -> jdbc.sql("UPDATE app.ai_tasks SET result_cards = CAST(:c AS jsonb) WHERE id = :id")
					.param("c", json.write(d == null ? null : d.get("cards"))).param("id", r.id()).update();
			case "MODE_CHANGED" -> {
				if (d != null && d.has("mode")) {
					jdbc.sql("""
							UPDATE app.conversations SET mode = :m,
							    consultation_id = COALESCE(CAST(:cid AS bigint), consultation_id) WHERE id = :id
							""").param("m", d.get("mode").asText())
							.param("cid", d.hasNonNull("consultationId") ? d.get("consultationId").asLong() : null)
							.param("id", r.conversationId()).update();
				}
			}
			case "APPROVAL_REQUIRED" -> jdbc.sql("""
					UPDATE app.ai_tasks SET status = 'WAITING_APPROVAL', pending_action = CAST(:p AS jsonb) WHERE id = :id
					""").param("p", json.write(d)).param("id", r.id()).update();
			case "DONE" -> jdbc.sql("""
					UPDATE app.ai_tasks SET status = 'DONE', answer = :a, sources = CAST(:s AS jsonb), finished_at = now()
					WHERE id = :id
					""").param("a", d != null && d.has("answer") ? d.get("answer").asText() : null)
					.param("s", json.write(d == null ? null : d.get("sources"))).param("id", r.id()).update();
			case "FAILED" -> jdbc.sql("""
					UPDATE app.ai_tasks SET status = 'FAILED', error = :err, finished_at = now() WHERE id = :id
					""").param("err", json.write(errorOf(d))).param("id", r.id()).update();
			default -> {
				// TOKEN, TOOL_START/END, TRIP_PLAN, MEMORY_PROPOSAL, VERIFY, CONVERSATION_OPENED: 중계만
				if ("QUEUED".equals(r.status())) {
					setStatus(r.id(), "RUNNING");
				}
			}
		}
	}

	private static Map<String, Object> errorOf(JsonNode d) {
		Map<String, Object> err = new LinkedHashMap<>();
		err.put("code", d != null && d.has("code") ? d.get("code").asText() : "AI_UNAVAILABLE");
		err.put("message", d != null && d.has("message") ? d.get("message").asText() : null);
		return err;
	}

	private void setStatus(UUID id, String status) {
		jdbc.sql("UPDATE app.ai_tasks SET status = :s WHERE id = :id AND status IN ('QUEUED','RUNNING')")
				.param("s", status).param("id", id).update();
	}

	/**
	 * 작업 실패 처리 (발행 실패·DLQ·시간 초과). 이미 끝난 작업은 그대로 둔다.
	 * backend 가 만든 FAILED 이벤트도 SSE 로 보낸다 (seq = 마지막 번호 + 1).
	 */
	public void fail(UUID taskId, String code, String message) {
		Integer seq = tx.execute(status -> jdbc.sql("""
				UPDATE app.ai_tasks SET status = 'FAILED', error = :err, finished_at = now(), updated_at = now(),
				    last_seq = last_seq + 1
				WHERE id = :id AND status IN ('QUEUED','RUNNING','WAITING_APPROVAL')
				RETURNING last_seq
				""").param("err", json.write(Map.of("code", code, "message", message))).param("id", taskId)
				.query(Integer.class).optional().orElse(null));
		if (seq != null) {
			ObjectNode data = json.mapper().createObjectNode();
			data.put("code", code);
			data.put("message", message);
			data.put("traceId", taskId.toString());
			AfterCommit.run(() -> hub.publish(taskId, new SseHub.Event(seq, "FAILED", data)));
		}
	}

	/** agent 가 응답 없이 멈춘 작업 정리 (기본 5분) */
	@Scheduled(fixedDelayString = "PT30S", initialDelayString = "PT30S")
	public void sweepStale() {
		List<UUID> stale = jdbc.sql("""
				SELECT id FROM app.ai_tasks WHERE status IN ('QUEUED','RUNNING') AND updated_at < :cutoff
				""").param("cutoff", OffsetDateTime.now().minus(app.ai().taskTimeout())).query(UUID.class).list();
		for (UUID id : stale) {
			fail(id, "AI_UNAVAILABLE", "AI task timed out");
		}
	}

	// ------------------------------------------------------------------ 공통

	private Row requireOwned(CurrentUser user, UUID taskId) {
		Row r = require(taskId);
		if (r.userId() != user.id() || user.role() != Role.CUSTOMER) {
			throw new ApiException(ErrorCode.ACCESS_DENIED);
		}
		return r;
	}

	private Row require(UUID taskId) {
		return jdbc.sql(select() + " WHERE id = :id").param("id", taskId).query((rs, i) -> row(rs)).optional()
				.orElseThrow(() -> ApiException.notFound("task"));
	}

	private static String select() {
		return """
				SELECT id, conversation_id, user_id, input, status, answer, sources::text AS sources,
				       pending_action::text AS pending_action, error, last_seq, created_at, finished_at
				FROM app.ai_tasks""";
	}

	private static Row row(ResultSet rs) throws SQLException {
		return new Row(rs.getObject("id", UUID.class), rs.getObject("conversation_id", UUID.class),
				rs.getLong("user_id"), rs.getString("input"), rs.getString("status"), rs.getString("answer"),
				rs.getString("sources"), rs.getString("pending_action"), rs.getString("error"), rs.getInt("last_seq"),
				Times.kst(rs.getObject("created_at", OffsetDateTime.class)),
				Times.kst(rs.getObject("finished_at", OffsetDateTime.class)));
	}

	private AiTask toDto(Row r) {
		JsonNode sources = json.read(r.sources());
		return new AiTask(r.id(), r.conversationId(), r.status(), r.input(), r.answer(),
				sources == null ? json.mapper().createArrayNode() : sources, json.read(r.pendingAction()),
				errorNode(r.error()), r.createdAt(), r.finishedAt());
	}

	/** error 컬럼은 {"code","message"} JSON 문자열. 예전 형식(일반 문자열)이면 message 로 감싼다 */
	private JsonNode errorNode(String error) {
		if (error == null) {
			return null;
		}
		try {
			JsonNode n = json.mapper().readTree(error);
			if (n.isObject()) {
				return n;
			}
		} catch (com.fasterxml.jackson.core.JsonProcessingException ignored) {
			// 문자열
		}
		return json.mapper().createObjectNode().put("code", "AI_UNAVAILABLE").put("message", error);
	}
}
