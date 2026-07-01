# P3-03 design note: LLM gateway (pluggable model backend)

Status: Phase A in progress (2026-06-30). See `PLAN.md` P3-03.

## Problem

Anki's cloud is dead; Vector runs on self-hosted wire-pod. We want Vector to
answer open questions ("Hey Vector, I have a question") through any LLM -- local
or cloud, any provider -- behind one interface, instead of being tied to a
vendor. The spike had two open questions: where to integrate, and what
abstraction to use.

## Key finding: wire-pod already has a pluggable LLM backend

Verified against the live wire-pod on the Pi (`~/wire-pod`, not just the public
repo). wire-pod's knowledge-graph code
(`chipper/pkg/wirepod/ttr/kgsim.go`) selects a provider and the `custom` case is
the exact seam we need:

```go
case "custom":
    conf := openai.DefaultConfig(vars.APIConfig.Knowledge.Key)
    conf.BaseURL = vars.APIConfig.Knowledge.Endpoint   // <- point this anywhere
    c = openai.NewClientWithConfig(conf)
```

It uses the OpenAI-compatible `go-openai` client, sends a chat-completions
request with `Stream: true`, splits the streamed reply on punctuation, and speaks
each sentence via the robot's own TTS -- with touch / wake-word interrupt
handling already built in. So the "single interface" the task asks for already
exists: an **OpenAI-compatible streaming endpoint**. The design work is choosing
what sits behind it.

The knowledge-graph config struct (`chipper/pkg/vars/config.go`) exposes:
`enable`, `provider` (`together` / `openai` / `custom`), `key`, `model`,
`endpoint`, `openai_prompt` (the persona/system prompt), `intentgraph` (route any
unmatched phrase to the LLM), `commands_enable` (string-template robot actions),
`temp`, `top_p`. Editable via the web UI, `POST /api/set_kg_api`, or
`~/wire-pod/apiConfig.json`.

## Decisions

**Integration point: intercept at wire-pod's knowledge-graph `custom` provider.**
Not our own SDK-over-gRPC code. wire-pod already owns STT (Vosk), intent routing,
sentence-splitting, streaming TTS through Vector's voice, and touch/wake-word
interrupts. Driving responses from the SDK would mean re-implementing all of that
and racing wire-pod for behavior control. The voice path is wire-pod's; we plug
into the one seam it offers. (`vectorkit.robot_session` is therefore not used on
this path -- it stays the tool for SDK-driven prototypes like the future vision
work.)

**Abstraction: a thin OpenAI-compatible gateway we own, in this repo.** wire-pod
points at it once; backends switch in the gateway's own config with no wire-pod
change. Considered and rejected:
- *Pure wire-pod config* (point `endpoint` straight at a backend): no owned seam
  to inject persona, translate formats, hold memory, or add backends; switching
  edits wire-pod each time.
- *LiteLLM proxy*: maintained and capable, but a heavier dependency and more of a
  black box for a worked example whose point is understanding. Kept as an easy
  future migration -- the wire-pod config is identical, so swapping our gateway
  for LiteLLM later is a one-line endpoint change.

**Why a gateway and not Anthropic's OpenAI-compatible endpoint directly.**
Pointing wire-pod straight at Anthropic would leave no owned seam for persona,
format translation, memory, local backends, or the LiteLLM migration -- and the
recommended path is the native Messages API, not a compatibility shim. The
gateway translates **OpenAI-in -> Anthropic Messages API -> OpenAI-SSE-out**,
which is exactly the bridge the native SDK is for.

**Backend day one: Claude via the Anthropic API** (owner's personal key). Default
model `claude-haiku-4-5` (fastest/cheapest -- right for short spoken answers),
with `claude-opus-4-8` as the richer-answer switch. A local backend (Ollama) is
deferred (no hosting capacity now) but the gateway is built to drop it in -- see
P3-05. The task's "one local + one cloud, switchable by config" is demonstrated
now by switching Haiku <-> Opus by config alone.

## Data flow

```mermaid
sequenceDiagram
    participant U as User (voice)
    participant V as Vector
    participant P as wire-pod (escapepod.local:443)
    participant G as Our gateway (:8088)
    participant A as Anthropic API (Claude)

    Note over U,A: LLM path -- transcript leaves the LAN to Anthropic (opt-in)
    U->>V: "Hey Vector, I have a question" + the question
    V->>P: TLS 443 -- streamed audio
    P->>P: Vosk STT -> transcript; knowledge_question intent
    P->>G: POST /v1/chat/completions (OpenAI, stream=true)
    G->>A: client.messages.stream() (Anthropic Messages API)
    A-->>G: streamed text deltas
    G-->>P: OpenAI SSE chunks (data: {...}) ... data: [DONE]
    P->>P: split on punctuation
    P->>V: SayText per sentence
    V->>U: speaks Claude's answer
```

Switch backend/model = edit the gateway's env + restart the gateway. wire-pod
config never changes after the one-time setup.

## Translation rules (and why)

- **System message** is a separate top-level Anthropic param; OpenAI puts it in
  `messages`. The gateway extracts it, so wire-pod's Vector persona
  (`openai_prompt`) flows through untouched -- the persona stays configured in
  wire-pod.
- **Strip `temperature` / `top_p`** -- they return HTTP 400 on Opus 4.8 (and
  Fable). Steer via prompt instead.
- **Omit `thinking`** -- keeps spoken replies low-latency.
- **Ignore the inbound `model` name**; use the gateway's `CLAUDE_MODEL`. The
  gateway config is the single source of truth for which backend/model is live --
  the whole point of the abstraction.
- **OpenAI SSE out** (`chat.completion.chunk` deltas ending in `data: [DONE]`) is
  exactly what wire-pod's go-openai stream reader expects, so it splits and speaks
  as Claude generates.

## Privacy note (opt-in)

On the LLM path, the transcribed question leaves the LAN and is sent to Anthropic.
This is a deliberate departure from the otherwise fully self-hosted setup (voice,
STT, intents all stay on the Pi). Only knowledge-graph questions take this path --
normal intents (time, weather) never leave wire-pod. A local backend (P3-05)
restores full self-hosting for the LLM path too; until then, cloud LLM use is an
explicit, conscious opt-in enabled by setting `provider=custom` and turning the
knowledge graph on.

## wire-pod config recipe (one-time, no code change)

Set the knowledge-graph config to the `custom` provider via the web UI
(`http://vector-pod.local:8080`), `POST /api/set_kg_api`, or by editing
`~/wire-pod/apiConfig.json` and restarting wire-pod:

- `enable = true`
- `provider = "custom"`
- `endpoint = "http://<gateway-host>:8088/v1"`
- `key = "local"` (the gateway ignores it)
- `model = "claude-haiku-4-5"` (informational; the gateway picks the real model)
- optional `intentgraph = true` -- route any unmatched phrase to the LLM instead
  of failing.

Trigger the LLM path with "Hey Vector, I have a question".

## TARS-AI: analogous open project + design validation

`TARS-AI-Community/TARS-AI` (successor to `poboisvert/GPTARS_Interstellar`) is a
Python stack that runs **on** a Raspberry Pi which **is** the robot. It ships the
exact abstraction this note lands on: a single `llm_backend` selector + `base_url`
pointing at any OpenAI-compatible endpoint, swapping OpenAI / Ollama / LM Studio /
Oobabooga / TabbyAPI / DeepInfra by config. That is external validation of the
design. The one thing TARS-AI never needed is an Anthropic translation layer
(everything it targets already speaks OpenAI) -- which is precisely what our
gateway adds, and why it's a gateway and not a direct point-at-Anthropic.

What transfers to Vector vs. what doesn't (Vector is a closed appliance; we reach
it only through wire-pod's voice path + the gRPC SDK):

| TARS-AI capability | On Vector | Verdict |
|---|---|---|
| `llm_backend` + `base_url` (OpenAI-compat) | wire-pod `custom` provider + this gateway | Same pattern (this task) |
| Character-card persona | wire-pod `openai_prompt` / gateway | Direct map (Phase B / P3-06) |
| Memory (HybridRAG) | held in the gateway | Maps as a gateway extension (P3-06) |
| Vision (BLIP) | gRPC camera frame -> vision model | Separate SDK prototype (Phase C / P3-07) |
| Custom "hey tars" wake word | escape-pod custom wake-word option | Viable today (P3-08) |
| STT (Whisper/Vosk) | wire-pod's Vosk | Given to us; not freely swappable |
| TTS (Piper/ElevenLabs) | Vector's on-robot voice via SayText | Given to us; no engine swap without raw-audio piping |
| LLM tool-calling (search/HA) | wire-pod `commands_enable`, or gateway -> SDK behaviors | Possible, advanced (out of scope) |
| Servo control (PCA9685) | SDK behaviors via the behavior tree | Different mechanism |

## Roadmap

- **Phase A (this task, P3-03):** thin Claude gateway, config-switchable model.
- **Phase B (P3-06):** TARS-style persona + conversation memory held in the
  gateway (wire-pod keeps only ~16 messages).
- **Phase C (P3-07):** SDK-driven vision prototype -- gRPC camera frame -> vision
  model -> Vector speaks what it sees. Independent of the voice path.
- **P3-05:** add an Ollama (local) backend to the gateway -- the deferred half of
  "one local + one cloud."
- **P3-08:** custom "Hey X" wake word via escape-pod's existing option.

## Prototype

See `prototypes/llm-gateway/` for the gateway and a run/verify walkthrough.
