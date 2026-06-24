# Architecture

How the pieces connect once everything is set up.

```
  +---------------------+         LAN (mDNS: escapepod.local)
  |  Raspberry Pi arm64 |
  |                     |
  |   wire-pod server   | <-----------------------------+
  |   - Vosk STT        |                               |
  |   - weather/intents |                               |
  |   - web UI :8080    |                               |
  +----------+----------+                               |
             ^                                          |
             | voice / cloud requests                   | gRPC :443
             |                                          | (camera, motors,
  +----------+----------+                               |  animations, events)
  |    Anki Vector      |                               |
  |  (ep firmware,      | <-----------------------------+
  |   authenticated)    |                               |
  +---------------------+                               |
                                                        |
  +---------------------+                               |
  |   Your Python code  | ------------------------------+
  |  (SDK fork + libs/) |
  |  dev machine or Pi  |
  +---------------------+
```

## Data flow

- Voice: Vector records audio, sends it to wire-pod, which runs Vosk locally
  and returns an intent. No external cloud.
- Control: your Python process authenticates with the robot using credentials
  stored in `~/.anki_vector/` (written during SDK auth) and opens a gRPC
  connection on the LAN. This is independent of the voice path.

## Where code runs

- wire-pod: always on the Pi.
- Python prototypes: anywhere on the LAN. Run on your dev machine while
  iterating; deploy long-running ones to the Pi.

## Credentials

The SDK stores per-robot certs and a token under `~/.anki_vector/`. These are
secret and machine-local. They are gitignored and must never be committed. To
run a prototype on a new machine you re-run the SDK auth step there.

## Conventions

- Shared connection/config helpers live in `libs/` and are imported by
  prototypes, so robot serial/IP handling exists in one place.
- Each prototype is self-contained under `prototypes/<name>/` with its own
  README and entry point.
