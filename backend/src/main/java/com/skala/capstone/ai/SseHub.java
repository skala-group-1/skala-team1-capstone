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
	/** 작업이 다시 재개되지 않는 진짜 끝 */
	private static final Set<String> FINAL = Set.of("DONE", "FAILED");
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
	 * <p>
	 * 승인 후 재개된 작업은 버퍼 중간에 이미 끝난 구간(… → APPROVAL_REQUIRED)이 남아 있다.
	 * 이 구간을 다시 보내면 브라우저가 승인 카드를 또 띄우고 스트림을 닫으므로,
	 * 이미 지나간 종료 이벤트(작업이 다시 실행 중이거나, 뒤에 이벤트가 더 있는 것)까지는 Last-Event-ID 가 없어도 건너뛴다.
	 */
	public SseEmitter subscribe(UUID taskId, int lastEventId, boolean stillRunning, Event fallback) {
		SseEmitter emitter = new SseEmitter(EMITTER_TIMEOUT_MS);
		Stream s = streams.computeIfAbsent(taskId, k -> new Stream());
		synchronized (s) {
			int from = Math.max(lastEventId, finishedSegmentEnd(s.buffer, stillRunning));
			List<Event> replay = s.buffer.stream().filter(e -> e.seq() > from).toList();
			for (Event e : replay) {
				if (!send(emitter, e)) {
					return emitter;
				}
			}
			// DB 상태를 읽은 직후 작업이 끝났으면(stillRunning=true 인데 버퍼 끝이 DONE·FAILED) 여기서 닫는다
			boolean finished = !replay.isEmpty() && FINAL.contains(replay.get(replay.size() - 1).event());
			if (!stillRunning || finished) {
				if (replay.isEmpty() && fallback != null && fallback.seq() > from) {
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

	/**
	 * 이미 끝난 앞 구간의 마지막 seq (없으면 0).
	 * 맨 끝 이벤트는 현재 상태라 보낸다. 단, 작업이 다시 실행 중인데 맨 끝이 APPROVAL_REQUIRED 면 이미 승인된 것이라 건너뛴다.
	 * DONE·FAILED 는 그 뒤로 재개되지 않으므로 맨 끝에 있으면 stillRunning 과 관계없이 보낸다
	 * (DB 상태를 읽은 직후 작업이 끝나는 경합에서 DONE 을 건너뛰어 스트림이 멈추지 않도록).
	 */
	static int finishedSegmentEnd(List<Event> buffer, boolean stillRunning) {
		int end = 0;
		for (int i = 0; i < buffer.size(); i++) {
			Event e = buffer.get(i);
			if (!TERMINAL.contains(e.event())) {
				continue;
			}
			boolean lastOne = i == buffer.size() - 1;
			if (lastOne && !(stillRunning && "APPROVAL_REQUIRED".equals(e.event()))) {
				break;
			}
			end = e.seq();
		}
		return end;
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
