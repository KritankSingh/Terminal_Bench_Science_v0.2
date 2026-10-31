# Per-Test Validation Policy (Terminal-Bench Science)

`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth; Section D
(Master #37–#60), the evidence checks #40, #53, #72–#74 and the TB-Science checks
#100–#102 (Section J) govern everything on this page, and the master wins where they differ. Package-level rules (what
ships, rubric syntax, trajectory inventory) sit below it in
`docs/reference/DELIVERY_CHECKLIST.md` and `docs/reference/PACKAGE_RULES.md`.

Aggregate suite scores hide weak, coupled, or baseline-passing tests. This
workflow therefore makes the **individual verifier test** the unit of Oracle/NOP
evidence, inside the Terminal-Bench Science separate-verifier layout
(`tests/Dockerfile`, top-level `artifacts`, `[verifier].environment_mode = "separate"`).
Master #40: zero individual tests may pass under NOP — read each NOP ctrf.json
test by test, never only the aggregate reward.

## What every test must do (Master #37–#60, #100–#102)

- **Check the value, not the artifact** (#59): an assertion that a file exists
  and parses lets a plausible wrong output pass.
- **Independent ground truth** (#44, #45): the expected side is never computed by
  calling code the agent can edit, and fixtures feeding it are baked into the
  verifier image, not read from the agent's mutable copy.
- **Holdouts that matter** (#46): every hidden case's expected value differs
  from the public case's.
- **Exactness and tolerances literally as documented** (#47, #6): set equality
  for "exactly these keys"; tolerance literals identical to `instruction.md`/docs.
- **Tolerances justified by the science** (#101): every inequality — tolerance,
  threshold, percentile bound, fuzzy match — brackets a stated quantity and absorbs
  named legitimate variation (floating point, alternative valid estimators or
  discretizations, seeded nondeterminism). It is measured on at least one independent
  correct implementation that differs from `solution/` in a structural choice, and the
  separation from a defective approach is recorded in the write-ups' `## Verification`
  (`authoring/<task>/write-ups.md`). A
  bound tightened until only the reference clears it is manufactured difficulty (#95).
- **Ground truth with a stated origin** (#100): the reference values a test grades
  against come from the generating model, a cited external value, or a second
  implementation written to cross-check the oracle — or they are oracle-derived and
  disclosed as such in the write-ups, with a varied oracle stage reproducing them within
  tolerance. Grader-only data is baked into the tests image only.
- **Every graded instance discriminates** (#102): run the trivial nulls that need no
  science (a constant, the mean or median of the allowed range, the centre of the
  domain, the majority class, copy-through, the task's own negative control) against
  each withheld instance separately; an instance a null clears is either replaced
  (prefer asymmetric placements) or named in the write-ups' `## Verification`.
- **No guard-only tests** (#41, #42): a "regression guard" or "inputs pristine"
  check is coupled, in the same test function, to a real behavioral assertion.
  A NOP-passable guard is fixed by coupling, never by deletion.
- **Positive controls for fail-closed tests** (#52): a test that only checks
  that bad input is rejected also runs a known-good input through the same
  entrypoint in the same test function; otherwise an always-fail script passes.
- **Named assertions for shortcuts** (#60): empty submission, format-only fake,
  hardcoded public answer, self-reported metric, missing artifact, and fake
  reward/report (including a detached writer) are each rejected by their own
  named assertion.
- **Honest names and no dead code** (#43, #49–#51): names and docstrings match
  the body; no string-concatenation obfuscation; no unused helpers.
- **No wall-clock gates** (#57): no latency, throughput or percentile assertion.
- **Binary, identical grading** (#58): reward exactly 0 or 1; no branch on
  Oracle vs agent, identity flag or job name.
- **Test count matches evidence** (#53): every ctrf.json in the shipped
  evidence has exactly as many cases as the current `tests/` collects.

## The verifier seal

Master #54–#56 and the master's Appendix (copy its lines verbatim; they live only in
`tests/Dockerfile` and `tests/test.sh` — the same lines in `environment/Dockerfile`
violate #24 and protect nothing). Both halves of #54 are required; either alone is a
BLOCKER:

- **#54(a) root-only `/tests`.** `tests/Dockerfile` installs `util-linux procps`,
  creates uid 12000 (`sandbox`), `chown -R root:root /tests /logs/verifier /work`,
  `chmod -R go-rwx /tests`, `chmod 755 /logs/verifier /work` — `/work` stays
  root-owned; only the per-run subdirectory is the sandbox's. Required even when no
  agent code runs.
- **#54(b) every execution of agent-produced code** — a submitted script or binary,
  `cargo build`/`build.rs`, `make`, `pip`/`npm install` hooks, a plugin, a dev server
  — goes through `setpriv --reuid=12000 --regid=12000 --clear-groups --no-new-privs
  env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/work timeout -k 5 <PER_RUN_LIMIT> <cmd>`
  (plus the #106(a) thread-count variables), from a scratch directory the sandbox uid
  owns, with interpreter/toolchain paths it cannot write. Never import or exec agent
  code inside the pytest process (test-module import, conftest, `exec`, `importlib`):
  that is root with `/tests` readable. Launch it in a subprocess and read its output
  back as data. Write the uid as a literal (or a module-level `AGENT_UID = 12000`) so
  it can be checked without running the verifier. `<PER_RUN_LIMIT>` is stated in
  instruction.md and is at least 10× the reference's measured per-run runtime (#57(a)).
- **#55 artifacts are untrusted data.** Before any grading code touches them,
  `tests/test.sh` deletes every symlink under the artifact paths whose resolved target
  escapes them (the master Appendix `find … -type l -exec … -delete` line; in-tree links
  stay, so a symlinked executable is not zeroed by an unstated rule). Every expected-side
  file (fixtures, job specs, inputs, migrations, schemas, model/STEP files) is baked
  under `/tests` at build time; none is read from an artifact path or `/app`, and a
  value derivable from the input is recomputed from the baked copy, never taken from a
  row the agent wrote. A long-lived process that serves or scans artifacts runs
  through the #54 launcher.
- **#56 the reward is written last.** After all agent code has run, `tests/test.sh`
  kill-to-exhaustion (`pkill -9 -u 12000` until `pgrep -u 12000` is empty), then
  `rm -f /logs/verifier/reward.txt`, and only then writes exactly 0 or 1. The pass/fail
  comes from baked grader logic, never from a status string agent code printed. An
  early `echo 0` placeholder (#39) is fine; the `rm -f` and the final write must follow
  the kill.

The bundled auditor checks these mechanically (`T3-SETPRIV`, `T3-SANDBOX`, `T3-SEAL`,
`ISO-01/02/03` for #54, `T3-SYMLINK` for #55, `T3-REWARD-LAST` for #56). The judgment
half is the Appendix SELF-TEST: inside the built verifier image (`docker run --rm
<verifier-image> bash`) every line marked FAIL must fail, and a submission that (a)
reads `/tests`, (b) plants a symlink to a `/tests` file in an artifact path, and (c)
starts a background process that writes `reward.txt` after grading must score 0 each
time. Record that output against #54–#56 in the master record.

## Manifest contract

Each task contains `tests/test_manifest.json`:

```json
{
  "schema_version": "1.0",
  "selector_env": "TBENCH_TEST_ID",
  "tests": [
    {
      "id": "primary-behavior",
      "description": "Checks the public primary behavior on regenerated input.",
      "requirement": "instruction.md: Primary behavior",
      "cases": ["test_outputs.py::test_primary_behavior"],
      "independent": true
    }
  ]
}
```

IDs use lowercase letters, digits, and hyphens; `all` is reserved. Each entry has
exactly one unique `cases` value: the exact CTRF case name expected when that
selector runs. This one-to-one mapping makes each verifier test the unit of
Oracle/NOP evidence and proves that a selector did not silently run the whole
suite. Parameterized cases receive separate manifest entries using their full
CTRF names. `tests/test.sh` must:

1. run all declared tests when `TBENCH_TEST_ID` is unset;
2. run exactly the selected logical test when it is set;
3. on an unknown ID, print an error, leave the reward at `0`, emit no CTRF
   cases, and still exit `0` (the per-test gate rejects that row because its
   CTRF cases do not match the manifest);
4. initialize `/logs/verifier/reward.txt` to `0` before anything else;
5. write `1` only when the selected command succeeds and every expected case
   actually passes; skips and expected failures do not qualify. When `test.sh`
   writes that `1` only for the full suite (`TBENCH_TEST_ID` unset or `all`,
   Master #58(c)), a subset oracle row stays at reward `0` and is judged by its
   CTRF cases, which must still all be `passed`;
6. emit `/logs/verifier/ctrf.json` containing exactly the selected entry's
   declared cases;
7. suppress verifier source disclosure (`--tb=no`, `-rN`) **and** still name every
   failure's cause (#84): `tests/ctrf_reporter.py` records each failed case's own
   assertion message as the CTRF `message` field (the crash line only, never the
   rewritten comparison or any source), and `tests/test.sh` prints one
   `FAILED <case> - <message>` line per failed case from `ctrf.json`, so every
   failing run's `verifier/test-stdout.txt` says why it failed. Every assertion
   carries a message naming the observed outcome (per-case results, counts,
   violation kinds) and never a hidden expected answer. `scripts/task_check.py`
   FAILs `test_failure_messages` when either half is missing;
8. perform no runtime package installation (#38);
9. contain no `set -e`/errexit, write the reward on every path, and end with
   `exit 0` as its last command (#39) — the reward file, not the exit status,
   carries the result. `scripts/hardening_check.py` FAILs a `test.sh` whose last
   command is not `exit 0` or that enables errexit.

A conforming `tests/test.sh` runs from `/tests` to keep case IDs stable, clears
inherited pytest configuration, deletes stale CTRF output, and uses
`tests/ctrf_reporter.py` (dependency-free; replaces `pytest-json-ctrf`), loaded
as a plugin and writing to the canonical path:
`python -m pytest -p ctrf_reporter --ctrf /logs/verifier/ctrf.json …`. The
bundled auditor fails a pytest run without `--ctrf …/ctrf.json` (`VER-06`) and
recognises a custom reporter only by a `-p` name containing `ctrf`; a dotted
`-p tests.ctrf_reporter` reads as a missing `pytest-json-ctrf`. Do not replace it with a reporter that merges parameterized
cases or embeds tracebacks. Its local command deadline must remain below
`[verifier].timeout_sec`. Individual test subprocesses and service waits still
require their own shorter deadlines.

The selector is logical rather than pytest-specific, so tasks may dispatch to
pytest node IDs, shell checks, compiled harnesses, SQL checks, or another
framework, as long as the CTRF names match the manifest.

## Build-your-own-preconditions rule

A test must fail in its **call** phase, never in setup/teardown. Session-scoped
autouse fixtures that assert (for example "compile the submission") make every
NOP row an infrastructure error, which the gate rejects and Master #74 rejects
outright. Put shared expensive work in a memoized helper that never raises, and
assert on its result inside each test body. Each NOP failure must be "the
shipped code ran and produced the wrong answer", never "the shipped code did
not run".

## Bundled auditor enforcement

The rules on this page are also construction rules of the bundled auditor
`tools/final-tbsci-audit-master/`. `scripts/audit_task.py tree tasks/<task>`
stages the task in delivery layout and runs its screen; it is blocking step c1
of `scripts/gate_step2b.sh` and fails on any BLOCKER, MAJOR or MINOR finding
except those only Step 3c/4 evidence can satisfy. At Step 4,
`audit_task.py package` re-screens the candidate ZIP together with
`trial_evidence.py` (Oracle x3, NOP x2 at 0 of N, the five-run round — its runs in
launch order, `T3-RUN-ORDER`), and the
auditor's judged review of that exact ZIP must lint clean before
`package_task.py --promote`. In particular: assertions compare values computed
from the agent's output against independently derived expectations, never
constants the agent could echo, and held-out or regenerated inputs live in the
verifier image (#46).

## Verifier dependencies

Bake pinned verifier dependencies into `tests/Dockerfile` (hash-pinned
`requirements.lock` for Python; scientific stacks such as numpy, scipy, pandas and
domain libraries pinned `==`, Master #38, #106). `tests/test.sh` never installs
anything and performs no trial-time fetch — no `curl|sh`, no raw `curl`/`wget` of an
external host, no `git clone` (Master #38, upstream `check-trial-network-fetch.sh`).
The verifier phase runs with `[verifier.environment].network_mode = "no-network"`
declared (Master #64), so a test that needs the network fails by construction. No
bare `nproc` in `test.sh`; use a fixed worker count sized to `[environment].cpus`
(Master #106). The agent image (`environment/Dockerfile`) must not copy `tests/` or
`solution/`.

## Dynamic matrix (Step 2b gate)

`scripts/gate_step2b.sh tasks/<task>` is the one mechanical gate. After the
static checks and a local `scripts/dev_verify.sh` pass, it calls
`scripts/per_test_gate.py`, which starts a fresh Harbor trial for every
`(test ID, agent, repeat)` tuple, injects the selector, and compares the
resulting CTRF case list with the manifest:

```text
harbor run -p tasks/<task> -a oracle --verifier-env TBENCH_TEST_ID=<id> -k 1 -n 1 ...   # local Harbor, never stb
```

The gate's per-test part requires:

- every manifest test run once under `oracle`, reward exactly `1.0`, or
  reward `0.0` with every selected case `passed` when task reward `1` is
  written only for the full suite (Master #58(c));
- every manifest test run once under `nop`, reward exactly `0.0`, its case
  `failed` through a genuine assertion — `per_test_gate.py` rejects a NOP row
  whose `verifier/test-stdout.txt` shows a pytest ERROR row, a collection
  error, `INTERNALERROR`, an error count, or "no tests ran" (#74);
- no Harbor or verifier exception;
- a JSON report (report schema `1.1`) containing every pair with raw result/CTRF
  paths and hashes, sealed by `scripts/evidence.py seal` against the task
  digest from `scripts/task_digest.py`.

No aggregate suite pass can replace this matrix. A row also fails when the
reward is correct but its CTRF file is missing or contains extra/missing cases.
Oracle cases must report `passed`; NOP cases must report `failed`.
Skipped/pending cases, collection/setup/teardown errors, non-finite rewards,
reused job artifacts, and multiple trials disguised as one row are rejected.

## Negative-control matrix (same gate)

With `--with-nc` (the evidence Step 3b cites for Master #60), immediately
after sealing the gate stages every `authoring/<task>/
staged_controls/nc*.sh` as a full copy of the task with `solution/solve.sh`
replaced (`scripts/stage_controls.sh`) and runs one local `harbor` job per
copy. `scripts/controls_report.py` then writes the `## Gate results —
<digest>` section of `authoring/<task>/controls.md`: for each control the
reward, the failing CTRF case names, and PASS/FAIL against the case the plan
table predicted. A control that rewards `0` through an unplanned case is a
FAIL, because the planned assertion is untested. NC-01..NC-06b cover the
Master #60 shortcuts; NC-07..NC-14 are optional diagnostics. `python3 scripts/nc_generate.py
tasks/<task>` writes the task-agnostic scripts (NC-01/05/06/06b/09); the
task-specific ones are authored by hand and must exercise a real manifest case
(`task_check.py --strict` warns when `controls.md` names a case not in the
manifest).

The gate's `progress` file ends `VERDICT: PASS` only when every matrix it ran
passes on the same digest.

Step 3c runs three **full-suite** Oracle controls and two full-suite NOP
controls through the recording adapters (`scripts.harbor_recording:RecordingOracle` /
`RecordingNop`) alongside five model attempts — or, when the model trials come from
more than one round, in a `CONTROLS_ONLY=1 scripts/run_step3c_eval.sh` run at the same
digest, local Harbor version and adapter hashes, which `scripts/compose_step3c.py`
checks before it takes them (Master #94 item 1). Those controls are reported
separately from model pass rates and never replace the Step 2b gate; they are
what ships as `oracle-nop-evidence/` (Master #71–#74: every Oracle test
passing, every NOP test explicitly failing on a genuine assertion). Step 4
reruns nothing; the Step 2b per-test jobs and seal stay in the workspace and
never ship.

Task mutation during a gate run invalidates the report. Any behavioral task edit
returns the task to the Step 2b gate: fresh `OUT`, fresh digest, full
`scripts/gate_step2b.sh`. A descriptive-only edit (a descriptive `[metadata]` key) leaves
both graded digests unchanged and re-seals with `gate_step2b.sh --reseal-only`
instead (`docs/TBSCI_HARDENING_RULES.md` §8.3); editing `authoring/<task>/write-ups.md`
touches no task file and needs no re-seal. For a single suspect test, `prompts/step3a.md`
describes `per_test_gate.py --only <id> --repeat 3`; its report is diagnostic
and is never sealed.

## Independence review

For each manifest entry, reviewers answer:

- What public behavior does it check?
- Can two materially different correct approaches pass?
- Does it build all of its own preconditions?
- Can it run before or after any other test with the same result?
- Does it delete or namespace stale outputs before producing new ones?
- Are randomness, clocks, ports, process lifetimes, and performance
  measurements controlled? (Wall time is never reward logic, #57.)
- Is its expected value independent of agent-editable code (#44), and is the
  origin of that value stated (#100)?
- Does every tolerance it applies absorb legitimate variation from an independent
  correct implementation, and nothing finer than the science supports (#101)?
- Does any trivial null clear one of its graded instances (#102)?
- If it only checks rejection, does it also run a positive control (#52)?
- If it is a guard, is it coupled to a behavioral assertion (#41)?
- Is every exact expected value uniquely implied by the public contract?
- Does NOP failure demonstrate missing task behavior rather than missing test
  infrastructure?

If a test is inherently coupled to another requirement, combine the coupled
behavior into one logical manifest test. Do not claim independence by relying on
execution order.
