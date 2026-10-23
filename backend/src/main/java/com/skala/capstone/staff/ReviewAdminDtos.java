package com.skala.capstone.staff;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/** 병원 관리자 리뷰 관리 DTO (H5-D). 계약은 PR 본문에 정리. */
public final class ReviewAdminDtos {

	private ReviewAdminDtos() {
	}

	/** 숨김 사유 */
	public static final String HIDE_REASON = "PRIVACY|ABUSE|FALSE_INFO|SPAM|OTHER";

	public record AdminReview(
			long id,
			String procedureCode,
			String procedureName,
			int rating,
			String ageGroup,
			String gender,
			String reviewerNationality,
			String lang,
			String content,
			/** 보는 사람(관리자) 언어 번역. 같은 언어이거나 번역 전이면 null */
			String translatedContent,
			OffsetDateTime createdAt,
			Reply reply,
			Hidden hidden) {
	}

	/** 병원 답글. translations = 고객 언어별 번역 (번역 전이면 비어 있음) */
	public record Reply(String content, String lang, Map<String, String> translations, OffsetDateTime createdAt,
			OffsetDateTime updatedAt) {
	}

	public record Hidden(String reason, String detail, OffsetDateTime hiddenAt) {
	}

	/** 숨기지 않은 리뷰 기준 요약 (숨김 수만 따로) */
	public record ReviewSummary(
			long reviewCount,
			Double avgRating,
			Map<String, Long> byRating,
			long unreplied,
			long lowRating,
			long hidden,
			long thisMonth) {
	}

	public record AdminReviewPage(List<AdminReview> items, int page, int size, long total, ReviewSummary summary) {
	}

	public record ReplyRequest(@NotBlank @Size(max = 500) String content) {
	}

	/** OTHER 는 detail 필수 */
	public record HideRequest(
			@NotNull @Pattern(regexp = HIDE_REASON) String reason,
			@Size(max = 300) String detail) {
	}
}
