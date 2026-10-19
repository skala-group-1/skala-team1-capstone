package com.skala.capstone.ops;

import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.ai.AiDtos.AiTaskWithUser;
import com.skala.capstone.ai.AiTaskService;
import com.skala.capstone.common.web.Json;
import com.skala.capstone.common.web.PageResponse;
import com.skala.capstone.common.web.Times;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/** 운영자 화면 (URL 규칙으로 OPERATOR 만): 감사 로그, 실패한 AI 작업 추적 */
@Tag(name = "Operator")
@Validated
@RestController
@RequestMapping("/api/ops")
public class OpsController {

	public record AuditLog(long id, String traceId, Long actorId, String actorRole, String action, String target,
			JsonNode detail, OffsetDateTime createdAt) {
	}

	private final JdbcClient jdbc;
	private final Json json;
	private final AiTaskService tasks;

	public OpsController(JdbcClient jdbc, Json json, AiTaskService tasks) {
		this.jdbc = jdbc;
		this.json = json;
		this.tasks = tasks;
	}

	@Operation(summary = "감사 로그 (최신순, action 필터: LOGIN_FAILED, ACCESS_DENIED ...)")
	@GetMapping("/audit-logs")
	public PageResponse<AuditLog> auditLogs(@RequestParam(required = false) String action,
			@RequestParam(defaultValue = "0") @Min(0) int page,
			@RequestParam(defaultValue = "20") @Min(1) @Max(50) int size) {
		String where = action == null ? "" : " WHERE action = :a";
		Map<String, Object> p = new LinkedHashMap<>();
		if (action != null) {
			p.put("a", action);
		}
		long total = jdbc.sql("SELECT count(*) FROM app.audit_logs" + where).params(p).query(Long.class).single();
		p.put("l", size);
		p.put("o", (long) page * size);
		List<AuditLog> items = jdbc.sql("SELECT *, detail::text AS detail_json FROM app.audit_logs" + where
				+ " ORDER BY created_at DESC, id DESC LIMIT :l OFFSET :o").params(p)
				.query((rs, i) -> new AuditLog(rs.getLong("id"), rs.getString("trace_id"),
						(Long) rs.getObject("actor_id"), rs.getString("actor_role"), rs.getString("action"),
						rs.getString("target"), json.read(rs.getString("detail_json")),
						Times.kst(rs.getObject("created_at", OffsetDateTime.class))))
				.list();
		return new PageResponse<>(items, page, size, total);
	}

	@Operation(summary = "AI 작업 목록 (status=FAILED 로 실패 작업 추적)")
	@GetMapping("/ai-tasks")
	public PageResponse<AiTaskWithUser> aiTasks(@RequestParam(required = false) String status,
			@RequestParam(defaultValue = "0") @Min(0) int page,
			@RequestParam(defaultValue = "20") @Min(1) @Max(50) int size) {
		return tasks.forOperator(status, page, size);
	}
}
