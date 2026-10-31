# Terminal-Bench Science Review Blockers

`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth; this page is a
condensed walk of it, grouped by artifact, with the master check numbers in
brackets. Where the two disagree, the master wins. The authoritative per-task
record is `authoring/<task>/master-checklist.md`, checked by
`python3 scripts/master_checklist.py check tasks/<task> --stage review` (Step 3b) or `--stage package` (Step 4).
(`docs/archive/tb4-portal/` holds the old TB4 portal review guideline as an archived TB4
reference only; it is not current guidance.)

The bundled auditor `tools/final-tbsci-audit-master/` (procedure `SKILL.md`,
gates T and A–K in `CHECKLIST.md`, each mapped to "Master #N") grades against
the same master and is enforced twice: `scripts/audit_task.py tree` is a
blocking step (c1) of the Step 2b gate, and at Step 4 `audit_task.py package`
runs on the candidate ZIP and `audit_task.py verdict` requires the auditor's
judged review of that exact ZIP before `package_task.py --promote`. Every item
below that the auditor also checks is a finding there too.

## Severity (master definitions — triage only)

- **BLOCKER** — a correct solution could score 0, a wrong/empty solution could
  score above 0, an expert reader would flag it on inspection, or a real test
  passes under NOP.
- **MAJOR** — a real quality defect that compounds with others or misrepresents
  the task.
- **MINOR** — polish: smaller in scope, but still a real, verified defect.

**Nothing ships with any open item.** A task ships only when every finding is
resolved — zero BLOCKER, zero MAJOR, zero MINOR. "Minor" describes how much
work a fix takes, not whether it may remain. A finding whose label is unclear
is written down and fixed, not skipped. Labels only order the fix work.

## 1. task.toml / taxonomy / metadata (Master #61–#65)

- `artifacts` missing or nested under `[verifier]`; missing top-level `name`
  (#37, #61)
- `domain`/`field` not exact values from `docs/TASK_TAXONOMY.md` (or `field` not
  under `domain`), empty `subfield` (#61; Section J below for a wrong-but-valid field)
- Retired TB4 keys `category`, `subcategory` or `languages` present; write-up keys
  `difficulty_explanation`, `solution_explanation` or `verification_explanation` in
  `task.toml` (they are sections of `authoring/<task>/write-ups.md`, #103) (#61)
- An empty author field; tags outside 3–6; placeholder or stale
  `relevant_experience`; `expert_time_estimate_hours` missing or 0 (#61)
- A `difficulty` field, or any tier label, percentage or pass count anywhere in
  the task (#62)
- `[verifier].environment_mode` not `"separate"`; `[agent].timeout_sec`,
  `[verifier].timeout_sec` or `[environment].build_timeout_sec` not `28800` (#63)
- `[environment].network_mode` not declared `"public"` (the TB4 "no-network"
  exception is retired); `[verifier.environment].network_mode` not declared, or
  not `"no-network"` without a justified allowlist; `allow_internet` used (#64)
- Top-level `version` key, `[task]`/`[[task.authors]]` table, milestone fields /
  `number_of_milestones`, `codebase_size`, minute-based estimates, generator
  bookkeeping, a real local path; `cpus`/`memory_mb`/`storage_mb` undeclared,
  `gpus` not `0` or a `gpu_types` key; `is_multi_container` set on a
  single-container task or missing on a multi-container one (#65). (`schema_version`
  is optional — not a finding either way.)
- Missing `tests/Dockerfile`

## 2. Difficulty / triviality (Master #95, #92)

- Measured k=5 GPT-5.6 rate above 3/5 shipped anyway (the rate lives in
  workspace reports; the task is hardened at a fresh digest)
- Manufactured difficulty: obscurity, spec transcription, decoys with no fair
  signal, contradictory requirements, compliance walls, tight thresholds (#95)
- Failures caused by ambiguity, env bugs, flakes, `exception_info`, or timeout
  starvation presented as difficulty (#92)
- A task-side trial-analysis FAIL (`specification_completeness`,
  `solution_discoverability`, `verifier_correctness`, `boundary_fairness`) or an
  `unearned_credit` pass unresolved (#107, #93)
- Refusals, infrastructure failures, missing evidence, or spec gaps counted as
  capability failures
- Trials pooled across task digests or run configs, or selectively replaced (a valid
  trial skipped, best-of selection, runs out of launch order — Master #94 item 1)
- Public or near-complete solution can satisfy the verifier by hard-coding
- Credible expert path does not require at least five terminal commands with
  intermediate reasoning

## 3. Instruction (Master #0–#11)

- A stated requirement with no test (#1); a test enforcing an unstated rule (#2)
- "How"-shaped sentences where an outcome would do (#3, #4)
- Pipeline vocabulary: grader, test suite, verifier, pytest, `/tests`,
  `/opt/verifier`, `test_outputs`, reward file (#5)
- A constant, tolerance or format that differs from the tests (#6)
- A named path that does not exist in the built image (#7); a schema checked
  with less exactness than the prose implies (#47); self-contradiction (#9)
- Hints / stepwise solution / detection guides / narrated defect mechanisms (#10)
- Relative paths; task name in the body; GPT-polished "You are an expert…" voice (AI drafting itself is allowed); not solvable by an
  independent domain expert from the text alone — a two-convention choice left
  unstated, a field-independent choice (path, schema, differently drawn held-out
  input, different runtime or limits on submitted code) left unstated, or a metric
  that gates the result left unnamed (#0)
- Canary or GUID-shaped strings (#11)
- Env docs smuggling how-to or splitting instructions

## 4. Environment / Dockerfile (Master #12–#26)

- A file nobody needs; dead or orphaned files (#12, #18)
- Hint comments (`TODO`, `FIXME`, `BUG:`, `planted`, `deliberate`, "for the
  grader", "for the test") or comments echoing the author's wording (#13, #14)
- A lore/notes/history/attempt-log file that itemizes the defects (#15)
- Opaque names (`k7`, `qp7`) or names that mislabel behavior (#16, #17)
- An unused module that already implements the core capability (#19)
- A file byte-identical between `environment/` and `tests/`/`solution/` that
  computes any part of the graded quantity (#20)
- An environment doc that contradicts `instruction.md`, or has no tests (#12)
- Vendored archives carrying host usernames or paths (#23)
- `COPY` of `solution/`/`tests/` (directly or via a parent dir); agent image
  creating/modifying/chowning/chmodding `/tests`, `/solution`, `/oracle`,
  `/logs/verifier`, `/logs/artifacts` (#24)
- A decoy that is unreachable, unfair, or labelled as a decoy (#25)
- Digest-unpinned `FROM`/compose image; a final agent base other than
  `public.ecr.aws/docker/library/<python|node|golang|rust|eclipse-temurin|gcc|ruby|maven|debian|ubuntu>`
  without a justification comment (auditor `T3-BASE`); missing `tmux`/`asciinema` in the agent image;
  language packages not pinned exactly; apt packages version-pinned;
  `environment/` >100 MiB or a file >50 MiB; `--privileged`, docker socket or
  dangerous capability; `FROM --platform=...` or amd64-only artifact without a
  fallback (#26)
- Runtime HTTP/API/data fetch from environment code or `solution/**`
- Compose host bind mount instead of named volume; mutable `latest` reference (#106)

## 5. Solution (Master #27–#36)

- A touched file with no stated defect, or an out-of-scope delta (#27–#29)
- Correctness never verified independently for a named algorithm/metric (#30)
- Scenario-id branching or privileged knowledge of hidden data (#31, #32)
- Agents converging on a different answer, and the reference not re-checked (#33)
- Orphaned files `solve.sh` does not use (#34)
- A fix never ablated one file at a time, or whose ablation fails nothing (#35)
- Oracle not passing from a cold build (#36)
- Non-deterministic / unseeded randomness; silent failures

## 6. Verifier (Master #37–#60)

- Verifier deps installed at trial time or unpinned (#38)
- `set -e` in `tests/test.sh`; a path that exits before the reward write; last
  command not `exit 0` (#39)
- Any test passing under NOP; a guard-only test not coupled to a behavioral
  assertion (#40–#42)
- Test body not matching its name/docstring (#43, #51)
- Ground truth computed by agent-editable code; fixtures the agent can tamper
  with feeding the expected value (#44, #45)
- A holdout whose expected value does not differ from the public case (#46)
- Exactness or tolerances enforced differently from the docs (#47, #6)
- String-concatenation obfuscation; dead test code (#49, #50)
- A fail-closed test with no positive control in the same function (#52)
- Agent code executed privileged, unbounded, unsanitized, imported in-process, or
  with write access to `/logs/verifier` — i.e. not via the Appendix A launcher
  `setpriv --reuid=12000 --regid=12000 --clear-groups --no-new-privs env -i …
  timeout -k 5 <PER_RUN_LIMIT>` (auditor `T3-SETPRIV`, `T3-SANDBOX`, `ISO-01/02/03`) (#54)
- `tests/Dockerfile` without the Appendix step 1 seal — `/tests` readable by uid
  12000 (auditor `T3-SEAL`) (#54)
- Artifact symlinks not deleted before grading, or an expected value read from an
  artifact path (auditor `T3-SYMLINK`, `TRUST-01`) (#55)
- Reward not the last thing written: no kill-to-exhaustion and `rm -f` reward
  before the final write (auditor `T3-REWARD-LAST`) (#56)
- pytest not writing `--ctrf /logs/verifier/ctrf.json` (auditor `VER-06`)
- Assertions against constants the agent could echo instead of values computed
  from its output; held-out inputs not kept or regenerated in the verifier (#46)
- Any wall-clock latency, throughput or percentile assertion; a threshold set
  from model outcomes or within ~5% of the reference without recorded sign-off (#57)
- Non-binary reward; Oracle/agent conditional logic (#58)
- Existence/format-only checks (#59)
- A #60 shortcut rejected through an unplanned test, or not rejected (#60)
- Non-standard environment variable in `tests/test.sh` without a default

## 7. Novelty / originality

- Reskin of any prior benchmark edition or own prior task
- Answer reachable by web lookup or by memorizing a well-known published result
  (#99; see Section J)

## 8. Rubric (Master #66–#69, #70)

- Missing or empty `tasks/<task>/rubric.txt` (it must exist before the Step 2b
  gate: the auditor screen stages it)
- A line grading behavior the instruction never asks for (#66)
- Any line not exactly `Agent <behavior>, +N`/`, -N`; header, blank line or
  citation; magnitude 4 or outside {1,2,3,5}; unsigned positive; no negative;
  positive sum outside 10–40 (#67)
- Contradictory or double-counted lines (#68, #69)
- Point budget inconsistent with the real `rubric_score.txt` arithmetic (#70)

## 9. Evidence and trajectories (Master #71–#94)

- `oracle-nop-evidence/` not exactly Oracle x3 + NOP x2 with `ctrf.json`,
  `reward.txt`, `test-stdout.txt`; any Oracle test not passing; any NOP test not
  explicitly failing on a genuine assertion (#71–#74)
- Evidence not bound to the current digest; duplicated runs (#75, #76, #83)
- `SUMMARY.txt` not exactly two lines, rewards not matching each run, bundle
  sha not matching a fresh recompute (#77, #79, #80)
- A `rubric_score.txt` with prose, a verdict without an evidence citation, or
  copied from another run (#78, #85, #86); a failing run scored without reading
  its own files (#84)
- PII (`/Users/`, `/private/tmp/`, host home), word-boundary `stb`, or a canary
  in any run or job directory; hand-edited model-name fields (#87–#89)
- Missing canonical `agent/` or `verifier/` files in any run; `reasoning_effort`
  not `xhigh` on every run; `exception_info` populated (#90–#92)
- Reward-hacking behavior in any trajectory (#93)
- Runs that are not the first five fidelity-complete trials at the digest and run config in
  launch order, or a rerun whose SUMMARY / rubric scores / estimate / sha / grep did not
  move with the five (#94)

## 10. Zip / packaging (Master #96, #97)

- Structure not exactly the inner `<task-slug>/` (five members: `instruction.md`,
  `task.toml`, `environment/`, `solution/`, `tests/`) plus
  `rubric.txt`, `oracle-nop-evidence/`, `trajectories/` (#96)
- `SOURCE.txt`, `.DS_Store`, `__MACOSX`, `._*`, `.git`, `__pycache__`, `*.pyc`,
  `rubrics.txt`, a `README.md` or other write-up file anywhere, AI scaffolding, any
  Step 2b/3b gate or review record, authoring documents (`provenance/`, `calibration/`, `evidence/`,
  `hint.md`), or unrelated evidence in the ZIP (#96)
- The final PII/`stb`/canary grep not run as the last step (#97)
- Package evidence not matching the current task digest
- A ZIP in `Task_Ready_To_Submit/` that did not come from `package_task.py
  --promote`, or a candidate promoted without an auditor review of those exact
  bytes that lints `LINT_OK  ✅ Ready to Submit  (0 warning(s))`

## 11. TB-Science: science, format, reproducibility (Master #98–#107)

- **Wrong domain/field.** The declared `domain`/`field` is valid but not where the
  task belongs: classified by tooling or "the agent writes code" instead of the
  scientific expertise indispensable to solve it; an in-scope method (statistics,
  optimization, ML, simulation) applied to an out-of-scope subject; generic software,
  data munging or a canned fit dressed in scientific vocabulary (#98)
- Not research-level: a textbook exercise, course project, tutorial or gimmick; no
  real paper, dataset, pipeline or project named in `authoring/<task>/write-ups.md` (#99)
- **Web-lookupable answer.** The answer is reachable by an obvious web search or by
  memorizing a well-known published result, or the data/scenario is one whose solution
  is widely available — agents always have open internet (#99, #64)
- Data with no recorded origin (source, version/DOI or URL, licence, preprocessing;
  or generator and parameters in `authoring/<task>/provenance/`); a build-time fetch
  not pinned to an immutable literal revision and checksum-verified; grader-only data
  in the agent image (#100)
- **Undisclosed oracle-derived ground truth.** Graded reference values produced by
  running `solution/` but presented as independent, or with no stated origin at all;
  the write-ups' `## Verification` silent on where they come from (#100)
- **Unjustified tolerances.** A tolerance, threshold, percentile bound or fuzzy match
  that does not state what it brackets and which legitimate variation it absorbs, was
  never measured on an independent correct implementation differing from `solution/`
  structurally, is tightened until only the reference clears it, or claims precision
  finer than the science supports (#101, #95)
- A graded instance a trivial null (constant, range mean/median, domain centre,
  majority class, copy-through, the task's own negative control) clears, not
  acknowledged in the write-ups' `## Verification` (#102)
- **README.md present or write-ups missing.** A `README.md` in the task or at the
  package root (auditor `T3-README`); no `authoring/<task>/write-ups.md`, or one
  missing, renaming or leaving empty `## Difficulty`, `## Reference solution` or
  `## Verification`; write-ups that disagree with what `solution/` or `tests/` do; a
  pass rate, model score, tier or canary in them (#103, #62)
- **Missing instruction suffix.** `instruction.md` does not end with exactly
  `You have 28800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.`
  (blank line before, single newline after, N equal to `[agent].timeout_sec`) (#104)
- **Verifier with network.** `[verifier.environment].network_mode` missing, `"public"`,
  or an allowlist without a recorded reason; `tests/test.sh` doing a trial-time fetch
  (`curl|sh`, raw `curl`/`wget` of an external host, `git clone`) or installing pytest
  or other tooling (#38, #64)
- Bare `nproc` in a Dockerfile, `test.sh` or `solve.sh`; compose host bind mount;
  `FROM --platform=`; apt without `apt-get update` or list cleanup; an unpinned pip/uv
  install (numpy, scipy, pandas, domain libraries included); the agent Dockerfile
  naming `solve.sh`, `test.sh` or `test_*.py`; unseeded stochastic results (#106)
- A Step 3c trial not classified against the eight trial-analysis criteria, or a
  task-side criterion failing and the task shipped anyway (#107)

## When to run

| Step | Focus |
|------|--------|
| Idea (1 optional / 2a) | Domain/field fit, research grounding, not web-lookupable, provenance plan, no milestones, #95, #57, #98–#100 |
| Construction (2b) | Sections A–E by construction; `audit_task.py tree` PASS (gate step c1); `master_checklist.py auto` clean |
| Review (3b) | Every check this step answers, with evidence; pre-trial evidence for #1, #2, #15, #40, #53, #57 and #101 written on those PENDING lines (with #33, #70, #71–#94, #96, #97, #107); every auditor LEAD answered; auditor gates T, A–K; `--stage review` |
| Difficulty (3c) | Frozen digest, causal trial classification against the eight trial-analysis criteria, #92, #94, #107 |
| Package (4) | Post-trial verdicts #1, #2, #15, #33, #40, #53, #57, #70, #71–#94, #96, #97, #101, #107; `--stage package`; candidate build (`verify_package.py` + `audit_task.py package`) → auditor judged review → `--promote` |
