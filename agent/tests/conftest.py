import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from app.graph.builder import compile_graph


@pytest.fixture
def graph():
    return compile_graph(MemorySaver(), InMemoryStore())


@pytest.fixture
def config(request):
    return {"configurable": {"thread_id": request.node.name}}
