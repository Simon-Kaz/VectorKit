# boot-partition staging files

Two files you copy onto the SD card's boot partition (`/Volumes/bootfs` on
macOS) to enable a headless first boot. This is the imaging-tool-agnostic
method that works with balenaEtcher, `dd`, etc. - it does NOT depend on
Raspberry Pi Imager or a `custom.toml` (see the parent README for why).

## Files

- `ssh` - empty file. Its mere presence tells Raspberry Pi OS to start the
  SSH server on first boot. Tracked here as a 0-byte file; copy it as-is.
- `userconf.txt` - one line, `username:password-hash`, which creates the
  login user headlessly. This file is **gitignored** because the hash is a
  credential. Create your own from `userconf.txt.example`:

  ```bash
  # generate the hash (macOS LibreSSL lacks -6, so use Homebrew openssl)
  brew install openssl
  printf 'vector:' > infra/raspberry-pi/boot-files/userconf.txt
  $(brew --prefix openssl)/bin/openssl passwd -6 >> infra/raspberry-pi/boot-files/userconf.txt
  ```

## Copy to the card

```bash
cp infra/raspberry-pi/boot-files/ssh         /Volumes/bootfs/ssh
cp infra/raspberry-pi/boot-files/userconf.txt /Volumes/bootfs/userconf.txt
diskutil eject /Volumes/bootfs
```

These two files enable SSH and the user, but NOT Wi-Fi (the boot-partition
Wi-Fi method was removed in Bookworm). Boot the Pi on an Ethernet cable, SSH
in, then configure Wi-Fi with `nmcli`. Full walkthrough in the parent README.
