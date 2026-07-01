"""OpenAI-compatible -> Anthropic streaming gateway for wire-pod.

wire-pod's knowledge-graph `custom` provider speaks the OpenAI
chat-completions wire format and expects a streamed (SSE) reply, which it
splits on punctuation and speaks through Vector's voice. Claude's native API is
different, so this gateway translates:

    OpenAI /v1/chat/completions  ->  Anthropic Messages API  ->  OpenAI SSE out

Point wire-pod's knowledge `endpoint` at `http://<this-host>:8088/v1` (see the
README). Switch the live model by editing CLAUDE_MODEL and restarting -- wire-pod
needs no change. See docs/design/p3-03-llm-gateway.md.

Run:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=...           # never commit this
    uvicorn main:app --host 0.0.0.0 --port 8088
"""

from __future__ import annotations

import json
import os
import time

from anthropic import AsyncAnthropic
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

# The gateway config is the single source of truth for which model is live --
# the inbound OpenAI `model` field (set in wire-pod) is informational only.
MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5")
# Cap output: spoken answers should be short, and it bounds cost/latency.
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))

# Reads ANTHROPIC_API_KEY from the environment. Constructed once, reused.
client = AsyncAnthropic()
app = FastAPI(title="vector-llm-gateway")


def to_anthropic(body: dict) -> dict:
    """Translate an OpenAI chat-completions body to Anthropic Messages args.

    - System turns become Anthropic's top-level `system` (OpenAI inlines them in
      `messages`). wire-pod's persona (`openai_prompt`) rides here untouched.
    - temperature/top_p are dropped: they return HTTP 400 on Opus 4.8 / Fable.
    - `thinking` is omitted to keep spoken replies low-latency.
    """
    messages = body.get("messages", [])
    system = "\n".join(
        m["content"] for m in messages if m.get("role") == "system" and m.get("content")
    )
    msgs = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m.get("role") in ("user", "assistant")
    ]
    args: dict = {
        "model": MODEL,
        "messages": msgs,
        "max_tokens": min(int(body.get("max_tokens", MAX_TOKENS)), MAX_TOKENS),
    }
    if system:
        args["system"] = system
    return args


def _chunk(created: int, delta: dict, finish: str | None = None) -> str:
    """Format one OpenAI `chat.completion.chunk` SSE line."""
    payload = {
        "id": "chatcmpl-vector",
        "object": "chat.completion.chunk",
        "created": created,
        "model": MODEL,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    return f"data: {json.dumps(payload)}\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(req: Request) -> StreamingResponse:
    body = await req.json()
    args = to_anthropic(body)
    created = int(time.time())

    async def sse():
        # First chunk announces the assistant role (OpenAI convention).
        yield _chunk(created, {"role": "assistant"})
        async with client.messages.stream(**args) as stream:
            async for text in stream.text_stream:
                yield _chunk(created, {"content": text})
        yield _chunk(created, {}, finish="stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")


@app.get("/healthz")
def healthz() -> JSONResponse:
    return JSONResponse({"ok": True, "model": MODEL})
