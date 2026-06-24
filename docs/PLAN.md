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
the CURRENT name (Z3Y1) would work. None found.
=> The original DDL-era SSH key is dead. REVIVED by P2-06: after flashing
unlock-prod + WireOS, froggitti's tool issues a fresh SSH root key the (now-dev)
bot accepts. That is the working way to get root SSH for the wire-pod setup.

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
Root cause of remaining failure: tcpdump during Activate shows the bot sends
ZERO TCP to the Pi's 443/8084 and never queries escapepod.local -- it is not
pointed at our pod at all. A bot only talks to escapepod.local after its
server_config + cert are installed. The wpsetup "Activate" flow can't do that
for our dev/OSKR bot (it expects a retail/ep bot). So P2-02 is blocked on
getting onto wire-pod-capable firmware with root access -- which is P2-06
(unlock-prod + WireOS + fresh SSH key + wire-pod `setup.sh scp`).

### P2-04  Flash ep firmware via local OTA  [x] (DEAD END -- superseded by P2-06)
Attempted: get the bot onto retail `ep` firmware so it points at escapepod.local
without an SSH key, by hosting the .ota on the Pi and running `ota-start <url>`
in wpsetup's advanced terminal (bot in recovery mode). Did NOT work; kept here
as a record of what to skip.
Why it failed: with wifi connected in the terminal, `ota-start` returns
`status:214` (Dev/Prod mismatch). Our bot has OSKR/DEV signing keys and refuses
ALL prod-signed images. Every published `ep` build is prod-signed
(wpsetup.keriganc.com:81 and anki2.ca/ep: 1.4.1, 1.6.0, 1.7.3, 1.8.1,
2.0.1.6076..6091). No dev-signed `ep` exists. So the ep path is unusable for a
dev/OSKR bot -- it is the wrong family of firmware.
Diagnostic notes worth keeping: OTA error codes (203 URL not found, 209
signature, 211 wrong base, 214 dev/prod, 215 network stall, 216 downgrade); the
bot downloads the OTA itself over wifi and the wpsetup GUI hides failures (empty
`else` in onOtaProgress) -- read the real code via terminal `ota-progress`;
serve OTAs with a server that supports HTTP range/206 (nginx, not python
http.server) or the bot resets the connection.

### P2-06  Unlock-prod + WireOS via froggitti  [~]  <-- THE WAY FORWARD (taken)
This is the path that actually works for a dev/OSKR bot whose SSH key is lost.
Both other routes are dead: SSH-cert (P2-00b, key gone) and ep-flash (P2-04,
214). The breakthrough: a dev image flashed via `ota-start` fails `status:200`
(Unexpected .tar contents) because our recovery OS is the old `0.9.0`, which
can't parse a modern (3.0.1) image -- confirmed by trying WireOS dev.ota
(3.0.1.32d, ankidev=1; cleared 214, then hit 200). The os-vector docs
(os-vector.github.io/vector-docs) route dev/OSKR installs over SSH for exactly
this reason; only "Unlocked Prod" uses BLE ota-start.
Fix: froggitti's `Unlock-Prod.ota` -- a recovery-parseable image that re-enables
dev firmware on the bot. This one flashes and progresses (the first OTA that got
past 0%).
Steps (started 2026-06-24, chosen and in progress):
1. https://unlock-prod.froggitti.net -> Utility stack -> `Unlock-Prod.ota`.
   ~7 min, keep Vector on the charger, do not interrupt (rewrites recovery).
2. After reboot, flash WireOS via https://websetup.froggitti.net -> Custom
   Firmware stack (chosen target). Fallback if the GUI is flaky: re-run
   `ota-start http://192.168.178.66:8086/dev.ota` from the Pi -- with the unlock
   applied it should now install past the old 214/200.
3. Connect to wire-pod: download froggitti's SSH root key (the now-dev bot
   accepts it) and run wire-pod `setup.sh scp <bot-ip> <key>` on the Pi to write
   the escapepod cert + server_config. wire-pod is already in escape-pod mode
   and advertising escapepod.local (see P2-02 / P1-02).
Done when: bot runs WireOS and authenticates to wire-pod (rolls into P2-02).

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
