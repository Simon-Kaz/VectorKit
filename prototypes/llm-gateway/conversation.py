"""Persona + rolling conversation memory for the gateway (backend-agnostic).

These sit in the endpoint layer, BEFORE the backend, so both Claude and Ollama
get persona + memory for free -- the two-backend symmetry in main.py stays
intact. Kept stdlib-only on purpose: CI installs only `vector[dev]` (ruff +
pytest), so tests import this module without fastapi/httpx/anthropic present.
main.py imports it and wires it in.

Persona (P3-06 + P3-11): a character card (PERSONA_FILE) loaded at startup. It
REPLACES any `system` turn wire-pod sends (`openai_prompt`) -- the gateway is
the single source of truth for Vector's character. A JSON file is read as a
structured card (name / persona / speaking_style / user identity + few-shot
`example_dialogue`), modelled on what TARS-AI ships; the example turns are
injected as real user/assistant messages, which is the biggest lever for
holding a tiny local model in character. A non-JSON file is used verbatim as the
system prompt (backward compatible with the flat P3-06 persona.md). See
docs/design/p3-06-persona-memory.md.

Memory: Vector is a single-user robot and wire-pod's request carries no
conversation id, so history is one global rolling window -- a ring buffer of the
last N exchanges, cleared after IDLE_TIMEOUT seconds of silence so a new
conversation starts fresh. In-memory only: it resets on gateway restart, which
is fine for a prototype and keeps the 2 GB Pi's RAM budget honest.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Persona:
    """A loaded character: the system prompt plus few-shot example turns.

    `system` is the composed system prompt (empty = no persona). `examples` is a
    list of role/content message dicts (user/assistant pairs) injected before
    the rolling history to demonstrate voice and format -- the strongest way to
    keep a sub-1B local model in character.
    """

    system: str = ""
    examples: list[dict] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.system or self.examples)


def _compose_system(card: dict) -> str:
    """Build a system prompt string from character-card fields.

    Only the fields present contribute a section, so a minimal card (just
    `persona`) still works. Field names follow TARS-AI's card loosely, kept to
    what a spoken single-user robot needs.
    """
    name = (card.get("name") or "").strip()
    parts: list[str] = []
    if name:
        parts.append(f"You are {name}.")
    if card.get("persona"):
        parts.append(card["persona"].strip())
    if card.get("speaking_style"):
        parts.append("Speaking style:\n" + card["speaking_style"].strip())

    user_name = (card.get("user_name") or "").strip()
    user_details = (card.get("user_details") or "").strip()
    if user_name or user_details:
        who = f"You are speaking with {user_name}." if user_name else "About the user:"
        parts.append((who + " " + user_details).strip())

    if name:
        parts.append(
            "You remember the current conversation and can refer back to what "
            f"was just said. Stay in character as {name} at all times."
        )
    return "\n\n".join(parts).strip()


def _card_examples(card: dict) -> list[dict]:
    """Turn a card's `example_dialogue` into user/assistant message turns.

    Each entry is `{"user": "...", "assistant": "..."}`; blank sides are
    skipped. Injected before the rolling history as few-shot demonstrations.
    """
    turns: list[dict] = []
    for ex in card.get("example_dialogue") or []:
        u = (ex.get("user") or "").strip()
        a = (ex.get("assistant") or "").strip()
        if u:
            turns.append({"role": "user", "content": u})
        if a:
            turns.append({"role": "assistant", "content": a})
    return turns


def load_persona(path: str) -> Persona:
    """Load the character at `path` into a Persona; empty Persona if missing.

    A JSON file is parsed as a structured card. Anything else (or invalid JSON)
    is treated as a flat system prompt -- backward compatible with the P3-06
    plain-text persona.md. A missing or blank file means no persona (the
    gateway's pre-P3-06 behavior).
    """
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read().strip()
    except FileNotFoundError:
        return Persona()
    if not raw:
        return Persona()
    try:
        card = json.loads(raw)
    except json.JSONDecodeError:
        return Persona(system=raw)  # flat text prompt
    if not isinstance(card, dict):
        return Persona(system=raw)
    return Persona(system=_compose_system(card), examples=_card_examples(card))


def latest_user(messages: list[dict]) -> str | None:
    """The most recent user turn's content from an inbound message list.

    The gateway relies on its own stored history for context, so it only needs
    wire-pod's newest question -- this is robust whether or not wire-pod also
    replays earlier turns in the request.
    """
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            return m["content"]
    return None


class Conversation:
    """A single global rolling window of user/assistant turns.

    `max_turns` counts exchanges (a user turn + its assistant reply); the ring
    buffer holds `2 * max_turns` messages and always appends in pairs, so the
    oldest exchange drops out whole. `idle_timeout` seconds of silence clears
    the window on the next request. max_turns == 0 disables memory entirely.
    """

    def __init__(self, max_turns: int, idle_timeout: float) -> None:
        self._max_turns = max_turns
        self._idle_timeout = idle_timeout
        # maxlen None (unbounded) when disabled -- but we short-circuit anyway.
        self._turns: deque[dict] = deque(maxlen=2 * max_turns if max_turns else 0)
        self._last: float | None = None

    def _expire(self, now: float) -> None:
        if (
            self._last is not None
            and self._idle_timeout > 0
            and now - self._last > self._idle_timeout
        ):
            self._turns.clear()

    def build(self, persona: Persona, user: str, now: float) -> list[dict]:
        """Messages to send to the backend.

        Order: persona system prompt, few-shot example turns, rolling history,
        then this question. Expires stale history first (idle timeout). The
        current `user` turn is NOT yet in history -- record() adds it after the
        reply is known. The few-shot examples are constant priming, so they are
        never stored in history.
        """
        self._expire(now)
        msgs: list[dict] = []
        if persona.system:
            msgs.append({"role": "system", "content": persona.system})
        msgs.extend(persona.examples)
        msgs.extend(self._turns)
        msgs.append({"role": "user", "content": user})
        return msgs

    def record(self, user: str, assistant: str, now: float) -> None:
        """Append a completed exchange to the window and stamp last-active.

        No-op when memory is disabled (max_turns == 0) or the assistant reply
        is empty (nothing worth remembering)."""
        if self._max_turns == 0 or not assistant:
            self._last = now
            return
        self._turns.append({"role": "user", "content": user})
        self._turns.append({"role": "assistant", "content": assistant})
        self._last = now
