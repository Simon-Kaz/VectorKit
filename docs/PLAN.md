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
Fix 2026-06-24: it was installed in NON-escape-pod mode (`epconfig=false`), so
it served nothing on 443 and never advertised `escapepod.local` -- breaking bot
auth. Switched to escape-pod mode via `GET /api-chipper/use_ep`. Production/OSKR
Vectors REQUIRE escape-pod mode; pick "escapepod.local" certs in `setup.sh`.

### P1-03  Pin the Pi's IP  [ ]
Goal: stop the Pi's address from moving so wire-pod/SDK config stay valid.
Steps: add a DHCP reservation on the FRITZ!Box for wlan0 MAC
`e4:5f:01:8f:ab:db`.
Done when: the Pi keeps the same IP across reboots and lease renewals.

---

## Phase 2: Robot onboarding  (next)

### P2-00  Get Vector onto Wi-Fi  [x]
Goal: connect the bot to the LAN so it has an IP (prerequisite for every
wire-pod step). On 2026-06-24 the care screen showed SSID blank / no IP.
Steps: use the BLE setup flow (`https://wpsetup.keriganc.com` from a
Bluetooth-capable Chromium browser) to join the bot to Wi-Fi.
Outcome: joined the FRITZ!Box; bot got `192.168.178.67` on 2026-06-24.

### P2-00b  Obtain the OSKR SSH key  [b]
Goal: get the dev-unlock SSH key for this bot.
Status: LOST, likely unrecoverable. An OSKR bot's `/data/ssh/authorized_keys`
holds two keys: a per-bot `id_rsa_Vector-Z3Y1` (generated on the bot, was
downloaded from the dead DDL portal) and DDL's shared static dev key
(`digital_dream_labs_dev_key`, == wire-pod's `ssh_root_key`). Tested both:
- Shared key recovered from Wayback (`http://wire.my.to:81/ssh_root_key`, 502
  live but archived; fp SHA256:9lZMgxdfKD9Avvu59aNUDaCUOQMltOfkJKvJ5BX6HFI) ->
  bot rejects it (`Permission denied (publickey)`), so it is not in
  authorized_keys (removed or wiped by a Clear User Data).
- Per-bot `id_rsa_Vector-Z3Y1`: not found on owner's machine.
Clear User Data regenerates the key AND renames the bot, so only a key matching
the CURRENT name (Z3Y1) would work. None found. => SSH-cert onboarding path is
dead; must use the ep-OTA path (P2-04) instead, which needs no SSH key.

### P2-01  Confirm OSKR/dev firmware  [x]
Goal: confirm this bot is ready for wire-pod authentication. Our Vector is
OSKR/dev-unlocked, so the retail `ep`-firmware recovery flash does NOT apply.
Outcome: firmware is `1.7.1.6003oskr` (read in wpsetup after pairing), well
above the 1.4 floor. The earlier care-screen `0.9.0 (V4)` was a recovery/boot
string, not the OS version. ESN `00805A35`, BLE ID `Vector Z3Y1`.

### P2-02  Authenticate Vector to wire-pod  [b]
Goal: pair the bot to wire-pod so voice works.
Files: `docs/setup-vector.md` (step 3). Web UI: `http://vector-pod.local:8080`.
Done when: web UI shows "Vector setup is complete!" and a voice command
("Hey Vector, what time is it?") returns an answer.
Fixed (necessary, not sufficient): "Activate" failed "Error logging in" because
wire-pod was in NON-escape-pod mode (`apiConfig.json: epconfig=false`) so it
never served `escapepod.local:443` nor mDNS-advertised it (the name the bot
authenticates against). Fixed on the Pi via `GET /api-chipper/use_ep`
(epconfig=true, port=443, restart). escapepod.local now resolves to the Pi;
443/8084 listen; `http://escapepod.local:8080` loads from a LAN client. See
P1-02 note + setup-vector.md.
BLOCKED still: Activate continues to fail. tcpdump during Activate shows the bot
sends ZERO TCP to the Pi's 443/8084 and never queries escapepod.local -- it is
not pointed at our pod at all. An OSKR bot only talks to escapepod.local after
its server_config + cert are installed, via either the SSH path (P2-00b, dead)
or ep firmware (P2-04). So P2-02 is blocked on P2-04.

### P2-04  Flash ep firmware via local OTA (unblocks P2-02)  [~]
Goal: get the bot onto ep firmware so it points at escapepod.local without an
SSH key. ep is the designed escape hatch when the OSKR key is lost (P2-00b).
Method (from the DDL OSKR owner's manual, github.com/digital-dream-labs/
oskr-owners-manual, doc/unlock.md): host the .ota on the LAN and run
`ota-start <url>` in wpsetup's advanced terminal with the bot in recovery mode.
Local hosting set up on the Pi (2026-06-24, all TEMPORARY -- tear down when
done):
- ep OTA cached at `/var/www/ota/vicos-2.0.1.6076ep.ota` (179763200 bytes, from
  `http://wpsetup.keriganc.com:81/...`).
- nginx serves it on `http://192.168.178.66:8086/vicos-2.0.1.6076ep.ota`
  (HTTP/1.1 + Accept-Ranges + 206; python http.server on :8085 did NOT support
  ranges and the bot reset the connection -- units: ota-serve.service stopped).
- Pass to wpsetup as `?ota=<url>`:
  `https://wpsetup.keriganc.com/html/main.html?ota=http://192.168.178.66:8086/vicos-2.0.1.6076ep.ota`
Symptom: bot connects and GETs the file (User-Agent `Victor/0.9.0`, recovery
reports victorversion=0.9.0) but aborts after ~0.4-0.5 MB of 180 MB, at varying
offsets. NEXT STEP: read the real OTA error code via wpsetup terminal
`ota-start <url>` then `ota-progress` (codes: 203 not found, 209 signature, 211
wrong base version, 214 dev/prod mismatch, 215 network stall, 216 downgrade
blocked). Manual warns the 0.9.0 recovery sw "does not support updating the
appropriate partitions" for the unlock image -- but a normal OSKR/prod OTA is a
safe test. May need CLEAR USER DATA first (codes 211/216).
Done when: firmware string ends in `ep` and the bot reboots into it.

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
