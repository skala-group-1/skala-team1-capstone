"""Harness — State·Memory (「Harness 명세」). 단기 = checkpointer(thread), 장기 = store(사용자 프로필).

- thread_id = conversation_id
- PostgresSaver / PostgresStore 는 schema agent 를 쓴다
- DATABASE_URL 이 비어 있으면 개발용 MemorySaver / InMemoryStore 로 대체 (재시작 시 사라짐)
"""

from contextlib import asynccontextmanager

from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from app.config import get_settings

PROFILE_NAMESPACE = "user"  # namespace ("user", user_id), key "profile" (「AI Agent 설계」 9-4)
PROFILE_KEY = "profile"


@asynccontextmanager
async def open_checkpointer_and_store():
    """(checkpointer, store) 를 연다. 그래프 compile 시 넘긴다.

    TODO(agent): 테스트 — interrupt → 프로세스 재시작 → 같은 thread 로 resume 성공 (「Harness 명세」, 데모 B)
    TODO(agent): PostgresStore 에 저장하는 skinConcerns 등 민감 필드는 로그에서 마스킹 (「AI Agent 설계」 9-4)
    """
    url = get_settings().database_url
    if not url:
        yield MemorySaver(), InMemoryStore()
        return

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from langgraph.store.postgres.aio import AsyncPostgresStore

    # TODO(agent): URL 에 search_path=agent 를 넣거나 연결 후 SET search_path 로 schema agent 사용 확인
    async with (
        AsyncPostgresSaver.from_conn_string(url) as saver,
        AsyncPostgresStore.from_conn_string(url) as store,
    ):
        await saver.setup()
        await store.setup()
        yield saver, store
