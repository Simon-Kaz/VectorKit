# Vector ecosystem: landscape research

Research snapshot as of 2026-06. The goal: run an Anki Vector with no
dependency on Anki's dead servers, and drive it with custom code.

## Background

Anki shut down in May 2019 and never released source. Vector depended on
Anki's cloud for voice queries and registration; without it the robot is
"deaf" and cannot be set up by a new owner. Digital Dream Labs (DDL) acquired
the assets, ran a ~$500k Kickstarter for an "Open Source Kit for Robots"
(OSKR), and open-sourced parts of the stack. The community built free
self-hosted servers on top of that code.

## Three layers

Any working setup has three distinct layers. Conflating them is the main
source of confusion.

1. Server (cloud replacement). Handles speech-to-text, weather, knowledge
   queries, and bot registration. Replaces Anki's cloud.
2. Auth / setup. Puts the robot in recovery, flashes DDL firmware whose
   version string ends in `ep`, and authenticates the bot to your server.
3. Programmatic control. Your code talks to the robot's gRPC API to read the
   camera, drive motors, play animations, and subscribe to events.

## Options by layer

### Server

| Option | Cost | State | Notes |
|---|---|---|---|
| wire-pod | Free (MIT) | Active | Recommended. Offline Vosk STT, retail bot support, web UI. |
| DDL Escape Pod | Paid | Maintained | Turnkey, less hackable. |
| chipper (raw OSKR) | Free | Dormant | wire-pod is built from this. Reference only. |

We standardize on **wire-pod**.

### Auth / setup

- wire-pod's built-in web UI (and BLE scan) handles onboarding.
- `digital-dream-labs/vector-web-setup` is the original tool; superseded by
  wire-pod's flow for our purposes.
- Retail Vectors MUST be flashed with `ep`-suffixed firmware via recovery
  mode. Being on stock v2.0.x is NOT sufficient.

### Control

The Python SDK ecosystem is frozen. Verified last-commit dates (2026-06):

| SDK | Last commit | Notes |
|---|---|---|
| `kercre123/wirepod-vector-python-sdk` | 2024-03-14 | Most-maintained baseline. wire-pod auth built in, Python 3.11. |
| `cyb3rdog/vector-python-sdk` | 2021-12-12 | Added EscapePod/OSKR support. Stale. |
| `anki/vector-python-sdk` | 2020-04-26 | Official, dead. |

Fork lineage: Anki -> cyb3rdog (EscapePod/OSKR) -> MoonDog83 (py3.11 +
regenerated proto) -> kercre123 (wire-pod auth). The only forks with
2025/2026 activity (ZaviiNet, froggitti) carry CI/doc tweaks, not functional
SDK changes - so kercre123's is the real head, and it has been untouched for
~2 years.

Decision: there is no actively-maintained Vector Python SDK, and there does
not need to be - the gRPC protocol is fixed and reverse-engineered. We do NOT
write our own from scratch (the value is in the regenerated protobuf bindings
and the wire-pod auth flow, already solved). Instead we fork
`kercre123/wirepod-vector-python-sdk` into our own account and vendor it as a
git submodule under `libs/vendor/`, pinned by commit for reproducibility. We
own it and patch as needed; we pull upstream manually since upstream is
effectively dormant.

Go is the native language of wire-pod/chipper - use it for server plugins.

## Key repositories

- `kercre123/wire-pod` - the actual server code (MIT, active).
- `kercre123/WirePod` - packaging/build layer that produces installers and
  releases for wire-pod. Very active; latest releases live here, not in
  wire-pod. wire-pod is included as a submodule. This is where you download
  installers from.
- `digital-dream-labs/*` - OSKR upstream: `chipper`, `vector-cloud`,
  `vector-web-setup`, `vector-bluetooth`, `oskr-owners-manual`. Mostly
  dormant (2022-2023) but authoritative reference.
- `anki/vector-python-sdk` - official SDK (abandoned).
- project-victor.org - early community effort; largely historical now.

## Decision

- Server: wire-pod, installed from WirePod releases.
- Host: Raspberry Pi 4B on 64-bit Pi OS (arm64), always-on, same LAN as
  Vector. Headless - the 4B has the CPU/RAM for Vosk STT. (A Pi Zero 2 W is
  too tight for STT and is reserved for a future display prototype.)
- Control language: Python, via our fork of
  `kercre123/wirepod-vector-python-sdk` vendored under `libs/vendor/`.

See `architecture.md` for how these connect.
