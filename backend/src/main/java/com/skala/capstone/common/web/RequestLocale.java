package com.skala.capstone.common.web;

import java.util.Locale;
import java.util.Set;

import jakarta.servlet.http.HttpServletRequest;

import com.skala.capstone.common.security.CurrentUser;

/** 응답 언어 결정: 토큰 locale → Accept-Language → en (계약서 1장). */
public final class RequestLocale {

	public static final Set<String> SUPPORTED = Set.of("en", "zh", "ja", "ko");
	public static final String DEFAULT = "en";

	private RequestLocale() {
	}

	public static String resolve(HttpServletRequest request) {
		return CurrentUser.current().map(CurrentUser::locale).filter(SUPPORTED::contains)
				.orElseGet(() -> fromAcceptLanguage(request));
	}

	/** 명시적으로 받은 locale 파라미터가 있으면 우선 (내부 API용). */
	public static String resolve(String explicit, HttpServletRequest request) {
		if (explicit != null && SUPPORTED.contains(explicit)) {
			return explicit;
		}
		return resolve(request);
	}

	public static String fromAcceptLanguage(HttpServletRequest request) {
		if (request == null || request.getHeader("Accept-Language") == null) {
			return DEFAULT;
		}
		try {
			for (Locale.LanguageRange range : Locale.LanguageRange.parse(request.getHeader("Accept-Language"))) {
				String lang = range.getRange().split("-")[0].toLowerCase(Locale.ROOT);
				if (SUPPORTED.contains(lang)) {
					return lang;
				}
			}
		} catch (IllegalArgumentException ignored) {
			// 잘못된 헤더는 기본값
		}
		return DEFAULT;
	}
}
