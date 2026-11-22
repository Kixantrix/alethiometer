# AGENTS.md

> Canonical entry point for every AI agent in this repo. Harness: [Kerrigan](https://github.com/Kixantrix/kerrigan) v2.
> Read this file first, then the closest nested `AGENTS.md` (e.g. [`hardware/AGENTS.md`](hardware/AGENTS.md)).

## What this repo is

**The Alethiometer.** It has two products that share one oracle:

| Product | Where | Stack |
|---|---|---|
| Website (live on GitHub Pages) | `index.html`, `js/`, `css/` | Vanilla HTML/CSS/JS, no build step |
| Oracle API | `api/` | Azure Functions (Node 24, ESM), Azure OpenAI |
| Brass instrument | `hardware/`, `firmware/` (on `kixantrix-brass-alethiometer-hardware` until merged) | CadQuery, KiCad, PlatformIO ESP32-S3 |

The 36 symbols and their order are shared across `js/symbols.js`, `api/src/symbols.js`,
`firmware/src/symbols.h` and the dial. Change them together.

## Agent profiles

| When you want to | Talk to | Profile |
|---|---|---|
| Plan, decide, dispatch, maintain the harness | `kerrigan` | [`.github/agents/kerrigan.md`](.github/agents/kerrigan.md) |
| Implement one task slice | `cloud` | [`.github/agents/cloud.md`](.github/agents/cloud.md) |

Skills: [`.github/skills/`](.github/skills/). Locked set: [`.specify/skills.yaml`](.specify/skills.yaml).

## Principles

See [`specs/constitution.md`](specs/constitution.md). In short: artifact-driven, small PRs, tests
for every AC, human decides direction. **For physical work, design for manufacture and
assembly comes first:** see the [`dfma`](.github/skills/dfma/SKILL.md) skill.

## Projects

| Project | Artifacts |
|---|---|
| Brass alethiometer | [`specs/projects/brass-alethiometer/`](specs/projects/brass-alethiometer/): spec (with builder profile), plan, decisions, supplier facts, assembly ledger |

## Commands

```powershell
pwsh scripts/smoke.ps1                                   # or: bash scripts/smoke.sh
python tools/validators/agents_md.py                      # agent profiles + skills frontmatter
python tools/validators/check_assembly_ledger.py          # hand-work ledger vs builder profile
python tools/validators/check_assembly_ledger.py --strict # ready-to-order gate
```

Validators need PyYAML (`pip install -r tools/requirements.txt`).

## Conventions

- **Public repo.** No secrets, and no third-party art (Myth Made symbols are generated locally into git-ignored folders).
- **Decisions are recorded** in the project's `decisions.md` with the owner's words. Don't reopen settled ones.
- **Blocks:** write `.specify/blocks/<task-id>.yaml` ([block-report](.github/skills/block-report/SKILL.md)) and stop.
- **Labels:** `agent:go`, `agent:wait`, `agent:local`, `autonomy:override` (annotations only).
- Hardware tasks touching ordering, physical fit-up or KiCad/Freerouting are `agent:local` / `manual-human` ([delegation-rubric](.github/skills/delegation-rubric/SKILL.md)).
