# Vector

Personal monorepo for developing solutions, prototypes, and automation for the
Anki Vector robot. Anki's cloud went dark in 2019, so this project runs Vector
entirely on a self-hosted stack: a Raspberry Pi (arm64) runs `wire-pod` as the
always-on brain, and Python code drives the robot over its gRPC API.

## Layout

```
docs/        Research, architecture notes, and setup guides
infra/       Provisioning for the wire-pod server (Raspberry Pi)
libs/        Shared Python helpers (vectorkit) reused by prototypes
libs/vendor/ Vendored Vector Python SDK (our fork, git submodule)
prototypes/  Self-contained experiments, one directory each
```

## The stack

Three layers sit between you and the robot:

1. Server (cloud replacement) - `wire-pod`. Free, offline voice via Vosk,
   works with retail Vectors. Runs on the Pi.
2. Auth/setup - flash DDL `ep` firmware and authenticate the bot to wire-pod.
   See `docs/setup-vector.md`.
3. Control - our fork of the Vector Python SDK (vendored under `libs/vendor/`)
   talking to the robot's gRPC API. See `prototypes/hello-vector`.

See `docs/landscape.md` for the full research writeup and `docs/architecture.md`
for how the pieces fit together.

## Quick start

This repo vendors the Vector SDK as a git submodule. Clone with:

```bash
git clone --recurse-submodules https://github.com/Simon-Kaz/VectorKit.git
# already cloned? run: git submodule update --init --recursive
```

1. Provision the Pi and install wire-pod: `infra/wire-pod/README.md`.
2. Flash and authenticate your Vector: `docs/setup-vector.md`.
3. Set up Python and run the hello-world: `prototypes/hello-vector/README.md`.

## Requirements

- An Anki / Digital Dream Labs Vector (1.0 or 2.0)
- A Raspberry Pi running 64-bit Raspberry Pi OS (arm64)
- Python 3.9+ on your dev machine
