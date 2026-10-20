package com.skala.capstone.consultation;

import java.util.List;

import jakarta.servlet.http.HttpServletRequest;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.web.RequestLocale;
import com.skala.capstone.consultation.ConsultationDtos.Consultation;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/** 상담사 문의함 (URL 규칙으로 COUNSELOR 만, 항상 자기 병원 기준). */
@Tag(name = "Counselor")
@RestController
@RequestMapping("/api/counselor/consultations")
public class CounselorController {

	private final ConsultationService consultations;

	public CounselorController(ConsultationService consultations) {
		this.consultations = consultations;
	}

	@Operation(summary = "우리 병원 상담 목록 (status: WAITING/ACTIVE/CLOSED)")
	@GetMapping
	public List<Consultation> inbox(@AuthenticationPrincipal CurrentUser counselor,
			@RequestParam(required = false) String status, HttpServletRequest request) {
		return consultations.inbox(counselor, status, RequestLocale.resolve(request));
	}

	@Operation(summary = "상담 수락 (WAITING → ACTIVE)")
	@PostMapping("/{id}/accept")
	public Consultation accept(@AuthenticationPrincipal CurrentUser counselor, @PathVariable long id,
			HttpServletRequest request) {
		return consultations.accept(counselor, id, RequestLocale.resolve(request));
	}

	@Operation(summary = "상담 종료 (→ CLOSED, 고객 대화창은 AI 응답 재개)")
	@PostMapping("/{id}/close")
	public Consultation close(@AuthenticationPrincipal CurrentUser counselor, @PathVariable long id,
			HttpServletRequest request) {
		return consultations.close(counselor, id, RequestLocale.resolve(request));
	}
}
