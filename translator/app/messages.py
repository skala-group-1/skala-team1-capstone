"""RabbitMQ 메시지 모델 (「공통 계약서」 7장). body 는 JSON camelCase, 파이썬 쪽은 snake_case.

agent/app/workers/messages.py 에서 복사한 것 — 컨테이너가 분리돼 있어 agent 패키지를 import 하지 않는다.
필드를 바꾸면 「공통 계약서」를 먼저 고치고 backend·agent 와 맞춘다.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

EXCHANGE = "capstone.direct"
HEADER_TRACE_ID = "x-trace-id"
HEADER_ATTEMPT = "x-attempt"


class Queue:
    """큐 이름 = routing key. 선언은 backend 가 기동 시 전부 한다 (재시도·DLQ 포함)."""
    CHAT_TRANSLATE = "chat.translate"            # backend → translator
    CHAT_TRANSLATED = "chat.translated"          # translator → backend
    SUMMARY_TRANSLATE = "summary.translate"      # backend → translator
    SUMMARY_TRANSLATED = "summary.translated"    # translator → backend


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    def to_json(self) -> bytes:
        return self.model_dump_json(by_alias=True).encode()


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
