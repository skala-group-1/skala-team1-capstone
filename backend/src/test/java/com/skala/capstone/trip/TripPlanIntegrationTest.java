package com.skala.capstone.trip;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import com.fasterxml.jackson.databind.JsonNode;
import com.skala.capstone.IntegrationTest;
import com.skala.capstone.common.web.Times;

/** 일정 적합성 계산 (03 문서 9-2, 16 명세 8장) */
class TripPlanIntegrationTest extends IntegrationTest {

	@Test
	void computesRecoveryAndBufferPerHospital() throws Exception {
		LocalDate today = LocalDate.now(Times.SEOUL);
		String procedure = "DOUBLE_EYELID_INCISION";
		int downtime = jdbc.sql("SELECT downtime_days FROM app.procedures WHERE code = :c").param("c", procedure)
				.query(Integer.class).single();
		List<Long> offering = jdbc.sql("""
				SELECT DISTINCT hospital_id FROM app.price_options WHERE procedure_code = :c ORDER BY hospital_id LIMIT 2
				""").param("c", procedure).query(Long.class).list();
		long notOffering = jdbc.sql("""
				SELECT id FROM app.hospitals h WHERE NOT EXISTS
				  (SELECT 1 FROM app.price_options p WHERE p.hospital_id = h.id AND p.procedure_code = :c)
				ORDER BY id LIMIT 1
				""").param("c", procedure).query(Long.class).single();

		// 짧은 체류: 회복이 출국 뒤에 끝남
		JsonNode shortStay = plan(procedure, List.of(offering.get(0), notOffering), today.plusDays(1), today.plusDays(3));
		JsonNode first = shortStay.at("/plans/0");
		assertThat(first.get("hospitalId").asLong()).isEqualTo(offering.get(0));
		assertThat(first.get("downtimeDays").asInt()).isEqualTo(downtime);
		if (first.get("slot").isNull()) {
			assertThat(first.get("reason").asText()).isEqualTo("NO_SLOT_BEFORE_DEPARTURE");
		} else {
			LocalDate day = LocalDate.parse(first.at("/slot/startAt").asText().substring(0, 10));
			LocalDate recovery = LocalDate.parse(first.get("recoveryEndDate").asText());
			assertThat(recovery).isEqualTo(day.plusDays(downtime));
			assertThat(first.get("bufferDays").asInt())
					.isEqualTo((int) ChronoUnit.DAYS.between(recovery, today.plusDays(3)));
			assertThat(first.get("feasible").asBoolean()).isFalse();
			assertThat(first.get("reason").asText()).isEqualTo("RECOVERY_AFTER_DEPARTURE");
		}
		assertThat(shortStay.at("/plans/1/reason").asText()).isEqualTo("PROCEDURE_NOT_OFFERED");

		// 긴 체류(다운타임 + 넉넉히): 가능
		JsonNode longStay = plan(procedure, offering, today.plusDays(1), today.plusDays(downtime + 20));
		boolean anyFeasible = false;
		for (JsonNode p : longStay.get("plans")) {
			if (p.get("feasible").asBoolean()) {
				anyFeasible = true;
				assertThat(p.get("reason").asText()).isEqualTo("OK");
				assertThat(p.get("bufferDays").asInt()).isGreaterThanOrEqualTo(1);
			}
		}
		assertThat(anyFeasible).isTrue();
	}

	@Test
	void validatesDatesAndProcedure() throws Exception {
		LocalDate today = LocalDate.now(Times.SEOUL);
		request("JAW_BOTOX", List.of(1L), today.plusDays(5), today.plusDays(1)).andExpect(status().isBadRequest());
		request("NOT_A_CODE", List.of(1L), today, today.plusDays(3)).andExpect(status().isUnprocessableEntity());
		request("JAW_BOTOX", List.of(99999L), today, today.plusDays(3)).andExpect(status().isNotFound());
		request("JAW_BOTOX", List.of(1L, 2L, 3L, 4L, 5L, 6L), today, today.plusDays(3)).andExpect(status().isBadRequest());
	}

	private JsonNode plan(String procedure, List<Long> hospitals, LocalDate arrival, LocalDate departure)
			throws Exception {
		return body(request(procedure, hospitals, arrival, departure).andExpect(status().isOk()).andReturn());
	}

	private org.springframework.test.web.servlet.ResultActions request(String procedure, List<Long> hospitals,
			LocalDate arrival, LocalDate departure) throws Exception {
		return mvc.perform(post("/internal/trip-plans").header("X-Service-Token", "test-service-token")
				.header("X-Acting-User-Id", "3").contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("procedureCode", procedure, "hospitalIds", hospitals,
						"arrivalDate", arrival.toString(), "departureDate", departure.toString()))));
	}
}
