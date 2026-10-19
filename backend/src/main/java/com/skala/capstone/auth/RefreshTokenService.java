package com.skala.capstone.auth;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.OffsetDateTime;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.skala.capstone.common.config.AppProperties;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.security.AuditLogger;

/**
 * Refresh Token: 불투명 랜덤 문자열, DB에는 SHA-256 해시만. 갱신마다 회전하고,
 * 이미 폐기된 토큰이 다시 오면 탈취로 보고 그 사용자의 토큰을 전부 폐기한다 (11 문서).
 */
@Service
public class RefreshTokenService {

	private final RefreshTokenRepository tokens;
	private final AuditLogger audit;
	private final AppProperties.Jwt props;

	public RefreshTokenService(RefreshTokenRepository tokens, AuditLogger audit, AppProperties app) {
		this.tokens = tokens;
		this.audit = audit;
		this.props = app.jwt();
	}

	public record Issued(String rawToken, long userId) {
	}

	@Transactional
	public Issued issue(long userId, String userAgent) {
		return issue(userId, UUID.randomUUID(), userAgent).issued();
	}

	/** 회전: 기존 토큰 폐기 + 같은 family 로 새 토큰. 재사용 감지 시 폐기를 커밋한 뒤 REFRESH_INVALID. */
	@Transactional(noRollbackFor = ApiException.class)
	public Issued rotate(String rawToken, String userAgent) {
		if (rawToken == null || rawToken.isBlank()) {
			throw new ApiException(ErrorCode.REFRESH_INVALID);
		}
		OffsetDateTime now = OffsetDateTime.now();
		RefreshToken current = tokens.findByTokenHash(hash(rawToken))
				.orElseThrow(() -> new ApiException(ErrorCode.REFRESH_INVALID));
		if (current.getRevokedAt() != null) {
			tokens.revokeAllForUser(current.getUserId(), now);
			audit.log(current.getUserId(), null, "TOKEN_REUSE_DETECTED", "user:" + current.getUserId(),
					Map.of("familyId", current.getFamilyId().toString()));
			throw new ApiException(ErrorCode.REFRESH_INVALID);
		}
		if (!current.isActive(now)) {
			throw new ApiException(ErrorCode.REFRESH_INVALID);
		}
		Created next = issue(current.getUserId(), current.getFamilyId(), userAgent);
		current.revoke(now, next.entity().getId());
		return next.issued();
	}

	@Transactional
	public void revoke(String rawToken) {
		if (rawToken == null || rawToken.isBlank()) {
			return;
		}
		tokens.findByTokenHash(hash(rawToken)).ifPresent(t -> t.revoke(OffsetDateTime.now(), null));
	}

	private record Created(Issued issued, RefreshToken entity) {
	}

	private Created issue(long userId, UUID familyId, String userAgent) {
		String raw = UUID.randomUUID() + "." + UUID.randomUUID();
		RefreshToken entity = tokens.save(new RefreshToken(userId, hash(raw), familyId,
				OffsetDateTime.now().plus(props.refreshTtl()), truncate(userAgent)));
		return new Created(new Issued(raw, userId), entity);
	}

	static String hash(String raw) {
		try {
			MessageDigest md = MessageDigest.getInstance("SHA-256");
			return HexFormat.of().formatHex(md.digest(raw.getBytes(StandardCharsets.UTF_8)));
		} catch (NoSuchAlgorithmException e) {
			throw new IllegalStateException(e);
		}
	}

	private static String truncate(String s) {
		return s == null || s.length() <= 300 ? s : s.substring(0, 300);
	}
}
