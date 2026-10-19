package com.skala.capstone.auth;

import java.io.IOException;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;

import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.error.ErrorResponseFactory;

/** 401: 만료 토큰이면 TOKEN_EXPIRED(FE가 refresh 후 재시도), 그 외 UNAUTHENTICATED. */
public class RestAuthenticationEntryPoint implements AuthenticationEntryPoint {

	private final ErrorResponseFactory errors;

	public RestAuthenticationEntryPoint(ErrorResponseFactory errors) {
		this.errors = errors;
	}

	@Override
	public void commence(HttpServletRequest request, HttpServletResponse response, AuthenticationException ex)
			throws IOException {
		Object reason = request.getAttribute(JwtAuthenticationFilter.AUTH_ERROR_ATTR);
		errors.write(response, reason instanceof ErrorCode code ? code : ErrorCode.UNAUTHENTICATED, request);
	}
}
