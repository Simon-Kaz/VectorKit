# VectorKit

Personal monorepo for developing solutions, prototypes, and automation for the
Anki Vector robot. Anki's cloud went dark in 2019, so this project runs Vector
entirely on a self-hosted stack: a Raspberry Pi 4B (arm64) runs `wire-pod` as
the always-on brain, and Python code drives the robot over its gRPC API.

**Docs site:** https://simon-kaz.github.io/VectorKit/ &mdash; the architecture
diagrams, setup guide, ecosystem research, and roadmap, rendered from `docs/`.

## Current state

- **Robot:** an OSKR / dev-unlocked Vector (`Vector-Z3Y1`, ESN `00805A35`)
  running community firmware **WireOS Dev 3.0.1.32d**, onboarded to our wire-pod.
- **Server:** wire-pod on the Pi (`vector-pod.local`, `192.168.178.66`) in
  escape-pod mode, offline Vosk STT, advertising `escapepod.local`. Voice is
  fully self-hosted (proven: no traffic to any public cloud).
- **Control:** the vendored Python SDK fork authenticates and drives the robot
  over gRPC; `hello-vector` runs from both the dev machine and the Pi.

The full onboarding arc (Phase 2) and foundation hardening (Phase 3 step 1) are
done. Next up is the architecture/understanding work and feature prototypes.
See `docs/PLAN.md` for the live backlog.

## Layout

```
docs/        Research, architecture diagrams, setup guides + the docs website
infra/       Provisioning for the wire-pod server (Raspberry Pi)
libs/        Shared Python helpers (vectorkit) reused by prototypes
libs/vendor/ Vendored Vector Python SDK (our fork, git submodule)
prototypes/  Self-contained experiments, one directory each
```

## The stack

Three layers sit between you and the robot (detail in `docs/landscape.md`):

1. **Server** (cloud replacement) &mdash; `wire-pod`. Free, offline voice via
   Vosk, web UI, escape-pod certs/mDNS. Runs on the Pi.
2. **Auth / setup** &mdash; flash community firmware (**WireOS Dev**) and
   onboard the bot to wire-pod via its web UI. The retail `ep`-firmware path is
   a dead end for a dev/OSKR bot (see `docs/setup-vector.md`).
3. **Control** &mdash; our fork of the Vector Python SDK (vendored under
   `libs/vendor/`) talking to the robot's gRPC API. See
   `prototypes/hello-vector`.

`docs/architecture.md` has Mermaid diagrams of the hardware/network layout,
wire-pod's internals, and how voice and control flow end to end.

## Quick start

This repo vendors the Vector SDK as a git submodule. Clone with:

```bash
git clone --recurse-submodules https://github.com/Simon-Kaz/VectorKit.git
# already cloned? run: git submodule update --init --recursive
```

1. Provision the Pi and install wire-pod: `infra/wire-pod/README.md`.
2. Flash and onboard your Vector: `docs/setup-vector.md`.
3. Set up Python and run the hello-world: `prototypes/hello-vector/README.md`.

## Development

```bash
make setup   # venv + dev deps
make hooks   # install pre-commit and pre-push git hooks
make check   # run all validation (lint, format, shellcheck, actionlint, tests)
```

Validation runs locally as git hooks and in CI via the same `pre-commit`
config, so green locally means green in CI. See `docs/development.md`.

## Requirements

- An Anki / Digital Dream Labs Vector (1.0 or 2.0)
- A Raspberry Pi running 64-bit Raspberry Pi OS (arm64)
- Python 3.9+ on your dev machine
