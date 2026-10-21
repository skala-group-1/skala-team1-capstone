// 「API·이벤트 명세」 2장 AI 상담. 실시간 진행은 sse.ts 의 streamTask 로 받는다
import type {
  AiTask,
  ApprovalRequest,
  Conversation,
  CreateConversationRequest,
  CreateTaskRequest,
  CreateTaskResponse,
  Uuid,
} from '@/types/contract'
import { http } from './http'

function normalizeConversation(conversation: Conversation): Conversation {
  return {
    ...conversation,
    conditions: conversation.conditions
      ? { ...conversation.conditions, areas: conversation.conditions.areas ?? [] }
      : conversation.conditions,
    messages: (conversation.messages ?? []).map((message) => ({
      ...message, sources: message.sources ?? [], cards: message.cards ?? [],
    })),
  }
}

export const aiApi = {
  /** hospitalId 가 있으면 병원 대화(이미 열린 게 있으면 그것 반환), parentConversationId 로 조건 복사 (D-20) */
  createConversation: (body: CreateConversationRequest) =>
    http.post<Conversation>('/ai/conversations', body).then((r) => normalizeConversation(r.data)),
  /** 내 대화창 목록 (messages=null), 최신순 */
  conversations: () => http.get<Conversation[]>('/ai/conversations').then((r) => r.data),
  conversation: (id: Uuid) => http.get<Conversation>(`/ai/conversations/${id}`).then((r) => normalizeConversation(r.data)),
  /** 202 {taskId} → 바로 streamTask(taskId) 로 SSE 연결 */
  createTask: (body: CreateTaskRequest) => http.post<CreateTaskResponse>('/ai/tasks', body).then((r) => r.data),
  task: (id: Uuid) => http.get<AiTask>(`/ai/tasks/${id}`).then((r) => r.data),
  /** 202. 같은 taskId 스트림이 이어진다. TASK_NOT_WAITING_APPROVAL(409) 주의 */
  approve: (id: Uuid, body: ApprovalRequest) => http.post<void>(`/ai/tasks/${id}/approval`, body).then(() => undefined),
  myTasks: () => http.get<AiTask[]>('/ai/tasks', { params: { mine: true } }).then((r) => r.data),
  // TODO(fe): GET/DELETE /api/me/ai-profile (장기 기억 조회·삭제, 「AI Agent 설계」 9-4) — P1
}
