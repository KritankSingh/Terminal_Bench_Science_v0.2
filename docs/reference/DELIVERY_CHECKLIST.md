# Delivery checklist — package your task like this before calling it done

> **`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth** and outranks this
> file. This checklist is the delivery-format view of it (master Sections E–I); every
> line below agrees with the master, and where anything seems to differ, the master
> wins. A task ships only when `authoring/<task>/master-checklist.md` answers every
> master check with evidence (`python3 scripts/master_checklist.py check tasks/<task>
> --stage package`), the candidate ZIP passes `scripts/verify_package.py` and the bundled
> auditor (`tools/final-tbsci-audit-master/`), the auditor's judged review of that exact
> candidate lints `✅ Ready to Submit` with zero warnings, and
> `scripts/package_task.py --promote` copies it to `Task_Ready_To_Submit/`. Tasks are
> prepared for private delivery to a buyer: "delivery" means a promoted local ZIP,
> nothing is submitted anywhere (the `Task_Ready_To_Submit/` name is kept because every
> script uses it).

## Folder structure (exactly this, nothing else, one zip per task)

```
<task-slug>/
├── <task-slug>/                (named after the actual task — NEVER the literal word
│                                 "task" or "bundle" — ONLY these 5 go in here)
│   ├── instruction.md          (ends with the "You have 28800 seconds…" suffix — Master #104)
│   ├── task.toml               (NO top-level version line and NO difficulty field
│   │                             (Master #62, #65); schema_version optional.
│   │                             [agent].timeout_sec, [verifier].timeout_sec and
│   │                             [environment].build_timeout_sec are all 28800 from
│   │                             creation (Master #63) — see below)
│   ├── environment/
│   ├── solution/
│   └── tests/
├── rubric.txt                  (sibling of the task folder — NOT inside it)
├── oracle-nop-evidence/         (sibling of the task folder — NOT inside it)
│   ├── oracle-1/   (ctrf.json, reward.txt, test-stdout.txt)
│   ├── oracle-2/
│   ├── oracle-3/               (oracle x3 — all reward 1.0, every test passing)
│   ├── nop-1/
│   └── nop-2/                  (nop x2 — all reward 0.0, every test failing)
└── trajectories/                (sibling of the task folder — NOT inside it)
    ├── run-01/   (agent/, verifier/, config.json, result.json, and a rubric_score.txt
    │              you write yourself — see the section below — that trial's own files only)
    ├── run-02/
    ├── run-03/
    ├── run-04/
    ├── run-05/                 (5 real GPT-5.6 xhigh runs)
    └── SUMMARY.txt             (required, not optional — exact format below)
```

`<task-slug>/`, `rubric.txt`, `oracle-nop-evidence/`, and `trajectories/` are four siblings
at the top level of the zip. Nothing else lives inside the inner `<task-slug>/` besides the
5 items above (`instruction.md`, `task.toml`, `environment/`, `solution/`, `tests/`).
No `README.md` anywhere in the zip — the write-ups (`## Difficulty`,
`## Reference solution`, `## Verification`) stay in the workspace as
`authoring/<task>/write-ups.md` and are never given to the agent (Master #103). No `task/` or `bundle/` wrapper — the folder must be named after the actual
task. No `SOURCE.txt`, no `.DS_Store`, `__MACOSX`, `._*`, `.git`, `__pycache__`, `*.pyc`
anywhere in the zip.

`reasoning_effort` and its value `xhigh` are REQUIRED, legitimate capture metadata — they
belong in every trajectory `config.json`. Never rename the key (e.g. to `effort`) or change
the value (e.g. to `high`) for any reason (Master #91). Never hand-edit a captured
`result.json` field such as the nested model name (Master #89). The only rewrite packaging
makes to captured files is replacing host paths (`task.path`, `trials_dir`, …) in each
run's `config.json`/`result.json` with repo-relative ones, because zero `/Users/`,
`/private/tmp/`, host `/home/<you>/` or word-boundary `stb` hits may ship (Master #87).

## Before marking a task ready for delivery, confirm every line below

- [ ] Task name is fully descriptive of what the task actually is — no version suffixes,
      no internal codenames, and specifically **no `hardened`/`harden`-style suffix**
      (e.g. never `<task>-hardened`, `<task>-v2-hardened`, `<task>_harden3`) anywhere in
      the slug, the folder name, or `task.toml`'s top-level `name`. Whatever internal round
      or hardening pass a task went through is process history, not part of its name —
      the shipped name should read like the scientific workflow it is, nothing else. Check
      `instruction.md` and `environment/` too, not just the folder name.
- [ ] No manufactured difficulty — every graded rule traces to a sentence in `instruction.md`
      or a doc it points to, or is standard practice an independent expert in the field
      applies unprompted (Master #0). Every tolerance is justified by the science and
      measured on an independent correct implementation with 10% margins on the
      shipped instances (Master #101; no fresh-draw study). Where instances come
      from a generator and a method's smallest shipped-set margin is under 20%,
      the default internal check is 3 fresh unselected draws (6 only if those 3
      are borderline or inconsistent); not running it is never a finding. No tight
      tolerances, hidden formats, private vocabulary, or timing races invented just to make
      it hard (Master #95).
- [ ] The task is a research-level scientific workflow in the `domain`/`field` it declares,
      on real or realistic data whose provenance is recorded, and its answer is not
      reachable by web lookup or memorization (Master #98–#100). The write-ups'
      `## Verification` (`authoring/<task>/write-ups.md`) says where the graded reference values come from (independent, or
      oracle-derived and disclosed). Every withheld instance is one no trivial null
      reaches (Master #100, #102).
- [ ] No senseless folder/file names (`ak`, `bks`, `wqt`, etc.) — every path should read
      like something a real researcher or engineer on this project would have written.
- [ ] No comments or docstrings anywhere that reveal a defect or a planted decoy
      (`TODO`, `FIXME`, `planted`, `deliberate`, `for the test/grader`, etc.).
- [ ] No solution leakage into `environment/`. If `solution/` is a `solve.sh`-style patch
      script (not a full mirrored tree), don't bother diffing directory trees — that's
      structurally noisy and produces false positives, since the patch script necessarily
      shares filenames and unchanged boilerplate with `environment/`. Instead check: (a)
      `environment/`'s Dockerfile never `COPY`s or otherwise bakes in `solution/`, (b)
      `instruction.md`/`environment/` never references `solve.sh` or a `solution/` path,
      and (c) your nop evidence (raw, unmodified environment) reliably scores reward=0.0 —
      that's the authoritative, pipeline-verified proof the fix isn't silently pre-applied.
- [ ] No reward-hacking behavior in any trajectory — a passing run must be a genuine fix,
      never reading the tests, disabling an assertion, or hard-coding an expected value.
      Every trial is classified against the eight trial-analysis criteria in the Step 3c
      report, and none indicts the task (Master #107).
- [ ] No false failures, and no agent/verifier timeout failures — with the timeouts set as
      above, a failure must be a real, knowable rule violation, never the clock running out.
- [ ] Every trajectory is complete — no truncated tool output, full API/message log,
      `reasoning_effort=xhigh` confirmed on every run.
- [ ] Ran at k=5; record the real pass rate (0/5 through 3/5 only acceptable for now — just
      report it honestly, don't discard or rerun a trial you don't like the result of). A
      run is replaced only for a populated `exception_info` (key exhaustion, timeout,
      infrastructure error — Master #92) or a failed capture check, never for its reward.
      The five runs are the first five fidelity-complete trials at the current digest and
      run config, in launch order across rounds, no valid attempt skipped (Master #94 item
      1): run-01..run-05 carry distinct `result.json` trial ids and strictly increasing
      `started_at`, one `task_checksum` and one agent configuration.
- [ ] The measured rate lives in the workspace difficulty report and in SUMMARY.txt's
      reward array — **never in the task**. `task.toml` has no `difficulty` field, and no
      tier label, percentage or pass-count appears anywhere in the task; the write-ups'
      `## Difficulty` is plain language about what makes the task hard (Master #62,
      #103).
- [ ] `task.toml` carries no top-level `version` line, no `[task]` table, milestone field,
      `codebase_size`, minute-based estimate, `[reference_pattern]` or other generator
      bookkeeping, and no real local machine path; `schema_version` is optional; `cpus`,
      `memory_mb`, `storage_mb` and `gpus = 0` are declared (Master #65). `artifacts` is
      top-level; `[metadata]` carries exact `domain`/`field`, a non-empty `subfield`, 3–6
      tags, `expert_time_estimate_hours` and a substantive `relevant_experience`; author
      fields are optional and non-empty when present; no `category`/`subcategory`/
      `languages` and no `*_explanation` keys (Master #61).
- [ ] `[environment].network_mode = "public"` and `[verifier.environment].network_mode =
      "no-network"` are both declared (Master #64).
- [ ] The task carries no `README.md` and no write-up file ships;
      `authoring/<task>/write-ups.md` has three non-empty sections, exactly
      `## Difficulty`, `## Reference solution` and `## Verification`, current with what
      `solution/` and `tests/` actually do (Master #103).
- [ ] Every `trajectories/run-0N/` has its own `rubric_score.txt`, and `trajectories/` has
      one `SUMMARY.txt` — both in the exact formats below, with zero explanatory notes.
- [ ] Oracle x3 and NOP x2 are genuinely independent executions (distinct ctrf.json and
      start timestamps — Master #76); every NOP failure is a real assertion
      mismatch, not a setup/import/collection error (Master #74).
- [ ] Every shipped evidence file is bound to the current digest; mtimes are secondary
      (Master #75) — an edit after capture means new evidence, whatever the sha says.
- [ ] `authoring/<task>/master-checklist.md` answers all master checks for the current
      digest with evidence, zero FAIL (`master_checklist.py check --stage package`).
- [ ] The bundled auditor has reviewed **this exact candidate ZIP** and it lints
      `LINT_OK  ✅ Ready to Submit  (0 warning(s))`: every screen finding dispositioned,
      every LEAD answered, manual probes and cheat simulation recorded, zero open findings
      of any severity. Only then `package_task.py --promote`.

## rubric.txt format — exactly this, every task, no exceptions

Every line is one criterion, nothing else:

```
Agent <does or fails to do something specific>, +N
Agent <does or fails to do something specific>, -N
```

- No `#` headers, no titles, no comments, no blank lines, no format-instructions-to-self.
  Not `# Rubric 1`, not `# <Task Name> - Task Rubric`, not `# Format: ...` — nothing but
  criterion lines. Different tasks in this project have used at least four different
  header styles; none of them are correct. The file is criteria only.
- Every line starts with the literal word `Agent`. If the natural phrasing doesn't put
  "Agent" first (e.g. "A sync commits...", "The report's row counts agree..."), rephrase
  it — "Agent's sync commits...", "Agent keeps the report's row counts in agreement..." —
  never drop the requirement to make the sentence read more naturally.
- No `[tests: ...]` bracket citations or any other inline annotation. State the criterion
  in plain language; don't cite test function names inside the rubric.
- The sentence flows directly into `, +N` or `, -N` with no period before the comma and
  nothing after the number.
- Positive criteria describe what a correct fix does; negative criteria describe specific
  failure/hack modes (hardcoding, editing tests, bypassing the real pipeline, partial
  fixes) — nearly every task should have both.

**Before shipping, confirm `rubric.txt` actually has content.** One task in this project
shipped with a rubric.txt containing only a placeholder header and a single throwaway
sentence — zero real grading criteria — and it was reviewed and marked "consistent" by
a check that only compared existing rubric lines against the tests, without noticing
there were no lines to compare. Checking a rubric against the tests only catches wrong
criteria; it does not catch a MISSING rubric. Explicitly confirm the file has one line
per test/failure-mode you expect it to cover before calling it done.

## No explanatory notes, anywhere — we do not owe an explanation

`SUMMARY.txt` and every `rubric_score.txt` are DATA files, not writeups. No prose about
what you fixed, why a number changed, what an earlier draft got wrong, or how you verified
something. If you're tempted to write a "note:" — delete it, not append it. This applies
even when the note is accurate and even when it would be genuinely useful context for you —
it still doesn't ship. This project shipped several of these notes before catching it: a
`SUMMARY.txt` that narrated a truncated-run replacement's history, a `rubric_score.txt` that
appended a paragraph justifying a correction. Both were stripped back to bare data. Keep
that discipline from the start instead of writing the explanation and then having to remove
it later.

`trajectories/SUMMARY.txt` is exactly two lines, nothing else:
```
<task-slug> sha=<hash> model=gpt-5.6 (reasoning_effort=xhigh)
5 runs, rewards: [r1, r2, r3, r4, r5]
```
`model=` is the stripped name (Master #77): drop everything through the last `/` and a leading `@`, so `@openai/gpt-5.6` and `openai/@openai/gpt-5.6` both become `gpt-5.6`. Each run's `config.json` keeps the provider form.
Recompute both the sha and the rewards fresh from what's actually on disk right now — don't
hand-edit stale numbers forward from an earlier draft. The sha is the **bundle sha** of the
inner task folder, which a reviewer recomputes from inside it with relative paths
(Master #80):
```
cd <task-slug>/<task-slug> && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
```
`scripts/bundle_sha.py` prints the same value; `package_task.py` writes it and
`verify_package.py` recomputes it from the finished ZIP.

## rubric_score.txt — one per trajectories/run-0N/, required

For each of the 5 runs, write `trajectories/run-0N/rubric_score.txt` scoring that specific
run against every line of `rubric.txt`:
```
reward=<0.0 or 1.0>
tests_passed=<N>/<M>

<rubric.txt line verbatim>, +N -- MET
<rubric.txt line verbatim>, +N -- NOT MET
<rubric.txt line verbatim>, -N -- TRIGGERED
<rubric.txt line verbatim>, -N -- NOT TRIGGERED

gradient: X/Y positive met, X/Y negative triggered
```
Nothing else in the file — the evidence for each verdict goes inline in parentheses on that
same line (see below), not as a trailing note. **Every** verdict line carries its
parenthetical citation (`-- MET (…)`, `-- NOT TRIGGERED (…)`); packaging refuses a verdict
without one (Master #78, #86). The five files are each written from their own run and are
never copies with the header swapped (Master #85); the gradient line is the arithmetic of
the verdicts above it (Master #70). A method-worded line is scored on whether that run
did the method; a later test failure does not by itself make it NOT MET. An outcome-worded
line is scored on that outcome. A quoted number may be a faithful rounding of the value
at that step (Master #86). Across the five runs the rubric orders them the same way the
reward does; N/A when all five rewards match (Master #70(b)).

**The evidence bar for every verdict, positive or negative:** open the run's
`agent/trajectory.json`, find the tool call where the agent writes its actual solution code
(a bash heredoc, `cat > file.ext <<'EOF' ... EOF`, inside a `bash_command` tool call's
`arguments.command`), and check that code against what the rubric line literally claims.
Cite the specific function, variable, or line you found, e.g.:
`Agent ranks candidates by the shard loss recorded with them, -4 -- NOT TRIGGERED (Select()
in CheckpointSelector.cs ranks by Training.ValidationLoss(), never reads ShardLoss)`.

**A failing test is not evidence a negative criterion was TRIGGERED.** For every failing
run, read the actual failure in that run's own `agent/trajectory.json` and
`verifier/test-stdout.txt` before writing its verdicts (Master #84), and spot-check MET
verdicts on passing runs too — an overclaimed MET is as real a defect as a wrong NOT MET.

**No verdict contradicts the run's own failure.** The code is where a verdict starts, not
where it ends. `test-stdout.txt` names each failed case's cause (`FAILED <case> -
<message>`, `docs/TESTING_POLICY.md` rule 7).

- **A failure line decides only the behaviour it names.** A criterion is NOT MET on a
  failure line when the line shows that specific behaviour going wrong, such as
  collisions against a "checks for collisions" line or a reported heading error
  against a "reaches the goal heading" line. The verdict cites that line. Complete-looking
  code or success on the public examples doesn't outweigh it.
- **A failed case or group is not a failed criterion.** A case that failed through a
  collision, a hang or a real-time timeout says nothing about the other behaviours it
  exercises. A bare timeout that names no cause decides no criterion on its own.
- **Judge undecided criteria from the rest of the run.** Use the hidden cases that passed
  and the trajectory, cite them, and apply one standard across all five runs.
- **Overscoring and underscoring are both defects.** Over-penalizing an unrelated
  criterion is as much a defect as an overclaimed MET.
- **Step citations must be exact.** Each points to the step where the quoted code or
  words first appear.

A `test-stdout.txt` without failure lines means the verifier predates rule 7. Fix
`tests/` by the regrade route before scoring.

## How to build the evidence

- **Oracle** = your own correct solution run through the verifier, 3 separate times.
  Every time: reward 1.0, every test passing.
- **NOP** = an empty/no-op submission run through the verifier, 2 separate times. Every
  time: reward 0.0, every test failing — `failed`, through a real assertion against the
  do-nothing behavior, never an error or skip (Master #40, #73, #74).
- **Trajectories** = 5 real attempts by gpt5.6 xhigh effort,
  captured in full (no truncated output, full message/API log kept).

Never zip by hand. Packaging is build → audit → promote:

1. `python3 scripts/package_task.py tasks/<task> --step3c-dir tasks/<task>/trajectories/<round>`
   builds a **candidate** at `artifacts/package-candidates/<task>/<task>.zip`. It refuses
   without a complete master record, recomputes every reward and the SUMMARY from disk, and
   runs `scripts/verify_package.py` (Master #97, the literal last-step grep) and the bundled
   auditor's scripted legs (`scripts/audit_task.py package`) on the finished candidate,
   deleting it on any finding.
2. The auditor's judged review of that candidate, per `tools/final-tbsci-audit-master/SKILL.md`:
   `review.sh extract <candidate>` → `review.sh audit <task>` → read, walk gates T and A–K,
   answer every LEAD, run the probes, fill `verdict.json` and `manual_probes.txt` →
   `review.sh lint <task>` must print `LINT_OK  ✅ Ready to Submit  (0 warning(s))`.
3. `python3 scripts/package_task.py tasks/<task> --promote` copies the exact audited bytes to
   `Task_Ready_To_Submit/<task>.zip`, and refuses if the candidate or the task moved since the
   build, or the review is not of these bytes.

The promoted ZIP is the whole delivery.
