package com.skala.capstone.common.security;

import java.util.List;
import java.util.Optional;

import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;

/**
 * 인증된 사용자 (SecurityContext principal). JWT 클레임 또는 /internal 의 X-Acting-User-Id 로 만든다.
 * 컨트롤러에서는 {@code @AuthenticationPrincipal CurrentUser user} 로 받는다.
 */
public record CurrentUser(long id, Role role, Long hospitalId, String locale) {

	public List<SimpleGrantedAuthority> authorities() {
		return List.of(new SimpleGrantedAuthority("ROLE_" + role.name()));
	}

	public static Optional<CurrentUser> current() {
		Authentication auth = SecurityContextHolder.getContext().getAuthentication();
		if (auth != null && auth.getPrincipal() instanceof CurrentUser user) {
			return Optional.of(user);
		}
		return Optional.empty();
	}
}
