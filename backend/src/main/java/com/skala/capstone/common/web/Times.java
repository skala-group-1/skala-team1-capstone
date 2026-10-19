package com.skala.capstone.common.web;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneId;

/** 일시는 ISO-8601 + 오프셋(+09:00)으로 내려준다. JDBC 드라이버는 UTC 오프셋으로 주므로 변환이 필요하다. */
public final class Times {

	public static final ZoneId SEOUL = ZoneId.of("Asia/Seoul");

	private Times() {
	}

	public static OffsetDateTime kst(OffsetDateTime t) {
		return t == null ? null : t.atZoneSameInstant(SEOUL).toOffsetDateTime();
	}

	public static OffsetDateTime startOfDay(LocalDate date) {
		return date.atStartOfDay(SEOUL).toOffsetDateTime();
	}
}
