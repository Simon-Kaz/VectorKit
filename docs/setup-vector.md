# Setting up Vector with wire-pod

How our Vector got onto our self-hosted wire-pod, the current confirmed
state, how to verify it, and the dead ends we hit so we never repeat them.

> TL;DR for our bot: it is an OSKR (dev-unlocked) Vector whose original DDL
> SSH key is lost. The ONLY path that worked was: reflash community firmware
> (WireOS Dev) and onboard via the web-UI tutorial against a clean escape-pod
> wire-pod. The manual SSH / BLE / ep-firmware paths all failed -- see
> "History and dead ends" below before trying any of them again.

---

## Current setup (CONFIRMED WORKING 2026-06-25)

Robot:
- Model: OSKR / dev-unlocked Vector. ESN `00805A35`, name `Vector-Z3Y1`.
- Firmware: **WireOS Dev `3.0.1.32d`** (community CFW by kercre123, based on the
  leaked 2.0.1.6076 source). Flashed from <https://vector.techshop82.com>.
- LAN IP: `192.168.178.67` (DHCP; can change -- see Troubleshooting).
- Active server config: WireOS reads **`/data/data/server_config.json`**, which
  points jdocs/tms/chipper/check all at `escapepod.local:443` -> our Pi.
  (NOTE: the other file, `/anki/data/assets/cozmo_resources/config/
  server_config.json`, may still say `vicapi.pvic.xyz` and is MISLEADING --
  it is not the one WireOS uses.)

Server (the Pi):
- Host `vector-pod` (`vector@vector-pod.local`, `192.168.178.66`). See
  `infra/raspberry-pi/`.
- wire-pod: systemd service, **escape-pod mode** (`apiConfig.json:
  epconfig=true`, port 443), serving 443 + 8084, advertising `escapepod.local`
  via its own mDNS. Vosk en-US STT loaded. **Non-BLE binary** (we removed the
  in-built-BLE build -- see history). Web UI: `http://vector-pod.local:8080`
  (also reachable as `http://escapepod.local:8080`).
- Hostname stays `vector-pod`; wire-pod self-advertises `escapepod.local`, so
  both names resolve. We did NOT rename the Pi.

How they connect: Vector sends all cloud traffic (auth/jdocs/voice) to
`escapepod.local:443` = the Pi. wire-pod handles STT (Vosk) and intents. There
is NO dependency on any hosted/public cloud (verified below).

---

## The path that worked (do THIS for a lost-key OSKR bot)

Prerequisite: wire-pod already running on the Pi in escape-pod mode, advertising
`escapepod.local`. To put/keep it there: `curl http://localhost:8080/
api-chipper/use_ep` on the Pi (sets epconfig=true, port=443, restarts chipper),
or re-run `setup.sh` and choose the `escapepod.local` certs. Verify with
`getent hosts escapepod.local` (returns the Pi IP) and that 443/8084 listen.

1. **Reflash WireOS Dev.** In Chrome, go to <https://vector.techshop82.com>
   (a WireOS web flasher). Put Vector in recovery mode (hold backpack ~15s on
   the charger) and flash WireOS Dev. Keep him on the charger throughout.
2. **Onboard to wire-pod via the web UI.** Follow the WireOS onboarding tutorial
   (<https://www.youtube.com/watch?v=MXycWBQtc0A>). When it asks for the server,
   use **`escapepod.local`** (or the Pi IP `192.168.178.66`). This writes
   `/data/data/server_config.json` -> escapepod and completes onboarding WITHOUT
   the blank-face hang we hit on the manual path.
3. **Done** when Vector shows eyes and a voice command returns an answer
   (see Verification).

Why this works when the manual path did not: the techshop82 flasher + web-UI
onboarding handle the firmware AND the onboarding-complete step in one
firmware-aware flow. Our manual approach got the bot connected but could never
clear onboarding (the `onboarding_mark_complete_and_exit` BLE command reliably
hung WireOS 3.0.1.32d's vision/behavior stack).

---

## Verification (how we proved it is OUR wire-pod, not a hosted one)

Voice working is necessary but not sufficient proof -- a bot pointed at the
public `vicapi.pvic.xyz` cloud would also answer. We confirmed self-hosting
three independent ways (2026-06-25):

1. **Voice end-to-end.** "Hey Vector, what time is it?" returns the correct time
   (via wakeword and via backpack-button). Voice intents resolve through the
   `chipper` endpoint, which is escapepod.local.

2. **Packet capture (positive proof).** On the Pi, capture the bot's outbound
   connections while asking the time. Pi = `192.168.178.66`, pvic =
   `38.191.23.141`:
   ```bash
   sudo tcpdump -ni wlan0 \
     "src host 192.168.178.67 and (dst host 192.168.178.66 or dst host 38.191.23.141)"
   ```
   Result: **200 packets to the Pi (port 443), 0 to pvic.xyz.** All cloud
   traffic goes to our Pi.

3. **Stop-the-pod dependency test (the clincher).** Stop wire-pod, ask the time:
   ```bash
   sudo systemctl stop wire-pod    # on the Pi
   ```
   Result: Vector shows the **no-cloud-connectivity icon** and cannot answer.
   A pvic-connected bot would still answer. Restart to restore:
   ```bash
   sudo systemctl start wire-pod
   ```

Also useful: the bot appears in the escapepod web UI at
`http://escapepod.local:8080/sdkapp/settings.html?serial=00805a35` (SDK
control). NOTE: SDK control works via the stored GUID regardless of
server_config, so the web UI alone does NOT prove the voice path -- use the
tests above.

---

## Authenticate the Python SDK (next: P2-03)

Install the vendored SDK (our fork), then authenticate. Writes per-robot creds
to `~/.anki_vector/` on the machine that runs your code.

```bash
pip install -e libs/vendor/wirepod-vector-python-sdk
python -m anki_vector.configure
```

You will need: robot serial (`00805A35`), robot name (`Vector-Z3Y1`), and the
robot IP (`192.168.178.67`; confirm on the care screen or your router).

Verify:
```bash
cd prototypes/hello-vector
python main.py
```
Vector should say hello and report battery state. If gRPC fails, confirm the IP
in `~/.anki_vector/sdk_config.ini` matches Vector's current IP.

---

## History and dead ends (how we got here -- do NOT repeat)

We spent a long time on paths that DID NOT work for this bot. Recorded so we
skip them next time. Full task-by-task detail is in `docs/PLAN.md`
(P2-01/04/06/07/08).

- **It is an OSKR bot, not retail.** Boots to an OSKR logo; firmware was
  `1.7.1.6003oskr`. The care-screen `0.9.0` we first saw was the recovery OS,
  not the OS version. Retail `ep`-firmware instructions do not apply.
- **ep firmware is a DEAD END on a dev/OSKR bot.** Flashing any prod-signed
  `ep` build via `ota-start` returns OTA `status:214` (Dev/Prod mismatch). All
  published `ep` builds (wpsetup.keriganc.com:81, anki2.ca/ep: 1.4.1..2.0.1.6091)
  are prod-signed. No dev-signed `ep` exists. Do not keep trying `ep` versions.
- **Old `0.9.0` recovery cannot install modern dev images over BLE.** A WireOS
  `dev.ota` (3.0.1) cleared the 214 but then failed `status:200` (Unexpected
  .tar contents) because the recovery OS is too old to parse it. froggitti's
  `Unlock-Prod.ota` (unlock-prod.froggitti.net) was the only OTA that progressed
  past 0% -- it re-enables dev firmware on a parseable image.
- **The lost SSH key:** an OSKR bot trusts a per-bot key (downloaded from the
  dead DDL portal) and DDL's shared static dev key. The per-bot key
  (`id_rsa_Vector-Z3Y1`) is gone; the shared key (recoverable from Wayback /
  unlock-prod.froggitti.net/media/ssh_root_key, fp
  `SHA256:9lZMgxdfKD9...`) was rejected by the prod bot but IS accepted once on
  WireOS.
- **Manual `setup.sh scp` connected the bot but could NOT finish onboarding.**
  We did install the escapepod cert + server_config + vic-cloud by hand (the
  script's `set -e` aborts on its build.prop SSH probe; needed `touch
  chipper/useepod` and `PubkeyAcceptedKeyTypes +ssh-rsa` in the Pi's ssh_config
  first). The bot authed and synced jdocs, but every "complete onboarding" path
  then hung it:
  - direct BLE `onboard?with_anim=true` AND `with_anim=false` -> blank LCD,
    unresponsive, `VisionComponent.TooLongSinceFrameWasCaptured` (no crash).
  - browser BLE (wpsetup.keriganc.com) "Activate" -> page hangs; token granted
    server-side but onboarding never completed.
  - wire-pod in-built BLE (which we compiled with `inbuiltble`) -> wedged the
    Pi 4's built-in Bluetooth ("BLE driver has broken"); wire-pod restarted.
  Conclusion: `onboarding_mark_complete_and_exit` is broken on this WireOS
  build. We abandoned this whole approach for the clean WireOS-Dev + web-UI
  reflash above, which just worked.
- **A subtle gotcha that cost time:** wire-pod grants the token, but the bot
  fetches it on a 5-min timer ("token refresher: no valid token yet, sleeping
  5m0s"). Restarting `vic-cloud` on the bot forces an immediate fetch.

---

## Troubleshooting

- **"Error logging in" at Activate / bot cannot reach wire-pod:** the bot
  authenticates against `escapepod.local:443`, which only works in escape-pod
  mode. Check `apiConfig.json` on the Pi for `"epconfig": false`; if so, run
  `curl http://localhost:8080/api-chipper/use_ep` (or re-run setup.sh, choose
  escapepod.local certs). Then `getent hosts escapepod.local` should return the
  Pi IP and 443/8084 should listen. mDNS broadcasts ~every 60s.
- **Which wire-pod is the bot REALLY using?** Check
  `/data/data/server_config.json` on the bot (the active one), NOT the
  `/anki/.../server_config.json`. Or run the verification tests above.
- **OTA `status:214` (dev/prod) or `status:200` (old recovery):** do not keep
  trying `ep` builds -- use the WireOS-Dev reflash in "The path that worked".
- **wpsetup stuck at 0% / "Error while updating":** the web UI hides the bot's
  real OTA error. Open its advanced terminal (uncheck "Enable auto-setup flow"
  before pairing), `wifi-connect "<SSID>" <pw>`, `ota-start <url>`, then
  `ota-progress` to read `status:<code>`. Serve OTAs from nginx (HTTP range/206
  support); python's http.server does not and the bot resets the connection.
- **Wrong IP after reboot:** update `sdk_config.ini` or set a DHCP reservation
  for Vector on the router.
- **"Not authorized" / TLS errors (SDK):** re-run `python -m
  anki_vector.configure`; the cert is per-robot and per-machine.
