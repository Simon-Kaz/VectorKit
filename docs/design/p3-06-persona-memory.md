# P3-06 design note: persona + conversation memory in the gateway

Status: shipped (2026-07-27). Builds on P3-03/P3-05 (the LLM gateway). See
`PLAN.md` P3-06 and `docs/design/p3-03-llm-gateway.md`.

## Problem

The gateway (P3-03) forwards one exchange to a backend and streams the reply,
but Vector has no consistent character and cannot reference an earlier turn.
wire-pod keeps only ~16 messages and is the wrong home for either: its config
holds a single `openai_prompt` string and it does not persist a conversation.
TARS-AI ships both a character-card persona and memory; the gateway is the seam
we own, so both belong here (see the TARS-AI table in the P3-03 note).

## Decisions

**Persona: a character-card file the gateway loads at startup.**
`PERSONA_FILE` (default `persona.md`) is read once into `PERSONA`. A missing or
blank file means no persona -- the pre-P3-06 behavior. Chosen over a `PERSONA`
env var because a multi-line character card is awkward in an env file and mixes
prose with config; a file is what TARS-AI does and lets the character be edited
without touching env. The card is committed (it is not a secret) and kept short:
replies are spoken through Vector's own voice, and the local model is sub-1B.

**Merge: the persona REPLACES wire-pod's system turn.** The gateway takes only
wire-pod's newest user turn and drops any inbound `system` turn, then prepends
`PERSONA`. This makes the gateway the single source of truth for Vector's
character -- no risk of a stale `openai_prompt` in wire-pod contradicting the
card. Set wire-pod's `openai_prompt` empty. (Considered prepend/merge; rejected
because two personas fighting is a worse failure than one owned in the gateway.)

**Memory: one global rolling window, in-memory.** Vector is a single-user robot
and wire-pod's `custom`-provider request carries no conversation id, so keying
per conversation has nothing to key on. Instead:
- `Conversation` holds a ring buffer of the last `MEMORY_TURNS` exchanges
  (default 6; `0` disables). The buffer appends in user+assistant pairs and is
  bounded at `2 * MEMORY_TURNS`, so the oldest exchange drops out whole.
- `MEMORY_IDLE_TIMEOUT` seconds of silence (default 300) clears the window on
  the next request, so a new conversation starts fresh without a session id.
- In-memory only: it resets on gateway restart. Fine for a prototype, and it
  keeps the 2 GB Pi's RAM budget honest. On-disk persistence was rejected as
  more than a prototype needs.

**Backend-agnostic placement.** Persona + memory live in the endpoint layer
(`conversation.py`, imported by `main.py`), BEFORE `backend.stream()`, so both
the Claude and Ollama backends inherit them for free -- preserving the
two-backend symmetry the gateway is built around. `conversation.py` is
stdlib-only so it imports under CI's ruff+pytest venv (which has no
fastapi/httpx/anthropic); `main.py`, which does pull those in, is never
imported by a test.

## Request flow (per question)

1. `_messages(body)` cleans the inbound OpenAI turns; `latest_user()` takes the
   newest user turn only. The gateway rebuilds context from its OWN history, so
   it does not matter whether wire-pod replays earlier turns.
2. `conversation.build(PERSONA, user, now)` expires stale history (idle
   timeout), then returns `[persona system] + [stored history] + [this user]`.
3. `backend.stream()` streams the reply as before; the endpoint accumulates the
   text and emits OpenAI SSE unchanged.
4. After a successful stream, `conversation.record(user, reply, now)` appends
   the exchange. Recording AFTER the stream means a failed generation does not
   poison history with a half reply; an empty reply is not recorded.

## Config (env, documented in `.env.example`)

- `PERSONA_FILE` -- character-card path (default `persona.md`).
- `MEMORY_TURNS` -- exchanges of history to keep (default 6; 0 = off).
- `MEMORY_IDLE_TIMEOUT` -- seconds of silence that start a fresh conversation
  (default 300).

`GET /healthz` now also reports `persona` (bool) and `memory_turns`.

## Testing

`test_conversation.py` covers the pure logic without a backend: persona load
(read/strip, missing, blank), `latest_user`, persona prepend/replace, memory
carry-over, whole-exchange eviction, idle-timeout clear, and the disabled/empty
cases. Verified end-to-end with a stub backend through FastAPI's TestClient:
turn 2's context carries turn 1, and the persona replaces wire-pod's system
turn. By-voice confirmation on the Pi is an owner-driven follow-up.

## Follow-ups

- By-voice confirmation on the Pi (deploy: `git pull` + `sudo systemctl restart
  vector-llm-gateway`, set wire-pod's `openai_prompt` empty).
- If a second concurrent speaker ever matters, revisit keying -- but that needs
  a conversation id wire-pod does not currently send.
