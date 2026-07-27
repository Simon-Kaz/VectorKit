"""Unit tests for the gateway's persona + memory logic (P3-06, P3-11).

Pure functions and a small stateful class -- no live backend, no fastapi. CI's
venv (ruff + pytest only) can import `conversation` directly; it must not import
main.py, which pulls in fastapi/httpx/anthropic.
"""

import json

from conversation import Conversation, Persona, latest_user, load_persona

# A persona with only a system prompt and no examples, for the memory tests.
P = Persona(system="P")
NO_PERSONA = Persona()


# --- load_persona: flat text (backward compatible with P3-06) --------------


def test_load_persona_flat_text(tmp_path):
    p = tmp_path / "persona.md"
    p.write_text("  You are Vector.\n", encoding="utf-8")
    persona = load_persona(str(p))
    assert persona.system == "You are Vector."
    assert persona.examples == []


def test_load_persona_missing_is_empty(tmp_path):
    persona = load_persona(str(tmp_path / "nope.json"))
    assert persona.system == ""
    assert persona.examples == []
    assert not persona


def test_load_persona_blank_is_empty(tmp_path):
    p = tmp_path / "persona.md"
    p.write_text("   \n\t\n", encoding="utf-8")
    assert not load_persona(str(p))


# --- load_persona: JSON character card (P3-11) -----------------------------


def _write_card(tmp_path, card):
    p = tmp_path / "character.json"
    p.write_text(json.dumps(card), encoding="utf-8")
    return str(p)


def test_card_composes_system_prompt(tmp_path):
    path = _write_card(
        tmp_path,
        {
            "name": "Vector",
            "persona": "A small desk robot.",
            "speaking_style": "Keep it short.",
        },
    )
    persona = load_persona(path)
    assert persona.system.startswith("You are Vector.")
    assert "A small desk robot." in persona.system
    assert "Speaking style:\nKeep it short." in persona.system
    # The name anchors a closing stay-in-character line.
    assert "Stay in character as Vector" in persona.system


def test_card_user_identity(tmp_path):
    path = _write_card(
        tmp_path,
        {"name": "Vector", "user_name": "Simon", "user_details": "Likes robots."},
    )
    persona = load_persona(path)
    assert "speaking with Simon" in persona.system
    assert "Likes robots." in persona.system


def test_card_example_dialogue_becomes_turns(tmp_path):
    path = _write_card(
        tmp_path,
        {
            "name": "Vector",
            "example_dialogue": [
                {"user": "Hi", "assistant": "Hey there."},
                {"user": "Bye", "assistant": "See you."},
            ],
        },
    )
    persona = load_persona(path)
    assert persona.examples == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hey there."},
        {"role": "user", "content": "Bye"},
        {"role": "assistant", "content": "See you."},
    ]


def test_card_minimal_only_persona(tmp_path):
    path = _write_card(tmp_path, {"persona": "Just a robot."})
    persona = load_persona(path)
    assert persona.system == "Just a robot."
    assert persona.examples == []


def test_invalid_json_falls_back_to_flat_text(tmp_path):
    p = tmp_path / "character.json"
    p.write_text("You are Vector. {not json", encoding="utf-8")
    persona = load_persona(str(p))
    assert persona.system == "You are Vector. {not json"
    assert persona.examples == []


# --- latest_user -----------------------------------------------------------


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


# --- Conversation.build: persona + examples + memory -----------------------


def test_build_prepends_persona_and_current_user():
    convo = Conversation(max_turns=3, idle_timeout=300)
    msgs = convo.build(P, user="hi", now=0.0)
    assert msgs == [
        {"role": "system", "content": "P"},
        {"role": "user", "content": "hi"},
    ]


def test_build_omits_system_when_no_persona():
    convo = Conversation(max_turns=3, idle_timeout=300)
    msgs = convo.build(NO_PERSONA, user="hi", now=0.0)
    assert msgs == [{"role": "user", "content": "hi"}]


def test_build_injects_examples_before_history():
    persona = Persona(
        system="P",
        examples=[
            {"role": "user", "content": "ex-q"},
            {"role": "assistant", "content": "ex-a"},
        ],
    )
    convo = Conversation(max_turns=3, idle_timeout=300)
    convo.record("real-q", "real-a", now=0.0)
    msgs = convo.build(persona, user="now", now=1.0)
    assert msgs == [
        {"role": "system", "content": "P"},
        {"role": "user", "content": "ex-q"},
        {"role": "assistant", "content": "ex-a"},
        {"role": "user", "content": "real-q"},
        {"role": "assistant", "content": "real-a"},
        {"role": "user", "content": "now"},
    ]


def test_examples_are_not_stored_in_history():
    persona = Persona(system="P", examples=[{"role": "user", "content": "ex"}])
    convo = Conversation(max_turns=3, idle_timeout=300)
    # Building twice must not accumulate the examples into history.
    convo.build(persona, user="a", now=0.0)
    convo.record("a", "b", now=1.0)
    msgs = convo.build(persona, user="c", now=2.0)
    assert msgs.count({"role": "user", "content": "ex"}) == 1


def test_memory_carries_earlier_turn():
    convo = Conversation(max_turns=3, idle_timeout=300)
    convo.build(P, user="my name is Sam", now=0.0)
    convo.record("my name is Sam", "Hello Sam.", now=1.0)

    msgs = convo.build(P, user="what is my name?", now=2.0)
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
    msgs = convo.build(NO_PERSONA, user="now", now=10.0)
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
    msgs = convo.build(NO_PERSONA, user="fresh", now=61.0)
    assert msgs == [{"role": "user", "content": "fresh"}]


def test_within_idle_timeout_keeps_history():
    convo = Conversation(max_turns=3, idle_timeout=60)
    convo.record("earlier", "ok", now=0.0)
    msgs = convo.build(NO_PERSONA, user="soon", now=30.0)
    assert msgs[0] == {"role": "user", "content": "earlier"}


def test_max_turns_zero_disables_memory():
    convo = Conversation(max_turns=0, idle_timeout=300)
    convo.record("q", "a", now=0.0)
    msgs = convo.build(NO_PERSONA, user="next", now=1.0)
    assert msgs == [{"role": "user", "content": "next"}]


def test_empty_assistant_reply_not_recorded():
    convo = Conversation(max_turns=3, idle_timeout=300)
    convo.record("q", "", now=0.0)
    msgs = convo.build(NO_PERSONA, user="next", now=1.0)
    assert msgs == [{"role": "user", "content": "next"}]
