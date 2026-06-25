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

### P2-02  Authenticate Vector to wire-pod  [x]
Goal: pair the bot to wire-pod so voice works.
Files: `docs/setup-vector.md` (step 3). Web UI: `http://vector-pod.local:8080`.
Done when: web UI shows "Vector setup is complete!" and a voice command
("Hey Vector, what time is it?") returns an answer.
OUTCOME 2026-06-25: DONE via the fresh-start route -- reflashed WireOS Dev
(vector.techshop82.com) and onboarded to our wire-pod through the web-UI
tutorial (youtube MXycWBQtc0A), NO BLE / no manual internals. Confirmed:
- wire-pod logged a clean auth (fresh GUID, token round-trip, "Successfully got
  jdocs from 00805a35"); bot shows in escapepod web UI (sdkapp control works).
- Bot config: WireOS reads `/data/data/server_config.json` (NOT the /anki one),
  which points jdocs/tms/chipper/check all at `escapepod.local:443` = our Pi.
- VERIFIED BY VOICE: "Hey Vector, what time is it?" returns the correct time,
  via both wakeword and backpack-button -- so the voice/chipper path runs
  through our self-hosted wire-pod. Bot renders eyes / reacts normally (the old
  blank-face onboarding hang is gone with the clean web-UI onboard).
Key gotcha: WireOS uses `/data/data/server_config.json` as the active override
(the /anki/.../server_config.json may still say pvic.xyz and is misleading).
Fixed (necessary, not sufficient): "Activate" failed "Error logging in" because
wire-pod was in NON-escape-pod mode (`apiConfig.json: epconfig=false`) so it
never served `escapepod.local:443` nor mDNS-advertised it (the name the bot
authenticates against). Fixed on the Pi via `GET /api-chipper/use_ep`
(epconfig=true, port=443, restart). escapepod.local now resolves to the Pi;
443/8084 listen; `http://escapepod.local:8080` loads from a LAN client. See
P1-02 note + setup-vector.md.
STATUS 2026-06-24: CONNECTED to wire-pod, but bot stuck on onboarding screen
(no eyes / no voice yet). Resolved the pre-WireOS blockers (see P2-06): after
WireOS + `setup.sh scp`, the bot now genuinely talks to wire-pod --
- vic-cloud loaded `/anki/etc/wirepod-cert.crt`, has a valid token ("token
  refresh: waiting for 716h").
- vic-engine JdocsManager round-trips to wire-pod: "Received user response ...
  userID: 'wirepod'" + WriteDoc RobotSettings/AccountSettings/UserEntitlements
  for Robot ID vic:00805a35.
- `escapepod.local/ok` connCheck returns 200; bot TLS handshake to
  escapepod.local:443 gets the CN=escapepod.local cert.
REMAINING BLOCKER (updated 2026-06-25): the onboarding-complete BLE command
itself wedges the WireOS behavior stack. We CAN now send it -- enabled wire-pod
in-built BLE on the Pi (see P2-07) and drove the full flow from the Pi:
scan -> connect (PIN shows on face) -> send_pin -> `onboard?with_anim=true`
(fires onboarding_wake_up_request then onboarding_mark_complete_and_exit). All
steps return success/done. BUT: reproducibly (twice), right after the onboard
command the bot's display goes BLANK (LCD backlight on, nothing drawn) and it
stops responding to button/touch/voice. Services stay `active` (no crash); the
engine soft-hangs -- vic-engine logs `VisionComponent.CaptureImage.
TooLongSinceFrameWasCaptured` (~6min since last frame). A reboot recovers it to
a working pairing screen (server_config persists = escapepod.local), but
onboarding does NOT stick, so we land back here. => this is a WireOS firmware
bug (behavior/vision stack hangs on mark_complete_and_exit), not a wire-pod
issue. The robot<->pod link itself is fully working.
EVERY onboarding-complete path now exhausted (2026-06-25), all converge on the
same WireOS hang or a transport failure:
- direct BLE `onboard?with_anim=true` -> vision/behavior hang (blank face).
- direct BLE `onboard?with_anim=false` -> SAME hang (so the wake animation is
  NOT the cause; mark_complete_and_exit itself wedges it).
- browser BLE (wpsetup.keriganc.com) "Activate" -> page hangs, but token IS
  granted server-side; bot did not exit onboarding.
- wire-pod UI in-built BLE scan/connect -> wedges the Pi's built-in Bluetooth
  driver ("BLE driver has broken... too long to connect"), wire-pod restarts.
NEW this session: the bot-side token pickup was the real gap after a browser
Activate -- vic-cloud logged "no valid token yet, sleeping 5m"; restarting
vic-cloud on the bot made it fetch the token ("token refresh: waiting 716h").
After that the bot boots WITH a valid token, but mark_complete_and_exit STILL
hangs it. So: token/cert/jdocs all good; the hang is purely WireOS's
onboarding-exit on build 3.0.1.32d.
NEXT (needs community/hardware, NOT more local trial-and-error):
1. os-vector / WireOS Discord with the above (blank face +
   VisionComponent.TooLongSinceFrameWasCaptured on mark_complete_and_exit).
2. A USB Bluetooth dongle on the Pi would fix the UI-BLE driver wedge (Pi 4
   built-in BT + wire-pod BLE is a known-flaky combo) -- lets the UI flow run.
3. Consider a different/older WireOS or another CFW if this build's onboarding
   is simply broken for escapepod.

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

### P2-06  Unlock-prod + WireOS via froggitti  [x]  <-- THE WAY FORWARD (taken)
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
OUTCOME 2026-06-24: DONE. Flashed Unlock-Prod.ota then WireOS (3.0.1.32d).
SSH into WireOS works with the standard `ssh_root_key` (froggitti serves it at
unlock-prod.froggitti.net/media/ssh_root_key; same key the prod bot rejected --
WireOS trusts it). Installed escapepod server_config + ep.crt + vic-cloud via
the steps inside wire-pod `setup.sh scp` (run manually: the script's `set -e`
aborts on the build.prop SSH probe; also `touch chipper/useepod` first and add
`PubkeyAcceptedKeyTypes +ssh-rsa` to the Pi's /etc/ssh/ssh_config). Then the
wpsetup BLE "Activate" succeeded: wire-pod logged "Token: Incoming Associate
Primary User request" + jdocs WriteDoc for Robot ID vic:00805a35. Remaining
onboarding-screen issue tracked under P2-02.

### P2-07  Enable wire-pod in-built BLE on the Pi  [x]
Goal: drive Vector's BLE onboarding from the Pi (no flaky browser BLE), to send
onboarding-complete. wire-pod's /api-ble/* routes are behind the `inbuiltble`
Go build tag; our binary lacked it (/api-ble/init -> 404).
What was tried/learned:
- Setting `USE_INBUILT_BLE=true` in source.sh did nothing: start.sh only
  recompiles when there is NO prebuilt `./chipper`; ours was prebuilt (no tag).
- Removing ./chipper to force `go run` FAILS under systemd: "module cache not
  found" (no GOPATH/HOME in the service env). Don't do this -- it crash-loops.
- The official v1.2.18 arm64 .deb binary HAS inbuiltble, but is hardcoded to
  `/etc/wire-pod` paths and won't run from our git-clone layout ("FATAL: no
  /etc/wire-pod folder").
- WORKING FIX: build in our layout as root with setup.sh's recipe --
  `GOTAGS=nolibopusfile,inbuiltble`, vosk CGO env (CGO_CFLAGS=-I/root/.vosk/
  libvosk, CGO_LDFLAGS="-L /root/.vosk/libvosk -lvosk -ldl -lpthread",
  LD_LIBRARY_PATH=/root/.vosk/libvosk), `go build -o chipper.ble cmd/vosk/
  main.go`. Stop service, `cp chipper.ble chipper`, start. /api-ble/init now
  returns "success". Backup of the non-BLE binary: chipper.noble.bak.
Outcome: Pi can pair/connect/send_pin/onboard over its own Bluetooth (hci0).
NOTE: REVERTED in P2-08 -- the in-built-BLE binary is removed for the
fresh-start (web-UI) approach. Build recipe above is kept for reference only.

### P2-08  Rebuild wire-pod clean (no BLE) for web-UI onboarding  [x]
Goal: undo the manual BLE/internals hacks so the web-UI tutorial flow works on
a clean wire-pod. Done 2026-06-25:
- Swapped chipper back to the non-BLE binary (`chipper.noble.bak` -> `chipper`,
  tag `nolibopusfile` only); removed `chipper.ble`. /api-ble/init now 404s.
- Removed `USE_INBUILT_BLE=true` from chipper/source.sh.
- Cleared stale bot data: jdocs/jdocs.json -> `[]`, jdocs/botSdkInfo.json ->
  `{"global_guid":"","robots":[]}` (old vic:00805a35 token/GUID gone; backups in
  /tmp/*.bak). Fresh for re-onboard.
- KEPT (correct, not hacks): escape-pod mode (epconfig=true, port 443),
  chipper/useepod marker, epod/ep.crt, certs/server_config.json (escapepod.local
  :443). Vosk en-US model loaded (self-test passes).
Verified: web up; 443/8084 serving; escapepod.local resolves to the Pi
(192.168.178.66); BLE route gone; no stale bot.

### Pi state (current, as of 2026-06-25 -- clean)
KEEP: wire-pod in escape-pod mode, NON-BLE binary, advertising escapepod.local;
Vosk en-US loaded; `chipper.noble.bak` retained as the live binary's source.
SSH-to-bot tooling kept in case needed: `/home/vector/wire-pod/frog_key`
(== ssh_root_key) and `PubkeyAcceptedKeyTypes +ssh-rsa` in /etc/ssh/ssh_config.
Pi hostname stays `vector-pod` (both vector-pod.local and escapepod.local
resolve). Pi Bluetooth unused now.
TORN DOWN earlier: temp OTA servers + ~340MB cached .ota images.

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
