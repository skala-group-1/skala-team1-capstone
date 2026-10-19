package com.skala.capstone.notification;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.skala.capstone.common.security.CurrentUser;
import com.skala.capstone.common.web.PageResponse;
import com.skala.capstone.notification.NotificationService.Notification;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

/** 인앱 알림 (모든 역할). 실시간 수신은 STOMP /user/queue/notifications. */
@Tag(name = "Notification")
@Validated
@RestController
@RequestMapping("/api/notifications")
public class NotificationController {

	private final NotificationService notifications;

	public NotificationController(NotificationService notifications) {
		this.notifications = notifications;
	}

	@Operation(summary = "내 알림 목록 (최신순)")
	@GetMapping
	public PageResponse<Notification> list(@AuthenticationPrincipal CurrentUser user,
			@RequestParam(defaultValue = "false") boolean unreadOnly,
			@RequestParam(defaultValue = "0") @Min(0) int page,
			@RequestParam(defaultValue = "20") @Min(1) @Max(50) int size) {
		return notifications.list(user.id(), unreadOnly, page, size);
	}

	@Operation(summary = "알림 읽음 처리")
	@PostMapping("/{id}/read")
	public ResponseEntity<Void> read(@AuthenticationPrincipal CurrentUser user, @PathVariable long id) {
		notifications.markRead(user.id(), id);
		return ResponseEntity.noContent().build();
	}

	@Operation(summary = "모든 알림 읽음 처리")
	@PostMapping("/read-all")
	public ResponseEntity<Void> readAll(@AuthenticationPrincipal CurrentUser user) {
		notifications.markAllRead(user.id());
		return ResponseEntity.noContent().build();
	}
}
