package com.skala.capstone.catalog;

import java.time.LocalDate;
import java.util.List;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.catalog.CatalogDtos.CompareRequest;
import com.skala.capstone.catalog.CatalogDtos.CompareResponse;
import com.skala.capstone.catalog.CatalogDtos.HospitalCard;
import com.skala.capstone.catalog.CatalogDtos.HospitalDetail;
import com.skala.capstone.catalog.CatalogDtos.Procedure;
import com.skala.capstone.catalog.CatalogDtos.Review;
import com.skala.capstone.catalog.CatalogDtos.Slot;
import com.skala.capstone.common.web.PageResponse;
import com.skala.capstone.common.web.RequestLocale;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/** 공개 탐색·비교 API (07 문서 2장). 로그인한 모든 역할이 조회 가능 (D-17). */
@Tag(name = "Catalog")
@Validated
@RestController
@RequestMapping("/api")
public class CatalogController {

	private final CatalogService catalog;

	public CatalogController(CatalogService catalog) {
		this.catalog = catalog;
	}

	@Operation(summary = "시술 목록 (category 로 묶어서 표시)")
	@GetMapping("/procedures")
	public List<Procedure> procedures(HttpServletRequest request) {
		return catalog.procedures(RequestLocale.resolve(request));
	}

	@Operation(summary = "조건에 맞는 병원 검색 (추천 아님, 사용자가 고른 기준으로 정렬 — D-01)")
	@GetMapping("/hospitals/search")
	public PageResponse<HospitalCard> search(
			@RequestParam(required = false) String procedure,
			@RequestParam(required = false) List<String> areas,
			@RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateFrom,
			@RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateTo,
			@RequestParam(required = false) @Min(0) Integer priceMax,
			@RequestParam(required = false) String language,
			@RequestParam(required = false, defaultValue = "REVIEW_COUNT") String sort,
			@RequestParam(required = false) Double lat,
			@RequestParam(required = false) Double lng,
			@RequestParam(defaultValue = "0") @Min(0) int page,
			@RequestParam(defaultValue = "20") @Min(1) @Max(50) int size,
			HttpServletRequest request) {
		var criteria = new SearchCriteria(procedure, areas, dateFrom, dateTo, priceMax, language, sort, lat, lng, null);
		return catalog.search(criteria, RequestLocale.resolve(request), page, size);
	}

	@Operation(summary = "병원 상세 (기본정보, 의사, 시술·가격, 리뷰 통계)")
	@GetMapping("/hospitals/{id}")
	public HospitalDetail detail(@PathVariable long id, HttpServletRequest request) {
		return catalog.detail(id, RequestLocale.resolve(request), false);
	}

	@Operation(summary = "예약 가능 슬롯 (AVAILABLE, 시작 시각 순)")
	@GetMapping("/hospitals/{id}/slots")
	public List<Slot> slots(@PathVariable long id,
			@RequestParam(required = false) String procedure,
			@RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateFrom,
			@RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateTo,
			@RequestParam(required = false) Long doctorId,
			@RequestParam(defaultValue = "100") @Min(1) @Max(500) int limit,
			HttpServletRequest request) {
		return catalog.slots(id, procedure, dateFrom, dateTo, doctorId, limit, RequestLocale.resolve(request));
	}

	@Operation(summary = "리뷰 목록 (최신순, lang·시술 필터)")
	@GetMapping("/hospitals/{id}/reviews")
	public PageResponse<Review> reviews(@PathVariable long id,
			@RequestParam(required = false) String lang,
			@RequestParam(required = false) String procedure,
			@RequestParam(defaultValue = "0") @Min(0) int page,
			@RequestParam(defaultValue = "20") @Min(1) @Max(50) int size, HttpServletRequest request) {
		return catalog.reviews(id, lang, procedure, page, size, RequestLocale.resolve(request));
	}

	@Operation(summary = "병원 비교 (최대 3곳, 한 시술 기준)")
	@PostMapping("/hospitals/compare")
	public CompareResponse compare(@Valid @RequestBody CompareRequest req, HttpServletRequest request) {
		return catalog.compare(req.hospitalIds(), req.procedureCode(), RequestLocale.resolve(request));
	}
}
