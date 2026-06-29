# The "Vector Web Setup" page(s)

During onboarding (Phase 2) we bounced between several near-identical web pages
-- `wpsetup.keriganc.com`, `vector.techshop82.com`,
`websetup.froggitti.net` / `unlock-prod.froggitti.net` -- plus wire-pod's own
setup UI. This explains what they actually are, which copy we control, and how
to point the flow at our own host instead of third-party sites. It is the
groundwork for Phase 5 (self-hosting the setup + OTAs).

## TL;DR

There are TWO distinct things, often conflated:

1. **The standalone Vector Web Setup app** -- one open-source Web-Bluetooth app
   (`digital-dream-labs/vector-web-setup`, MIT, Node.js). It runs in Chrome,
   talks to Vector over BLE, joins it to Wi-Fi, and can drive OTA flashes. The
   public hosts (keriganc / techshop82 / froggitti) are all THIS app, each
   pointed at a different firmware/OTA backend:
   - `wpsetup.keriganc.com` -- general setup; serves retail `ep` OTAs on `:81`.
   - `vector.techshop82.com` -- WireOS Dev flasher (the one that worked for us).
   - `unlock-prod.froggitti.net` / `websetup.froggitti.net` -- Unlock-Prod +
     custom-firmware stacks, plus the shared `ssh_root_key`.

2. **wire-pod's own setup UI** -- bundled in the wire-pod source at
   `chipper/webroot/` and served on `:8080` (its page title is literally
   "Wire-Pod"). This is the copy WE control. It is NOT a fork of the standalone
   app; it is wire-pod's own admin UI that, for the BLE onboarding step, either
   uses wire-pod's in-built BLE or links OUT to the keriganc-hosted standalone
   app.

So: the third-party sites are interchangeable instances of app #1; the thing we
can edit and self-host is app #2 (`chipper/webroot/`), which currently
references app #1 by hardcoded URL.

## What the bundled UI does (verified on the Pi, 2026-06-27)

Path on the Pi: `~/wire-pod/chipper/webroot/`. Layout:

```
webroot/
  index.html        # "Wire-Pod" -- main admin UI (intents, logs, bot auth, ...)
  setup.html        # "Wire-Pod Setup"
  initial.html      # "Wire-Pod Initial Setup"
  js/
    ble.js          # the bot-auth / BLE onboarding logic (the relevant file)
    main.js         # UI shell; warns if webroot != binary version
    battery.js, play_audio.js, ssh.js, ui.js, initial.js
  css/  assets/  sdkapp/  favicon.*
```

The onboarding logic lives in `js/ble.js`. On opening the Bot Auth section it
calls `checkBLECapability()`, which hits `GET /api-ble/init`:

- **If wire-pod can do BLE itself** (the `inbuiltble` build, see P2-07): it runs
  the full in-built flow against the Pi's own Bluetooth -- scan -> connect (PIN
  on face) -> send_pin -> Wi-Fi -> OTA -- all via `/api-ble/*` routes.
- **If not** (our current NON-BLE binary -> `/api-ble/init` 404s): it falls back
  to `showExternalSetupInstructions()`, which tells you to "head to the
  following site" and links to the hardcoded standalone app.

## The hardcoded third-party URLs

Only two, both in `chipper/webroot/js/ble.js` (line numbers confirmed on our Pi
2026-06-27; they match what P2-02/P4-02 recorded earlier):

- **Line 1** -- the external app the UI links to when it cannot do BLE itself:
  ```js
  const vectorEpodSetup = "https://wpsetup.keriganc.com";
  ```
  Used at lines 7-8 and 39 to render the "head to this site" link.

- **Line 234** -- the OTA image the UI flashes when ITS OWN in-built BLE detects
  a dev bot in recovery (`in_recovery_dev`), inside `whatToDo()`:
  ```js
  case "in_recovery_dev":
    doOTA("http://wpsetup.keriganc.com:81/1.6.0.3331.ota");
  ```
  `doOTA(url)` (line 268) just calls `GET /api-ble/start_ota?url=<url>` and polls
  `/api-ble/get_ota_status`. So the bot downloads the OTA itself; wire-pod only
  passes the URL through. (This is the same OTA mechanism that gave us the
  `status:NNN` codes in P2-04 -- serve OTAs from a host with HTTP range/206
  support, i.e. nginx, not python's http.server.)

Note: `index.html` / `ble.js` also link to `github.com/kercre123/wire-pod/wiki`
pages (custom intents, update guide, troubleshooting); those are doc links, not
setup/OTA hosts, and need no change.

## How to edit + self-host it (the Phase 5 hook)

The bundled UI is plain static HTML/JS we own. To repoint it at our own host
instead of keriganc:

1. Edit `chipper/webroot/js/ble.js` on the Pi: change line 1 to our setup host
   and line 234 to our OTA URL.
2. Mind the version guard: `js/main.js` warns "This webroot does not match with
   the wire-pod binary" if the webroot and the compiled binary drift (it ships a
   version stamp). Editing content is fine; keep the structure intact.
3. For the standalone app itself, clone `digital-dream-labs/vector-web-setup`
   (Node.js, MIT), point its OTA backend at our images, and serve it -- this is
   what P5-01 will do, alongside hosting the OTA set with checksums.

Until Phase 5, we deliberately leave these URLs pointing at the third-party
hosts (they work and the OTAs they serve are the ones we used).

## Sources

- Verified by reading the live `chipper/webroot/` on `vector-pod.local`
  (2026-06-27).
- `digital-dream-labs/vector-web-setup` (MIT) -- the standalone app. See
  `references.md`.
- Onboarding history and OTA error codes: `setup-vector.md`, PLAN P2-02/P2-04/
  P2-07.
