"""큐 소비 (aio-pika). agent 가 소비하는 큐: ai.task.requested, ai.task.resume, chat.translate, summary.translate.

실행: FastAPI lifespan(app/api/main.py)에서 start_consumers() 를 띄운다.
"""

import aio_pika

from app.config import get_settings
from app.workers.messages import AiTaskRequested, AiTaskResume, ChatTranslate, Queue, SummaryTranslate


async def handle_task_requested(msg: AiTaskRequested, trace_id: str) -> None:
    # TODO(agent): thread_id = conversation_id 로 그래프 astream_events 실행 → ai.task.event 발행 (events.py)
    # TODO(agent): user·action 을 초기 state 에 넣기 (user: id·role·locale 만, 개인정보 X)
    # TODO(agent): 120초 타임아웃·실패 시 FAILED {code: AI_UNAVAILABLE, traceId} (05 문서 Recovery)
    raise NotImplementedError


async def handle_task_resume(msg: AiTaskResume, trace_id: str) -> None:
    # TODO(agent): Command(resume={"approved":..., "editedArgs":..., "reason":...}) 로 같은 thread 재개
    raise NotImplementedError


async def handle_chat_translate(msg: ChatTranslate, trace_id: str) -> None:
    # TODO(agent): 번역 워커 — prompts/translate_chat.md + 용어집(glossary) 주입, 숫자·날짜·금액 검증 → NUMBER_MISMATCH,
    #              의료 질문 분류 → MEDICAL_QUESTION, 결과는 chat.translated 로 발행
    raise NotImplementedError


async def handle_summary_translate(msg: SummaryTranslate, trace_id: str) -> None:
    # TODO(agent): 요약 카드 → ko 번역 후 summary.translated 발행
    raise NotImplementedError


HANDLERS = {
    Queue.AI_TASK_REQUESTED: (AiTaskRequested, handle_task_requested),
    Queue.AI_TASK_RESUME: (AiTaskResume, handle_task_resume),
    Queue.CHAT_TRANSLATE: (ChatTranslate, handle_chat_translate),
    Queue.SUMMARY_TRANSLATE: (SummaryTranslate, handle_summary_translate),
}


async def start_consumers() -> aio_pika.abc.AbstractRobustConnection:
    """큐마다 consumer 를 붙이고 연결을 돌려준다 (종료 시 close).

    TODO(agent): 실패 시 x-attempt 를 올려 재시도 큐로, 2회 넘으면 DLQ (05 문서 Recovery, INFRA-02 정의 확정 후)
    TODO(agent): prefetch_count 조정 (LLM 호출이 길어 1~2 권장)
    """
    connection = await aio_pika.connect_robust(get_settings().rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    for queue_name, (model, handler) in HANDLERS.items():
        queue = await channel.get_queue(queue_name)  # 큐 선언은 INFRA-02 definitions.json

        async def on_message(message: aio_pika.abc.AbstractIncomingMessage, model=model, handler=handler):
            async with message.process(requeue=False):
                trace_id = (message.headers or {}).get("x-trace-id", "")
                await handler(model.model_validate_json(message.body), trace_id)

        await queue.consume(on_message)
    return connection
