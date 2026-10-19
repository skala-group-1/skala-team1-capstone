package com.skala.capstone.common.web;

import java.util.Arrays;
import java.util.stream.Collectors;

/** 스태프 화면에 보이는 고객 이름 마스킹: 단어별 첫 글자 + "**" ("Emily Carter" → "E** C**", "李晓梅" → "李**"). */
public final class Masking {

	private Masking() {
	}

	public static String name(String name) {
		if (name == null || name.isBlank()) {
			return name;
		}
		return Arrays.stream(name.trim().split("\\s+"))
				.map(w -> w.codePoints().limit(1)
						.collect(StringBuilder::new, StringBuilder::appendCodePoint, StringBuilder::append) + "**")
				.collect(Collectors.joining(" "));
	}
}
