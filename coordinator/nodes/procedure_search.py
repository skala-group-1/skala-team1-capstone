"""Main-only web evidence lookup. Never reads hospital RAG or business data."""
import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.config import get_settings
from app.harness.instructions import load_prompt

log = logging.getLogger(__name__)
UNAVAILABLE = {"status": "external_search_unavailable"}


def parse_answer(body, domains):
    """Only accept completed, searched responses with provider URL annotations."""
    output = body.get("output") or []
    if body.get("status") != "completed" or not any(
        item.get("type") == "web_search_call" and item.get("status") == "completed" for item in output
    ):
        return dict(UNAVAILABLE)
    parts, sources = [], []
    for item in output:
        if item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if part.get("type") != "output_text":
                continue
            text = part.get("text") or ""
            replacements = []
            for citation in part.get("annotations") or []:
                if citation.get("type") != "url_citation":
                    continue
                url = citation.get("url", "")
                parsed = urlparse(url)
                host = (parsed.hostname or "").lower()
                if (parsed.scheme != "https" or parsed.username or parsed.password
                        or any(c in url for c in '\n\r<>"')
                        or not any(host == domain or host.endswith('.' + domain) for domain in domains)):
                    return dict(UNAVAILABLE)
                start, end = citation.get("start_index"), citation.get("end_index")
                if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
                    return dict(UNAVAILABLE)
                if url not in [s["url"] for s in sources]:
                    sources.append({"url": url, "title": citation.get("title") or host})
                number = next(i + 1 for i, s in enumerate(sources) if s["url"] == url)
                safe_url = url.replace('(', '%28').replace(')', '%29')
                replacements.append((start, end, f"[{number}]({safe_url})"))
            for start, end, replacement in sorted(replacements, reverse=True):
                text = text[:start] + replacement + text[end:]
            parts.append(text)
    answer = '\n\n'.join(parts).strip()
    return {"status": "ready", "answer": answer, "sources": sources} if answer and sources else dict(UNAVAILABLE)


async def search_procedure(question, locale):
    settings = get_settings()
    domains = [d.strip().lower() for d in settings.procedure_search_domains.split(',') if d.strip()]
    if not settings.openai_api_key or not domains or not question.strip():
        return dict(UNAVAILABLE)
    prompt = load_prompt("procedure_search", directory=Path(__file__).resolve().parents[1] / "prompts")
    try:
        async with httpx.AsyncClient(timeout=settings.procedure_search_timeout_seconds) as client:
            response = await client.post('https://api.openai.com/v1/responses',
                headers={"Authorization": f"Bearer {settings.openai_api_key}"}, json={
                    "model": settings.procedure_search_model,
                    "instructions": prompt + "\nResponse locale: " + (locale if locale in ('ko', 'en', 'zh', 'ja') else 'en')
                        + "\nUse only these source domains: " + ', '.join(domains),
                    "input": question + " (" + " OR ".join('site:' + d for d in domains) + ")",
                    # gpt-4.1-mini supports web search but rejects API domain filters.
                    # Restrict the search instructions and validate every cited host below.
                    "tools": [{"type": "web_search"}],
                    "tool_choice": "required", "max_output_tokens": 1200, "store": False,
                })
            response.raise_for_status()
            return parse_answer(response.json(), domains)
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        log.warning("Procedure web search unavailable")
        return dict(UNAVAILABLE)
