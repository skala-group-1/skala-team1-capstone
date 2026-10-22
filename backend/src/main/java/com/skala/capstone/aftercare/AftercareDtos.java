package com.skala.capstone.aftercare;

import java.time.OffsetDateTime;
import java.util.UUID;

import com.skala.capstone.reservation.ReservationDtos.HospitalRef;

public final class AftercareDtos {

	private AftercareDtos() {
	}

	/**
	 * 사후관리 대화방. activeTaskId 는 진행 중인 AI 작업(첫 안내 포함)이 있으면 그 ID — FE 가 바로 SSE 를 연다.
	 * startAt 은 시술(슬롯) 시작 시각.
	 */
	public record AftercareConversation(UUID conversationId, long reservationId, String mode, String procedureCode,
			String procedureName, HospitalRef hospital, OffsetDateTime startAt, UUID activeTaskId,
			OffsetDateTime createdAt) {
	}
}
