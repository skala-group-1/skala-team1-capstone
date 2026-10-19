package com.skala.capstone.ai;

import java.io.IOException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * AI 작업 진행 상황을 브라우저로 흘려보내는 SSE 중계소 (12 계약서 6장, 16 명세 6-3).
 * - 작업별로 받은 이벤트를 메모리에 모아 두고(버퍼), 재연결하면 Last-Event-ID 이후만 다시 보낸다
 * - 종료 이벤트(DONE·FAILED·APPROVAL_REQUIRED)를 보내면 연결을 닫는다
 * - 15초마다 빈 주석(ping)으로 연결 유지, 끝난 작업 버퍼는 10분 뒤 정리
 * 단일 backend 인스턴스 기준이다 (여러 대로 늘리면 Redis 등 공유 버퍼가 필요).
 */
@Component
public class SseHub {

	public static final Set<String> TERMINAL = Set.of("DONE", "FAILED", "APPROVAL_REQUIRED");
	private static final long EMITTER_TIMEOUT_MS = 5 * 60 * 1000L;

	public record Event(int seq, String event, JsonNode data) {
	}

	private static final class Stream {
		final List<Event> buffer = new ArrayList<>();
		final List<SseEmitter> emitters = new CopyOnWriteArrayList<>();
		volatile Instant lastActivity = Instant.now();
	}

	private final Map<UUID, Stream> streams = new ConcurrentHashMap<>();

	/** agent 이벤트(또는 backend 가 만든 이벤트)를 버퍼에 넣고 연결된 브라우저에 보낸다 */
	public void publish(UUID taskId, Event e) {
		Stream s = streams.computeIfAbsent(taskId, k -> new Stream());
		synchronized (s) {
			s.buffer.add(e);
			s.lastActivity = Instant.now();
			for (SseEmitter emitter : s.emitters) {
				if (!send(emitter, e)) {
					s.emitters.remove(emitter);
				} else if (TERMINAL.contains(e.event())) {
					emitter.complete();
					s.emitters.remove(emitter);
				}
			}
		}
	}

	/**
	 * 새 연결. 버퍼에서 lastEventId 이후 이벤트를 다시 보내고,
	 * stillRunning=false(작업이 대기·종료 상태)면 마지막 이벤트까지 보낸 뒤 닫는다.
	 * 버퍼가 비어 있고 작업이 이미 끝났으면 fallback(DB 값으로 만든 종료 이벤트)을 보낸다.
	 */
	public SseEmitter subscribe(UUID taskId, int lastEventId, boolean stillRunning, Event fallback) {
		SseEmitter emitter = new SseEmitter(EMITTER_TIMEOUT_MS);
		Stream s = streams.computeIfAbsent(taskId, k -> new Stream());
		synchronized (s) {
			List<Event> replay = s.buffer.stream().filter(e -> e.seq() > lastEventId).toList();
			for (Event e : replay) {
				if (!send(emitter, e)) {
					return emitter;
				}
			}
			if (!stillRunning) {
				if (replay.isEmpty() && fallback != null && fallback.seq() > lastEventId) {
					send(emitter, fallback);
				}
				emitter.complete();
				return emitter;
			}
			s.emitters.add(emitter);
			s.lastActivity = Instant.now();
		}
		emitter.onCompletion(() -> s.emitters.remove(emitter));
		emitter.onTimeout(() -> s.emitters.remove(emitter));
		emitter.onError(t -> s.emitters.remove(emitter));
		return emitter;
	}

	@Scheduled(fixedDelayString = "PT15S")
	public void heartbeat() {
		for (Stream s : streams.values()) {
			for (SseEmitter emitter : s.emitters) {
				try {
					emitter.send(SseEmitter.event().comment("ping"));
				} catch (IOException | IllegalStateException e) {
					s.emitters.remove(emitter);
				}
			}
		}
	}

	@Scheduled(fixedDelayString = "PT1M")
	public void cleanup() {
		Instant cutoff = Instant.now().minusSeconds(600);
		streams.entrySet().removeIf(en -> en.getValue().emitters.isEmpty()
				&& en.getValue().lastActivity.isBefore(cutoff));
	}

	private static boolean send(SseEmitter emitter, Event e) {
		try {
			emitter.send(SseEmitter.event().id(String.valueOf(e.seq())).name(e.event()).data(e.data()));
			return true;
		} catch (IOException | IllegalStateException ex) {
			emitter.completeWithError(ex);
			return false;
		}
	}
}
