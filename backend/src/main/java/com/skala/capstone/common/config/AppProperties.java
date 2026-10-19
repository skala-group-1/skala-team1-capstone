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
		Seed seed) {

	public record Jwt(String secret, String issuer, Duration accessTtl, Duration refreshTtl) {
	}

	public record RefreshCookie(String name, String path, boolean secure) {
	}

	public record Cors(List<String> allowedOrigins) {
	}

	public record Seed(String demoPassword) {
	}
}
