# TB-Science task workflow (lean)

A workspace for building Terminal-Bench-Science style tasks for private delivery to a client
(no upstream submission). Five steps, one command each. Task creation target: about 2–3 hours
(estimate, not measured). Trials can take their 8 hours; that is separate.

- `MASTER_CHECKLIST_TBSCI.md` **version 4 is the source of truth, frozen** (md5 in `FROZEN.md5`).
- Scripts answer every mechanical master check in one run; one 16-point review card answers the
  judgment checks. No per-artifact sealing, no re-walks.
- **Client rules for v0.2** (V1–V20, `docs/V02_RULES.md`) sit on top of the master and never weaken it.
- **Trials are parked** until the client confirms its checklist and model (GPT-6 planned).

## The five steps

| Step | Command | You write | Time (estimate) |
|---|---|---|---|
| 1 Seed | `python3 scripts/tbsci.py seed <slug>` | `authoring/<slug>/seed.md` (one page) | 15–20 min |
| 2 Build | — | `tasks/<slug>/*` + `authoring/<slug>/calibration.md`, `write-ups.md` | 60–90 min |
| 3 Check | `python3 scripts/tbsci.py check <slug>` | nothing; fix what it reports | 20–40 min |
| 4 Review | `python3 scripts/tbsci.py review <slug>` | `authoring/<slug>/review.md` (16 points) | 20–30 min |
| 5 Trials + package | `tbsci.py labels <slug>`, `tbsci.py package <slug>` | `authoring/<slug>/trials.md` (5 rows) | trials: up to 8 h |

Details: `docs/WORKFLOW.md` (one page). Rules: `AGENTS.md` (one page).

## Quick start

```bash
uv venv --python 3.12 .venv && source .venv/bin/activate
python3 scripts/tbsci.py selftest            # the workflow checks itself (no Docker needed)
python3 scripts/doctor.py --strict-tools     # Docker, Harbor, stb for the Docker stage and trials

python3 scripts/tbsci.py seed my-task         # creates the seed card; fill it; run again
python3 scripts/tbsci.py status my-task
```

Toolchain details (uv, Docker, Harbor, stb) are in `commands.md`.

## Layout

| Path | What |
|---|---|
| `MASTER_CHECKLIST_TBSCI.md`, `FROZEN.md5` | the frozen source of truth |
| `scripts/tbsci.py` | the five-step tool |
| `scripts/v02_checks.py`, `scripts/trial_labels.py` | client-rule checks, trial labels |
| `config/round.toml` | trial model, band 0–3/5, `status = PARKED/CONFIRMED` |
| `config/client_rules.toml` | min tests (10), margins, hygiene patterns |
| `docs/WORKFLOW.md`, `docs/V02_RULES.md`, `docs/LESSONS.md` | how, what the client checks, what went wrong before |
| `scripts/*` (rest), `tools/final-tbsci-audit-master/` | the engine reused from v4 (`docs/ENGINE.md`) |
| `prompts/step1..4.md`, `docs/reference/` | long reference; open only when stuck |
| `authoring/<slug>/`, `tasks/<slug>/`, `specs/` | your work (git-ignored) |

## When the client's v0.2 checklist arrives

Fill `docs/CLIENT_CHECKLIST_DIFF.md`, close every gap, apply `docs/GPT6_SWITCH.md`, run the
selftest, then set `status = "CONFIRMED"` in `config/round.toml`.
