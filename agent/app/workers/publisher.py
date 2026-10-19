"""큐 발행 (aio-pika). exchange capstone.direct 에 routing key = 큐 이름으로 발행."""

import aio_pika

from app.workers.messages import EXCHANGE, HEADER_ATTEMPT, HEADER_TRACE_ID, CamelModel


async def publish(channel: aio_pika.abc.AbstractChannel, routing_key: str, body: CamelModel,
                  trace_id: str, attempt: int = 0) -> None:
    # TODO(agent): exchange 선언은 INFRA-02 definitions.json 이 담당 → 여기서는 get_exchange(passive) 로 가져오기만
    exchange = await channel.get_exchange(EXCHANGE)
    message = aio_pika.Message(
        body=body.to_json(),
        content_type="application/json",
        headers={HEADER_TRACE_ID: trace_id, HEADER_ATTEMPT: attempt},
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )
    await exchange.publish(message, routing_key=routing_key)
