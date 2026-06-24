#!/usr/bin/env bash
#
# Install wire-pod on a 64-bit Raspberry Pi (arm64) via the source-build path.
# Thin, auditable wrapper around the official setup. Read before running.
#
# Run as the NORMAL user (not root); it calls sudo where needed. Running the
# whole thing as root would make the clone root-owned, which fights the
# systemd service that runs as that user.
#
#   STT=vosk MODEL_LANG=en-US infra/wire-pod/install.sh
#
# Verified on Raspberry Pi OS Lite 64-bit (Debian 13 Trixie), Pi 4B.
# Latest upstream instructions: https://github.com/kercre123/wire-pod/wiki/Installation
set -euo pipefail

STT="${STT:-vosk}"
MODEL_LANG="${MODEL_LANG:-en-US}"        # Vosk language model to fetch; empty to skip
INSTALL_DIR="${INSTALL_DIR:-${HOME}/wire-pod}"
REPO="https://github.com/kercre123/wire-pod"   # HTTPS, not SSH: the wiki warns
                                               # an SSH clone breaks later updates.

if [[ "${EUID}" -eq 0 ]]; then
  echo "Run as your normal user, not root. The script uses sudo where needed." >&2
  exit 1
fi

arch="$(uname -m)"
if [[ "${arch}" != "aarch64" && "${arch}" != "arm64" ]]; then
  echo "Expected arm64/aarch64, got '${arch}'." >&2
  echo "On a Pi this means you booted a 32-bit OS; the armhf build segfaults." >&2
  exit 1
fi

echo "Installing build prerequisites..."
# git: clone. binutils-gold: the Vosk Go binding forces '-fuse-ld=gold', and
# Trixie dropped ld.gold from default binutils -- without it the chipper build
# fails with a misleading "collect2: cannot find 'ld'".
sudo apt-get update -qq
sudo apt-get install -y git binutils-gold

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  echo "Updating existing checkout in ${INSTALL_DIR}..."
  git -C "${INSTALL_DIR}" pull --ff-only
else
  echo "Cloning ${REPO} into ${INSTALL_DIR}..."
  git clone --depth=1 "${REPO}" "${INSTALL_DIR}"
fi

cd "${INSTALL_DIR}"

# setup.sh prompts for STT (skipped by STT=vosk) and for cert type. Feeding a
# blank line accepts the cert default (escapepod.local certs), which is correct
# for retail Vectors.
echo "Running wire-pod setup with STT=${STT}..."
yes "" | sudo STT="${STT}" ./setup.sh

echo "Building the chipper binary and installing the systemd service..."
yes "" | sudo STT="${STT}" ./setup.sh daemon-enable

# The service runs git as root against a user-owned checkout; mark it safe to
# silence "detected dubious ownership" warnings on startup.
sudo git config --global --add safe.directory "${INSTALL_DIR}"

echo "Starting wire-pod..."
sudo systemctl start wire-pod
sleep 5
if systemctl is-active --quiet wire-pod; then
  echo "wire-pod is active."
else
  echo "wire-pod did not start. Check: sudo journalctl -u wire-pod -n 50" >&2
  exit 1
fi

# setup.sh fetches the Vosk *library* but not the language *model*. The model
# is normally pulled via the web UI; trigger it here so STT works out of the box.
if [[ -n "${MODEL_LANG}" ]]; then
  echo "Triggering Vosk model download (${MODEL_LANG})..."
  curl -fsS -m 15 -X POST "http://localhost:8080/api/set_stt_info" \
    -H "Content-Type: application/json" -d "{\"language\":\"${MODEL_LANG}\"}" || true
  echo
  echo "Model is downloading in the background. Poll with:"
  echo "  curl -s http://localhost:8080/api/get_download_status"
  echo "When it reports success, restart so it loads: sudo systemctl restart wire-pod"
fi

ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo
echo "Done. Web UI: http://${ip:-<pi-ip>}:8080"
echo "Next: onboard your robot per docs/setup-vector.md."
