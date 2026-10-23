package com.skala.capstone.staff;

import jakarta.validation.Valid;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.staff.CounselorAdminDtos.Counselor;
import com.skala.capstone.staff.CounselorAdminDtos.CounselorRoster;
import com.skala.capstone.staff.CounselorAdminDtos.CreateCounselorRequest;
import com.skala.capstone.staff.CounselorAdminDtos.UpdateCounselorRequest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/** 병원관리자 상담사 관리 API (URL 규칙으로 HOSPITAL_ADMIN 만, 토큰의 hospitalId 기준). */
@Tag(name = "Hospital admin")
@RestController
@RequestMapping("/api/hospital-admin/counselors")
public class CounselorAdminController {

	private final CounselorAdminService counselors;

	public CounselorAdminController(CounselorAdminService counselors) {
		this.counselors = counselors;
	}

	@Operation(summary = "우리 병원 상담사 목록 + 대기 문의 수")
	@GetMapping
	public CounselorRoster list(@AuthenticationPrincipal CurrentUser admin) {
		return counselors.roster(admin);
	}

	@Operation(summary = "상담사 계정 만들기 (초기 비밀번호 지정, 이메일 중복이면 409 EMAIL_DUPLICATED)")
	@PostMapping
	public ResponseEntity<Counselor> create(@AuthenticationPrincipal CurrentUser admin,
			@Valid @RequestBody CreateCounselorRequest req) {
		return ResponseEntity.status(HttpStatus.CREATED).body(counselors.create(admin, req));
	}

	@Operation(summary = "이름·상담 언어·새 문의 받기 수정 (보낸 필드만)")
	@PatchMapping("/{id}")
	public Counselor update(@AuthenticationPrincipal CurrentUser admin, @PathVariable long id,
			@Valid @RequestBody UpdateCounselorRequest req) {
		return counselors.update(admin, id, req);
	}

	@Operation(summary = "비활성으로 전환 (진행 중 상담이 있으면 409 INVALID_STATE_TRANSITION)")
	@PostMapping("/{id}/deactivate")
	public Counselor deactivate(@AuthenticationPrincipal CurrentUser admin, @PathVariable long id) {
		return counselors.deactivate(admin, id);
	}

	@Operation(summary = "다시 활성으로 전환")
	@PostMapping("/{id}/activate")
	public Counselor activate(@AuthenticationPrincipal CurrentUser admin, @PathVariable long id) {
		return counselors.activate(admin, id);
	}
}
