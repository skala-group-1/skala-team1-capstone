package com.skala.capstone.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.IntegrationTest;
import com.skala.capstone.common.messaging.Queues;

/**
 * AI 작업 흐름 (16 명세 6장, 13 문서 "I-4 BE ↔ agent 큐").
 * 실제 agent 대신 테스트가 가짜 agent 역할: ai.task.requested 를 꺼내 보고 ai.task.event 를 발행한다.
 */
class AiIntegrationTest extends IntegrationTest {

	@Test
	void conversationsMainHospitalAndParentConditions() throws Exception {
		String token = accessToken("customer.en2@demo.local");
		JsonNode main = body(mvc.perform(post("/api/ai/conversations").header(HttpHeaders.AUTHORIZATION, token)
				.contentType(MediaType.APPLICATION_JSON).content("{}"))
				.andExpect(status().isCreated()).andReturn());
		assertThat(main.get("mode").asText()).isEqualTo("MAIN");
		jdbc.sql("UPDATE app.conversations SET conditions = CAST(:c AS jsonb) WHERE id = :id")
				.param("c", "{\"procedureCode\":\"JAW_BOTOX\"}").param("id", UUID.fromString(main.get("id").asText()))
				.update();

		Map<String, Object> req = Map.of("hospitalId", 9, "parentConversationId", main.get("id").asText());
		JsonNode hospital = body(mvc.perform(post("/api/ai/conversations").header(HttpHeaders.AUTHORIZATION, token)
				.contentType(MediaType.APPLICATION_JSON).content(json(req)))
				.andExpect(status().isCreated()).andReturn());
		assertThat(hospital.get("mode").asText()).isEqualTo("HOSPITAL");
		assertThat(hospital.at("/hospital/id").asLong()).isEqualTo(9);
		assertThat(hospital.at("/conditions/procedureCode").asText()).isEqualTo("JAW_BOTOX");

		// 같은 병원 대화를 다시 열면 기존 것 (200)
		JsonNode again = body(mvc.perform(post("/api/ai/conversations").header(HttpHeaders.AUTHORIZATION, token)
				.contentType(MediaType.APPLICATION_JSON).content(json(req)))
				.andExpect(status().isOk()).andReturn());
		assertThat(again.get("id").asText()).isEqualTo(hospital.get("id").asText());

		// 다른 고객은 볼 수 없음, 상담사는 AI API 자체가 불가
		mvc.perform(get("/api/ai/conversations/{id}", main.get("id").asText())
				.header(HttpHeaders.AUTHORIZATION, accessToken("customer.en1@demo.local")))
				.andExpect(status().isForbidden());
		mvc.perform(get("/api/ai/conversations").header(HttpHeaders.AUTHORIZATION, accessToken("counselor.h2@demo.local")))
				.andExpect(status().isForbidden());
	}

	@Test
	void taskFlowRelaysEventsOverSseAndRebuildsHistory() throws Exception {
		String token = accessToken("customer.zh2@demo.local");
		String conversationId = newConversation(token);
		JsonNode task = createTask(token, conversationId, "双眼皮 江南 10/20~10/26");
		assertThat(task.get("status").asText()).isEqualTo("QUEUED");
		String taskId = task.get("id").asText();

		// 가짜 agent: 요청 수신 확인 (backend 가 토큰에서 꺼낸 사용자 정보 + 대화 정보)
		JsonNode requested = receiveFrom(Queues.AI_TASK_REQUESTED, b -> taskId.equals(b.path("taskId").asText()));
		assertThat(requested.at("/user/role").asText()).isEqualTo("CUSTOMER");
		assertThat(requested.at("/user/locale").asText()).isEqualTo("zh");
		assertThat(requested.at("/conversation/mode").asText()).isEqualTo("MAIN");

		// 같은 대화에 작업이 진행 중이면 새 작업 불가
		mvc.perform(post("/api/ai/tasks").header(HttpHeaders.AUTHORIZATION, token).contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("conversationId", conversationId, "message", "again"))))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.details.activeTaskId").value(taskId));

		CompletableFuture<List<String>> sse = openSse(token, taskId, null);
		Thread.sleep(300); // 구독이 붙을 시간
		event(taskId, 1, "STATUS", Map.of("status", "RUNNING"));
		event(taskId, 2, "TOKEN", Map.of("text", "正在"));
		event(taskId, 2, "TOKEN", Map.of("text", "중복")); // 같은 seq 재전송 → 무시
		event(taskId, 3, "CONDITIONS", Map.of("conditions", Map.of("procedureCode", "DOUBLE_EYELID_NONINCISION"),
				"missing", List.of()));
		event(taskId, 4, "RESULT_CARDS", Map.of("cards", List.of(Map.of("id", 1, "name", "道淡松")),
				"relaxOptions", List.of()));
		event(taskId, 5, "DONE", Map.of("answer", "找到 1 家医院", "sources", List.of()));

		List<String> lines = sse.get(10, TimeUnit.SECONDS);
		List<String> events = lines.stream().filter(l -> l.startsWith("event:")).map(l -> l.substring(6)).toList();
		assertThat(events).containsExactly("STATUS", "TOKEN", "CONDITIONS", "RESULT_CARDS", "DONE");
		assertThat(lines).contains("id:5");

		JsonNode done = body(mvc.perform(get("/api/ai/tasks/{id}", taskId).header(HttpHeaders.AUTHORIZATION, token))
				.andExpect(status().isOk()).andReturn());
		assertThat(done.get("status").asText()).isEqualTo("DONE");
		assertThat(done.get("answer").asText()).isEqualTo("找到 1 家医院");

		JsonNode conv = body(mvc.perform(get("/api/ai/conversations/{id}", conversationId)
				.header(HttpHeaders.AUTHORIZATION, token)).andReturn());
		assertThat(conv.at("/conditions/procedureCode").asText()).isEqualTo("DOUBLE_EYELID_NONINCISION");
		assertThat(conv.get("messages")).hasSize(2);
		assertThat(conv.at("/messages/1/role").asText()).isEqualTo("assistant");
		assertThat(conv.at("/messages/1/cards/0/id").asInt()).isEqualTo(1);

		// 끝난 작업에 다시 연결하면 버퍼 재생 후 바로 닫힘, Last-Event-ID 이후만
		List<String> replay = openSse(token, taskId, "4").get(5, TimeUnit.SECONDS);
		assertThat(replay.stream().filter(l -> l.startsWith("event:")).toList()).containsExactly("event:DONE");
	}

	@Test
	void approvalPausesAndResumesTheSameTask() throws Exception {
		String token = accessToken("customer.ja2@demo.local");
		String conversationId = newConversation(token);
		String taskId = createTask(token, conversationId, "予約したい").get("id").asText();
		receiveFrom(Queues.AI_TASK_REQUESTED, b -> taskId.equals(b.path("taskId").asText()));

		Map<String, Object> pending = new LinkedHashMap<>();
		pending.put("action", "CREATE_RESERVATION");
		pending.put("display", Map.of("title", "予約内容の確認", "rows", List.of()));
		pending.put("args", Map.of("slotId", 1));
		pending.put("editable", List.of("note"));
		event(taskId, 1, "APPROVAL_REQUIRED", pending);
		await(() -> "WAITING_APPROVAL".equals(taskStatus(taskId)), "WAITING_APPROVAL");

		// 수정 불가 항목 → 400, 수정 가능 항목만 → 202
		mvc.perform(post("/api/ai/tasks/{id}/approval", taskId).header(HttpHeaders.AUTHORIZATION, token)
				.contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("approved", true, "editedArgs", Map.of("slotId", 2)))))
				.andExpect(status().isBadRequest());
		mvc.perform(post("/api/ai/tasks/{id}/approval", taskId).header(HttpHeaders.AUTHORIZATION, token)
				.contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("approved", true, "editedArgs", Map.of("note", "午後希望")))))
				.andExpect(status().isAccepted())
				.andExpect(jsonPath("$.status").value("QUEUED"));
		JsonNode resume = receiveFrom(Queues.AI_TASK_RESUME, b -> taskId.equals(b.path("taskId").asText()));
		assertThat(resume.get("approved").asBoolean()).isTrue();
		assertThat(resume.at("/editedArgs/note").asText()).isEqualTo("午後希望");

		// 두 번 승인 불가
		mvc.perform(post("/api/ai/tasks/{id}/approval", taskId).header(HttpHeaders.AUTHORIZATION, token)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("approved", true))))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("TASK_NOT_WAITING_APPROVAL"));

		// 재연결(Last-Event-ID=1) 후 이어지는 이벤트 수신
		CompletableFuture<List<String>> sse = openSse(token, taskId, "1");
		Thread.sleep(300);
		event(taskId, 2, "DONE", Map.of("answer", "予約を申請しました", "sources", List.of()));
		assertThat(sse.get(10, TimeUnit.SECONDS)).contains("event:DONE");
	}

	@Test
	void deadLetterAndHumanModeAndOwnership() throws Exception {
		String token = accessToken("customer.ja1@demo.local");
		String conversationId = newConversation(token);
		String taskId = createTask(token, conversationId, "hello").get("id").asText();
		receiveFrom(Queues.AI_TASK_REQUESTED, b -> taskId.equals(b.path("taskId").asText()));

		// 남의 작업은 볼 수 없음
		mvc.perform(get("/api/ai/tasks/{id}", taskId).header(HttpHeaders.AUTHORIZATION,
				accessToken("customer.zh1@demo.local"))).andExpect(status().isForbidden());

		// agent 가 재시도 끝에 포기 → DLQ → FAILED
		rabbit.convertAndSend(Queues.EXCHANGE, Queues.AI_TASK_DLQ, Map.of("taskId", taskId));
		await(() -> "FAILED".equals(taskStatus(taskId)), "FAILED from DLQ");
		mvc.perform(get("/api/ai/tasks/{id}", taskId).header(HttpHeaders.AUTHORIZATION, token))
				.andExpect(jsonPath("$.error.code").value("AI_UNAVAILABLE"));

		// 상담사 연결 중(HUMAN)이면 AI 작업 불가
		jdbc.sql("UPDATE app.conversations SET mode = 'HUMAN' WHERE id = :id").param("id", UUID.fromString(conversationId))
				.update();
		mvc.perform(post("/api/ai/tasks").header(HttpHeaders.AUTHORIZATION, token).contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("conversationId", conversationId, "message", "hi"))))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.details.from").value("HUMAN"));
	}

	// ------------------------------------------------------------------ helpers

	private String newConversation(String token) throws Exception {
		return body(mvc.perform(post("/api/ai/conversations").header(HttpHeaders.AUTHORIZATION, token)
				.contentType(MediaType.APPLICATION_JSON).content("{}")).andReturn()).get("id").asText();
	}

	private JsonNode createTask(String token, String conversationId, String message) throws Exception {
		return body(mvc.perform(post("/api/ai/tasks").header(HttpHeaders.AUTHORIZATION, token)
				.contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("conversationId", conversationId, "message", message))))
				.andExpect(status().isAccepted()).andReturn());
	}

	private void event(String taskId, int seq, String event, Object data) {
		rabbit.convertAndSend(Queues.EXCHANGE, Queues.AI_TASK_EVENT,
				Map.of("taskId", taskId, "seq", seq, "event", event, "data", data, "at", "2026-10-20T10:00:00+09:00"));
	}

	private String taskStatus(String taskId) {
		return jdbc.sql("SELECT status FROM app.ai_tasks WHERE id = :id").param("id", UUID.fromString(taskId))
				.query(String.class).single();
	}

	/** 실제 HTTP 로 SSE 를 열고, 스트림이 닫힐 때까지 받은 줄을 모은다 */
	private CompletableFuture<List<String>> openSse(String token, String taskId, String lastEventId) {
		HttpRequest.Builder b = HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/api/ai/tasks/" + taskId + "/stream"))
				.header("Authorization", token).header("Accept", "text/event-stream");
		if (lastEventId != null) {
			b.header("Last-Event-ID", lastEventId);
		}
		return HttpClient.newHttpClient().sendAsync(b.build(), HttpResponse.BodyHandlers.ofLines())
				.thenApply(r -> {
					assertThat(r.statusCode()).isEqualTo(200);
					List<String> out = new ArrayList<>();
					r.body().forEach(out::add);
					return out;
				});
	}
}
