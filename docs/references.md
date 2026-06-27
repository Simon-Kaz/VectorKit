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

## How these map to our work

- Firmware / OTA (Phase 5, P5-01/P5-02): TRM boot+recovery + the OTA archive and
  WireOS build notes in the link hub. Our P2-04/P2-06 dead-ends already line up
  with the TRM's dev-vs-prod signing story.
- Behaviors / onboarding hangs (P2-02): the wiki's behavior-tree and self-test
  docs explain the `mark_complete_and_exit` / vision-stack behavior we hit.
- SDK / proto regeneration (P3-04): the TRM's protocol chapter and the wiki's
  SDK pages document the gRPC services our vendored fork wraps.

See `landscape.md` for why we chose this stack and `architecture.md` for how our
pieces connect.
