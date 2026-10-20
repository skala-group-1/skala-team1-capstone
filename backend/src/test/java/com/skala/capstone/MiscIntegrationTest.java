package com.skala.capstone;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;

/** 알림 읽음, 언어 변경, 운영자 API, 문서 원문(agent 없음 → 503) */
class MiscIntegrationTest extends IntegrationTest {

	@Test
	void notificationsReadAndOwnership() throws Exception {
		long mine = jdbc.sql("""
				INSERT INTO app.notifications (user_id, type, payload) VALUES (4, 'RESERVATION_CONFIRMED', '{"reservationId": 1}')
				RETURNING id""").query(Long.class).single();
		String token = accessToken("customer.zh2@demo.local");
		mvc.perform(get("/api/notifications").param("unreadOnly", "true").header(HttpHeaders.AUTHORIZATION, token))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.items[?(@.id == " + mine + ")].payload.reservationId").value(1));
		// 남의 알림 → 403
		mvc.perform(post("/api/notifications/{id}/read", mine)
				.header(HttpHeaders.AUTHORIZATION, accessToken("customer.en1@demo.local")))
				.andExpect(status().isForbidden());
		mvc.perform(post("/api/notifications/{id}/read", mine).header(HttpHeaders.AUTHORIZATION, token))
				.andExpect(status().isNoContent());
		mvc.perform(post("/api/notifications/read-all").header(HttpHeaders.AUTHORIZATION, token))
				.andExpect(status().isNoContent());
		mvc.perform(get("/api/notifications").param("unreadOnly", "true").header(HttpHeaders.AUTHORIZATION, token))
				.andExpect(jsonPath("$.total").value(0));
	}

	@Test
	void customerCanChangeLocaleWithinAllowedSet() throws Exception {
		String token = accessToken("customer.en2@demo.local");
		mvc.perform(patch("/api/me").header(HttpHeaders.AUTHORIZATION, token).contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("locale", "fr")))).andExpect(status().isBadRequest());
		// 고객도 한국어 선택 가능 (D-43)
		mvc.perform(patch("/api/me").header(HttpHeaders.AUTHORIZATION, token).contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("locale", "ko")))).andExpect(status().isOk()).andExpect(jsonPath("$.locale").value("ko"));
		mvc.perform(patch("/api/me").header(HttpHeaders.AUTHORIZATION, token).contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("locale", "ja")))).andExpect(status().isOk()).andExpect(jsonPath("$.locale").value("ja"));
		mvc.perform(patch("/api/me").header(HttpHeaders.AUTHORIZATION, token).contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("locale", "en")))).andExpect(status().isOk());
	}

	@Test
	void operatorApisAreOperatorOnly() throws Exception {
		String operator = accessToken("operator@demo.local");
		mvc.perform(get("/api/ops/audit-logs").param("action", "LOGIN_SUCCESS").header(HttpHeaders.AUTHORIZATION, operator))
				.andExpect(status().isOk()).andExpect(jsonPath("$.items[0].action").value("LOGIN_SUCCESS"));
		mvc.perform(get("/api/ops/ai-tasks").param("status", "FAILED").header(HttpHeaders.AUTHORIZATION, operator))
				.andExpect(status().isOk()).andExpect(jsonPath("$.items").isArray());
		mvc.perform(get("/api/ops/audit-logs").header(HttpHeaders.AUTHORIZATION, accessToken("admin.h1@demo.local")))
				.andExpect(status().isForbidden());
	}

	@Test
	void docsReturn503WhenAgentIsDown() throws Exception {
		String token = accessToken("customer.en1@demo.local");
		mvc.perform(get("/api/docs/guide-double-eyelid").param("section", "recovery-downtime")
				.header(HttpHeaders.AUTHORIZATION, token))
				.andExpect(status().isServiceUnavailable())
				.andExpect(jsonPath("$.code").value("AI_UNAVAILABLE"));
		mvc.perform(get("/api/docs/{id}", "bad id!").header(HttpHeaders.AUTHORIZATION, token))
				.andExpect(status().isNotFound());
	}
}
