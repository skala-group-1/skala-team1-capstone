package com.skala.capstone.catalog;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;

import com.fasterxml.jackson.annotation.JsonAlias;

/** 12 공통 계약서 5장 탐색·병원 DTO. 다국어 필드는 요청자 locale 로 골라 name 하나로 준다. */
public final class CatalogDtos {

	private CatalogDtos() {
	}

	public record Procedure(String code, String category, String name, Integer durationMin, Integer downtimeDays) {
	}

	public record HospitalCard(long id, String name, String areaCode, String category,
			Integer minPriceKrw, Boolean priceVerified, long reviewCount, Double rating,
			List<String> languages, boolean hasInterpreter, OffsetDateTime earliestSlotAt, Double distanceKm) {
	}

	public record HospitalDetail(long id, String name, String nameKo, String category, String areaCode,
			String address, String phone, String description, Map<String, Object> openHours,
			List<String> languages, boolean hasInterpreter, LocalDate verifiedAt,
			List<Doctor> doctors, List<ProcedureOptions> procedures, ReviewStats reviewStats) {
	}

	public record ProcedureOptions(Procedure procedure, List<PriceOption> options) {
	}

	public record Doctor(long id, String name, String title, List<String> specialties, List<String> languages,
			Integer careerYears) {
	}

	public record PriceOption(long id, String procedureCode, String product, String dose, int priceKrw,
			boolean vatIncluded, String conditions, LocalDate verifiedAt) {
	}

	public record Slot(long id, OffsetDateTime startAt, OffsetDateTime endAt, Long doctorId, String doctorName,
			String status) {
	}

	public record ReviewStats(long reviewCount, Double avgRating, Map<String, Long> byAgeGroup,
			Map<String, Long> byGender) {
	}

	/** content·lang 은 원문. translatedContent 는 보는 사람 언어 번역본 (같은 언어이거나 번역 전이면 null) */
	public record Review(long id, String procedureCode, int rating, String ageGroup, String gender,
			String reviewerNationality, String lang, String content, OffsetDateTime createdAt,
			String translatedContent) {
	}

	public record CompareRequest(
			@NotEmpty @Size(max = 3) List<Long> hospitalIds,
			// 07 문서는 procedure, 12 계약서는 procedureCode → 둘 다 받는다
			@NotBlank @JsonAlias("procedure") String procedureCode) {
	}

	public record CompareColumn(HospitalCard hospital, List<PriceOption> options, OffsetDateTime earliestSlotAt,
			LocalDate verifiedAt) {
	}

	public record CompareResponse(String procedureCode, List<CompareColumn> columns) {
	}

	public record ProcedureCandidate(String code, String name, double score) {
	}

	public record NormalizeResponse(List<ProcedureCandidate> candidates) {
	}

	public record SearchResult(List<HospitalCard> items, long total) {
	}
}
