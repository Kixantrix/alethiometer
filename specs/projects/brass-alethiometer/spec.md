# Spec: brass alethiometer (physical instrument)

> Retroactive spec for the hardware on `kixantrix-brass-alethiometer-hardware` (`hardware/`,
> `firmware/`, `api/src/functions/voice.js`). Lens: [dfma](../../../.github/skills/dfma/SKILL.md).

## Goal

A hand-held, working alethiometer that the owner orders as a kit and assembles at home. The
main construction is laser-cut brass. It uses the same oracle as the website. You turn three
thumbwheels to set three framing hands, hold the crown and speak a question, and the needle
sweeps through the reading while a hidden speaker reads the interpretation aloud.

## Builder profile

```yaml
builder:
  profile: novice-maker
  max_unaided_precision_mm: 0.5
  ok_skills: [tht-soldering, wire-soldering, drilling-with-guide, rough-cut-to-gauge,
              countersinking, gluing, screwing]
  avoid: [precision-cutting, measuring-during-assembly, stacking-and-adhering,
          structural-soldering, hand-finishing, blind-alignment, chemical-finishing]
```

In the owner's words: *"I can cut but I CANNOT do it precisely. I am not a watchmaker. I am not
that good of a crafter. Need the easiest assembly methods."* and *"I want to limit the
postprocessing and precise cutting work I need to do."* Countersinking with the right tool is
fine (D-014). THT soldering is fine (D-004). Rough cuts are fine when a gauge sets the line (D-010).

The machine-checked copy of this profile lives in [`assembly-ledger.yaml`](assembly-ledger.yaml).

## Requirements

- **R1** Brass construction orderable from SendCutSend (D-002). Buy stock parts wherever they exist (D-011).
- **R2** Three knobs set three framing hands over the 36-symbol dial, in website order with Hourglass at 12 (D-001, D-003).
- **R3** A motorised answer needle plays the reading's stops and swings.
- **R4** Mic and speaker are tastefully hidden. Push-to-talk on the crown.
- **R5** Battery, charging, USB-C flashing and OTA updates. Every module is socketed for service (D-005).
- **R6** A complete BOM (parts, sources, costs, **tools**) and an assembly guide a novice can follow (D-015).
- **R7** Assembly within the builder profile: no step needs precision tighter than 0.5 mm unless a
  part feature or supplied fixture sets it.

## Show-stopper

The needle sweeping across the brass dial through the reading, then the instrument answering
aloud from a hidden speaker.

## Acceptance criteria

- **AC-1** `hardware/cad/build.py --check` reports zero interferences and zero manufacturability notes. Level: integration. Environment: cloud-linux.
- **AC-2** `python tools/validators/check_assembly_ledger.py --strict` passes before any order is placed. Level: unit. Environment: cloud-linux.
- **AC-3** The BOM tools table matches the ledger's `tools` (`--tools-table`). Level: unit. Environment: cloud-linux.
- **AC-4** Carrier PCB DRC: 0 violations, 0 unconnected. Level: integration. Environment: local-attested-kicad.
- **AC-5** Firmware builds with PlatformIO. Level: unit. Environment: cloud-linux.
- **AC-6** Every part in the viewer has a source, retention, connection, step and tool (dfma §5); the viewer shows the real PCB and all fasteners. Level: scenario. Environment: manual-human.
- **AC-7** The built instrument answers a spoken question end to end. Attested with photos/video. Level: scenario. Environment: manual-human.
