package com.skala.capstone.catalog;

import java.time.LocalDate;
import java.util.List;

/**
 * 병원 검색 조건. 공개 API(07: procedure, priceMax, language, sort)와
 * 내부 API(12 Conditions: procedureCode, budgetMaxKrw, consultLanguage, sortBy)가 같은 조건으로 변환해 쓴다.
 *
 * @param dateFrom 입국일 (포함)
 * @param dateTo 출국일 (포함)
 * @param hospitalIds 비교 등에서 특정 병원만 볼 때
 */
public record SearchCriteria(
		String procedureCode,
		List<String> areas,
		LocalDate dateFrom,
		LocalDate dateTo,
		Integer priceMax,
		String language,
		String sortBy,
		Double lat,
		Double lng,
		List<Long> hospitalIds) {

	public static final List<String> AREA_CODES =
			List.of("GANGNAM", "SINSA", "APGUJEONG", "CHEONGDAM", "MYEONGDONG", "HONGDAE", "JAMSIL");
	public static final List<String> SORT_BY = List.of("REVIEW_COUNT", "RATING", "PRICE", "DISTANCE");

	public static SearchCriteria forHospitals(List<Long> hospitalIds, String procedureCode) {
		return new SearchCriteria(procedureCode, null, null, null, null, null, null, null, null, hospitalIds);
	}
}
