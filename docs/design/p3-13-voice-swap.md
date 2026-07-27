# P3-13 design note: swap Vector's spoken voice (TTS)

Status: feasibility investigation (2026-07-27). No code yet. See `PLAN.md` P3-13.

## Problem

Vector answers in one voice: its stock firmware TTS. We want to make it speak in
a different voice. The P3-03 gateway work explicitly scoped voice OUT, noting
that Vector's on-robot voice via `SayText` allows "no engine swap without
raw-audio piping". This note revisits that line and asks: is a different voice
doable, and at what cost?

## How the voice is produced today

Verified against the live wire-pod on the Pi (`~/wire-pod`, not just the public
repo). The current path:

Vector hears -> wire-pod Vosk STT -> intent/knowledge -> our gateway returns text
-> wire-pod calls `robot.Conn.SayText(..., UseVectorVoice: true)` over gRPC ->
Vector synthesizes the audio on-robot in its one built-in voice.

`SayText` has no voice parameter. The voice is a firmware asset; you cannot pick
a different one through it. Changing the voice therefore means changing WHERE the
audio is produced, not flipping a `SayText` option.

## Key finding: wire-pod already ships the raw-audio-piping path

Our wire-pod fork already implements exactly the "raw-audio piping" the P3-03
note said would be required. In `chipper/pkg/wirepod/ttr/kgsim_cmds.go`,
`DoSayText` has a second branch, `DoSayText_OpenAI`, that:

1. calls OpenAI's `CreateSpeech` TTS API to synthesize the reply text in a chosen
   voice (raw PCM), then
2. streams that audio to the robot's speaker over gRPC via
   `robot.Conn.ExternalAudioStreamPlayback` (16 kHz; downsampled from OpenAI's
   24 kHz by `downsample24kTo16k`).

```go
func DoSayText(input string, robot *vector.Vector) error {
    if (vars.APIConfig.STT.Language != "en-US" && ...Provider == "openai") ||
        vars.APIConfig.Knowledge.OpenAIVoiceWithEnglish {
        return DoSayText_OpenAI(robot, input)   // external voice, streamed audio
    }
    robot.Conn.SayText(..., UseVectorVoice: true, ...)   // stock firmware voice
}
```

Two consequences:

- **Path 3 (firmware voice replacement) is unnecessary and ruled out.** Vector's
  firmware exposes `ExternalAudioStreamPlayback`; any audio, any voice, can be
  streamed to the speaker with zero firmware changes. No OTA territory.
- **The reusable mechanism is engine-agnostic:** `external TTS -> 16 kHz PCM ->
  ExternalAudioStreamPlayback`. OpenAI is just the engine wired up today; a local
  (Piper) or other cloud (ElevenLabs/Azure) engine can drop into the same
  streaming path with a source change to our fork.

## The knobs that exist today

In `apiConfig.json` under `knowledge` (struct in `chipper/pkg/vars/config.go`):

- `openai_voice` -- one of `alloy / onyx / fable / shimmer / nova / echo`
  (defaults to `fable` when blank; see `getOpenAIVoice`).
- `openai_voice_with_english` -- bool. This is the gate. Currently `false`, so on
  our en-US setup we get the stock `SayText` voice.

## The one catch for the OpenAI path: the shared API key

Both the chat call and the TTS call read the same field, `Knowledge.Key`:

- Chat (`kgsim.go`, `custom` provider): `openai.DefaultConfig(Knowledge.Key)` with
  `BaseURL = Knowledge.Endpoint` -> points at OUR local gateway
  (`http://localhost:8088/v1`). Our gateway ignores the auth key entirely
  (verified: `prototypes/llm-gateway/main.py` has no Authorization check).
- TTS (`kgsim_cmds.go`): `openai.NewClient(Knowledge.Key)` with the DEFAULT base
  URL -> hits `api.openai.com`.

So the "collision" resolves cleanly with config alone: put a real OpenAI key in
`Knowledge.Key`. The chat call still works (gateway ignores the key); the TTS
call now authenticates to OpenAI. No code change needed for the OpenAI path.

## Options (increasing effort)

- **A. OpenAI TTS, as-shipped.** Set `openai_voice`, set
  `openai_voice_with_english: true`, put an OpenAI key in `Knowledge.Key`.
  Near-zero code. Cloud round-trip per utterance (latency + per-char cost), only
  6 fixed voices, and philosophically off-stack (the rest of the stack is
  self-hosted). Best for quickly PROVING a different voice sounds right on the
  robot.
- **B. Local Piper TTS in our fork.** Add a Piper branch alongside
  `DoSayText_OpenAI`, reusing the `ExternalAudioStreamPlayback` streaming.
  Self-hosted, custom voices, no cloud, no per-call cost. Cost: a wire-pod source
  change we maintain, plus a resample step (Piper's lessac-medium outputs
  22050 Hz; the robot wants 16 kHz -- analogous to the OpenAI path's 24k->16k).
- **C. Other cloud TTS (ElevenLabs / Azure) in our fork.** Best/custom voice
  quality; cloud dependency + separate key management; more code than A.

## Pi feasibility spot-check (for option B)

Read-only inspection of `vector-pod.local` (2026-07-27):

- Hardware: 4-core aarch64, 1.8 GB RAM (1.4 GB available with wire-pod + Ollama
  running), 19 GB free disk, load average ~0.
- Piper was NOT installed. Benchmarked standalone on the Pi (2026-07-27, Piper
  1.2.0 aarch64 binary + `en_US-lessac-medium`, ~61 MB model, no wire-pod/robot
  changes):
  - **Real-time factor 0.37** -- synthesizes ~2.7x faster than realtime
    (infer 1.6 s for a 4.3 s reply). Latency is a non-issue for our use.
  - Model load ~1.0 s, one-time (paid once if Piper runs as a persistent process,
    not per utterance).
  - Output: 22050 Hz mono 16-bit PCM. The robot CANNOT play this directly:
    Vector's speaker accepts only 8000-16025 Hz, 16-bit, mono (hard constraint
    enforced in the SDK, `anki_vector/audio.py:106`, and the reason wire-pod's
    OpenAI path has a `downsample24kTo16k` step). 22050 Hz exceeds the 16025 Hz
    ceiling, so a resample to 16 kHz is REQUIRED for lessac-medium.
    Alternative: Piper "low"-quality voices are typically 16 kHz native, which
    would fit the window and avoid resampling at the cost of voice quality --
    a lead to confirm, not yet verified on our Pi.
  - Quality (lessac-medium) is good; sample WAV reviewed on the owner's Mac.
  - Verdict: option B is VIABLE on the 2 GB Pi. The open item is a persistent
    Piper process/service (avoid the 1 s load per call) and the resample step.

## Recommendation

Both options are now proven feasible (see test results). Lean toward **option B
(local Piper)** as the target: it is self-hosted (matches the rest of the stack),
free per call, benchmarked fast on our Pi (RTF 0.37), and good quality -- whereas
option A is blocked on a funded OpenAI account and is cloud-dependent by nature.
Option A remains the quickest way to hear a swapped voice come out of the robot
end-to-end (near-zero code) IF a funded key appears, and it already proved the
`ExternalAudioStreamPlayback` streaming works.

Next step for B: build the wire-pod fork change -- a Piper branch in `DoSayText`
that runs a persistent Piper process, gets audio into the robot's 8000-16025 Hz
window (resample lessac-medium 22050->16000, OR use a native-16 kHz "low" voice),
streams via `ExternalAudioStreamPlayback`, and (per the bug below) falls back to
`SayText` on any TTS error.

Requires an OpenAI API key (owner to provide) and a live-robot test -- both need
owner authorization before running.

## Test results (2026-07-27, live robot)

Option A was tested end-to-end on the live robot. The full path worked exactly as
designed -- STT -> gateway (reply text generated fine) -> the OpenAI TTS branch
was reached -- but both API keys tried failed at the OpenAI call, so no audio was
produced:

- `OPENAI_API_KEY_VOICE`: HTTP 429, "You exceeded your current quota". A valid
  `sk-` OpenAI key, but the account has no credit / billing enabled. To use it,
  add billing/credit to that account (Platform > Billing); no config or code
  change needed on our side.
- `OPENAI_API_KEY`: HTTP 401, "Incorrect API key". The value is `zdai_`-prefixed
  -- NOT an OpenAI key (real ones start with `sk-`). Wrong credential entirely.

Neither test cost anything (both rejected before audio generation). The mechanism
(config -> wire-pod -> OpenAI TTS -> `ExternalAudioStreamPlayback`) is proven;
only a funded OpenAI key is missing to hear a swapped voice via option A.

### Bug found: TTS failure mutes the robot (no fallback)

`DoSayText_OpenAI` has no fallback to `SayText`. When the OpenAI call errors
(429/401 above), wire-pod logs "Waiting for more content from LLM..." and the
robot goes SILENT -- it appears stuck rather than falling back to the stock
voice. Any external-TTS path we adopt (OpenAI now, or Piper later) must fall back
to `SayText` on TTS error so a TTS outage does not mute the robot. Capture as a
follow-up for whichever path we build.
