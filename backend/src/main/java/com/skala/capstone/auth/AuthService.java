package com.skala.capstone.auth;

import java.util.Map;

import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.skala.capstone.auth.AuthDtos.LoginResponse;
import com.skala.capstone.auth.AuthDtos.SignupRequest;
import com.skala.capstone.auth.AuthDtos.UserSummary;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.security.AuditLogger;
import com.skala.capstone.staff.StaffAccounts;
import com.skala.capstone.user.User;
import com.skala.capstone.user.UserRepository;

@Service
public class AuthService {

	/** 존재하지 않는 이메일에도 BCrypt 비교를 해서 응답 시간으로 계정 존재 여부가 드러나지 않게 한다. */
	private final String dummyHash;

	private final UserRepository users;
	private final PasswordEncoder passwordEncoder;
	private final JwtProvider jwt;
	private final RefreshTokenService refreshTokens;
	private final AuditLogger audit;
	private final StaffAccounts accounts;

	public AuthService(UserRepository users, PasswordEncoder passwordEncoder, JwtProvider jwt,
			RefreshTokenService refreshTokens, AuditLogger audit, StaffAccounts accounts) {
		this.users = users;
		this.passwordEncoder = passwordEncoder;
		this.jwt = jwt;
		this.refreshTokens = refreshTokens;
		this.audit = audit;
		this.accounts = accounts;
		this.dummyHash = passwordEncoder.encode("timing-equalizer");
	}

	/** 로그인 결과: 응답 바디 + Set-Cookie 로 내려갈 refresh 원문. */
	public record Session(LoginResponse body, String refreshToken) {
	}

	@Transactional
	public UserSummary signup(SignupRequest req) {
		String email = req.email().trim().toLowerCase();
		if (users.existsByEmailIgnoreCase(email)) {
			throw new ApiException(ErrorCode.EMAIL_DUPLICATED);
		}
		User user = users.save(User.newCustomer(email, passwordEncoder.encode(req.password()), req.name().trim(),
				req.birthDate(), req.gender(), req.nationality(), req.locale()));
		return UserSummary.of(user);
	}

	@Transactional
	public Session login(String email, String password, String userAgent) {
		User user = users.findByEmailIgnoreCase(email.trim()).orElse(null);
		boolean ok = passwordEncoder.matches(password, user == null ? dummyHash : user.getPasswordHash());
		if (user == null || !ok) {
			audit.log(user == null ? null : user.getId(), null, "LOGIN_FAILED", null,
					Map.of("email", AuditLogger.maskEmail(email)));
			throw new ApiException(ErrorCode.INVALID_CREDENTIALS);
		}
		// 병원 관리자가 비활성으로 바꾼 상담사 (V105). 계정 존재 여부는 드러내지 않는다
		if (!accounts.isActive(user.getId())) {
			audit.log(user.getId(), user.getRole(), "LOGIN_BLOCKED_INACTIVE", "user:" + user.getId(), Map.of());
			throw new ApiException(ErrorCode.INVALID_CREDENTIALS);
		}
		accounts.recordLogin(user.getId());
		audit.log(user.getId(), user.getRole(), "LOGIN_SUCCESS", "user:" + user.getId(), Map.of());
		return newSession(user, refreshTokens.issue(user.getId(), userAgent).rawToken());
	}

	@Transactional(noRollbackFor = ApiException.class)
	public Session refresh(String rawRefreshToken, String userAgent) {
		RefreshTokenService.Issued issued = refreshTokens.rotate(rawRefreshToken, userAgent);
		// 역할·병원이 바뀌었으면 여기서 반영된다 (최대 30분 지연, 11 문서)
		User user = users.findById(issued.userId()).orElseThrow(() -> new ApiException(ErrorCode.REFRESH_INVALID));
		return newSession(user, issued.rawToken());
	}

	public void logout(String rawRefreshToken) {
		refreshTokens.revoke(rawRefreshToken);
	}

	private Session newSession(User user, String refreshToken) {
		String access = jwt.issue(user.toCurrentUser());
		return new Session(new LoginResponse(access, jwt.accessTtlSeconds(), UserSummary.of(user)), refreshToken);
	}
}
