# llm-gateway (P3-03 + P3-05)

A thin OpenAI-compatible gateway that fronts a pluggable LLM backend for
wire-pod. wire-pod's knowledge-graph `custom` provider calls it like an OpenAI
chat endpoint; the gateway routes to the backend `LLM_BACKEND` selects and
streams the reply back as OpenAI SSE, which wire-pod splits and speaks through
Vector's voice.

Two backends:

- **`claude`** (cloud) -- translates to Claude's native Messages API. Sends the
  transcript to Anthropic, so it leaves the LAN. Needs `ANTHROPIC_API_KEY`.
- **`ollama`** (local) -- talks to a local Ollama server's `/api/chat`. Fully
  self-hosted: no API key, the transcript never leaves the LAN.

Switch backend or model by editing one env var and restarting -- wire-pod never
changes. That config-only swap is the "pluggable backend" the task asks for, and
`claude` <-> `ollama` is the "one cloud + one local" pair (P3-05).

Persona + conversation memory (P3-06) sit in front of both backends: a
character-card persona (`persona.md`) replaces wire-pod's system prompt, and a
rolling memory window lets Vector reference an earlier turn in the same
conversation. Both are config, no wire-pod change. See "Persona + memory" below.

Design + rationale: `docs/design/p3-03-llm-gateway.md` (gateway),
`docs/design/p3-06-persona-memory.md` (persona + memory).

## How it fits in

```
"Hey Vector, I have a question"
  -> Vector --TLS 443--> wire-pod (Vosk STT, knowledge_question intent)
       -> POST /v1/chat/completions (OpenAI, stream)  -->  THIS GATEWAY (:8088)
            -> claude:  Anthropic / Claude   (cloud)
               ollama:  local Ollama server  (LAN)
            -> OpenAI SSE chunks back
  -> wire-pod splits on punctuation -> SayText -> Vector speaks
```

## Run

```sh
cd prototypes/llm-gateway
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set LLM_BACKEND (+ ANTHROPIC_API_KEY for claude)
set -a; . ./.env; set +a      # export the .env vars into this shell
uvicorn main:app --host 0.0.0.0 --port "${GATEWAY_PORT:-8088}"
```

For the **ollama** backend you also need a running Ollama server with the model
pulled:

```sh
ollama serve                  # if not already running
ollama pull llama3.2          # must match OLLAMA_MODEL
```

Where to run it: the **Pi** (alongside wire-pod) for an always-on setup --
wire-pod then points at `http://localhost:8088/v1`. For iterating on this
worked example, run it on the **dev Mac** first (watch the logs live) with
wire-pod pointed at `http://<mac-ip>:8088/v1`, then move it to the Pi as a
systemd service. The API key (claude backend) lives in a gitignored `.env` on
whichever host runs it.

## Always-on (systemd, on the Pi)

`vector-llm-gateway.service` in this dir is the unit that keeps the gateway
running across reboots. It assumes the venv + `.env` set up above, and starts
after `ollama.service`. Install it (paths in the unit expect
`/home/vector/VectorKit/prototypes/llm-gateway`):

```sh
sudo install -m 0644 vector-llm-gateway.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vector-llm-gateway
curl -s http://localhost:8088/healthz    # {"ok":true,"backend":...,"model":...}
```

After `LLM_BACKEND` / model changes in `.env`, `sudo systemctl restart
vector-llm-gateway`. Ollama itself already runs as its own systemd service.

## Persona + memory (P3-06)

Both live in the gateway, in front of whichever backend is selected, so they
apply to `claude` and `ollama` alike. Config in `.env` (see `.env.example`):

- `PERSONA_FILE` (default `persona.md`) -- a character card loaded at startup.
  It **replaces** any system prompt wire-pod sends, so the gateway owns Vector's
  character. Edit `persona.md` and restart the gateway to change it. Set
  wire-pod's `openai_prompt` empty to avoid a stale second persona. A missing or
  blank file = no persona (the pre-P3-06 behavior).
- `MEMORY_TURNS` (default 6) -- exchanges of history kept in a rolling window so
  Vector can reference an earlier turn. `0` disables memory. Kept small for the
  2 GB Pi. In-memory only: resets on gateway restart.
- `MEMORY_IDLE_TIMEOUT` (default 300s) -- silence after which the next question
  starts a fresh conversation (there is no per-conversation id to key on -- the
  robot is single-user).

`curl http://localhost:8088/healthz` reports `persona` (bool) and `memory_turns`.
Design + rationale: `docs/design/p3-06-persona-memory.md`.

## Point wire-pod at it (one-time, no code change)

Set the knowledge-graph config to the `custom` provider -- web UI at
`http://vector-pod.local:8080`, `POST /api/set_kg_api`, or edit
`~/wire-pod/apiConfig.json` then restart wire-pod:

- `enable = true`
- `provider = "custom"`
- `endpoint = "http://<gateway-host>:8088/v1"`
- `key = "local"` (ignored by the gateway)
- `model = "gateway"` (informational; the gateway picks the real backend/model)
- optional `intentgraph = true` -- send any unmatched phrase to the LLM.

Trigger the LLM path with "Hey Vector, I have a question".

## Verify

1. **Gateway alone** -- stream a reply with an OpenAI-shaped request (works the
   same against either backend):

   ```sh
   curl -N http://localhost:8088/v1/chat/completions \
     -H 'content-type: application/json' \
     -d '{"model":"x","stream":true,"messages":[
           {"role":"system","content":"You are Vector, a helpful robot. Be brief."},
           {"role":"user","content":"In one sentence, why is the sky blue?"}]}'
   ```

   Expect `data: {...}` chunks streaming the answer, ending in `data: [DONE]`.
   `curl http://localhost:8088/healthz` reports the live backend + model.

2. **Through wire-pod** -- point the `custom` endpoint at the gateway, restart
   wire-pod, say "Hey Vector, I have a question" then a question. Vector speaks
   the answer. Tail the gateway log to see the request + streamed reply.

3. **Backend switch (proves the abstraction)** -- set `LLM_BACKEND=ollama` (or
   flip back to `claude`) in `.env`, restart **only** the gateway, ask again ->
   answered by the other backend. No wire-pod change. This is the "one local +
   one cloud, switchable by config" the task asks for -- cloud (Claude) and
   local (Ollama), swapped by one env var.

## Not in this prototype

Vision (P3-07) and LLM-driven robot actions are deliberately out of scope -- see
the design note's roadmap. Persona + conversation memory shipped in P3-06 (see
"Persona + memory" above).
