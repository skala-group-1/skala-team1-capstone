"""RabbitMQ 메시지 모델 (「공통 계약서」 7장). body 는 JSON camelCase, 파이썬 쪽은 snake_case.

exchange capstone.direct(direct), routing key = 큐 이름. 헤더 x-trace-id, x-attempt.
필드를 바꾸면 「공통 계약서」를 먼저 고치고 backend 와 맞춘다.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

EXCHANGE = "capstone.direct"
HEADER_TRACE_ID = "x-trace-id"
HEADER_ATTEMPT = "x-attempt"


class Queue:
    """큐 이름 = routing key. 소비(consume)/발행(publish) 주체는 「공통 계약서」 7장."""
    AI_TASK_REQUESTED = "ai.task.requested"      # backend → agent
    AI_TASK_RESUME = "ai.task.resume"            # backend → agent
    AI_TASK_EVENT = "ai.task.event"              # agent → backend (SSE 중계)
    CHAT_TRANSLATE = "chat.translate"            # backend → agent 번역 워커
    CHAT_TRANSLATED = "chat.translated"          # agent → backend
    SUMMARY_TRANSLATE = "summary.translate"      # backend → agent 번역 워커
    SUMMARY_TRANSLATED = "summary.translated"    # agent → backend
    NOTIFY = "notify"                            # backend 내부 (agent 는 사용 안 함)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    def to_json(self) -> bytes:
        return self.model_dump_json(by_alias=True).encode()


class TaskUser(CamelModel):
    id: int
    role: Literal["CUSTOMER", "COUNSELOR", "HOSPITAL_ADMIN", "OPERATOR"]
    locale: Literal["en", "zh", "ja", "ko"]


class AiTaskRequested(CamelModel):
    task_id: str
    conversation_id: str
    user: TaskUser
    message: str
    action: dict[str, Any] | None = None    # {"type":"SELECT_HOSPITAL","hospitalId":1} 등 (「공통 계약서」 CreateTaskRequest)
    requested_at: datetime


class AiTaskResume(CamelModel):
    task_id: str
    conversation_id: str
    user: TaskUser
    approved: bool
    edited_args: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class AiTaskEvent(CamelModel):
    task_id: str
    seq: int
    event: str                               # events.SseEvent 값
    data: dict[str, Any]
    at: datetime


class ChatTranslate(CamelModel):
    message_id: int
    consultation_id: int
    text: str
    from_: str = Field(alias="from")
    to: str


class ChatTranslated(CamelModel):
    message_id: int
    ok: bool
    translated_text: str | None = None
    flags: list[Literal["NUMBER_MISMATCH", "MEDICAL_QUESTION"]] = Field(default_factory=list)
    error: str | None = None


class SummaryTranslate(CamelModel):
    consultation_id: int
    summary_card: dict[str, Any]             # 「공통 계약서」 SummaryCard
    from_: str = Field(alias="from")
    to: str


class SummaryTranslated(CamelModel):
    consultation_id: int
    ok: bool
    summary_card_ko: dict[str, Any] | None = None


class Notify(CamelModel):
    user_ids: list[int]
    type: str                                # 「공통 계약서」 NotificationType
    payload: dict[str, Any]
