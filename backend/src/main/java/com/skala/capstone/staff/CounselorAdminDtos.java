package com.skala.capstone.staff;

import java.time.OffsetDateTime;
import java.util.List;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/** 병원 관리자 상담사 관리 DTO (H4-D). 계약은 PR 본문에 정리. */
public final class CounselorAdminDtos {

	private CounselorAdminDtos() {
	}

	/** 상담 언어: ko·en·zh·ja 중 1개 이상 */
	public static final String LANGUAGE = "ko|en|zh|ja";

	public record Counselor(
			long id,
			String name,
			String email,
			List<String> languages,
			boolean acceptingNew,
			boolean active,
			int activeConsultations,
			int closedThisMonth,
			OffsetDateTime lastLoginAt,
			OffsetDateTime createdAt) {
	}

	/** 목록 + 우리 병원 대기 문의 수 (상단 "진행 상담" 카드의 보조 문구) */
	public record CounselorRoster(List<Counselor> items, int waitingConsultations) {
	}

	public record CreateCounselorRequest(
			@NotBlank @Size(max = 100) String name,
			@NotBlank @Email @Size(max = 255) String email,
			@NotBlank @Pattern(regexp = "^(?=.*[A-Za-z])(?=.*\\d).{8,72}$",
					message = "at least 8 characters with letters and digits") String password,
			@NotEmpty @Size(max = 4) List<@NotBlank @Pattern(regexp = LANGUAGE) String> languages) {
	}

	/** 보낸 필드만 바꾼다 (null = 그대로). 이메일은 바꿀 수 없다. */
	public record UpdateCounselorRequest(
			@Size(min = 1, max = 100) @Pattern(regexp = ".*\\S.*", message = "must not be blank") String name,
			@Size(min = 1, max = 4) List<@NotBlank @Pattern(regexp = LANGUAGE) String> languages,
			Boolean acceptingNew) {
	}
}
