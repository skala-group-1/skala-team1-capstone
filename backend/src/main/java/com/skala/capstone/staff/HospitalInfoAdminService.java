package com.skala.capstone.staff;

import java.sql.Array;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.skala.capstone.catalog.ReviewTranslations;
import com.skala.capstone.common.error.ApiException;
import com.skala.capstone.common.error.ErrorCode;
import com.skala.capstone.common.security.AuditLogger;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.web.AfterCommit;
import com.skala.capstone.common.web.Json;
import com.skala.capstone.staff.HospitalInfoAdminDtos.AdminDoctor;
import com.skala.capstone.staff.HospitalInfoAdminDtos.DayHours;
import com.skala.capstone.staff.HospitalInfoAdminDtos.DoctorRequest;
import com.skala.capstone.staff.HospitalInfoAdminDtos.HospitalInfo;
import com.skala.capstone.staff.HospitalInfoAdminDtos.ProcedureRef;
import com.skala.capstone.staff.HospitalInfoAdminDtos.UpdateHospitalRequest;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * 병원 관리자의 병원 정보·의료진 수정. 운영팀 검토 없이 바로 고객 화면에 반영된다 (정보 확인일 verifiedAt 은 운영팀 확인일이라 바꾸지 않음).
 * 병원 소개(한국어)를 바꾸면 translator 에 다른 언어 번역을 맡긴다 (review.translate 큐, kind = HOSPITAL).
 * 진료 시간을 바꿔도 이미 만든 예약 가능 시간(slots)·예약은 그대로다.
 */
@Service
public class HospitalInfoAdminService {

	private static final List<String> WEEKDAYS = List.of("mon", "tue", "wed", "thu", "fri", "sat", "sun");
	private static final List<String> LANGUAGE_ORDER = List.of("ko", "en", "zh", "ja");

	private final JdbcClient jdbc;
	private final Json json;
	private final ReviewTranslations translations;
	private final AuditLogger audit;

	public HospitalInfoAdminService(JdbcClient jdbc, Json json, ReviewTranslations translations, AuditLogger audit) {
		this.jdbc = jdbc;
		this.json = json;
		this.translations = translations;
		this.audit = audit;
	}

	@Transactional(readOnly = true)
	public HospitalInfo get(CurrentUser admin) {
		long h = admin.hospitalId();
		List<AdminDoctor> doctors = jdbc.sql("SELECT * FROM app.doctors WHERE hospital_id = :h ORDER BY id")
				.param("h", h).query(HospitalInfoAdminService::doctor).list();
		List<ProcedureRef> procedures = jdbc.sql("""
				SELECT p.code, p.name_ko FROM app.procedures p
				WHERE p.code IN (SELECT procedure_code FROM app.price_options WHERE hospital_id = :h)
				ORDER BY p.category, p.code
				""").param("h", h).query((rs, i) -> new ProcedureRef(rs.getString("code"), rs.getString("name_ko"))).list();
		return jdbc.sql("SELECT * FROM app.hospitals WHERE id = :h").param("h", h)
				.query((rs, i) -> new HospitalInfo(rs.getLong("id"), rs.getString("name_ko"), rs.getString("name_en"),
						rs.getString("phone"), rs.getString("address_ko"), rs.getString("address_en"),
						rs.getString("description_ko"), strings(rs.getArray("supported_languages")),
						rs.getBoolean("has_interpreter"), hours(rs.getString("open_hours")),
						rs.getObject("verified_at", LocalDate.class), doctors, procedures))
				.optional().orElseThrow(() -> ApiException.notFound("hospital"));
	}

	@Transactional
	public HospitalInfo update(CurrentUser admin, UpdateHospitalRequest req) {
		if (req.openHours() != null) {
			validateHours(req.openHours());
		}
		String before = jdbc.sql("SELECT description_ko FROM app.hospitals WHERE id = :h FOR UPDATE")
				.param("h", admin.hospitalId()).query(String.class).optional().orElse(null);
		String description = trim(req.descriptionKo());
		jdbc.sql("""
				UPDATE app.hospitals SET
				    phone = COALESCE(CAST(:phone AS varchar), phone),
				    address_ko = COALESCE(CAST(:addrKo AS varchar), address_ko),
				    address_en = COALESCE(CAST(:addrEn AS varchar), address_en),
				    description_ko = COALESCE(CAST(:desc AS text), description_ko),
				    supported_languages = COALESCE(string_to_array(CAST(:langs AS text), ','), supported_languages),
				    has_interpreter = COALESCE(CAST(:interp AS boolean), has_interpreter),
				    open_hours = COALESCE(CAST(:hours AS jsonb), open_hours)
				WHERE id = :h
				""")
				.param("phone", trim(req.phone())).param("addrKo", trim(req.addressKo()))
				.param("addrEn", trim(req.addressEn())).param("desc", description)
				.param("langs", req.languages() == null ? null : ordered(req.languages()))
				.param("interp", req.hasInterpreter())
				.param("hours", req.openHours() == null ? null : json.write(orderedHours(req.openHours())))
				.param("h", admin.hospitalId()).update();
		if (description != null && !description.equals(before)) {
			translations.requestHospitalAfterCommit(admin.hospitalId(), description, "ko");
		}
		AfterCommit.run(() -> audit.log(admin, "HOSPITAL_INFO_UPDATED", "hospital:" + admin.hospitalId(), Map.of()));
		return get(admin);
	}

	@Transactional
	public AdminDoctor addDoctor(CurrentUser admin, DoctorRequest req) {
		validateSpecialties(req);
		long id = jdbc.sql("""
				INSERT INTO app.doctors (hospital_id, name_ko, name_en, title, career_years, languages, specialties)
				VALUES (:h, :ko, :en, :title, :years, string_to_array(:langs, ','),
				        COALESCE(string_to_array(CAST(:spec AS text), ','), '{}'::text[]))
				RETURNING id
				""").param("h", admin.hospitalId()).params(doctorParams(req)).query(Long.class).single();
		AfterCommit.run(() -> audit.log(admin, "DOCTOR_ADDED", "doctor:" + id, Map.of()));
		return doctor(admin, id);
	}

	@Transactional
	public AdminDoctor updateDoctor(CurrentUser admin, long id, DoctorRequest req) {
		validateSpecialties(req);
		int n = jdbc.sql("""
				UPDATE app.doctors SET name_ko = :ko, name_en = :en, title = :title, career_years = :years,
				    languages = string_to_array(:langs, ','),
				    specialties = COALESCE(string_to_array(CAST(:spec AS text), ','), '{}'::text[])
				WHERE id = :id AND hospital_id = :h
				""").param("id", id).param("h", admin.hospitalId()).params(doctorParams(req)).update();
		if (n == 0) {
			throw ApiException.notFound("doctor");
		}
		AfterCommit.run(() -> audit.log(admin, "DOCTOR_UPDATED", "doctor:" + id, Map.of()));
		return doctor(admin, id);
	}

	private AdminDoctor doctor(CurrentUser admin, long id) {
		return jdbc.sql("SELECT * FROM app.doctors WHERE id = :id AND hospital_id = :h").param("id", id)
				.param("h", admin.hospitalId()).query(HospitalInfoAdminService::doctor).single();
	}

	private Map<String, Object> doctorParams(DoctorRequest req) {
		Map<String, Object> p = new LinkedHashMap<>();
		p.put("ko", req.nameKo().trim());
		p.put("en", trim(req.nameEn()));
		p.put("title", req.title());
		p.put("years", req.careerYears());
		p.put("langs", ordered(req.languages()));
		p.put("spec", req.specialties() == null || req.specialties().isEmpty() ? null
				: String.join(",", req.specialties().stream().distinct().toList()));
		return p;
	}

	/** 전문 시술은 시술 코드여야 한다 */
	private void validateSpecialties(DoctorRequest req) {
		if (req.specialties() == null || req.specialties().isEmpty()) {
			return;
		}
		List<String> codes = req.specialties().stream().distinct().toList();
		long known = jdbc.sql("SELECT count(*) FROM app.procedures WHERE code IN (:codes)").param("codes", codes)
				.query(Long.class).single();
		if (known != codes.size()) {
			throw new ApiException(ErrorCode.VALIDATION_FAILED,
					Map.of("fields", List.of(Map.of("field", "specialties", "reason", "unknown procedure code"))));
		}
	}

	/** 7개 요일 키가 모두 있어야 하고, 연 날은 시작 < 끝 */
	private static void validateHours(Map<String, DayHours> hours) {
		if (!hours.keySet().containsAll(WEEKDAYS) || hours.size() != WEEKDAYS.size()) {
			throw new ApiException(ErrorCode.VALIDATION_FAILED,
					Map.of("fields", List.of(Map.of("field", "openHours", "reason", "must have mon..sun"))));
		}
		hours.forEach((day, h) -> {
			if (h != null && h.open().compareTo(h.close()) >= 0) {
				throw new ApiException(ErrorCode.VALIDATION_FAILED,
						Map.of("fields", List.of(Map.of("field", "openHours." + day, "reason", "open must be before close"))));
			}
		});
	}

	private static Map<String, DayHours> orderedHours(Map<String, DayHours> hours) {
		Map<String, DayHours> out = new LinkedHashMap<>();
		WEEKDAYS.forEach(d -> out.put(d, hours.get(d)));
		return out;
	}

	private Map<String, DayHours> hours(String raw) {
		JsonNode node = json.read(raw);
		Map<String, DayHours> out = new LinkedHashMap<>();
		for (String d : WEEKDAYS) {
			JsonNode day = node == null ? null : node.get(d);
			out.put(d, day == null || day.isNull() ? null : new DayHours(day.path("open").asText(), day.path("close").asText()));
		}
		return out;
	}

	private static String ordered(List<String> langs) {
		return String.join(",", LANGUAGE_ORDER.stream().filter(langs::contains).toList());
	}

	private static String trim(String s) {
		return s == null ? null : s.trim();
	}

	private static List<String> strings(Array array) throws SQLException {
		return array == null ? List.of() : List.of((String[]) array.getArray());
	}

	private static AdminDoctor doctor(ResultSet rs, int i) throws SQLException {
		return new AdminDoctor(rs.getLong("id"), rs.getString("name_ko"), rs.getString("name_en"), rs.getString("title"),
				(Integer) rs.getObject("career_years"), strings(rs.getArray("languages")),
				strings(rs.getArray("specialties")));
	}
}
