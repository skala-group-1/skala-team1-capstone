package com.skala.capstone.catalog;

import java.sql.Array;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import java.util.stream.Collectors;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.skala.capstone.catalog.CatalogDtos.CompareColumn;
import com.skala.capstone.catalog.CatalogDtos.CompareResponse;
import com.skala.capstone.catalog.CatalogDtos.Doctor;
import com.skala.capstone.catalog.CatalogDtos.HospitalCard;
import com.skala.capstone.catalog.CatalogDtos.HospitalDetail;
import com.skala.capstone.catalog.CatalogDtos.PriceOption;
import com.skala.capstone.catalog.CatalogDtos.Procedure;
import com.skala.capstone.catalog.CatalogDtos.ProcedureCandidate;
import com.skala.capstone.catalog.CatalogDtos.ProcedureOptions;
import com.skala.capstone.catalog.CatalogDtos.Review;
import com.skala.capstone.catalog.CatalogDtos.ReviewStats;
import com.skala.capstone.catalog.CatalogDtos.SearchResult;
import com.skala.capstone.catalog.CatalogDtos.Slot;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.web.PageResponse;
import com.skala.capstone.common.web.Times;

/**
 * 탐색·상세·슬롯·비교 조회. 공개 API(/api)와 내부 API(/internal, business-mcp)가 이 서비스 하나를 공유한다 (07 문서 5장: 규칙 중복 금지).
 * 읽기 전용 + 동적 조건이 많아 JPA 대신 SQL(JdbcClient)로 조회한다.
 */
@Service
@Transactional(readOnly = true)
public class CatalogService {

	/** DISTANCE 정렬인데 좌표가 없을 때 쓰는 기준점 (서울시청). D-21: 지도 없이 mock 좌표로 계산 */
	static final double DEFAULT_LAT = 37.5665;
	static final double DEFAULT_LNG = 126.9780;

	private static final List<String> WEEKDAYS = List.of("mon", "tue", "wed", "thu", "fri", "sat", "sun");

	private final JdbcClient jdbc;
	private final ObjectMapper objectMapper;

	public CatalogService(JdbcClient jdbc, ObjectMapper objectMapper) {
		this.jdbc = jdbc;
		this.objectMapper = objectMapper;
	}

	// ---------------------------------------------------------------- procedures

	public List<Procedure> procedures(String locale) {
		return jdbc.sql("SELECT * FROM app.procedures ORDER BY category, code")
				.query((rs, i) -> procedure(rs, locale)).list();
	}

	/** 자유 텍스트(다국어·동의어) → 시술 코드 후보. 정확 일치 1.0, 부분 일치 0.8. */
	public List<ProcedureCandidate> normalize(String text, String locale) {
		String q = squash(text);
		if (q.isEmpty()) {
			return List.of();
		}
		record Row(Procedure procedure, List<String> terms) {
		}
		List<Row> rows = jdbc.sql("SELECT * FROM app.procedures").query((rs, i) -> {
			List<String> terms = new ArrayList<>(strings(rs, "synonyms"));
			terms.addAll(Arrays.asList(rs.getString("code"), rs.getString("name_ko"), rs.getString("name_en"),
					rs.getString("name_zh"), rs.getString("name_ja")));
			return new Row(procedure(rs, locale), terms);
		}).list();
		List<ProcedureCandidate> out = new ArrayList<>();
		for (Row row : rows) {
			double best = 0;
			for (String term : row.terms()) {
				String t = squash(term);
				if (t.isEmpty()) {
					continue;
				}
				if (t.equals(q)) {
					best = 1.0;
					break;
				}
				if (t.contains(q) || q.contains(t)) {
					best = Math.max(best, 0.8);
				}
			}
			if (best > 0) {
				out.add(new ProcedureCandidate(row.procedure().code(), row.procedure().name(), best));
			}
		}
		out.sort(Comparator.comparingDouble(ProcedureCandidate::score).reversed()
				.thenComparing(ProcedureCandidate::code));
		return out.size() > 5 ? out.subList(0, 5) : out;
	}

	/** 존재하지 않는 시술 코드면 422 UNKNOWN_PROCEDURE + 후보. */
	public void requireProcedure(String code, String locale) {
		Integer n = jdbc.sql("SELECT count(*) FROM app.procedures WHERE code = :code")
				.param("code", code).query(Integer.class).single();
		if (n == 0) {
			throw new ApiException(ErrorCode.UNKNOWN_PROCEDURE, Map.of("candidates", normalize(code, locale)));
		}
	}

	// ---------------------------------------------------------------- search

	public PageResponse<HospitalCard> search(SearchCriteria c, String locale, int page, int size) {
		SearchResult all = searchAll(c, locale, true);
		int from = Math.min(page * size, all.items().size());
		int to = Math.min(from + size, all.items().size());
		return new PageResponse<>(all.items().subList(from, to), page, size, all.total());
	}

	public SearchResult searchLimited(SearchCriteria c, String locale, int limit) {
		SearchResult all = searchAll(c, locale, true);
		return new SearchResult(all.items().subList(0, Math.min(limit, all.items().size())), all.total());
	}

	/**
	 * 조건에 맞는 병원 전체를 정렬해서 반환 (병원 50개 규모라 페이지는 메모리에서 자른다).
	 * - 시술 지정 시: 그 시술 가격 옵션이 있는 병원만, minPriceKrw = 그 시술 최저가
	 * - 날짜 지정 시: 입국일~출국일 사이에 예약 가능한(AVAILABLE) 슬롯이 있는 병원만
	 * - 슬롯은 시술 지정 시 그 시술을 하는 의사(specialties)의 슬롯만 본다
	 */
	private SearchResult searchAll(SearchCriteria c, String locale, boolean onlyOffering) {
		validate(c, locale);
		boolean byDistance = "DISTANCE".equals(c.sortBy());
		Double lat = c.lat() != null ? c.lat() : byDistance ? DEFAULT_LAT : null;
		Double lng = c.lng() != null ? c.lng() : byDistance ? DEFAULT_LNG : null;
		Map<String, Object> params = new LinkedHashMap<>();

		StringBuilder sql = new StringBuilder("WITH price AS (\n")
				.append("  SELECT DISTINCT ON (hospital_id) hospital_id, price_krw, verified_at IS NOT NULL AS verified\n")
				.append("  FROM app.price_options\n");
		if (c.procedureCode() != null) {
			sql.append("  WHERE procedure_code = :procedure\n");
			params.put("procedure", c.procedureCode());
		}
		sql.append("  ORDER BY hospital_id, price_krw, id\n), ")
				.append(earliestSlotCte(c.procedureCode(), c.dateFrom(), c.dateTo(), params))
				.append("""
						SELECT h.id, h.name_ko, h.name_en, h.name_zh, h.name_ja, h.area_code, h.category,
						       h.supported_languages, h.has_interpreter,
						       p.price_krw, p.verified, st.review_count, st.avg_rating, sl.earliest,
						""")
				.append(lat == null ? "       NULL::numeric" : "       " + distanceSql())
				.append(" AS distance_km\n")
				.append("""
						FROM app.hospitals h
						JOIN app.hospital_review_stats st ON st.hospital_id = h.id
						LEFT JOIN price p ON p.hospital_id = h.id
						LEFT JOIN slot sl ON sl.hospital_id = h.id
						WHERE 1 = 1
						""");
		if (lat != null) {
			params.put("lat", lat);
			params.put("lng", lng);
		}
		if (c.procedureCode() != null && onlyOffering) {
			sql.append(" AND p.hospital_id IS NOT NULL\n");
		}
		if (c.areas() != null && !c.areas().isEmpty()) {
			sql.append(" AND h.area_code IN (:areas)\n");
			params.put("areas", c.areas());
		}
		if (c.priceMax() != null) {
			sql.append(" AND p.price_krw <= :priceMax\n");
			params.put("priceMax", c.priceMax());
		}
		if (c.language() != null) {
			sql.append(" AND :language = ANY(h.supported_languages)\n");
			params.put("language", c.language());
		}
		if (c.dateFrom() != null || c.dateTo() != null) {
			sql.append(" AND sl.earliest IS NOT NULL\n");
		}
		if (c.hospitalIds() != null && !c.hospitalIds().isEmpty()) {
			sql.append(" AND h.id IN (:ids)\n");
			params.put("ids", c.hospitalIds());
		}
		sql.append(" ORDER BY ").append(switch (c.sortBy() == null ? "REVIEW_COUNT" : c.sortBy()) {
			case "RATING" -> "st.avg_rating DESC NULLS LAST, st.review_count DESC";
			case "PRICE" -> "p.price_krw ASC NULLS LAST, st.review_count DESC";
			case "DISTANCE" -> "distance_km ASC NULLS LAST";
			default -> "st.review_count DESC, st.avg_rating DESC NULLS LAST";
		}).append(", h.id");

		List<HospitalCard> items = jdbc.sql(sql.toString()).params(params).query((rs, i) -> new HospitalCard(
				rs.getLong("id"),
				Localized.pick(locale, rs.getString("name_ko"), rs.getString("name_en"), rs.getString("name_zh"),
						rs.getString("name_ja")),
				rs.getString("area_code"),
				rs.getString("category"),
				(Integer) rs.getObject("price_krw"),
				(Boolean) rs.getObject("verified"),
				rs.getLong("review_count"),
				doubleOrNull(rs, "avg_rating"),
				strings(rs, "supported_languages"),
				rs.getBoolean("has_interpreter"),
				Times.kst(rs.getObject("earliest", OffsetDateTime.class)),
				doubleOrNull(rs, "distance_km"))).list();
		return new SearchResult(items, items.size());
	}

	private void validate(SearchCriteria c, String locale) {
		List<Map<String, String>> fields = new ArrayList<>();
		if (c.areas() != null) {
			c.areas().stream().filter(a -> !SearchCriteria.AREA_CODES.contains(a))
					.forEach(a -> fields.add(Map.of("field", "areas", "reason", "unknown area " + a)));
		}
		if (c.sortBy() != null && !SearchCriteria.SORT_BY.contains(c.sortBy())) {
			fields.add(Map.of("field", "sortBy", "reason", "one of " + SearchCriteria.SORT_BY));
		}
		if (c.language() != null && !List.of("en", "zh", "ja", "ko").contains(c.language())) {
			fields.add(Map.of("field", "language", "reason", "one of en, zh, ja, ko"));
		}
		if (c.dateFrom() != null && c.dateTo() != null && c.dateFrom().isAfter(c.dateTo())) {
			fields.add(Map.of("field", "dateTo", "reason", "must not be before dateFrom"));
		}
		if ((c.lat() == null) != (c.lng() == null)) {
			fields.add(Map.of("field", "lat/lng", "reason", "both required"));
		}
		if (!fields.isEmpty()) {
			throw new ApiException(ErrorCode.VALIDATION_FAILED, Map.of("fields", fields));
		}
		if (c.procedureCode() != null) {
			requireProcedure(c.procedureCode(), locale);
		}
	}

	/** slot CTE: 병원별 가장 이른 AVAILABLE 슬롯 (현재 이후, 날짜 범위·시술 담당 의사 조건). */
	private String earliestSlotCte(String procedureCode, LocalDate dateFrom, LocalDate dateTo,
			Map<String, Object> params) {
		StringBuilder sql = new StringBuilder("""
				slot AS (
				  SELECT s.hospital_id, min(s.start_at) AS earliest
				  FROM app.slots s LEFT JOIN app.doctors d ON d.id = s.doctor_id
				  WHERE s.status = 'AVAILABLE' AND s.start_at > now()
				""");
		appendSlotFilters(sql, procedureCode, dateFrom, dateTo, params);
		return sql.append("  GROUP BY s.hospital_id\n)\n").toString();
	}

	private static void appendSlotFilters(StringBuilder sql, String procedureCode, LocalDate dateFrom,
			LocalDate dateTo, Map<String, Object> params) {
		if (dateFrom != null) {
			sql.append("    AND s.start_at >= :fromTs\n");
			params.put("fromTs", Times.startOfDay(dateFrom));
		}
		if (dateTo != null) {
			sql.append("    AND s.start_at < :toTs\n");
			params.put("toTs", Times.startOfDay(dateTo.plusDays(1)));
		}
		if (procedureCode != null) {
			sql.append("    AND (s.doctor_id IS NULL OR :procedure = ANY(d.specialties))\n");
			params.put("procedure", procedureCode);
		}
	}

	private static String distanceSql() {
		return "round((6371 * 2 * asin(sqrt(power(sin(radians(h.lat - :lat) / 2), 2)"
				+ " + cos(radians(:lat)) * cos(radians(h.lat)) * power(sin(radians(h.lng - :lng) / 2), 2))))::numeric, 1)";
	}

	// ---------------------------------------------------------------- detail

	public HospitalDetail detail(long hospitalId, String locale, boolean lite) {
		HospitalDetail base = jdbc.sql("SELECT * FROM app.hospitals WHERE id = :id").param("id", hospitalId)
				.query((rs, i) -> {
					// 주소는 한국어/영어 두 벌만 있다
					String address = Localized.pick("ko".equals(locale) ? "ko" : "en", rs.getString("address_ko"),
							rs.getString("address_en"), null, null);
					return new HospitalDetail(
							rs.getLong("id"),
							Localized.pick(locale, rs.getString("name_ko"), rs.getString("name_en"),
									rs.getString("name_zh"), rs.getString("name_ja")),
							rs.getString("name_ko"),
							rs.getString("category"),
							rs.getString("area_code"),
							address,
							rs.getString("phone"),
							Localized.pick(locale, rs.getString("description_ko"), rs.getString("description_en"),
									rs.getString("description_zh"), rs.getString("description_ja")),
							openHours(rs.getString("open_hours")),
							strings(rs, "supported_languages"),
							rs.getBoolean("has_interpreter"),
							rs.getObject("verified_at", LocalDate.class),
							null, null, null);
				}).optional().orElseThrow(() -> ApiException.notFound("hospital"));
		if (lite) {
			return base;
		}
		Map<String, Procedure> procedures = procedures(locale).stream()
				.collect(Collectors.toMap(Procedure::code, Function.identity()));
		Map<String, List<PriceOption>> byProcedure = new LinkedHashMap<>();
		for (PriceOption o : prices(hospitalId, null, locale)) {
			byProcedure.computeIfAbsent(o.procedureCode(), k -> new ArrayList<>()).add(o);
		}
		List<ProcedureOptions> offered = byProcedure.entrySet().stream()
				.map(e -> new ProcedureOptions(procedures.get(e.getKey()), e.getValue())).toList();
		return new HospitalDetail(base.id(), base.name(), base.nameKo(), base.category(), base.areaCode(),
				base.address(), base.phone(), base.description(), base.openHours(), base.languages(),
				base.hasInterpreter(), base.verifiedAt(), doctors(hospitalId, null, locale), offered,
				reviewStats(hospitalId));
	}

	public List<Doctor> doctors(long hospitalId, String procedureCode, String locale) {
		requireHospital(hospitalId);
		if (procedureCode != null) {
			requireProcedure(procedureCode, locale);
		}
		String sql = "SELECT * FROM app.doctors WHERE hospital_id = :id"
				+ (procedureCode != null ? " AND :procedure = ANY(specialties)" : "") + " ORDER BY id";
		var spec = jdbc.sql(sql).param("id", hospitalId);
		if (procedureCode != null) {
			spec = spec.param("procedure", procedureCode);
		}
		return spec.query((rs, i) -> new Doctor(
				rs.getLong("id"),
				"ko".equals(locale) || rs.getString("name_en") == null ? rs.getString("name_ko") : rs.getString("name_en"),
				rs.getString("title"),
				strings(rs, "specialties"),
				strings(rs, "languages"),
				(Integer) rs.getObject("career_years"))).list();
	}

	public List<PriceOption> prices(long hospitalId, String procedureCode, String locale) {
		requireHospital(hospitalId);
		if (procedureCode != null) {
			requireProcedure(procedureCode, locale);
		}
		String sql = """
				SELECT po.* FROM app.price_options po JOIN app.procedures p ON p.code = po.procedure_code
				WHERE po.hospital_id = :id
				""" + (procedureCode != null ? " AND po.procedure_code = :procedure" : "")
				+ " ORDER BY p.category, po.procedure_code, po.price_krw, po.id";
		var spec = jdbc.sql(sql).param("id", hospitalId);
		if (procedureCode != null) {
			spec = spec.param("procedure", procedureCode);
		}
		return spec.query((rs, i) -> priceOption(rs, locale)).list();
	}

	/** 예약 가능한(AVAILABLE) 미래 슬롯, 시작 시각 순. 시술 지정 시 그 시술 담당 의사 슬롯만. */
	public List<Slot> slots(long hospitalId, String procedureCode, LocalDate dateFrom, LocalDate dateTo,
			Long doctorId, int limit, String locale) {
		requireHospital(hospitalId);
		if (procedureCode != null) {
			requireProcedure(procedureCode, locale);
		}
		Map<String, Object> params = new LinkedHashMap<>();
		params.put("id", hospitalId);
		params.put("limit", limit);
		StringBuilder sql = new StringBuilder("""
				SELECT s.id, s.start_at, s.end_at, s.doctor_id, s.status, d.name_ko, d.name_en
				FROM app.slots s LEFT JOIN app.doctors d ON d.id = s.doctor_id
				WHERE s.hospital_id = :id AND s.status = 'AVAILABLE' AND s.start_at > now()
				""");
		appendSlotFilters(sql, procedureCode, dateFrom, dateTo, params);
		if (doctorId != null) {
			sql.append("    AND s.doctor_id = :doctorId\n");
			params.put("doctorId", doctorId);
		}
		sql.append(" ORDER BY s.start_at, s.id LIMIT :limit");
		return jdbc.sql(sql.toString()).params(params).query((rs, i) -> slot(rs, locale)).list();
	}

	// ---------------------------------------------------------------- 단건 조회 (예약·일정 응답 조립용)

	/** 슬롯 단건 (상태 무관) */
	public Optional<Slot> slot(long slotId, String locale) {
		return jdbc.sql("""
				SELECT s.id, s.start_at, s.end_at, s.doctor_id, s.status, d.name_ko, d.name_en
				FROM app.slots s LEFT JOIN app.doctors d ON d.id = s.doctor_id WHERE s.id = :id
				""").param("id", slotId).query((rs, i) -> slot(rs, locale)).optional();
	}

	/** 여러 슬롯을 요청한 id 순서대로 (없는 id 는 건너뜀) */
	public List<Slot> slotsByIds(List<Long> ids, String locale) {
		if (ids == null || ids.isEmpty()) {
			return List.of();
		}
		Map<Long, Slot> byId = jdbc.sql("""
				SELECT s.id, s.start_at, s.end_at, s.doctor_id, s.status, d.name_ko, d.name_en
				FROM app.slots s LEFT JOIN app.doctors d ON d.id = s.doctor_id WHERE s.id IN (:ids)
				""").param("ids", ids).query((rs, i) -> slot(rs, locale)).list().stream()
				.collect(Collectors.toMap(Slot::id, Function.identity()));
		return ids.stream().map(byId::get).filter(java.util.Objects::nonNull).toList();
	}

	/**
	 * 요청 시각에서 가장 가까운 예약 가능 슬롯 (SLOT_UNAVAILABLE 의 대안 제시용).
	 * 같은 병원, 현재 이후, 시술 담당 의사 슬롯만.
	 */
	public List<Slot> nearestAvailableSlots(long hospitalId, String procedureCode, OffsetDateTime around,
			long excludeSlotId, int limit, String locale) {
		return jdbc.sql("""
				SELECT s.id, s.start_at, s.end_at, s.doctor_id, s.status, d.name_ko, d.name_en
				FROM app.slots s LEFT JOIN app.doctors d ON d.id = s.doctor_id
				WHERE s.hospital_id = :h AND s.status = 'AVAILABLE' AND s.start_at > now() AND s.id <> :ex
				  AND (s.doctor_id IS NULL OR :procedure = ANY(d.specialties))
				ORDER BY abs(extract(epoch FROM s.start_at - CAST(:around AS timestamptz))), s.start_at
				LIMIT :limit
				""").param("h", hospitalId).param("procedure", procedureCode).param("around", around)
				.param("ex", excludeSlotId).param("limit", limit)
				.query((rs, i) -> slot(rs, locale)).list();
	}

	public Optional<Procedure> procedure(String code, String locale) {
		return jdbc.sql("SELECT * FROM app.procedures WHERE code = :c").param("c", code)
				.query((rs, i) -> procedure(rs, locale)).optional();
	}

	public Optional<PriceOption> priceOption(long id, String locale) {
		return jdbc.sql("SELECT * FROM app.price_options WHERE id = :id").param("id", id)
				.query((rs, i) -> priceOption(rs, locale)).optional();
	}

	/** 병원 이름 (요청자 locale) */
	public Optional<String> hospitalName(long hospitalId, String locale) {
		return jdbc.sql("SELECT name_ko, name_en, name_zh, name_ja FROM app.hospitals WHERE id = :id")
				.param("id", hospitalId)
				.query((rs, i) -> Localized.pick(locale, rs.getString("name_ko"), rs.getString("name_en"),
						rs.getString("name_zh"), rs.getString("name_ja")))
				.optional();
	}

	// ---------------------------------------------------------------- reviews

	public ReviewStats reviewStats(long hospitalId) {
		return jdbc.sql("SELECT * FROM app.hospital_review_stats WHERE hospital_id = :id").param("id", hospitalId)
				.query((rs, i) -> {
					Map<String, Long> byAge = new LinkedHashMap<>();
					for (String g : List.of("20s", "30s", "40s", "50s")) {
						byAge.put(g, rs.getLong("age_" + g + "_count"));
					}
					Map<String, Long> byGender = new LinkedHashMap<>();
					byGender.put("F", rs.getLong("female_count"));
					byGender.put("M", rs.getLong("male_count"));
					byGender.put("X", rs.getLong("other_gender_count"));
					return new ReviewStats(rs.getLong("review_count"), doubleOrNull(rs, "avg_rating"), byAge, byGender);
				}).optional().orElseThrow(() -> ApiException.notFound("hospital"));
	}

	public PageResponse<Review> reviews(long hospitalId, String lang, int page, int size) {
		requireHospital(hospitalId);
		String where = " WHERE hospital_id = :id" + (lang != null ? " AND lang = :lang" : "");
		Map<String, Object> params = new LinkedHashMap<>();
		params.put("id", hospitalId);
		if (lang != null) {
			params.put("lang", lang);
		}
		long total = jdbc.sql("SELECT count(*) FROM app.reviews" + where).params(params).query(Long.class).single();
		params.put("limit", size);
		params.put("offset", (long) page * size);
		List<Review> items = jdbc.sql("SELECT * FROM app.reviews" + where
				+ " ORDER BY created_at DESC, id DESC LIMIT :limit OFFSET :offset").params(params)
				.query((rs, i) -> new Review(
						rs.getLong("id"),
						rs.getString("procedure_code"),
						rs.getInt("rating"),
						rs.getString("age_group"),
						rs.getString("gender"),
						rs.getString("reviewer_nationality"),
						rs.getString("lang"),
						rs.getString("content"),
						Times.kst(rs.getObject("created_at", OffsetDateTime.class)))).list();
		return new PageResponse<>(items, page, size, total);
	}

	// ---------------------------------------------------------------- compare

	/** 요청한 병원 순서대로 열을 만든다. 그 시술을 안 하는 병원도 열은 두고 options 를 비운다. */
	public CompareResponse compare(List<Long> hospitalIds, String procedureCode, String locale) {
		List<Long> ids = hospitalIds.stream().distinct().toList();
		Map<Long, HospitalCard> cards = searchAll(SearchCriteria.forHospitals(ids, procedureCode), locale, false)
				.items().stream().collect(Collectors.toMap(HospitalCard::id, Function.identity()));
		List<CompareColumn> columns = new ArrayList<>();
		for (Long id : ids) {
			HospitalCard card = cards.get(id);
			if (card == null) {
				throw ApiException.notFound("hospital");
			}
			List<PriceOption> options = prices(id, procedureCode, locale);
			LocalDate verifiedAt = options.isEmpty() || options.stream().anyMatch(o -> o.verifiedAt() == null) ? null
					: options.stream().map(PriceOption::verifiedAt).min(Comparator.naturalOrder()).orElse(null);
			columns.add(new CompareColumn(card, options, card.earliestSlotAt(), verifiedAt));
		}
		return new CompareResponse(procedureCode, columns);
	}

	// ---------------------------------------------------------------- helpers

	public void requireHospital(long hospitalId) {
		Integer n = jdbc.sql("SELECT count(*) FROM app.hospitals WHERE id = :id").param("id", hospitalId)
				.query(Integer.class).single();
		if (n == 0) {
			throw ApiException.notFound("hospital");
		}
	}

	private static Procedure procedure(ResultSet rs, String locale) throws SQLException {
		return new Procedure(rs.getString("code"), rs.getString("category"),
				Localized.pick(locale, rs.getString("name_ko"), rs.getString("name_en"), rs.getString("name_zh"),
						rs.getString("name_ja")),
				(Integer) rs.getObject("duration_min"), (Integer) rs.getObject("downtime_days"));
	}

	private static PriceOption priceOption(ResultSet rs, String locale) throws SQLException {
		return new PriceOption(
				rs.getLong("id"),
				rs.getString("procedure_code"),
				rs.getString("product"),
				rs.getString("dose"),
				rs.getInt("price_krw"),
				rs.getBoolean("vat_included"),
				"ko".equals(locale) ? rs.getString("conditions_ko") : rs.getString("conditions_en"),
				rs.getObject("verified_at", LocalDate.class));
	}

	private static Slot slot(ResultSet rs, String locale) throws SQLException {
		return new Slot(
				rs.getLong("id"),
				Times.kst(rs.getObject("start_at", OffsetDateTime.class)),
				Times.kst(rs.getObject("end_at", OffsetDateTime.class)),
				(Long) rs.getObject("doctor_id"),
				rs.getObject("doctor_id") == null ? null
						: "ko".equals(locale) || rs.getString("name_en") == null ? rs.getString("name_ko")
								: rs.getString("name_en"),
				rs.getString("status"));
	}

	private static List<String> strings(ResultSet rs, String column) throws SQLException {
		Array array = rs.getArray(column);
		return array == null ? List.of() : List.of((String[]) array.getArray());
	}

	private static Double doubleOrNull(ResultSet rs, String column) throws SQLException {
		Number n = (Number) rs.getObject(column);
		return n == null ? null : n.doubleValue();
	}

	/** jsonb 는 키가 알파벳순으로 저장되므로 요일 순서(mon~sun)로 다시 정렬한다. 휴무일은 null. */
	private Map<String, Object> openHours(String json) {
		try {
			Map<String, Object> raw = json == null ? Map.of()
					: objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {
					});
			Map<String, Object> ordered = new LinkedHashMap<>();
			WEEKDAYS.forEach(d -> ordered.put(d, raw.get(d)));
			return ordered;
		} catch (JsonProcessingException e) {
			throw new IllegalStateException("invalid open_hours json", e);
		}
	}

	private static String squash(String s) {
		return s == null ? "" : s.toLowerCase(Locale.ROOT).replaceAll("[\\s_\\-()]+", "");
	}
}
