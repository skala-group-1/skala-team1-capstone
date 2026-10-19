from app.harness.instructions import PROMPTS_DIR, load_prompt
from app.harness.loop import MAX_SAME_TOOL_CALLS, MAX_TURNS, check_limits

PROMPTS = ("system_base", "guard_input", "extract_conditions", "ask_clarify", "rag_answer",
           "hospital_agent", "summarize_handoff", "translate_chat")


def test_all_prompt_files_exist_with_version():
    for name in PROMPTS:
        assert (PROMPTS_DIR / f"{name}.md").exists()
        assert "version:" in load_prompt(name)


def test_loop_limits():
    assert check_limits({"turn": 0, "tool_counts": {}, "started_at": 0}, now=1) is None
    assert check_limits({"turn": MAX_TURNS, "started_at": 0}, now=1) == "MAX_TURNS"
    assert check_limits({"turn": 0, "started_at": 0}, now=999) == "TIMEOUT"
    assert check_limits({"turn": 0, "tool_counts": {"x": MAX_SAME_TOOL_CALLS}, "started_at": 0}, now=1) == "SAME_TOOL_REPEATED"
