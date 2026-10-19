package com.skala.capstone.reservation;

import java.time.OffsetDateTime;
import java.util.List;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import com.skala.capstone.catalog.CatalogDtos.PriceOption;
import com.skala.capstone.catalog.CatalogDtos.Procedure;
import com.skala.capstone.catalog.CatalogDtos.Slot;

/** 12 공통 계약서 5장 예약 DTO (+ note). */
public final class ReservationDtos {

	private ReservationDtos() {
	}

	public record CreateReservationRequest(
			@NotNull Long hospitalId,
			@NotNull Long slotId,
			@NotBlank String procedureCode,
			Long priceOptionId,
			@Size(max = 500) String note) {
	}

	public record CancelRequest(@Size(max = 500) String reason) {
	}

	public record RejectRequest(
			@NotBlank @Size(max = 500) String reason,
			@Size(max = 3) List<Long> alternativeSlotIds) {
	}

	public record AcceptAlternativeRequest(@NotNull Long slotId) {
	}

	public record HospitalRef(long id, String name) {
	}

	/** 스태프·운영자 조회 시에만 채워지는 고객 정보 (이름 마스킹, 연락처 없음) */
	public record CustomerRef(long id, String name, String nationality, String locale) {
	}

	public record Reservation(long id, String status, String source, HospitalRef hospital, Slot slot,
			Procedure procedure, PriceOption priceOption, OffsetDateTime holdExpiresAt, String rejectReason,
			List<Slot> alternatives, CustomerRef customer, String note, OffsetDateTime createdAt,
			OffsetDateTime decidedAt) {
	}

	public record HospitalDashboard(long todayReservations, long pendingReservations, long activeConsultations,
			List<Reservation> recentRequests) {
	}
}
