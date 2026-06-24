# infra

Provisioning for the self-hosted Vector stack.

- `raspberry-pi/` - headless Pi provisioning (flash + first-boot config).
- `wire-pod/` - install and run wire-pod on the Raspberry Pi (arm64).

The Pi is the always-on host: it runs wire-pod (the cloud replacement) so
Vector's voice and registration work without Anki's servers. See
`../docs/architecture.md`.
