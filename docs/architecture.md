# Architecture

How the pieces connect once everything is set up. Three views: the
hardware/network layout, what runs inside wire-pod, and how a voice command and
an SDK command actually flow end to end.

The concrete facts (firmware versions, IPs, the dead ends) live in
`setup-vector.md` and `landscape.md`; this file is the map.

## View A: hardware and network

Everything sits on one LAN behind a FRITZ!Box router. Two addresses are pinned
by DHCP reservation so configs stay valid across reboots (see P1-03): the Pi at
`.66` and (intended) Vector at `.67`.

```mermaid
graph TB
    subgraph LAN["Home LAN (FRITZ!Box, 192.168.178.0/24)"]
        router["FRITZ!Box router<br/>DHCP + reservations"]

        vector["Anki Vector 'Vector-Z3Y1'<br/>ESN 00805A35<br/>WireOS Dev 3.0.1.32d<br/>192.168.178.67"]

        pi["Raspberry Pi 4B 'vector-pod'<br/>Debian 13 arm64, Python 3.13<br/>192.168.178.66<br/>runs wire-pod (always-on)"]

        dev["Dev machine (Mac)<br/>Python SDK + this repo<br/>iterate here"]

        pizero["Pi Zero 2 W + Display HAT Mini<br/>(future display project, P3-02)<br/>NOT yet deployed"]
    end

    router -.->|DHCP lease| vector
    router -.->|reservation .66| pi
    router -.->|DHCP| dev

    vector <-->|"cloud traffic: TLS 443 to escapepod.local"| pi
    vector <-->|"gRPC 443 (camera, motors, events)"| dev
    dev -.->|"deploy long-running code"| pi
    pi -.->|"gRPC 443 when SDK runs on the Pi"| vector

    classDef future stroke-dasharray: 5 5,fill:#f5f5f5;
    class pizero future;
```

- `escapepod.local` resolves to the Pi: wire-pod advertises that name via its
  own mDNS, in addition to the Pi's real hostname `vector-pod.local`.
- The control path (gRPC) and the voice path (TLS to `escapepod.local`) both
  use port 443 on the robot/Pi but are independent: the SDK can run from the dev
  machine or the Pi, and proving it runs on the Pi was P3-01.
- The Pi Zero 2 W is reserved hardware, not wired in yet.

## View B: wire-pod internals

wire-pod is one Go service (the `chipper` binary) plus a Vosk model and a web
UI. We run it from a git checkout under systemd in **escape-pod mode**
(`apiConfig.json: epconfig=true`), which is what makes it serve and advertise
`escapepod.local:443` -- the name the robot authenticates against.

```mermaid
graph TB
    subgraph pod["wire-pod service (systemd, on the Pi)"]
        chipper["chipper binary<br/>build tag: nolibopusfile<br/>(non-BLE)"]

        subgraph listeners["Listeners"]
            p443["TLS :443<br/>cloud API (escapepod.local)"]
            p8084[":8084 token/jdocs"]
            p8080["web UI :8080"]
        end

        vosk["Vosk en-US<br/>offline STT"]
        intents["intent + knowledge handlers<br/>weather, time, etc."]
        jdocs["jdocs store<br/>per-robot settings + token<br/>(jdocs.json, botSdkInfo.json)"]
        certs["escape-pod certs<br/>epod/ep.crt, server_config.json<br/>CN=escapepod.local"]
        mdns["mDNS responder<br/>advertises escapepod.local"]
        webroot["bundled web setup app<br/>chipper/webroot/<br/>(js/ble.js: BLE onboarding)"]
    end

    p443 --> chipper
    p8084 --> chipper
    p8080 --> chipper
    chipper --> vosk
    chipper --> intents
    chipper --> jdocs
    chipper --> certs
    chipper --> mdns
    p8080 --> webroot
```

- **Non-BLE binary.** We compile `chipper` with only the `nolibopusfile` tag.
  An in-built-BLE build exists (`inbuiltble` tag, P2-07) but wedged the Pi 4's
  Bluetooth, so it was reverted (P2-08). BLE onboarding now runs from the
  browser-based web setup app instead.
- **escape-pod certs.** The robot expects a server presenting a
  `CN=escapepod.local` certificate on 443; `server_config.json` points the
  robot's jdocs/tms/chipper/check endpoints there.
- **jdocs** holds the robot's token and settings server-side. Clearing it
  (P2-08) is how we reset for a fresh onboard.
- **Bundled web setup app** is wire-pod's own copy of the open-source "Vector
  Web Setup" page (the same app hosted by keriganc/froggitti/techshop82, just
  pointed at different OTA backends -- see P4-02). It is served on :8080.

## View C: data flow (voice and control)

Two independent request paths reach the robot. The voice path is wire-pod
answering "Hey Vector" queries; the control path is our Python code driving the
robot over gRPC. They share port 443 on the robot but never touch each other.

```mermaid
sequenceDiagram
    participant U as User (voice)
    participant V as Vector
    participant P as wire-pod (escapepod.local:443)
    participant S as Vosk STT
    participant I as intent handler
    participant C as Your Python code (SDK)

    Note over U,P: Voice path -- self-hosted, no external cloud
    U->>V: "Hey Vector, what time is it?"
    V->>P: TLS 443 -- streamed audio
    P->>S: decode audio
    S-->>P: transcript text
    P->>I: match intent (time/weather/...)
    I-->>P: response payload
    P-->>V: intent + response
    V->>U: speaks the answer (TTS)

    Note over C,V: Control path -- independent of voice
    C->>C: load creds from ~/.anki_vector/
    C->>V: gRPC 443 -- connect + auth (cert + GUID)
    V-->>C: behavior-control grant
    C->>V: say_text / get_battery_state / drive / ...
    V-->>C: events, camera frames, telemetry
```

- **Voice is fully local.** Audio goes to the Pi, Vosk transcribes it, an intent
  handler answers. Proven self-hosted three ways (tcpdump, stop-the-pod, and
  `server_config`) in `setup-vector.md` -- 0 packets to the old pvic.xyz cloud.
- **Control auth.** The SDK reads per-robot creds from `~/.anki_vector/`
  (written by `anki_vector.configure`), opens a gRPC channel to the robot on
  443, and requests behavior control. That first control grant can flake with a
  `_request_control` timeout; a retry succeeds (parking-lot note from P2-03).
- **Where the SDK code sits.** `prototypes/<name>/main.py` calls
  `vectorkit.robot_session()` (`libs/vectorkit/connection.py`), a thin wrapper
  over the vendored `anki_vector` SDK that handles config loading and
  connect/disconnect.

## Where code runs

- wire-pod: always on the Pi, under systemd.
- Python prototypes: anywhere on the LAN. Iterate on the dev machine; deploy
  long-running ones to the Pi (the SDK is proven to run there, P3-01).

## Credentials

The SDK stores per-robot certs and a token under `~/.anki_vector/` (written
during SDK auth). These are secret and machine-local: gitignored, never
committed. To run a prototype on a new machine, re-run `anki_vector.configure`
there. wire-pod's own escape-pod certs and the robot's token live on the Pi
(jdocs), separate from these.

## Conventions

- Shared connection/config helpers live in `libs/vectorkit/` and are imported by
  prototypes, so robot serial/IP handling exists in one place.
- Each prototype is self-contained under `prototypes/<name>/` with its own
  README and entry point.
