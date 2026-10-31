# commands.md — Terminal-Bench Science

Authoritative CLI patterns for this repo. Run everything from the repository
root with `<task-name>` replaced literally. Oracle/NOP and negative controls
run on the local `harbor` CLI (installed alongside `stb`); **`stb`** is used
only for the GPT-5.6 model trials in Step 3c (the optional Step 3a hinted
diagnostic is a local `harbor run` with your own agent credentials and never counts). There is no `harbor check`
LLM-judge step. Do not invent flags — run `<script> --help`, `harbor run --help`,
or `stb harbor --help` when unsure.

`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth for what a task must
pass; the commands below are how this workspace enforces it. Tasks are for
private delivery to a buyer: nothing is submitted upstream, to a portal or to a hub
(`Task_Ready_To_Submit/` keeps its name because every script uses it).
The active workflow is defined by the master and `docs/WORKFLOW.md` (`scripts/tbsci.py`).

## Toolchain install

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install snorkelai-stb \
  --find-links https://snorkel-python-wheels.s3.us-west-2.amazonaws.com/stb/index.html \
  --python ">=3.12"

stb --version                        # 2.4.16 or newer (bundles Harbor 0.23.0)
harbor --version                     # 0.23.0 — local Harbor for Oracle/NOP gates (uv tool install harbor==0.23.0)
stb login                            # only needed before Step 3c model trials
python3 scripts/stb_key_guard.py status   # key usable? NEVER run `stb keys refresh` by hand: keys carry a $10 budget,
                                     # the account has 20 refreshes, and a refresh revokes the key other rounds are using;
                                     # run_step3c_eval.sh refreshes only when the budget is exhausted (stb_key_guard.py ensure)
python3 scripts/patch_stb_harbor.py  # full-fidelity capture in the stb-bundled harbor; ends "stb-bundled harbor patch: PASS"; re-run after every stb install, upgrade or reinstall
python3 scripts/patch_stb_harbor.py --check        # verify only (run_step3c_eval.sh repeats it before every model attempt)
python3 scripts/prune_evidence.py all              # dry run: stale/void gate payloads and rounds that would be deleted
#   (deletion runs on its own: gate_step2b.sh after a PASS verdict, run_step3c_eval.sh after
#    fidelity PASS, regrade_step3c.py run after a PASS; log: artifacts/prune-log/<date>.log)
python3 scripts/patch_stb_harbor.py --check-agent  # the Step 3c --ak set validates through Harbor 0.23 preflight
```

Docker Desktop/engine must be running. On this WSL host: `docker context use default`
(see `.cursor/rules/wsl-native-docker.mdc`).

## Preflight (every new shell)

```bash
source .venv/bin/activate            # Python 3.11+; see README "Start here"
docker context use default
python3 scripts/doctor.py --strict-tools
```

`stb` is not required for anything before Step 3c.

## Interactive environment

```bash
harbor tasks start-env -p tasks/<task-name> -i
# inside container: explore, dry-run solution steps, exit
```

## Step 2a — contract lock

Write `specs/<task-name>.md` and `authoring/<task-name>/{contract,
traceability,threat-model,resource-plan,controls}.md` from the templates. Step 1
is optional; whichever step you start at, copy the templates once:

```bash
cp -r authoring/_templates authoring/<task-name>
mkdir -p authoring/<task-name>/provenance authoring/<task-name>/evidence   # data origin records (Master #100), cross-checks (#101)
# fill authoring/<task-name>/write-ups.md (copied above; Master #103): workspace only, never shipped; the task carries no README.md
# optional, for a Step 3a hinted diagnostic only: authoring/<task-name>/hint.md (never in tasks/)
```

The `controls.md` plan table must name manifest cases; see `prompts/step2a.md`.

## Step 2b — construct and gate

Static checks while building:

```bash
python3 scripts/task_check.py tasks/<task-name> --strict   # structural + manifest + hardening; warns on controls.md cases not in the manifest
python3 scripts/hardening_check.py tasks/<task-name>        # hardening rules only
python3 scripts/task_digest.py tasks/<task-name>            # canonical digest for every report
python3 scripts/master_checklist.py init tasks/<task-name>  # once: authoring/<task-name>/master-checklist.md, one line per master check
python3 scripts/audit_task.py tree tasks/<task-name>        # the bundled TB-Science auditor on the task in delivery layout; must PASS (needs rubric.txt)
python3 scripts/master_checklist.py auto tasks/<task-name>  # static + auditor findings grouped by Master #N, and the leads to answer
python3 scripts/bundle_sha.py tasks/<task-name>             # the sha SUMMARY.txt will carry (Master #80)
```

Local loop until reward 1 (no Harbor job before this passes):

```bash
scripts/dev_verify.sh tasks/<task-name>
scripts/dev_verify.sh tasks/<task-name> --keep-image --extra 'cat /logs/verifier/ctrf.json'
```

Negative controls: generate the task-agnostic scripts, author the rest, fill
the plan table:

```bash
python3 scripts/nc_generate.py tasks/<task-name>            # --out authoring/<task-name>/staged_controls, --force to overwrite
cat authoring/<task-name>/staged_controls/README.md
```

The gate (detaches; default OUT `authoring/<task-name>/evidence/step2b-<stamp>`):

```bash
scripts/gate_step2b.sh tasks/<task-name>
tail -f authoring/<task-name>/evidence/step2b-*/progress     # last line: VERDICT: PASS|FAIL
```

Options: `--out <dir>`, `--skip-nc` (stop after the seal), `--nc-only`
(controls against the existing seal), `--foreground`. The gate runs
`doctor.py --strict-tools` → `task_check.py --strict` → `hardening_check.py`
→ `audit_task.py tree` (blocking) → `master_checklist.py auto` (informational) → `task_digest.py` → `dev_verify.sh` → `per_test_gate.py` (one local
`harbor` job per test and agent, selector injected with
`--verifier-env TBENCH_TEST_ID=<id>`) → `evidence.py seal` →
`stage_controls.sh` + one local `harbor` job per staged control →
`controls_report.py --write`. Outputs: `artifacts/gates/<task-name>/step2b.json`
and the `## Gate results — <digest>` section of
`authoring/<task-name>/controls.md`.

Pieces the gate calls, for reruns or reading:

```bash
python3 scripts/evidence.py check tasks/<task-name> \
  --evidence artifacts/gates/<task-name>/step2b.json
scripts/stage_controls.sh tasks/<task-name> authoring/<task-name>/evidence/step2b-<stamp>/nc
python3 scripts/controls_report.py --task-dir tasks/<task-name> \
  --evidence authoring/<task-name>/evidence/step2b-<stamp> --write
```

Acceptance and exit phrase (`GATE PASSED — READY FOR PAPER REVIEW`): see
`prompts/step2b.md`. Any behavioral task edit after the seal → full gate again,
fresh OUT. A descriptive-only edit (a descriptive `[metadata]` key such as
`expert_time_estimate_hours`) re-seals instead; editing
`authoring/<task-name>/write-ups.md` touches no task file and needs no re-seal:

```bash
scripts/gate_step2b.sh tasks/<task-name> --reseal-only    # static screen + evidence.py reseal; refuses if a graded digest moved
python3 scripts/stage_reports.py rebind-review tasks/<task-name>
```

## Step 3a — optional diagnostics (never required)

```bash
python3 scripts/evidence.py check tasks/<task-name> \
  --evidence artifacts/gates/<task-name>/step2b.json
python3 scripts/per_test_gate.py tasks/<task-name> \
  --only <test-id> --agents oracle,nop --repeat 3 \
  --output artifacts/gates/<task-name>/diagnostic-<test-id>.json
scripts/gate_step2b.sh tasks/<task-name> --nc-only
scripts/dev_verify.sh tasks/<task-name> --keep-image --extra '<shell snippet>'
```

Hinted diagnostic ("hard or broken?", `prompts/step3a.md`): a staged copy with
its **own slug** and the chosen hints from `authoring/<task-name>/hint.md` pasted
above the instruction's closing timeout paragraph, run on local Harbor with your own
agent credentials — never through `stb`, never counted, never archived.

```bash
H=authoring/<task-name>/hinted/<task-name>-hinted
mkdir -p "$(dirname "$H")" && cp -a tasks/<task-name> "$H" && rm -rf "$H/trajectories" "$H/rubric.txt"
sed -i 's/^name = ".*"/name = "<task-name>-hinted"/' "$H/task.toml"
# edit $H/instruction.md: hints above the final "You have 28800 seconds ..." paragraph
harbor run -p "$H" -a <agent> -m <provider/model>
```

## Step 3b — paper review

Starts as soon as the seal exists (the NC batch may still be running):

```bash
python3 scripts/evidence.py check tasks/<task-name> \
  --evidence artifacts/gates/<task-name>/step2b.json
python3 scripts/task_check.py tasks/<task-name> --strict
```

Then `prompts/step3b.md`: walk the master into the record. The pre-trial
evidence for #1, #2, #15, #40, #53, #57 and #101 goes on those PENDING lines;
those lines, plus #33,
#70, #71–#94, #96, #97, #101 and #107, stay PENDING until Step 4. Then

```bash
python3 scripts/master_checklist.py check tasks/<task-name> --stage review   # PENDING only on the post-trial lines, zero FAIL
```

Write `authoring/<task-name>/step3b-review.md` and
`artifacts/reviews/<task-name>.md` with exactly one `Task:`, `Task digest:`,
and `Verdict:` line each. The verdict line waits for a complete
`## Gate results — <digest>` section.

Header check (what Step 3c and Step 4 run):

```bash
python3 - <<'EOF'
import sys; sys.path.insert(0, "scripts")
from pathlib import Path
from stage_reports import check_stage_report
errors = check_stage_report(Path("tasks/<task-name>"), Path("artifacts/reviews/<task-name>.md"), "review")
print("\n".join(errors) or "Review header: PASS")
raise SystemExit(1 if errors else 0)
EOF
```

## Step 3c — difficulty evaluation

Model attempts run the way they will be judged (STB full-fidelity kit,
`docs/reference/stb-full-fidelity-kit/README.md`): GPT-5.6 at
`reasoning_effort=xhigh`, uncapped observations, every message stored, raw API
log, asciinema recording. A default-effort or capped run is void.

```bash
stb login
python3 scripts/patch_stb_harbor.py                     # once per stb install/upgrade (launcher refuses to start without it)
scripts/run_step3c_eval.sh tasks/<task-name>            # 5x GPT-5.6 @ xhigh via stb + Oracle x3/NOP x2 via local harbor, OUT=./evidence-<task-name>
                                                        # ends with "SUMMARY evidence-<task-name>: x/5 solved; fidelity PASS"
python3 scripts/check_trajectory.py evidence-<task-name>   # re-run the fidelity check on demand
```

A round cut short (key budget exhausted mid-trial, stb refresh quota, infra abort, `exception_info`) is not void:
the five shipped runs are the first five fidelity-complete trials at the digest and
run config in launch order across rounds (Master #94 item 1). Run more attempts in a
fresh OUT, the controls if no source round has them, then compose:

```bash
CONTROLS_ONLY=1 scripts/run_step3c_eval.sh tasks/<task-name>   # Oracle x3/NOP x2 only, local harbor, OUT=./evidence-<task-name>-controls
python3 scripts/compose_step3c.py tasks/<task-name> \
  --source evidence-<task-name>-r1 --source evidence-<task-name>-r2 \
  --controls evidence-<task-name>-controls --out evidence-<task-name>-composed \
  [--reason <trial-id>='<outcome-independent reason>']   # only for an operator stop/unfinished trial inside the first five
# refuses on any digest/run-config mismatch, fewer than 5 valid trials, or an unlisted same-config round;
# writes composition.json (every candidate: start time, validity, selected/excluded + reason) and ends "fidelity PASS".
# archive_step3c.py / audit_step3c.py then take --jobs-dir evidence-<task-name>-composed.
```

```bash
python3 scripts/archive_step3c.py --task-dir tasks/<task-name> \
  --jobs-dir evidence-<task-name>          # hard-linked task-local copy; no zip unless --zip is given
python3 scripts/audit_step3c.py --task-dir tasks/<task-name> --jobs-dir evidence-<task-name>
```

Fixing a verifier defect *after* the round is captured — no model re-runs
(`docs/TBSCI_HARDENING_RULES.md` §8.2). Run `bind` BEFORE touching `tests/`:

```bash
python3 scripts/regrade_step3c.py bind --task-dir tasks/<task-name> \
  --round evidence-<task-name> --seal artifacts/gates/<task-name>/step2b.json
# ... edit tests/ ... then a full gate, because the per-test matrix must re-run:
scripts/gate_step2b.sh tasks/<task-name>
python3 scripts/regrade_step3c.py run --task-dir tasks/<task-name> \
  --record artifacts/regrade/<task-name>/evidence-<task-name>.bind.json \
  --out evidence-regrade-<task-name>       # every captured reward must come back identical
python3 scripts/regrade_step3c.py verify --task-dir tasks/<task-name> \
  --record artifacts/regrade/<task-name>/evidence-<task-name>.regrade.json
# then archive/audit the REGRADE round and re-issue Step 3b; package that round.
# First time on a task, prove the verifier is deterministic before trusting any of it:
#   run with tests/ unchanged and --allow-identical-grader; rewards must be identical.
```

What the launcher runs, one job each (kept so every flag is visible; it also
probes the stb key before every model attempt and refreshes it only when its $10
budget is exhausted (`scripts/stb_key_guard.py`), and writes `SOURCE.txt` + `fidelity-check.log` into `OUT`):

`RecordingTerminus2` is Harbor's legacy upstream agent identifier. It is kept
verbatim for compatibility; it does not name this workspace.

```bash
export TERMINUS_MAX_OUTPUT_BYTES=100000000 TERMINUS_RAW_API_LOG=1
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
unset TBENCH_TEST_ID
stb harbor run -p tasks/<task-name> -a scripts.harbor_recording:RecordingTerminus2 -m '@openai/gpt-5.6' -n 1 --max-retries 0 --ak max_output_bytes=0 --ak reasoning_effort=xhigh --ak store_all_messages=true --job-name <task-name>-gpt56-t1 -o evidence-<task-name>
harbor run -p tasks/<task-name> -a scripts.harbor_recording:RecordingOracle -n 1 --max-retries 0 --job-name oracle-1 -o evidence-<task-name>
harbor run -p tasks/<task-name> -a scripts.harbor_recording:RecordingOracle -n 1 --max-retries 0 --job-name oracle-2 -o evidence-<task-name>
harbor run -p tasks/<task-name> -a scripts.harbor_recording:RecordingOracle -n 1 --max-retries 0 --job-name oracle-3 -o evidence-<task-name>
harbor run -p tasks/<task-name> -a scripts.harbor_recording:RecordingNop    -n 1 --max-retries 0 --job-name nop-1    -o evidence-<task-name>
harbor run -p tasks/<task-name> -a scripts.harbor_recording:RecordingNop    -n 1 --max-retries 0 --job-name nop-2    -o evidence-<task-name>
```

All three Oracle trials must pass every declared case; both NOP trials must
fail every case through a real assertion (Master #40, #72–#74). Controls are reported separately from model pass
rates and do not replace the Step 2b seal. Audit every trajectory per
`prompts/step3c.md`, including the eight trial-analysis criteria of Master #107
for every model trial; only `VALID_PASS`/`VALID_FAIL` enter a defensible rate.
Write `artifacts/difficulty/<task-name>.md` (and the copy in
`authoring/<task-name>/step3c-report.md`) with the `Task:` / `Task digest:` /
`Review SHA256:` / `Evaluation policy:` / `Trial evidence:` / `Verdict:` header.

The measured pass rate across the five GPT-5.6 attempts is recorded in the
difficulty report only — **never written into the task** (`task.toml` has no
`difficulty` field; Master #62). A measured 0/5–3/5 ships. There is no cross-model
(Opus) run and no predeclared-plus-confirmation split in the current gate — every
one of the five GPT attempts counts toward the measured rate equally.

## Step 4 — packaging only (no Oracle rerun)

Write `artifacts/rubric-scores/<task-name>/<step3c-round>/run-01.txt` … `run-05.txt`
(every verdict with a parenthetical citation from that run's own trajectory), walk
the post-trial verdicts (#1, #2, #15, #33, #40, #53, #57, #70, #71–#94, #96,
#97, #101, #107) into the record, then:

```bash
python3 scripts/master_checklist.py check tasks/<task-name> --stage package   # all 108 checks (#0–#107) answered, zero FAIL
python3 scripts/evidence.py check tasks/<task-name> \
  --evidence artifacts/gates/<task-name>/step2b.json
python3 scripts/task_check.py tasks/<task-name> --strict
python3 - <<'EOF'
import sys; sys.path.insert(0, "scripts")
from pathlib import Path
from stage_reports import check_stage_report
task = Path("tasks/<task-name>")
review = Path("artifacts/reviews/<task-name>.md")
errors = check_stage_report(task, review, "review")
errors += check_stage_report(task, Path("artifacts/difficulty/<task-name>.md"), "difficulty", review_path=review)
print("\n".join(errors) or "Stage reports: PASS")
raise SystemExit(1 if errors else 0)
EOF
```

Packaging is **build → audit → promote**. Build the candidate:

```bash
python3 scripts/package_task.py tasks/<task-name> \
  --step3c-dir tasks/<task-name>/trajectories/<step3c-round>
# candidate: artifacts/package-candidates/<task-name>/<task-name>.zip (+ .candidate.json)
python3 scripts/verify_package.py artifacts/package-candidates/<task-name>/<task-name>.zip   # already run by the build
python3 scripts/audit_task.py package artifacts/package-candidates/<task-name>/<task-name>.zip  # already run by the build
```

Audit the candidate exactly as the reviewer will (`tools/final-tbsci-audit-master/SKILL.md`):

```bash
A=tools/final-tbsci-audit-master/scripts
$A/review.sh extract artifacts/package-candidates/<task-name>/<task-name>.zip
$A/review.sh audit <task-name>      # -> tools/final-tbsci-audit-master/audit/<task-name>/<stamp>/
# read every file; walk CHECKLIST.md gates T, A–K; answer every LEAD; run the manual probes
# and cheat simulation; fill verdict.json + manual_probes.txt (no PENDING, no <<UNFILLED>>)
$A/review.sh lint <task-name>       # must print: LINT_OK  ✅ Ready to Submit  (0 warning(s))
$A/review.sh report <task-name>     # report.md
```

Promote the audited bytes:

```bash
python3 scripts/package_task.py tasks/<task-name> --promote
python3 scripts/audit_task.py verdict Task_Ready_To_Submit/<task-name>.zip   # re-check any time
python3 -m zipfile -l Task_Ready_To_Submit/<task-name>.zip
sha256sum Task_Ready_To_Submit/<task-name>.zip
```

The build requires a complete `authoring/<task-name>/master-checklist.md` for the
current digest, `tasks/<task-name>/rubric.txt`, the rubric scores, the complete Step 3c
round named by the difficulty report, and the sealed Step 2b per-test Oracle/NOP jobs.
It refuses mismatched digests, altered evidence, incomplete trial counts, stale reports
and symlinks. The ZIP is laid out per `docs/reference/DELIVERY_CHECKLIST.md`:
`<task-name>/<task-name>/` (the five task members: `instruction.md`, `task.toml`,
`environment/`, `solution/`, `tests/`; no README.md) beside `rubric.txt`,
`oracle-nop-evidence/` and `trajectories/` (run-01..05 + SUMMARY.txt). It rewrites host
paths in each run's `config.json`/`result.json`, writes SUMMARY.txt with the bundle sha,
and runs `verify_package.py` and the auditor legs on the candidate, deleting it on any
finding. Rebuilding replaces the candidate, and an old auditor review then no longer
matches. `--promote` refuses unless the candidate and the task are unchanged since the
build, the master record, `verify_package.py` and the auditor legs still pass, and the
auditor's judged review is of these exact bytes, linted Ready with zero warnings; it
never overwrites an existing `Task_Ready_To_Submit/<task-name>.zip`. Authoring records,
the master record, the auditor's working folders, negative-control staging, unrelated
evidence and workspace scaffolding never ship.

## Docker hygiene

```bash
docker context use default
docker ps
docker network prune   # after many harbor runs if network create fails
```

## Doctor

```bash
python3 scripts/doctor.py --strict-tools   # workspace files, Python 3.11+, docker context, harbor --verifier-env
python3 scripts/tbsci_doctor.py               # lightweight tool listing
```

## Never claim without output

PASS/READY/APPROVED/PACKAGED requires pasted command evidence in the chat.
`GATE PASSED — READY FOR PAPER REVIEW` requires the gate's `progress` file and
the `controls_report.py` output.
