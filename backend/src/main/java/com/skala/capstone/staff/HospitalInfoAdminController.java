package com.skala.capstone.staff;

import jakarta.validation.Valid;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.staff.HospitalInfoAdminDtos.AdminDoctor;
import com.skala.capstone.staff.HospitalInfoAdminDtos.DoctorRequest;
import com.skala.capstone.staff.HospitalInfoAdminDtos.HospitalInfo;
import com.skala.capstone.staff.HospitalInfoAdminDtos.UpdateHospitalRequest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/** 병원관리자 병원 정보·의료진 수정 API (URL 규칙으로 HOSPITAL_ADMIN 만, 토큰의 hospitalId 병원만). 바로 반영된다. */
@Tag(name = "Hospital admin")
@RestController
@RequestMapping("/api/hospital-admin/hospital")
public class HospitalInfoAdminController {

	private final HospitalInfoAdminService hospitals;

	public HospitalInfoAdminController(HospitalInfoAdminService hospitals) {
		this.hospitals = hospitals;
	}

	@Operation(summary = "우리 병원 정보 (수정용 원본 값: 한국어·영어, 의료진, 고를 수 있는 시술)")
	@GetMapping
	public HospitalInfo get(@AuthenticationPrincipal CurrentUser admin) {
		return hospitals.get(admin);
	}

	@Operation(summary = "병원 정보 수정 (보낸 필드만, 바로 반영. 소개를 바꾸면 다른 언어는 번역)")
	@PatchMapping
	public HospitalInfo update(@AuthenticationPrincipal CurrentUser admin, @Valid @RequestBody UpdateHospitalRequest req) {
		return hospitals.update(admin, req);
	}

	@Operation(summary = "의료진 추가")
	@PostMapping("/doctors")
	public ResponseEntity<AdminDoctor> addDoctor(@AuthenticationPrincipal CurrentUser admin,
			@Valid @RequestBody DoctorRequest req) {
		return ResponseEntity.status(HttpStatus.CREATED).body(hospitals.addDoctor(admin, req));
	}

	@Operation(summary = "의료진 수정 (전체 값)")
	@PutMapping("/doctors/{id}")
	public AdminDoctor updateDoctor(@AuthenticationPrincipal CurrentUser admin, @PathVariable long id,
			@Valid @RequestBody DoctorRequest req) {
		return hospitals.updateDoctor(admin, id, req);
	}
}
