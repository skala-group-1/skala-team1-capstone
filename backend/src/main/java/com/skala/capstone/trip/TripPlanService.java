package com.skala.capstone.trip;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.skala.capstone.catalog.CatalogDtos.Procedure;
import com.skala.capstone.catalog.CatalogDtos.Slot;
import com.skala.capstone.catalog.CatalogService;
import com.skala.capstone.common.config.AppProperties;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.web.Times;

/**
 * 일정 적합성 계산 (03 문서 9-2, 16 명세 8장) — "출국 전에 회복까지 끝낼 수 있나?"
 *
 * 병원마다: 입국일 ~ 출국 전날 사이 가장 이른 예약 가능 슬롯을 고르고
 *   회복 완료일 = 시술일 + 시술 다운타임(일)
 *   여유일     = 출국일 − 회복 완료일
 *   가능 여부  = 여유일 ≥ 최소 여유일(기본 1, TRIP_MIN_BUFFER_DAYS)
 * 의료 판단이 아니라 데이터 기반 일정 계산이다. 설명·대안 탐색은 에이전트가 한다.
 */
@Service
public class TripPlanService {

	public record TripPlanRequest(
			@NotBlank String procedureCode,
			@NotEmpty @Size(max = 5) List<Long> hospitalIds,
			@NotNull LocalDate arrivalDate,
			@NotNull LocalDate departureDate) {
	}

	/** reason: OK | RECOVERY_AFTER_DEPARTURE | NO_SLOT_BEFORE_DEPARTURE | PROCEDURE_NOT_OFFERED */
	public record TripPlan(long hospitalId, String hospitalName, Slot slot, String procedureCode, int downtimeDays,
			LocalDate recoveryEndDate, Integer bufferDays, boolean feasible, String reason) {
	}

	public record TripPlans(List<TripPlan> plans) {
	}

	private final JdbcClient jdbc;
	private final CatalogService catalog;
	private final AppProperties app;

	public TripPlanService(JdbcClient jdbc, CatalogService catalog, AppProperties app) {
		this.jdbc = jdbc;
		this.catalog = catalog;
		this.app = app;
	}

	@Transactional(readOnly = true)
	public TripPlans plan(TripPlanRequest req, String locale) {
		if (req.arrivalDate().isAfter(req.departureDate())) {
			throw new ApiException(ErrorCode.VALIDATION_FAILED, Map.of("fields",
					List.of(Map.of("field", "departureDate", "reason", "must not be before arrivalDate"))));
		}
		catalog.requireProcedure(req.procedureCode(), locale);
		Procedure procedure = catalog.procedure(req.procedureCode(), locale).orElseThrow();
		int downtime = procedure.downtimeDays() == null ? 0 : procedure.downtimeDays();
		List<TripPlan> plans = new ArrayList<>();
		for (Long hospitalId : req.hospitalIds().stream().distinct().toList()) {
			catalog.requireHospital(hospitalId);
			String name = catalog.hospitalName(hospitalId, locale).orElse(null);
			Integer offered = jdbc.sql("SELECT count(*) FROM app.price_options WHERE hospital_id = :h AND procedure_code = :p")
					.param("h", hospitalId).param("p", req.procedureCode()).query(Integer.class).single();
			if (offered == 0) {
				plans.add(new TripPlan(hospitalId, name, null, req.procedureCode(), downtime, null, null, false,
						"PROCEDURE_NOT_OFFERED"));
				continue;
			}
			Optional<Slot> slot = earliestSlot(hospitalId, req.procedureCode(), req.arrivalDate(), req.departureDate(),
					locale);
			if (slot.isEmpty()) {
				plans.add(new TripPlan(hospitalId, name, null, req.procedureCode(), downtime, null, null, false,
						"NO_SLOT_BEFORE_DEPARTURE"));
				continue;
			}
			LocalDate procedureDay = slot.get().startAt().atZoneSameInstant(Times.SEOUL).toLocalDate();
			LocalDate recoveryEnd = procedureDay.plusDays(downtime);
			int buffer = (int) ChronoUnit.DAYS.between(recoveryEnd, req.departureDate());
			boolean feasible = buffer >= app.trip().minBufferDays();
			plans.add(new TripPlan(hospitalId, name, slot.get(), req.procedureCode(), downtime, recoveryEnd, buffer,
					feasible, feasible ? "OK" : "RECOVERY_AFTER_DEPARTURE"));
		}
		return new TripPlans(plans);
	}

	/** 입국일 0시 ~ 출국일 0시 전, 현재 이후, 시술 담당 의사의 가장 이른 AVAILABLE 슬롯 */
	private Optional<Slot> earliestSlot(long hospitalId, String procedureCode, LocalDate arrival, LocalDate departure,
			String locale) {
		OffsetDateTime from = Times.startOfDay(arrival);
		OffsetDateTime now = OffsetDateTime.now();
		return jdbc.sql("""
				SELECT s.id FROM app.slots s LEFT JOIN app.doctors d ON d.id = s.doctor_id
				WHERE s.hospital_id = :h AND s.status = 'AVAILABLE' AND s.start_at > :now
				  AND s.start_at >= :from AND s.start_at < :to
				  AND (s.doctor_id IS NULL OR :p = ANY(d.specialties))
				ORDER BY s.start_at, s.id LIMIT 1
				""").param("h", hospitalId).param("p", procedureCode).param("now", now)
				.param("from", from).param("to", Times.startOfDay(departure))
				.query(Long.class).optional().flatMap(id -> catalog.slot(id, locale));
	}
}
