#!/usr/bin/env bash
#
# Install wire-pod on a 64-bit Raspberry Pi (arm64) via the source-build path.
# Thin, auditable wrapper around the official setup. Read before running.
#
#   sudo STT=vosk infra/wire-pod/install.sh
#
# Verify the latest instructions against:
#   https://github.com/kercre123/wire-pod/wiki/Installation
set -euo pipefail

STT="${STT:-vosk}"
INSTALL_DIR="${INSTALL_DIR:-/opt/wire-pod}"
REPO="https://github.com/kercre123/wire-pod"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root (sudo). The setup installs a system service." >&2
  exit 1
fi

arch="$(uname -m)"
if [[ "${arch}" != "aarch64" && "${arch}" != "arm64" ]]; then
  echo "Expected arm64/aarch64, got '${arch}'." >&2
  echo "On a Pi this means you booted a 32-bit OS; the armhf build segfaults." >&2
  echo "Reflash 64-bit Raspberry Pi OS, or set INSTALL anyway at your own risk." >&2
  exit 1
fi

echo "Installing build prerequisites..."
apt-get update
apt-get install -y git

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  echo "Updating existing checkout in ${INSTALL_DIR}..."
  git -C "${INSTALL_DIR}" pull --ff-only
else
  echo "Cloning ${REPO} into ${INSTALL_DIR}..."
  git clone --recurse-submodules "${REPO}" "${INSTALL_DIR}"
fi

echo "Running wire-pod setup with STT=${STT}..."
cd "${INSTALL_DIR}"
STT="${STT}" ./setup.sh

echo
echo "Done. Web UI should be on this host's port 8080"
echo "  (http://escapepod.local:8080 or http://<pi-ip>:8080)."
echo "Next: onboard your robot per docs/setup-vector.md."
