package com.skala.capstone.common.error;

import org.springframework.http.HttpStatus;

/** 12 공통 계약서 3장 오류 코드. 사용자 문구는 messages*.properties 의 error.{name}. */
public enum ErrorCode {
	VALIDATION_FAILED(HttpStatus.BAD_REQUEST),
	UNAUTHENTICATED(HttpStatus.UNAUTHORIZED),
	TOKEN_EXPIRED(HttpStatus.UNAUTHORIZED),
	INVALID_CREDENTIALS(HttpStatus.UNAUTHORIZED),
	REFRESH_INVALID(HttpStatus.UNAUTHORIZED),
	ACCESS_DENIED(HttpStatus.FORBIDDEN),
	NOT_FOUND(HttpStatus.NOT_FOUND),
	EMAIL_DUPLICATED(HttpStatus.CONFLICT),
	SLOT_UNAVAILABLE(HttpStatus.CONFLICT),
	CONCURRENT_UPDATE(HttpStatus.CONFLICT),
	INVALID_STATE_TRANSITION(HttpStatus.CONFLICT),
	CONSENT_REQUIRED(HttpStatus.CONFLICT),
	TASK_NOT_WAITING_APPROVAL(HttpStatus.CONFLICT),
	REVIEW_NOT_ALLOWED(HttpStatus.CONFLICT),
	REVIEW_ALREADY_EXISTS(HttpStatus.CONFLICT),
	UNKNOWN_PROCEDURE(HttpStatus.UNPROCESSABLE_ENTITY),
	INTERNAL_ERROR(HttpStatus.INTERNAL_SERVER_ERROR),
	AI_UNAVAILABLE(HttpStatus.SERVICE_UNAVAILABLE);

	private final HttpStatus status;

	ErrorCode(HttpStatus status) {
		this.status = status;
	}

	public HttpStatus status() {
		return status;
	}

	public String messageKey() {
		return "error." + name();
	}
}
