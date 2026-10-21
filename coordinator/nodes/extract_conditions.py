"""Pass saved conditions to the coordinator tool loop for incremental extraction.

collect_conditions uses the same model conversation as search, so first-turn
intake can persist conditions even when no search is performed yet.
"""
from app.graph.state import AgentState


def extract_conditions(state: AgentState) -> dict:
    return {"conditions": dict(state.get("conditions") or {}), "missing": []}
