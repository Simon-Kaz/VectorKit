"""OpenAI-compatible gateway for wire-pod: Claude (cloud) or Ollama (local).

wire-pod's knowledge-graph `custom` provider speaks the OpenAI chat-completions
wire format and expects a streamed (SSE) reply, which it splits on punctuation
and speaks through Vector's voice. This gateway accepts that request and
translates it to whichever backend LLM_BACKEND selects, streaming the reply
back as OpenAI SSE:

    OpenAI /v1/chat/completions
        -> claude:  Anthropic Messages API   (cloud, needs ANTHROPIC_API_KEY)
        -> ollama:  Ollama /api/chat          (local, no API key, stays on LAN)
        -> OpenAI SSE out

Both backends expose the same interface (`.model` + an async `stream()` that
yields text deltas); the endpoint is backend-agnostic. Switch backend/model by
editing the env and restarting -- wire-pod needs no change. The Anthropic
client is only constructed for the claude backend, so a pure-local Ollama host
needs no API key. See docs/design/p3-03-llm-gateway.md.

Persona + conversation memory (P3-06) sit in the endpoint layer, before the
backend, so both backends inherit them: a character-card persona (PERSONA_FILE)
replaces wire-pod's system turn, and a global rolling memory window lets Vector
reference an earlier turn. See conversation.py and
docs/design/p3-06-persona-memory.md.

Run:
    pip install -r requirements.txt
    export LLM_BACKEND=ollama              # or claude (+ ANTHROPIC_API_KEY)
    uvicorn main:app --host 0.0.0.0 --port 8088
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import AsyncIterator

import httpx
from conversation import Conversation, latest_user, load_persona
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

# Which backend is live. The inbound OpenAI `model` field (set in wire-pod) is
# informational only -- the gateway config is the single source of truth.
BACKEND = os.environ.get("LLM_BACKEND", "claude").lower()
# Cap output: spoken answers should be short, and it bounds cost/latency.
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))

# Persona + memory (P3-06), both held here in the gateway. The persona is a
# character card that REPLACES wire-pod's system turn; memory is one global
# rolling window (single-user robot, no conversation id in the request). See
# conversation.py and docs/design/p3-06-persona-memory.md.
PERSONA_FILE = os.environ.get("PERSONA_FILE", "character.json")
# Exchanges (user+reply) of history to keep. Small: the Pi has ~1.2 GB free and
# a sub-1B model has a tight context. 0 disables memory.
MEMORY_TURNS = int(os.environ.get("MEMORY_TURNS", "6"))
# Seconds of silence after which the next question starts a fresh conversation.
MEMORY_IDLE_TIMEOUT = float(os.environ.get("MEMORY_IDLE_TIMEOUT", "300"))

PERSONA = load_persona(PERSONA_FILE)
conversation = Conversation(max_turns=MEMORY_TURNS, idle_timeout=MEMORY_IDLE_TIMEOUT)

# Only user/assistant/system turns carry into the backend; anything else in the
# OpenAI body (tool calls, names) is dropped -- wire-pod never sends them.
_ROLES = ("system", "user", "assistant")


def _messages(body: dict) -> list[dict]:
    """Pull the clean role/content turns out of an OpenAI chat body."""
    return [
        {"role": m["role"], "content": m["content"]}
        for m in body.get("messages", [])
        if m.get("role") in _ROLES and m.get("content")
    ]


class ClaudeBackend:
    """OpenAI-in -> Anthropic Messages API -> text deltas out.

    Translation rules (and why):
    - System turns become Anthropic's top-level `system` (OpenAI inlines them in
      `messages`). wire-pod's persona (`openai_prompt`) rides here untouched.
    - temperature/top_p are dropped: they return HTTP 400 on Opus 4.8 / Fable.
    - `thinking` is omitted to keep spoken replies low-latency.
    """

    def __init__(self) -> None:
        # Imported here so the ollama backend never needs the anthropic package
        # or an API key. Reads ANTHROPIC_API_KEY from the environment.
        from anthropic import AsyncAnthropic

        self.model = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5")
        self._client = AsyncAnthropic()

    async def stream(self, messages: list[dict], max_tokens: int) -> AsyncIterator[str]:
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        args: dict = {
            "model": self.model,
            "messages": [m for m in messages if m["role"] in ("user", "assistant")],
            "max_tokens": max_tokens,
        }
        if system:
            args["system"] = system
        async with self._client.messages.stream(**args) as stream:
            async for text in stream.text_stream:
                yield text


class OllamaBackend:
    """OpenAI-in -> Ollama /api/chat -> text deltas out.

    Ollama already speaks the OpenAI role/content shape (including an inline
    `system` turn), so this is close to a passthrough -- the contrast with the
    Claude translation layer is the point. Everything stays on the LAN; no API
    key. OLLAMA_HOST points at the Ollama server (default localhost:11434).
    """

    def __init__(self) -> None:
        self.model = os.environ.get("OLLAMA_MODEL", "llama3.2")
        self._host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

    async def stream(self, messages: list[dict], max_tokens: int) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            # Disable thinking: reasoning models (gemma4, deepseek-r1, ...) would
            # otherwise spend the whole num_predict budget on `thinking` tokens
            # and stream NO `content` -- Vector would say nothing. Omitting
            # thinking also keeps spoken replies low-latency (same call we make
            # on the claude path). Silently ignored by non-thinking models.
            "think": False,
            "options": {"num_predict": max_tokens},
        }
        # No timeout: a cold model load or a long answer can take a while, and
        # wire-pod is already streaming to the robot as tokens arrive.
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{self._host}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break


def _build_backend():
    if BACKEND == "claude":
        return ClaudeBackend()
    if BACKEND == "ollama":
        return OllamaBackend()
    raise RuntimeError(f"unknown LLM_BACKEND={BACKEND!r} (expected 'claude' or 'ollama')")


backend = _build_backend()
app = FastAPI(title="vector-llm-gateway")


def _chunk(created: int, delta: dict, finish: str | None = None) -> str:
    """Format one OpenAI `chat.completion.chunk` SSE line."""
    payload = {
        "id": "chatcmpl-vector",
        "object": "chat.completion.chunk",
        "created": created,
        "model": backend.model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    return f"data: {json.dumps(payload)}\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(req: Request) -> StreamingResponse:
    body = await req.json()
    max_tokens = min(int(body.get("max_tokens", MAX_TOKENS)), MAX_TOKENS)
    created = int(time.time())

    # Persona + memory both live in the gateway (P3-06). We take only wire-pod's
    # newest question and rebuild the context from the gateway's own rolling
    # history, so the reply is in-persona and can reference an earlier turn.
    user = latest_user(_messages(body))
    messages = conversation.build(PERSONA, user, created) if user else _messages(body)

    async def sse() -> AsyncIterator[str]:
        # First chunk announces the assistant role (OpenAI convention).
        yield _chunk(created, {"role": "assistant"})
        reply: list[str] = []
        async for text in backend.stream(messages, max_tokens):
            reply.append(text)
            yield _chunk(created, {"content": text})
        yield _chunk(created, {}, finish="stop")
        yield "data: [DONE]\n\n"
        # Record the completed exchange only after a successful stream, so a
        # failed generation does not poison the history with a half reply.
        if user:
            conversation.record(user, "".join(reply), created)

    return StreamingResponse(sse(), media_type="text/event-stream")


@app.get("/healthz")
def healthz() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "backend": BACKEND,
            "model": backend.model,
            "persona": bool(PERSONA),
            "memory_turns": MEMORY_TURNS,
        }
    )
