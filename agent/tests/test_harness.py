from pathlib import Path

from app.harness.instructions import PROMPTS_DIR, load_prompt
from app.harness.loop import MAX_SAME_TOOL_CALLS, MAX_TURNS, check_limits

PROMPTS = {
    PROMPTS_DIR: ("system_base", "hospital_agent", "summarize_handoff", "translate_chat"),
    Path(__file__).resolve().parents[2] / "coordinator/prompts": (
        "guard_input", "extract_conditions", "ask_clarify", "rag_answer"),
}


def test_all_prompt_files_exist_with_version():
    for directory, names in PROMPTS.items():
        for name in names:
            assert "version:" in load_prompt(name, directory=directory)


def test_coordinator_prompt_loads_from_role_directory():
    directory = Path(__file__).resolve().parents[2] / "coordinator/prompts"
    assert load_prompt("coordinator", directory=directory).strip()


def test_loop_limits():
    assert check_limits({"turn": 0, "tool_counts": {}, "started_at": 0}, now=1) is None
    assert check_limits({"turn": MAX_TURNS, "started_at": 0}, now=1) == "MAX_TURNS"
    assert check_limits({"turn": 0, "started_at": 0}, now=999) == "TIMEOUT"
    assert check_limits({"turn": 0, "tool_counts": {"x": MAX_SAME_TOOL_CALLS}, "started_at": 0}, now=1) == "SAME_TOOL_REPEATED"
