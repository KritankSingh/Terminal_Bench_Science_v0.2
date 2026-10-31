# Assertion traceability — <task-name>

Source of truth: `MASTER_CHECKLIST_TBSCI.md`. Step 3b cites these tables as
evidence for Master #1, #2, #12, #35, #41, #43, #46, #52, #60 and #100–#102, and
re-verifies every row on disk.

## Instruction sentence → test (Master #1, #2)

One row per declarative sentence of `instruction.md`. A sentence with no test is
a gap (#1) unless its only possible test would pass under NOP; a test with no
sentence enforces an unstated rule (#2, BLOCKER). The closing "You have 28800
seconds…" paragraph (#104) gets no row.

| instruction.md line | Sentence (quoted) | Requirement ID | Test(s) (file::name) |
|---|---|---|---|
| | | | |

## Environment doc → requirement → test (Master #12)

Every doc under `environment/` is a graded requirement. One row per rule a doc
states. A doc with no row is either tested or removed.

| Doc (path:line) | Rule stated | Requirement ID | Test(s) | Consistent with instruction.md? (#12) |
|---|---|---|---|---|
| | | | | |

## Requirement → test

| Requirement ID | Verifier assertion/test | Independent? | Public/held-out input | How the holdout changes the expected value (#46) | Negative control | Equivalent-output handling |
|---|---|---:|---|---|---|---|
| R-01 | | | | | | |

## Manifest plan

`tests/test_manifest.json` entries (`docs/TESTING_POLICY.md`): ID, requirement,
the one CTRF case it reports. Guard-style tests are coupled to a behavioral
assertion in the same function (#41, #42); fail-closed tests name their
positive control (#52).

| Manifest ID | Requirement | CTRF case | Guard coupled to (#41) | Positive control (#52) |
|---|---|---|---|---|

## Solution ablation (Master #35)

One row per file `solve.sh` touches: revert only that file to its shipped
state, keep every other fix, run the suite. Record the command and the tests
that failed. Every file, not a sample.

| Solution file | Defect/capability (instruction or doc source) | Tests that failed when ablated | Command / evidence path |
|---|---|---|---|

## Shortcut → named assertion (Master #60)

| Shortcut | Named assertion that rejects it | Control (NC-xx) |
|---|---|---|
| Empty submission | | NC-01 |
| Format-only fake | | NC-02 |
| Hardcoded public/example answer | | NC-03 |
| Self-reported metric | | NC-04 |
| Missing declared artifact | | NC-05 |
| Fake reward/report (incl. detached writer) | | NC-06 / NC-06b |

## Ground truth → source (Master #100)

Where each graded value comes from. Oracle-derived values are disclosed in
`write-ups.md` `## Verification` and defended by a varied oracle stage.

| Graded value / file | Independent source (generating model, cited value, second implementation) or "oracle-derived" | Evidence (provenance file, command, output) |
|---|---|---|

## Tolerance → justification (Master #101)

One row per inequality the tests apply. The independent implementation differs
from `solution/` in a structural choice; its code and runs live in
`authoring/<task-name>/calibration/`.

| Tolerance (tests file:line, literal) | What it brackets / legitimate variation absorbed | Method class (correct / defective / accepted equivalent) | Independent implementation result and margin | Reference result and margin | Defective method: which instance rejects it, miss margin |
|---|---|---|---|---|---|

## Trivial nulls per graded instance (Master #102)

| Graded instance | Constant | Range mean/median | Domain centre | Majority class | Copy-through | Public-answer replay | Reached by a null? (finding to fix, not disclose) |
|---|---|---|---|---|---|---|---|

## Byte-diff and grep evidence (Master #13, #20)

Output of the environment/ vs tests/ and solution/ byte-diff and of the literal
TODO/FIXME/BUG:/planted/deliberate/"for the grader"/"for the test" grep, with a
justification for every hit.

## Coverage summary

- Requirements without independent tests:
- Assertions without public requirements:
- Environment docs without tests:
- Coupled tests that need separation:
