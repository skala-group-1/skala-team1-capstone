package com.skala.capstone.staff;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;

import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.web.RequestLocale;
import com.skala.capstone.staff.ReviewAdminDtos.AdminReview;
import com.skala.capstone.staff.ReviewAdminDtos.AdminReviewPage;
import com.skala.capstone.staff.ReviewAdminDtos.HideRequest;
import com.skala.capstone.staff.ReviewAdminDtos.ReplyRequest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/** 병원관리자 리뷰 관리 API (URL 규칙으로 HOSPITAL_ADMIN 만, 토큰의 hospitalId 기준). */
@Tag(name = "Hospital admin")
@Validated
@RestController
@RequestMapping("/api/hospital-admin/reviews")
public class ReviewAdminController {

	private final ReviewAdminService reviews;

	public ReviewAdminController(ReviewAdminService reviews) {
		this.reviews = reviews;
	}

	@Operation(summary = "우리 병원 리뷰 목록 + 요약 (filter: ALL·UNREPLIED·LOW·HIDDEN, sort: LATEST·RATING_LOW·RATING_HIGH)")
	@GetMapping
	public AdminReviewPage list(@AuthenticationPrincipal CurrentUser admin,
			@RequestParam(defaultValue = "ALL") ReviewAdminService.Filter filter,
			@RequestParam(required = false) @Pattern(regexp = "ko|en|zh|ja") String lang,
			@RequestParam(defaultValue = "LATEST") ReviewAdminService.Sort sort,
			@RequestParam(defaultValue = "0") @Min(0) int page,
			@RequestParam(defaultValue = "20") @Min(1) @Max(50) int size,
			HttpServletRequest request) {
		return reviews.list(admin, filter, lang, sort, page, size, RequestLocale.resolve(request));
	}

	@Operation(summary = "병원 답글 등록·수정 (리뷰당 1개, 고객 언어로 번역)")
	@PutMapping("/{id}/reply")
	public AdminReview reply(@AuthenticationPrincipal CurrentUser admin, @PathVariable long id,
			@Valid @RequestBody ReplyRequest req, HttpServletRequest request) {
		return reviews.reply(admin, id, req.content(), RequestLocale.resolve(request));
	}

	@Operation(summary = "병원 답글 삭제")
	@DeleteMapping("/{id}/reply")
	public ResponseEntity<Void> deleteReply(@AuthenticationPrincipal CurrentUser admin, @PathVariable long id) {
		reviews.deleteReply(admin, id);
		return ResponseEntity.noContent().build();
	}

	@Operation(summary = "리뷰 숨김 (고객 목록·통계에서 빠짐, 삭제 아님. OTHER 는 detail 필수)")
	@PostMapping("/{id}/hide")
	public AdminReview hide(@AuthenticationPrincipal CurrentUser admin, @PathVariable long id,
			@Valid @RequestBody HideRequest req, HttpServletRequest request) {
		return reviews.hide(admin, id, req, RequestLocale.resolve(request));
	}

	@Operation(summary = "숨김 해제")
	@PostMapping("/{id}/unhide")
	public AdminReview unhide(@AuthenticationPrincipal CurrentUser admin, @PathVariable long id,
			HttpServletRequest request) {
		return reviews.unhide(admin, id, RequestLocale.resolve(request));
	}
}
