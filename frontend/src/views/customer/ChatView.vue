<script setup lang="ts">
// 「화면 목록」 C4 AI 채팅 (메인/병원/상담사 모드 공용)
// TODO(fe): route.params.conversationId 로 conversation.load(), 없으면 open()
// TODO(fe): 메시지 목록 + 스트리밍 draft(TOKEN), 진행 칩(activeTools), 조건 칩 바(conditions·missing, 탭하면 수정)
// TODO(fe): RESULT_CARDS → 병원 카드 가로 스크롤, '이 병원 상담' → send(null, {type:'SELECT_HOSPITAL', hospitalId})
// TODO(fe): 0건 완화 선택지(relaxOptions) → send(null, {type:'RELAX', option})
// TODO(fe): CONVERSATION_OPENED(openedConversation) → router.push(`/chat/${conversationId}`)
// TODO(fe): 근거 칩(sources) → C4-1 근거 문서 바텀시트 (catalogApi.doc)
// TODO(fe): APPROVAL_REQUIRED(pendingAction) → C4-2 승인 카드(예약) / C4-3 니즈 요약 카드 + 동의(상담). 확인·수정·취소 → conversation.approve()
// TODO(fe): MODE_CHANGED HUMAN → 모드 배지 '상담사 연결됨' + consultation 스토어(STOMP)로 전환
// TODO(fe): TRIP_PLAN 일정 카드, MEMORY_PROPOSAL '기억할까요?' 칩
// TODO(fe): FAILED → 오류 + 재시도 버튼
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>

<template>
  <PagePlaceholder id="C4" title="AI 채팅 (메인/병원/상담사 모드 공용)" />
</template>
