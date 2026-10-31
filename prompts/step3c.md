> **Lean workspace, step 5.** Do not start unless `config/round.toml` status is CONFIRMED and
> docs/GPT6_SWITCH.md has been applied; the launcher refuses otherwise. Five trials per task, on the
> client's model. Then fill `authoring/<slug>/trials.md` and run `python3 scripts/tbsci.py labels <slug>`.
> Any hack-pass or false-fail is a task defect: the round is void; fix, `check`, `review`, new round.
> References to GPT-5.6 / xhigh below are the engine's current defaults until the switch is made.

# Step 3c: Difficulty Evaluation and Evidence Capture

Task path: `tasks/<task-name>` (`<task-name>` is the task slug).

`MASTER_CHECKLIST_TBSCI.md` is the source of truth; Sections G and H of it
(#71–#94) and the trial analysis of #107 are what this round's evidence must
later satisfy at Step 4, so capture it with those checks in mind.

Run only after Step 3b returns `READY FOR DIFFICULTY EVAL`. Run five model
attempts, three full-suite Oracle controls, and two full-suite NOP controls.
Preserve all ten trials and audit every outcome. The validity audit is
incorporated below.

Model attempts are run the way they will be judged (STB full-fidelity kit,
`docs/reference/stb-full-fidelity-kit/README.md`): `@openai/gpt-5.6` at
`reasoning_effort=xhigh`, no truncated observation, every prompt and reply
stored, every raw API request and response logged, terminal session recorded.
A run at default effort or with the stock 10,000-byte observation cap is not
evidence of difficulty and is **void**; never quote numbers from it.

## 1. Verify the starting task

Bind this round to the sealed digest and the current paper review before any
job starts. Nothing here reruns the Step 2b gate.

```bash
source .venv/bin/activate
docker context use default
python3 scripts/doctor.py --strict-tools
python3 scripts/patch_stb_harbor.py --check   # after "python3 scripts/patch_stb_harbor.py" once per stb install/upgrade
python3 scripts/evidence.py check tasks/<task-name> \
  --evidence artifacts/gates/<task-name>/step2b.json
python3 scripts/task_check.py tasks/<task-name> --strict
python3 - <<'EOF'
import sys; sys.path.insert(0, "scripts")
from pathlib import Path
from stage_reports import check_stage_report
errors = check_stage_report(Path("tasks/<task-name>"), Path("artifacts/reviews/<task-name>.md"), "review")
print("\n".join(errors) or "Review header: PASS")
raise SystemExit(1 if errors else 0)
EOF
sha256sum artifacts/reviews/<task-name>.md
```

`Evidence readiness: PASS`, `Review header: PASS`, and the same digest in both
are required; the review check fails on a missing, duplicated, or stale
`Task:` / `Task digest:` / `Verdict: READY FOR DIFFICULTY EVAL` line. Record
the task digest, review SHA256, Harbor and `stb` versions, resolved agent/model,
recording adapter and its source hashes, `reasoning_effort=xhigh`, and resource
limits (the launcher writes them to `<OUT>/SOURCE.txt`).
The task already carries `[agent].timeout_sec = 28800` (and `28800` for the
verifier and build) from creation (Master #63); never lower it for a round. Run
the full verifier; unset `TBENCH_TEST_ID` and remove any inherited selector
from run settings before all ten trials.
Do not edit authored task files to enable recording.

## 2. Run five model attempts and five baseline controls

Model: `@openai/gpt-5.6` (LiteLLM / Portkey wire form `openai/@openai/gpt-5.6`)
at `reasoning_effort=xhigh`, using Terminus-2 through the local recording
adapter. Launch model attempts via `stb harbor run` so Portkey credentials and
attribution headers are injected; the Oracle and NOP controls run on plain local
`harbor run` (no stb). Prefer **one Harbor job per model attempt** (`-n 1`,
default one attempt) with job names `<task-slug>-gpt56-t1` … `<task-slug>-gpt56-t5`.
The three Oracle jobs and the two NOP jobs each use one attempt. Explicitly disable
retries so failed attempts remain visible. Use a fresh output directory for each
evaluation round. Credential policy: a key from `stb keys refresh` carries a $10 budget and lasts
30 days, the account allows only 20 refreshes, and every refresh revokes the
previous key (killing any other round's trials on it). Never refresh by hand. The
launcher probes the stored key before every model attempt
(`scripts/stb_key_guard.py ensure`) and refreshes it only when the gateway
rejects it for its usage limit (Portkey error code 04), once, under a
machine-wide lock, logging fingerprints to `~/.cache/tb4-workflow/stb-key-ledger.jsonl`.
Parallel rounds share one key. A trial whose `result.json` holds an
`AuthenticationError` or a usage-limit error is an infrastructure failure, not a
model failure.

Settings that must never change for a round that ships:

| setting | value | why |
|---|---|---|
| model | `@openai/gpt-5.6` | the reference solver |
| `--ak reasoning_effort=xhigh` | xhigh | default effort understates the model |
| `--ak max_output_bytes=0` + `TERMINUS_MAX_OUTPUT_BYTES=100000000` | uncapped | no observation is ever truncated |
| `--ak store_all_messages=true` | on | every prompt and reply lands in `result.json` |
| `TERMINUS_RAW_API_LOG=1` | on | `agent/api-calls.jsonl`: every request + raw response |
| asciinema recording | on | `agent/recording.cast` |
| console log + `SOURCE.txt` | written | binds the run to the task digest, model, effort, k |

### Output limits and recording

Stock Harbor 0.23.0 (local, and bundled in stb 2.4.16) does **not** read `TERMINUS_MAX_OUTPUT_BYTES`; its Terminus-2
helper caps terminal observations at 10,000 bytes. Merely exporting `10000000`
does not remove that cap, and 10,000,000 bytes would still be a finite limit.
The local `scripts.harbor_recording:RecordingTerminus2` adapter (a preserved
legacy upstream Harbor identifier) makes the setting
explicit: `--ak max_output_bytes=0` removes the terminal-observation byte cap.
It overrides the exported value below and saves every observation in full under
`agent/terminal-output/`. A positive adapter value caps only model-facing output;
the raw observation files remain complete.

The adapter also enables full message retention and terminal-session recording,
and records `reasoning_effort` and the raw-API-log setting in
`agent/recording_config.json`.

The raw API log needs the Harbor copy **bundled inside stb** (which `stb harbor
run` executes, not the standalone `harbor`) to carry the kit's capture patches:
`python3 scripts/patch_stb_harbor.py` edits
`~/.local/share/uv/tools/snorkelai-stb/.../harbor/{agents/terminus_2/terminus_2.py,llms/lite_llm.py}`
so that the observation cap honours `TERMINUS_MAX_OUTPUT_BYTES` and every
request/response is appended to `<trial>/agent/api-calls.jsonl`. It is
idempotent, keeps `.orig-<stb version>` backups, and must be re-run after every
`stb` upgrade; the launcher refuses to start while the patch is missing (exit 3).
No authored task file and no local (Oracle/NOP) Harbor file is modified.

Retain native ATIF, every continuation/summarization file, raw responses, sessions,
metrics, `api-calls.jsonl`, and `recording.cast`; do not strip or reserialize
them. This removes the terminal-output byte cap, not the model's context/output-token
limits or the task's 28800-second agent timeout. Record context compression and any
capture errors.

Oracle and NOP have no native model ATIF in Harbor 0.23. Their recording adapters
retain actual execution in `agent/execution_trace.jsonl`: start/end, executed
commands and returned stdout/stderr, timestamps, and exceptions. Oracle also
retains its redirected solution output in `agent/oracle.txt`. NOP legitimately
has no commands or model reasoning; its trace records that no-op run. These are
execution traces, not fabricated ATIF. Copy any additional native trajectories
when present. All three agent types retain verifier CTRF, rewards, and trial logs.

### Commands

Use the launcher; it verifies the stb-bundled patch before every model attempt
(`<OUT>/patch-guard.log`), probes the key before each model attempt (refreshing only on budget exhaustion), runs the ten jobs below in order, refuses an
existing `OUT`, records the digest, adapter hashes and `SOURCE.txt`, and ends
with the fidelity check (ten jobs: five model attempts, oracle-1..3, nop-1..2):

```bash
stb login                                   # once; model trials need Portkey credentials
python3 scripts/patch_stb_harbor.py         # after every stb install/upgrade/reinstall; ends "stb-bundled harbor patch: PASS"
scripts/run_step3c_eval.sh tasks/<task-name>          # OUT defaults to ./evidence-<task-name>
```

Its last lines must read `SUMMARY evidence-<task-name>: x/5 solved; fidelity PASS`
(`scripts/check_trajectory.py`, also saved as `<OUT>/fidelity-check.log`). It
checks, per model trial: reward and test counts, `all_messages` stored,
`api-calls.jsonl` and `recording.cast` present, every logged API request
carrying `reasoning_effort=xhigh`, `agent/recording_config.json` recording
`max_output_bytes=0`, `reasoning_effort=xhigh` and a raw API log, and no
observation containing a truncation
marker (`[... output limited to N bytes; M interior bytes omitted ...]`). On
`fidelity FAIL` the round cannot be archived as it stands: its `BAD` trials are
never candidates, its `OK` trials still are. Fix the cause (usually a missing
patch or an expired key mid-run), run another round at the same digest and run
config with a fresh `OUT`, and complete the evidence with
`scripts/compose_step3c.py` (section "Rounds cut short" below). `MODEL=` / `EFFORT=` overrides exist for diagnostics only;
`archive_step3c.py` rejects a round whose recorded effort is not `xhigh`.

The launcher is equivalent to the following, kept here so every flag is
visible. Run from the repository root with Harbor available. The import path
exposes the local adapters to Harbor's Python; no installed Harbor files are
modified.

```bash
set -uo pipefail
export TERMINUS_MAX_OUTPUT_BYTES=100000000     # honoured by the patched stb-bundled Harbor
export TERMINUS_RAW_API_LOG=1                  # <trial>/agent/api-calls.jsonl
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
unset TBENCH_TEST_ID
python3 scripts/patch_stb_harbor.py --check || exit 3
TASK="$(realpath tasks/<task-name>)"
OUT="./evidence-$(basename "$TASK")"
test ! -e "$OUT" || { echo "Choose a fresh OUT directory for this round." >&2; exit 2; }
mkdir -p "$OUT"
sha256sum scripts/harbor_recording.py scripts/recording.py scripts/archive_step3c.py \
  scripts/check_trajectory.py scripts/patch_stb_harbor.py > "$OUT/recording-source.sha256"
python3 scripts/task_digest.py "$TASK" > "$OUT/task-digest.txt"   # SOURCE.txt is derived from this

# Keep console output and command statuses even when a job fails; run all controls.
SLUG="$(basename "$TASK")"
run_logged() {
  local launcher="$1" job="$2"
  shift 2
  $launcher run "$@" --job-name "$job" 2>&1 | tee "$OUT/$job.console.log"
  local codes=("${PIPESTATUS[@]}")
  printf 'harbor=%s\ntee=%s\n' "${codes[0]}" "${codes[1]}" > "$OUT/$job.exit-codes.txt"
}

for i in 1 2 3 4 5; do
  python3 scripts/stb_key_guard.py ensure --label "${SLUG}-gpt56-t${i}" --log "$OUT/keys-refresh.log"   # refreshes only on budget exhaustion
  run_logged "stb harbor" "${SLUG}-gpt56-t${i}" -p "$TASK" -a scripts.harbor_recording:RecordingTerminus2 \
    -m '@openai/gpt-5.6' -n 1 --max-retries 0 \
    --ak max_output_bytes=0 --ak reasoning_effort=xhigh --ak store_all_messages=true -o "$OUT"
done
run_logged harbor oracle-1 -p "$TASK" -a scripts.harbor_recording:RecordingOracle -n 1 --max-retries 0 -o "$OUT"
run_logged harbor oracle-2 -p "$TASK" -a scripts.harbor_recording:RecordingOracle -n 1 --max-retries 0 -o "$OUT"
run_logged harbor oracle-3 -p "$TASK" -a scripts.harbor_recording:RecordingOracle -n 1 --max-retries 0 -o "$OUT"
run_logged harbor nop-1 -p "$TASK" -a scripts.harbor_recording:RecordingNop -n 1 --max-retries 0 -o "$OUT"
run_logged harbor nop-2 -p "$TASK" -a scripts.harbor_recording:RecordingNop -n 1 --max-retries 0 -o "$OUT"
python3 scripts/check_trajectory.py "$OUT" | tee "$OUT/fidelity-check.log"   # last line: fidelity PASS
```

Wait for each job to finish. Do not replace failed attempts with unreported
retries: every attempt at the digest is either in the round or listed in a
composed round's `composition.json`. Retain all job-level configuration/results and all trial directories;
use actual Harbor trial IDs rather than guessing their generated names.

### Archive and verify every trial

```bash
python3 scripts/archive_step3c.py --task-dir "$TASK" --jobs-dir "$OUT"
```

This replaces a bare `zip -r` with a checked archive. It copies **all** output,
including extra files and failed runs, to `tasks/<task>/trajectories/<OUT-name>/`
(hard-linked to the round where the filesystem allows, so the round is stored once),
writes `$OUT/collection.json` with per-file SHA256 hashes, discovered trial records,
and missing-trial diagnostics, and verifies the copy byte for byte. No evidence zip is
written unless `--zip <file>` is given: nothing in the workflow reads one (disk rule).
It refuses to overwrite previous evidence; for a rerun choose a new `OUT`. Record the
actual paths in the difficulty report.

### Rounds cut short: compose the first five valid trials (Master #94 item 1)

A round can stop before five fidelity-complete trials exist — the key's budget runs
out mid-trial, the `stb keys refresh` quota runs out, an infrastructure fault aborts an attempt, a trial dies
with `exception_info`. Its completed trials are not void. The five packaged runs
are **the first five fidelity-complete trials at the current digest and run
config, in launch order across rounds, with no valid attempt skipped**. Launch
another round at the same digest with the same launcher (a fresh `OUT`), stop it
once five valid trials exist across the rounds if you like (an operator stop
after the first five is outcome-independent), run the controls if no source
round has them, and compose:

```bash
CONTROLS_ONLY=1 scripts/run_step3c_eval.sh tasks/<task-name>   # Oracle x3 + NOP x2 only, local harbor; OUT ./evidence-<task-name>-controls
python3 scripts/compose_step3c.py tasks/<task-name> \
  --source evidence-<task-name>-r1 --source evidence-<task-name>-r2 \
  --controls evidence-<task-name>-controls \
  --out evidence-<task-name>-composed            # ends "SUMMARY ...: x/5 solved; fidelity PASS"
```

`compose_step3c.py` enforces the boundaries; it refuses rather than warns:

- **Same digest.** Every source and the controls round record the same
  `task-digest.txt` (and agent/grader digests). Pooling never crosses digests.
- **Same run config.** Model, `reasoning_effort=xhigh`, agent adapter and
  launcher, capture settings (`max_output_bytes=0`, `store_all_messages`, raw
  API log, `TERMINUS_MAX_OUTPUT_BYTES`), stb and Harbor versions, arch, the
  full-fidelity patch revision in each round's `patch-guard.log`, and the
  run-affecting hashes in `recording-source.sha256` (`harbor_recording.py`,
  `recording.py`, `patch_stb_harbor.py`) — compared from each round's
  `SOURCE.txt`, `task-digest.txt`, `recording-source.sha256` and every trial's
  `config.json`, `recording_config.json`, `result.json` `task_checksum` and
  job `lock.json`. Controls must match on digest, local Harbor, arch and the
  adapter hashes; they may come from any source round or a `CONTROLS_ONLY=1` run.
- **Fidelity-complete** = every per-trial `check_trajectory.py` criterion,
  verifier CTRF with test records, `exception_info` null, and the files
  `archive_step3c.py` requires.
- **Selection** sorts every model trial across the sources by its own
  `result.json` `started_at` and takes the first five valid ones. Never
  best-of: no valid attempt launched before the fifth selected one can be left
  out. A trial is excluded only for an outcome-independent reason (infra
  abort, credential/quota abort, `exception_info`, operator stop after the first
  five were complete); an operator stop or an unfinished trial *inside* the
  first five needs an explicit `--reason <trial-id>='<why>'`, which is recorded.
- **No hidden rounds.** Another round directory at this digest and run config
  with a trial launched before the fifth selected one is a refusal until it is
  passed as `--source` — including a directory renamed `_void-*`.

The composed `OUT` holds `<task>-gpt56-t1..t5` in launch order (whole job
directories copied, only the job folder renamed; the job-level `config.json`
keeps its captured `job_name`, trial folders, IDs and timestamps are
untouched), `oracle-1..3`/`nop-1..2`, merged `SOURCE.txt`,
`task-digest.txt`, `recording-source.sha256`, `provenance/<round>/` and
`composition.json` (every candidate trial across the sources, its start time,
validity, selected/excluded and why). It then goes through `archive_step3c.py`
and `audit_step3c.py` exactly like a single round. Nothing new ships:
`SUMMARY.txt` stays two lines and no report enters the ZIP — the shipped runs'
own `result.json` (distinct `id`, strictly increasing `started_at`) and
`config.json` are the evidence, and `verify_package.py` and the auditor check
that order. The difficulty report names the composed round and cites
`composition.json` for every excluded or not-selected trial.

```text
evidence-<task>/
├── collection.json
├── SOURCE.txt               # task digest, model, reasoning_effort, capture settings, stb/harbor versions
├── fidelity-check.log       # check_trajectory.py output; last line "fidelity PASS"
├── <task>-gpt56-t1/ … <task>-gpt56-t5/   # One model attempt each
│   ├── config.json, result.json, job.log, ...
│   └── <trial-id>/
│       ├── agent/           # ATIF, all segments, raw observations, api-calls.jsonl, recording.cast, ...
│       ├── verifier/        # ctrf.json, reward.txt, stdout/stderr, ...
│       ├── config.json
│       ├── result.json
│       └── trial.log
├── oracle-1/                # One trial, including execution_trace.jsonl and oracle.txt
├── oracle-2/                # One trial, including execution_trace.jsonl and oracle.txt
├── oracle-3/                # One trial, including execution_trace.jsonl and oracle.txt
├── nop-1/                   # One trial, including its no-op execution trace
├── nop-2/                   # One trial, including its no-op execution trace
└── *.console.log, *.exit-codes.txt
```

CTRF is required for **each** model and control trial that was launched. Missing
CTRF, ATIF for a model trial, baseline execution traces, or other required
records yields `capture_status: INCOMPLETE` and a nonzero collector exit. So does
a model trial whose `recording_config.json` records a reasoning effort other
than `xhigh`, lacks the raw API log, has an empty `api-calls.jsonl`, or whose
ATIF contains a truncation marker: such a trial is not evidence, and the round
cannot be archived as it stands; its fidelity-complete trials remain candidates
for `compose_step3c.py`, which re-checks each one.
Available evidence is still copied and zipped for diagnosis. Record the missing
files and exceptions; never invent evidence or count infrastructure failures as
valid model failures. `COMPLETE` describes capture only, not task approval.
Inspect the actual exit codes and JSON contents, not only file presence, before
accepting results.

Keep originals and task-local copies (`scripts/prune_evidence.py` retires them only once
they are stale: another digest, no live regrade chain, no current candidate). Task-root
`trajectories/` is excluded from the behavioral task-source digest, so
archiving does not invalidate the Step 2b seal. Step 4 packages the complete
archived round only after its file inventory and recorded task digest match the
current task (`docs/reference/SUBMISSION_CHECKLIST.md`).
The full-suite controls here supplement Step 2b's sealed per-test Oracle/NOP
matrix and negative-control matrix; they do not replace that gate. Step 4 is
packaging-only and does not re-run Oracle or NOP.

## 3. Audit validity for every trial

Build the reading aid first, then read the raw trajectories it points to:

```bash
python3 scripts/audit_step3c.py --task-dir tasks/<task-name> --jobs-dir evidence-<task-name>
# writes evidence-<task-name>/audit-dossier.md (override with --out)
```

The dossier lists, per trial, reward, CTRF summary, command counts, token
usage, compaction events, harness errors, reward-hack and refusal signals, the
raw-API-log record count with the reasoning effort each request carried, the
truncated-observation count, a `Capture fidelity` line, and a command timeline;
controls get their execution-trace summary. It reports missing files as
`MISSING` and is not a verdict. Classification below is yours.

Audit the complete task, verifier, and **all available** trajectories. The five
model trials and five baseline controls above form the current evaluation (for a
composed round: the five selected in `composition.json`; list its excluded and
not-selected trials with their recorded reasons, outside every denominator).
Identify historical runs separately with their task digests; do not pool
different task versions into its rates.
Read full traces and actual modifications, not only final messages or rewards.

Assign each model trial exactly one classification:

| Classification | Meaning |
| --- | --- |
| `VALID_PASS` | The model genuinely satisfied the public contract. |
| `VALID_FAIL` | The model violated a requirement explicitly stated or uniquely derivable from the public contract. |
| `FALSE_FAIL_SPEC_GAP` | The verifier rejected valid behavior using an unstated or overly specific requirement. |
| `INVALID_PASS_REWARD_HACK` | The verifier accepted exploitation, bypass, overfitting, or tampering instead of a genuine solution. |
| `INFRA_FAILURE` | Environment, setup, harness, or verifier malfunction prevents measuring model capability. |

Reward `0` alone cannot establish `VALID_FAIL`; reward `1` alone cannot establish
`VALID_PASS`. If evidence is insufficient for classification, mark the audit
incomplete and recover it or rerun. Do not guess a valid outcome.

**Trial analysis (Master #107).** Every model trial, passing and failing, is
also judged from its full trajectory against the eight trial-analysis criteria
adopted from upstream `rubrics/trial-analysis.toml` — `PASS` / `FAIL` / `N/A`
per criterion, each with the ATIF step, raw-log record or verifier line that
decides it. The table goes in the report (section 5, template
`authoring/_templates/step3c-report.md`, "Trial analysis (#107)"):

| Criterion | Side | What a FAIL means |
| --- | --- | --- |
| `specification_completeness` | task | The trial hit a requirement the instruction and public files never stated or uniquely implied. |
| `solution_discoverability` | task | A domain expert with the public materials could not have found a correct approach (missing data, an unobtainable input, a hidden convention). |
| `verifier_correctness` | task | The tests rejected correct work or accepted wrong work, or crashed on valid output. |
| `boundary_fairness` | task | A tolerance, threshold or fuzzy match decided the outcome where the science gives no basis for that boundary (#101). |
| `policy_refusal` | trial | The model refused or abandoned the work on policy grounds. |
| `execution_blocked` | trial | A harness fault, limit, key or infrastructure stop ended the trial before the work was judged (#92). |
| `unearned_credit` | trial | A pass that exploited the evaluation, tampered with grading or already knew the answer (#93). |
| `meaningful_difficulty` | trial | The outcome turned on procedure, formatting or luck rather than the scientific work the task is about. |

How the criteria map onto the classification above: any task-side `FAIL`
indicts the **task**, not the model — the trial is `FALSE_FAIL_SPEC_GAP` (or
`INFRA_FAILURE` for a verifier crash), the results decision is a fix-and-rerun,
and the task is repaired at a fresh digest; it never ships with one open.
`unearned_credit` `FAIL` is `INVALID_PASS_REWARD_HACK`. `policy_refusal` or
`execution_blocked` `FAIL` keeps the trial out of the defensible rate (AGENTS.md
rule 21). A `meaningful_difficulty` `FAIL` on a failing trial means the failure
is not difficulty evidence; on a passing trial it is a shallow-shortcut signal
(`TOO EASY`). Only trials with every applicable criterion `PASS` are
`VALID_PASS` or `VALID_FAIL`.

For baseline controls, require each Oracle reward to be `1.0` with every declared
CTRF case passed, and the NOP reward to be `0.0` with every declared case failed.
A satisfied control is `CONTROL_PASS`; a genuine mismatch is `CONTROL_FAIL`;
setup, execution, skipped/missing cases, or missing evidence is `INFRA_FAILURE`.
Trace every mismatch to its cause. A failing control blocks accepting this round
until resolved; baseline controls never enter the model pass-rate denominator.

### A. Build the public contract first

Read `instruction.md` and every solver-visible interface: environment files,
input data, manifests, configuration, schemas, starter code, and documentation.
Inventory every requirement, cite its source, and classify it:

- `EXPLICIT`: directly stated in the instruction.
- `DERIVABLE`: uniquely implied by public files or specification.
- `NOT_PUBLIC`: present only in tests, hidden fixtures, Oracle, or grader assumptions.

Establish this contract before interpreting hidden tests. Never use the Oracle
or hidden fixtures to retroactively resolve ambiguity in public requirements.

### B. Map every meaningful assertion to the contract

Inspect `tests/test.sh`, all verifier logic and helpers, fixtures, generated
cases, and `solution/solve.sh` as a reference implementation. For every meaningful
assertion, report the public requirement, source, and classification above.

Flag exact bytes, strings, filenames, ordering, serialization, hashes,
algorithms, implementation strategies, intermediate values, internal
representations, or formatting when equivalent answers are permitted. Check
whether expectations came directly from Oracle output without a public reason
for that representation. Judge semantic invariants rather than Oracle identity.

### C. Explain every failed trajectory

For each failed trial:

1. Identify the first meaningful failing assertion or execution failure. Cite
   verifier file/line, logs, and ATIF step IDs as applicable.
2. Determine what the model actually implemented and what behavior it produced.
3. Compare it with the public requirement and determine whether the failing
   condition was knowable to the solver.
4. Check whether a semantically equivalent valid solution was rejected. Record
   the hidden assumption and any proposed verifier/spec correction.
5. Assess independent genuine violations too; an unfair first assertion does
   not by itself establish that the entire solution satisfies the contract.

A failure counts as difficulty evidence only when a public requirement was
violated. If an expert could not establish the violation from public materials,
investigate a specification gap before assigning `VALID_FAIL`.

### D. Audit every success for reward hacking and generalization

Inspect changed files and behavior for disabled assertions, altered tests or
grading infrastructure, hardcoded answers or fixtures, special handling of known
test inputs, grader detection, answer leakage, fake outputs, path/symlink tricks,
and bypassed computation. Unconventional implementations that satisfy the public
contract are legitimate successes.

Where practical, run the submitted solution **unchanged** against harmless unseen
variants allowed by the contract: reordered records, fresh IDs, different valid
inputs or seeds, legal sizes, new manifests, and already-public edge cases.
Change filenames only when they are not contractual. Use isolated copies and
bounded commands; preserve the original trial evidence and task source. Record
performed checks, results, and limits on generalization evidence.

For every success, report suspicious behavior (or none), changed code, whether
the verifier was modified, generalization evidence, classification, and confidence.

### E. Attribute infrastructure failures by cause

Identify Docker/setup failures, unavailable dependencies or network resources,
corrupted fixtures, harness malfunctions, verifier crashes, and nondeterministic
grading. These cannot count as model capability failures. A failure caused by a
truncated observation, a key expiring mid-run (`AuthenticationError` in
`result.json`), or a harness crash is not a failure of the task; a failure
counts only if the trajectory shows the model saw everything it needed and
still failed on a rule the instruction or docs state. Exceeding a documented
budget because of the model's implementation can be a `VALID_FAIL`; a timeout
caused by infrastructure is `INFRA_FAILURE`. Apply the same causal distinction
to dependency and execution errors.

## 4. Calculate raw and defensible pass rates

Report all ten trial rows, including missing rewards and exceptions. Give counts,
denominators, and percentages when defined:

If fewer than five model trials launched, mark the round incomplete and report
the launched/missing counts. Do not present unstarted attempts as measured failures.

- **Raw pass rate:** model grader successes / total model attempts (five).
  List missing rewards explicitly; do not invent reward `0` for an exception.
- **Defensible model pass rate:** model `VALID_PASS / (VALID_PASS + VALID_FAIL)`.
- Report the five baseline control outcomes separately, outside both model rates.
- Count model valid passes, valid failures, false failures, reward-hacked passes,
  infrastructure failures, and any trials awaiting sufficient evidence.

Exclude `FALSE_FAIL_SPEC_GAP`, `INVALID_PASS_REWARD_HACK`, and `INFRA_FAILURE`
from the defensible denominator. If no valid trials remain, report `N/A`.
Do not claim a model was defeated based on contaminated failures or draw strong
success-rate conclusions from five model trials. 5/5 at `xhigh` means the model
already does this task; that is the band, whatever a default-effort run said
before. Rounds at other digests get separate
tables and denominators; same-digest, same-config rounds are pooled only through
`compose_step3c.py`.

**Measured rate.** State the result as `k/5` (the number of `VALID_PASS` model
trials out of five, with the raw rewards beside it). A measured 0/5, 1/5, 2/5 or 3/5
is shippable. A higher rate is reported honestly and the task is hardened at a
fresh digest; a trial is never discarded or re-rolled because its result is
inconvenient. The rate lives **only** in workspace records —
`artifacts/difficulty/<task-name>.md`, `authoring/<task-name>/step3c-report.md`
— and, at packaging, in `SUMMARY.txt`'s reward array. Never write it, a tier
word (hard/medium/easy or any other), a percentage or a pass count into
`task.toml`, `instruction.md`, or any other task file (Master #62); there is no
`difficulty` field. The `## Difficulty` section of
`authoring/<task-name>/write-ups.md` (workspace only; the task carries no
README.md) stays a plain-language account of what makes the task hard
(Master #62, #103) and never carries the rate.

**Reruns (Master #92).** A model trial whose `result.json` has `exception_info`
populated (key exhaustion, `AuthenticationError`, timeout, infrastructure
error), a failed fidelity check, or a failure that was still making progress at
cutoff is not a measurement. It is never shipped with an assumed reward. It is
replaced by the **next fidelity-complete trial at the same digest and run
config in launch order** (Master #94 item 1): launch more attempts in a fresh
`OUT` and compose with `scripts/compose_step3c.py`, which records the excluded
trial and its reason in `composition.json` and keeps it out of every
denominator. Never hand-copy a trial into another round, never pick which
valid trial to keep, and never pool across digests. A trial that reached a
reward with full capture is fidelity-complete whatever its reward, and
`compose_step3c.py` never excludes it; a judged `INFRA_FAILURE` among the five
stays an `INFRASTRUCTURE RERUN` results decision (section 5), not a selection
change.

**The set that moves after any rerun (Master #94).** Whatever five ship — one
round or a composed one — move together: the five run folders (the first five
fidelity-complete trials in launch order, item 1), `SUMMARY.txt` sha and
rewards, all five `rubric_score.txt` files, `expert_time_estimate_hours` if the
new trajectories materially change it (a descriptive `[metadata]` edit:
`gate_step2b.sh --reseal-only` then `stage_reports.py rebind-review`), the
bundle sha recompute, and a fresh PII/`stb`/canary grep. Step 4 checks all six;
a partially refreshed set is a FAIL.

## 5. Save the combined difficulty and validity report

Write `artifacts/difficulty/<task-name>.md` and the same content to
`authoring/<task-name>/step3c-report.md` (template:
`authoring/_templates/step3c-report.md`). These workspace reports are the only
place the measured rate is written. Begin with these machine-checked metadata
lines, replacing placeholders with actual values and the actual verdict:

```text
Task: <task-name>
Task digest: sha256:<current-task-digest>
Review SHA256: sha256:<hash-of-complete-paper-review>
Evaluation policy: @openai/gpt-5.6 reasoning_effort=xhigh via stb harbor (bundled harbor patched, stb <version>); Terminus-2 recording adapter; five model attempts (<task>-gpt56-t1..t5); Oracle x3; NOP x2; uncapped terminal observations; raw API log; fidelity PASS; acceptance band measured 0/5-3/5
Trial evidence: tasks/<task-name>/trajectories/evidence-<task-name>/; evidence-<task-name>/collection.json; evidence-<task-name>/SOURCE.txt; evidence-<task-name>/fidelity-check.log   (composed round: also evidence-<task-name>-composed/composition.json)
Verdict: <difficulty-verdict>
```

Include all of the following:

1. **Validity summary:** `CLEAN` (complete evidence and all trials valid),
   `CONTAMINATED` (valid and invalid results mixed), or `INVALID` (no defensible
   results or missing essential evidence). State public-contract alignment
   `PASS`/`FAIL`; rate false-fail and reward-hack risk as
   `NONE`/`LOW`/`MEDIUM`/`HIGH`/`CONFIRMED`, with reasons. Mark incomplete assessments
   explicitly rather than claiming an unsupported rating.
2. **Trajectory audit:** ten rows (expand the model placeholder into five), plus a short
   summary of what each agent did and its first genuine blocker, if any.
   **Trial analysis (#107):** one row per model trial with a `PASS` / `FAIL` /
   `N/A` verdict and its citation for each of the eight criteria in section 3.
3. **False-failure findings:** failing assertion, verifier file/line, agent
   behavior, public requirement, hidden assumption, and recommended correction.
4. **Success/reward-hacking findings:** actual changed files, verifier tampering,
   generalization evidence, classification, and confidence for every success.
5. **Assertion-to-contract matrix:** each meaningful assertion, its public
   requirement and source, `EXPLICIT`/`DERIVABLE`/`NOT_PUBLIC`, and whether the
   assertion is valid or unspecified.
6. **Results:** both rates, the measured rate as `k/5`, all classification
   counts, missing evidence, raw and copied artifact paths, hashes, exceptions
   (`exception_info` per trial), and audit limitations.
7. **Evidence notes for Step 4:** per model trial, the `trajectory.json` steps
   and `verifier/test-stdout.txt` lines Step 4 will cite in that run's
   `rubric_score.txt` (Master #84, #86), and whether any full-precision numeric
   result agrees across runs suspiciously closely (Master #83).

| Label | Model | Job name | Raw reward | Exceptions | Classification | Exact reason | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <each of five model trial IDs> | @openai/gpt-5.6 | <task>-gpt56-tN | ... | ... | ... | ... | ATIF step / CTRF / raw log |
| <Oracle trial ID> | N/A (oracle) | oracle-1 | ... | ... | CONTROL_PASS / CONTROL_FAIL / INFRA_FAILURE | ... | execution trace / CTRF / oracle.txt |
| <Oracle trial ID> | N/A (oracle) | oracle-2 | ... | ... | CONTROL_PASS / CONTROL_FAIL / INFRA_FAILURE | ... | execution trace / CTRF / oracle.txt |
| <Oracle trial ID> | N/A (oracle) | oracle-3 | ... | ... | CONTROL_PASS / CONTROL_FAIL / INFRA_FAILURE | ... | execution trace / CTRF / oracle.txt |
| <NOP trial ID> | N/A (nop) | nop-1 | ... | ... | CONTROL_PASS / CONTROL_FAIL / INFRA_FAILURE | ... | execution trace / CTRF |
| <NOP trial ID> | N/A (nop) | nop-2 | ... | ... | CONTROL_PASS / CONTROL_FAIL / INFRA_FAILURE | ... | execution trace / CTRF |

Choose exactly one **results decision**:

- `ACCEPT RESULTS`: clean evaluation; observed outcomes are defensible.
- `FIX VERIFIER AND RERUN`: tests enforce stricter behavior than the public contract.
- `FIX SPEC AND RERUN`: intended exact behavior was not communicated.
- `REMOVE REWARD-HACK VECTOR AND RERUN`: successful agents can bypass the task.
- `INFRASTRUCTURE RERUN`: infrastructure or evidence capture contaminated results.
- `MULTIPLE ISSUES — FIX AND RERUN`: more than one issue above applies.

Keep results validity separate from the **difficulty verdict** in the header:

- `READY FOR PACKAGING`: results are `ACCEPT RESULTS`, evidence capture is
  complete with `fidelity PASS`, controls are clean (Oracle x3 at 1.0 with
  every test passing, NOP x2 at 0.0 with every test failing on a genuine
  assertion), no trial has `exception_info`, every model trial has a complete
  #107 row with no task-side criterion `FAIL`, no unresolved
  fairness/verifier/infra issue remains, and the measured rate is 0/5, 1/5, 2/5
  or 3/5. Use this when Step 4 packaging may proceed (Step 4 does not re-run
  Oracle/NOP).
- `TOO EASY`: the measured rate is 4/5 or higher, or valid outcomes show a
  substantiated shallow shortcut. Harden at a fresh digest.
- `NEEDS REVISION`: task, verifier, infrastructure, or evidence defects prevent
  accepting this evaluation.
- `EVALUATED`: reserved for audits that measure outcomes but are not cleared for
  packaging (for example incomplete capture or pending policy). Prefer
  `READY FOR PACKAGING` once `ACCEPT RESULTS` and trajectories are complete.

Five model attempts and five controls specify the run plan; the acceptance band is
the measured rate rule above.
`ACCEPT RESULTS` with complete evidence and clean controls authorizes
`Verdict: READY FOR PACKAGING` for Step 4 (packaging-only; no fresh Oracle/NOP).
Any task-source repair requires the full Step 2b gate, a fresh Step 3b, and
fresh difficulty trials. A changed paper review also invalidates this report's
review hash. Retain old evidence and distinguish reruns in the report.

Before handing off, confirm the header binds to the current task and review
(this is the check Step 4 runs):

```bash
python3 - <<'EOF'
import sys; sys.path.insert(0, "scripts")
from pathlib import Path
from stage_reports import check_stage_report
errors = check_stage_report(Path("tasks/<task-name>"), Path("artifacts/difficulty/<task-name>.md"),
                            "difficulty", review_path=Path("artifacts/reviews/<task-name>.md"))
print("\n".join(errors) or "Difficulty header: PASS")
raise SystemExit(1 if errors else 0)
EOF
```
