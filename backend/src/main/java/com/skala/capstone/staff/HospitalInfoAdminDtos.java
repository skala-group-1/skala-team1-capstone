package com.skala.capstone.staff;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * 병원 관리자 병원 정보 수정 DTO (H3-E). 고객 화면용 HospitalDetail 과 달리 locale 로 고르지 않은 원본 값(한국어·영어)을 준다.
 * 계약은 PR 본문에 정리.
 */
public final class HospitalInfoAdminDtos {

	private HospitalInfoAdminDtos() {
	}

	public static final String LANGUAGE = "ko|en|zh|ja";
	public static final String HHMM = "([01]\\d|2[0-3]):[0-5]\\d";
	/** DB 에는 한국어 직함만 있고 응답할 때 locale 로 바꾼다 (D-44) */
	public static final String TITLE = "대표원장|원장|부원장";

	public record HospitalInfo(
			long id,
			String nameKo,
			String nameEn,
			String phone,
			String addressKo,
			String addressEn,
			/** 한국어 소개 (다른 언어는 저장하면 translator 가 다시 번역) */
			String descriptionKo,
			List<String> languages,
			boolean hasInterpreter,
			/** mon~sun 순서, 휴무는 null */
			Map<String, DayHours> openHours,
			LocalDate verifiedAt,
			List<AdminDoctor> doctors,
			/** 의료진 전문 시술로 고를 수 있는 이 병원 시술 */
			List<ProcedureRef> procedures) {
	}

	public record DayHours(@NotNull @Pattern(regexp = HHMM) String open, @NotNull @Pattern(regexp = HHMM) String close) {
	}

	public record AdminDoctor(long id, String nameKo, String nameEn, String title, Integer careerYears,
			List<String> languages, List<String> specialties) {
	}

	public record ProcedureRef(String code, String name) {
	}

	/** 보낸 필드만 바꾼다 (null = 그대로). openHours 는 7일 모두 보내고 휴무는 null */
	public record UpdateHospitalRequest(
			@Size(min = 1, max = 30) @Pattern(regexp = "[0-9+\\-() ]{7,30}", message = "phone number") String phone,
			@Size(min = 1, max = 300) String addressKo,
			@Size(min = 1, max = 300) String addressEn,
			@Size(min = 1, max = 500) String descriptionKo,
			@Size(min = 1, max = 4) List<@NotBlank @Pattern(regexp = LANGUAGE) String> languages,
			Boolean hasInterpreter,
			Map<String, @Valid DayHours> openHours) {
	}

	public record DoctorRequest(
			@NotBlank @Size(max = 50) String nameKo,
			@Size(max = 100) String nameEn,
			@NotBlank @Pattern(regexp = TITLE) String title,
			@Min(0) @Max(60) Integer careerYears,
			@NotEmpty @Size(max = 4) List<@NotBlank @Pattern(regexp = LANGUAGE) String> languages,
			@Size(max = 20) List<@NotBlank String> specialties) {
	}
}
