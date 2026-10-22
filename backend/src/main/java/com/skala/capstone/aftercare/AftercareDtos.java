package com.skala.capstone.aftercare;

import java.time.OffsetDateTime;
import java.util.UUID;

import com.skala.capstone.reservation.ReservationDtos.HospitalRef;

public final class AftercareDtos {

	private AftercareDtos() {
	}

	/**
	 * 사후관리 대화방. activeTaskId 는 진행 중인 AI 작업(그날 안내 포함)이 있으면 그 ID — FE 가 바로 SSE 를 연다.
	 * startAt 은 시술(슬롯) 시작 시각, daysFromProcedure 는 오늘이 시술일로부터 며칠째인지 (시술일 0, 시술 전 음수).
	 * reservationStatus 가 PENDING·CONFIRMED 가 아니면 안내가 끝난 방이다 (기록만 표시).
	 */
	public record AftercareConversation(UUID conversationId, long reservationId, String reservationStatus, String mode,
			String procedureCode, String procedureName, HospitalRef hospital, OffsetDateTime startAt,
			int daysFromProcedure, UUID activeTaskId, OffsetDateTime createdAt) {
	}
}
