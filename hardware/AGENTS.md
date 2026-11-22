# hardware/AGENTS.md: CAD, PCB and assembly work

> The closest AGENTS.md wins. Read this before touching `hardware/`. Root rules still apply ([../AGENTS.md](../AGENTS.md)).
> Preload the **[dfma](../.github/skills/dfma/SKILL.md)** skill and follow
> [playbooks/hardware-product.md](../playbooks/hardware-product.md).

## The job

Produce a kit that **this owner** can assemble, not just a model that passes interference checks.
The builder profile is in [`specs/projects/brass-alethiometer/spec.md`](../specs/projects/brass-alethiometer/spec.md#builder-profile):
a novice who can't cut or position precisely. Every change is judged on two axes: does it fit,
and does it add or remove hand work?

## Before you change a part

1. **Read the settled decisions** in [`decisions.md`](../specs/projects/brass-alethiometer/decisions.md). Don't reopen one without new information.
2. **Check [`supplier-facts.md`](../specs/projects/brass-alethiometer/supplier-facts.md)** before you propose a process, thickness or bought part. Add each new fact with its source and date.
3. **Climb the sourcing ladder from the bottom:** eliminate the part, buy it stock, buy it configured, have it made precise, have it made plus a fixture, and only then hand work (dfma §2). Snap parameters to purchasable values.

## While you change it

- **Precision goes in the part.** No step may say "measure", "at X mm" or "align by eye". Use a shoulder,
  flange, stop or slot, or ship a fixture in `tooling()`.
- **Every part is complete:** source, retention, connection, step and tool, *all modelled*. That
  includes screws, nuts, glue joints, wire runs and the real PCB in the viewer.
- **Apply features uniformly** across like parts, or give the reason in a comment.
- **One agent edits `cad/design.py` at a time.** Parallel workers (firmware, API, viewer, dial) read committed revisions only.

## Before you hand back

- `python cad/build.py --check` is green (interference + manufacturability).
- `python -m pytest cad` is green. When the owner reports a problem, add an assertion that would have caught it.
- [`assembly-ledger.yaml`](../specs/projects/brass-alethiometer/assembly-ledger.yaml) is updated for any changed step, set `reflects.ref`, then run
  `python tools/validators/check_assembly_ledger.py` from the repo root.
- `ASSEMBLY.md`, `BOM.md` (including §G tools) and `SETUP.md` match the model. Regenerate the viewer and say so.
- Report in hand-work terms: operations added or removed, ledger violations cleared, cost delta.
  Ask decision questions per dfma §7, with options in hand-work terms and a recommendation.

**Ready to order** additionally needs `check_assembly_ledger.py --strict` to pass, and the owner's direction sign-off on renders and the viewer.

## Environment (Windows-first; see `SETUP.md` for macOS)

- Run CAD scripts from `hardware/cad` with `$env:PYTHONIOENCODING="utf-8"`. When you edit files
  from scripts, write UTF-8 with `\n` (Windows PowerShell 5.1 `Set-Content` mangles UTF-8).
- Time costs: `build.py --check` ~2 min, full build ~6–7 min, tests 1–8 min. Run the full build in the background and post a one-line status first.
- KiCad 10: `%LOCALAPPDATA%\Programs\KiCad\10.0\bin\python.exe` and `kicad-cli` in the same folder. Freerouting 1.9.0 jar via Java 17 (the 2.5 CLI crashed).
- PlatformIO: `$env:PLATFORMIO_CORE_DIR="C:\pio"`, then `pio run` in `firmware/`.
- Myth Made art is **local only** (`dial/local/`, git-ignored). This repo is public.
