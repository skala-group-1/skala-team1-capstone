package com.skala.capstone.auth;

import java.io.IOException;
import java.util.Map;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.web.access.AccessDeniedHandler;

import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.error.ErrorResponseFactory;
import com.skala.capstone.common.security.AuditLogger;
import com.skala.capstone.common.security.CurrentUser;

/** URL 역할 규칙 거부 → 403 ACCESS_DENIED + audit_logs. */
public class RestAccessDeniedHandler implements AccessDeniedHandler {

	private final ErrorResponseFactory errors;
	private final AuditLogger audit;

	public RestAccessDeniedHandler(ErrorResponseFactory errors, AuditLogger audit) {
		this.errors = errors;
		this.audit = audit;
	}

	@Override
	public void handle(HttpServletRequest request, HttpServletResponse response, AccessDeniedException ex)
			throws IOException {
		audit.log(CurrentUser.current().orElse(null), "ACCESS_DENIED",
				request.getMethod() + " " + request.getRequestURI(), Map.of());
		errors.write(response, ErrorCode.ACCESS_DENIED, request);
	}
}
