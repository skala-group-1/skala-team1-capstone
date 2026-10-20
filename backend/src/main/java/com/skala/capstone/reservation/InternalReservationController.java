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
import com.skala.capstone.reservation.ReservationDtos.CancelRequest;
import com.skala.capstone.reservation.ReservationDtos.CreateReservationRequest;
import com.skala.capstone.reservation.ReservationDtos.Reservation;

import io.swagger.v3.oas.annotations.tags.Tag;

/**
 * business-mcp 예약 도구용 (get_my_reservations, create_reservation_request, cancel_reservation).
 * acting user(X-Acting-User-Id)로 공개 API 와 같은 규칙·권한 검사를 한다 → 에이전트가 남의 예약을 건드릴 수 없다.
 */
@Tag(name = "Internal (business-mcp)")
@RestController
@RequestMapping("/internal/reservations")
public class InternalReservationController {

	private final ReservationService reservations;

	public InternalReservationController(ReservationService reservations) {
		this.reservations = reservations;
	}

	@GetMapping("/mine")
	public List<Reservation> mine(@AuthenticationPrincipal CurrentUser user,
			@RequestParam(required = false) String status, @RequestParam(required = false) String locale,
			HttpServletRequest request) {
		return reservations.mine(user, status, RequestLocale.resolve(locale, request));
	}

	@PreAuthorize("hasRole('CUSTOMER')")
	@PostMapping
	public ResponseEntity<Reservation> create(@AuthenticationPrincipal CurrentUser user,
			@RequestHeader(value = ReservationController.IDEMPOTENCY_KEY, required = false) String key,
			@Valid @RequestBody CreateReservationRequest req, @RequestParam(required = false) String locale,
			HttpServletRequest request) {
		var result = reservations.create(user, key, req, "AI", RequestLocale.resolve(locale, request));
		return ResponseEntity.status(result.created() ? HttpStatus.CREATED : HttpStatus.OK).body(result.reservation());
	}

	@PostMapping("/{id}/cancel")
	public Reservation cancel(@AuthenticationPrincipal CurrentUser user, @PathVariable long id,
			@Valid @RequestBody(required = false) CancelRequest req, @RequestParam(required = false) String locale,
			HttpServletRequest request) {
		return reservations.cancel(user, id, req == null ? null : req.reason(), RequestLocale.resolve(locale, request));
	}
}
