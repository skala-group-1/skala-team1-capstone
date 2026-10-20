package com.skala.capstone.consultation;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.web.RequestLocale;
import com.skala.capstone.consultation.ConsultationDtos.Consultation;
import com.skala.capstone.consultation.ConsultationDtos.CreateConsultationRequest;

import io.swagger.v3.oas.annotations.tags.Tag;

/** business-mcp request_consultation (고객 승인 후에만 에이전트가 호출) */
@Tag(name = "Internal (business-mcp)")
@RestController
@RequestMapping("/internal/consultations")
public class InternalConsultationController {

	private final ConsultationService consultations;

	public InternalConsultationController(ConsultationService consultations) {
		this.consultations = consultations;
	}

	@PostMapping
	public ResponseEntity<Consultation> request(@AuthenticationPrincipal CurrentUser user,
			@Valid @RequestBody CreateConsultationRequest req, @RequestParam(required = false) String locale,
			HttpServletRequest request) {
		var r = consultations.request(user, req.hospitalId(), req.conversationId(), req.summaryCard(), req.consent(),
				RequestLocale.resolve(locale, request));
		return ResponseEntity.status(r.created() ? HttpStatus.CREATED : HttpStatus.OK).body(r.consultation());
	}
}
