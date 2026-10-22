from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from langchain_core.messages import HumanMessage

from coordinator.nodes import procedure_search as search
from coordinator.nodes.planner_agent import run_coordinator
from coordinator.tests.test_coordinator import ScriptedModel, call


def response(url='https://www.aad.org/public/cosmetic/botox'):
    return {'status': 'completed', 'output': [
        {'type': 'web_search_call', 'status': 'completed'},
        {'type': 'message', 'content': [{'type': 'output_text',
            'text': 'Sourced information [cite]', 'annotations': [
                {'type': 'url_citation', 'url': url, 'title': 'AAD',
                 'start_index': 20, 'end_index': 26}]}]},
    ]}


def test_citations_become_clickable_links():
    body = response()
    # The exact offsets refer to the citation, never model-authored URLs.
    part = body['output'][1]['content'][0]
    part['annotations'][0].update(start_index=20, end_index=26)
    result = search.parse_answer(body, ['aad.org'])
    assert result['status'] == 'ready'
    assert result['answer'] == 'Sourced information [1](https://www.aad.org/public/cosmetic/botox)'
    assert result['sources'][0]['title'] == 'AAD'


@pytest.mark.parametrize('change', ['no_search', 'no_citation', 'incomplete', 'bad_url', 'bad_offsets'])
def test_unverified_outputs_are_not_answers(change):
    body = response()
    if change == 'no_search': body['output'].pop(0)
    if change == 'no_citation': body['output'][1]['content'][0]['annotations'] = []
    if change == 'incomplete': body['status'] = 'incomplete'
    if change == 'bad_url': body['output'][1]['content'][0]['annotations'][0]['url'] = 'https://aad.org.evil.test/x'
    if change == 'bad_offsets': body['output'][1]['content'][0]['annotations'][0]['end_index'] = 999
    assert search.parse_answer(body, ['aad.org'])['status'] == 'external_search_unavailable'


async def test_search_request_forces_web_and_handles_timeout(monkeypatch):
    settings = SimpleNamespace(openai_api_key='fake', procedure_search_domains='aad.org',
        procedure_search_model='test-model', procedure_search_timeout_seconds=1)
    monkeypatch.setattr(search, 'get_settings', lambda: settings)
    client = AsyncMock()
    client.post.side_effect = httpx.ReadTimeout('provider failure')
    context = AsyncMock()
    context.__aenter__.return_value = client
    monkeypatch.setattr(search.httpx, 'AsyncClient', lambda **kwargs: context)
    assert (await search.search_procedure('Question', 'ja'))['status'] == 'external_search_unavailable'
    payload = client.post.call_args.kwargs['json']
    assert payload['tool_choice'] == 'required'
    assert payload['tools'] == [{'type': 'web_search'}]
    assert 'Use only these source domains: aad.org' in payload['instructions']
    assert payload['input'] == 'Question (site:aad.org)'
    assert 'Response locale: ja' in payload['instructions']
    assert payload['store'] is False


async def test_sourced_answer_passes_through_without_rewrite_or_rag(monkeypatch):
    answer = '説明 [1](https://www.aad.org/public/cosmetic/botox)'
    lookup = AsyncMock(return_value={'status': 'ready', 'answer': answer, 'sources': []})
    monkeypatch.setattr(search, 'search_procedure', lookup)
    business = AsyncMock()
    model = ScriptedModel(call('procedure_consultation', {'question': 'ボトックスのリスク'}))
    result = await run_coordinator({'messages': [HumanMessage('ボトックスのリスク')],
        'user': {'locale': 'ja'}, 'conditions': {'areas': ['GANGNAM']}}, model, business_loader=business)
    assert result['draft'] == answer
    assert len(model.history) == 1
    lookup.assert_awaited_once_with('ボトックスのリスク', 'ja')
    business.assert_not_awaited()
    from app.mcp_client.tools import PLANNER_TOOLS, HOSPITAL_READ_TOOLS
    assert not any(name.startswith('rag_') for name in PLANNER_TOOLS)
    assert 'rag_search_procedure_docs' in HOSPITAL_READ_TOOLS
    assert 'rag_search_hospital_docs' in HOSPITAL_READ_TOOLS
