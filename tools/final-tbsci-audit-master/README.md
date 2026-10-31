# final-tbsci-audit-master

Single-flow, single-task auditor for **Terminal-Bench Science** (TB-Science) task
bundles — the Harbor separate-verifier format, in the task shape of
`harbor-framework/terminal-bench-science` as adopted by this workspace. `SKILL.md` is the procedure, `CHECKLIST.md`
holds the gates, `scripts/` holds the quantitative legs. Nothing here authors or
fixes a task.

**Authority order (default `terminus` profile):**
`reference/MASTER_CHECKLIST_TBSCI.md` (a copy of the repo-root
`MASTER_CHECKLIST_TBSCI.md`, the single source of truth, checks numbered 0–107 —
Section J, #98–#107, holds the TB-Science science/format checks) >
`reference/DELIVERY_CHECKLIST.md` > everything else in this tool. Where any gate,
script message or calibration note here disagrees with the master, the master
wins. `CHECKLIST.md` maps every gate to the "Master #N" check it enforces, and
every screen finding carries its master number in a `master` field.

```
tbsci-task-auditor/
├── Inbox/ extracted/ audit/   staging folders (contents are gitignored)
├── reference/
│   ├── MASTER_CHECKLIST_TBSCI.md  THE top authority (copy of the repo-root master, checks 0–107)
│   ├── DELIVERY_CHECKLIST.md      the delivery-format view of the master (gate T); subordinate to it
│   └── TAXONOMY.md                the 5 TB-Science domains, their 20 fields, and the fit questions
├── SKILL.md              procedure, the terminus package standard, calibration (do-not-flag list), output shape
├── CHECKLIST.md          gate T (package standard) + gates A–K, each mapped to its Master #N, plus the master coverage map
├── VERSION_DELTAS.md     calibration history: TB 2.1 → 3.0 (Terminus 3) → Terminal-Bench 4.0, removals, fix families, flipped rules, sources; then the TB-Science deltas
└── scripts/
    ├── review.sh              extract | audit | lint | report | all  (Inbox → extracted → audit)
    ├── audit_run.py           runs the three legs, writes the evidence files + a verdict.json skeleton
    ├── verdict_lint.py        verdict.json vs the SKILL.md contract; derives the closing line
    ├── report_render.py       verdict.json → report.md (refuses while lint has errors)
    ├── tbsci_static_screen.py   one delivery package (dir or .zip) → JSON flags (each with its Master #N) + leads + bundle sha
    ├── trial_evidence.py      trajectories/ + oracle-nop-evidence/ → required round, oracle/NOP quorum, truncation, pass@1, measured k/5 rate, bundle-sha check
    └── ctrf_summary.py        ctrf.json → per-test validity, passed/total, NOP-passing names, shipped-suite diff
```

## Inside the authoring workspace

This is the only auditor in the workspace (`tools/final-tbsci-audit-master/`), and the
workspace builds every task to clear it — not only at the end:

| Stage | Command (from the repo root) | Must be |
|---|---|---|
| Step 2b gate, step (c1), and any time while building | `python3 scripts/audit_task.py tree tasks/<task>` — this screen on the task staged in delivery layout | zero BLOCKER/MAJOR/MINOR (only "no packaged evidence yet" is excused); LEADs go to Step 3b |
| Step 3b | `python3 scripts/master_checklist.py auto tasks/<task>` lists the screen's leads under their Master #N; the reviewer walks gates T, A–K here with the master. #1, #2, #15, #40, #53, #57 and #101 stay PENDING with pre-trial evidence; #33 stays PENDING | every lead answered; a lead on a check this step closes is on its master line; a pre-trial lead is the PENDING line's evidence |
| Step 4 record | the post-trial verdicts (#1, #2, #15, #33, #40, #53, #57, #70, #71–#94, #96, #97, #101, #107) are answered in `authoring/<task>/master-checklist.md`, each citing the packaged runs or oracle/NOP record | `master_checklist.py check --stage package` PASS |
| Step 4 build | `python3 scripts/package_task.py tasks/<task> --step3c-dir <round>` → candidate `artifacts/package-candidates/<task>/<task>.zip`, checked by `verify_package.py` and `audit_task.py package` (screen + `trial_evidence.py`) | zero findings, zero trial flags |
| Step 4 review | `review.sh extract <candidate>` → `review.sh audit <task>` → judge per `SKILL.md` → `review.sh lint <task>` | `LINT_OK  ✅ Ready to Submit  (0 warning(s))` |
| Step 4 promote | `python3 scripts/package_task.py tasks/<task> --promote` (runs `audit_task.py verdict`) | the review is of these exact bytes, verdict `ready`, nothing moved since the build |

Only a promoted ZIP (`Task_Ready_To_Submit/<task>.zip`) is a deliverable. (The
directory keeps its historical name; tasks here are for private delivery and nothing is
submitted upstream.)

## Quick start (needs Python 3.11+)

```bash
cp my-task.zip Inbox/
./scripts/review.sh extract && ./scripts/review.sh audit my-task     # → audit/my-task/<ts>/
#   read the task; fill audit/my-task/latest/manual_probes.txt and verdict.json (replace every PENDING)
./scripts/review.sh lint my-task && ./scripts/review.sh report my-task   # → report.md + closing line
```

See `SKILL.md` → *Workflow folders and commands* for what `lint` enforces.

## Profiles

**`--profile terminus` (the default)** — the program delivery standard, defined by
`reference/MASTER_CHECKLIST_TBSCI.md` (top authority) and its delivery-format view
`reference/DELIVERY_CHECKLIST.md` (gate T traces to both). The zip's single
top-level member is `<task-slug>/`, holding four siblings:

```
<task-slug>/
├── <task-slug>/            ONLY instruction.md, task.toml,
│                           environment/, solution/, tests/
├── rubric.txt
├── oracle-nop-evidence/    oracle-1..3 (reward 1.0, every test passing)
│                           nop-1..2    (reward 0.0, every test failing)
└── trajectories/           run-01..run-05 (agent/, verifier/, config.json,
                            result.json, rubric_score.txt) + SUMMARY.txt
```

`SOURCE.txt`, `rubrics.txt`, `.git`, `__pycache__`, `*.pyc`, `.DS_Store`,
`__MACOSX`, `._*` and canary strings are **rejected anywhere in the zip**
(`T3-BANNED`, `T3-CANARY`). The task carries **no** `README.md` (`T3-README`,
Master #103, 2026-10-07): the three write-ups (`## Difficulty`,
`## Reference solution`, `## Verification`) are the workspace record
`authoring/<task>/write-ups.md`, which never ships and is read as supplied
evidence for #100–#102; the `*_explanation` keys in `task.toml` are rejected
(`T3-WRITEUP`). `[metadata]` carries `domain` / `field` / `subfield` from the
official TB-Science taxonomy (`TOML-04`, `TOML-05` — Master #61, #98) plus `tags`
(3–6), `expert_time_estimate_hours` and `relevant_experience`; the retired TB4
`category` / `subcategory` / `languages` keys are `T3-RESIDUE`. Author fields are
optional, non-empty when present (`TOML-04`, `T3-AUTHOR`). `name` is the directory
slug — kebab-case, a name not a sentence (`SLUG-01`, `SLUG-02`; 2–4 tokens typical, Master #61) — and carries no
`hardened`/`harden`-style suffix or internal codename (checked in the shipped
trajectory JSON too); `schema_version` is optional, but a top-level `version`
(`T3-SCHEMA`) and other stale-schema residue are findings (Master #65), and there is
**no `difficulty` field** — no tier label, percentage or pass-count anywhere in the
task (Master #62); `[agent].timeout_sec`, `[verifier].timeout_sec`
and `[environment].build_timeout_sec` are all exactly 28800 on every task, from
creation (Master #63), and `instruction.md` ends with the matching
`You have 28800 seconds to complete this task. Do not cheat by using online
solutions or hints specific to this task.` paragraph (`INSTR-01`, Master #104);
the network policy is declared on both phases — agent `[environment].network_mode =
"public"`, verifier `[verifier.environment].network_mode = "no-network"` (or a
justified allowlist) (`T3-NET`, Master #64); `gpus` is 0 (`T3-GPU`);
`reasoning_effort` is present and exactly `xhigh` in every `run-0N/config.json`
(Master #91); `SUMMARY.txt`'s `sha=` is the bundle sha recomputed from inside the
inner task folder (Master #80); every image is digest-pinned; `tmux` + `asciinema`
go in the final agent image only; the verifier seal (Master #54–#56, the master's
Appendix A): agent code runs as `setpriv --reuid=12000 … env -i … timeout -k <PER_RUN_LIMIT>`
behind a root-only `/tests` and root-owned `/work`, escaping artifact symlinks are
deleted before grading, and the reward is written last after kill-to-exhaustion;
wall-clock thresholds must not
reach the reward. The upstream conventions this inverts (canary, `[task] name`,
`allow_internet`, the pytest/CTRF version pins, `rubric.txt` / `trajectories/` as
extraneous) are **dropped**, not downgraded to INFO.

**`--profile upstream`** — the `harbor-framework/terminal-bench-science` PR
conventions count instead (canary required, `[task] name =
"terminal-bench-science/<slug>"`, `allow_internet` in either polarity rejected,
the pytest / CTRF version pins, `rubric.txt` / `trajectories/` extraneous), and the
`T3-*` rules do not apply. This workspace never opens such a PR (private delivery);
the profile is kept for comparison only. The instruction suffix, kebab-case slug
and the domain/field taxonomy apply under **both** profiles; upstream's required
README.md (`STRUCT-README`, `README-01..04`, the `PROV-01` / `PROV-02` / `TOL-01`
leads) applies under `upstream` only.

See `SKILL.md` → Profiles and `CHECKLIST.md` → gate T.

## One flow

```bash
A=/path/to/tbsci-task-auditor/scripts
T=/path/to/<task-slug>     # the DELIVERY ROOT (parent of the inner task folder) or the submission .zip

python3 $A/tbsci_static_screen.py --task $T --pretty                 # 1. screen (exit 2 = BLOCK); prints the bundle sha
#   … read every file (SKILL.md step 2), walk CHECKLIST.md T→K and the master coverage map, answer every LEAD …
python3 $A/trial_evidence.py --runs $T/trajectories $T/oracle-nop-evidence \
        --task $T/<task-slug> --pretty                             # 9. oracle x3 N/N, NOP x2 0/N, the GPT-5.6 xhigh x5
                                                                   #    round, truncation, pass@1, measured k/5 rate, bundle sha

# Master #80 by hand — must equal SUMMARY.txt's sha= and the screen's bundle_sha:
( cd $T/<task-slug> && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum )
python3 $A/ctrf_summary.py $T/oracle-nop-evidence/nop-1/ctrf.json    --task $T/<task-slug> --expect nop     # per-test zero
python3 $A/ctrf_summary.py $T/oracle-nop-evidence/oracle-1/ctrf.json --task $T/<task-slug> --expect oracle  # N/N
```

Then produce the JSON verdict block from `SKILL.md` and its closing line.

**A clean screen is never "Ready to Submit".** Readiness additionally requires
valid package evidence (`rubric.txt`, `run-01..run-05` with `SUMMARY.txt` and a
`rubric_score.txt` per run, and `oracle-nop-evidence/` at oracle x3 / NOP x2), a
`SUMMARY.txt` `sha=` equal to the bundle sha the screen recomputes over the inner
task folder (Master #80) with evidence bound to the shipped digests (Master #75),
and every master check answered with evidence — zero BLOCKER, zero MAJOR, zero
MINOR (the master ships nothing with an open finding). The screen's `task_digest`
is a separate internal binding for the audit run itself, not the SUMMARY sha.

Nothing in this workspace is opened as a PR, and AGENTS.md forbids `harbor check`.
For comparison only: upstream TB-Science runs its `ci_checks/check-*.sh` static
checks, an LLM review against the 39 criteria of `rubrics/task-implementation.toml`
(`harbor check`), oracle / nop validation, and `harbor analyze` against the eight
criteria of `rubrics/trial-analysis.toml`. Every one of those files has a recorded
decision in the workspace's `docs/CI_CHECKS_REVIEW.md`; the adopted criteria are
folded into the master (Section J) and judged by reading, not run.

## What the scripts decide vs. what you decide

Scripts decide mechanical facts: `task.toml` residue (`version`, `difficulty`,
`[task]`, milestones, `*_min`, retired `category`/`subcategory`/`languages`, local
paths — Master #62/#65), the taxonomy values (#61/#98), timeouts (#63), the
instruction suffix (#104), the two-phase network policy (#64), no README.md
in the task (#103), `artifacts` placement and landing dirs, pins, bare `nproc` and
host binds (#106),
tooling baked, trial-time fetches, CTRF, reward shape, privilege drop, ctrf test
counts (#53), per-row Oracle/NOP statuses (#72/#73), NOP setup errors (#74),
evidence freshness (#75), duplicated controls or runs (#76/#83), SUMMARY
lines, rewards and bundle sha (#77/#79/#80), rubric_score shape, evidence
citations and pairwise distinctness (#78/#85/#86), per-directory PII/`stb`/canary
greps (#87/#97), agent/verifier file sets (#90), `reasoning_effort` (#91),
`exception_info` (#92), a reward-hack command scan (#93), pass rates and
saturation. Everything that sends a TB-Science task
back in practice is a reading job: where every expected value comes from,
what the executed agent code can read at grade time, whether a hand-written
artifact would pass, whether every assertion is licensed by something the agent
can read, whether every "do not modify" is enforced, whether thresholds are
calibrated and justified by the science (#101), whether the graded instances
defeat trivial nulls (#102), whether the data and ground truth have recorded
provenance (#100), whether the difficulty is essential, whether the task is
genuinely research-level work in its declared field (#98, #99), and whether it is
solvable by lookup on the open internet. The screen narrows what to read and
emits those questions as `LEAD`s; it never replaces reading.

Calibration: the terminus profile was first calibrated, before the 2026-10-06
TB-Science revamp, against a fixture built to the then master checklist exactly
(clean: 0 findings, 4 leads, SUMMARY sha equal to the shell recompute) and mutated
one rule at a time — a `[metadata].difficulty` (T3-DIFFICULTY), a pass-count in
the difficulty write-up, a 5400 s timeout, a `[task]` table / `*_min` field / host
`/home/<user>` path / `is_multi_container = false` / `artifacts` under
`[verifier]`, an agent-phase `no-network`, a wrong SUMMARY sha or reward, a tests/ edit after
capture (bundle sha, mtime and test-count findings), a NOP row with status `error`
and an `ERROR at setup` line, a copied oracle directory, a copied
`rubric_score.txt` and a verdict without evidence, `/Users/` and `stb` in one run
and one control, a missing `recording.cast`, `reasoning_effort=high`, a populated
`exception_info`, a `cat /tests/test_outputs.py` tool call, `set -e` without a
final `exit 0`, "the verifier" in the instruction, and the clean fixture shipped as
a `.zip` (mtimes restored from the archive) — each caught by its own rule. Two
mutations of that set are no longer findings under TB-Science: a `schema_version`
line (optional, Master #65) and `anonymous@example.com` (author fields optional,
Master #61). The TB-Science rules (README.md sections, the instruction suffix, the
two-phase network policy, domain/field/subfield, bare `nproc`, host binds) were
added to the screen at the revamp; on 2026-10-07 the README.md requirement was
reversed (a README.md in the task is now `T3-README`; the section checks run under
`upstream` only). This file records no separate recalibration run for them.

The upstream profile was run, before the revamp, over all 66 tasks shipped in
Terminal-Bench 4.0 (v4.0.0) against the Terminal-Bench 4.0 conventions. It passed
or MINORed 45 of them; the 21 it blocked were all on criteria the rubric stated
explicitly (`verifier_execution_isolation` on tasks merged before that criterion
existed, a trial-time `apt-get`, a vendored tree without canaries, a missing
`--ctrf`). Those tasks are NOT calibration for the terminus profile — they are
packaged to the upstream standard, so they trip the package rules by
construction — and the profile now targets the TB-Science conventions, so that
run is history, not a current baseline.

## Sources folded in

- `harbor-framework/terminal-bench-science` (read at commit `4c55d75`,
  2026-10-05): `CONTRIBUTING.md`, `task-template.toml`,
  `task-readme-template.md`, `REVIEWING.md`, `rubrics/task-implementation.toml`
  (39 criteria), `rubrics/trial-analysis.toml` (8 criteria),
  `rubrics/task-proposal.md`, `.github/hack-trial-prompt.md` and every
  `ci_checks/check-*` file — paraphrased and cited, never vendored (decisions in
  the workspace's `docs/TBSCI_REVAMP.md` and `docs/CI_CHECKS_REVIEW.md`).
- Terminal-Bench 4.0 calibration history — `harbor-framework/terminal-bench`
  (main, 2026-09): `CONTRIBUTING.md`, `docs/prompts/task-implementation.toml`
  (35 criteria), `task-proposal.md`, `trial-analysis.toml`,
  `hack-trial-prompt.md`, `TASK_REVIEW_AUTOMATION.md` (every `check-*.sh`),
  `REVIEWING.md`, `TAXONOMY.md`, `task-template.toml`,
  `.github/harbor-run-defaults.yml`; the v4.0.0 release notes, the eight
  removal PRs and the nineteen per-task change logs (`VERSION_DELTAS.md`).
- Terminus 3 docs and `TASK_QUALITY_SSOT.md` (TB 2.1): every defect family that
  survives the separate-verifier / open-internet model, with the reversals
  called out in `VERSION_DELTAS.md` §4.
- Discussion #224 "What Makes a Good Terminal Bench Task" and Snorkel's
  "Terminal-Bench 4.0: Why Continuous Benchmarks Require Continuous QA".
