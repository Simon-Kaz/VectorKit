# wire-pod on Raspberry Pi (arm64)

Provisioning the always-on Vector brain. wire-pod is the server; WirePod is
the packaging/release repo you download installers from.

- Server source: https://github.com/kercre123/wire-pod
- Releases/installers: https://github.com/kercre123/WirePod/releases
- Install docs: https://github.com/kercre123/wire-pod/wiki/Installation

## Requirements

- Raspberry Pi running 64-bit Raspberry Pi OS (**arm64**). Pi 5 requires
  arm64; the armhf build segfaults. Pi 4 with 64-bit OS is fine.
- On the same LAN as Vector.
- Bluetooth (for BLE onboarding) and a browser machine that can reach the Pi.

## Install

The exact commands change between releases, so `install.sh` here is a thin,
auditable wrapper that follows the wiki's source-build path. Read it before
running. Pin the STT engine via the `STT` env var (default `vosk`, fully
offline).

```bash
sudo STT=vosk infra/wire-pod/install.sh
```

After install, wire-pod runs as a service. The web UI is typically on port
8080, reachable at `http://escapepod.local:8080` (mDNS) or the Pi's IP.

## Next

Onboard the robot: `../../docs/setup-vector.md`.

## Notes

- Keep this host on a static DHCP lease so the web UI address is stable.
- Docker compose is an alternative (needs `escapepod.local` / mDNS); see the
  wiki. We default to the native service install for simplicity on a
  dedicated Pi.
