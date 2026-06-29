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

### P1-03  Pin the Pi's IP  [x]
Goal: stop the Pi's address from moving so wire-pod/SDK config stay valid.
Steps: add a DHCP reservation on the FRITZ!Box for wlan0 MAC
`e4:5f:01:8f:ab:db`.
Done when: the Pi keeps the same IP across reboots and lease renewals.
Outcome 2026-06-27: marked done by owner -- DHCP reservation set on the FRITZ!Box
so the Pi holds `192.168.178.66` (the address wire-pod/SDK config assume).

---

## Phase 2: Robot onboarding  (done)

### P2-00  Get Vector onto Wi-Fi  [x]
Goal: connect the bot to the LAN so it has an IP (prerequisite for every
wire-pod step). On 2026-06-24 the care screen showed SSID blank / no IP.
Steps: use the BLE setup flow (`https://wpsetup.keriganc.com` from a
Bluetooth-capable Chromium browser) to join the bot to Wi-Fi.
Outcome: joined the FRITZ!Box; bot got `192.168.178.67` on 2026-06-24.

### P2-00b  Obtain the OSKR SSH key  [x]  (resolved via P2-06, not recovered)
Goal: get the dev-unlock SSH key for this bot.
Status: original DDL-era key LOST/unrecoverable, but the GOAL (root SSH for the
wire-pod setup) is met -- P2-06 flashing unlock-prod + WireOS makes the bot
accept froggitti's fresh `ssh_root_key`. History of the dead recovery routes:
An OSKR bot's `/data/ssh/authorized_keys`
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
PROVEN self-hosted (not pvic), 2026-06-25, three ways:
1. tcpdump during a voice command: 200 packets bot->Pi (192.168.178.66:443), 0
   to pvic.xyz (38.191.23.141).
2. Dependency test: stop wire-pod -> Vector shows the no-cloud-connectivity icon
   and cannot answer; restart -> works again. (A pvic bot would still answer.)
3. server_config /data/data override points all endpoints at escapepod.local.
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

### P2-03  Authenticate the Python SDK  [x]
Goal: write robot creds to `~/.anki_vector/` so code can connect over gRPC.
Files: `docs/setup-vector.md` (step 4), `prototypes/hello-vector/`.
Steps: `pip install -e libs/vendor/wirepod-vector-python-sdk` then
`python -m anki_vector.configure`.
Done when: `python prototypes/hello-vector/main.py` connects, prints battery,
and Vector speaks.
OUTCOME 2026-06-26: DONE. Installed the SDK into `.venv` and ran
`anki_vector.configure` (serial 00805A35, name Vector-Z3Y1, ip 192.168.178.67,
wire-pod 192.168.178.66:8080); cert + GUID written to `~/.anki_vector/`.
hello-vector connects over gRPC, prints battery (~3.99V level 2), and Vector
spoke "Hello. The pipeline works." Notes for next time:
- The configure script's Anki-cloud login is stubbed out (hardcoded token) since
  wire-pod is escape-pod; it only asks "proceed?" + the wire-pod web IP:port.
- First connect can time out on the behavior-control grant
  (`_request_control` -> asyncio TimeoutError) even though auth/gRPC are fine; a
  retry succeeds. Connecting with `behavior_control_level=None` reads battery
  without needing control, useful to isolate auth from the control grant.
- Vector must be awake/on the charger; the bot does not answer ICMP ping but 443
  is reachable.

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

---

## Phase 3: Prototypes & solutions  (next)

Direction (owner, 2026-06-26): work the order below, foundation first.
1. FOUNDATION -- a full, reliably working setup for both wire-pod and Vector
   that survives reboots. The onboarding arc (Phase 2) is done and voice + SDK
   work; the remaining hardening (P1-03 pin the Pi IP, P3-01 SDK runs from the
   Pi) is now DONE. This prerequisite gate is met -- the rest of Phase 3 is clear
   to start.
2. UNDERSTAND -- lay out the architecture and how it all actually works end to
   end before building on it (P4-03 diagrams, and P5 for the firmware/OTA side).
3. BUILD -- then the feature/exploration work: LLM gateway (P3-03), refactor /
   modernize the codebase (P3-04), and the self-hosted firmware pipeline (P5).

### P3-01  Verify the SDK fork builds on the Pi  [x]
Goal: confirm the vendored SDK's proto/build works on arm64 + the Pi's Python.
Why: it is an abandoned fork; we own it and need to know it runs before
building on it. Files: `libs/vendor/wirepod-vector-python-sdk`.
Done when: the SDK imports and `hello-vector` runs from the Pi.
OUTCOME 2026-06-27: DONE. Cloned the repo (`--recurse-submodules`; the SDK is a
git submodule -> `Simon-Kaz/wirepod-vector-python-sdk`) to `~/VectorKit` on the
Pi, made a `.venv`, and `pip install -e`'d the SDK. Everything resolved to
prebuilt arm64 manylinux wheels -- NO source compilation (good, since the Pi has
no python dev headers / pip). Verified, all on the Pi:
- `import anki_vector` (0.8.1) + every `messaging/*_pb2`/`_pb2_grpc` + the
  `vectorkit` wrapper import cleanly.
- `hello-vector` connects over gRPC, prints battery (4.1V level 2), Vector
  speaks; exit 0. Control was granted on first try (no `_request_control`
  timeout this run).
Key finding for P3-04: the SDK declares Python 3.7-3.11 but runs FINE on the
Pi's Python 3.13.5 with all-modern deps -- aiogrpc 1.8, grpcio 1.81.1,
protobuf 7.35.1, numpy 2.5.0, Pillow 12.2.0, cryptography 49.0.0. So the old
version ceiling is stale, not a real constraint.
Pi env: Debian 13 (trixie), aarch64, Python 3.13.5; system pip is absent /
PEP-668 externally-managed, so the `.venv` is required. SDK creds
(`~/.anki_vector/`) were already present on the Pi from earlier work.

### P3-02  Pick the second-Pi display project  [ ]
Goal: decide what the Pi Zero 2 W + Pimoroni Display HAT Mini should do
(status dashboard, robot face, etc.). Output: a new prototype dir + tasks.

### P3-03  LLM gateway: pluggable model backend  [ ]
Goal: let Vector use any LLM -- local or cloud, any provider -- behind a single
interface, instead of being tied to one vendor. wire-pod already has some
"knowledge graph"/LLM hooks; decide whether to extend those or sit a gateway in
front of them.
Open questions to resolve first (spike, not commit):
- Integration point: intercept at wire-pod (intent/knowledge-graph handler) vs.
  drive responses from our own SDK code over gRPC. Which gives cleaner control
  of TTS + behaviors?
- Abstraction: adopt an existing gateway/proxy (e.g. an OpenAI-compatible
  shim so any backend speaks one API) vs. a thin in-repo provider interface.
  Prefer not to reinvent if a maintained option fits.
- Backends to support day one: at least one local (e.g. Ollama) and one cloud;
  config-switchable, no code change to swap.
Depends on: P3-01 (SDK proven) and P4-03 (know where the seams are).
Done when: a design note picks the integration point + abstraction, and a
prototype answers a Vector voice prompt through at least one local and one cloud
model, switchable by config.

### P3-04  Refactor / modernize the codebase  [ ]
Goal: assess what in the vendored SDK fork (and our own code) is outdated or
worth replacing, and do it deliberately rather than ad hoc. The SDK is an
abandoned fork we now own.
Scope to define after P3-01/P4-03: e.g. Python version + async stack currency,
dependency pinning, dead Anki-cloud code paths (login is already stubbed -- see
P2-03), proto regeneration, packaging.
Done when: a short assessment lists what to keep / replace / drop with reasons,
and the agreed quick wins are applied with CI green.

(Add prototype ideas here as they come up.)

---

## Phase 4: Documentation & tooling  (backlog)

Captured from the long, painful P2 onboarding. Goal: never repeat the manual
trial-and-error, and finally understand the system.

### P4-01  Interactive Vector onboarding guide  [ ]
Goal: a step-by-step, interactive helper that walks a user through onboarding a
Vector onto our wire-pod, one stage at a time, instead of the manual slog we
just did. Proposed flow:
1. wire-pod health: is it up, in escape-pod mode, advertising escapepod.local,
   Vosk loaded? (mirror the verification commands in `docs/setup-vector.md`).
2. Vector health/identity: reachable on LAN, current firmware/OS + whether it
   is retail vs OSKR vs already-CFW (read the care screen / build.prop).
3. Decision: does it need unlocking? If yes -> unlock-prod OTA steps, then
   WireOS Dev flash; if already CFW -> skip to onboarding.
4. Onboard to wire-pod via the web-UI flow; point at escapepod.local.
5. Verify: voice test + the tcpdump / stop-the-pod proofs.
Implementation idea: a Claude Code skill or a guided script. Source material is
`docs/setup-vector.md` (the working path + dead ends are already mapped there).
Done when: a fresh Vector can be onboarded by following the guide alone, with no
manual log-spelunking.

### P4-02  Understand & document the "Vector Web Setup" page  [x]
Goal: demystify the setup sites we bounced between -- wpsetup.keriganc.com,
vector.techshop82.com, websetup.froggitti.net / unlock-prod.froggitti.net.
Facts established 2026-06-25: they are all the SAME open-source "Vector Web
Setup" Chrome/Web-Bluetooth app, hosted by different people, each pointed at
different firmware/OTA backends (keriganc=ep OTAs on :81 + the link wire-pod's
own UI hardcodes; froggitti=Unlock-Prod + CFW stacks; techshop82=WireOS Dev).
wire-pod SHIPS ITS OWN COPY at `chipper/webroot/` (served on :8080); e.g.
`js/ble.js` hardcodes `wpsetup.keriganc.com` (line 1) and an OTA URL (line 234).
Done when: a short doc explains what the page is, the upstream repo, which copy
we control (the bundled one), how to edit + self-host it, and how to point it at
our own OTAs instead of third-party sites.
OUTCOME 2026-06-27: DONE -> `docs/web-setup.md` (+ docs-site nav/card). Verified
against the LIVE `chipper/webroot/` on the Pi. Refinement to the earlier note:
there are TWO things, not one. (1) the standalone Web-Bluetooth app
`digital-dream-labs/vector-web-setup` (MIT, Node) -- keriganc/techshop82/
froggitti are instances of THIS, each on a different OTA backend. (2) wire-pod's
OWN admin UI at `chipper/webroot/` (page title "Wire-Pod"), which is NOT a fork
of #1 -- for BLE onboarding it either uses wire-pod's in-built BLE (P2-07) or
links OUT to the keriganc-hosted #1. Confirmed the only hardcoded third-party
URLs are both in `js/ble.js`: line 1 (`wpsetup.keriganc.com`, the link-out) and
line 234 (`...:81/1.6.0.3331.ota`, flashed when in-built BLE sees a dev bot in
recovery). Doc covers edit/self-host + the `main.js` webroot-vs-binary version
guard. Feeds P5-01. PR #TBD.

### P4-03  Architecture diagrams for the whole project  [x]
Goal: diagrams of how the pieces connect, since the architecture has never been
laid out visually. Suggested views: (a) hardware/network -- Vector, Pi
(wire-pod), router, dev machine, the second Pi Zero; (b) wire-pod internals --
chipper, escape-pod certs/mDNS, Vosk STT, jdocs, the bundled web setup app, BLE;
(c) onboarding/data flow -- how a voice command travels bot -> escapepod.local
:443 -> STT/intent -> response. Put in `docs/architecture.md` (Mermaid).
Done when: `docs/architecture.md` has the diagrams and a fresh reader can follow
how voice and control flow end-to-end.
OUTCOME 2026-06-27: DONE. Rewrote `docs/architecture.md` with all three Mermaid
views -- (A) hardware/network graph (Vector .67, Pi .66, dev machine, future Pi
Zero), (B) wire-pod internals graph (chipper non-BLE binary, 443/8084/8080
listeners, Vosk, intents, jdocs, escape-pod certs, mDNS, bundled webroot), and
(C) a sequence diagram for the voice path and the independent gRPC control path.
All three validated by rendering to SVG with mermaid-cli; `make check` green.
Outcome: PR #10.

### P4-04  Publish a docs website (GitHub Pages)  [~]
Goal: surface the docs (architecture diagrams + guides) as a website at the
front of the repo, instead of only being readable as raw markdown.
Approach: static HTML + CSS in `docs/`, served by GitHub Pages from `main`
`/docs`. `index.html` fetches the existing `docs/*.md` at runtime and renders
them client-side with marked.js + mermaid.js (CDN), so the markdown stays the
single source of truth -- no build step, no duplication. `.nojekyll` disables
Jekyll. Also revamp the README for the current state (drop the stale retail-`ep`
firmware claim; it is WireOS Dev + web-UI onboarding now).
Done when: the site renders Home + all docs with the Mermaid diagrams drawing,
README points at it, and Pages is enabled (Settings -> Pages -> main /docs).
OUTCOME 2026-06-27: site built (`docs/index.html`, `style.css`, `.nojekyll`);
headless-browser smoke test passes (all 3 mermaid diagrams render, tables OK,
cross-doc links rewritten to hash routes, no console errors). README revamped.
Owner still needs to flip on Pages in repo Settings. Outcome: PR #11.

---

## Phase 5: Self-hosted firmware & OTA pipeline  (backlog)

Own the whole flashing flow instead of depending on third-party web setups
(keriganc / froggitti / techshop82) and their OTA hosting. Builds on P4-02,
which already established those are one open-source web app pointed at different
OTA backends, and that wire-pod bundles its own copy at `chipper/webroot/`.
Gate: do this AFTER the foundation + architecture are solid (Phase 3 step 1-2).

### P5-01  Self-host the Vector Web Setup + all OTAs  [ ]
Goal: a setup site and OTA host WE control, serving every image the onboarding
flow needs so no third-party site is required: prod-unlock, dev-unlock, WireOS
(CFW), and the latest official OS as a clean base.
Steps (to refine): mirror the OTAs (record source + checksums + signing type --
prod vs dev/OSKR, the distinction that broke P2-04); host them with HTTP
range/206 support (nginx, not python http.server -- see P2-04 note); take the
bundled `chipper/webroot/` copy and repoint its hardcoded URLs
(`js/ble.js`: wpsetup.keriganc.com line 1, OTA URL line 234) at our host.
Done when: a Vector can be unlocked + flashed end to end from our own site +
OTA host, with zero third-party dependencies, and the OTA set is checksummed.
See `docs/web-setup.md` (from P4-02) for the verified webroot layout, the two
hardcoded URLs, and the edit/self-host notes.

### P5-02  Understand OTA internals + build a custom OTA  [ ]
Goal: learn what actually goes into a Vector OTA and whether building our own is
useful (vs. just hosting existing ones). Reverse the format, then attempt a
minimal custom image.
Approach: dissect an official OTA's structure (the .tar contents the recovery OS
parses -- recall P2-06: old 0.9.0 recovery couldn't parse a 3.0.1 image), the
signing model (dev/OSKR vs prod keys), and the manifest/payload layout.
Worked example: take a base official OS and diff WireOS against it to see what a
real CFW changes -- via froms commit history / build scripts if available, else
by comparing unpacked images. Document the delta as a teaching example.
Done when: a doc explains OTA anatomy + signing, shows the WireOS-vs-stock diff
as a worked example, and states whether a custom OTA is worth building for us
(with a minimal proof-of-concept image if yes).

---

## Parking lot

Unscheduled ideas, decisions to revisit, things noticed mid-task. Promote to a
real task when ready.

- Harden SSH: set `password_authentication = false` once key login is trusted.
- Consider whether to track a `requirements`-pinned SDK build for CI.
- SDK behavior-control grant flakes on first connect (`_request_control` ->
  asyncio TimeoutError) though auth/gRPC are fine; retry works. Watch for this
  in Phase 3 prototypes -- may want a connect-retry/backoff helper. (From P2-03.)
