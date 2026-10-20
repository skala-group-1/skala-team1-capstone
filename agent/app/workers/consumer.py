"""큐 소비 (aio-pika). agent 가 소비하는 큐: ai.task.requested, ai.task.resume.

chat.translate·summary.translate 는 translator 컨테이너(공용 에이전트 파트)로 이관 — 여기서 소비하면
메시지를 나눠 먹어 유실된다.

실행: FastAPI lifespan(app/api/main.py)에서 start_consumers() 를 띄운다.
"""

import aio_pika

from app.config import get_settings
from app.workers.messages import AiTaskRequested, AiTaskResume, Queue


async def handle_task_requested(msg: AiTaskRequested, trace_id: str) -> None:
    # TODO(agent): thread_id = conversation_id 로 그래프 astream_events 실행 → ai.task.event 발행 (events.py)
    # TODO(agent): user·action 을 초기 state 에 넣기 (user: id·role·locale 만, 개인정보 X)
    # TODO(agent): 120초 타임아웃·실패 시 FAILED {code: AI_UNAVAILABLE, traceId} (「Harness 명세」 Recovery)
    raise NotImplementedError


async def handle_task_resume(msg: AiTaskResume, trace_id: str) -> None:
    # TODO(agent): Command(resume={"approved":..., "editedArgs":..., "reason":...}) 로 같은 thread 재개
    raise NotImplementedError


HANDLERS = {
    Queue.AI_TASK_REQUESTED: (AiTaskRequested, handle_task_requested),
    Queue.AI_TASK_RESUME: (AiTaskResume, handle_task_resume),
}


async def start_consumers() -> aio_pika.abc.AbstractRobustConnection:
    """큐마다 consumer 를 붙이고 연결을 돌려준다 (종료 시 close).

    TODO(agent): 실패 시 x-attempt 를 올려 재시도 큐로, 2회 넘으면 DLQ (「Harness 명세」 Recovery, INFRA-02 정의 확정 후)
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
