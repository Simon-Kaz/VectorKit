# VectorKit project plan

The task backlog for this repo. Pick a task by ID in any conversation; each
entry is self-contained enough to start from cold. Run `/task <id>` (see
`.claude/commands/task.md`) or just say "do P2-01".

## How to use this file

- Tasks have a stable ID (`P<phase>-<n>`). IDs never change or get reused.
- Status is one of: `todo`, `in-progress`, `blocked`, `done`.
- When you finish a task, set it to `done` and add a one-line outcome.
- Add new tasks at the end of the relevant phase; never renumber existing ones.
- Keep entries short. Link to the doc that holds the real detail rather than
  duplicating it here.

Status legend: [ ] todo  [~] in-progress  [b] blocked  [x] done

---

## Phase 0: Foundation  (done)

### P0-01  Scaffold the repo  [x]
Monorepo layout, README, license, Python package skeleton. Outcome: PR #1.

### P0-02  Local validation  [x]
pre-commit + pre-push hooks, Makefile, unified CI. Outcome: PR #2.
Detail: `docs/development.md`.

---

## Phase 1: Self-hosted server  (done)

### P1-01  Provision the Pi host  [x]
Headless Pi 4B on Wi-Fi, reachable over SSH as `vector@vector-pod.local`.
Detail: `infra/raspberry-pi/README.md`. Outcome: PR #4.

### P1-02  Install wire-pod  [x]
wire-pod running as a systemd service, Vosk en-US STT, web UI on :8080.
Detail: `infra/wire-pod/README.md`. Outcome: PR #4.

### P1-03  Pin the Pi's IP  [ ]
Goal: stop the Pi's address from moving so wire-pod/SDK config stay valid.
Steps: add a DHCP reservation on the FRITZ!Box for wlan0 MAC
`e4:5f:01:8f:ab:db`.
Done when: the Pi keeps the same IP across reboots and lease renewals.

---

## Phase 2: Robot onboarding  (next)

### P2-00  Get Vector onto Wi-Fi  [ ]
Goal: connect the bot to the LAN so it has an IP (prerequisite for every
wire-pod step). On 2026-06-24 the care screen showed SSID blank / no IP.
Steps: use the BLE setup flow (`https://wpsetup.keriganc.com` from a
Bluetooth-capable Chromium browser) to join the bot to Wi-Fi.
Done when: Vector's care screen shows the SSID and a real IP on the LAN.

### P2-00b  Obtain the OSKR SSH key  [ ]
Goal: get the dev-unlock SSH key for this bot; wire-pod's OSKR "Set up bot"
step requires uploading it and we do not have it. The key came from whoever
OSKR-unlocked the bot. Store it outside the repo (see `.gitignore`).
Done when: the bot's SSH key file is on the machine running setup, not
committed.

### P2-01  Confirm OSKR/dev firmware  [b]
Goal: confirm this bot is ready for wire-pod authentication. Our Vector is
OSKR/dev-unlocked (boots to the OSKR logo), so the retail `ep`-firmware
recovery flash does NOT apply -- OSKR bots are unlocked via an SSH key instead
(wire-pod's "Configure an OSKR/dev-unlocked robot" path).
Files: `docs/setup-vector.md` (step 2). Needs: physical robot + charger.
Done when: bot confirmed OSKR/dev-unlocked and firmware version >= 1.4 (the
floor wire-pod's OSKR path requires).
BLOCKED on P2-00 (bot not on Wi-Fi: SSID blank, no IP) and P2-00b (no OSKR SSH
key on hand). Care-screen readout 2026-06-24: ESN `00805A35`, OS `0.9.0 (V4)`,
BLE ID `Vector Z3Y1`. The `0.9.0 (V4)` string is below the UI's stated "1.4 and
above" -- meaning of the OSKR version scheme is unconfirmed; recheck firmware
once the bot is online.

### P2-02  Authenticate Vector to wire-pod  [ ]
Goal: pair the bot to wire-pod so voice works.
Files: `docs/setup-vector.md` (step 3). Web UI: `http://vector-pod.local:8080`.
Done when: web UI shows "Vector setup is complete!" and a voice command
("Hey Vector, what time is it?") returns an answer.

### P2-03  Authenticate the Python SDK  [ ]
Goal: write robot creds to `~/.anki_vector/` so code can connect over gRPC.
Files: `docs/setup-vector.md` (step 4), `prototypes/hello-vector/`.
Steps: `pip install -e libs/vendor/wirepod-vector-python-sdk` then
`python -m anki_vector.configure`.
Done when: `python prototypes/hello-vector/main.py` connects, prints battery,
and Vector speaks.

---

## Phase 3: Prototypes & solutions  (backlog)

### P3-01  Verify the SDK fork builds on the Pi  [ ]
Goal: confirm the vendored SDK's proto/build works on arm64 + the Pi's Python.
Why: it is an abandoned fork; we own it and need to know it runs before
building on it. Files: `libs/vendor/wirepod-vector-python-sdk`.
Done when: the SDK imports and `hello-vector` runs from the Pi.

### P3-02  Pick the second-Pi display project  [ ]
Goal: decide what the Pi Zero 2 W + Pimoroni Display HAT Mini should do
(status dashboard, robot face, etc.). Output: a new prototype dir + tasks.

(Add prototype ideas here as they come up.)

---

## Parking lot

Unscheduled ideas, decisions to revisit, things noticed mid-task. Promote to a
real task when ready.

- Harden SSH: set `password_authentication = false` once key login is trusted.
- Consider whether to track a `requirements`-pinned SDK build for CI.
