package com.skala.capstone.auth;

import java.io.IOException;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.springframework.http.HttpHeaders;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.security.CurrentUser;

import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;

/**
 * Bearer 토큰 검증 → SecurityContext. 실패해도 여기서 끊지 않고 사유만 남긴다.
 * 인증이 필요한 경로면 {@link RestAuthenticationEntryPoint} 가 그 사유(TOKEN_EXPIRED / UNAUTHENTICATED)로 401을 쓴다.
 */
public class JwtAuthenticationFilter extends OncePerRequestFilter {

	public static final String AUTH_ERROR_ATTR = "auth.error";

	private final JwtProvider jwt;

	public JwtAuthenticationFilter(JwtProvider jwt) {
		this.jwt = jwt;
	}

	@Override
	protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
			throws ServletException, IOException {
		String header = request.getHeader(HttpHeaders.AUTHORIZATION);
		if (header != null && header.startsWith("Bearer ")) {
			try {
				CurrentUser user = jwt.parse(header.substring(7).trim());
				var auth = new UsernamePasswordAuthenticationToken(user, null, user.authorities());
				SecurityContextHolder.getContext().setAuthentication(auth);
			} catch (ExpiredJwtException e) {
				request.setAttribute(AUTH_ERROR_ATTR, ErrorCode.TOKEN_EXPIRED);
			} catch (JwtException | IllegalArgumentException e) {
				request.setAttribute(AUTH_ERROR_ATTR, ErrorCode.UNAUTHENTICATED);
			}
		}
		chain.doFilter(request, response);
	}
}
