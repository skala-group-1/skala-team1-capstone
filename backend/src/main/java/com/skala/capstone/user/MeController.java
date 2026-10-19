package com.skala.capstone.user;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Set;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.security.Role;

import io.swagger.v3.oas.annotations.tags.Tag;

@Tag(name = "Auth")
@RestController
@RequestMapping("/api/me")
public class MeController {

	private final UserRepository users;

	public MeController(UserRepository users) {
		this.users = users;
	}

	@GetMapping
	public MeResponse me(@AuthenticationPrincipal CurrentUser current) {
		return toResponse(users.findById(current.id()).orElseThrow(() -> ApiException.notFound("user")));
	}

	/**
	 * 화면 언어 변경. 고객은 en/zh/ja, 스태프·운영자는 ko/en.
	 * 토큰 안의 locale 은 다음 refresh 때 바뀐다 (그 전까지 응답 언어는 Accept-Language 로 맞추면 됨).
	 */
	@PatchMapping
	@Transactional
	public MeResponse update(@AuthenticationPrincipal CurrentUser current, @Valid @RequestBody UpdateMeRequest req) {
		User u = users.findById(current.id()).orElseThrow(() -> ApiException.notFound("user"));
		boolean customer = u.getRole() == Role.CUSTOMER;
		boolean allowed = customer ? Set.of("en", "zh", "ja").contains(req.locale())
				: Set.of("ko", "en").contains(req.locale());
		if (!allowed) {
			throw new ApiException(ErrorCode.VALIDATION_FAILED, Map.of("fields", List.of(
					Map.of("field", "locale", "reason", customer ? "one of en, zh, ja" : "one of ko, en"))));
		}
		u.changeLocale(req.locale());
		return toResponse(u);
	}

	public record UpdateMeRequest(@NotNull @Pattern(regexp = "en|zh|ja|ko") String locale) {
	}

	private static MeResponse toResponse(User u) {
		return new MeResponse(u.getId(), u.getEmail(), u.getName(), u.getRole(), u.getHospitalId(), u.getLocale(),
				u.getNationality(), u.getGender(), u.getBirthDate());
	}

	public record MeResponse(long id, String email, String name, Role role, Long hospitalId, String locale,
			String nationality, String gender, LocalDate birthDate) {
	}
}
