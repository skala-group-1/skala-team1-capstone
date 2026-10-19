package com.skala.capstone.user;

import java.time.LocalDate;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.common.error.ApiException;
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
		User u = users.findById(current.id()).orElseThrow(() -> ApiException.notFound("user"));
		return new MeResponse(u.getId(), u.getEmail(), u.getName(), u.getRole(), u.getHospitalId(), u.getLocale(),
				u.getNationality(), u.getGender(), u.getBirthDate());
	}

	public record MeResponse(long id, String email, String name, Role role, Long hospitalId, String locale,
			String nationality, String gender, LocalDate birthDate) {
	}
}
