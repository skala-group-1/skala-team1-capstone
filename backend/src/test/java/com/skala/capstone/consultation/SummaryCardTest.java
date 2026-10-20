package com.skala.capstone.consultation;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

/** 요약 카드가 예전 mock 모양이어도 「공통 계약서」 SummaryCard 키가 모두 채워지는지. */
class SummaryCardTest {

	private final ObjectMapper mapper = new ObjectMapper();

	@Test
	void legacySeedCardIsMappedToContractShape() throws Exception {
		JsonNode legacy = mapper.readTree("""
				{"concerns":["효과 지속 기간","일본어 통역"],"language":"ja","procedure_code":"JAW_BOTOX",
				 "procedure_name":"사각턱 보톡스","preferred_areas":["강남"],"preferred_dates":["2026-10-23","2026-10-23"]}
				""");
		JsonNode card = ConsultationService.summaryCard(legacy, "ja");
		assertThat(card.get("procedure").asText()).isEqualTo("사각턱 보톡스");
		assertThat(card.get("preferredDates").asText()).isEqualTo("2026-10-23");
		assertThat(card.get("stayDays").isNull()).isTrue();
		assertThat(card.get("budget").isNull()).isTrue();
		assertThat(card.get("questions")).hasSize(2);
		assertThat(card.get("customerLocale").asText()).isEqualTo("ja");
	}

	@Test
	void contractCardIsKeptAsIs() throws Exception {
		JsonNode contract = mapper.readTree("""
				{"procedure":"Jaw Botox","preferredDates":"10/23~10/25","stayDays":5,"budget":"300,000 KRW",
				 "questions":["Pain?"],"customerLocale":"en"}
				""");
		assertThat(ConsultationService.summaryCard(contract, "en")).isEqualTo(contract);
	}

	@Test
	void missingCardBecomesEmptyContractCard() {
		JsonNode card = ConsultationService.summaryCard(null, "zh");
		assertThat(card.get("procedure").asText()).isEmpty();
		assertThat(card.get("questions")).isEmpty();
		assertThat(card.get("customerLocale").asText()).isEqualTo("zh");
	}
}
