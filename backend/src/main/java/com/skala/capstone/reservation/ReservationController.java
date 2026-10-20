package com.skala.capstone.reservation;

import java.util.List;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.web.RequestLocale;
import com.skala.capstone.reservation.ReservationDtos.AcceptAlternativeRequest;
import com.skala.capstone.reservation.ReservationDtos.CancelRequest;
import com.skala.capstone.reservation.ReservationDtos.CreateReservationRequest;
import com.skala.capstone.reservation.ReservationDtos.Reservation;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/** 고객 예약 API (16 명세 4장). 생성·대안 수락은 Idempotency-Key 헤더 필수. */
@Tag(name = "Reservation")
@RestController
@RequestMapping("/api/reservations")
public class ReservationController {

	static final String IDEMPOTENCY_KEY = "Idempotency-Key";

	private final ReservationService reservations;

	public ReservationController(ReservationService reservations) {
		this.reservations = reservations;
	}

	@Operation(summary = "직접 예약 요청 → PENDING (슬롯 30분 홀드). 같은 키 재요청은 기존 예약 200")
	@PreAuthorize("hasRole('CUSTOMER')")
	@PostMapping
	public ResponseEntity<Reservation> create(@AuthenticationPrincipal CurrentUser user,
			@RequestHeader(value = IDEMPOTENCY_KEY, required = false) String key,
			@Valid @RequestBody CreateReservationRequest req, HttpServletRequest request) {
		var result = reservations.create(user, key, req, "DIRECT", RequestLocale.resolve(request));
		return ResponseEntity.status(result.created() ? HttpStatus.CREATED : HttpStatus.OK).body(result.reservation());
	}

	@Operation(summary = "내 예약 목록 (최신순)")
	@PreAuthorize("hasRole('CUSTOMER')")
	@GetMapping("/me")
	public List<Reservation> mine(@AuthenticationPrincipal CurrentUser user,
			@RequestParam(required = false) String status, HttpServletRequest request) {
		return reservations.mine(user, status, RequestLocale.resolve(request));
	}

	@Operation(summary = "예약 단건 (본인·같은 병원 관리자·운영자)")
	@GetMapping("/{id}")
	public Reservation get(@AuthenticationPrincipal CurrentUser user, @PathVariable long id,
			HttpServletRequest request) {
		return reservations.get(user, id, RequestLocale.resolve(request));
	}

	@Operation(summary = "예약 취소 (PENDING·CONFIRMED → CANCELLED)")
	@PostMapping("/{id}/cancel")
	public Reservation cancel(@AuthenticationPrincipal CurrentUser user, @PathVariable long id,
			@Valid @RequestBody(required = false) CancelRequest req, HttpServletRequest request) {
		return reservations.cancel(user, id, req == null ? null : req.reason(), RequestLocale.resolve(request));
	}

	@Operation(summary = "반려된 예약의 대안 슬롯 수락 → 새 PENDING")
	@PreAuthorize("hasRole('CUSTOMER')")
	@PostMapping("/{id}/accept-alternative")
	public ResponseEntity<Reservation> acceptAlternative(@AuthenticationPrincipal CurrentUser user,
			@PathVariable long id, @RequestHeader(value = IDEMPOTENCY_KEY, required = false) String key,
			@Valid @RequestBody AcceptAlternativeRequest req, HttpServletRequest request) {
		var result = reservations.acceptAlternative(user, id, req.slotId(), key, RequestLocale.resolve(request));
		return ResponseEntity.status(result.created() ? HttpStatus.CREATED : HttpStatus.OK).body(result.reservation());
	}
}
