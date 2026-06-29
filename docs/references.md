# External references

Authoritative outside documentation for Vector's hardware, firmware, behaviors,
and the gRPC/protobuf protocols. Consult these BEFORE editing anything that
touches Vector internals (firmware, OTA, behaviors, the SDK protos) so we are
not working blind. They are reverse-engineered community sources -- treat them
as strong guidance, but our own verified notes in `setup-vector.md` win where
they conflict for our specific bot.

## Primary

- **Vector Technical Reference Manual (TRM)** -- Randall Maas.
  <https://randym32.github.io/Vector-TRM.pdf>
  The deepest single document: architecture, file system, boot/recovery, the
  vic-* process map, and the cloud protocols (Chipper, JDocs, token manager)
  with their gRPC/Protobuf shape. Start here for "how does X actually work
  inside the robot."

- **Vector Community Documents (wiki)** -- Randall Maas et al.
  <https://randym32.github.io/Anki.Vector.Documentation/>
  Companion wiki to the TRM. Covers the behavior tree (classes/IDs, animation
  triggers), console variables, backpack lights, sound banks, self-test/error
  codes, hardware repair (exploded views, part swaps), the Python/C# SDKs, and
  WebViz. Good for behaviors and on-robot specifics.

- **Available Anki Vector Documentation (link hub)** -- claudix29 (MIT).
  <https://github.com/claudix29/available-anki-vector-documentation>
  Curated index of nearly everything else: DDL firmware/hardware docs, the OTA
  archive, WireOS / wire-os-victor (custom firmware + OTA building), unlock
  tools (froggitti et al.), the Ankibots wiki, plus local docs on SSH custom
  commands, BLE terminal commands, and self-test error codes. Use as the
  jumping-off point when the two above do not cover something.

## Tooling, SDKs, and samples

Code to study, not adopt wholesale. Most are .NET/C# while we are Python -- so
treat them as protocol/format references and worked examples, not drop-in deps.
The two Python-relevant ones for us are the package tooling.

On-robot packaging (Python -- usable directly):
- **Anki.Vector.PackageInstaller** -- randym32, MIT, Python.
  <https://github.com/randym32/Anki.Vector.PackageInstaller>
  `vector-pkg.py` builds/installs `.vpkg` bundles on Vector (sprites, behaviors,
  sound banks, config) from an `.ini` manifest; includes the VEP2 design doc.
  The closest existing tool to "deploy our own assets/code to the bot."
- **Anki.Vector.Packages** -- randym32, per-package licenses.
  <https://github.com/randym32/Anki.Vector.Packages>
  A small repo of example `.vpkg` packages produced by the installer above.
  Reference for the package format in practice.

Resource / asset internals (C#, but the format knowledge is language-agnostic):
- **Anki.Resources.SDK** -- randym32, BSD-2-Clause.
  <https://github.com/randym32/Anki.Resources.SDK>
  Reads the resource tree extracted from an OTA: sounds, sprite-sequences,
  animations, plus the `cozmo_anim.fbs` / `vector_anim.fbs` schemas. Directly
  relevant to Phase 5 OTA work and to understanding Vector's assets.
- **Anki.Resources.Samples** -- randym32.
  <https://github.com/randym32/Anki.Resources.Samples>
  C# examples for the above: playing sounds, sprite sequences, composite-image
  animations, image recognition, text substitution.

SDK / protocol references (C# -- mine for protocol behavior, not code):
- **codaris/Anki.Vector.Samples** -- Apache-2.0, C#.
  <https://github.com/codaris/Anki.Vector.Samples>
  18 tutorials for the .NET Vector SDK (speech, motion, face display, camera,
  cubes, events, intents). Useful as a capability checklist mirrored against our
  Python SDK fork.
- **Anki.Vector.WebVizSDK** -- randym32, BSD-2-Clause, C#.
  <https://github.com/randym32/Anki.Vector.WebVizSDK>
  Connects to the WebViz API on DEV-build robots (audio events, mic data, speech
  recognition). Niche -- only dev units expose WebViz -- but the one reference
  for that interface, which our WireOS-Dev bot may expose.

## How these map to our work

- Firmware / OTA (Phase 5, P5-01/P5-02): TRM boot+recovery + the OTA archive and
  WireOS build notes in the link hub. Our P2-04/P2-06 dead-ends already line up
  with the TRM's dev-vs-prod signing story.
- Behaviors / onboarding hangs (P2-02): the wiki's behavior-tree and self-test
  docs explain the `mark_complete_and_exit` / vision-stack behavior we hit.
- SDK / proto regeneration (P3-04): the TRM's protocol chapter and the wiki's
  SDK pages document the gRPC services our vendored fork wraps; codaris's .NET
  samples are a capability checklist to test our Python SDK against.
- Deploying our own code/assets to the bot: PackageInstaller (`.vpkg`) is the
  existing Python tool; Anki.Resources.SDK + the `.fbs` schemas explain the
  asset formats those packages touch. Worth a look when a prototype needs to
  ship files onto Vector.

For the browser setup/flashing flow specifically (keriganc/froggitti/techshop82
and the copy wire-pod bundles), see `web-setup.md`.

See `landscape.md` for why we chose this stack and `architecture.md` for how our
pieces connect.
