# QC Audit Rubric (Terminal-Bench Science)

`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth; this rubric
is a per-file view of the same checks (master numbers in the Detail column)
and never overrides it. The binding record is
`authoring/<task>/master-checklist.md`, validated by
`scripts/master_checklist.py check --stage review` (Step 3b) or `--stage package` (Step 4).

A per-file scoring pass for reviewing a task bundle before it ships. This is
not the same thing as a task's own `rubric.txt` (which grades an **agent's
solution attempt** against that one task's specific criteria) — this rubric is
the standing, task-agnostic quality bar every bundle is measured against, file
by file. Use it during Step 3b (independent paper review) or any later audit
pass, alongside `docs/reference/TBSCI_REVIEW_BLOCKERS.md` (flat BLOCKER/MAJOR/MINOR walk) and
`docs/TBSCI_HARDENING_RULES.md` (the underlying rules and their rationale). This
doc adds structure and a score, not new rules — every criterion below cites
where its full rationale lives.

The bundled auditor `tools/final-tbsci-audit-master/` scores the same ground by
gate (T and A–K in its `CHECKLIST.md`) and is enforced at the Step 2b gate
(`scripts/audit_task.py tree`, step c1) and at Step 4 (`audit_task.py package`
on the candidate ZIP, then `audit_task.py verdict` on the auditor's judged
review before `package_task.py --promote`). A criterion scored 5 here that the
auditor flags is not a 5: every auditor `LEAD` is answered in the master record
and every auditor finding is a finding here.

## Scale

Score each criterion **1–5**:

- **1–2 — Major issue** (master BLOCKER or MAJOR). Blocks delivery, must be fixed.
- **3–4 — Minor issue** (master MINOR). Also blocks delivery: there is no
  "ship with a note" tier. "Minor" describes the size of the fix, not
  permission to leave it.
- **5 — No issue.** Clean on this criterion.

A bundle ships only when every criterion scores 5.

Score against the files on disk right now, with evidence (file:line, a quoted
string, or command output) attached to every finding — never from memory or a
prior pass's claim. Re-verify a clean automated check or a passing reference
run yourself before crediting it; a tool result is material for a review, not
the review itself.

Find and record every real issue in one pass. Fixing issue #1 only to
discover issue #2 next round is worse than naming both up front.

## instruction.md

| Criterion | Major-issue trigger | Detail |
|---|---|---|
| Spec completeness | A test/oracle depends on a field, flag, or rule never stated in `instruction.md` or a doc it names as authoritative; or a stated requirement has no test | Master #1, #2; `docs/TESTING_POLICY.md` |
| No pipeline vocabulary | Mentions the grader, test suite, verifier, pytest, `/tests`, `/opt/verifier`, `test_outputs`, or a reward file | Master #5 |
| What, not how | A sentence prescribes an internal step where an outcome would do, and is not a graded interface contract | Master #3, #4 |
| No manufactured difficulty | Invented tolerance, artificial timing race, or difficulty from piling unrelated requirements rather than interacting ones | Master #95; `docs/reference/DIFFICULTY_GUIDELINES.md` "Does not work" |
| No diagnosis / decoy leakage | States the bug's mechanism, explains why a naive path fails, or names a planted decoy directly | Master #10, #25 |
| Expert solvability | An independent domain expert could not solve it from the text alone: a choice between two defensible conventions (index origin, transform sign/normalisation, estimator, units, tie-break) left unstated; a field-independent choice (path, schema, differently drawn held-out input, different runtime, limits on submitted code) left unstated; a gating metric left unnamed; or padding that spells out field-standard conventions | Master #0; upstream `CONTRIBUTING.md` "instruction.md"; `docs/reference/INSTRUCTION_PROMPT_STYLING.md` |
| Instruction suffix | Does not end with exactly `You have 28800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.` (blank line before, one newline after, N = `[agent].timeout_sec`) | Master #104; mechanical (`INSTR-01`) |
| Network claim consistency | Instruction implies the agent works offline while `[environment].network_mode` is (always) `"public"` | Master #64 |
| No internal-tool trace / PII | Contains `stb`, or a real local machine path | `docs/reference/PACKAGE_RULES.md` |
| No canary strings | A canary/GUID-shaped string anywhere, or present in a delivered trajectory but absent from the shipped environment (staleness signal on top of the leak) | Master #11, #88 |
| No hints / stepwise solution / detection guidance | Step-by-step walkthrough, a "Detection Guidance" section, exact function signatures, or a mandated tool list | Master #3, #10; `docs/reference/INSTRUCTION_PROMPT_STYLING.md` |
| Absolute paths only | Any relative path, or a named path that does not exist in the built image | Master #0, #7 |
| Task name not in body | The task's own slug/name appears verbatim | `docs/reference/INSTRUCTION_PROMPT_STYLING.md` |
| Instruction voice | GPT-polished cadence, "You are an expert…" framing, decorative markdown/emoji (AI drafting itself is allowed) | `docs/reference/INSTRUCTION_PROMPT_STYLING.md`; master preamble |
| Env docs define WHAT, never HOW | A spec/schema file under `environment/` carries how-to guidance, or instruction content was moved there to shorten `instruction.md` | `docs/reference/INSTRUCTION_PROMPT_STYLING.md` |
| Multi-step / agentic depth | Credible expert path needs fewer than five terminal commands, or hits five only by clerical splitting | `docs/WORKFLOW.md` Step 2a; upstream rubric `agentic` |
| Formula/digest precision | A documented hash/concatenation formula was never diffed byte-for-byte against the test's real compute function | new — `docs/reference/DIFFICULTY_GUIDELINES.md` "Works" |
| Degenerate-input coverage | An edge case (empty field, zero-width interval, a unit declaring none of its own contents) has no documented meaning | new — `docs/reference/DIFFICULTY_GUIDELINES.md` "Works" |
| Enumerated value completeness | Instruction's value list for a field is narrower than what the tests actually feed | new |
| Tie-break / mandatory-flag completeness | A tie-break states only THAT disambiguation happens, not the order/winner/format; or a flag called "optional" is passed on every invocation | new |
| Cross-file numeric consistency | A limit/threshold number disagrees across `instruction.md`, `tests/`, and `rubric.txt` | Master #6 |
| Schema exactness | Prose says "exactly these keys" but the test checks presence only | Master #47 |
| Internal consistency | Two sentences imply different readings of one rule | Master #9 |
| Decoy/stale doc hygiene | An unreferenced doc under `environment/` contradicts the graded spec | Master #12 |

## environment/

| Criterion | Major-issue trigger | Detail |
|---|---|---|
| Every file needed | A file no build step, doc or test uses | Master #12 |
| Naming realism | Opaque short codes (`k7`, `qp7`), names that mislabel behavior, or obfuscation as the *sole* source of difficulty | Master #16, #17 |
| No defect/decoy reveal in comments | TODO/FIXME/BUG:/"planted"/"deliberate"/"for the grader"/"for the test" language, or a comment echoing the author's wording | Master #13, #14 |
| No lore/notes index | A notes/history/attempt-log file whose bullets map onto the planted defects or rubric lines | Master #15 |
| No answer-key module | An unused module already implements the core capability | Master #19 |
| No leaked oracle | A file byte-identical between `environment/` and `tests/`/`solution/` computes any part of the graded quantity | Master #20 |
| Docs are requirements | An environment doc with no test, or one that contradicts `instruction.md` | Master #12 |
| No solution leakage | Dockerfile bakes in `solution/`/`tests/`, references `solve.sh`, or touches a Harbor-reserved path | Master #24 |
| Dockerfile / build hygiene | Unpinned `FROM`/image, final agent base not `public.ecr.aws/docker/library/<python\|node\|golang\|rust\|eclipse-temurin\|gcc\|ruby\|maven\|debian\|ubuntu>` and no justification comment, language deps not pinned exactly (numpy/scipy/pandas and domain libraries included), apt packages version-pinned, apt without `apt-get update` or list cleanup, bare `nproc`, a reference to `solve.sh`/`test.sh`/`test_*.py`, missing `tmux`/`asciinema` | Master #26, #106; auditor `T3-BASE`, `ENV-05`, `ENV-10/11`, `ENV-13` |
| Package size / runtime fetch | `environment/` >100 MiB, a file >50 MiB, any runtime data fetch, or a build-time data fetch not pinned to an immutable literal revision and checksum-verified | Master #26, #100 |
| Vendored archive metadata | Host username/path in a tarball, wheel or `.deb` | Master #23 |
| Realistic fixtures / no hidden coupling | Test data obviously generator-shaped, or behavior secretly depends on undocumented external state | `docs/reference/QUALITY_GUIDELINES.md` |
| Single coherent incident | More than ~3 unrelated defects bundled under one thin narrative | `docs/TBSCI_HARDENING_RULES.md` §1 |
| Build platform consistency | Undeclared arch dependency (amd64-only binary, `-march=native`, `--platform=`) with no portable fallback | Master #26, #36 |
| No hidden test/solution access | `/tests`, `/solution`, `/oracle`, or Harbor log mounts reachable from the built agent image | Master #24 |
| No privileged operations | `--privileged`, docker.sock, dangerous capabilities, host bind mount instead of named volume, mutable sidecar | Master #26 |
| No AI-scaffolding filenames | `CLAUDE.md`/`AGENTS.md`/`.cursor/`/`.aider/` shipped and not itself the task's subject | — |

## solution/

| Criterion | Major-issue trigger | Detail |
|---|---|---|
| Oracle correctness (per-test + full-suite) | Any of Oracle-1/2/3 fails a named test | Master #72 |
| Independent correctness | A named algorithm/metric/transform graded with no independent re-derivation of the reference output | Master #30 (mandatory) |
| Genuine derivation | Echoes/prints the expected output, or branches on a scenario id, instead of computing it | Master #31 |
| No privileged knowledge | Encodes hidden-data identities, windows or thresholds the agent cannot see | Master #32 |
| Ablation | A touched file never reverted alone to confirm its expected failures, or whose ablation fails nothing | Master #35 |
| Cold build | Oracle never run on a no-cache build | Master #36 |
| No dead code / answer leakage | Commented-out fix, orphaned files `solve.sh` does not use, or debug prints revealing grading logic | Master #34 |
| Minimal, targeted diff | Rewrites far more than the planted defects require, or the golden solution changes already-correct fields | Master #27–#29 |
| No generator/meta commentary | Comments reference the authoring/generation process | — |
| Literal instruction fidelity | Satisfies its own paired tests while contradicting `instruction.md`'s plain wording on an untested case | invisible from "oracle passes" alone |
| Determinism / no silent failures | Unseeded randomness, unsorted listing order, silent failure paths | `docs/reference/HARD_BUT_FAIR_AUTHORING.md` |

## tests/ (separate verifier)

| Criterion | Major-issue trigger | Detail |
|---|---|---|
| NOP correctness (per-test) | Any test passing under **either** NOP run, or a NOP failure that is an error/import/crash instead of an assertion | Master #40, #73, #74 |
| Guard coupling | A guard-only test with no coupled behavioral assertion | Master #41, #42 |
| Independent reference | A test only checks a self-reported field, or computes its expected side with agent-editable code | Master #44, #45 |
| Holdouts | A held-out case whose expected value equals the public one, or held-out inputs not kept or regenerated in the verifier | Master #46 |
| Computed values, not constants | An assertion compares against a constant the agent could echo instead of a value computed from its output | Master #59; auditor gate E |
| Value, not existence | Asserts a file exists/parses without checking the value | Master #59 |
| Determinism | Wall-clock timing, race-prone ordering, live network at grade time | Master #57, #64 |
| Rubric coverage | A `rubric.txt` line has no corresponding test, or vice versa | `docs/TESTING_POLICY.md` |
| No exact-match overfitting | Asserts an exact string/order the contract never fixed | Master #47; `docs/TBSCI_HARDENING_RULES.md` §2 rule 3 |
| Test independence / own preconditions | Tests share order-dependent state, or fail in setup/teardown rather than call phase | `docs/TESTING_POLICY.md` |
| Threshold calibration / no near-Oracle gate | Threshold set without measuring the unfixed baseline, or within ~5% of Oracle without sign-off | Master #57 |
| No wall-clock latency/throughput assertions | Any timing-based pass/fail logic | Master #57 — absolute ban |
| Positive controls | A rejection-only test with no known-good control in the same function | Master #52 |
| Test count matches evidence | A ctrf.json case count differs from the current `tests/` collection | Master #53 |
| PATH/wrapper-shim resolution | Verifier resolves a tool from an agent-writable PATH | NC-12, §3 |
| Agent-code execution isolation | Executed agent code not run through the Appendix A launcher (`setpriv --reuid=12000 --regid=12000 --clear-groups --no-new-privs env -i … timeout -k 5 <PER_RUN_LIMIT>`), imported in-process, or `/logs/verifier` not root-owned and unwritable by uid 12000 | Master #54(b); auditor `T3-SETPRIV`, `T3-SANDBOX`, `ISO-01`, `ISO-02`, `ISO-03` |
| Verifier seal | `tests/Dockerfile` lacks the Appendix step 1 lines (uid 12000, `chmod -R go-rwx /tests`, root-owned `/tests` and `/logs/verifier`) | Master #54(a); auditor `T3-SEAL` |
| Artifacts as untrusted data | `test.sh` does not delete artifact symlinks that escape the artifact paths (Appendix `find … -type l … -delete` line) before grading, or deletes in-tree links a valid submission may use, or an expected value is read from an artifact path or `/app` | Master #55; auditor `T3-SYMLINK`, `TRUST-01` |
| Reward written last | No kill-to-exhaustion then `rm -f /logs/verifier/reward.txt` before the final reward write, or the pass/fail comes from a status string agent code printed | Master #56; auditor `T3-REWARD-LAST` |
| CTRF output | pytest does not write `--ctrf /logs/verifier/ctrf.json` (workspace reporter loaded as `-p ctrf_reporter`) | `docs/TESTING_POLICY.md`; auditor `VER-06` |
| Identical Oracle/agent test logic | Any conditional branch on actor identity | Master #58 |
| Per-test manifest / `TBENCH_TEST_ID` compliance | Manifest entries don't map 1:1 to CTRF cases, or the selector mishandles set/unset/unknown ids | `docs/TESTING_POLICY.md` |
| Shortcut coverage | A Master #60 shortcut not rejected, or rejected through an unplanned assertion | Master #60 |
| Binary reward, always written | `test.sh` has `set -e`, exits before writing, does not end `exit 0`, or writes a fraction/ratio | Master #39, #58 |
| Correctness before performance | A performance/score gate executes before correctness is confirmed | Master #57; `docs/TBSCI_HARDENING_RULES.md` §2 rule 5 |
| Semantic correctness, not format-only | Asserts presence/type/length without checking the actual value | Master #59 |
| Test hygiene | Names/docstrings that misdescribe the body; string-concatenation obfuscation; dead helpers | Master #43, #49 |
| `tests/Dockerfile` build hygiene | Unpinned base, deps not baked, missing `RUN mkdir -p` for a declared artifact's parent | Master #37, #38 |
| **New tactical gotchas** (byte-diff parser verification, rejection-test positive controls, precedence-test adverse preconditions, iteration-count-bounded races, resource-limit platform guards, partial-fix-pass ablation-by-building) | — | `docs/TBSCI_HARDENING_RULES.md` §9.1–9.2 |

## task.toml

| Criterion | Major-issue trigger | Detail |
|---|---|---|
| Required top-level fields | `artifacts` nested under `[verifier]` (silently dropped) or missing; missing `name` or `name` ≠ directory slug | Master #37, #61 |
| Descriptive fields | Tags outside 3–6 or generic; `expert_time_estimate_hours` missing, 0 or inconsistent with the write-ups' `## Difficulty`; `relevant_experience` missing or placeholder; an author field present but empty | Master #61; upstream rubric `expert_time_estimate` |
| Verifier / separate-mode config | `[verifier].environment_mode` not exactly `"separate"`, or `tests/Dockerfile` missing | Master #63 |
| Timeout configuration | Any of `[agent].timeout_sec`, `[verifier].timeout_sec`, `[environment].build_timeout_sec` not `28800` | Master #63 |
| Network policy (two phases) | `[environment].network_mode` not declared `"public"`; `[verifier.environment].network_mode` not declared `"no-network"` (or an allowlist without a reason in `resource-plan.md`); the removed `allow_internet` key | Master #64 |
| Taxonomy exactness | `domain`/`field` not exact kebab-case values from `docs/TASK_TAXONOMY.md` (or `field` not under `domain`); empty `subfield`; retired `category`/`subcategory`/`languages` present | Master #61, #98 |
| Write-ups not in task.toml | `difficulty_explanation`, `solution_explanation` or `verification_explanation` present in `task.toml` (they are sections of `authoring/<task>/write-ups.md`) | Master #61, #103 |
| No stale-schema residue | Top-level `version`, a `[task]` table, milestone fields, `codebase_size`, minute estimates, generator bookkeeping, a real local path (`schema_version` is optional — never a finding) | Master #65 |
| Resources | `cpus`/`memory_mb`/`storage_mb` not declared or not sized to the task; `gpus` not `0`; a `gpu_types` key; difficulty that comes from compute rather than reasoning | Master #65; upstream rubric `resource_configuration` |
| **No difficulty field** | Any `difficulty` key, tier label, percentage or pass count in `task.toml` or anywhere else in the task | Master #62 |
| Multi-container metadata | Missing `is_multi_container = true` on a genuinely multi-container task, or set on a single-container one | Master #65 |

## Write-ups (`authoring/<task>/write-ups.md`, workspace only)

| Criterion | Major-issue trigger | Detail |
|---|---|---|
| No README.md; sections present | A `README.md` in the task or at the package root; no `authoring/<task>/write-ups.md`, or `## Difficulty`, `## Reference solution`, `## Verification` missing, renamed or empty | Master #103; auditor `T3-README`; `task_check.py` |
| Difficulty write-up | Does not say what makes it hard for an expert and for an agent, whether the data is real or synthetic, and who does this work; states a rate, score or tier | Master #62, #103 |
| Reference-solution write-up | Strategy and key insight do not match what `solution/` actually does | Master #103 |
| Verification write-up | Does not say what the tests check and why that suffices, where the graded reference values come from, how every bound was calibrated, or which instances a trivial null clears | Master #100–#103 |
| Readable, not padded | Written for specialists only, or prose far past the ~400 / 300 / 600-word soft caps (a lead, never by itself a failure) | Master #103 |

## rubric.txt

| Criterion | Major-issue trigger | Detail |
|---|---|---|
| Content presence | Fewer lines than the distinct behaviors/tests it should cover, or missing entirely (packaging refuses to build) | Master #67 |
| Format compliance | A header/comment, a `[tests: …]` citation, or the filename `rubrics.txt` | Master #67 |
| Score magnitude & sum | Any magnitude outside `{1,2,3,5}`, positive sum outside 10–40, or a positive line missing its `+` | Master #67 |
| Instruction alignment | Grades something `instruction.md` never asked for, or a stated behavior has no line | Master #66 |
| Internal consistency | Two lines no correct solution can satisfy together; a behavior scored twice | Master #68, #69 |
| Arithmetic | Point budget disagrees with the real `rubric_score.txt` gradients | Master #70 |
| Positive/negative balance | No negative criterion at all | Master #67 — ≥1 required |
| Locally authored | Reads as templated/generated rather than authored for this task | — |

## trajectories/ and oracle-nop-evidence/

| Criterion | Major-issue trigger | Detail |
|---|---|---|
| Trial inventory | `trajectories/` isn't exactly `run-01..run-05`; `oracle-nop-evidence/` isn't exactly `oracle-1,2,3` + `nop-1,2` | Master #71, #90, #96 |
| Evidence freshness and independence | Evidence not bound to the current digest; duplicated control or model runs | Master #75, #76, #83 |
| SUMMARY.txt | Not exactly two lines; rewards not matching each run; sha not matching a fresh recompute | Master #77, #79, #80 |
| rubric_score.txt | Prose or notes; a verdict with no evidence citation; copied across runs; failing run scored without reading its own files | Master #78, #84–#86 |
| Task-digest binding | Any packaged trial's recorded digest differs from the current task digest | §8, `docs/TBSCI_HARDENING_RULES.md` |
| Step 3c file integrity | A file under the archived round doesn't match `collection.json`'s recorded sha256 | `scripts/archive_step3c.py` |
| Per-test Oracle/NOP seal | `artifacts/gates/<task>/step2b.json` missing/stale, or a named job directory missing/empty | `docs/TESTING_POLICY.md` |
| Completeness / no truncation | Any run has truncated tool output or an incomplete API log | STB full-fidelity kit |
| Full causal trial classification | A trial entered the difficulty count without full-trajectory classification against the eight trial-analysis criteria, or a task-side criterion / `unearned_credit` left unresolved | Master #107; `docs/reference/DIFFICULTY_GUIDELINES.md` |
| No reward hacking | Agent reads test files, disables an assertion, hardcodes the expected value, or tampers with reward/CTRF | Master #93 |
| No false failures / low-timeout artifacts | A `low_timeout` case (still progressing at cutoff) presented as a genuine failure | — |
| Measured rate | Rate not recorded as `k/5` in the workspace reports, or written into the task; any run with `exception_info` counted | Master #62, #92; `docs/reference/DIFFICULTY_GUIDELINES.md` |
| Capture settings | `reasoning_effort=xhigh` not confirmed per run; missing canonical `agent/`/`verifier/` files | Master #90, #91 |
| No trials pooled across digests | Any trial captured against a superseded digest | §8, `docs/TBSCI_HARDENING_RULES.md` |
| No PII (checked per run) | Any individual run's own `config.json`/`result.json` carries a real local machine path or a word-boundary `stb` — check every run directory by name, not one aggregate grep | Master #87, #89 |
| **Cross-run duplication check** | Agreement to 15–16 significant figures across independently-run model attempts on an error-accumulating computation | Master #83 |
| First five valid, in launch order; set moves together | Runs not the first five fidelity-complete trials at the digest and run config in launch order across rounds (a valid attempt skipped, best-of, `started_at` not increasing, mixed config); or trajectories replaced without SUMMARY, rubric scores, estimate, sha and grep moving with them | Master #94 |

## Reward-hacking corpus review

| Criterion | Major-issue trigger | Detail |
|---|---|---|
| Corpus uniqueness / novelty | No recorded comparison against prior editions/tasks exists, or a real reskin shipped anyway | This is a **manual judgment call to document**, not a scripted check — Program rule 14, `AGENTS.md` |
| Public-solution resistance | A public artifact/constant could satisfy the verifier and held-out coverage doesn't catch it | §6, `docs/TBSCI_HARDENING_RULES.md` |
| General cheat-simulation checklist | Hardcoded output, forced-success flag, partial-fix pass, deleting the graded component, or a PATH/wrapper shim all fail to be rejected | §3–4 |
| Answer reachability in the agent image | The agent image (or reachable history) contains the answer somewhere | Master #19, #20, #24 |
| Reward-hacking threat-class coverage | The task's threat model skips a standard class with no `n/a` reason | §4, `docs/TBSCI_HARDENING_RULES.md` |

## Structure / packaging

| Criterion | Major-issue trigger | Detail |
|---|---|---|
| Package layout | Inner `<task-slug>/` (exactly `instruction.md`, `task.toml`, `environment/`, `solution/`, `tests/`), `rubric.txt`, `oracle-nop-evidence/`, `trajectories/` not present as exact siblings | Master #96 |
| Trajectories evidence completeness | Missing `SUMMARY.txt`, or any run missing its own `rubric_score.txt` | `docs/reference/DELIVERY_CHECKLIST.md` |
| No packaging cruft | `rubrics.txt`, a `README.md` or other write-up file, authoring material (`provenance/`, `calibration/`, `evidence/`, `hint.md`, `write-ups.md`), AI-scaffolding files, `SOURCE.txt`, `.git`, `__pycache__` anywhere in the zip | Zip bans, `AGENTS.md` |
| No behavioral edit since freeze | Agent/grader surface changed after the seal/capture without a fresh downstream run | §8, `docs/TBSCI_HARDENING_RULES.md` |
| Final pre-zip re-verification | The last stb/canary/PII grep predates a subsequent edit | Master #97 — `verify_package.py` runs it on every candidate ZIP, and again at `--promote` |
| Auditor-judged promotion | The ZIP in `Task_Ready_To_Submit/` was not promoted by `package_task.py --promote` from a candidate whose auditor review lints `LINT_OK  ✅ Ready to Submit  (0 warning(s))` | `docs/reference/DELIVERY_CHECKLIST.md`; `tools/final-tbsci-audit-master/SKILL.md` |

## TB-Science: science, format, reproducibility (Master #98–#107)

Upstream TB-Science runs its `rubrics/task-implementation.toml` and
`rubrics/trial-analysis.toml` as LLM judges; this workspace does not run them
(`AGENTS.md` forbids `harbor check`) but folds their science criteria into Master
Section J and scores them here by hand (decisions in the v4 workspace's CI_CHECKS_REVIEW notes (not carried here)).
Criterion names in backticks are the upstream ones, paraphrased.

| Criterion | Major-issue trigger | Detail |
|---|---|---|
| Scope (`scope`, `category_and_tags`) | The task does not genuinely belong to its declared `domain`/`field`: classified by tooling rather than the scientific expertise indispensable to solve it, or an in-scope method applied to an out-of-scope subject | Master #98 |
| Scientifically grounded (`scientifically_grounded`) | Not drawn from a real research-level workflow: a textbook exercise, course project, tutorial, gimmick, generic data munging or canned fit in scientific vocabulary; no paper, dataset, pipeline or project named | Master #99 |
| Novel (`novel`) | Answer reachable by obvious web lookup or memorization of a well-known result; data or scenario with a widely available solution | Master #99, #64 |
| Ground-truth provenance (`ground_truth_provenance`) | Graded reference values have no stated origin, or were produced by `solution/` while presented as independent; oracle-derived values disclosed but never shown to survive a varied oracle stage | Master #100 |
| Graded instances discriminate (`graded_instances_discriminate`) | A trivial null (constant, range mean/median, domain centre, majority class, copy-through, the task's negative control) clears a graded instance and nothing acknowledges it; nulls run only against the suite, not per instance | Master #102 |
| Essential difficulty (`essential_difficulty`) | Most failures would come from formatting, output precision or clerical details; a bound narrow enough that only the reference reliably clears it; a tolerance never measured on an independent correct implementation | Master #101, #95 |
| Deterministic and reproducible (`deterministic_reproducible`) | Unpinned dependencies; build-time data from a mutable reference, a build argument or without checksum verification; a live service used during the trial or by the verifier; unseeded stochastic results | Master #100, #38, #64, #106 |
| Write-ups (`task_readme`, `*_explanation_quality`, `reviewable`) | `authoring/<task>/write-ups.md` duplicates the instruction instead of giving reviewer context, is misleading, or leaves a non-specialist unable to judge correctness (see the write-ups table above); a README.md in the task | Master #103 |
| Instruction suffix and verifier network | Suffix missing or reworded; verifier network not declared `"no-network"`; trial-time fetch or install in `test.sh` | Master #104, #38, #64 |
| Trial analysis — task side (`specification_completeness`, `solution_discoverability`, `verifier_correctness`, `boundary_fairness`) | Any trial whose outcome traces to a misleading or incomplete specification, an undiscoverable solution, a verifier that accepts what it should reject (or the reverse), or a pass/fail boundary that separates equivalent methods, luck or unsupported precision — and the task shipped without a fix at a fresh digest | Master #107, #101 |
| Trial analysis — credit (`unearned_credit`) | A pass that exploited the evaluation or already knew the answer counted as a solve | Master #107, #93 |
| Trial analysis — exclusions (`policy_refusal`, `execution_blocked`) | A refusal, configured-limit stop or harness fault counted as capability evidence | Master #107, #92; `AGENTS.md` rule 21 |
| Trial analysis — difficulty (`meaningful_difficulty`) | A failure (or pass) that turned on procedure, accident or a misleading surface rather than real scientific or technical work, used as difficulty evidence | Master #107, #95 |

## Lettered checks (version 4; the master owns the wording)

| Check | What the review records | Severity the master sets |
|---|---|---|
| Materiality (preamble, #2, #6, #102) | A letter-of-the-rule hit that cannot change any graded verdict — epsilon slack at the data's precision, an accepted equivalent such as 3.0 for 3, a round value in a wide band with no method producing it — is a NOTE | A test stricter than stated is still a BLOCKER (#6) |
| #26(a) | Every `FROM` / compose `image:` digest is a multi-arch manifest, or the one supported architecture is recorded | Silent single-platform digest is a finding; media type absent → NOT VERIFIED naming the registry query |
| #54(c) | After agent code runs, root never writes inside a sandbox-writable directory; multi-run scratch lives under root-owned `/work` | Secret or reward exposure is BLOCKER; a (c) breach whose only exploit needs a surviving sandbox process, with no path shown, is MAJOR |
| #58(c) | A subset selector never writes reward 1 for the whole task; unknown or empty selector fails closed | Trace every path to reward 1 |
| #59(c) | A capped decision procedure accepts a certificate that meets the stated condition by a comfortable multiple of the margin | N/A when grading is not a capped search; a cap that rejects a valid answer is BLOCKER |
| #70(b) | The rubric orders the five runs the same way the reward does | N/A when all five rewards match; otherwise MINOR, or MAJOR when it coincides with a crux-line failure on a passing run |
| #86 | A method-worded line is scored on whether the run did the method; an outcome-worded line is scored on that outcome; a quoted number may be a faithful rounding | A method line decided only by the test result is reworded as an outcome and every run re-scored |
| #101 probe | Generator tasks whose smallest shipped-set margin is under 20%: 3 fresh unselected draws (6 if borderline or inconsistent) | Not running the probe is never a finding; a correct method failing a draw, or a defective method passing one, is a margin finding |

## Review discipline

- A clean automated check, a passing reference run, or a tidy setup is
  material for a review, never the review itself.
- Don't hold a task back for a schema complaint unbacked by an actual failing
  check. A `difficulty` field or any tier word, percentage or pass count in the
  task is always a real defect (Master #62), whatever its value.
- "Passes every check in one run" and "is a solvable, fair task" are
  different claims. A task can have zero full passes across five attempts and
  still be solvable — difficulty evidence is per-requirement across attempts,
  not per-attempt across requirements.
