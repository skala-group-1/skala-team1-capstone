package com.skala.capstone.ai;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;

import org.junit.jupiter.api.Test;

/** 재연결 시 버퍼 어디부터 다시 보낼지 (Last-Event-ID 없을 때) */
class SseHubTest {

	private static SseHub.Event ev(int seq, String name) {
		return new SseHub.Event(seq, name, null);
	}

	@Test
	void 승인_후_재개_중이면_승인카드까지_건너뜀() {
		var buffer = List.of(ev(1, "TOKEN"), ev(2, "APPROVAL_REQUIRED"));
		assertThat(SseHub.finishedSegmentEnd(buffer, true)).isEqualTo(2);
	}

	@Test
	void 승인_대기_중_새로고침이면_승인카드를_다시_보냄() {
		var buffer = List.of(ev(1, "TOKEN"), ev(2, "APPROVAL_REQUIRED"));
		assertThat(SseHub.finishedSegmentEnd(buffer, false)).isZero();
	}

	@Test
	void 끝난_작업은_앞_구간만_건너뛰고_DONE_을_보냄() {
		var buffer = List.of(ev(1, "APPROVAL_REQUIRED"), ev(2, "STATUS"), ev(3, "DONE"));
		assertThat(SseHub.finishedSegmentEnd(buffer, false)).isEqualTo(1);
	}

	@Test
	void 실행중으로_읽었는데_방금_끝났으면_DONE_을_건너뛰지_않음() {
		// DB 에서 RUNNING 을 읽은 직후 DONE 이 버퍼에 들어온 경합
		var buffer = List.of(ev(1, "STATUS"), ev(2, "TOKEN"), ev(3, "DONE"));
		assertThat(SseHub.finishedSegmentEnd(buffer, true)).isZero();

		var resumed = List.of(ev(1, "APPROVAL_REQUIRED"), ev(2, "STATUS"), ev(3, "FAILED"));
		assertThat(SseHub.finishedSegmentEnd(resumed, true)).isEqualTo(1);
	}
}
