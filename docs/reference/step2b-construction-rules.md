# Step 2b construction rules (reference; driven now by the sub-steps, see docs/PROCEDURES.md)

`MASTER_CHECKLIST_TBSCI.md` is the source of truth. Build the task so it passes
Master #0–#69, #95 and Section J's #98–#106 the first time it is reviewed;
Step 3b walks those checks one by one and any FAIL sends the task back here.

Pull `docs/PROCEDURES.md`, `docs/PROCEDURES.md`, `docs/reference/QUALITY_GUIDELINES.md`,
`docs/TBSCI_HARDENING_RULES.md`, `docs/TESTING_POLICY.md`, and
`docs/reference/TBSCI_CAPABILITY_HARDENING_RULES.md`, plus `docs/TASK_COMPONENTS.md` (the
`task.toml` and instruction-suffix templates) and
`docs/TASK_TAXONOMY.md`. Construct only from the locked Step 2a contract.
Task path: `tasks/<task-name>`; author-side material (data generators,
provenance records, the independent cross-check implementation, the optional
`hint.md`) lives in `authoring/<task-name>/`, never in the task tree.

Step 2b ends with one mechanical gate, `scripts/gate_step2b.sh`. The per-test
Oracle/NOP matrix and the seal run inside it; Step 3b starts on the sealed
evidence.

## 1. Construction requirements

- **instruction.md (#0–#11, #104):** an AI assistant may draft it (human-only authorship is not required; no review is blocked on an AI-text detector), absolute paths, every
  output file named, "what" not "how", no pipeline vocabulary, no canary, no
  defect mechanism narrated; an independent domain expert could solve it from
  the text alone (#0). It ends with exactly this paragraph, preceded by a blank
  line and followed by one newline (#104):
  `You have 28800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.`
  Every other sentence maps to a test in `traceability.md`.
- **Write-ups (#103, #62):** the task carries **no README.md** (the static
  check and the auditor fail one). `authoring/<task-name>/write-ups.md` —
  workspace only, never shipped, never given to the agent — has three non-empty
  sections exactly `## Difficulty`, `## Reference solution`, `## Verification`
  (template `authoring/_templates/write-ups.md`). Written for a non-domain reader; names
  the paper, dataset or pipeline the work comes from (#99); `## Verification`
  says where the reference values come from (#100), how every tolerance was
  calibrated (#101) and which graded instance a trivial null clears, if any
  (#102). No pass rate, model score, tier or canary.
- **environment/ (#12–#26):** only files that are needed; no hint comments, no
  lore/notes files indexing defects, no opaque or mislabelling names, no dead
  files, no unused answer-key module; every doc under `environment/` has tests
  (#12) and agrees with `instruction.md` (#12); vendored archives re-tarred with
  `--owner=0 --group=0` (#23); the agent Dockerfile never copies or touches
  `/tests`, `/solution`, `/oracle`, `/logs/verifier`, `/logs/artifacts` (#24);
  digest-pinned `FROM`, final agent base
  `public.ecr.aws/docker/library/<python|node|golang|rust|eclipse-temurin|gcc|ruby|maven|debian|ubuntu>@sha256:…`
  or a comment justifying the exception, tmux + asciinema, language packages
  pinned exactly (numpy, scipy, pandas and domain libraries included), apt
  packages unpinned behind `apt-get update` with `/var/lib/apt/lists` cleaned,
  no `FROM --platform`, size limits (#26, #106); no bare `nproc` anywhere and no
  compose host bind mounts; the agent Dockerfile never names `solve.sh`,
  `test.sh` or `test_*.py` (#106); seeds fixed so results are identical across
  runs.
- **Data and ground truth (#99–#102):** real or realistic data with its origin
  recorded under `authoring/<task-name>/provenance/` (source, version/DOI or
  URL, licence, preprocessing — or the generator and its parameters); any
  build-time fetch pinned to an immutable revision written as a literal and
  checksum-verified; grader-only data only in the tests image. The answer is not
  reachable by web lookup or by memorising a published result (the agent has
  open internet).
- **solution/ (#27–#36):** each touched file maps to a stated defect or
  capability (#28, #29); no scenario-id branching or privileged knowledge (#31,
  #32); no orphaned files (#34).
- **tests/ (#37–#60):** separate verifier with top-level `artifacts` and their
  parent dirs created in `tests/Dockerfile` (#37); verifier deps baked at exact
  pins (#38); `tests/test.sh` has no `set -e`, writes the reward on every path
  and ends with `exit 0` (#39); value checks, not existence checks (#59);
  ground truth never computed by agent-editable code (#44, #45); holdouts that
  change the outcome (#46); exactness and tolerances literally as documented
  (#47, #6), each one justified by the science and measured on an
  independent implementation (#101); no string-concatenation obfuscation, no dead test code, accurate
  test names and docstrings (#43, #49); the verifier seal is the master's
  Appendix A — `tests/Dockerfile` makes `/tests` root-only and `/work` root-owned
  for uid 12000, agent code the verifier executes runs via `setpriv --reuid=12000
  --regid=12000 --clear-groups --no-new-privs env -i … timeout -k 5 <PER_RUN_LIMIT>` (#54),
  `test.sh` deletes artifact symlinks before grading (#55) and kill-to-exhaustion
  then `rm -f /logs/verifier/reward.txt` before the reward write
  (#56), and the Appendix A SELF-TEST passes in the built verifier image; pytest writes `--ctrf /logs/verifier/ctrf.json` with
  `tests/ctrf_reporter.py` loaded as a plugin (`-p ctrf_reporter`); tests
  assert computed values, never constants; **no
  wall-clock latency/throughput assertion at all** (#57); binary reward and
  identical Oracle/agent logic (#58); defaults for every non-standard variable
  `tests/test.sh` reads.
- **Guards and fail-closed tests:** every guard-style test is coupled to a real
  behavioral assertion in the same test function (#41, #42); every
  rejection-only test also runs a known-good positive control in the same
  function (#52); each #60 shortcut is rejected by its own named assertion.
- **task.toml (#61–#65, #98):** exactly as planned in Step 2a, from the
  `docs/TASK_COMPONENTS.md` template — top-level `name` and `artifacts`;
  `[metadata]` `domain`/`field` (exact kebab-case values from
  `docs/TASK_TAXONOMY.md`, classified by the scientific expertise indispensable
  to solve the task), non-empty `subfield`, 3–6 `tags`,
  `expert_time_estimate_hours`, `relevant_experience`; author fields optional
  (non-empty when present); no `difficulty`, no top-level `version`, no
  `category`/`subcategory`/`languages`, no `*_explanation` keys (they are
  `authoring/<task-name>/write-ups.md` sections); `schema_version` optional; all three timeouts `28800`;
  `environment_mode = "separate"`; `[environment].network_mode = "public"` and
  `[verifier.environment].network_mode = "no-network"`, both declared;
  `cpus`/`memory_mb`/`storage_mb` sized to the task and `gpus = 0`, no
  `gpu_types`.
- **rubric.txt (#66–#70):** write `tasks/<task-name>/rubric.txt` now, before the
  gate — the auditor screen stages it beside the inner task folder and fails
  the gate without it.

The bundled auditor (`tools/final-tbsci-audit-master/`) screens many of the
rules above mechanically — among them the canonical base, the verifier seal
(root-only `/tests`, the uid-12000 `setpriv` launcher, artifact symlink deletion,
reward written last), the `--ctrf` path, `task.toml` residue, taxonomy,
timeouts and network policy, the absence of a README.md, the instruction suffix,
the #106 portability rules, and the presence of `rubric.txt`. Run its screen on the tree while
you build, not only at the gate; it must print `PASS`:

```bash
python3 scripts/audit_task.py tree tasks/<task-name>
```

It stages the task in delivery layout (`<slug>/<slug>/` + `<slug>/rubric.txt`)
and fails on any BLOCKER, MAJOR or MINOR finding except the few only Step 3c/4
evidence can satisfy (no `oracle-nop-evidence/`, `trajectories/` or
`SUMMARY.txt` yet). The `LEAD` lines it prints are questions Step 3b will
answer; read them now and fix anything they expose.

Update `authoring/<task-name>/traceability.md` with the exact verifier tests.
Do not tune fixtures, tolerances, or deterministic score/work thresholds
against frontier model attempts. Models run only in Step 3c, on a frozen digest.

## 2. Verifier contract

Ship `tests/test_manifest.json`, `tests/ctrf_reporter.py`, and a
`TBENCH_TEST_ID`-aware `tests/test.sh` per `docs/TESTING_POLICY.md`. Each
manifest entry maps to exactly one CTRF case. Every verifier test builds its
own preconditions and fails in its call phase, never in a fixture: a
session-scoped autouse fixture that asserts turns every NOP row into a setup
error, which the gate rejects and Master #74 rejects outright. `tests/test.sh`
initialises the reward to `0`, installs nothing, and prints no verifier source.

## 3. Local loop before any Harbor job

```bash
source .venv/bin/activate
scripts/dev_verify.sh tasks/<task-name>
```

`dev_verify.sh` builds the images, runs `solution/solve.sh`, then runs
`tests/test.sh` in the verifier image; it exits `0` only when `reward.txt` is
`1`. Use `--keep-image` to skip the rebuild while iterating and
`--extra '<shell snippet>'` to run an ad-hoc probe in the verifier container.

## 4. Proofs you owe before the gate

These are Master checks the gate cannot run for you. Record each result in
`authoring/<task-name>/traceability.md` (or `resource-plan.md` for #30) with the
command and its output; Step 3b cites them.

- **#35 ablation, one file at a time.** For every file `solve.sh` touches:
  apply every other fix, leave this one file in its shipped state, run the
  suite (`dev_verify.sh` with the ablated solve), and record which named tests
  fail. A fix whose ablation fails nothing is a no-op delta (#28) or a
  coverage gap. Do every file, not a sample.
- **#30 independent correctness** for any named algorithm/metric/transform:
  diff the reference output on the shipped fixtures against the trusted
  external implementation or hand derivation named in Step 2a.
- **#20 byte-diff:** `diff`/`sha256sum` every file under `environment/` against
  its counterpart under `tests/` and `solution/`; explain every identical file.
- **#13 literal grep:** `grep -rnE 'TODO|FIXME|BUG:|planted|deliberate|for the grader|for the test' environment/ solution/`
  — zero hits, or each hit justified.
- **#36 cold build:** `docker builder prune` (or `--no-cache`) and build both
  images from scratch once; the Oracle must pass on the cold image.
- **#46 holdouts:** show the expected value on each held-out case differs from
  the public one.
- **#57:** if a deterministic score/work threshold exists, run the reference and
  the named naive baseline through the real scoring code and record the margin.
- **#100 ground truth:** record where every graded value comes from — the
  generating model, a cited external value, or a second implementation written
  to cross-check the oracle — or, when oracle-derived, show a varied oracle
  stage reproducing it within tolerance. Provenance files go under
  `authoring/<task-name>/provenance/`.
- **#101 tolerances:** run at least one independent correct implementation that
  differs from `solution/` in a structural choice (estimator, discretisation,
  library) and every named defective approach through the real tests on the
  shipped instances; classify each method; record each bound, what legitimate
  variation it absorbs and the 10% margins. No fresh-draw study is required.
  Where instances come from a generator and a method's smallest shipped-set
  margin is under 20%, the default internal check is 3 fresh unselected draws
  (6 only if those 3 are borderline or inconsistent); not running it is never a finding.
  Keep the cross-check code in `authoring/<task-name>/calibration/`.
- **#102 trivial nulls:** run the nulls that need no science (a constant, the
  mean or median of the allowed range, the domain centre, the majority class,
  copy-through, the public answer replayed) against each graded instance
  separately; an instance a null reaches is a finding to fix, not to disclose.

## 5. Master checklist record

Create and pre-fill the per-task record the reviewer will complete:

```bash
python3 scripts/master_checklist.py init tasks/<task-name>   # writes authoring/<task-name>/master-checklist.md
python3 scripts/master_checklist.py auto tasks/<task-name>   # mechanical findings + review leads per check
```

`auto` includes the auditor's tree findings and leads, grouped by master
number. Fix every mechanical finding `auto` reports before running the gate. Do not
mark checks PASS yourself; the independent reviewer does that in Step 3b.

## 6. Negative controls

Master #60 requires the empty submission, a format-only fake, a hardcoded
public/example answer, a self-reported metric, a missing declared artifact and
a fake reward/report (foreground and detached) each to be rejected through its
**own named assertion** — reward 0 through a different test is a fail of that
check. Prove it with controls:

```bash
python3 scripts/nc_generate.py tasks/<task-name>
ls authoring/<task-name>/staged_controls/
cat authoring/<task-name>/staged_controls/README.md
```

`nc_generate.py` writes NC-01 (empty), NC-05 (missing artifact), NC-06 and
NC-06b (fake reward/CTRF, foreground and detached), and NC-09 (unpersisted
state); author NC-02 (format-only), NC-03 (hardcoded answer) and NC-04
(self-reported metric) by hand. NC-07..NC-14 are optional diagnostics. Fill
the plan table in `authoring/<task-name>/controls.md` with the **named** CTRF
case each control must fail; `task_check.py --strict` warns when a named case
is not in the manifest.

## 7. The gate

```bash
source .venv/bin/activate
docker context use default
scripts/gate_step2b.sh tasks/<task-name> --with-nc
tail -f authoring/<task-name>/evidence/step2b-*/progress
```

The gate detaches by default and writes `progress` under
`OUT=authoring/<task-name>/evidence/step2b-<stamp>/` (override with
`--out <dir>`; use a fresh directory for every round). In order it runs:
`doctor.py --strict-tools` → `task_check.py --strict` → `hardening_check.py`
→ (c1) `audit_task.py tree` (the bundled auditor's screen, blocking; log
`$OUT/auditor-tree.log`) → (c2) `master_checklist.py auto` (informational,
`$OUT/master-checklist-auto.log`) → `task_digest.py` → `dev_verify.sh` → per-test Oracle/NOP matrix
(`per_test_gate.py`, one local `harbor` job per row) → `evidence.py seal` →
with `--with-nc`, `stage_controls.sh` + one local `harbor` job per staged
control → `controls_report.py --write`. The last line of `progress` is
`VERDICT: PASS` or `VERDICT: FAIL`.

Outputs on PASS:

- `artifacts/gates/<task-name>/step2b.json` — the seal (checked with
  `python3 scripts/evidence.py check tasks/<task-name> --evidence artifacts/gates/<task-name>/step2b.json`);
- `authoring/<task-name>/controls.md` — a `## Gate results — <digest>` section
  written by `controls_report.py`: reward, failing CTRF cases, and PASS/FAIL
  against the plan for each control;
- `$OUT/` — raw Harbor job directories, console logs, and exit codes. Keep
  them; the seal verifies their hashes.

`--nc-only` reruns just the control matrix against the existing seal;
`--foreground` runs attached. `--reseal-only` is only for a later
descriptive edit — a descriptive `[metadata]` key (for example
`expert_time_estimate_hours`; a `write-ups.md` edit touches no task file and
needs no re-seal); it
still runs the static screen and step c1 (`audit_task.py tree`), and it is
never a substitute for this gate.

## 8. Acceptance

Step 2b is complete only when all of the following are true on one digest:

- every manifest test has an Oracle row with reward `1.0` / status `passed`
  and a NOP row with reward `0.0` / status `failed`; no setup errors; every NOP
  failure is a genuine assertion mismatch against do-nothing behavior, not an
  import/crash/infrastructure error (#40, #73, #74) — read the per-test NOP
  stdout, not only the reward;
- `evidence.py check` reports `Evidence readiness: PASS`;
- each #60 control rewards `0` through the CTRF case named in the plan, with no
  verifier crash — "reward 0" through a different case is a FAIL;
- the Section 4 proofs are recorded, and `master_checklist.py auto` reports no
  open mechanical finding;
- `audit_task.py tree` prints `PASS` (step c1, `$OUT/auditor-tree.log`);
- no Harbor exception in any job; `progress` ends with `VERDICT: PASS`.

Any edit to `instruction.md`, a functional `task.toml` key, `environment/**`,
`solution/**`, or `tests/**` after the seal returns you here: fresh `OUT`,
fresh digest, full gate. Never keep a favourable partial result from an older
digest. An edit to a descriptive `[metadata]` key only
(`domain`/`field`/`subfield`, `tags`, `expert_time_estimate_hours`,
`relevant_experience`, author fields) leaves both graded surfaces
byte-identical: re-seal it with `gate_step2b.sh tasks/<task-name> --reseal-only`
instead of re-measuring. Editing `authoring/<task-name>/write-ups.md` touches no
task file and needs no re-seal.

Exit only with the phrase `GATE PASSED — READY FOR PAPER REVIEW`, and only with
the `progress` file and the `controls_report.py` output pasted in the chat.
Exit with the digest, not a difficulty claim.
