# Step 4 — Digest-bound packaging only

`MASTER_CHECKLIST_TBSCI.md` is the source of truth; `docs/reference/DELIVERY_CHECKLIST.md`
gives the ZIP layout and file formats. Read `docs/reference/DELIVERY_CHECKLIST.md`. Step 4 packages a
task whose evidence is already complete. It never reruns Oracle, NOP, controls,
or model trials, and never repairs task behavior. Task path: `tasks/<task-name>`.

## 1. Verify seal, review, and difficulty report

All three must bind to the current task digest; the difficulty report must
also bind to the SHA256 of the current review.

```bash
source .venv/bin/activate
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
python3 scripts/task_digest.py tasks/<task-name>
python3 scripts/master_checklist.py check tasks/<task-name> --stage review
```

Required: `Evidence readiness: PASS`, `Stage reports: PASS` (review says
`READY FOR DIFFICULTY EVAL`, difficulty report says `READY FOR PACKAGING`, both
on this digest), and the review-stage master record still passing on this
digest with no open finding of any severity. A failure on any line means the
task changed after its evidence; stop and route the change to its gate
(`docs/WORKFLOW.md`, revision routing). Confirm the Step 3c round is
archived under `tasks/<task-name>/trajectories/<step3c-round>/`, its
`task-digest.txt` matches the current digest, and the difficulty report names
that round. A round composed across rounds (`scripts/compose_step3c.py`) is
packaged exactly like a single one; read its `composition.json` for #94 item 1
(every candidate, start time, selected/excluded and the recorded
outcome-independent reason) — it stays in the workspace and never ships.

## 2. Write one rubric_score.txt per run

`tasks/<task-name>/rubric.txt` exists and satisfies Master #66–#69 (checked at
Step 3b); #70 is checked here against the real scores. For each of the five runs, write
`artifacts/rubric-scores/<task-name>/<step3c-round>/run-0N.txt` in the
`docs/reference/DELIVERY_CHECKLIST.md` format:

```text
reward=<0.0 or 1.0>
tests_passed=<N>/<M>

<rubric.txt line verbatim> -- MET (<evidence from THIS run>)
<rubric.txt line verbatim> -- NOT MET (<evidence from THIS run>)
<rubric.txt negative line verbatim> -- TRIGGERED (<evidence from THIS run>)
<rubric.txt negative line verbatim> -- NOT TRIGGERED (<evidence from THIS run>)

gradient: X/Y positive met, X/Y negative triggered
```

- **Every** verdict line — MET, NOT MET, TRIGGERED and NOT TRIGGERED — ends
  with a parenthetical citation: a function, variable, command, step id or
  quoted value from that run's own `agent/trajectory.json` or
  `verifier/test-stdout.txt` (Master #78, #86). A failing test is not by itself
  evidence that a negative criterion was triggered.
- For every failing run, read the actual failure from that run's
  `trajectory.json` and `verifier/test-stdout.txt` before scoring (#84) — the
  `FAILED <case> - <message>` lines name each failed case's cause
  (`docs/TESTING_POLICY.md` rule 7). If they do not, the verifier is missing that
  rule: fix `tests/` by the regrade route first; do not score around it.
- **Score what the run achieved, not only what the agent wrote.** No verdict may
  contradict that run's own failure lines, in either direction:
  - **A failure line decides only the behaviour it names.** A criterion is NOT
    MET on a failure line only when that line shows *that specific behaviour*
    going wrong: the run's collisions against a "checks for collisions" line, a
    reported heading error against a "reaches the goal heading" line. Cite the
    line. Code that attempts the behaviour, or success on the public examples,
    does not outweigh it.
  - **A failed case or group is not a failed criterion.** When a case fails for
    a cause another criterion covers (a collision, a hang, a real-time timeout),
    that failure says nothing about the other behaviours the case also
    exercises. A failure line that does not say what went wrong (a bare timeout
    with no position or heading error) decides no criterion on its own.
  - **Then judge from the rest of the run's evidence.** For any criterion no
    failure line decides, use the other graded outcomes (hidden cases that passed
    and so show the behaviour working) and the trajectory, and cite them. NOT MET
    then needs a cited step showing the behaviour absent or wrong. Never infer it
    from a failure elsewhere.
  - **Use one standard across all five runs.** The same kind of evidence gets the
    same verdict in every run. Before saving, re-read each criterion across the
    five files.
  - **Negative criteria use the whole trajectory.** Logic chosen so that each
    public example passes is per-scenario behaviour even with no literal constant.
  - **Cite the right step.** A step number points to the step where the quoted
    code or words first appear in that run's `trajectory.json`. Check each
    citation against the file; don't carry one over from an earlier scoring.
- Each file cites its own run. Diff the five files against each other; no two
  may be copies with the header swapped (#85).
- Data only: no `note:`, no summary, no prose (#78). Check the `gradient:`
  arithmetic by hand against the verdicts (#70).

## 3. Record the post-trial verdicts

These lines were `PENDING` at Step 3b. Walk them against the five packaged runs
and the packaged oracle/NOP evidence, and fill
`authoring/<task-name>/master-checklist.md` with one verdict and evidence each.
Nothing from memory. An answer written before the runs existed is not an
answer: replace it. After a rerun or regrade, answer them again against the
new evidence. Keep the pre-trial evidence already on #1, #2, #15, #40, #53,
#57 and #101, and add the run or control that settles the check. The evidence
must name that packaged record (`run-0N`, `trajectories/`, `oracle-N`, `nop-N`,
`ctrf`, `step3c`, `result.json`, or `reward.txt`); `--stage package` rejects a
verdict that does not.

- #1 and #2: the instruction↔test map from Step 3b, re-read against what the
  five runs did. A run that fails because a graded rule was never stated, or
  that satisfies a stated requirement no test exercises, decides the verdict.
- #15: each lore/notes file mapped against the trajectories as well as
  `rubric.txt`.
- #33: where several independent runs converge on an answer different from the
  reference, that disagreement is read from their own trajectories.
- #40 and #53: packaged oracle-1..3 and nop-1..2, and every run's `ctrf.json`
  (test count and per-row status).
- #57: no packaged run was decided by a wall-clock, throughput or percentile
  assertion; the thresholds frozen before the trials are the ones graded.
- #101: margins on the shipped instances, and whether a packaged trial, the
  reference or the independent implementation was decided by a margin under
  10%. Where a generator method's smallest shipped-set margin is under 20%,
  the Step 3b record of 3 fresh draws (6 if those were borderline or
  inconsistent) is cited; not running that probe is never a finding.
- #70, #71–#94, #96, #97 and #107, each run and job directory read individually:

- evidence structure, Oracle x3 all tests passing, NOP x2 all tests failing on
  genuine assertions (read every ctrf.json and test-stdout.txt test by test),
  mtimes newer than every graded file, and three/two genuinely independent
  control runs (#71–#76);
- `SUMMARY.txt` two lines (`model=gpt-5.6`, provider prefix stripped, Master #77), rewards equal to each run's own `reward.txt` and
  `ctrf.json`, bundle sha recomputed fresh from inside the inner task folder
  (#77, #79, #80 — `python3 scripts/bundle_sha.py <inner-task-dir>`), and the
  digest-bound evidence, with mtimes secondary (#75);
- cross-run duplication on the five runs and their rubric scores (#83); every
  failing run read from its own files (#84); rubric scores independent and
  evidence-cited (#85, #86): a method-worded line is scored on whether the run
  did the method (a downstream test failure does not by itself make it NOT MET);
  an outcome-worded line is scored on that outcome; a quoted number may be a
  faithful rounding of the value at that step;
- #70(b): across the five runs the rubric orders them the same way the reward
  does. A reward-0 run whose positive total is at least some reward-1 run's is
  a finding. N/A when all five rewards match, with that reason recorded;
- PII and `stb` scrub per run/job directory, no canary, raw model-name fields
  untouched (#87–#89); canonical `agent/` and `verifier/` file sets in every run
  (#90); `reasoning_effort=xhigh` confirmed per run (#91); no `exception_info`
  (#92); per-run reward-hacking scan (#93); #94: the five runs are the first
  five fidelity-complete trials at this digest and run config in launch order
  across rounds, none skipped (the round's `composition.json` when composed;
  `verify_package.py` checks strictly increasing `result.json` `started_at`,
  distinct trial ids, one task checksum and one agent config from the shipped
  files), and the rest of the set moved with them;
- delivery structure — the inner `<task-slug>/` holds exactly
  `instruction.md`, `task.toml`, `environment/`, `solution/` and `tests/`,
  with no README.md (#103) — and the final grep (#96, #97);
- the trial analysis (#107): the Step 3c report has a row for every one of the
  five shipped model trials, each of the eight criteria judged from that
  trial's own trajectory with a citation, and no task-side criterion
  (`specification_completeness`, `solution_discoverability`,
  `verifier_correctness`, `boundary_fairness`) `FAIL`. A composed round is
  judged on the five it ships.

Then:

```bash
python3 scripts/master_checklist.py check tasks/<task-name> --stage package
```

It must pass: every check #0–#107 has a verdict with evidence, zero `FAIL`, zero
`PENDING`, bound to the current digest.

## 4. Package — build, auditor review, promote

Walk `docs/reference/SUBMISSION_CHECKLIST.md` and `docs/reference/TBSCI_REVIEW_BLOCKERS.md`; zero open
items of any severity. Packaging then runs in three phases, in this order.
There is no single command that packages straight to `Task_Ready_To_Submit/`;
only a promoted ZIP is a deliverable.

**Phase 1 — build the candidate.**

```bash
python3 scripts/package_task.py tasks/<task-name> \
  --step3c-dir tasks/<task-name>/trajectories/<step3c-round>
# writes artifacts/package-candidates/<task-name>/<task-name>.zip
#    and artifacts/package-candidates/<task-name>/<task-name>.candidate.json
# default rubric scores: artifacts/rubric-scores/<task-name>/<step3c-round>/
python3 -m zipfile -l artifacts/package-candidates/<task-name>/<task-name>.zip
```

`scripts/package_task.py` is the only packaging path. The build refuses
without a complete master record bound to the current digest, validates the
seal, reports, Step 3c inventory and every `rubric_score.txt`, rewrites host
paths in each shipped run's `config.json`/`result.json` to repo-relative form
without touching model-name fields, and builds the `docs/reference/DELIVERY_CHECKLIST.md`
layout (inner `<task-slug>/` with the five task members — no `README.md` —
`rubric.txt`,
`oracle-nop-evidence/` Oracle x3 + NOP x2, `trajectories/run-01..05` +
`SUMMARY.txt`). It then runs `scripts/verify_package.py` — the mechanical
master checks on the ZIP itself, including the final `stb` / `/Users/` /
`/private/tmp/` / host-home / canary grep over every file (Master #97) — and
`scripts/audit_task.py package` — the bundled auditor's screen plus
`trial_evidence.py`, zero findings of any severity, zero trial flags or errors,
no stale evidence. The candidate is deleted on any failure. No Step 2b/3b
record, `SOURCE.txt`, `rubrics.txt`, `hint.md` or other `authoring/` material,
AI scaffolding, caches or `.git` may appear anywhere in it, and no `README.md`
or other write-up file ships in the inner task folder or beside the four
top-level siblings (Master #96, #103); `authoring/<task-name>/write-ups.md`
stays in the workspace. Rebuilding replaces the candidate.

**Phase 2 — the auditor's judged review of the candidate.** The reviewer runs
the bundled auditor (`tools/final-tbsci-audit-master/`) on that exact ZIP,
following its `SKILL.md` procedure:

```bash
A=tools/final-tbsci-audit-master/scripts
$A/review.sh extract artifacts/package-candidates/<task-name>/<task-name>.zip
$A/review.sh audit <task-name>     # -> tools/final-tbsci-audit-master/audit/<task-name>/<ts>/, latest -> it
# read every file (SKILL.md step 2); walk CHECKLIST.md gate T, then A -> K, and the
# master coverage map; confirm or discard every screen flag; answer every LEAD;
# run the manual probes and the cheat simulation; fill verdict.json and
# manual_probes.txt (no PENDING, no <<UNFILLED>>)
$A/review.sh lint <task-name>      # must print: LINT_OK  ✅ Ready to Submit  (0 warning(s))
$A/review.sh report <task-name>    # renders report.md
```

The lint line must read `LINT_OK  ✅ Ready to Submit  (0 warning(s))` —
verdict `ready`, zero open findings, zero warnings. Any finding of any
severity, or any warning, means the fix goes back to the gate that owns it
(task source → Step 2b gate; rubric or rubric scores → this step), then the
candidate is rebuilt and re-audited from `extract`.

**Phase 3 — promote.**

```bash
python3 scripts/package_task.py tasks/<task-name> --promote
# copies the exact candidate bytes to Task_Ready_To_Submit/<task-name>.zip
python3 -m zipfile -l Task_Ready_To_Submit/<task-name>.zip
sha256sum Task_Ready_To_Submit/<task-name>.zip
```

`--promote` refuses unless the candidate bytes and the task digest are
unchanged since the build, the master record still passes `--stage package`,
`verify_package.py` and `audit_task.py package` still pass on the candidate,
and `audit_task.py verdict` passes: the auditor's review under
`tools/final-tbsci-audit-master/audit/<task-name>/latest/` lints clean as
`✅ Ready to Submit` with zero warnings, verdict `ready`, zero open findings,
and the auditor's extracted copy is byte-identical to the candidate, evidence
included. It refuses to overwrite an existing `Task_Ready_To_Submit/<task-name>.zip`.

A candidate rebuild invalidates the earlier auditor review automatically: the
new bytes no longer match the auditor's extracted copy or its task digest, so
`--promote` refuses until the new candidate is re-extracted and re-judged. Any
edit to anything after this point — task source, rubric, a rubric score —
means a new build, a new auditor review and a new promotion; the final grep
only counts when it is the last step.

## 5. Record

Write the ZIP SHA256, task digest, bundle sha, review SHA256 and the auditor's
`report.md` path next to the Step 3c report
(`authoring/<task-name>/step3c-report.md`, packaging section). The deliverable
is the promoted `Task_Ready_To_Submit/<task-name>.zip`. Exit only with the
build's `Package: PASS (candidate)` output, the auditor's `LINT_OK` line, the
promotion's `Package: PASS (promoted)` output, and the promoted ZIP listing.
