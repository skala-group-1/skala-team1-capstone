package com.skala.capstone.auth;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.error.ErrorResponseFactory;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.user.UserRepository;

/**
 * /internal/** 전용 (business-mcp 대리 호출, 11 문서 3-4).
 * X-Service-Token 으로 서비스를 인증하고, X-Acting-User-Id 사용자를 DB에서 로드해 그 사용자로 SecurityContext 를 채운다.
 * 이후 인가는 공개 API와 같은 규칙(AccessGuard 등)으로 재검사된다. Bearer 토큰은 무시한다.
 */
public class InternalServiceTokenFilter extends OncePerRequestFilter {

	public static final String SERVICE_TOKEN_HEADER = "X-Service-Token";
	public static final String ACTING_USER_HEADER = "X-Acting-User-Id";

	private final byte[] serviceToken;
	private final UserRepository users;
	private final ErrorResponseFactory errors;

	public InternalServiceTokenFilter(String serviceToken, UserRepository users, ErrorResponseFactory errors) {
		this.serviceToken = serviceToken.getBytes(StandardCharsets.UTF_8);
		this.users = users;
		this.errors = errors;
	}

	@Override
	protected boolean shouldNotFilter(HttpServletRequest request) {
		return !request.getRequestURI().startsWith("/internal/");
	}

	@Override
	protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
			throws ServletException, IOException {
		SecurityContextHolder.clearContext();
		String token = request.getHeader(SERVICE_TOKEN_HEADER);
		if (token == null || !MessageDigest.isEqual(serviceToken, token.getBytes(StandardCharsets.UTF_8))) {
			errors.write(response, ErrorCode.UNAUTHENTICATED, request);
			return;
		}
		CurrentUser acting;
		try {
			long userId = Long.parseLong(String.valueOf(request.getHeader(ACTING_USER_HEADER)));
			acting = users.findById(userId).map(u -> u.toCurrentUser()).orElse(null);
		} catch (NumberFormatException e) {
			acting = null;
		}
		if (acting == null) {
			errors.write(response, ErrorCode.UNAUTHENTICATED, request);
			return;
		}
		var auth = new UsernamePasswordAuthenticationToken(acting, null, acting.authorities());
		SecurityContextHolder.getContext().setAuthentication(auth);
		chain.doFilter(request, response);
	}
}
