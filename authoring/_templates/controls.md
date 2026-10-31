# Negative controls — <task-name>

Plan written at Step 2a, staged scripts authored at Step 2b, results written by
`scripts/gate_step2b.sh --with-nc` (via `scripts/controls_report.py`). Do not
edit the results section by hand.

## Plan

Source of truth: `MASTER_CHECKLIST_TBSCI.md`. Master #60 requires the empty
submission, a format-only fake, a hardcoded public/example answer, a
self-reported metric, a missing declared artifact, and a fake reward/report
(including a detached process rewriting it after the agent's turn) each to be
rejected through its **own named assertion**; reward 0 through a different,
unplanned test is a fail of that check. NC-01..NC-06b are the controls that
prove it. NC-07..NC-14 are optional diagnostics: a script, or `n/a` with a
reason grounded in the public contract.

Staged scripts live in `authoring/<task-name>/staged_controls/` and replace
`solution/solve.sh` in a staged copy of the task (`scripts/stage_controls.sh`).
`python3 scripts/nc_generate.py tasks/<task-name>` writes the task-agnostic
ones (NC-01, NC-05, NC-06, NC-06b, NC-09); author the rest. The expected
failure must be a case from `tests/test_manifest.json` (`task_check.py --strict`
warns otherwise), followed by the assertion or `failure_reason` that case is
expected to report.

| ID | Shortcut | Master #60? | Staged script | Expected named failure (CTRF case → assertion/failure_reason) | n/a reason |
|---|---|---:|---|---|---|
| NC-01 | empty/no-op | yes | generated (nc_generate.py) | | |
| NC-02 | format-only fake, every declared file present | yes | | | |
| NC-03 | hard-coded public/example answer | yes | | | |
| NC-04 | self-reported metric without the work | yes | | | |
| NC-05 | one declared artifact missing | yes | generated (nc_generate.py) | | |
| NC-06 | fake reward/CTRF written from the agent side | yes | generated (nc_generate.py) | | |
| NC-06b | detached process writing reward/CTRF after solve.sh exits | yes | generated (nc_generate.py) | | |
| NC-07 | correct but naive baseline | optional | | | |
| NC-08 | primary axis passes, second stated requirement violated | optional | | | |
| NC-09 | correct value printed, not persisted | optional | generated (nc_generate.py) | | |
| NC-10 | visible-size / first-N / sorted-input / one-boundary shortcut | optional | | | |
| NC-11 | protected input or baseline tampered | optional | | | |
| NC-12 | PATH shim / shadow module / wrapper returning success | optional | | | |
| NC-13 | smallest-scale-only or warm-cache-only | optional | | | |
| NC-14 | fits public examples, fails a legal unseen variant | optional | | | |

## Trivial nulls (Master #102) are not controls

The science-free nulls of Master #102 (a constant, the mean or median of the
allowed range, the domain centre, the majority class, copy-through) are run per
graded instance and recorded in `traceability.md`, not here. A null that
reaches an instance is named in `write-ups.md` `## Verification`. Where a null is
also a #60 shortcut (a hard-coded constant is NC-03), the control row above
names its assertion as usual.

## Gate results

Filled by `scripts/controls_report.py` when `scripts/gate_step2b.sh --with-nc`
finishes (or on `--nc-only`). It appends a `## Gate results — <digest>` section
with the per-test Oracle/NOP summary and one row per control: reward, failing
CTRF cases, and PASS/FAIL against the plan above. A control that rewards `0`
through a case other than the planned one is a FAIL. Step 3b compares the
digest in that heading with the one `scripts/evidence.py check` prints and
cites these rows for Master #60.

## Exceptions and reruns

Record any job that was repeated, with the reason and both job names. Never
delete a failed job directory.
