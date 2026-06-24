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

OSKR bots are already dev-unlocked, so there is no `ep` flash and no recovery
step -- they are unlocked with an SSH key instead. wire-pod's web UI even notes
a firmware warning here "can be ignored"; the OSKR path needs firmware >= 1.4.

Order matters, and it is the reverse of the retail flow: do the SSH-key step
FIRST, then authenticate. Going straight to the `wpsetup` link before the bot
is set up makes that page reset and do nothing.

1. In Bot Setup, under **"Configure an OSKR/dev-unlocked robot"**, enter the
   bot's IP address, upload the bot's SSH key, and click **Set up bot**.
2. Only then proceed to step 3 (the `wpsetup` authentication link).

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

- "Not authorized" / TLS errors: re-run the SDK configure step; the cert is
  per-robot and per-machine.
- Wrong IP after reboot: update `sdk_config.ini` or assign Vector a static
  DHCP lease on your router.
- Firmware version does not end in `ep`: re-flash via recovery; voice and
  full control will not work otherwise.
