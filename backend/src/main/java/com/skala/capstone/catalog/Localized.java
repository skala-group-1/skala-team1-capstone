package com.skala.capstone.catalog;

/** 다국어 컬럼(_ko/_en/_zh/_ja) 중 요청 locale 값을 고른다. 비어 있으면 en → ko 순으로 대체. */
final class Localized {

	private Localized() {
	}

	static String pick(String locale, String ko, String en, String zh, String ja) {
		return switch (locale == null ? "en" : locale) {
			case "ko" -> first(ko, en);
			case "zh" -> first(zh, en, ko);
			case "ja" -> first(ja, en, ko);
			default -> first(en, ko);
		};
	}

	private static String first(String... values) {
		for (String v : values) {
			if (v != null && !v.isBlank()) {
				return v;
			}
		}
		return null;
	}
}
