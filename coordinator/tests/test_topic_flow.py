"""Conversation-level checks for topic persistence and read-only entry actions."""
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from app.graph import builder
from coordinator.nodes.planner_agent import run_coordinator
from coordinator.tests.test_coordinator import ScriptedModel, call


async def test_topic_survives_followup_and_changes_without_losing_conditions(monkeypatch):
    model = ScriptedModel(AIMessage('어느 부위가 고민이세요?'), AIMessage('조건에 맞는 병원을 찾아볼게요.'))
    loader = AsyncMock()
    async def planner(state):
        return await run_coordinator(state, model, business_loader=loader)
    monkeypatch.setattr(builder, 'planner_agent', planner)
    graph = builder.compile_graph(MemorySaver(), InMemoryStore())
    config = {'configurable': {'thread_id': 'topic-flow'}}
    conditions = {'procedure_code': 'JAW_BOTOX', 'areas': ['GANGNAM'], 'date_from': '2026-11-09'}
    first = await graph.ainvoke({'mode': 'MAIN', 'user': {'locale': 'ko'},
        'conditions': conditions, 'messages': [HumanMessage('피부 고민으로 시술 찾기')],
        'action': {'type': 'SELECT_TOPIC', 'topic': 'SKIN_CONCERN'}}, config)
    assert first['topic'] == 'SKIN_CONCERN' and not model.history
    second = await graph.ainvoke({'messages': [HumanMessage('색소가 고민이야')], 'action': None}, config)
    assert second['topic'] == 'SKIN_CONCERN' and second['conditions'] == conditions
    third = await graph.ainvoke({'messages': [HumanMessage('이제 병원을 찾고 싶어')],
        'action': {'type': 'SELECT_TOPIC', 'topic': 'HOSPITAL_SEARCH'}}, config)
    assert third['topic'] == 'HOSPITAL_SEARCH' and third['conditions'] == conditions
    saved = await graph.aget_state(config)
    assert saved.values['topic'] == 'HOSPITAL_SEARCH'
    assert [m.content for m in saved.values['messages'] if isinstance(m, HumanMessage)] == [
        '피부 고민으로 시술 찾기', '색소가 고민이야', '이제 병원을 찾고 싶어']
    loader.assert_not_awaited()


@pytest.mark.parametrize('topic', ['MY_RESERVATIONS', 'CANCEL_RESERVATION'])
async def test_reservation_entry_is_read_only_and_preserves_topic(topic):
    reads = []
    @tool
    async def business_get_my_reservations(status: str | None = None):
        """Read the authenticated customer's reservations."""
        reads.append(status)
        return {'reservations': []}
    loader = AsyncMock(return_value=[business_get_my_reservations])
    model = ScriptedModel(call('hospital_lookup', {'operation': 'reservations', 'arguments': {}}),
                          AIMessage('조회된 예약이 없습니다.'))
    result = await run_coordinator({'user': {'locale': 'ko'},
        'action': {'type': 'SELECT_TOPIC', 'topic': topic},
        'messages': [HumanMessage('내 예약 확인')]}, model, business_loader=loader)
    assert reads == [None] and result['topic'] == topic
    assert result['draft'] == '조회된 예약이 없습니다.'
    assert not any('cancel' in name or 'create_reservation' in name for name in model.names)
    assert not result.get('pending_action')


async def test_selected_concerns_reach_model_without_hospital_intake():
    model = ScriptedModel(AIMessage('색소가 어느 부위에서 신경 쓰이세요?'))
    loader = AsyncMock()
    result = await run_coordinator({'user': {'locale': 'ko'},
        'action': {'type': 'FIND_BY_CONCERNS', 'concerns': ['PIGMENTATION']},
        'messages': [HumanMessage('색소·잡티')]}, model, business_loader=loader)
    assert result['topic'] == 'SKIN_CONCERN'
    assert 'PIGMENTATION' in model.history[0][1].content
    assert not result.get('missing')
    loader.assert_not_awaited()


async def test_generic_toning_requires_actual_candidate_then_searches_saved_filters():
    lookups, searches = [], []
    @tool
    async def business_normalize_procedure(text: str):
        """Normalize a procedure against the catalog."""
        lookups.append(text)
        candidates = []
        if text == '토닝': candidates = [{'code': 'PICO_TONING', 'name': '피코토닝', 'score': 0.8}]
        if text == '피코토닝': candidates = [{'code': 'PICO_TONING', 'name': '피코토닝', 'score': 1}]
        return {'candidates': candidates}
    @tool
    async def business_search_hospitals(procedure_code: str, areas: list[str], date_from: str,
                                       sort_by: str, limit: int):
        """Read matching hospitals."""
        searches.append((procedure_code, areas, date_from))
        return {'hospitals': [{'id': 1, 'name': 'Test hospital'}], 'total': 1}
    loader = AsyncMock(return_value=[business_normalize_procedure, business_search_hospitals])
    state = {'user': {'locale': 'ko'}, 'topic': 'SKIN_CONCERN',
        'conditions': {'areas': [], 'date_from': '2026-10-24'},
        'messages': [HumanMessage('레이저 토닝 예약하고 싶어')]}
    first = await run_coordinator(state, ScriptedModel(call('collect_conditions', {
        'fields': {'procedure_code': '레이저 토닝'}, 'search_hospitals': True})), business_loader=loader)
    assert lookups == ['레이저 토닝', '토닝']
    assert first['topic'] == 'HOSPITAL_SEARCH'
    assert '1. 피코토닝' in first['draft'] and not searches
    assert '어떤 시술을 알아보고 싶으세요?' not in first['draft']
    assert first['conditions']['areas'] == []
    assert first['conditions']['date_from'] == '2026-10-24'
    assert not first['conditions'].get('procedure_code')
    second = await run_coordinator({**state, **first, 'messages': [HumanMessage('피코토닝으로 찾아줘')]},
        ScriptedModel(call('collect_conditions', {'fields': {'procedure_code': '피코토닝'}})),
        business_loader=loader)
    assert searches == [('PICO_TONING', [], '2026-10-24')]
    assert second['candidates'][0]['id'] == 1


@pytest.mark.parametrize('locale', ['ko', 'en', 'zh', 'ja'])
@pytest.mark.parametrize('count', [1, 3])
async def test_related_procedures_are_listed_without_automatic_selection(locale, count):
    candidates = [{'code': f'TEST_{i}', 'name': f'Procedure {i}', 'score': 0.8}
                  for i in range(1, count + 1)]
    @tool
    async def business_normalize_procedure(text: str):
        """Find catalog names."""
        return {'candidates': candidates}
    loader = AsyncMock(return_value=[business_normalize_procedure])
    result = await run_coordinator({'user': {'locale': locale}, 'topic': 'HOSPITAL_SEARCH',
        'conditions': {'areas': [], 'date_from': '2026-10-24'},
        'messages': [HumanMessage('related procedure')]},
        ScriptedModel(call('collect_conditions', {'fields': {'procedure_code': 'related procedure'}})),
        business_loader=loader)
    for i in range(1, count + 1):
        assert f'{i}. Procedure {i}' in result['draft']
    assert 'TEST_' not in result['draft']
    assert not result['conditions'].get('procedure_code')
    assert result['conditions']['date_from'] == '2026-10-24'
    assert result['conditions']['areas'] == []
    assert not result.get('candidates')


async def test_failed_normalization_does_not_broaden_as_if_no_matches():
    lookups = []
    @tool
    async def business_normalize_procedure(text: str):
        """Find catalog names."""
        lookups.append(text)
        return {'status': 'unavailable', 'candidates': []}
    result = await run_coordinator({'user': {'locale': 'ko'},
        'messages': [HumanMessage('레이저 토닝')]},
        ScriptedModel(call('collect_conditions', {'fields': {'procedure_code': '레이저 토닝'}})),
        business_loader=AsyncMock(return_value=[business_normalize_procedure]))
    assert lookups == ['레이저 토닝']
    assert '1.' not in result['draft']
    assert not result.get('candidates')
