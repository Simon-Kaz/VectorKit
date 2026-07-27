"""Persona + rolling conversation memory for the gateway (backend-agnostic).

These sit in the endpoint layer, BEFORE the backend, so both Claude and Ollama
get persona + memory for free -- the two-backend symmetry in main.py stays
intact. Kept stdlib-only on purpose: CI installs only `vector[dev]` (ruff +
pytest), so tests import this module without fastapi/httpx/anthropic present.
main.py imports it and wires it in.

Persona: a character-card file (PERSONA_FILE) loaded at startup. It REPLACES
any `system` turn wire-pod sends (`openai_prompt`) -- the gateway is the single
source of truth for Vector's character (see docs/design/p3-06-persona-memory.md).

Memory: Vector is a single-user robot and wire-pod's request carries no
conversation id, so history is one global rolling window -- a ring buffer of the
last N exchanges, cleared after IDLE_TIMEOUT seconds of silence so a new
conversation starts fresh. In-memory only: it resets on gateway restart, which
is fine for a prototype and keeps the 2 GB Pi's RAM budget honest.
"""

from __future__ import annotations

from collections import deque


def load_persona(path: str) -> str:
    """Read the persona character card at `path`; '' if missing or blank.

    A missing or empty file means no persona -- the gateway's pre-P3-06
    behavior (forward whatever system turn wire-pod sent, or none).
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    except FileNotFoundError:
        return ""


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

    def build(self, persona: str, user: str, now: float) -> list[dict]:
        """Messages to send to the backend: persona + history + this question.

        Expires stale history first (idle timeout). The current `user` turn is
        NOT yet in history -- record() adds it after the reply is known.
        """
        self._expire(now)
        msgs: list[dict] = []
        if persona:
            msgs.append({"role": "system", "content": persona})
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
