package com.skala.capstone.common.config;

import java.time.Duration;
import java.util.List;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("app")
public record AppProperties(
		Jwt jwt,
		RefreshCookie refreshCookie,
		String serviceToken,
		Cors cors,
		Agent agent,
		Ai ai,
		Reservation reservation,
		Trip trip,
		Seed seed) {

	public record Jwt(String secret, String issuer, Duration accessTtl, Duration refreshTtl) {
	}

	public record RefreshCookie(String name, String path, boolean secure) {
	}

	public record Cors(List<String> allowedOrigins) {
	}

	/** backend → agent 내부 HTTP (문서 원문 조회) */
	public record Agent(String baseUrl, Duration timeout) {
	}

	/** AI 작업이 이 시간 넘게 진행이 없으면 실패 처리 */
	public record Ai(Duration taskTimeout) {
	}

	/** 예약 요청 시 슬롯을 잡아두는 시간 (기본 30분) */
	public record Reservation(Duration hold) {
	}

	/** 일정 적합성 계산: 회복 완료 후 출국까지 최소 여유일 */
	public record Trip(int minBufferDays) {
	}

	public record Seed(String demoPassword) {
	}
}
