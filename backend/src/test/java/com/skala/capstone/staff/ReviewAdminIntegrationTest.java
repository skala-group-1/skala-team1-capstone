package com.skala.capstone.staff;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.Map;
import java.util.stream.StreamSupport;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.IntegrationTest;
import com.skala.capstone.common.messaging.Queues;

/** 병원 관리자 리뷰 관리. 시드 리뷰는 다른 테스트가 세므로 숨김·답글은 새로 넣은 리뷰(병원 2)로만 한다. */
class ReviewAdminIntegrationTest extends IntegrationTest {

	private long insertReview(String lang, String content, int rating) {
		return jdbc.sql("""
				INSERT INTO app.reviews (hospital_id, procedure_code, rating, age_group, gender, reviewer_nationality, lang, content)
				VALUES (2, (SELECT procedure_code FROM app.price_options WHERE hospital_id = 2 LIMIT 1), :r, '30s', 'F', 'CN',
				        :lang, :c) RETURNING id
				""").param("r", rating).param("lang", lang).param("c", content).query(Long.class).single();
	}

	/** 고객이 보는 병원 2 리뷰 최신 50개 중 id 로 찾기 (없으면 null) */
	private JsonNode customerView(String token, long id) throws Exception {
		JsonNode page = body(mvc.perform(get("/api/hospitals/2/reviews").param("size", "50")
				.header(HttpHeaders.AUTHORIZATION, token)).andExpect(status().isOk()).andReturn());
		return StreamSupport.stream(page.get("items").spliterator(), false)
				.filter(r -> r.get("id").asLong() == id).findFirst().orElse(null);
	}

	private long visibleCount() {
		return jdbc.sql("SELECT review_count FROM app.hospital_review_stats WHERE hospital_id = 2").query(Long.class)
				.single();
	}

	@Test
	void listSummaryIsConsistentAndScoped() throws Exception {
		String admin = accessToken("admin.h2@demo.local");
		JsonNode page = body(mvc.perform(get("/api/hospital-admin/reviews").param("size", "5")
				.header(HttpHeaders.AUTHORIZATION, admin)).andExpect(status().isOk()).andReturn());
		JsonNode summary = page.get("summary");
		assertThat(page.get("items").size()).isLessThanOrEqualTo(5);
		long byRating = 0;
		for (JsonNode n : summary.get("byRating")) {
			byRating += n.asLong();
		}
		assertThat(byRating).isEqualTo(summary.get("reviewCount").asLong());
		assertThat(page.at("/items/0/procedureName").asText()).isNotBlank();

		JsonNode low = body(mvc.perform(get("/api/hospital-admin/reviews").param("filter", "LOW").param("sort", "RATING_LOW")
				.header(HttpHeaders.AUTHORIZATION, admin)).andExpect(status().isOk()).andReturn());
		low.get("items").forEach(r -> assertThat(r.get("rating").asInt()).isLessThanOrEqualTo(2));

		mvc.perform(get("/api/hospital-admin/reviews").param("filter", "NOPE").header(HttpHeaders.AUTHORIZATION, admin))
				.andExpect(status().isBadRequest());
		mvc.perform(get("/api/hospital-admin/reviews").header(HttpHeaders.AUTHORIZATION, accessToken("counselor.h2@demo.local")))
				.andExpect(status().isForbidden());

		// 다른 병원 리뷰는 못 건드린다
		long id = insertReview("ko", "다른 병원 관리자 테스트", 4);
		mvc.perform(put("/api/hospital-admin/reviews/{id}/reply", id)
				.header(HttpHeaders.AUTHORIZATION, accessToken("admin.h3@demo.local"))
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("content", "x"))))
				.andExpect(status().isNotFound());
	}

	@Test
	void replyIsTranslatedAndShownToCustomer() throws Exception {
		String admin = accessToken("admin.h2@demo.local");
		String zhCustomer = accessToken("customer.zh1@demo.local");
		long id = insertReview("zh", "朋友推荐来做的，效果很自然。", 5);

		mvc.perform(put("/api/hospital-admin/reviews/{id}/reply", id).header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("content", " "))))
				.andExpect(status().isBadRequest());
		mvc.perform(put("/api/hospital-admin/reviews/{id}/reply", id).header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("content", "소중한 후기 감사합니다."))))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.reply.content").value("소중한 후기 감사합니다."))
				.andExpect(jsonPath("$.reply.lang").value("ko"));

		// backend → translator: 같은 review.translate 큐, kind = REPLY
		JsonNode req = receiveFrom(Queues.REVIEW_TRANSLATE,
				m -> m.get("reviewId").asLong() == id && "REPLY".equals(m.path("kind").asText()));
		assertThat(req.get("text").asText()).isEqualTo("소중한 후기 감사합니다.");

		// 번역 전: 고객은 원문만
		assertThat(customerView(zhCustomer, id).at("/reply/translatedContent").isNull()).isTrue();

		rabbit.convertAndSend(Queues.EXCHANGE, Queues.REVIEW_TRANSLATED, Map.of("reviewId", id, "ok", true, "kind", "REPLY",
				"detectedLang", "ko", "translations", Map.of("zh", "感谢您的宝贵评价。", "en", "Thank you.", "ja", "ありがとう。")));
		await(() -> replyTranslations(id) == 3, "reply translations stored");
		JsonNode seen = customerView(zhCustomer, id);
		assertThat(seen.at("/reply/content").asText()).isEqualTo("소중한 후기 감사합니다.");
		assertThat(seen.at("/reply/translatedContent").asText()).isEqualTo("感谢您的宝贵评价。");
		// 답글 번역이 리뷰 번역에 섞이지 않는다
		assertThat(jdbc.sql("SELECT count(*) FROM app.review_translations WHERE review_id = :id").param("id", id)
				.query(Long.class).single()).isZero();

		// 고치면 이전 번역은 지운다
		mvc.perform(put("/api/hospital-admin/reviews/{id}/reply", id).header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("content", "다시 방문해 주세요."))))
				.andExpect(status().isOk()).andExpect(jsonPath("$.reply.translations").isEmpty());
		assertThat(replyTranslations(id)).isZero();

		mvc.perform(delete("/api/hospital-admin/reviews/{id}/reply", id).header(HttpHeaders.AUTHORIZATION, admin))
				.andExpect(status().isNoContent());
		assertThat(customerView(zhCustomer, id).get("reply").isNull()).isTrue();
	}

	@Test
	void hiddenReviewLeavesCustomerListAndStats() throws Exception {
		String admin = accessToken("admin.h2@demo.local");
		String customer = accessToken("customer.zh1@demo.local");
		long id = insertReview("zh", "广告 www.example.com", 1);
		long before = visibleCount();
		assertThat(customerView(customer, id)).isNotNull();

		mvc.perform(post("/api/hospital-admin/reviews/{id}/hide", id).header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("reason", "OTHER"))))
				.andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("VALIDATION_FAILED"));
		mvc.perform(post("/api/hospital-admin/reviews/{id}/hide", id).header(HttpHeaders.AUTHORIZATION, admin)
				.contentType(MediaType.APPLICATION_JSON).content(json(Map.of("reason", "SPAM", "detail", "광고 링크"))))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.hidden.reason").value("SPAM"))
				.andExpect(jsonPath("$.hidden.detail").value("광고 링크"));

		assertThat(customerView(customer, id)).isNull();
		assertThat(visibleCount()).isEqualTo(before - 1);
		JsonNode hidden = body(mvc.perform(get("/api/hospital-admin/reviews").param("filter", "HIDDEN").param("size", "50")
				.header(HttpHeaders.AUTHORIZATION, admin)).andExpect(status().isOk()).andReturn());
		assertThat(hidden.get("items").findValues("id").stream().map(JsonNode::asLong)).contains(id);
		assertThat(hidden.at("/summary/hidden").asLong()).isPositive();

		mvc.perform(post("/api/hospital-admin/reviews/{id}/unhide", id).header(HttpHeaders.AUTHORIZATION, admin))
				.andExpect(status().isOk()).andExpect(jsonPath("$.hidden").isEmpty());
		assertThat(customerView(customer, id)).isNotNull();
		assertThat(visibleCount()).isEqualTo(before);
	}

	private long replyTranslations(long reviewId) {
		return jdbc.sql("SELECT count(*) FROM app.review_reply_translations WHERE review_id = :id").param("id", reviewId)
				.query(Long.class).single();
	}
}
