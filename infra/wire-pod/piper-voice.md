# Piper voice (custom TTS) on wire-pod

How to replicate or migrate the local Piper TTS voice swap (VectorKit P3-13 /
P3-14). This is our one custom change to wire-pod: Vector speaks the LLM answer
in a local Piper voice (`en_US-danny-low`) instead of the stock firmware voice.

Design rationale and the feasibility work live in
`../../docs/design/p3-13-voice-swap.md`. This file is the operational recipe:
what is installed where, how to rebuild, and how to verify.

## What the setup consists of

Three independent pieces. To replicate on a fresh Pi, do all three; to migrate
to a new host, carry all three across.

1. **Our wire-pod fork.** The voice code lives in a fork of upstream, not in
   this repo: `https://github.com/Simon-Kaz/wire-pod` (branched off
   `kercre123/wire-pod`). Relevant code, all in `chipper/pkg/wirepod/ttr/`:
   - `piper.go` -- the persistent Piper process (`piperSynth`).
   - `kgsim_cmds.go` -- `DoSayText_Piper`, the `DoSayText` router, and the
     `SayText` fallback on any external-TTS error.
   - `pkg/vars/config.go` -- the `piper_enable` / `piper_binary` / `piper_voice`
     config fields.
2. **The Piper binary + voice model**, installed on the Pi at `/opt/piper`
   (outside the wire-pod checkout, so a wire-pod update never touches it).
3. **The config flags** in `chipper/apiConfig.json` that turn it on.

## 1. Install Piper + the voice model

Piper 1.2.0 (aarch64) and the `en_US-danny-low` voice. Run on the Pi:

```bash
# Binary: extracts to /opt/piper/piper/ (binary + bundled .so libs alongside).
cd /tmp
curl -fsSL -o piper.tar.gz \
  "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz"
sudo rm -rf /opt/piper && sudo mkdir -p /opt/piper
sudo tar -xzf piper.tar.gz -C /opt/piper && rm piper.tar.gz

# Voice: en_US-danny-low is 16 kHz NATIVE, so it needs no resampling to fit the
# robot speaker's 8000-16025 Hz window. Any other voice MUST be 16 kHz.
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/danny/low"
sudo curl -fsSL -o /opt/piper/en_US-danny-low.onnx      "$BASE/en_US-danny-low.onnx"
sudo curl -fsSL -o /opt/piper/en_US-danny-low.onnx.json "$BASE/en_US-danny-low.onnx.json"
```

Resulting layout:
- Binary: `/opt/piper/piper/piper` (run with `LD_LIBRARY_PATH=/opt/piper/piper`;
  wire-pod sets this itself from the binary's directory).
- Voice: `/opt/piper/en_US-danny-low.onnx` (+ `.onnx.json`).

Smoke-test standalone before wiring it in:

```bash
echo "Hello, I am Vector." | LD_LIBRARY_PATH=/opt/piper/piper \
  /opt/piper/piper/piper --model /opt/piper/en_US-danny-low.onnx --output-raw \
  > /tmp/t.pcm && ls -l /tmp/t.pcm && rm /tmp/t.pcm
```

Expect a non-empty file and a `Real-time factor` around 0.28 in the log.

## 2. Deploy the fork code

wire-pod runs from a source checkout on the Pi (`~/wire-pod`, installed per
`README.md`). Point that checkout at our fork branch instead of upstream:

```bash
cd ~/wire-pod
git remote add fork https://github.com/Simon-Kaz/wire-pod.git   # once
git fetch fork
git checkout -B piper-deploy fork/main   # fork/main carries the merged voice code
```

**Then you MUST rebuild the binary.** `start.sh` runs the prebuilt
`./chipper/chipper` if it exists -- it does NOT recompile from source on
restart. Editing or checking out source alone has no effect until you rebuild.
Use the upstream build path (rebuilds `./chipper/chipper` from the current
checkout, as `install.sh` did originally):

```bash
cd ~/wire-pod
sudo STT=vosk ./setup.sh daemon-enable
sudo systemctl restart wire-pod
```

(That rebuilds against the vosk STT backend, matching this Pi. It also rewrites
the systemd unit, which is harmless -- same paths.)

## 3. Enable Piper in the config

`chipper/apiConfig.json` is root-owned. Set the three flags (default is off, so
Piper does nothing until enabled):

```bash
sudo python3 - <<'PY'
import json
p="/home/vector/wire-pod/chipper/apiConfig.json"
d=json.load(open(p)); k=d["knowledge"]
k["piper_enable"]=True
k["piper_binary"]="/opt/piper/piper/piper"
k["piper_voice"]="/opt/piper/en_US-danny-low.onnx"
json.dump(d,open(p,"w"),indent=2)
PY
sudo systemctl restart wire-pod
```

Note: only a Piper-aware binary preserves these fields. If an OLD chipper binary
starts, it rewrites `apiConfig.json` and silently drops the unknown Piper keys --
re-set them after any binary swap.

## Verify

```bash
systemctl is-active wire-pod
```

Say to Vector: "Hey Vector, I have a question. How are you?" -- the answer should
come out in the danny voice. The log shows the process starting once and being
reused:

```bash
sudo journalctl -u wire-pod --since "2 min ago" --no-pager | grep -i piper
# Piper: started persistent process (voice en_US-danny-low.onnx)   <- once
```

**Fallback check:** point `piper_voice` at a bad path, restart, ask again --
Vector must answer in the STOCK voice (not go silent). The log shows
`Piper TTS failed, falling back to SayText`. Restore the good path afterwards.

## How it works (so you can debug it)

- The gateway's streaming path (`KGSim`) splits the LLM answer on `". "` and
  calls `DoSayText` once per sentence. `DoSayText` routes to `DoSayText_Piper`
  when `piper_enable` is set.
- `piperSynth` (in `piper.go`) keeps ONE long-lived Piper process in WAV mode
  (`-f -`) with the model loaded, so sentences don't each pay the ~1s model
  load. It is mutex-serialized, lazily started, and respawned if it dies or the
  configured binary/voice changes. Each call writes one line and reads back
  exactly one WAV (framed by the RIFF data-chunk size).
- On ANY Piper error the process is killed and an error returned, so `DoSayText`
  falls back to the stock `SayText` voice. The robot never goes silent.

## Known limitations

- The firmware "ready" acknowledgment (spoken when the knowledge-question intent
  fires, before your question is captured) is firmware TTS and is NOT routed
  through wire-pod, so it stays in Vector's stock voice. Only the LLM answer is
  swapped. See PLAN P3-15.
- Response latency is dominated by the local LLM gateway (Ollama), not Piper.

## Migrating to a new Pi

1. Provision + install wire-pod (`../raspberry-pi/README.md`, then `install.sh`).
2. Redo section 1 (install Piper + voice at `/opt/piper`).
3. Redo section 2 (point the checkout at `fork/main`, rebuild).
4. Redo section 3 (set the config flags).
Nothing about the voice setup is host-specific beyond these paths.
