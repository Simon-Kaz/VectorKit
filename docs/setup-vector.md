# Setting up Vector with wire-pod

End-to-end onboarding for a retail Vector. Assumes wire-pod is already running
on the Pi (see `infra/wire-pod/README.md`).

> Order matters: install/start wire-pod first, then flash + authenticate the
> robot against it.

## 1. Prerequisites

- Vector on its charger, fully booted.
- Pi running wire-pod, reachable on the LAN (default web UI on port 8080,
  often as `http://escapepod.local:8080` or the Pi's IP).
- A Chromium-based browser (the setup page uses Web Bluetooth / Web Serial).
- Vector and the browser machine on the same network.

## 2. Prepare the bot (firmware / unlock)

First find out which kind of bot you have. On the charger, raise the lift arm
to the top and lower it to cycle Vector's Customer Care Info Screen, which
shows serial, firmware version, and IP. A bot that boots to an **OSKR logo**
is dev-unlocked.

### Retail bot

Retail bots need DDL firmware whose version string ends in `ep`. Stock v2.0.x
is NOT enough.

1. Place Vector on the charger.
2. Hold the backpack button ~15 seconds until it enters recovery mode.
3. In wire-pod's web UI, follow "Bot Setup" to flash the DDL-compiled
   firmware. After flashing, the firmware version should end in `ep`.

### OSKR / dev-unlocked bot

OSKR bots are already dev-unlocked. The intended path is to SSH in and run
wire-pod's `setup.sh scp <bot-ip> <ssh-key>`, which writes the escapepod cert +
`server_config.json` onto the bot so it talks to `escapepod.local`. This needs
the bot's root SSH key.

**If you HAVE the SSH key:** run `setup.sh scp` and skip ahead to section 4.

**If the SSH key is LOST (our case -- this is the route we took):** the original
DDL-portal key is gone and the retail `ep`-firmware path does NOT work on a
dev/OSKR bot (it fails OTA `status:214`, Dev/Prod mismatch -- all published `ep`
builds are prod-signed). The way forward is to re-flash with community CFW:

1. **Unlock-prod first.** Our bot's recovery OS was the old `0.9.0`, which
   cannot parse a modern dev image over BLE (fails OTA `status:200`, Unexpected
   .tar contents). Flash froggitti's `Unlock-Prod.ota` via
   <https://unlock-prod.froggitti.net> (Utility stack). ~7 min; keep Vector on
   the charger and do NOT interrupt -- it rewrites the recovery filesystem.
2. **Then flash WireOS** (the chosen CFW) via <https://websetup.froggitti.net>
   -> Custom Firmware stack. WireOS is SSH-able and wire-pod-friendly.
3. **Get a working SSH key + connect to wire-pod.** froggitti's tool issues a
   fresh SSH root key the now-dev bot accepts. Use it with wire-pod's
   `setup.sh scp <bot-ip> <key>` to install the escapepod cert + server_config.

Reference docs: the DDL OSKR owner's manual
(github.com/digital-dream-labs/oskr-owners-manual) and the community CFW docs
(os-vector.github.io/vector-docs). Note os-vector routes dev/OSKR installs over
SSH precisely because BLE `ota-start` only works for "Unlocked Prod" bots.

## 3. Clear user data and authenticate

1. In the web UI, clear user data when prompted.
2. Use "Bot Setup" -> Scan (BLE) to find Vector, or follow the provided link.
3. Click ACTIVATE / AUTHENTICATE. If it errors, wait ~20 seconds and retry.
4. Success shows "Vector setup is complete!"

OSKR / dev-unlocked bots: complete the "Set up OSKR/dev bot" step first.

## 4. Authenticate the Python SDK

Install the vendored SDK (our fork), then authenticate. This writes per-robot
credentials to `~/.anki_vector/` on the machine that will run your code.

```bash
pip install -e libs/vendor/wirepod-vector-python-sdk
python -m anki_vector.configure
```

You will need, from the underside of Vector or the app:
- Robot serial number
- Robot name (e.g. `Vector-A1B2`)
- Robot IP address (shown on Vector's face: lift + lower, or via your router)

## 5. Verify

```bash
cd prototypes/hello-vector
python main.py
```

Vector should say hello and report battery state. If gRPC connection fails,
confirm the IP in `~/.anki_vector/sdk_config.ini` matches Vector's current IP
(it can change on DHCP lease renewal).

## Troubleshooting

- "Error logging in. The bot is likely unable to communicate with your
  wire-pod instance" at the Activate step: the bot authenticates against
  `escapepod.local:443`. This fails if wire-pod is NOT in escape-pod mode --
  check `apiConfig.json` on the Pi for `"epconfig": false`. Our Pi is named
  `vector-pod` (so only `vector-pod.local` resolves by default); wire-pod must
  advertise `escapepod.local` itself, which it only does in escape-pod mode.
  Fix: `curl http://localhost:8080/api-chipper/use_ep` on the Pi (sets
  epconfig=true, port=443, restarts chipper), or re-run `setup.sh` and choose
  the `escapepod.local` certs. Then `getent hosts escapepod.local` should
  return the Pi's IP and 443/8084 should be listening. mDNS broadcasts ~every
  60s, so wait a minute and retry Activate.
- wpsetup stuck at 0% / "Error while updating": the web UI hides the bot's real
  OTA error (the failure branch is a no-op). A stale browser cache can also
  break it -- try an incognito window. To see the REAL error, open wpsetup's
  advanced terminal (uncheck "Enable auto-setup flow" before pairing), then run
  `wifi-connect "<SSID>" <pw>`, `ota-start <url>`, and `ota-progress` -- it
  prints `status:<code>`. Common codes: 200 unexpected .tar contents (recovery
  OS too old to parse the image), 203 URL unreachable, 209 signature, 214
  dev/prod mismatch (dev bot refusing a prod-signed `ep`), 215 network stall.
  Host the .ota on a server that supports HTTP range/206 (nginx; python's
  http.server does not, and the bot resets the connection).
- OTA `status:214` on a dev/OSKR bot, or `status:200` on old recovery: do not
  keep trying `ep` builds. Use the unlock-prod + WireOS route in section 2.
- "Not authorized" / TLS errors: re-run the SDK configure step; the cert is
  per-robot and per-machine.
- Wrong IP after reboot: update `sdk_config.ini` or assign Vector a static
  DHCP lease on your router.
- Firmware version does not end in `ep`: re-flash via recovery; voice and
  full control will not work otherwise (retail bots only; OSKR bots are
  already dev-unlocked and report an `oskr`-suffixed version like
  `1.7.1.6003oskr`).
