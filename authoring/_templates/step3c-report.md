Task: <task-name>
Task digest: sha256:<digest>
Review SHA256: sha256:<sha256-of-step3b-review>
Evaluation policy: @openai/gpt-5.6 reasoning_effort=xhigh via stb harbor (bundled harbor patched, stb <version>); Terminus-2 recording adapter; five model attempts (<task>-gpt56-t1..t5); Oracle x3; NOP x2; uncapped terminal observations; raw API log; fidelity PASS; acceptance band measured 0/5-3/5
Trial evidence: tasks/<task-name>/trajectories/evidence-<task-name>/; evidence-<task-name>/collection.json; evidence-<task-name>/SOURCE.txt; evidence-<task-name>/fidelity-check.log
Verdict: READY FOR PACKAGING | TOO EASY | NEEDS REVISION

# Step 3c report — <task-name>

Source of truth: `MASTER_CHECKLIST_TBSCI.md`. Header format: `prompts/step3c.md`
section 5 (checked by `scripts/stage_reports.py`). This report and
`artifacts/difficulty/<task-name>.md` are the only places the measured rate is
written. Never copy it, a tier word, a percentage or a pass count into
`task.toml` or any task file (Master #62).

Round: <OUT name>
Resolved agents/models/settings: <from <OUT>/SOURCE.txt: model, reasoning_effort, stb/harbor versions, capture flags>
Validity: CLEAN | CONTAMINATED | INVALID | INCOMPLETE
Results decision:
Measured rate: <k>/5 (raw rewards: [r1, r2, r3, r4, r5])

## Frozen configuration and capture inventory

## Assertion-to-contract matrix

## Trial audit

Ten rows: five model trials, oracle-1..3, nop-1..2.

| Trial ID | Model/control | In denominator? | Reward | exception_info (#92) | Classification | First blocker or success proof | Evidence |
|---|---|---:|---:|---|---|---|---|

## Trial analysis (#107)

Every model trial, passing and failing, against the eight criteria of upstream
`rubrics/trial-analysis.toml` — PASS / FAIL / N/A with the trajectory step or verifier
line that decides it. Any FAIL on a task-side criterion (the first four) indicts the
TASK: fix it at a fresh digest, never ship. `unearned_credit` FAIL is a reward-hacked
pass (#93); `policy_refusal` / `execution_blocked` FAIL removes the trial from the
defensible rate (#92, AGENTS.md rule 21).

| Trial | specification_completeness | solution_discoverability | verifier_correctness | boundary_fairness | policy_refusal | execution_blocked | unearned_credit | meaningful_difficulty |
|---|---|---|---|---|---|---|---|---|

## Failure analysis (#33, #84)

Per failing run: the failure read from its own `agent/trajectory.json` and
`verifier/test-stdout.txt`, with the step/line Step 4 will cite.

## Success, shortcut, and generalization analysis (#93)

Per run: reads/writes of `/tests`, `test_outputs.py`, `ctrf.json`,
`reward.txt`, `/logs/verifier`, `solution/`; hand-written outputs; truncation
markers; genuine completion step.

## Cross-run duplication (#83)

## Control reconciliation (#72–#74)

Oracle x3 every test passing; NOP x2 every test failing on a genuine assertion.

## Raw and defensible rates

## Reruns and the shipped five (#92, #94)

Every round at this digest by name. For a composed round, the candidate table from
`composition.json` (launch position, start time, trial ID, validity, selected /
excluded / not selected and the recorded outcome-independent reason); confirm the
five are the first five fidelity-complete trials in launch order with none skipped,
and that all six items of #94 moved together.

## Limitations and final decisions

## Packaging

Filled at Step 4: candidate ZIP SHA256 (`artifacts/package-candidates/<task-name>/<task-name>.zip`),
auditor review path and lint line (`tools/final-tbsci-audit-master/audit/<task-name>/latest/`,
`LINT_OK  ✅ Ready to Submit  (0 warning(s))`), promoted ZIP SHA256
(`Task_Ready_To_Submit/<task-name>.zip`, equal to the candidate's), task digest,
bundle sha, review SHA256.
