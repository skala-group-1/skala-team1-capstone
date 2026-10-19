package com.skala.capstone.reservation;

import java.time.LocalDate;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.web.PageResponse;
import com.skala.capstone.common.web.RequestLocale;
import com.skala.capstone.reservation.ReservationDtos.HospitalDashboard;
import com.skala.capstone.reservation.ReservationDtos.RejectRequest;
import com.skala.capstone.reservation.ReservationDtos.Reservation;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/** 병원관리자 API (URL 규칙으로 HOSPITAL_ADMIN 만). 항상 토큰의 hospitalId 기준으로만 조회·변경한다. */
@Tag(name = "Hospital admin")
@Validated
@RestController
@RequestMapping("/api/hospital-admin")
public class HospitalAdminController {

	private final ReservationService reservations;

	public HospitalAdminController(ReservationService reservations) {
		this.reservations = reservations;
	}

	@Operation(summary = "대시보드: 오늘 예약·승인 대기·진행 중 상담 수, 최근 요청 5건")
	@GetMapping("/dashboard")
	public HospitalDashboard dashboard(@AuthenticationPrincipal CurrentUser admin, HttpServletRequest request) {
		return reservations.dashboard(admin, RequestLocale.resolve(request));
	}

	@Operation(summary = "우리 병원 예약 목록 (status, 슬롯 날짜 필터)")
	@GetMapping("/reservations")
	public PageResponse<Reservation> list(@AuthenticationPrincipal CurrentUser admin,
			@RequestParam(required = false) String status,
			@RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date,
			@RequestParam(defaultValue = "0") @Min(0) int page,
			@RequestParam(defaultValue = "20") @Min(1) @Max(50) int size,
			HttpServletRequest request) {
		return reservations.forHospital(admin, status, date, page, size, RequestLocale.resolve(request));
	}

	@Operation(summary = "예약 승인 (PENDING → CONFIRMED)")
	@PostMapping("/reservations/{id}/approve")
	public Reservation approve(@AuthenticationPrincipal CurrentUser admin, @PathVariable long id,
			HttpServletRequest request) {
		return reservations.approve(admin, id, RequestLocale.resolve(request));
	}

	@Operation(summary = "예약 반려 (사유 필수, 대안 슬롯 최대 3)")
	@PostMapping("/reservations/{id}/reject")
	public Reservation reject(@AuthenticationPrincipal CurrentUser admin, @PathVariable long id,
			@Valid @RequestBody RejectRequest req, HttpServletRequest request) {
		return reservations.reject(admin, id, req.reason(), req.alternativeSlotIds(), RequestLocale.resolve(request));
	}
}
