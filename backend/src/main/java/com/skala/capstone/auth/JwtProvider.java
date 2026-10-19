package com.skala.capstone.auth;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import java.util.UUID;

import javax.crypto.SecretKey;

import org.springframework.stereotype.Component;

import com.skala.capstone.common.config.AppProperties;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.security.Role;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;

/** Access Token (HS256, 30분). 클레임: sub, role, hospitalId, locale, jti, iat, exp, iss — 개인정보 없음 (11 문서). */
@Component
public class JwtProvider {

	private final SecretKey key;
	private final AppProperties.Jwt props;

	public JwtProvider(AppProperties app) {
		this.props = app.jwt();
		byte[] secret = props.secret().getBytes(StandardCharsets.UTF_8);
		if (secret.length < 32) {
			throw new IllegalStateException("JWT_SECRET must be at least 32 bytes");
		}
		this.key = Keys.hmacShaKeyFor(secret);
	}

	public String issue(CurrentUser user) {
		Instant now = Instant.now();
		return Jwts.builder()
				.subject(String.valueOf(user.id()))
				.claim("role", user.role().name())
				.claim("hospitalId", user.hospitalId())
				.claim("locale", user.locale())
				.id(UUID.randomUUID().toString())
				.issuer(props.issuer())
				.issuedAt(Date.from(now))
				.expiration(Date.from(now.plus(props.accessTtl())))
				.signWith(key, Jwts.SIG.HS256)
				.compact();
	}

	public long accessTtlSeconds() {
		return props.accessTtl().toSeconds();
	}

	/**
	 * @throws io.jsonwebtoken.ExpiredJwtException 만료
	 * @throws io.jsonwebtoken.JwtException 위조·형식 오류
	 */
	public CurrentUser parse(String token) {
		Claims c = Jwts.parser().verifyWith(key).requireIssuer(props.issuer()).build()
				.parseSignedClaims(token).getPayload();
		Number hospitalId = c.get("hospitalId", Number.class);
		return new CurrentUser(Long.parseLong(c.getSubject()), Role.valueOf(c.get("role", String.class)),
				hospitalId == null ? null : hospitalId.longValue(), c.get("locale", String.class));
	}
}
