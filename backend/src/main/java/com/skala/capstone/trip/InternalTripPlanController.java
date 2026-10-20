package com.skala.capstone.trip;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.common.web.RequestLocale;
import com.skala.capstone.trip.TripPlanService.TripPlanRequest;
import com.skala.capstone.trip.TripPlanService.TripPlans;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/** business-mcp plan_trip 도구용 */
@Tag(name = "Internal (business-mcp)")
@RestController
@RequestMapping("/internal/trip-plans")
public class InternalTripPlanController {

	private final TripPlanService trips;

	public InternalTripPlanController(TripPlanService trips) {
		this.trips = trips;
	}

	@Operation(summary = "병원별 출국 전 회복 가능 일정 계산 (최대 5곳)")
	@PostMapping
	public TripPlans plan(@Valid @RequestBody TripPlanRequest req, @RequestParam(required = false) String locale,
			HttpServletRequest request) {
		return trips.plan(req, RequestLocale.resolve(locale, request));
	}
}
