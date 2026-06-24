# Raspberry Pi headless provisioning

How the wire-pod host (a Pi 4B) was set up from a Mac with no monitor, and the
reusable procedure for future Pis. This documents what actually worked, after
a false start with `custom.toml` (see "Why not custom.toml" below).

Tested on: Raspberry Pi 4B, Raspberry Pi OS Lite 64-bit (Debian 13 Trixie),
flashed with balenaEtcher, configured from macOS.

## Overview

1. Flash Raspberry Pi OS Lite (64-bit) with balenaEtcher.
2. Drop two files on the boot partition to enable SSH + create the user.
3. Boot on an **Ethernet cable**, SSH in over the wired connection.
4. Bring up Wi-Fi with `nmcli`, then drop the cable.
5. Pin the IP with a router DHCP reservation.

## 1. Flash

Download Raspberry Pi OS Lite (64-bit) `.img.xz` and flash it with
balenaEtcher (it reads `.xz` directly). 64-bit is required for wire-pod;
Lite because the host is headless.

## 2. Enable SSH + user (boot partition)

Re-insert the card; the boot partition mounts at `/Volumes/bootfs`. Copy the
two staging files from `boot-files/` (see `boot-files/README.md` for how to
generate `userconf.txt` with your own password hash):

```bash
cp infra/raspberry-pi/boot-files/ssh          /Volumes/bootfs/ssh
cp infra/raspberry-pi/boot-files/userconf.txt /Volumes/bootfs/userconf.txt
diskutil eject /Volumes/bootfs
```

## 3. Boot wired and SSH in

Card into the Pi, **plug in Ethernet**, power on. After ~60-90s:

```bash
ssh <user>@raspberrypi.local
```

The hostname is the default `raspberrypi` at this point (we set a real one
below). If `.local` does not resolve, find the Pi's IP in your router's client
list and SSH to that. Log in with the password whose hash is in
`userconf.txt`.

## 4. Configure the box (over SSH)

```bash
# hostname
sudo hostnamectl set-hostname vector-pod

# install your SSH public key(s) for keyless login
install -d -m 700 ~/.ssh
cat >> ~/.ssh/authorized_keys <<'EOF'
<paste contents of your *.pub file(s), one per line>
EOF
chmod 600 ~/.ssh/authorized_keys

# Wi-Fi. NOTE: single-quote an SSID containing '!' or bash history expansion
# ("event not found") will break the command.
sudo raspi-config nonint do_wifi_country <CC>          # e.g. IE -- REQUIRED
sudo nmcli radio wifi on
sudo nmcli device wifi connect '<SSID>' password '<WIFI_PASSWORD>'

# confirm Wi-Fi got an IP BEFORE unplugging Ethernet
nmcli -t -f NAME,DEVICE connection show --active
ip -4 addr show wlan0 | grep inet
```

Then reboot, unplug Ethernet, and reconnect over Wi-Fi:
`ssh <user>@vector-pod.local`.

## 5. Pin the IP

DHCP can move the address and break wire-pod's config later. Reserve it in the
router (preferred, survives reinstalls): bind the Pi's `wlan0` MAC
(`cat /sys/class/net/wlan0/address`) to a fixed IP. On a FRITZ!Box:
Home Network -> Network -> Network Connections -> edit the device ->
"Always assign this network device the same IPv4 address".

## Why not custom.toml

Raspberry Pi OS only runs the `custom.toml` / `firstrun.sh` first-boot
provisioning if `cmdline.txt` contains a `systemd.run=...firstrun.sh` trigger.
**Raspberry Pi Imager adds that line; balenaEtcher (and `dd`) do not.** A
`custom.toml` placed on an Etcher-written card is silently ignored - no user,
no Wi-Fi, no SSH. The `ssh` + `userconf.txt` files used above are handled by a
separate mechanism that works regardless of imaging tool, which is why this is
the reliable path. The old boot-partition `wpa_supplicant.conf` Wi-Fi method
was also removed in Bookworm, so Wi-Fi is configured post-boot via `nmcli`.

## Next

Install wire-pod on the host: `../wire-pod/README.md`.
