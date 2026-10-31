# TB-Science hardening rules

`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth; every rule
here names the master checks it serves, and the master wins where they differ.
This document turns the Terminal-Bench 3.0 to 4.0 cleanup (the lessons this
workspace inherited from its Terminal-Bench 4 origins) into preventive
authoring rules for this Terminal-Bench Science repository. It supplements the
program contract in `AGENTS.md`; it does not replace program-specific schema,
taxonomy, model, or packaging rules. Below the master,
`docs/reference/QUALITY_GUIDELINES.md` is authoritative when a local hardening
suggestion would conflict with the program quality bar. For capability
patterns (how to make a task genuinely harder), see
`TBSCI_CAPABILITY_HARDENING_RULES.md` at the repo root.

The bundled auditor `tools/final-tbsci-audit-master/` enforces the same master
from the first file: `scripts/audit_task.py tree` is blocking step c1 of the
Step 2b gate (full and `--reseal-only`), and at Step 4 `audit_task.py package`
screens the candidate ZIP and the auditor's judged review of that exact ZIP
(`review.sh … lint` → `LINT_OK  ✅ Ready to Submit  (0 warning(s))`) is
required before `package_task.py --promote`. Its construction rules are
written into the rules below (§2 rules 8–9, §5).

§1 is inherited history: the Terminal-Bench 3.0 → 4.0 cleanup as it was observed,
left as written because its lessons still apply to scientific tasks. §§2–9 are live
rules for TB-Science tasks; §10 adds the TB-Science-specific rules behind Master
Section J (#98–#107), each citing the upstream `harbor-framework/terminal-bench-science`
file it was adapted from (decisions in the v4 workspace's TBSCI_REVAMP notes (not carried here)).

Policy labels:

- **PROGRAM** — required by the Terminal-Bench Science policy mirrored in this repository.
- **UPSTREAM LESSON** — supported by the Terminal-Bench 4.0 release or task repairs (inherited), or by the
  upstream Terminal-Bench Science contribution rules (`harbor-framework/terminal-bench-science`).
- **LOCAL GATE** — an additional check imposed by this authoring workflow.

Sources:

- <https://www.tbench.ai/news/terminal-bench-4-0> (TB 4.0 release; history)
- <https://www.tbench.ai/news/writing-a-good-terminal-bench-task>
- `tbench_v3_vs_v4_audit.md` (historical)
- upstream TB-Science `CONTRIBUTING.md`, `rubrics/task-implementation.toml`,
  `rubrics/trial-analysis.toml`, `ci_checks/` (paraphrased, never vendored)
- `MASTER_CHECKLIST_TBSCI.md`

## 1. What failed in Terminal-Bench 3 (inherited history)

Terminal-Bench 4.0 did not add tasks. It removed 8, repaired 19, and recalibrated resources.
That means the useful lesson is not “make tasks harder”; it is “reject invalid
difficulty before publication.”

| Hazard | TB3 symptom | Workflow defense |
|---|---|---|
| Saturation | Current model families solved the task 5/5, or clarification removed the only difficulty | The seed review (Step 1, or Step 2a when Step 1 is skipped) states the real crux; Step 3c requires a non-saturated clean batch and rejects ambiguity-based failures |
| Public solution | A public artifact or proof could be copied; a constant or fixture still passed | Search-risk review in the seed review; hard-coded-public-answer and held-out controls in Steps 2b/3a |
| Refusal-prone framing | Trials measured model policy rather than task capability | Refusal-risk screen in the seed review; REF outcomes are invalid difficulty evidence in Step 3c |
| Platform dependence | amd64-only binaries or host-sensitive behavior | Portability plan in Step 2a; static and runtime review in Steps 3a/3b |
| Misspecification | Tests enforced details absent from the public contract | Contract and assertion traceability before model trials |
| Brittle verification | Exact representation, notation, strings, or ordering rejected equivalent answers | Semantic-equivalence probes and normalized comparisons |
| Incomplete verification | A headline metric passed while correctness or another stated requirement was untested | One requirement-to-test row per behavior; single-axis negative control |
| Trusted self-report | Agent-written metrics or summaries were accepted as truth | Independent recomputation from raw artifacts and verifier-only truth |
| State illusion | Displayed or in-memory state passed while durable state was wrong | Reload persisted artifacts/state before verification |
| Environmental flakiness | Mutable downloads, host binds, under-sized resources, or low timeouts polluted failures | Pinning, no host binds, clean rebuilds, resource headroom, and causal trial classification |
| Reward channel exposure | Agent could modify tests, reward files, tool resolution, or grader behavior | Separate verifier, protected reward channel, isolated execution, tamper controls |

## 2. Non-negotiable verifier rules

1. **Public contract alignment** (**PROGRAM**, Master #1, #2, #12). Every meaningful assertion must
   cite an explicit sentence in `instruction.md` or a solver-visible interface
   that the instruction points to. Hidden tests may hide inputs, not requirements.
2. **Bidirectional coverage** (**PROGRAM**, **LOCAL GATE**, Master #1, #2).
   Every environment doc counts as a public requirement source (Master #12). Every public
   requirement has an independent test, and every meaningful test maps back to
   a public requirement. A test that can fail only because another requirement
   fails is not independent coverage.
3. **Semantic outcomes** (**UPSTREAM LESSON**, Master #47, #59). Verify the requested outcome,
   not the oracle’s implementation, exact serialization, source shape, or an
   incidental ordering. Normalize equivalent correct forms before comparison.
4. **Independent truth** (**LOCAL GATE**, Master #30, #44, #45). Recompute expected values or metrics
   from pristine inputs and verifier-only truth. Never trust an agent-reported
   score, status, summary, or checksum by itself.
5. **Correctness before performance** (**UPSTREAM LESSON**, Master #57). A fast wrong answer
   is reward 0. Performance gates execute only after semantic correctness.
6. **Persisted-state verification** (**UPSTREAM LESSON**). Tear down or reload
   state before checking it. Logs, UI values, or in-memory objects do not prove
   persistence.
7. **Binary reward on every path** (**PROGRAM**, Master #39, #58). `tests/test.sh`
   writes exactly `0` or `1`, including missing-artifact, crash, and
   early-failure paths; no `set -e`; its last command is `exit 0`.
8. **Separate verifier ownership** (**PROGRAM**, Master #20, #24, #37, #54). Tests, truth, dependencies,
   and reward logic belong to the verifier image, which ends with the master's
   Appendix step 1 (uid 12000, `chmod -R go-rwx /tests`). The agent image contains no solution, hidden test, or
   answer-bearing build residue. Held-out or regenerated inputs live in the
   verifier (#46), and assertions compare values computed from the agent's
   output, never constants. pytest writes `--ctrf /logs/verifier/ctrf.json`
   through `tests/ctrf_reporter.py` loaded as `-p ctrf_reporter`.
9. **The verifier seal** (**PROGRAM**, Master #54–#56). Copy the master's Appendix A
   into `tests/Dockerfile` and `tests/test.sh`. Every execution of agent
   code goes through `setpriv --reuid=12000 --regid=12000 --clear-groups
   --no-new-privs env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/work timeout -k 5
   <PER_RUN_LIMIT>` from root-owned `/work` (sandbox owns only the per-run subdirectory), never as an in-process import; `test.sh`
   deletes every artifact symlink whose resolved target escapes the artifact paths
   before grading (in-tree links are kept), reads every expected
   value from `/tests`, and after grading kill-to-exhaustion then `rm -f
   /logs/verifier/reward.txt` before writing the reward. The auditor reports a
   missing drop (`T3-SETPRIV`, `ISO-01`), an unsanitized or unbounded launcher
   (`T3-SANDBOX`), a writable `/logs/verifier` (`ISO-02`), a readable `/tests`
   (`T3-SEAL`), undeleted artifact symlinks (`T3-SYMLINK`) or a reward not written
   last (`T3-REWARD-LAST`) as MAJOR. Run the Appendix SELF-TEST in the built verifier
   image and record its output against #54–#56.
10. **Precondition integrity** (**LOCAL GATE**, Master #41, #45). Assert that pristine inputs are
    non-empty and unchanged before scoring, so disabling a feature, deleting
    inputs, or zeroing a dataset cannot create a trivial success. Such a guard
    is coupled to a behavioral assertion in the same test (Master #41, #42), and
    every fail-closed test runs a known-good positive control (Master #52).
11. **Identical actor treatment** (**PROGRAM**, Master #58). Oracle and agent receive the
    same verifier logic, inputs, permissions, thresholds, and environment. The
    verifier never branches on `/oracle` or actor identity.
12. **Portable test entrypoint** (**PROGRAM**). Every non-standard environment
    variable read by `tests/test.sh` has a compatible default.
13. **Network-isolated verifier** (**PROGRAM**, Master #64; upstream
    `check-allow-internet.sh`, `check-trial-network-fetch.sh`). `task.toml` declares
    `[verifier.environment].network_mode = "no-network"` (an `"allowlist"` with
    `allowed_hosts` only for a host the verifier genuinely needs, justified in
    `authoring/<task>/resource-plan.md`). `tests/test.sh` fetches and installs nothing at
    trial time; every tool is baked in `tests/Dockerfile`.
14. **Bounds justified by the science** (**PROGRAM**, Master #101). Every tolerance or
    threshold states what it brackets and which legitimate variation it absorbs, and is
    measured on an independent correct implementation that differs from `solution/` in
    a structural choice. Classify every named method as correct or defective;
    separation must be achieved on the shipped graded instances (10% margin). No
    fresh-draw study is required. Where instances come from a generator and a
    method's smallest shipped-set margin is under 20%, the default internal check
    is 3 fresh unselected draws (6 only if those 3 are borderline or inconsistent). A correct
    method that fails a draw, or a defective method that passes one, is a margin
    finding. Not running the probe is never a finding. Precision finer than the science supports is a
    finding, and so is a bound placed just past the reference's own margin.
15. **Ground truth with a stated origin** (**PROGRAM**, Master #100). The graded
    reference values are independent of `solution/` (the generating model, a cited
    external value, or a second implementation written to cross-check the oracle), or
    are disclosed in the write-ups' `## Verification` (`authoring/<task>/write-ups.md`)
    as oracle-derived and shown to survive a
    varied oracle stage within tolerance.

## 3. Shortcut controls (Master #60)

NOP proves only that the untouched environment fails. It does not prove that
the verifier checks meaningful content. Master #60 requires each shortcut in
the first table to be rejected through its **own named assertion**; reward 0
through a different, unplanned test is a fail of that check. The controls are
recorded in `authoring/<task>/controls.md`, implemented as temporary `solve.sh`
substitutes, and run against a staged copy of the task
(`scripts/gate_step2b.sh --with-nc`).

| ID | Shortcut | Required result |
|---|---|---|
| NC-01 | Empty/no-op | Reward 0 through named missing/content tests; no verifier crash |
| NC-02 | Format-only fake with every declared file present | Reward 0 through semantic-value tests |
| NC-03 | Hard-coded public/example answer | Reward 0 on held-out or generated variants |
| NC-04 | Self-reported target metric without underlying work | Reward 0 after independent recomputation |
| NC-05 | Missing one declared artifact | Reward 0 through a named artifact test |
| NC-06 | Write fake reward/CTRF from the agent side | Ignored; verifier produces reward 0 |
| NC-06b | Detached process rewriting reward/CTRF after the agent's turn | Ignored; verifier produces reward 0 |

Optional diagnostics (run when the condition applies; an `n/a` states why):

| ID | Apply when | Shortcut to reject |
|---|---|---|
| NC-07 | Obvious baseline exists | Correct but naive/textbook approach misses the crux or deterministic score/work gate |
| NC-08 | More than one correctness axis | Primary metric passes while a second stated requirement is violated |
| NC-09 | Durable state is required | Correct value is printed but not persisted/committed |
| NC-10 | Inputs vary | Visible-size, first-N, sorted-input, or one-boundary-only implementation |
| NC-11 | Inputs/protected files exist | Tamper with or replace a protected input/baseline |
| NC-12 | Verifier executes agent code | PATH shim, shadow module, `sitecustomize.py`, or wrapper returning success |
| NC-13 | Performance is scored | Smallest-scale-only or warm-cache-only implementation |
| NC-14 | Public examples exist | Fit public cases exactly and fail a legal unseen/metamorphic case |

An `n/a` must state why the task’s public contract makes the shortcut impossible.

## 4. Reward-hacking threat classes

Every Step 2a spec must address these classes in its threat model:

- reward/test/CTRF modification;
- format-only or plausible-default output;
- hard-coded public or visible fixtures;
- trusted self-reported metrics;
- single-axis partial solutions;
- unpersisted state;
- first-N, ordering, boundary, or scale shortcuts;
- missing-artifact laundering;
- protected-input tampering;
- PATH/module/wrapper/`LD_PRELOAD` manipulation;
- background processes reaching the reward channel;
- verifier-time network fetch poisoning (closed by the declared no-network verifier,
  Master #64);
- answers reachable by web lookup or memorization — the agent phase always has open
  internet (Master #64, #99);
- timing, cache, or precomputation manipulation;
- answers leaked through layers, history, comments, or data;
- `/solution` or hidden-test access;
- alternate state such as empty inputs or disabled features.

## 5. Portability and resource rules

- No `FROM --platform=...` pins or silent amd64-only artifacts.
- No `-march=native`, architecture-specific intrinsics, or prebuilt downloads
  without a portable fallback or explicit program-approved justification.
- No Docker socket, privileged mode, host kernel modules, or undeclared devices.
- Compose uses named volumes, not host bind mounts (Master #106).
- External files, repositories, package versions, images, and sidecars are
  pinned as required by the program; no `latest`. Data fetched at build time is
  pinned to an immutable revision written as a literal (never a build argument)
  and checksum-verified during the build; grader-only data lands only in the tests
  image (Master #100).
- No bare `nproc` in any Dockerfile, `test.sh` or `solve.sh`: inside a container
  it reports the host count. Use a fixed worker count sized to `[environment].cpus`
  (Master #106; upstream `check-nproc.sh`).
- `apt-get update` before every apt install and `rm -rf /var/lib/apt/lists/*`
  after it; every pip / uv install pinned `==`, scientific stacks (numpy, scipy,
  pandas, domain libraries) included (Master #106).
- Network declared on both phases: agent `[environment].network_mode = "public"`,
  verifier `[verifier.environment].network_mode = "no-network"` (Master #64).
- `[environment]` declares `cpus`, `memory_mb`, `storage_mb` and `gpus = 0`, no
  `gpu_types`, sized from measurement: hard for the agent, not the computer
  (Master #65).
- Build twice from a clean state when mutable external material is involved.
- Resource limits come from measurements with headroom. A model timeout that
  was still making progress is not difficulty evidence.
- **No wall-clock latency or throughput assertion is allowed** (Master #57).
  Timing may be measured only to diagnose infrastructure.
- Timeouts are `28800` for agent, verifier and build on every task (Master #63);
  they are never tuned down.
- Deterministic work/quality thresholds are fixed before model trials from the
  public objective and realistic baselines. Never place a threshold just beyond
  the best model attempt or within roughly 5% of the reference's own result
  (without a recorded sign-off) so that only Oracle-like implementations pass.
- Digest-pinned bases; language packages pinned exactly, apt packages
  unpinned; environment/ ≤100 MiB, no file >50 MiB (Master #26).
- Final agent base `public.ecr.aws/docker/library/<python|node|golang|rust|eclipse-temurin|gcc|ruby|maven|debian|ubuntu>@sha256:…`,
  or a Dockerfile comment justifying why no canonical image works (Master #26;
  auditor `T3-BASE`).
- When efficiency is part of the public contract, prefer deterministic work
  counters, bounded memory/representation, scale behavior, or semantic-quality
  constraints. Verify correctness first and admit fundamentally different
  correct implementations.

## 6. Public-solution and refusal review

Before construction:

1. Record three searches a capable agent would make: task name/concept, a key
   error or identifier, and the likely upstream algorithm/library.
2. Record the closest public solution and why copying it cannot satisfy the
   hidden, variable, or stateful contract.
3. Reject a task whose deliverable is a public constant or small artifact that
   NC-03 cannot distinguish from genuine work, and a task whose answer is a
   well-known published result or sits on a dataset whose solution is widely
   available — the agent runs with open internet, so that is a design defect, not a
   reason to cut the network (Master #99).
4. Apply the clarification-collapse test: rewrite every ambiguous requirement
   clearly. If the clarified task becomes trivial, redesign the crux.
5. Classify refusal risk. Security tasks should use synthetic artifacts and
   defensive analysis, detection, forensics, or hardening framing.
6. In Step 3c, refusal outcomes are classified separately and do not count as
   model capability failures.

## 7. Stop-hardening list

The following changes are rejected because they lower pass rate without
measuring more capability:

- fussy whitespace, key order, verbose schemas, or exact strings when semantics suffice;
- extra reports, renames, headers, or unrelated subtasks;
- hidden encodings, defaults, ordering, or assumptions;
- larger data that adds waiting rather than a new scaling requirement;
- numeric tolerances below measured oracle/reference variance, or finer than the
  science supports (Master #101);
- deterministic score/work thresholds chosen after seeing agent outcomes;
- smaller timeouts or under-provisioned resources;
- any latency, throughput, p50/p95/p99, or hardware-sensitive wall-clock gate;
- near-Oracle thresholds that turn the task into implementation replication;
- disabling internet access in the agent phase (it is always `public`, Master #64;
  a web-lookupable answer is redesigned, Master #99);
- adding many independent requirements that do not interact.

Real hardening strengthens the capability crux: hidden computational structure,
interacting pruning/reuse/representation/laziness/memory decisions, realistic
partial solutions, held-out legal variation, semantic verification, and robust
resource measurement.

## 8. Freeze and invalidation

The task has two graded surfaces, and they invalidate different things.
`scripts/task_digest.py --part {full,agent,grader}` prints each one. A third,
descriptive surface — the descriptive `[metadata]` keys — is covered by the full
digest only (§8.3). The workspace write-ups `authoring/<task>/write-ups.md` are not
task files and sit outside every digest (Master #103).

### 8.1 Agent-surface freeze

The **agent surface** is `instruction.md`, `task.toml`, `environment/**` and
`solution/**` — everything that determines what the agent saw and could do. Any
change to it invalidates Oracle, NOP, negative-control, review, **and model
evidence**. Re-enter at Step 2b for a behavioral change; a demonstrably
non-behavioral packaging fix still re-runs the Step 2b gate on the new digest.
Never pool trials from different digests (same-digest, same-config rounds are pooled
only through `scripts/compose_step3c.py`, §8.4).

### 8.2 Grader-surface rebinding

The **grader surface** is `tests/**`. Because every task sets
`[verifier].environment_mode = "separate"`, the reward is a pure function of
`tests/` and the captured artifacts. So `tests/` may be improved after
trajectories exist and the existing trials **re-graded** — no model re-runs — as
long as the agent digest is unchanged.

Master #94 records this as policy: a regraded round is current-digest evidence when
only `tests/` changed, `regrade_step3c.py verify` passes, the agent digest is
byte-identical to the captured trials', and every reward came back identical (or a
flip meets the waiver below). The difficulty report names the regrade record and the
agent digest so an auditor can check the binding.

**Allowed:** splitting monolithic tests into per-case tests; keeping assertion
messages in the CTRF; exporting diagnostics; adding a test for a requirement
`instruction.md` **already** states; accepting a materially different valid
implementation the contract already licenses (for example a permitted file format
the loader happened to reject); marking non-gating cases informational.

**Not allowed:** any new requirement `instruction.md` does not state — that needs
an instruction change and fresh runs; moving a threshold so specific attempts
flip; loosening a test without quoting the instruction sentence that licenses it.

**Before delivery:** Oracle N/N and NOP 0 on the new suite; every previously
captured trial re-graded; pre-capture seals preserved, never rewritten. The full
gate this route runs includes the auditor's tree screen (step c1), so a
`tests/`-only fix for an auditor finding — a missing verifier-seal line (#54–#56), a
`setpriv` drop, the `--ctrf` path — follows this route and must clear it.

**When a re-graded reward moves.** The default expectation is that every reward
comes back identical — a flip is the tripwire for loosening, and
`regrade_step3c.py run` reports it as FAIL. But the "accepting a materially
different valid implementation" clause above flips a trial by construction: a
submission the old loader rejected for an unpublished reason now scores what it
always deserved. Such a flip is admissible only if **every one** of these holds,
recorded per trial in the Step 3b review as an explicit waiver:

- the flip traces to one named verifier defect, with the old code line that rejected
  the submission and the verbatim `instruction.md` sentence the submission satisfied;
- no threshold, tolerance or operator moved anywhere in the same edit (revert those
  first and re-grade; a flip that survives the reversion is defect-driven, one that
  does not was threshold-driven and is fatal);
- nothing the agent could see contradicts the claim — a signature, filename or
  format published in the shipped scaffold counts as published;
- the difficulty report states the corrected rate causally, trial by trial, and
  retracts any earlier claim the flip refutes.

A flip that cannot meet all four is a loosening. Either revert it, or treat the
evidence as void and capture a fresh round at the new digest.

Consequences worth knowing before you start:

- **`task.toml` is on the agent surface, but only its functional fields count.**
  `scripts/common.py` folds the descriptive `[metadata]` keys
  (`expert_time_estimate_hours`, `relevant_experience`, `domain`/`field`/`subfield`,
  author fields, tags, …) out of the agent digest, because `task.toml` is never copied into the agent container:
  Harbor reads it to configure the trial and the agent reads `instruction.md`. So a
  descriptive field may be corrected after capture without invalidating trials.
  Anything Harbor acts on — `[agent].timeout_sec`, `artifacts`, `[environment]`,
  `[verifier]` — still moves the agent digest. The FULL digest hashes `task.toml`
  byte-for-byte either way, so any edit still re-enters the Step 2b gate — but a
  descriptive-only edit re-enters it as a **re-seal**, not a re-measurement: see §8.3.
- **`tests/seed/**` is not grader-only.** Where it mirrors `environment/` it is the
  pristine ground truth the agent was held to; `task_check.py` enforces byte parity
  (`seed_parity`). Editing it is an agent-surface change in disguise.
- **Declared `artifacts` are frozen by the record.** Adding an entry silently
  invalidates every captured trial for regrade, because the captured
  `artifacts/manifest.json` has no bytes for it.
- **The per-test matrix must re-run** on the new manifest — that is the only proof a
  newly split case is not vacuous, and it is the dominant cost of a grader change.
- **A trial whose captured artifacts contain symlinks cannot be regraded.** Harbor
  0.23.0 replays a single-step trial's artifacts with `copytree(symlinks=False)`: a
  link into the agent's `/app` aborts the copy on the host, and any other link turns
  into a regular file, so the verifier would not see what was submitted (Master #55
  keeps in-tree links). `regrade_step3c.py` refuses such a model trial at `bind` and
  at `run`; take a fresh Step 3c round at the current digest instead.
- **Run the null control first.** Re-grade with `tests/` unchanged and require
  identical rewards; if they move, the verifier is not a pure function of `tests/`
  plus artifacts and this whole section is void for that task.

Mechanics: `scripts/regrade_step3c.py bind` before the edit, `run` after. Full rule
set in `docs/reference/PACKAGE_RULES.md`. Name the `run --out` directory after the task alone
(e.g. `evidence-<task>-b`): Harbor bakes that path into every shipped `config.json` and
`result.json`, the auditor rejects process-history words there (`regrade`, `rerun`,
`void`, `aborted`, `harden…`, `round-N`, … — T3-ROUND-NAME), and a finished regrade
cannot be renamed. `run` refuses such a name before starting. Package the regrade
output only after `archive_step3c.py` has copied it into `tasks/<task>/trajectories/`,
and re-score every run from its regraded `test-stdout.txt` (`prompts/step4.md` §2).

### 8.3 Descriptive-only re-seal

Some descriptive edits are legitimately needed after capture — the standard cases
are updating `expert_time_estimate_hours` when a fresh round materially changes it
(Master #94 item 4) and correcting a stale `relevant_experience` (Master #61). Such
an edit moves the **full** task digest while moving neither graded surface: the full
digest covers exactly the agent surface, the grader surface and the descriptive
`[metadata]` keys that `functional_task_toml()` folds out of the agent digest
(`DESCRIPTIVE_SURFACE` in `scripts/common.py` is empty — the task carries no
`README.md`, Master #103), so "full moved, neither half moved" leaves only an edit no
trial could have observed. Editing the write-ups in `authoring/<task>/write-ups.md`
— for example to record a trivial-null result or a tolerance study measured after
capture — touches no task file, moves no digest and needs no re-seal. Re-running the
per-test Oracle/NOP matrix would measure a byte-identical grader against a
byte-identical Oracle and NOP.

(There is no `difficulty` field to set: the measured k=5 rate lives only in
workspace reports, Master #62. Earlier revisions used this mechanism to write a
tier into `task.toml`; that step is retired.)

So the rule is by *kind of edit*, not by "the digest moved":

- **Behavioral edit** — anything that moves the agent or the grader digest, including
  `[agent].timeout_sec`, `artifacts`, `[environment]`, `[verifier]`, and anything under
  `instruction.md`, `environment/`, `solution/` or `tests/` — re-enters the full
  `scripts/gate_step2b.sh` with a fresh OUT and a fresh digest. Nothing here is relaxed.
- **Descriptive-only edit** — the keys in `DESCRIPTIVE_METADATA_KEYS`
  (`expert_time_estimate_hours`, `relevant_experience`, `domain`/`field`/`subfield`,
  author fields, tags, …) — re-seals and re-binds:

      scripts/gate_step2b.sh tasks/<task> --reseal-only        # static screen + re-seal
      scripts/stage_reports.py rebind-review tasks/<task>      # review header only

  `--reseal-only` runs `task_check --strict`, `hardening_check` and the bundled
  auditor's tree screen (`audit_task.py tree`, step c1) — the static screen can
  genuinely fail here, e.g. on a `write-ups.md` section left empty or renamed, or a
  retired key such as `category` or `difficulty_explanation` reintroduced —
  then `evidence.py reseal` and `evidence.py check`, and ends with the usual
  `VERDICT: PASS|FAIL` in `<OUT>/progress`. It starts no container.

The precondition is checked, never assumed. `evidence.py reseal` recomputes both split
digests and **refuses** unless each equals what the seal recorded, naming the half that
moved and sending you to the full gate. It also refuses when the sealed per-test report
has moved, is missing, or no longer covers the manifest, and when the seal predates the
split digest.

The evidence records what happened rather than hiding it. The re-stamped seal keeps its
original `created_at`, its `per_test_report` and that report's hash, and gains a `reseal`
record carrying `previous_task_digest`, the superseded-digest lineage, both graded digests,
`resealed_at` and `reason = "descriptive [metadata] only; agent and grader surfaces
byte-identical"` (the literal `evidence.py` writes and checks). The per-test report itself is **never rewritten**.

The Step 3b review is re-bound, not re-issued: `stage_reports.py rebind-review` rewrites
only its `Task digest:` line under the same guard, appends a provenance paragraph, and
keeps `artifacts/reviews/<task>.md` and `authoring/<task>/step3b-review.md` byte-identical.
The master record (`authoring/<task>/master-checklist.md`) is re-checked on the new digest
— Master #61 is re-verified for the edited field. (The record is bound to the task digest
only; an edit to `MASTER_CHECKLIST_TBSCI.md` itself does not void it unless it changes the
set of check numbers, which `master_checklist.py check` reports line by line.) Re-binding changes the review's bytes,
so the difficulty report must be re-headed afterwards with the new `Task digest:` and
`Review SHA256:`. Because `SUMMARY.txt`'s `sha=` is the bundle sha of the shipped inner
task folder (Master #80), a descriptive edit also changes it; Step 4 recomputes it.
If a candidate ZIP was already built, it is stale: rebuild it, and the auditor
reviews the new candidate before `--promote` (the old review no longer matches
its bytes).

What this does **not** license: pooling trials across digests; a re-seal after a grader
change, which is §8.2 and `regrade_step3c.py`; any edit to the per-test report; or any
behavioral edit.

### 8.4 Rounds cut short: first five valid trials across rounds

MASTER_CHECKLIST_TBSCI.md #94 item 1: the five packaged runs are **the first five
fidelity-complete trials at the current digest and run config, in launch order across
rounds, with no valid attempt skipped**; the order is checkable from each run's own
`result.json` timestamps and trial IDs. A round that stops early (stb refresh quota,
infrastructure abort, a trial with `exception_info`) is therefore not void: its
fidelity-complete trials count, and another round at the same digest supplies the rest.
`scripts/compose_step3c.py` is the only way to assemble such a round, and it enforces the
boundaries rather than trusting them:

- **Same digest** — every source and the controls round carry the same
  `task-digest.txt` (and agent/grader digests). Never across revisions.
- **Same run config** — model, `reasoning_effort=xhigh`, adapter, launcher, capture
  settings (`max_output_bytes=0`, `store_all_messages`, raw API log), stb/Harbor
  versions, arch, full-fidelity patch revision (`patch-guard.log`), the run-affecting
  `recording-source.sha256` entries, and every trial's `config.json` agent block,
  `recording_config.json`, `task_checksum` and job `lock.json` Harbor version.
- **Fidelity-complete** — every per-trial `check_trajectory.py` criterion, verifier CTRF,
  `exception_info` null, and the files `archive_step3c.py` requires.
- **Selection by launch order** — sort by `result.json` `started_at`, take the first five
  valid. Never best-of; a valid trial launched before the fifth selected one is never
  left out. Exclusions are outcome-independent only (infra or credential/quota abort,
  `exception_info`, operator stop after the first five were complete); an operator stop
  or an unfinished trial inside the first five needs an explicit recorded `--reason`.
- **No hidden rounds** — another same-digest, same-config round directory (a `_void-*`
  one included) with a trial launched before the fifth selected trial is a refusal until
  it is passed as `--source`.
- **Controls** — Oracle x3 / NOP x2 at the same digest, local Harbor version, arch and
  adapter hashes, from any source round or a `CONTROLS_ONLY=1 scripts/run_step3c_eval.sh`
  round.

Nothing new ships: `composition.json` (every candidate, start time, validity,
selected/excluded and why) stays in the workspace with the round; `SUMMARY.txt` stays two
lines. `verify_package.py` and the auditor's `T3-RUN-ORDER` check the shipped runs'
`result.json` for distinct trial ids, strictly increasing `started_at`, one
`task_checksum` and one agent configuration.

## 9. Tactical review gotchas (**LOCAL GATE** unless noted)

Narrow, specific techniques that catch real defects a general rule in §§1–8 can
miss. Additive, not a replacement — cross-reference the relevant general rule
where one exists.

### 9.1 Verifier / reference gotchas

- **Byte-diff `environment/` against `tests/` and `solution/`, file by file** (Master #20).
  A file that's byte-identical between the agent's own image and the
  verifier's private copy is a leaked oracle, not a coincidence — if it can
  compute even a subset of the graded quantity, the agent has a perfect local
  answer-check for that subset. Severity depends on how much of the graded
  surface leaks; don't assume "harmless" without checking exactly what's in
  the shared file. (Extends rule 8, separate verifier ownership.)
- **The reference must not branch on a case/scenario identifier and return a
  constant that happens to match** (Master #31). This reads like real computation on a
  skim. Diff every output field against hand-derived expected values,
  especially any field that looks suspiciously constant per case — this is a
  reward-hack *inside the golden solution*, not just an agent-side shortcut,
  and it means that axis was never actually validated by real computation.
- **If independent agent attempts converge on an answer that disagrees with
  the reference, don't default to "they all made the same mistake"** (Master #32, #33).
  Hand-derive the correct value from the shipped spec and check whether the
  agents, not the reference, are right — a reference built partly on
  privileged or held-out information contaminates any threshold built from
  its output, not just tightens it.
- **Extract and run a hand-rolled fixture parser standalone** in the task's
  own base image before trusting it. Oracle passing is not evidence the
  parser is correct — an off-by-one that silently falls back to a hardcoded
  default lets Oracle and NOP both pass while every non-default-sized fixture
  runs at the wrong size.
- **Guard a `ulimit`/`RLIMIT_AS`/cgroup-cap test with a `platform.machine()`
  check** when the image is pinned to a foreign platform. Emulation overhead
  alone can trip the limit before the code under test runs, independent of
  rule 5's architecture-portability requirement.
- **Pair every rejection test with a positive control** (Master #52) — a known-good input
  that succeeds through the same entrypoint, in the same test. "Exit nonzero,
  no output written" passes trivially against the untouched NOP tree and
  proves nothing about real validation on its own.
- **Precedence/tie-break assertions must construct the adverse state they
  claim to defend against**, not just assert the outcome. A test asserting
  "X must win over Y" without ever creating a hostile Y is satisfied by
  construction on any implementation — check this specifically against NOP
  per-test evidence, where such a test is a giveaway pass.
- **Readiness/sync waits must be wall-clock-bounded, never iteration-count-
  bounded**, and never busy-spin without sleeping. A correct-but-slower
  solution fails an iteration-bounded wait that a fast Oracle clears —
  a portability/determinism defect, not a difficulty signal.
- **Build and run the obvious naive baseline through the real verifier** when
  one exists (NC-07); don't assume from a static read that it fails. A naive
  approach that fails every gate but one and slips past a single aggregate
  threshold is a real, different finding from one that fails cleanly
  everywhere, and only running it distinguishes the two.

### 9.2 Evidence-integrity gotchas

- **Cross-run duplication check** (Master #83). For any numeric result that accumulates
  floating-point error over many iterative steps, compare full-precision
  values across all five model runs (not just Oracle/NOP). Agreement to only
  a handful of significant figures is unremarkable; agreement to 15–16
  significant figures on a value sensitive to implementation details is close
  to impossible for genuinely independent attempts — escalate as an
  evidence-integrity concern, don't wave it off as convergence.
- **Partial-fix-pass ablations must be built and run, not inferred from
  reading code** (Master #35: every file `solve.sh` touches, not a sample). Confirm every suspected partial-fix-pass (fixing only one
  of several planted defects still passes) by actually building the
  environment with exactly one defect left in its original state and running
  the real suite (extends the single-axis threat class in §4). This also
  hands you the fix: whichever assertion never goes red across any ablation
  is the coverage gap.

### 9.3 Infrastructure hazards

- **Shared-UID process-count contention (false capability failures).**
  Docker containers without user-namespace remapping share the kernel's
  per-UID process count host-wide. A verifier that runs the candidate as a
  fixed shared UID (e.g. `nobody`/65534) under an `RLIMIT_NPROC` cap fails
  intermittently whenever *other* containers on the same host also have
  several processes under that same UID at once — other trials' candidates,
  a profiler, an agent's own measurement script. Symptom: a `setpriv:
  ... Resource temporarily unavailable` (exit 126) failure within seconds,
  indistinguishable from a genuine capability failure without checking host
  contention. Confirmed by direct reproduction: unrelated same-UID processes
  in another container flipped a real test from pass to fail. Fix: draw the
  execution UID at random per session/run (not a fixed shared one, and not
  just the container's own PID namespace) and `chown` working directories to
  it. Relevant across all ten trials a task runs (5 model + 3 Oracle + 2 NOP)
  — any pair can collide if they land on the same host concurrently.

## 10. TB-Science rules (Master Section J, #98–#107)

Live rules added by the TB-Science revamp. Each is **PROGRAM** unless marked; the
judgment ones are answered in the master record at Step 3b (#98–#103, #106) or Step 4
(#107), #104 is mechanical, and #105 is a merged placeholder answered by #37, #38 and #64.

1. **Taxonomy and scope** (Master #61, #98; upstream `CONTRIBUTING.md` "Task
   Diversity", rubric `scope`). `domain` and `field` are exact kebab-case values from
   `docs/TASK_TAXONOMY.md`; `subfield` names the research specialty. Classify by the
   scientific expertise indispensable to solve the task: strip the tool names and ask
   whether a researcher in that field would call it their work. A computational method
   applied to an out-of-scope subject is out of scope.
2. **Research-level, not lookup-able** (Master #99; rubric `scientifically_grounded`,
   `novel`). The task comes from a real research workflow named in
   `authoring/<task>/write-ups.md`, needs
   domain judgment about what to compute and why, and its answer is not one web search
   or one memorized published result away. Agents keep open internet; a lookup-able
   answer is redesigned.
3. **Provenance recorded** (Master #100; rubric `ground_truth_provenance`,
   `deterministic_reproducible`). Real data: source, version/DOI or URL, a licence that
   permits redistribution, preprocessing. Synthetic data: the generator and its
   parameters. Both live in `authoring/<task>/provenance/` (workspace, never shipped);
   independent reference implementations and tolerance studies in
   `authoring/<task>/calibration/`.
4. **Tolerances measured, not tuned** (Master #101; rubric `essential_difficulty`,
   trial-analysis `boundary_fairness`). See §2 rule 14. Record the measured margin
   between the independent correct implementation and the nearest defective approach in
   the write-ups' `## Verification`.
5. **Trivial nulls per instance** (Master #102; rubric
   `graded_instances_discriminate`). Run the no-science nulls (constant, range mean or
   median, domain centre, majority class, copy-through, the task's own negative control)
   against each graded instance. Prefer asymmetric placements; name any instance a null
   clears in the write-ups' `## Verification`.
6. **No README.md** (Master #103; upstream `task-readme-template.md` not adopted). The
   task carries no `README.md` and no write-up file ships. The write-ups are the
   workspace record `authoring/<task>/write-ups.md`: three non-empty sections, exactly
   `## Difficulty`, `## Reference solution`, `## Verification`, current with
   `solution/` and `tests/`. Editing it later touches no task file — no re-seal
   (§8.3), never a re-measure.
7. **Instruction suffix** (Master #104; upstream `check-instruction-suffix.sh`).
   `instruction.md` ends with `You have 28800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.`
   Changing it is an agent-surface (behavioral) edit.
8. **Verifier network and tooling** (Master #38, #64). See §2 rule 13.
9. **Reproducible, portable environment** (Master #106). See §5; a stochastic task
   fixes its seeds, and results are identical across runs.
10. **Trial analysis** (Master #107; upstream `rubrics/trial-analysis.toml`). Every
    Step 3c trial is classified from its full trajectory against
    `specification_completeness`, `solution_discoverability`, `verifier_correctness`,
    `boundary_fairness` (any failure here indicts the task: fix it at a fresh digest),
    `unearned_credit` (with #93), `meaningful_difficulty`, and `policy_refusal` /
    `execution_blocked` (not difficulty evidence; with #92 and AGENTS.md rule 21).
11. **Optional hints** (**LOCAL GATE**; upstream `task-hint-template.md`, adapted).
    `authoring/<task>/hint.md` holds gentlest-first numbered `## Hint N` sections for an
    optional Step 3a hinted diagnostic run only. It is never used in Step 3c, never
    ships and carries no canary; a hint that hands over the answer makes the hinted run
    measure nothing.
