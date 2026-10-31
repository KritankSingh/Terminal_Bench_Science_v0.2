# Terminal-Bench Science quality guidelines

`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth; where this
page and the master disagree, the master wins (authority order: master >
`docs/reference/DELIVERY_CHECKLIST.md` > `docs/reference/PACKAGE_RULES.md` > everything else).
These program rules are mandatory for every task and take precedence over
local hardening advice. Each section names the master checks it covers; the
science sections paraphrase upstream `CONTRIBUTING.md` ("Task Guidelines") and
the science criteria of upstream `rubrics/task-proposal.md` and
`rubrics/task-implementation.toml`. (The Terminal-Bench 4 portal text under
`docs/archive/tb4-portal/` is archived TB4 reference, not current guidance.)
Nothing ships with an open finding of any severity.

## 1. High-level requirements

| Requirement | Gate |
|---|---|
| Instruction styling | Concise `instruction.md` (an AI assistant may draft it; human-only authorship is not required, and no review is blocked on an AI-text detector), normally one or two paragraphs or no more than 20 bullets unless the task genuinely needs more, ending with the 28800-second suffix (Master #0–#11, #104) |
| Expert-solvable | An independent domain expert could solve it from the instruction alone: field-standard conventions omitted, a choice between defensible conventions stated, everything the field does not determine stated (Master #0) |
| Scientifically grounded | A research-level workflow a scientist would be paid to do, needing real domain knowledge — not a textbook exercise, course project or generic coding in scientific vocabulary (Master #98, #99) |
| Data and ground truth | Real or realistic data with recorded provenance; reference values independent of `solution/` or disclosed as oracle-derived and defended (Master #100) |
| Multi-step | At least five terminal commands in a realistic solution path, intermediate state, and reasoning such as branching, investigation, or recovery; no single command or straight-line burst |
| Testable | Fully specified, self-contained, deterministic final-state verification with no hidden contract (Master #1, #2) |
| Novel | No variation/reskin of an upstream benchmark task, a prior benchmark-edition task or your own earlier tasks; not a well-known problem with cookbook solutions; answer not reachable by obvious web lookup (Master #99) |
| Genuine difficulty | Hardness from scientific reasoning and domain judgment, never manufactured: no obscure-fact or trick questions, no tedium, no tolerance tighter than the science (Master #95, #101) |
| Robust across time and hardware | Pinned stacks, build-time data pinned and checksum-verified, no live services, portable across architectures (Master #100, #106) |
| No privileged operations | No root-only task requirement, `--privileged`, Docker socket, unsafe capability, or host dependency |
| Standalone | No human input after start; every parameter comes from files, flags, or environment variables |

Tasks are prepared for private delivery and validated on local Docker through
`harbor` (Oracle/NOP, controls) and the patched stb harbor (Step 3c); nothing is
submitted to a hosted validation path.

## 2. No latency-based tests (Master #57)

Verifier tests must not assert wall-clock latency, throughput, p50/p95/p99,
hardware speed, or “faster than” behavior — an absolute ban, not a calibration
question. Such checks vary across machines and can make Oracle reproducibility
depend on the host.

Allowed:

- semantic correctness and final-state properties;
- deterministic operation/work counters when they are part of the public contract;
- output-quality or resource-bounded correctness measures that are independent
  of wall-clock speed;
- wall-time measurements used only as author diagnostics for timeout headroom,
  never as pass/fail assertions.

If a task’s only crux is latency improvement, redesign it around deterministic
algorithmic work, bounded representation/memory, or semantic quality.

## 3. Identical Oracle and agent testing (Master #58)

The verifier must apply exactly the same tests, permissions, inputs,
environment, tolerances, and thresholds to Oracle and model agents. Conditional
logic based on `/oracle`, agent identity, agent type, job name, or an
`EVAL_IS_ORACLE`-style flag is prohibited.

The Oracle may create a correct artifact differently, but the verifier cannot
know or care which actor produced the artifact.

## 4. Multi-container metadata (Master #65)

For a genuinely multi-container task:

```toml
[metadata]
is_multi_container = true
```

Omit the field for single-container tasks. Harbor discovers
`environment/docker-compose.yaml` directly; do not add an invented task.toml
path or compose field.

## 5. No runtime web data fetches (Master #26, #38, #64, #100)

Task environments, solution scripts, and verifier entrypoints must not download
task data or depend on mutable webpages/APIs at runtime. Store required small
data under `environment/`, respecting the 100 MiB total and 50 MiB per-file
limits.

Package installation and pinned dependency download are allowed during Docker
image build. They are not allowed from `tests/test.sh` or `solution/**` at trial
time. Larger datasets and model weights are fetched **at build time** only,
pinned to an immutable revision written as a literal (a full commit SHA, never a
branch, tag or build argument) and checksum-verified during the build
(`sha256sum -c`), so the build reproduces the exact bytes the task was
calibrated on or fails loudly (upstream `CONTRIBUTING.md` "Hosting large task
data", `rubrics/task-implementation.toml` `deterministic_reproducible`). Any
host is acceptable for private delivery, but record the source in
`authoring/<task>/provenance/` and `authoring/<task>/write-ups.md`. Agent-visible inputs go into
`environment/Dockerfile`; grader-only data (expected values, truth labels)
goes into `tests/Dockerfile` only. `docs/reference/DOCKERFILE_BEST_PRACTICES.md` has the
pattern.

The agent phase always runs with `network_mode = "public"` (Master #64), which
does not permit the task itself to depend on live mutable data; the verifier
phase is declared `"no-network"` and `tests/test.sh` performs no fetch or
install (Master #38).

## 6. Preserve Harbor reserved paths (Master #24)

The agent `environment/Dockerfile` must not create, copy to, modify, chown, or
chmod `/tests`, `/solution`, `/oracle`, `/logs/verifier`, or `/logs/artifacts`,
and must not `COPY` `solution/` or `tests/` at any layer (including through a
parent directory). Harbor owns these paths.

This prohibition applies to the agent environment. The separate verifier’s
`tests/Dockerfile` is expected to bake its own test bundle at `/tests`; that is
not an agent-image collision.

## 7. Always write a binary reward (Master #39, #58)

Every verifier outcome, including pytest failure, missing artifact, or handled
error, must write `0` or `1` to `/logs/verifier/reward.txt`. No `set -e`; do not
exit before the reward write; the last command of `tests/test.sh` is `exit 0`,
because the reward file, not the exit status, carries the result. Never a
fraction, ratio or weighted composite. Missing reward is an infrastructure
error, not a model fail.

The Oracle and model agent execute the same reward path.

## 8. Default test environment variables

Every non-standard environment variable read by `tests/test.sh` must have a
task-compatible default. Standard variables such as `HOME` and `PWD` are exempt.

Preferred patterns:

```bash
TEST_DIR="${TEST_DIR:-/tests}"
python -m pytest -p ctrf_reporter --ctrf /logs/verifier/ctrf.json \
  "$TEST_DIR/test_outputs.py" -rN --tb=no

# Or use the default inline:
python -m pytest -p ctrf_reporter --ctrf /logs/verifier/ctrf.json \
  "${TEST_DIR:-/tests}/test_outputs.py" -rN --tb=no
```

A hard-coded canonical path such as `/tests/test_outputs.py` is also valid.
Whichever form is used, `test.sh` then prints each failed case's CTRF `message`
(`docs/TESTING_POLICY.md` rule 7): `--tb=no` hides source, not the cause of a failure.
Failing merely because an optional framework variable is unset is prohibited.

## 9. No Oracle-replication threshold (Master #57)

A quality, score, work, or other deterministic threshold is allowed only when
efficiency is genuinely part of the public contract, and it must measure
meaningful task completion, not near-reproduction of the Oracle. A threshold
within roughly 5% of the reference's own achieved performance is a BLOCKER
unless an explicit sign-off is recorded. Run the reference and a named naive
baseline through the real scoring logic and measure the margin yourself; a code
comment claiming calibration is not evidence. Correctness is always checked
before any such gate.

Before freeze, demonstrate that a fundamentally different correct approach can
reasonably pass. Thresholds are fixed from the public objective, realistic
baselines, and domain requirements—not from the best model attempt and not from
the Oracle’s exact implementation.

The same discipline applies to numerical tolerances on scientific outputs: a
tolerance is justified by the science and measured on an independent correct
implementation, never placed just past the reference's own error (Master #101,
§11).

## 10. Built to clear the bundled auditor (Master #12, #26, #46, #47, #54–#56)

The bundled auditor `tools/final-tbsci-audit-master/` grades the task against the
same master, and it is enforced twice: `scripts/audit_task.py tree` is a
blocking step (c1) of the Step 2b gate, and at Step 4 `audit_task.py package`
screens the candidate ZIP and the auditor's judged review of that exact ZIP
must lint `✅ Ready to Submit` with zero warnings before `package_task.py
--promote`. A task is built to its construction rules from the first file:

- final agent base `public.ecr.aws/docker/library/<python|node|golang|rust|eclipse-temurin|gcc|ruby|maven|debian|ubuntu>@sha256:…`,
  or a Dockerfile comment justifying the exception (#26);
- `tests/Dockerfile` ends with the master's Appendix A step 1 (uid 12000 `sandbox`,
  `chmod -R go-rwx /tests`, root-owned `/logs/verifier` and `/work` at 755) (#54);
- agent code the verifier executes runs through the Appendix A launcher
  `setpriv --reuid=12000 --regid=12000 --clear-groups --no-new-privs env -i …
  timeout -k 5 <PER_RUN_LIMIT>`, never imported into pytest; `/work` is root-owned;
  root derives the reward from baked grader logic, never from a status string the
  child printed (#54, #56);
- before grading, `test.sh` deletes every artifact symlink whose resolved target escapes
  the artifact paths, keeping in-tree links (#55), and,
  after grading, kill-to-exhaustion then `rm -f
  /logs/verifier/reward.txt` before writing the reward (#56);
- pytest writes `--ctrf /logs/verifier/ctrf.json`, with `tests/ctrf_reporter.py`
  loaded as a plugin (`-p ctrf_reporter`);
- tests assert values computed from the agent's output, never constants; held-out
  or regenerated inputs live in the verifier (#46);
- every output key, column and format the tests check is named in words in
  `instruction.md` (#47);
- `tasks/<task>/rubric.txt` exists before the gate (the screen stages it).

## 11. Scientific grounding, provenance and tolerances (Master #98–#102)

- **Taxonomy and scope (#98).** `domain` / `field` exact from
  `docs/TASK_TAXONOMY.md`, `subfield` the research specialty, classified by the
  scientific expertise indispensable to solve the task. An in-scope method
  applied to an out-of-scope subject is out of scope.
- **Grounding and novelty (#99).** A real research workflow — something a
  scientist would be paid to do on a computer — needing judgment about what to
  compute and why. Not reachable by obvious web lookup or memorization of a
  published result. The write-ups (`authoring/<task>/write-ups.md`) name the
  paper, dataset, pipeline or project the work comes from.
- **Provenance (#100).** Every dataset's origin is recorded: real (source,
  version/DOI or URL, licence, preprocessing) or realistic synthetic (generator
  and parameters) in `authoring/<task>/provenance/`. Graded reference values
  come from an independent source — the generating model, a cited external
  value, a second implementation written to cross-check the oracle — or are
  disclosed as oracle-derived and defended by a varied oracle stage that
  reproduces them within tolerance. The write-ups' `## Verification` says which.
- **Tolerances (#101).** Each bound states what it brackets and what
  legitimate variation it absorbs, and is measured on at least one independent
  correct implementation that differs from `solution/` structurally. Classify
  every named method as correct or defective; separation must be achieved on
  the shipped graded instances (10% margin rule). No fresh-draw study is
  required. Where instances come from a generator and a method's smallest
  shipped-set margin is under 20%, the default internal check is 3 fresh
  unselected draws (6 only if those 3 are borderline or inconsistent). A correct method that
  fails a draw, or a defective method that passes one, is a margin finding.
  Not running the probe is never a finding. Never tighten a bound to the reference's own margin, and never finer than
  the science supports.
- **Discriminating instances (#102).** Trivial nulls (constant, centre of the
  range, majority class, identity, the task's own negative control, the public
  answer replayed) are run against each graded instance separately; an instance
  a null reaches is a finding to fix, not something to disclose and ship.
- **Reviewable (#103).** The workspace write-ups `authoring/<task>/write-ups.md`
  (never shipped; the task carries no README.md) explain the science well enough for a
  technically literate non-specialist to check that instruction, tests,
  solution and environment are consistent (upstream
  `rubrics/task-implementation.toml` `reviewable`).

Evidence for #100–#102 — the independent implementation, the null runs, the
sensitivity study — lives in `authoring/<task>/calibration/`; the narrative goes
in `authoring/<task>/write-ups.md`.

## 12. Reproducible, portable environment (Master #26, #106)

No bare `nproc` (use a fixed value sized to `[environment].cpus`), no host
bind mounts in compose, no `FROM --platform=`, `apt-get update` before install
and `rm -rf /var/lib/apt/lists/*` after, every pip/uv install pinned `==`
(numpy, scipy, pandas and domain libraries included), and the agent Dockerfile
never names `solve.sh`, `test.sh` or `test_*.py`. A stochastic task fixes its
seeds; results are identical across runs. Details:
`docs/reference/DOCKERFILE_BEST_PRACTICES.md`.

## 13. Enforcement map

| Rule | Master | Earliest gate | Mechanical check |
|---|---|---|---|
| Concise instruction (AI drafting allowed) | #0–#11 | Step 2a (Step 1 if used) | reviewer + instruction lint |
| Instruction suffix | #104 | Step 2b | `task_check.py --strict` |
| Five-command multi-step path | #95 | Step 2a (Step 1 if used) | seed/spec review |
| Deterministic/self-contained | #1, #2 | Step 2a/2b | contract + verifier review |
| Taxonomy and scope | #61, #98 | Step 2a/2b | `task_check.py --strict` (`TOML-05`) + reviewer |
| Scientific grounding, novelty, no web-lookup answer | #99 | Step 2a | seed review (manual) + Step 3b |
| Data and ground-truth provenance | #100 | Step 2a/3b | `authoring/<task>/provenance/` + write-ups review |
| Tolerances justified, nulls per instance | #101, #102 | Step 2a/3b | resource plan + `authoring/<task>/calibration/` + reviewer |
| No privileged operation | #26 | Step 2b | static checker |
| No latency assertions | #57 | Step 2b/3b | static checker + reviewer |
| Identical Oracle/agent tests | #58 | Step 2b/3b | static checker + controls |
| Multi-container metadata | #65 | Step 2b | task.toml/compose check |
| No runtime web fetch | #38 | Step 2b | static checker |
| Reserved paths untouched | #24 | Step 2b | static checker |
| Reward always written; no `set -e`; ends `exit 0` | #39 | Step 2b | static checker + NOP/control runs |
| Test env defaults | — | Step 2b | static checker |
| No near-Oracle threshold | #57 | Step 2a/3b | resource plan + reviewer |
| task.toml fields (domain/field/subfield, no `difficulty`, no `*_explanation`, `version` banned, `schema_version` optional), timeouts 28800, declared network and resources | #61–#65 | Step 2a/2b | `task_check.py --strict` |
| No README.md; `authoring/<task>/write-ups.md` sections | #103 | Step 2b/3b | `task_check.py --strict` + reviewer |
| Verifier network and baked tooling | #38, #64 | Step 2b | `hardening_check.py` |
| Reproducible environment (`nproc`, binds, pins, platform) | #106 | Step 2b | `hardening_check.py` |
| Trial analysis (eight criteria) | #107 | Step 3c/4 | `audit_step3c.py` + Step 3c report |
| Every check walked with evidence | all | Step 3b/4 | `master_checklist.py check --stage review` / `--stage package` |
| Auditor construction rules (§10) | #12, #26, #46, #54–#56 | Step 2b | `audit_task.py tree` (gate step c1) |
| Auditor leads answered; gates T, A–K walked | all | Step 3b | reviewer, in the master record |
| Auditor judged review of the exact ZIP | all | Step 4 | `audit_task.py package`, `review.sh lint`, `package_task.py --promote` |
