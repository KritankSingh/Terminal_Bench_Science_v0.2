# Engine (reused) vs new layer

This repo is a fresh, lean workspace. The Harbor/stb machinery that already worked in the
v4 workspace is reused as the "engine"; a thin layer on top (`scripts/tbsci.py`) runs it as five
fast steps.

## New layer (written for this repo)

| File | Purpose |
|---|---|
| `scripts/tbsci.py` | the five-step tool: seed, check, review, labels, package, status, selftest |
| `scripts/v02_checks.py` | mechanical client-layer checks (V1–V4, V14) on a task or a zip |
| `scripts/trial_labels.py` | trial labels and band verdict on legitimate outcomes |
| `config/round.toml`, `config/client_rules.toml` | trial model, band, parking; client thresholds and hygiene patterns |
| `docs/V02_RULES.md`, `docs/LESSONS.md`, `docs/CLIENT_CHECKLIST_DIFF.md`, `docs/GPT6_SWITCH.md` | rules, lessons, diff template, model switch inventory |

## Engine (copied from the v4 workspace)

All of `scripts/*.py` and `scripts/*.sh` except the three new files above, the bundled auditor
`tools/final-tbsci-audit-master/` (without its old `audit/` history and `Inbox/`),
`authoring/_templates/` (Step 2a records), `prompts/step1..4.md`, `commands.md`, and the reference
docs the scripts read at run time: `docs/TASK_TAXONOMY.md`, `docs/TASK_COMPONENTS.md`,
`docs/TESTING_POLICY.md`, `docs/TBSCI_HARDENING_RULES.md`, `docs/reference/stb-full-fidelity-kit/`.

Reference docs the stage prompts point to were moved under `docs/reference/` (delivery and package
rules, quality guidelines, Dockerfile practice, review blockers, QC rubric, idea validation,
capability hardening, difficulty guidance, the old Step 2b construction rules). Their links were
repointed; their content is unchanged. The v4 workspace's long process docs
(AUTHORING_WORKFLOW, TBSCI_REVAMP, CI_CHECKS_REVIEW, the TB4 archive) and the `.cursor` skills are
not carried; `docs/WORKFLOW.md` and `.cursor/rules/00-tbsci-workflow.mdc` replace them.

Edits made to engine files (everything else is byte-identical to the v4 workspace):

| File | Edit |
|---|---|
| `scripts/doctor.py` | required-files list: dropped five long docs this repo no longer carries; added the new layer's files |
| `scripts/tbsci_doctor.py` | same, for its doc list |
| `scripts/run_step3c_eval.sh` | parking guard: exits 3 unless `config/round.toml` status is CONFIRMED |
| `prompts/step2b.md`, `prompts/step3b.md`, `prompts/step3c.md` | rewritten or prefixed for the five-step flow (old step2b kept as `docs/reference/step2b-construction-rules.md`) |
| prompts, `commands.md`, engine docs | links repointed to `docs/reference/` (text otherwise unchanged) |

Not done yet (on purpose): the engine still hard-codes GPT-5.6 / xhigh; see docs/GPT6_SWITCH.md.

`MASTER_CHECKLIST_TBSCI.md` is version 4, byte-identical to the v4 workspace, md5 in
`FROZEN.md5`; `tbsci.py selftest` fails if it changes.
