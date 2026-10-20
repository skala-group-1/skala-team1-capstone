package com.skala.capstone.auth;

import java.time.LocalDate;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Past;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import com.skala.capstone.common.security.Role;
import com.skala.capstone.user.User;

/** 12 공통 계약서 5장 Auth DTO. */
public final class AuthDtos {

	private AuthDtos() {
	}

	public record SignupRequest(
			@NotBlank @Email @Size(max = 255) String email,
			@NotBlank @Pattern(regexp = "^(?=.*[A-Za-z])(?=.*\\d).{8,72}$",
					message = "at least 8 characters with letters and digits") String password,
			@NotBlank @Size(max = 100) String name,
			@NotNull @Past LocalDate birthDate,
			@NotNull @Pattern(regexp = "F|M|X") String gender,
			@NotNull @Pattern(regexp = "[A-Z]{2}", message = "ISO 3166-1 alpha-2") String nationality,
			// 가입은 고객만. 고객 언어는 en/zh/ja + ko (D-43: 한국어로 쓰는 고객도 허용)
			@NotNull @Pattern(regexp = "en|zh|ja|ko") String locale) {
	}

	public record LoginRequest(@NotBlank String email, @NotBlank String password) {
	}

	public record UserSummary(long id, String name, Role role, Long hospitalId, String locale) {

		public static UserSummary of(User u) {
			return new UserSummary(u.getId(), u.getName(), u.getRole(), u.getHospitalId(), u.getLocale());
		}
	}

	public record LoginResponse(String accessToken, long expiresIn, UserSummary user) {
	}
}
