package com.skala.capstone.ai;

import java.util.UUID;

/**
 * AI 작업이 DONE 으로 끝났을 때 (Spring 이벤트). watched 는 그 순간 이 작업의 SSE 를 보고 있는 브라우저가 있었는지.
 * 다른 기능(예: 사후관리 알림)이 AiTaskService 를 고치지 않고 이어 붙이기 위한 연결점이다.
 */
public record AiTaskDone(UUID taskId, boolean watched) {
}
