package com.skala.capstone.common.security;

import java.security.Principal;
import java.util.List;
import java.util.Optional;

import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;

/**
 * 인증된 사용자 (SecurityContext principal). JWT 클레임 또는 /internal 의 X-Acting-User-Id 로 만든다.
 * 컨트롤러에서는 {@code @AuthenticationPrincipal CurrentUser user} 로 받는다.
 * Principal 이름 = 사용자 id → STOMP 개인 큐(/user/{id}/queue/notifications) 주소로 쓰인다.
 */
public record CurrentUser(long id, Role role, Long hospitalId, String locale) implements Principal {

	@Override
	public String getName() {
		return String.valueOf(id);
	}

	public boolean is(Role r) {
		return role == r;
	}

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
