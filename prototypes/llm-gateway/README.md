# llm-gateway (P3-03, Phase A)

A thin OpenAI-compatible -> Anthropic streaming gateway. wire-pod's
knowledge-graph `custom` provider calls it like an OpenAI chat endpoint; it
translates each request to Claude's native Messages API and streams the reply
back as OpenAI SSE, which wire-pod splits and speaks through Vector's voice.

Switch the live model by editing one env var and restarting -- wire-pod never
changes. That config-only swap is the "pluggable backend" the task asks for.

Design + rationale: `docs/design/p3-03-llm-gateway.md`.

## How it fits in

```
"Hey Vector, I have a question"
  -> Vector --TLS 443--> wire-pod (Vosk STT, knowledge_question intent)
       -> POST /v1/chat/completions (OpenAI, stream)  -->  THIS GATEWAY (:8088)
            -> client.messages.stream()  -->  Anthropic / Claude
            -> OpenAI SSE chunks back
  -> wire-pod splits on punctuation -> SayText -> Vector speaks
```

## Run

```sh
cd prototypes/llm-gateway
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then put your ANTHROPIC_API_KEY in .env
set -a; . ./.env; set +a      # export the .env vars into this shell
uvicorn main:app --host 0.0.0.0 --port "${GATEWAY_PORT:-8088}"
```

Where to run it: the **Pi** (alongside wire-pod) for an always-on setup --
wire-pod then points at `http://localhost:8088/v1`. For iterating on this
worked example, run it on the **dev Mac** first (watch the logs live) with
wire-pod pointed at `http://<mac-ip>:8088/v1`, then move it to the Pi as a
systemd service. The API key lives in a gitignored `.env` on whichever host runs
it.

## Point wire-pod at it (one-time, no code change)

Set the knowledge-graph config to the `custom` provider -- web UI at
`http://vector-pod.local:8080`, `POST /api/set_kg_api`, or edit
`~/wire-pod/apiConfig.json` then restart wire-pod:

- `enable = true`
- `provider = "custom"`
- `endpoint = "http://<gateway-host>:8088/v1"`
- `key = "local"` (ignored by the gateway)
- `model = "claude-haiku-4-5"` (informational; the gateway picks the real model)
- optional `intentgraph = true` -- send any unmatched phrase to the LLM.

Trigger the LLM path with "Hey Vector, I have a question".

## Verify

1. **Gateway alone** -- stream a reply with an OpenAI-shaped request:

   ```sh
   curl -N http://localhost:8088/v1/chat/completions \
     -H 'content-type: application/json' \
     -d '{"model":"x","stream":true,"messages":[
           {"role":"system","content":"You are Vector, a helpful robot. Be brief."},
           {"role":"user","content":"In one sentence, why is the sky blue?"}]}'
   ```

   Expect `data: {...}` chunks streaming Claude's answer, ending in `data: [DONE]`.
   `curl http://localhost:8088/healthz` reports the live model.

2. **Through wire-pod** -- point the `custom` endpoint at the gateway, restart
   wire-pod, say "Hey Vector, I have a question" then a question. Vector speaks
   Claude's answer. Tail the gateway log to see the request + streamed reply.

3. **Config switch (proves the abstraction)** -- set `CLAUDE_MODEL=claude-opus-4-8`
   in `.env`, restart **only** the gateway, ask again -> richer answer. No
   wire-pod change. (Haiku <-> Opus stands in for cloud <-> local until the local
   backend lands in P3-05.)

## Not in this prototype

Persona + conversation memory (P3-06), vision (P3-07), a local Ollama backend
(P3-05), and LLM-driven robot actions are deliberately out of scope -- see the
design note's roadmap.
