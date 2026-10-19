package com.skala.capstone.auth;

import java.time.OffsetDateTime;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "refresh_tokens", schema = "app")
public class RefreshToken {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	private Long id;

	@Column(name = "user_id", nullable = false)
	private Long userId;

	@Column(name = "token_hash", nullable = false, unique = true)
	private String tokenHash;

	@Column(name = "family_id", nullable = false)
	private UUID familyId;

	@Column(name = "expires_at", nullable = false)
	private OffsetDateTime expiresAt;

	@Column(name = "revoked_at")
	private OffsetDateTime revokedAt;

	@Column(name = "replaced_by")
	private Long replacedBy;

	@Column(name = "user_agent")
	private String userAgent;

	@Column(name = "created_at", nullable = false)
	private OffsetDateTime createdAt;

	protected RefreshToken() {
	}

	public RefreshToken(Long userId, String tokenHash, UUID familyId, OffsetDateTime expiresAt, String userAgent) {
		this.userId = userId;
		this.tokenHash = tokenHash;
		this.familyId = familyId;
		this.expiresAt = expiresAt;
		this.userAgent = userAgent;
		this.createdAt = OffsetDateTime.now();
	}

	public boolean isActive(OffsetDateTime now) {
		return revokedAt == null && expiresAt.isAfter(now);
	}

	public void revoke(OffsetDateTime now, Long replacedById) {
		if (revokedAt == null) {
			revokedAt = now;
		}
		replacedBy = replacedById;
	}

	public Long getId() {
		return id;
	}

	public Long getUserId() {
		return userId;
	}

	public UUID getFamilyId() {
		return familyId;
	}

	public OffsetDateTime getRevokedAt() {
		return revokedAt;
	}
}
