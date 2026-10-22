package com.skala.capstone.aftercare;

import java.util.List;

import jakarta.servlet.http.HttpServletRequest;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.aftercare.AftercareDtos.AftercareConversation;
import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.web.RequestLocale;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/** 시술 사후관리 대화방 API. 대화 메시지·작업은 기존 /api/ai/** 를 그대로 쓴다. */
@Tag(name = "Aftercare")
@RestController
@RequestMapping("/api")
public class AftercareController {

	private final AftercareService aftercare;

	public AftercareController(AftercareService aftercare) {
		this.aftercare = aftercare;
	}

	@Operation(summary = "확정 예약의 사후관리 대화방 열기. 새로 만들면 201 + AI 첫 안내 요청, 이미 있으면 200")
	@PreAuthorize("hasRole('CUSTOMER')")
	@PostMapping("/reservations/{id}/aftercare-conversation")
	public ResponseEntity<AftercareConversation> open(@AuthenticationPrincipal CurrentUser user, @PathVariable long id,
			HttpServletRequest request) {
		var result = aftercare.open(user, id, RequestLocale.resolve(request));
		return ResponseEntity.status(result.created() ? HttpStatus.CREATED : HttpStatus.OK).body(result.conversation());
	}

	@Operation(summary = "내 사후관리 대화방 목록 (최신순)")
	@PreAuthorize("hasRole('CUSTOMER')")
	@GetMapping("/aftercare/conversations")
	public List<AftercareConversation> mine(@AuthenticationPrincipal CurrentUser user, HttpServletRequest request) {
		return aftercare.mine(user, RequestLocale.resolve(request));
	}
}
