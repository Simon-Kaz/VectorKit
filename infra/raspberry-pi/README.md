# Raspberry Pi headless provisioning

Reusable setup for any Pi in this project (the wire-pod host and future
display Pis). Flash, configure headlessly over Wi-Fi, then SSH in - no monitor
needed.

## Files

- `custom.toml.template` - sanitized first-boot config for Raspberry Pi OS
  (Bookworm+). Copy it, fill in the placeholders, and drop it as `custom.toml`
  on the SD card's boot partition. A filled-in `custom.toml` is gitignored
  because it contains a password hash and Wi-Fi secrets.

## Flow (balenaEtcher on macOS)

1. Flash Raspberry Pi OS Lite (64-bit) to the card with balenaEtcher.
2. Re-insert the card; the boot partition mounts at `/Volumes/bootfs`.
3. Generate a password hash and fill the template (see comments inside it).
4. Write it: `pbpaste > /Volumes/bootfs/custom.toml`, then
   `diskutil eject /Volumes/bootfs`.
5. Boot the Pi (~90s), then `ssh <user>@<hostname>.local`.
6. Confirm it is arm64-ready: `uname -m` should print `aarch64`.

For installing wire-pod on the host once it is reachable, see
`../wire-pod/README.md`.
