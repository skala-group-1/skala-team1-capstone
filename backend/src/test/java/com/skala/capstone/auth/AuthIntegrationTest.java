package com.skala.capstone.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import java.util.Map;

import jakarta.servlet.http.Cookie;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MvcResult;

import com.skala.capstone.IntegrationTest;
import com.skala.capstone.common.config.AppProperties;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;

/** 11 문서 7장 테스트 목록 중 인증·URL 인가·내부 API 항목. */
class AuthIntegrationTest extends IntegrationTest {

	@Autowired
	AppProperties app;

	@Test
	void requestWithoutTokenIsRejectedWithTraceId() throws Exception {
		mvc.perform(get("/api/hospitals/search"))
				.andExpect(status().isUnauthorized())
				.andExpect(header().exists("X-Trace-Id"))
				.andExpect(jsonPath("$.code").value("UNAUTHENTICATED"))
				.andExpect(jsonPath("$.traceId").isNotEmpty());
	}

	@Test
	void seedUserCanLoginAndReadMe() throws Exception {
		MvcResult result = login("customer.zh1@demo.local");
		assertThat(body(result).at("/user/role").asText()).isEqualTo("CUSTOMER");
		assertThat(body(result).at("/user/locale").asText()).isEqualTo("zh");
		assertThat(body(result).get("expiresIn").asLong()).isEqualTo(1800);
		String setCookie = result.getResponse().getHeader(HttpHeaders.SET_COOKIE);
		assertThat(setCookie).contains("refresh_token=", "HttpOnly", "SameSite=Strict", "Path=/api/auth");

		String token = "Bearer " + body(result).get("accessToken").asText();
		mvc.perform(get("/api/me").header(HttpHeaders.AUTHORIZATION, token))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.email").value("customer.zh1@demo.local"))
				.andExpect(jsonPath("$.hospitalId").doesNotExist());
	}

	@Test
	void wrongPasswordIsInvalidCredentialsAndAudited() throws Exception {
		mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("email", "customer.en1@demo.local", "password", "wrong-pass1"))))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"));
		mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("email", "nobody@demo.local", "password", "wrong-pass1"))))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"));
		Long failures = jdbc.sql("SELECT count(*) FROM app.audit_logs WHERE action = 'LOGIN_FAILED'")
				.query(Long.class).single();
		assertThat(failures).isGreaterThanOrEqualTo(2);
	}

	@Test
	void expiredTokenReturnsTokenExpired() throws Exception {
		Instant past = Instant.now().minusSeconds(3600);
		String expired = Jwts.builder().subject("1").claim("role", "CUSTOMER").claim("locale", "en")
				.issuer(app.jwt().issuer()).issuedAt(Date.from(past)).expiration(Date.from(past.plusSeconds(60)))
				.signWith(Keys.hmacShaKeyFor(app.jwt().secret().getBytes(StandardCharsets.UTF_8)))
				.compact();
		mvc.perform(get("/api/me").header(HttpHeaders.AUTHORIZATION, "Bearer " + expired))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("TOKEN_EXPIRED"));
	}

	@Test
	void forgedTokenIsUnauthenticated() throws Exception {
		String forged = Jwts.builder().subject("1").claim("role", "OPERATOR").issuer(app.jwt().issuer())
				.expiration(Date.from(Instant.now().plusSeconds(600)))
				.signWith(Keys.hmacShaKeyFor("another-secret-another-secret-0123456789".getBytes(StandardCharsets.UTF_8)))
				.compact();
		mvc.perform(get("/api/me").header(HttpHeaders.AUTHORIZATION, "Bearer " + forged))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("UNAUTHENTICATED"));
	}

	@Test
	void refreshRotatesAndReuseRevokesEverything() throws Exception {
		Cookie first = refreshCookie(login("customer.ja1@demo.local"));

		MvcResult rotated = mvc.perform(post("/api/auth/refresh").cookie(first))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.accessToken").isNotEmpty())
				.andExpect(jsonPath("$.user.locale").value("ja"))
				.andReturn();
		Cookie second = refreshCookie(rotated);
		assertThat(second.getValue()).isNotEqualTo(first.getValue());

		// 폐기된 첫 토큰 재사용 → 거부 + 계보 전체 폐기
		mvc.perform(post("/api/auth/refresh").cookie(first))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("REFRESH_INVALID"));
		mvc.perform(post("/api/auth/refresh").cookie(second))
				.andExpect(status().isUnauthorized())
				.andExpect(jsonPath("$.code").value("REFRESH_INVALID"));
		Long reuse = jdbc.sql("SELECT count(*) FROM app.audit_logs WHERE action = 'TOKEN_REUSE_DETECTED'")
				.query(Long.class).single();
		assertThat(reuse).isGreaterThanOrEqualTo(1);
	}

	@Test
	void logoutRevokesRefreshToken() throws Exception {
		Cookie cookie = refreshCookie(login("customer.en2@demo.local"));
		mvc.perform(post("/api/auth/logout").cookie(cookie))
				.andExpect(status().isNoContent())
				.andExpect(header().string(HttpHeaders.SET_COOKIE, org.hamcrest.Matchers.containsString("Max-Age=0")));
		mvc.perform(post("/api/auth/refresh").cookie(cookie))
				.andExpect(status().isUnauthorized());
	}

	@Test
	void signupCreatesCustomerOnly() throws Exception {
		Map<String, Object> req = Map.of("email", "new.user@example.com", "password", "Abcdefg1", "name", "New User",
				"birthDate", "1999-03-02", "gender", "F", "nationality", "CN", "locale", "zh");
		mvc.perform(post("/api/auth/signup").contentType(MediaType.APPLICATION_JSON).content(json(req)))
				.andExpect(status().isCreated())
				.andExpect(jsonPath("$.role").value("CUSTOMER"));
		mvc.perform(post("/api/auth/signup").contentType(MediaType.APPLICATION_JSON).content(json(req)))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("EMAIL_DUPLICATED"));
		mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
				.content(json(Map.of("email", "new.user@example.com", "password", "Abcdefg1"))))
				.andExpect(status().isOk());
	}

	@Test
	void customerCanSignupInKorean() throws Exception {
		// D-43: 고객 가입 언어에 ko 허용
		Map<String, Object> req = Map.of("email", "ko.user@example.com", "password", "Abcdefg1", "name", "김고객",
				"birthDate", "1995-05-05", "gender", "F", "nationality", "KR", "locale", "ko");
		mvc.perform(post("/api/auth/signup").contentType(MediaType.APPLICATION_JSON).content(json(req)))
				.andExpect(status().isCreated())
				.andExpect(jsonPath("$.role").value("CUSTOMER"))
				.andExpect(jsonPath("$.locale").value("ko"));
	}

	@Test
	void signupValidatesFields() throws Exception {
		Map<String, Object> req = Map.of("email", "bad", "password", "short", "name", "X",
				"birthDate", "1999-03-02", "gender", "Q", "nationality", "CN", "locale", "fr");
		mvc.perform(post("/api/auth/signup").contentType(MediaType.APPLICATION_JSON).content(json(req)))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
				.andExpect(jsonPath("$.details.fields.length()").value(4));
	}

	@Test
	void counselorCannotUseHospitalAdminApi() throws Exception {
		mvc.perform(get("/api/hospital-admin/dashboard")
				.header(HttpHeaders.AUTHORIZATION, accessToken("counselor.h1@demo.local")))
				.andExpect(status().isForbidden())
				.andExpect(jsonPath("$.code").value("ACCESS_DENIED"));
		Long denied = jdbc.sql("SELECT count(*) FROM app.audit_logs WHERE action = 'ACCESS_DENIED'")
				.query(Long.class).single();
		assertThat(denied).isGreaterThanOrEqualTo(1);
	}

	@Test
	void internalApiRequiresServiceTokenAndActingUser() throws Exception {
		String customerToken = accessToken("customer.en1@demo.local");
		// 사용자 JWT 로는 내부 API 불가
		mvc.perform(get("/internal/procedures/normalize").param("text", "botox")
				.header(HttpHeaders.AUTHORIZATION, customerToken))
				.andExpect(status().isUnauthorized());
		// 서비스 토큰만 있고 acting user 없음
		mvc.perform(get("/internal/procedures/normalize").param("text", "botox")
				.header("X-Service-Token", app.serviceToken()))
				.andExpect(status().isUnauthorized());
		mvc.perform(get("/internal/procedures/normalize").param("text", "botox")
				.header("X-Service-Token", app.serviceToken()).header("X-Acting-User-Id", "1")
				.header("X-Trace-Id", "trace-from-mcp"))
				.andExpect(status().isOk())
				.andExpect(header().string("X-Trace-Id", "trace-from-mcp"))
				.andExpect(jsonPath("$.candidates[0].code").exists());
	}

	@Test
	void errorMessageFollowsUserLocale() throws Exception {
		mvc.perform(get("/api/hospitals/99999").header(HttpHeaders.AUTHORIZATION, accessToken("customer.zh2@demo.local")))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("NOT_FOUND"))
				.andExpect(jsonPath("$.message").value("未找到请求的内容。"))
				.andExpect(jsonPath("$.details.resource").value("hospital"));
	}

	private static Cookie refreshCookie(MvcResult result) {
		Cookie cookie = result.getResponse().getCookie("refresh_token");
		assertThat(cookie).isNotNull();
		return new Cookie(cookie.getName(), cookie.getValue());
	}
}
