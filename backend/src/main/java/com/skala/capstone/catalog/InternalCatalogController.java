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
import com.skala.capstone.catalog.CatalogDtos.Doctor;
import com.skala.capstone.catalog.CatalogDtos.HospitalDetail;
import com.skala.capstone.catalog.CatalogDtos.NormalizeResponse;
import com.skala.capstone.catalog.CatalogDtos.PriceOption;
import com.skala.capstone.catalog.CatalogDtos.SearchResult;
import com.skala.capstone.catalog.CatalogDtos.Slot;
import com.skala.capstone.catalog.CatalogDtos.Review;
import com.skala.capstone.common.web.PageResponse;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.web.RequestLocale;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/**
 * business-mcp 전용 조회 API (12 계약서 8장). 헤더: X-Service-Token, X-Acting-User-Id, X-Trace-Id.
 * 쿼리 이름은 Conditions 를 따른다 (procedureCode, budgetMaxKrw, consultLanguage, sortBy).
 * locale 은 파라미터 → acting user locale → en.
 */
@Tag(name = "Internal (business-mcp)")
@Validated
@RestController
@RequestMapping("/internal")
public class InternalCatalogController {

	private final CatalogService catalog;

	public InternalCatalogController(CatalogService catalog) {
		this.catalog = catalog;
	}

	@Operation(summary = "자유 텍스트 → 시술 코드 후보")
	@GetMapping("/procedures/normalize")
	public NormalizeResponse normalize(@RequestParam String text, @RequestParam(required = false) String locale,
			HttpServletRequest request) {
		return new NormalizeResponse(catalog.normalize(text, RequestLocale.resolve(locale, request)));
	}

	@GetMapping("/hospitals/search")
	public SearchResult search(
			@RequestParam(required = false) String procedureCode,
			@RequestParam(required = false) List<String> areas,
			@RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateFrom,
			@RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateTo,
			@RequestParam(required = false) @Min(0) Integer budgetMaxKrw,
			@RequestParam(required = false) String consultLanguage,
			@RequestParam(required = false, defaultValue = "REVIEW_COUNT") String sortBy,
			@RequestParam(defaultValue = "10") @Min(1) @Max(50) int limit,
			@RequestParam(required = false) String locale,
			HttpServletRequest request) {
		var criteria = new SearchCriteria(procedureCode, areas, dateFrom, dateTo, budgetMaxKrw, consultLanguage,
				sortBy, null, null, null);
		return catalog.searchLimited(criteria, RequestLocale.resolve(locale, request), limit);
	}

	@GetMapping("/hospitals/{id}")
	public HospitalDetail detail(@PathVariable long id, @RequestParam(required = false) String locale,
			@RequestParam(defaultValue = "false") boolean lite, HttpServletRequest request) {
		return catalog.detail(id, RequestLocale.resolve(locale, request), lite);
	}

	@GetMapping("/hospitals/{id}/doctors")
	public List<Doctor> doctors(@PathVariable long id, @RequestParam(required = false) String procedureCode,
			@RequestParam(required = false) String locale, HttpServletRequest request) {
		return catalog.doctors(id, procedureCode, RequestLocale.resolve(locale, request));
	}

	@Operation(summary = "선택 병원 리뷰 조회 (최신순, lang·시술 필터)")
	@GetMapping("/hospitals/{id}/reviews")
	public PageResponse<Review> reviews(@PathVariable long id,
			@RequestParam(required = false) String lang,
			@RequestParam(required = false) String procedureCode,
			@RequestParam(defaultValue = "0") int page,
			@RequestParam(defaultValue = "20") int size) {
		if (page < 0 || size < 1 || size > 50) {
			throw new ApiException(ErrorCode.VALIDATION_FAILED);
		}
		return catalog.reviews(id, lang, procedureCode, page, size, null);
	}

	@GetMapping("/hospitals/{id}/prices")
	public List<PriceOption> prices(@PathVariable long id, @RequestParam String procedureCode,
			@RequestParam(required = false) String locale, HttpServletRequest request) {
		return catalog.prices(id, procedureCode, RequestLocale.resolve(locale, request));
	}

	@Operation(summary = "예약 가능 슬롯 최대 20개")
	@GetMapping("/hospitals/{id}/slots")
	public List<Slot> slots(@PathVariable long id,
			@RequestParam(required = false) String procedureCode,
			@RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateFrom,
			@RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate dateTo,
			@RequestParam(required = false) Long doctorId,
			@RequestParam(required = false) String locale,
			HttpServletRequest request) {
		return catalog.slots(id, procedureCode, dateFrom, dateTo, doctorId, 20, RequestLocale.resolve(locale, request));
	}

	@PostMapping("/hospitals/compare")
	public CompareResponse compare(@Valid @RequestBody CompareRequest req, @RequestParam(required = false) String locale,
			HttpServletRequest request) {
		return catalog.compare(req.hospitalIds(), req.procedureCode(), RequestLocale.resolve(locale, request));
	}
}
