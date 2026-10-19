package com.skala.capstone.auth;

import jakarta.validation.Valid;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseCookie;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CookieValue;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.auth.AuthDtos.LoginRequest;
import com.skala.capstone.auth.AuthDtos.LoginResponse;
import com.skala.capstone.auth.AuthDtos.SignupRequest;
import com.skala.capstone.auth.AuthDtos.UserSummary;
import com.skala.capstone.common.config.AppProperties;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

@Tag(name = "Auth")
@RestController
@RequestMapping("/api/auth")
public class AuthController {

	private final AuthService auth;
	private final AppProperties app;

	public AuthController(AuthService auth, AppProperties app) {
		this.auth = auth;
		this.app = app;
	}

	@Operation(summary = "고객 회원가입 (스태프·운영자는 시드 계정)")
	@PostMapping("/signup")
	public ResponseEntity<UserSummary> signup(@Valid @RequestBody SignupRequest req) {
		return ResponseEntity.status(HttpStatus.CREATED).body(auth.signup(req));
	}

	@Operation(summary = "로그인 → accessToken + refresh 쿠키(HttpOnly)")
	@PostMapping("/login")
	public ResponseEntity<LoginResponse> login(@Valid @RequestBody LoginRequest req,
			@RequestHeader(value = HttpHeaders.USER_AGENT, required = false) String userAgent) {
		return withCookie(auth.login(req.email(), req.password(), userAgent));
	}

	@Operation(summary = "refresh 쿠키로 access 재발급 (refresh 회전)")
	@PostMapping("/refresh")
	public ResponseEntity<LoginResponse> refresh(@CookieValue(value = "${app.refresh-cookie.name}", required = false) String refreshToken,
			@RequestHeader(value = HttpHeaders.USER_AGENT, required = false) String userAgent) {
		return withCookie(auth.refresh(refreshToken, userAgent));
	}

	@Operation(summary = "로그아웃 (refresh 폐기 + 쿠키 삭제)")
	@PostMapping("/logout")
	public ResponseEntity<Void> logout(@CookieValue(value = "${app.refresh-cookie.name}", required = false) String refreshToken) {
		auth.logout(refreshToken);
		return ResponseEntity.noContent().header(HttpHeaders.SET_COOKIE, cookie("", 0).toString()).build();
	}

	private ResponseEntity<LoginResponse> withCookie(AuthService.Session session) {
		long maxAge = app.jwt().refreshTtl().toSeconds();
		return ResponseEntity.ok()
				.header(HttpHeaders.SET_COOKIE, cookie(session.refreshToken(), maxAge).toString())
				.body(session.body());
	}

	private ResponseCookie cookie(String value, long maxAgeSeconds) {
		AppProperties.RefreshCookie c = app.refreshCookie();
		return ResponseCookie.from(c.name(), value)
				.httpOnly(true)
				.secure(c.secure())
				.sameSite("Strict")
				.path(c.path())
				.maxAge(maxAgeSeconds)
				.build();
	}
}
