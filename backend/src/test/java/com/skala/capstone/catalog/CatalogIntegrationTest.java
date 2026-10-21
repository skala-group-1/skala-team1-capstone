package com.skala.capstone.catalog;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.IntegrationTest;
import com.skala.capstone.common.config.AppProperties;

class CatalogIntegrationTest extends IntegrationTest {

	@Autowired
	AppProperties app;

	String zhCustomer;

	@BeforeEach
	void setUp() throws Exception {
		zhCustomer = accessToken("customer.zh1@demo.local");
	}

	@Test
	void proceduresAreLocalized() throws Exception {
		JsonNode list = body(mvc.perform(get("/api/procedures").header(HttpHeaders.AUTHORIZATION, zhCustomer))
				.andExpect(status().isOk()).andReturn());
		assertThat(list).hasSize(18);
		JsonNode jaw = find(list, "code", "JAW_BOTOX");
		assertThat(jaw.get("name").asText()).isEqualTo("瘦脸针");
		assertThat(jaw.get("downtimeDays").asInt()).isZero();
	}

	/**
	 * mock README 페르소나: 중국어·쌍꺼풀(DOUBLE_EYELID_*)·강남/명동 → 병원 1, 7, 11, 12, 15, 41, 48, 49.
	 * 비절개(NONINCISION)만 보면 그중 일부(15, 48 제외)다.
	 */
	@Test
	void personaSearchFindsMatchingHospitals() throws Exception {
		JsonNode page = body(mvc.perform(get("/api/hospitals/search").header(HttpHeaders.AUTHORIZATION, zhCustomer)
				.param("procedure", "DOUBLE_EYELID_NONINCISION")
				.param("areas", "GANGNAM", "MYEONGDONG")
				.param("language", "zh"))
				.andExpect(status().isOk()).andReturn());
		List<Long> ids = new ArrayList<>();
		long prevReviews = Long.MAX_VALUE;
		for (JsonNode card : page.get("items")) {
			ids.add(card.get("id").asLong());
			assertThat(card.get("areaCode").asText()).isIn("GANGNAM", "MYEONGDONG");
			assertThat(card.get("languages").toString()).contains("\"zh\"");
			assertThat(card.get("minPriceKrw").isNull()).isFalse();
			long reviews = card.get("reviewCount").asLong();
			assertThat(reviews).isLessThanOrEqualTo(prevReviews);
			prevReviews = reviews;
		}
		assertThat(ids).containsExactlyInAnyOrder(1L, 7L, 11L, 12L, 41L, 49L);
		assertThat(page.get("total").asLong()).isEqualTo(6);
	}

	@Test
	void searchSortsByPriceAndPaginates() throws Exception {
		JsonNode page = body(mvc.perform(get("/api/hospitals/search").header(HttpHeaders.AUTHORIZATION, zhCustomer)
				.param("procedure", "JAW_BOTOX").param("sort", "PRICE").param("size", "5"))
				.andExpect(status().isOk()).andReturn());
		assertThat(page.get("items")).hasSize(5);
		assertThat(page.get("total").asLong()).isGreaterThan(5);
		int prev = 0;
		for (JsonNode card : page.get("items")) {
			assertThat(card.get("minPriceKrw").asInt()).isGreaterThanOrEqualTo(prev);
			prev = card.get("minPriceKrw").asInt();
		}
	}

	@Test
	void searchWithDistanceSortReturnsDistances() throws Exception {
		JsonNode page = body(mvc.perform(get("/api/hospitals/search").header(HttpHeaders.AUTHORIZATION, zhCustomer)
				.param("sort", "DISTANCE").param("lat", "37.5636").param("lng", "126.9827"))
				.andExpect(status().isOk()).andReturn());
		double prev = 0;
		for (JsonNode card : page.get("items")) {
			assertThat(card.get("distanceKm").asDouble()).isGreaterThanOrEqualTo(prev);
			prev = card.get("distanceKm").asDouble();
		}
	}

	@Test
	void unknownProcedureReturnsCandidates() throws Exception {
		mvc.perform(get("/api/hospitals/search").header(HttpHeaders.AUTHORIZATION, zhCustomer)
				.param("procedure", "BOTOX"))
				.andExpect(status().isUnprocessableEntity())
				.andExpect(jsonPath("$.code").value("UNKNOWN_PROCEDURE"))
				.andExpect(jsonPath("$.details.candidates[0].code").exists());
	}

	@Test
	void invalidAreaIsValidationFailed() throws Exception {
		mvc.perform(get("/api/hospitals/search").header(HttpHeaders.AUTHORIZATION, zhCustomer)
				.param("areas", "BUSAN"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("VALIDATION_FAILED"));
	}

	@Test
	void hospitalDetailHasDoctorsProceduresAndStats() throws Exception {
		JsonNode d = body(mvc.perform(get("/api/hospitals/1").header(HttpHeaders.AUTHORIZATION, zhCustomer))
				.andExpect(status().isOk()).andReturn());
		assertThat(d.get("name").asText()).isEqualTo("道淡松整形皮肤科诊所");
		assertThat(d.get("nameKo").asText()).isNotBlank();
		assertThat(d.get("doctors").size()).isGreaterThan(0);
		assertThat(d.at("/doctors/0/title").asText()).isEqualTo("代表院长");
		assertThat(d.get("procedures").size()).isGreaterThan(0);
		assertThat(d.at("/procedures/0/options/0/priceKrw").asInt()).isPositive();
		assertThat(d.at("/reviewStats/reviewCount").asLong()).isPositive();
		List<String> days = new ArrayList<>();
		d.get("openHours").fieldNames().forEachRemaining(days::add);
		assertThat(days).containsExactly("mon", "tue", "wed", "thu", "fri", "sat", "sun");
	}

	@Test
	void doctorTitlesFollowResponseLanguage() throws Exception {
		JsonNode en = body(mvc.perform(get("/api/hospitals/1")
				.header(HttpHeaders.AUTHORIZATION, accessToken("customer.en1@demo.local"))).andExpect(status().isOk()).andReturn())
				.get("doctors");
		JsonNode ko = body(mvc.perform(get("/api/hospitals/1")
				.header(HttpHeaders.AUTHORIZATION, accessToken("counselor.h1@demo.local"))).andExpect(status().isOk()).andReturn())
				.get("doctors");
		assertThat(en.get(0).get("title").asText()).isEqualTo("Chief Director");
		assertThat(ko.get(0).get("title").asText()).isEqualTo("대표원장");
		for (JsonNode doctor : en) {
			assertThat(doctor.get("title").asText()).isIn("Chief Director", "Director", "Associate Director");
		}
	}

	@Test
	void slotsAreAvailableAndOrdered() throws Exception {
		JsonNode slots = body(mvc.perform(get("/api/hospitals/1/slots").header(HttpHeaders.AUTHORIZATION, zhCustomer)
				.param("procedure", "DOUBLE_EYELID_NONINCISION").param("limit", "10"))
				.andExpect(status().isOk()).andReturn());
		assertThat(slots.size()).isBetween(1, 10);
		OffsetDateTime prev = OffsetDateTime.MIN;
		for (JsonNode s : slots) {
			assertThat(s.get("status").asText()).isEqualTo("AVAILABLE");
			assertThat(s.get("startAt").asText()).endsWith("+09:00");
			OffsetDateTime start = OffsetDateTime.parse(s.get("startAt").asText());
			assertThat(start).isAfterOrEqualTo(prev);
			prev = start;
		}
	}

	@Test
	void reviewsArePagedAndFilteredByLang() throws Exception {
		JsonNode page = body(mvc.perform(get("/api/hospitals/1/reviews").header(HttpHeaders.AUTHORIZATION, zhCustomer)
				.param("lang", "zh").param("size", "3"))
				.andExpect(status().isOk()).andReturn());
		assertThat(page.get("items").size()).isLessThanOrEqualTo(3);
		for (JsonNode r : page.get("items")) {
			assertThat(r.get("lang").asText()).isEqualTo("zh");
		}
	}

	@Test
	void compareKeepsRequestedOrder() throws Exception {
		JsonNode res = body(mvc.perform(post("/api/hospitals/compare").header(HttpHeaders.AUTHORIZATION, zhCustomer)
				.contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("hospitalIds", List.of(7, 1, 11), "procedure", "DOUBLE_EYELID_NONINCISION"))))
				.andExpect(status().isOk()).andReturn());
		assertThat(res.get("procedureCode").asText()).isEqualTo("DOUBLE_EYELID_NONINCISION");
		assertThat(res.at("/columns/0/hospital/id").asLong()).isEqualTo(7);
		assertThat(res.at("/columns/1/hospital/id").asLong()).isEqualTo(1);
		assertThat(res.at("/columns/2/options").size()).isPositive();
	}

	@Test
	void internalSearchUsesConditionsNamesAndActingUserLocale() throws Exception {
		JsonNode res = body(mvc.perform(get("/internal/hospitals/search")
				.header("X-Service-Token", app.serviceToken()).header("X-Acting-User-Id", "3")
				.param("procedureCode", "DOUBLE_EYELID_NONINCISION").param("areas", "GANGNAM,MYEONGDONG")
				.param("consultLanguage", "zh").param("limit", "3"))
				.andExpect(status().isOk()).andReturn());
		assertThat(res.get("items")).hasSize(3);
		assertThat(res.get("total").asLong()).isEqualTo(6);
		// acting user 3 = customer.zh1 → 중국어 이름
		assertThat(res.at("/items/0/name").asText()).matches(".*[\\u4e00-\\u9fff].*");
	}

	@Test
	void internalNormalizeFindsKoreanSynonym() throws Exception {
		mvc.perform(get("/internal/procedures/normalize").param("text", "사각턱 보톡스")
				.header("X-Service-Token", app.serviceToken()).header("X-Acting-User-Id", "1"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.candidates[0].code").value("JAW_BOTOX"))
				.andExpect(jsonPath("$.candidates[0].score").value(1.0));
	}

	@Test
	void internalSlotsAreCappedAt20() throws Exception {
		JsonNode slots = body(mvc.perform(get("/internal/hospitals/1/slots")
				.header("X-Service-Token", app.serviceToken()).header("X-Acting-User-Id", "1"))
				.andExpect(status().isOk()).andReturn());
		assertThat(slots.size()).isEqualTo(20);
	}

	private static JsonNode find(JsonNode array, String field, String value) {
		for (JsonNode n : array) {
			if (value.equals(n.get(field).asText())) {
				return n;
			}
		}
		throw new AssertionError(field + "=" + value + " not found");
	}
}
