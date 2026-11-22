# Constitution: The Alethiometer

Non-negotiable principles for all work in this repo. They build on
[Kerrigan's constitution](https://github.com/Kixantrix/kerrigan/blob/main/specs/constitution.md).

## 1) One oracle, three faces
The website, the API and the instrument share one symbol set, one order and one reading
format. A change to any of them updates all of them in the same PR.

## 2) Small, reviewable increments
One task, one branch, one PR. Keep CI green. Split large changes into milestones.

## 3) Artifact-driven
Specs, plans, decisions, supplier facts and the assembly ledger live in `specs/projects/`. If it
isn't written down, it doesn't exist. This matters most across long sessions and computers.

## 4) Tests are part of the feature
Every AC maps to an automated test or an attested scenario. When the owner reports a problem, the
fix includes an assertion that would have caught it.

## 5) Design for the builder (physical work)
- Write the builder profile down and design to it. The current builder can't cut or position precisely.
- Take the lowest rung of the sourcing ladder that works: eliminate, buy stock, buy configured, fab-precise, fab plus fixture, and only then hand work.
- Precision lives in the part or a supplied fixture, never in the builder's hands.
- Fewer, more uniform parts. Every custom part, fastener type and tool needs a reason.
- Every part has a source, retention, connection, step and tool, and all of them are modelled.
- `check_assembly_ledger.py --strict` passes before anything is ordered.

## 6) Human decides direction; agents own quality
The owner approves direction from renders, the viewer and hand-work-framed options. Technical
correctness is the agent's and CI's job.

## 7) Public by default, safe by default
Secrets stay in app settings, never in the repo. Third-party art that isn't redistributable stays local.
