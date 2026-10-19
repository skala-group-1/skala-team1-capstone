package com.skala.capstone.common.error;

import java.util.Map;

public class ApiException extends RuntimeException {

	private final ErrorCode code;
	private final Map<String, Object> details;

	public ApiException(ErrorCode code) {
		this(code, Map.of());
	}

	public ApiException(ErrorCode code, Map<String, Object> details) {
		super(code.name());
		this.code = code;
		this.details = details;
	}

	public static ApiException notFound(String resource) {
		return new ApiException(ErrorCode.NOT_FOUND, Map.of("resource", resource));
	}

	public ErrorCode code() {
		return code;
	}

	public Map<String, Object> details() {
		return details;
	}
}
