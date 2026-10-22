package com.skala.capstone.catalog;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.IntegrationTest;
import com.skala.capstone.common.messaging.Queues;

/** 리뷰 번역: seed 번역본 노출, translator 결과(review.translated) 저장. */
class ReviewTranslationIntegrationTest extends IntegrationTest {

	@Test
	void reviewListCarriesViewerLanguageTranslation() throws Exception {
		JsonNode page = body(mvc.perform(get("/api/hospitals/{id}/reviews", 1).param("size", "50")
				.header(HttpHeaders.AUTHORIZATION, accessToken("customer.ja2@demo.local")))
				.andExpect(status().isOk()).andReturn());
		int translated = 0;
		for (JsonNode r : page.get("items")) {
			if ("ja".equals(r.get("lang").asText())) {
				assertThat(r.get("translatedContent").isNull()).isTrue(); // 이미 내 언어
			} else if (r.hasNonNull("translatedContent")) {
				translated++;
				assertThat(r.get("translatedContent").asText()).isNotEqualTo(r.get("content").asText());
			}
		}
		assertThat(translated).isPositive();
		// 원문 수는 그대로 (번역본이 리뷰 행을 늘리지 않음)
		long reviews = jdbc.sql("SELECT count(*) FROM app.reviews WHERE hospital_id = 1").query(Long.class).single();
		assertThat(page.get("total").asLong()).isLessThanOrEqualTo(reviews);
	}

	@Test
	void translatedResultIsStoredAndSourceLanguageCorrected() throws Exception {
		// 화면 언어는 en 이었지만 실제로는 한국어로 쓴 리뷰
		long id = jdbc.sql("""
				INSERT INTO app.reviews (hospital_id, procedure_code, rating, lang, content)
				VALUES (2, (SELECT procedure_code FROM app.price_options WHERE hospital_id = 2 LIMIT 1), 5, 'en',
				        '상담이 친절했어요.') RETURNING id
				""").query(Long.class).single();
		rabbit.convertAndSend(Queues.EXCHANGE, Queues.REVIEW_TRANSLATED, Map.of("reviewId", id, "ok", true,
				"detectedLang", "ko", "translations",
				Map.of("en", "The consultation was kind.", "zh", "咨询很亲切。", "ja", "カウンセリングが親切でした。",
						"ko", "무시돼야 함")));
		await(() -> count(id) == 3, "review translations stored");
		assertThat(jdbc.sql("SELECT lang FROM app.reviews WHERE id = :id").param("id", id).query(String.class)
				.single()).isEqualTo("ko");
		assertThat(jdbc.sql("SELECT content FROM app.review_translations WHERE review_id = :id AND lang = 'en'")
				.param("id", id).query(String.class).single()).isEqualTo("The consultation was kind.");

		// 실패 결과는 아무것도 바꾸지 않는다
		rabbit.convertAndSend(Queues.EXCHANGE, Queues.REVIEW_TRANSLATED,
				Map.of("reviewId", id, "ok", false, "error", "LLM timeout"));
		Thread.sleep(500);
		assertThat(count(id)).isEqualTo(3);
	}

	private long count(long reviewId) {
		return jdbc.sql("SELECT count(*) FROM app.review_translations WHERE review_id = :id").param("id", reviewId)
				.query(Long.class).single();
	}
}
