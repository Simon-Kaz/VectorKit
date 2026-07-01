# P5-01 design note: self-host the Vector Web Setup + all OTAs

Status: design (not started). Refines the P5-01 task in `docs/PLAN.md`. Not
blocking other work -- this is the plan to act on when Phase 5 begins.

## Goal

A setup site and OTA host WE control, serving every image the onboarding flow
needs, so no third-party site (keriganc / techshop82 / froggitti) is required to
unlock + flash + onboard a Vector.

## Background (what we learned)

- The browser setup tool is one open-source Web-Bluetooth app
  (`digital-dream-labs/vector-web-setup`, MIT, Node). keriganc/techshop82/
  froggitti are all descendants of it, each pointed at a different OTA backend.
  See `docs/web-setup.md`.
- The valuable, hard part -- the reverse-engineered BLE GATT/RTS protocol
  (`site/js/rts.js`, ~16k lines) -- is byte-for-byte intact in every fork.
  Nobody re-derived it. So a fork inherits the protocol for free; the work is in
  config, hosting, and UX.
- keriganc is a dead HTTrack mirror of techshop82; techshop82 (no public source)
  is the live one. Its OTA host `ota.techshop82.com` serves exactly our images:
  `ep` builds, `unlock-prod.ota`, `revert-to-prod.ota`, `wireos-dev.ota`.

## Decisions already made

- **Fork base: `bliteknight/vector-web-setup`**, forked to
  `Simon-Kaz/vector-web-setup` (public, MIT restored, lineage in its
  `NOTICE.md`). Chosen because it already has the firmware-selection dropdown,
  OTA progress bar + error label, and step-by-step instructions, and it tracks
  the techshop82 OTA set that matches the path that actually worked for us in
  Phase 2. (froggitti was the runner-up: cleaner Docker/nginx/HTTPS deploy and
  intact MIT, but a thin UI.)
- The fork is already hygiene-fixed: DDL MIT LICENSE restored, committed private
  TLS key removed + gitignored, `server.js` guarded to run HTTP without it.

## The core constraint: Web Bluetooth needs a secure context

`navigator.bluetooth` only works on **HTTPS** or **`http://localhost`**. This is
why every public instance is an HTTPS site, and why the app cannot simply be
served from the Pi over `http://escapepod.local:8080`.

Crucial split, confirmed by reading `server.js` (the app's BLE page and the OTA
file server are two listeners):

- **The setup web app needs HTTPS** (it runs the BLE in the browser).
- **The OTA images do NOT.** The *robot* downloads the OTA over its own Wi-Fi;
  the browser only hands it a URL via `ota-start`. The robot cannot do an HTTPS
  handshake during flashing -- OTAs MUST be plain HTTP. (This matches the
  README's own note and our P2-04 findings.)

So self-hosting is two hosts, not one.

## Proposed architecture

```
+---------------------------+        +-----------------------------+
|  Setup web app (HTTPS)    |        |  OTA host (plain HTTP)      |
|  our fork of vector-web-  |        |  nginx on the Pi            |
|  setup                    |        |  serves *.ota with          |
|                           |        |  range/206 support          |
|  Option A: GitHub Pages   |        |  (NOT python http.server)   |
|   (free HTTPS) -- preferred|        |  http://<pi>:<port>/ota/... |
|  Option B: localhost on   |        +--------------+--------------+
|   the setup machine        |                      ^
+------------+--------------+                       |
             | Web Bluetooth (browser <-> robot)    | robot downloads OTA
             v                                       | over its own Wi-Fi
        +----+-------------------------------+-------+
        |              Anki Vector                    |
        +---------------------------------------------+
```

### Host 1 -- the setup app (HTTPS)

Preferred: **GitHub Pages on our fork** (free HTTPS, trivial deploy, no Pi
cert maintenance). Caveat: bliteknight's app is a Node/Express server
(`server.js`) that serves `site/` statically AND has a tiny stub `/sessions`
endpoint. For Pages (static only) we either:

- (a) serve `site/` statically and replace the `/sessions` stub with a static
  JSON or a client-side shim (escape-pod auth is already stubbed -- see P2-03),
  or
- (b) keep the Node server and host it where it can run with HTTPS (Pi +
  Let's Encrypt needs a public DNS name; or a small VPS). froggitti's
  Docker+nginx+certbot setup is the reference if we go this way.

Lean (a) for simplicity unless the `/sessions` stub turns out to be load-bearing
for our escape-pod flow (needs a spike).

Fallback for anyone without Pages: `git clone` + `node server.js`, use via
`http://localhost:8000`. Always works, no cert.

### Host 2 -- the OTA host (plain HTTP, on the Pi)

- nginx on the Pi (we already run wire-pod there), serving an `ota/` dir with
  HTTP **range/206** support -- python's `http.server` does NOT, and the bot
  resets the connection (P2-04).
- Mirror the image set we need, recording for each: source URL, sha256, and
  **signing type (prod vs dev/OSKR)** -- the distinction that broke P2-04.
  Minimum set: `unlock-prod.ota`, `wireos-dev.ota` (the path that worked), plus
  `revert-to-prod.ota` and a clean official base for completeness.

### Repointing the fork at our hosts

Two edits (bliteknight specifics, verified):

- `site/js/env/endpoints.js` -- `otaEndpoints` (auto-flash URL) and
  `accountEndpoints`. Point at our OTA host.
- The firmware `<select>` in `site/html/main.html` -- replace the
  `ota.techshop82.com/...` option URLs with our host's URLs.
- (In wire-pod's bundled copy, the equivalents are `chipper/webroot/js/ble.js`
  line 1 + line 234 -- see `docs/web-setup.md`. We may or may not touch that copy
  depending on whether onboarding uses our standalone app or wire-pod's UI.)

Mind the `site/js/main.js` webroot-vs-binary version guard (for the wire-pod
copy only).

## BLE decision: standardize on browser BLE, drop Pi in-built BLE

We have two BLE mechanisms and our own history already picked the winner:

- **Browser BLE** (the standalone app, the laptop/phone's Bluetooth -> robot):
  this is what WORKED for us (P2-02, the techshop82 web-UI reflash).
- **Pi in-built BLE** (wire-pod `/api-ble/*` using the Pi's own Bluetooth):
  reproducibly wedged the Pi 4's built-in Bluetooth ("BLE driver has broken"),
  reverted in P2-07/P2-08.

Decision: **the self-hosted flow uses browser BLE only.** Do not revive Pi
in-built BLE (a USB BT dongle could rescue it per P2-07, but it is not worth it
when browser BLE is reliable and needs no Pi hardware). This removes the most
confusing and error-prone branch.

## UX revamp (fold in P4-01)

The current flow is confusing because errors are swallowed (P2-04: the GUI's
empty `else` in `onOtaProgress` hid the real `status:NNN` code) and because the
right next step depends on opaque bot state. The revamp -- which IS the P4-01
interactive onboarding guide, so do it once, here -- should:

1. Detect bot state (retail/OSKR, recovery vs firmware, dev vs prod) and show
   only the relevant next step. bliteknight's `whatToDo()` switch on
   `get_robot_status` is the seed.
2. Pick firmware from a clearly-labelled list (what each image does, signing
   type), defaulting to our known-good path.
3. Flash with **live status and real error codes surfaced** (fix the swallowed
   `else`), with the OTA error-code table from `docs/setup-vector.md`.
4. Onboard against escapepod.local, then run the verification (voice test;
   optionally the tcpdump / stop-the-pod proofs).

Treat "revamped web setup app" and "P4-01 guide" as the SAME deliverable.

## Security / hygiene

- Never commit private TLS keys (already removed from the fork; generate per
  deploy). If GitHub Pages, the cert is managed for us.
- Record OTA checksums; verify after mirroring. Note signing type per image.
- The fork's stub `/sessions` returns a hardcoded token + a stranger's email
  (inherited from upstream's escape-pod stub) -- replace/neutralize it in the
  revamp; it is not a secret of ours but it should not ship in our UI.

## Open questions (resolve with small spikes, not commitment)

1. Is the Node `/sessions` stub load-bearing for OUR escape-pod onboarding, or
   can the app be fully static on Pages? (Determines Host-1 option a vs b.)
2. Where do we source the OTA images to mirror, and are their checksums
   recorded anywhere authoritative? (techshop82 + froggitti serve them; the
   `references.md` link hub has an OTA archive.)
3. Do we still need to touch wire-pod's bundled `chipper/webroot/` copy at all,
   or does the standalone app fully replace it for onboarding?

## Done when (unchanged from P5-01)

A Vector can be unlocked + flashed end to end from our own site + OTA host, with
zero third-party dependencies, and the OTA set is checksummed.

## References

- `docs/web-setup.md` -- what the page is, the bundled copy, the hardcoded URLs.
- `docs/setup-vector.md` -- the working path, OTA error codes, the proofs.
- `docs/references.md` -- TRM, community wiki, OTA archive link hub.
- The fork: `Simon-Kaz/vector-web-setup` (see its `NOTICE.md`).
- PLAN: P5-01, P5-02 (OTA internals), P4-01 (onboarding guide -- folded in).
