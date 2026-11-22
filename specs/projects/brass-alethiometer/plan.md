# Plan: brass alethiometer

> Living plan. Workflow and gates: [playbooks/hardware-product.md](../../../playbooks/hardware-product.md).
> Code lives on `kixantrix-brass-alethiometer-hardware` until it merges to `main`.

## Architecture (as of ea2574c)

| Area | Source of truth | Generates |
|---|---|---|
| Mechanics | `hardware/cad/design.py` (CadQuery), with constants in `hardware/cad/layout.py` | SendCutSend DXF/STEP, renders, `build_report.json`, viewer GLB |
| PCB | `hardware/pcb/make_pcb.py` (KiCad 10 + Freerouting), reading `layout.py` | Gerbers, DRC report, renders |
| Dial | `hardware/dial/make_dial.py` (+ local-only Myth Made art) | Sticker SVG/PNG/PDF |
| Viewer | `hardware/viewer/export_viewer.py` + three.js | `assets/` (git-ignored) |
| Firmware | `firmware/` (PlatformIO, ProS3 ESP32-S3) | Firmware image |
| Cloud | `api/src/functions/voice.js` (`/api/ask-voice`, `/api/speak`) | Azure Function |
| Hand work | [`assembly-ledger.yaml`](assembly-ledger.yaml) | BOM §G tools table, the ready-to-order gate |

## Check loop

| Command | When | Time |
|---|---|---|
| `python hardware/cad/build.py --check` | After every model edit | ~2 min |
| `python -m pytest hardware/cad` | After every model edit | 1–8 min |
| `python tools/validators/check_assembly_ledger.py` | When an assembly step changes | <1 s |
| `python hardware/cad/build.py` | At milestones; run in the background | ~6–7 min |
| `python hardware/viewer/export_viewer.py` | After every model change the owner will review | ~20 s |

## Ledger status (ea2574c)

31 operations and 125 hand touches. 17 violations: 3 accepted (countersinking, hinge leaf trim)
and 14 with remediation planned. Most of the remediations are D-013 (turned-parts kit) and
D-012 (spring-steel hands). These are the ones *not* covered by an approved decision. Each needs
an owner decision framed per dfma §7:

| Ledger op | Problem | Proposed fix |
|---|---|---|
| `set-motor-mesh` | The X27 is slid in a slot until the mesh has "a hair of backlash". That's judgement at about 0.05 mm. | Fixed pin holes at the designed centre distance, or a laser-cut mesh shim |
| `coax-p2-onto-shafts` | P2 goes onto ~10 shaft tips at once with tweezers | Stagger tip heights; chamfered lead-ins on the turned tips |
| `press-motor-gear` | Gear placed 5.5 mm above the motor face by measuring | Laser-cut height gauge in `tooling()` |
| `apply-dial-sticker` | Sticker centred by eye | Laser-cut application ring that registers on P2 |
| `ream-tight-gear-bore` | Contingency hand-reaming | Verify SendCutSend hole tolerance on a first article; size `GEAR_FIT` for the worst case |

## Open risks

- Turned-parts quote (D-013); Misumi 26T/5/4 configuration (D-011); Guden hinge sample (D-010).
- X27 shaft length, B3F actuator height, USB-C overmould fit: all assumed.
- Budget targets (60 hand touches, 16 tools) are proposals; the owner should confirm them.

## Follow-ups (dispatchable)

- **F-1** Generate `assembly-ledger.yaml` from the model, from part kinds plus a joint table in
  `design.py`, so it can't drift. Touch: `hardware/cad/`, this file. Test: ledger regenerates byte-identical.
- **F-2** Generate BOM §G from `--tools-table` instead of maintaining it by hand.
- **F-3** Add `build.py --check` and the ledger to `scripts/smoke.*` once `hardware/` is on `main`.
- **F-4** Merge `main` (this kerriganification) into the hardware branch so its agents get
  `hardware/AGENTS.md` and the dfma skill.
