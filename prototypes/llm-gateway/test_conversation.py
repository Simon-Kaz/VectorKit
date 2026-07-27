"""Unit tests for the gateway's persona + memory logic (P3-06).

Pure functions and a small stateful class -- no live backend, no fastapi. CI's
venv (ruff + pytest only) can import `conversation` directly; it must not import
main.py, which pulls in fastapi/httpx/anthropic.
"""

from conversation import Conversation, latest_user, load_persona


def test_load_persona_reads_and_strips(tmp_path):
    p = tmp_path / "persona.md"
    p.write_text("  You are TARS.\n", encoding="utf-8")
    assert load_persona(str(p)) == "You are TARS."


def test_load_persona_missing_is_empty(tmp_path):
    assert load_persona(str(tmp_path / "nope.md")) == ""


def test_load_persona_blank_is_empty(tmp_path):
    p = tmp_path / "persona.md"
    p.write_text("   \n\t\n", encoding="utf-8")
    assert load_persona(str(p)) == ""


def test_latest_user_picks_last_user_turn():
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "reply"},
        {"role": "user", "content": "second"},
    ]
    assert latest_user(msgs) == "second"


def test_latest_user_none_when_absent():
    assert latest_user([{"role": "system", "content": "sys"}]) is None
    assert latest_user([{"role": "user", "content": ""}]) is None


def test_build_prepends_persona_and_current_user():
    convo = Conversation(max_turns=3, idle_timeout=300)
    msgs = convo.build(persona="You are TARS.", user="hi", now=0.0)
    assert msgs == [
        {"role": "system", "content": "You are TARS."},
        {"role": "user", "content": "hi"},
    ]


def test_build_omits_system_when_no_persona():
    convo = Conversation(max_turns=3, idle_timeout=300)
    msgs = convo.build(persona="", user="hi", now=0.0)
    assert msgs == [{"role": "user", "content": "hi"}]


def test_memory_carries_earlier_turn():
    convo = Conversation(max_turns=3, idle_timeout=300)
    convo.build(persona="P", user="my name is Sam", now=0.0)
    convo.record("my name is Sam", "Hello Sam.", now=1.0)

    msgs = convo.build(persona="P", user="what is my name?", now=2.0)
    assert msgs == [
        {"role": "system", "content": "P"},
        {"role": "user", "content": "my name is Sam"},
        {"role": "assistant", "content": "Hello Sam."},
        {"role": "user", "content": "what is my name?"},
    ]


def test_window_drops_oldest_exchange_whole():
    convo = Conversation(max_turns=2, idle_timeout=300)
    for i in range(3):
        convo.record(f"q{i}", f"a{i}", now=float(i))
    msgs = convo.build(persona="", user="now", now=10.0)
    # Only the last 2 exchanges survive; q0/a0 dropped as a pair.
    assert msgs == [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "now"},
    ]


def test_idle_timeout_clears_history():
    convo = Conversation(max_turns=3, idle_timeout=60)
    convo.record("earlier", "ok", now=0.0)
    # 61s later, past the idle window -> history cleared before building.
    msgs = convo.build(persona="", user="fresh", now=61.0)
    assert msgs == [{"role": "user", "content": "fresh"}]


def test_within_idle_timeout_keeps_history():
    convo = Conversation(max_turns=3, idle_timeout=60)
    convo.record("earlier", "ok", now=0.0)
    msgs = convo.build(persona="", user="soon", now=30.0)
    assert msgs[0] == {"role": "user", "content": "earlier"}


def test_max_turns_zero_disables_memory():
    convo = Conversation(max_turns=0, idle_timeout=300)
    convo.record("q", "a", now=0.0)
    msgs = convo.build(persona="", user="next", now=1.0)
    assert msgs == [{"role": "user", "content": "next"}]


def test_empty_assistant_reply_not_recorded():
    convo = Conversation(max_turns=3, idle_timeout=300)
    convo.record("q", "", now=0.0)
    msgs = convo.build(persona="", user="next", now=1.0)
    assert msgs == [{"role": "user", "content": "next"}]
