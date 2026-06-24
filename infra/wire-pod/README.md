# wire-pod on Raspberry Pi (arm64)

The always-on Vector brain. wire-pod is the server (the cloud replacement);
WirePod is the separate packaging/release repo.

- Server source: https://github.com/kercre123/wire-pod
- Releases/installers: https://github.com/kercre123/WirePod/releases
- Install docs: https://github.com/kercre123/wire-pod/wiki/Installation

Verified on: Raspberry Pi 4B, Raspberry Pi OS Lite 64-bit (Debian 13 Trixie),
Vosk STT.

## Requirements

- Raspberry Pi on 64-bit Raspberry Pi OS (**arm64**). The armhf build
  segfaults. A Pi 4B (4 cores, ~2 GB RAM) handles Vosk comfortably.
- Provisioned and reachable over SSH: see `../raspberry-pi/README.md`.

## Install

`install.sh` is a thin, auditable wrapper over the upstream source build.
Read it first. Run it **as your normal user** (it calls sudo itself; running
the whole thing as root makes the checkout root-owned and fights the service).

From the repo checked out on the Pi (or copy just the script over):

```bash
STT=vosk MODEL_LANG=en-US infra/wire-pod/install.sh
```

It will: install prerequisites (incl. the gold linker, see below), clone
wire-pod over HTTPS, run `setup.sh` non-interactively, build the chipper
binary, install + start the systemd service, and trigger the Vosk language
model download.

When the model finishes downloading, restart so it loads:

```bash
curl -s http://localhost:8080/api/get_download_status   # wait for: success
sudo systemctl restart wire-pod
```

Verify: the web UI answers on port 8080
(`http://vector-pod.local:8080` or `http://<pi-ip>:8080`), and the logs show
`Vosk test successful!`:

```bash
systemctl is-active wire-pod
sudo journalctl -u wire-pod -n 20
```

## Gotchas (hit and resolved on Trixie)

- **`collect2: cannot find 'ld'` during build.** Misleading message. The Vosk
  Go binding forces `-fuse-ld=gold`, and Debian Trixie dropped `ld.gold` from
  the default binutils. Fix: `sudo apt install binutils-gold`. (Handled by
  `install.sh`.)
- **"wire-pod is ready to run!" is premature.** `setup.sh` downloads the Vosk
  *library*, not the language *model*. The model is fetched via the web UI
  (`/api/set_stt_info`). Until then the log shows
  `open ../vosk/models/: no such file or directory`. (Handled by `install.sh`.)
- **"detected dubious ownership in repository".** The root-run service calls
  git against the user-owned checkout. Harmless; silenced with
  `sudo git config --global --add safe.directory <checkout>`.
- **Clone over HTTPS, not SSH.** The wiki warns an SSH clone breaks future
  `update.sh` runs.

## Next

Onboard the robot: `../../docs/setup-vector.md`.

## Notes

- Keep the Pi on a static DHCP lease so the web UI address is stable.
- Docker compose is an upstream alternative (needs `escapepod.local`/mDNS); we
  use the native systemd service on a dedicated Pi for simplicity.
