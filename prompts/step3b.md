> **Lean workspace.** This long prompt is reference. The review itself is step 4 of
> docs/WORKFLOW.md: fill `authoring/<slug>/review.md` (16 points) and run
> `python3 scripts/tbsci.py review <slug>`, which fills the master record and runs
> `master_checklist.py check --stage review`. After review the task is PARKED until
> `config/round.toml` says CONFIRMED.

# Step 3b — Independent paper review

`MASTER_CHECKLIST_TBSCI.md` is the source of truth, and this step is where it
is walked. Read `docs/PROCEDURES.md` (section 3b), `docs/reference/TBSCI_REVIEW_BLOCKERS.md`,
`docs/reference/QC_AUDIT_RUBRIC.md`, `docs/reference/QUALITY_GUIDELINES.md`,
`docs/TBSCI_HARDENING_RULES.md`, `docs/TASK_COMPONENTS.md` and
`docs/TASK_TAXONOMY.md`. Task path: `tasks/<task-name>`. You did not
author this task; do not edit it, run model trials, or package.

## 1. Bind to the sealed evidence

Step 3b starts as soon as the Step 2b seal exists.

```bash
source .venv/bin/activate
python3 scripts/evidence.py check tasks/<task-name> \
  --evidence artifacts/gates/<task-name>/step2b.json
python3 scripts/task_check.py tasks/<task-name> --strict
python3 scripts/master_checklist.py auto tasks/<task-name>
python3 scripts/audit_task.py tree tasks/<task-name>
```

`Evidence readiness: PASS` and the printed `Task digest:` are the only things
that tie your review to a task version. If the check fails, stop and send the
task back to Step 2b; do not review a task whose seal is stale. If
`authoring/<task-name>/master-checklist.md` does not exist yet, create it with
`python3 scripts/master_checklist.py init tasks/<task-name>`.

`audit_task.py tree` runs the bundled auditor's screen
(`tools/final-tbsci-audit-master/`) on the task staged in delivery layout; it
must print `PASS` (the gate already required it at step c1 — a FAIL now means
the tree moved and goes back to Step 2b). `master_checklist.py auto` groups the
same auditor findings and `LEAD` lines by master number, prefixed `AUDITOR`.
Every auditor `LEAD` printed by either command is a question you answer.

Read `authoring/<task-name>/controls.md`: the plan table and the
`## Gate results — <digest>` section written by `scripts/controls_report.py`.
The digest in that heading must equal the one `evidence.py check` printed.
Compare predicted and actual failing CTRF case names control by control; a
control that rewarded `0` through a different case than planned is a FAIL of
Master #60 for that shortcut, because the planned assertion is untested.

## 2. Walk the master checklist, check by check

Reconstruct the public contract from `instruction.md` and solver-visible files
before reading hidden expectations. Then walk `MASTER_CHECKLIST_TBSCI.md` in
order and fill `authoring/<task-name>/master-checklist.md`. Each record line
reads `#<N> | <VERDICT> | <evidence>`.

Checks whose single verdict reads the five packaged runs stay `PENDING`.
Do the pre-trial parts of #1, #2, #15, #40, #53, #57 and #101 now (the
instruction↔test map, lore/notes files against `rubric.txt`, the gate's
per-test NOP and ctrf shape, the absence of a wall-clock assertion, and the
tolerance measurement) and put that evidence on the PENDING line
(`#N | PENDING | <file:line, quote, or command output>`). An empty line fails
review. #33 has no
pre-trial part. Step 4 records the single verdict for #1, #2, #15, #33, #40,
#53, #57, #70, #71–#94, #101 and #107 against the five runs and the packaged
oracle/NOP evidence. #96 and #97 judge the zip and stay `PENDING` until Step 4.
A `PASS`, `N/A`, `AUTO` or `FAIL` on any of those trial-evidence lines fails
`--stage review`: an answer recorded before the trials existed is not an answer.

Rules for every line:

- **Verdict + evidence on every line.** `PASS` needs evidence you produced now:
  `file:line`, quoted text, or command output. `N/A` needs a reason and is only
  for conditional checks (e.g. #30 when no named algorithm is graded, #54 when
  the verifier executes no agent code, #102 when only one instance is graded).
  `AUTO` only where a script enforces the check mechanically and you saw it
  pass (in Section J that is #104; #105 is a merged placeholder, N/A; `master_checklist.py auto` lists
  every AUTO-eligible number). `FAIL` carries the evidence and the
  required fix. `PENDING` is not a verdict on a check this step answers. On #1, #2,
  #15, #33, #40, #53, #57, #70, #71–#94, #96, #97, #101 and #107 it is the
  required Step 3b state. On #1, #2, #15, #40, #53, #57 and #101 that PENDING
  line still carries the pre-trial evidence. Empty evidence there fails review.
- **Nothing from memory.** Re-verify every check against the disk state in
  front of you. The author's traceability, a clean `auto` run, or Oracle 3/3 is
  material for the review, never the review itself (Master #30: Oracle passing
  proves self-consistency, not correctness).
- **Do the work the check names.** Map instruction sentences to tests both ways
  (#1, #2); grep tolerances and constants literally (#6); byte-diff
  environment/ against tests/ and solution/ (#20); map every environment doc to
  its tests (#12) and every notes/lore-style file against `rubric.txt` (#15);
  read every COPY/ADD line (#24); read the Step 2b ablation record for every
  solution file and spot-rerun at least one (#35); read every test's body, not
  its name (#43); confirm each holdout changes the outcome (#46); read the
  per-test NOP stdout and confirm each failure is an assertion mismatch (#40,
  #74); check for any wall-clock timing assertion (#57); confirm binary reward
  and identical Oracle/agent logic (#58); check `task.toml` field by field
  (#61–#65: top-level `name` and `artifacts`; `domain`/`field`/`subfield`,
  `tags`, `expert_time_estimate_hours`, `relevant_experience`; no `difficulty`
  or tier/percentage/pass count anywhere in the task or in
  `authoring/<task-name>/write-ups.md`; no
  top-level `version`, no retired `category`/`subcategory`/`languages`, no
  `*_explanation` key; author fields non-empty when present; `schema_version`
  present or absent is not a finding; timeouts `28800`; both network modes
  declared; `cpus`/`memory_mb`/`storage_mb` sized to the task, `gpus = 0`);
  check `rubric.txt` format, budget and mapping (#66–#69); classify what
  makes the task hard in plain language (#95).

- **Walk Section J as a scientist in the field would (#98–#106).** Name the
  field and confirm the task is that field's work once the tool names are
  stripped — generic software or data munging in scientific vocabulary is out
  of scope (#98). Confirm the work is research-level, needs domain judgment,
  and that its answer is not one web search or one remembered published result
  away; try the obvious searches yourself (#99). Open
  `authoring/<task-name>/provenance/` and confirm every dataset's origin and
  where every graded value comes from, independent or oracle-derived and
  disclosed in `authoring/<task-name>/write-ups.md` `## Verification` (#100). For every tolerance, find
  the independent implementation run that measured it, the correct/defective
  classification and the 10% margins on the shipped instances; a bound only the
  reference clears is a finding (#101; no fresh-draw study is required). Where
  instances come from a generator and a method's smallest shipped-set margin is
  under 20%, the default internal check is 3 fresh unselected draws, increased
  to 6 if those 3 are borderline or inconsistent; a correct method that fails a
  draw, or a defective method that passes one, is a margin finding. Not running
  the probe is never a finding. Record this measurement in the review. The #101
  line stays `PENDING` until Step 4, which cites it against the packaged runs.
  Read the trivial-null record per graded instance (#102). Confirm the task
  carries no README.md, and read `write-ups.md`'s three sections against
  `solution/` and `tests/` — they must describe what the code actually does,
  for a non-domain reader (#103). Confirm the instruction
  suffix byte for byte (#104), the verifier network and baked tooling (#64, #38),
  and the #106 portability rules in every Dockerfile, `test.sh` and `solve.sh`.

- **Walk the lettered checks the master assigns.** A rule that cannot change a graded verdict is a NOTE, not a FAIL (preamble materiality; #2, #6, #102): epsilon slack at the data's precision, an accepted equivalent such as 3.0 for 3, a round value in a wide band with no method producing it. A test stricter than the instruction is still a BLOCKER (#6). Every `FROM` digest is multi-arch, or the single architecture is recorded (#26(a)); otherwise NOT VERIFIED naming the registry query. After agent code runs, root never writes inside a sandbox-writable directory, and multi-run scratch sits under root-owned `/work` (#54(c): secret or reward exposure is BLOCKER; an unshown survivor path is MAJOR). A subset selector never writes reward 1 for the whole task, and an unknown selector fails closed (#58(c)). A capped prover, sampler or optimiser accepts a certificate that meets the stated condition by a comfortable multiple of the margin (#59(c); N/A when grading is not a capped search; a cap that rejects a valid answer is a BLOCKER).

- **Answer every auditor lead.** Each `AUDITOR ... LEAD` row from `auto` (or
  from `audit_task.py tree`) is answered with evidence (`file:line`, quoted
  text or command output). A lead on a check answered at this step goes on
  that master line. A lead on #1, #2, #15, #40, #53, #57 or #101 is the
  evidence on that `PENDING` line. A lead on #33 is answered in this review;
  that line stays `PENDING` with no pre-trial evidence. Step 4's verdict cites
  the answer plus the runs. A lead with no master number is
  answered in the review. An unanswered lead on a check this step answers
  leaves that check `PENDING`.

## 3. Walk the auditor's gates

Then walk the bundled auditor's `tools/final-tbsci-audit-master/CHECKLIST.md`
gate by gate — **T, then A → K** — against the task tree, reading its
calibration list in `SKILL.md` ("Do not false-flag") so you neither miss nor
invent findings. Every gate item gets pass / fail / n/a with quoted evidence
and its "Master #N"; the TB-Science items (taxonomy, no README.md, suffix,
network, portability) map to Section J. Items that need packaged evidence (gate T's
`oracle-nop-evidence/`, `trajectories/` and `SUMMARY.txt`, gate H, the trial
half of gate I) are marked "Step 4" — the auditor's judged review of the
candidate ZIP answers them. Gate J (corpus novelty) is out of the auditor's
scope; Master #95 still applies. The auditor asks the reading questions the
screen cannot: where every expected value comes from, what executed agent
code can read at grade time, whether a hand-written artifact would pass, and
whether every "do not modify" is enforced. Any gate failure is a finding.

Also walk `docs/reference/TBSCI_REVIEW_BLOCKERS.md` and score `docs/reference/QC_AUDIT_RUBRIC.md`;
both point back to the same master checks.

When the walk is complete:

```bash
python3 scripts/master_checklist.py check tasks/<task-name> --stage review
```

It must pass: zero `FAIL`, and `PENDING` only on #1, #2, #15, #33, #40, #53,
#57, #70, #71–#94, #96, #97, #101 and #107 (merged #81 and #82 stay `N/A`).
#1, #2, #15, #40, #53, #57 and #101 carry pre-trial evidence on that PENDING
line. Evidence on every `PASS`, a reason on every `N/A`, bound to the current digest.

## 4. Write the review

Write the same content to both paths:

- `authoring/<task-name>/step3b-review.md`
- `artifacts/reviews/<task-name>.md`

Begin the file with exactly these unindented lines, one occurrence each, values
taken from the evidence check (this is the format `scripts/stage_reports.py`
checks; Step 3c and Step 4 refuse a review without it):

```text
Task: <task-name>
Task digest: sha256:<current-task-digest>
Verdict: READY FOR DIFFICULTY EVAL
```

Below the header: every finding labelled BLOCKER / MAJOR / MINOR (Master
definitions — labels order the fix work, they never decide what ships), with
`file:line`, the master check number, and the required action; evidence paths
(seal, `OUT` directory, job names); the `master_checklist.py check` output;
the `audit_task.py tree` result line, every auditor `LEAD` with its answer, and
the gate T/A–K walk; and the program quality scenarios from
`authoring/_templates/step3b-review.md`.
Record the SHA256 of the finished review file; Step 3c's report binds to it.

## 5. Verdict rule

`Verdict: READY FOR DIFFICULTY EVAL` only when all of these hold:

- the gate's `progress` file ends in `VERDICT: PASS` for the current digest;
- `master_checklist.py check --stage review` passes;
- `audit_task.py tree` prints `PASS` and every auditor `LEAD` is answered with
  evidence;
- the auditor's gates T and A–K raise nothing on the tree;
- there is **no open finding of any severity** — from the master walk, the
  auditor gates, the blockers doc or the QC rubric. A MINOR finding blocks exactly
  like a BLOCKER — "Minor" describes the size of the fix, not permission to
  leave it.

Otherwise — and on any finding of any severity — `Verdict: NEEDS REVISION`.
Exit only as `READY FOR DIFFICULTY EVAL` or `NEEDS REVISION`, with the
evidence-check, `master_checklist.py check` and `audit_task.py tree` output
pasted. If a task file must change, stop: the fix happens under Step
2b, the gate reruns on a fresh digest, and Step 3b restarts from section 1 with
a fresh walk of every check. A `write-ups.md` fix touches no task file and
needs no re-seal (re-walk #99–#103). The one exception is a descriptive-only
fix — a descriptive `[metadata]` key — which re-seals with
`gate_step2b.sh tasks/<task-name> --reseal-only` (it refuses unless both graded
digests are unchanged), then `python3 scripts/stage_reports.py rebind-review
tasks/<task-name>` after you re-walk the checks the edit touches (#61, #62,
#98–#103) and re-head the master record's `Task digest:`.
