# Package rules — the single source of truth

> **`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth**, then
> `docs/reference/DELIVERY_CHECKLIST.md`, then this file. Where this file disagrees with either —
> folder layout, file names, control counts, `task.toml` fields — they win and this file
> is amended to match. Everything else here (what the workspace verifies before it
> packages, and why) still stands. Master check numbers are cited as "Master #N".

These rules are authoritative for **both** sides of this workspace:

- the authoring scripts and policy docs (`scripts/`, `AGENTS.md`, `docs/`, `prompts/`);
- the audit tool (`tools/final-tbsci-audit-master/`, shipped as `final-tbsci-audit-master.zip`) —
  the only auditor in the workspace, run by `scripts/audit_task.py` at the Step 2b gate and
  on every Step 4 candidate.

Where any other document disagrees with this file, this file wins — except the master
checklist and the delivery checklist, above. When a rule changes, change it here first, then update both
sides in the same commit.

## What ships

The package ZIP holds one top-level `<task-slug>/` folder with exactly four members
(`docs/reference/DELIVERY_CHECKLIST.md`, "Folder structure"). It is a local deliverable for
private delivery to a buyer — nothing is submitted anywhere:

```
<task-slug>/
├── <task-slug>/            task.toml  instruction.md  environment/  solution/  tests/
├── rubric.txt              a SIBLING of the task folder, not a member of it
├── oracle-nop-evidence/    oracle-1..3, nop-1..2; ctrf.json + reward.txt + test-stdout.txt each
└── trajectories/           run-01..run-05 (agent/, verifier/, config.json, result.json,
                            rubric_score.txt) and SUMMARY.txt
```

Earlier rounds shipped the task files at the ZIP root with `rubric.txt` and
`trajectories/` beside them, and shipped the round under its capture name with its
job-level logs. That layout is retired. The five model trials are renamed
`run-01`..`run-05` in launch order (`<slug>-gpt56-t1` → `run-01`), each carrying only
its own trial files; the Oracle and NOP controls move out of `trajectories/` into
`oracle-nop-evidence/`, reduced to the three files that carry the verdict.
`scripts/package_task.py` emits exactly this and nothing else.

`trajectories/SUMMARY.txt` is two lines of data, no prose:

```
<task-slug> sha=<task digest, bare hex> model=gpt-5.6 (reasoning_effort=xhigh)
5 runs, rewards: [r1, r2, r3, r4, r5]
```

`model=` is the stripped name (Master #77): drop everything through the last `/` and a leading `@`. Each run's `config.json` keeps `@openai/gpt-5.6`.

`sha=` is the **bundle sha** of the inner task folder — what a reviewer gets by running,
from inside `<task-slug>/<task-slug>/`,
`find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum`
(Master #80; `scripts/bundle_sha.py` prints the same value). It replaced the workspace
task digest in this field because a reviewer cannot recompute that fold. The workspace
digest still binds every internal record (`task-digest.txt`, `collection.json`, the
seal, the reviews, the master record); `package_task.py` proves both describe the same
files by checking the digest against the seal and round and hashing exactly the files it
writes. Packaging recomputes the sha, and every reward, from disk; nothing is carried
forward from an earlier draft.

## What must never ship

**Step 2b and Step 3b records of any kind are workspace-only.** They prove the task
is sound *to us*; they are not part of the artifact. Excluded:

- `trajectories/per-test/**` — the sealed per-test Oracle/NOP job bundles,
  `step2b-seal.json`, `step2b-report.json`;
- `authoring/**` — `controls.md`, `step3b-review.md`, `master-checklist.md`, traceability,
  threat model, `provenance/`, `calibration/`, the optional `hint.md`;
- `artifacts/gates/**`, `artifacts/reviews/**`, `artifacts/regrade/**`;
- `evidence-*/`, `jobs/`, any pre-hardening captured round;
- AI scaffolding (`AGENTS.md`, `.cursor/`, `.claude/`, `CLAUDE.md`, `skills.md`);
- caches, secrets, **canary strings**, `rubrics.txt`, and any `README.md` or other
  write-up file anywhere in the ZIP (the write-ups stay in `authoring/<task>/write-ups.md`,
  Master #96, #103);
- **`SOURCE.txt`** anywhere in the ZIP. `archive_step3c.py` writes one into the round to
  record where the capture came from; it is a workspace record and the checklist bans it
  from the package. The new layout copies from the trial directories, so it cannot travel
  by accident, and `package_task.py` rejects the name wherever it appears;
- `.DS_Store`, `__MACOSX`, `._*`, `.git`, `__pycache__`, `*.pyc` anywhere in the ZIP —
  including inside `environment/` or `tests/`, where packaging fails rather than quietly
  dropping them, since a silent drop would ship a task that differs from its digest.

## The rules

0. **Master record.** `authoring/<task>/master-checklist.md` answers every check in
   `MASTER_CHECKLIST_TBSCI.md` for the current task digest — PASS with evidence, N/A with
   a reason, or AUTO where a script enforces the check completely — with zero FAIL and
   zero PENDING. `package_task.py` refuses otherwise
   (`python3 scripts/master_checklist.py check tasks/<task> --stage package`), and after
   writing the candidate ZIP it runs `scripts/verify_package.py` and the auditor's scripted
   legs (`scripts/audit_task.py package`) over it and deletes it on any finding. The
   candidate becomes a deliverable only through `package_task.py --promote`, which requires
   the auditor's judged review of those exact bytes to lint `✅ Ready to Submit` with zero
   warnings (`scripts/audit_task.py verdict`). No severity ships: a MINOR finding blocks
   exactly like a BLOCKER.
1. **Rubric.** `rubric.txt` is required in the final package, as a sibling of the task
   folder. Validate (Master #66–#70): at least one negative criterion; 10–40 positive
   points in total; exactly `Agent <behavior>, +N` or `, -N` on every line (a single
   space after the comma, no period before it); scores limited to ±1, ±2, ±3, ±5 (never
   4); explicit `+` on positive scores. The file is **criterion lines only** — no `#` header of any style, no title,
   no comments, no blank lines, no `[tests: …]` citations, and every line begins with
   the literal word `Agent`. Confirm it actually has content: a rubric that was checked
   only for consistency with the tests once shipped with a header and one throwaway
   line, because comparing existing lines against the tests cannot notice that there are
   no lines.
2. **Trajectories.** Require a complete five-attempt GPT-5.6 xhigh round with complete,
   untruncated trajectories, plus **Oracle ×3** and **NOP ×2** control traces, all tied
   to the current task digest. No stale or unrelated trajectories. The five runs are the
   first five fidelity-complete trials at the current digest and run config, in launch
   order across rounds, with no valid attempt skipped (Master #94 item 1): one captured
   round, or one assembled by `scripts/compose_step3c.py` (its `composition.json` stays in
   the workspace; nothing new ships). `package_task.py` numbers `run-01..05` from the
   round's `t1..t5`, which compose already put in launch order, and `verify_package.py`
   refuses runs whose `result.json` trial ids repeat, whose `started_at` does not strictly
   increase, or which disagree on `task_checksum` or agent configuration. Controls may come
   from any same-digest, same-config round, including a `CONTROLS_ONLY=1` run. (NOP ×1 was the rule
   through the previous edition; the checklist raised it to ×2, and both NOP runs must
   reward 0.0 with **every** test failing, as all three Oracle runs must reward 1.0 with
   every test passing. `package_task.py` re-reads each control's `reward.txt`,
   `result.json` and `ctrf.json` and refuses the package if any of that is untrue.)
   What ships per run, as `trajectories/run-0N/`: `agent/` (the untruncated ATIF,
   `recording.cast`, `api-calls.jsonl`), `verifier/` (`ctrf.json`, `reward.txt`,
   `test-stdout.txt`), `config.json`, `result.json` and the `rubric_score.txt` written
   for that run. `reasoning_effort = "xhigh"` is required capture metadata in every
   `config.json`; packaging fails if a run lacks it or carries any other value, and the
   key is never renamed or downgraded. The job-level `console.log`, `job.log`,
   `lock.json` and `trial.log` stay in the workspace round — they belong to the capture,
   not to a run — as does the agent's **submitted output artifacts** directory
   (`artifacts/`), which for a task whose declared artifacts are large media dwarfs the
   evidence a reviewer reads (one audio task: 1.41 GB of WAV against 8 MB of
   trajectory). The omission used to be listed in `trajectories/omitted-artifacts.json`;
   the checklist's `trajectories/` holds `run-01..05` and `SUMMARY.txt` and nothing else,
   so that file no longer ships and the packaging report carries the omitted file count
   and byte total instead. The full artifacts stay in the workspace round where
   `regrade_step3c.py` still needs them.
   `task-digest.txt` and `package-digest.txt` are likewise no longer ZIP members. The
   round's own records (`collection.json`, `task-digest.txt`, `fidelity-check.log`,
   `SOURCE.txt`) are verified at packaging time and stay in the workspace; the digest
   they carry reaches the reviewer as the `sha=` field of `SUMMARY.txt`. The external
   TB-Science audit tool used to bind packaged traces by searching the round for *its own*
   digest (`tbsci_static_screen.py` `task_digest`), which is why `package-digest.txt`
   existed; the delivery layout has no member it could be written to, so
   `package_task.py` still computes that number over the packaged task files and reports
   it as `auditor_task_digest` rather than shipping it. `rubric.txt`,
   `oracle-nop-evidence/` and `trajectories/` are required package members, never
   `STRUCT-VENDOR` or extraneous.
   **`rubric_score.txt` and `SUMMARY.txt` are required, not optional.** Every
   `run-0N/` carries a `rubric_score.txt` scoring that run against every line of
   `rubric.txt`, every verdict with a parenthetical evidence citation from that run's own
   trajectory (Master #78, #86), the five files pairwise distinct (Master #85), and
   `trajectories/` carries one two-line `SUMMARY.txt`. Both are data
   files: no prose, no explanatory notes, no "note:" justifying a number. Writing a
   score needs the run's trajectory read, so `package_task.py` does not generate them —
   it validates them, against the rubric and against that run's own reward and CTRF
   counts, and refuses to package if one is missing, malformed, or carrying numbers that
   disagree with the trial on disk. The workspace keeps them outside the frozen round
   (default `artifacts/rubric-scores/<task>/<round>/run-0N.txt`, overridable with
   `--rubric-scores`), because an extra file inside the round breaks its
   `collection.json` `source_sha256` inventory.
3. **`rubric.txt`, `oracle-nop-evidence/` and `trajectories/` are required package
   members**, and they are siblings of the inner `<task-slug>/` folder rather than
   members of it. Never report them as `STRUCT-VENDOR`, informational, or extraneous.
4. **Reject `rubrics.txt` and `README.md`.** Neither the inner `<task-slug>/` nor the
   package root carries a `README.md`, and no other write-up file ships (Master #96,
   #103). Reviewer-facing explanations come from the workspace record
   `authoring/<task>/write-ups.md` — its `## Difficulty`, `## Reference solution` and
   `## Verification` sections (Master #103) — never from `task.toml` or the ZIP.
5. **Reject canary strings.** Do not report missing canaries, recommend adding them, or
   recommend a GUID.
6. **Authorship is optional.** `author_name`, `author_email` and `author_organization`
   may be omitted; when present each is a non-empty string (Master #61). The TB4
   `"anonymous"` rule is retired (there is no vendor review to anonymise for). Do not
   require `author_github`, `author_profile`, `referred_by` or `conflicts_of_interest`
   (upstream Hub fields, rejected in the v4 workspace's TBSCI_REVAMP notes (not carried here)).
7. **Task name; `schema_version` optional.** Validate the top-level
   `name = "<directory-slug>"`. Reject a `[task]` table (it duplicates the top-level
   name) and do not require a `terminal-bench-science/<slug>` namespace. `schema_version`
   is **optional** — present or absent is not a finding (upstream `task-template.toml`
   carries one; nothing in Harbor branches on it, Master #65). A top-level `version` key
   is still rejected. (History: the previous edition required `schema_version = "1.1"`,
   the TB4 workspace then banned it; both rules are retired.) Also rejected: milestone
   fields, `codebase_size`, minute-based time estimates, `[reference_pattern]` or any
   generator bookkeeping, and any real local machine path. `[environment]` declares
   `cpus`, `memory_mb`, `storage_mb` and `gpus = 0`, with no `gpu_types` (Master #65).
8. **Metadata fields.** Require (Master #61, #98): `domain` and `field` (exact
   kebab-case values from `docs/TASK_TAXONOMY.md`, `field` listed under `domain`),
   `subfield` (non-empty free text naming the research specialty), `tags` (3–6),
   `expert_time_estimate_hours` and a substantive `relevant_experience` — current, not a
   placeholder or a stale draft. Reject the retired TB4 keys `category`, `subcategory`
   and `languages`, and reject `difficulty_explanation`, `solution_explanation` and
   `verification_explanation` in `task.toml`: those write-ups are sections of the workspace
   record `authoring/<task>/write-ups.md` (Master #103). `is_multi_container = true` only when the task really is
   multi-container; omit it otherwise.
   **There is no `difficulty` field** (Master #62), and no tier label, percentage or
   pass-count appears anywhere in the task; the write-ups' `## Difficulty`
   explains in plain language what makes the task hard. The k=5 GPT-5.6
   rate is still measured and classified causally at Step 3c, and it is recorded in the
   workspace difficulty report and in SUMMARY.txt's reward array only. (The previous
   revision of this rule required `difficulty = hard|medium|easy|too easy` read off the
   measured rate; that field is now a finding.) A descriptive edit — a descriptive
   `[metadata]` key such as `expert_time_estimate_hours` corrected after a rerun (Master
   #94 item 4) — changes the **full** task digest but neither graded surface, because
   `scripts/common.py` folds the descriptive keys out of the agent digest and `tests/`
   is untouched, so it is a
   **re-seal, not a re-gate**: `gate_step2b.sh --reseal-only` re-runs the static screen
   and re-stamps the existing seal (`evidence.py reseal` refuses unless both graded
   digests are byte-identical), `stage_reports.py rebind-review` re-points the Step 3b
   review's digest header, the difficulty report is re-headed with the review's new
   SHA256, and the master record is re-walked and re-headed. A behavioral edit still
   re-enters the full gate. See `docs/TBSCI_HARDENING_RULES.md` §8.3. An edit to
   `authoring/<task>/write-ups.md` touches no task file and needs no re-seal.
9. **Network mode — declared on both phases** (Master #64; upstream
   `check-allow-internet.sh`). The agent phase declares
   `[environment].network_mode = "public"`, always: the TB4 exception ("no-network when
   internet would let the agent skip the work") is retired — a task whose answer is
   reachable by web lookup is a design defect under Master #99, not a reason to cut the
   network. The verifier phase declares `[verifier.environment].network_mode =
   "no-network"`; `"allowlist"` with a non-empty `allowed_hosts` only when the verifier
   genuinely needs one host, justified in `authoring/<task>/resource-plan.md`. The
   deprecated `allow_internet` key is not used. Dependencies are baked at build time
   either way, and `tests/test.sh` performs no trial-time fetch or install.
10. **Timeouts.** Exactly 28800 s in all three places — `[agent].timeout_sec`,
    `[verifier].timeout_sec` and `[environment].build_timeout_sec` — on every task,
    **from creation** (Master #63: "deliberately — not a value to fix down"). A failure
    must be a real rule violation and never the clock running out. The old "1800–28800
    band while authoring, raise before packaging" rule is retired: raising a timeout after
    Step 3c would be a behavioral edit that voids the runs. `hardening_check.py` enforces
    28800 at every gate and `package_task.py` re-asserts it. A task should still not
    *need* eight hours — a run that only passes near the ceiling is telling you
    something. **Require the instruction suffix** (Master #104, upstream
    `check-instruction-suffix.sh`): `instruction.md` ends with exactly
    `You have 28800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.`
    — preceded by a blank line, followed by one newline, N equal to `[agent].timeout_sec`.
    (The TB4 rule "no timeout sentence in `instruction.md`" is reversed.)
11. **Slug.** Kebab-case, equal to the top-level `name`. 2–4 hyphen tokens is typical;
    length is not itself a finding as long as the slug reads as a name, not a sentence
    (Master #61).
12. **Test selection.** Strictly require `TBENCH_TEST_ID` or `tests/test_manifest.json`.
13. **CTRF.** Require valid per-test CTRF output, permitting `pytest-json-ctrf`. Do not
    require upstream-specific pytest or CTRF package versions.
14. **Controls.** Require full-suite Oracle x3 success (reward 1.0, every test passing)
    and NOP x2 failure (reward 0.0, every test explicitly `failed` through a real
    assertion — Master #40, #72–#74), three and two genuinely independent executions
    (Master #76). Do **not** require a fixed NC-01–NC-14 negative-control matrix;
    every shortcut in Master #60 is instead rejected by its own named assertion.
15. **Negative controls may be reviewed when supplied, but their absence is not a
    submission finding.** Anti-cheat review instead verifies isolation, hidden-test
    protection, independent recomputation, and reward-channel integrity.
16. **Reject wall-clock latency, throughput, speedup or runtime thresholds that affect
    reward** — an absolute ban, not acceptable merely because they are calibrated
    (Master #57). Deterministic work counters and memory bounds remain legal when
    efficiency is part of the public contract: fixed before model trials from the public
    objective and a realistic baseline, admitting a fundamentally different correct
    strategy, not within ~5% of the reference without recorded sign-off, and checked only
    after correctness.
17. **Images.** Every Docker `FROM` and Compose `image:` must be digest-pinned. The final
    agent base must be canonical or carry a credible justification; where a credible
    justification exists, do not emit `T3-BASE`.
18. **Size.** `environment/` ≤100 MiB total and ≤50 MiB per file. Put install commands in
    the Dockerfile rather than carrying compiled binaries.
19. **Terminal tooling.** Require `tmux` and `asciinema`, installed explicitly, in the
    **final agent image only**, not in the verifier image. apt packages are installed
    without version pins; language packages are pinned to exact versions (Master #26).
20. **`trial_evidence.py` Python 3.11 compatibility.** Line 104 placed a regex containing
    a backslash inside an f-string expression, raising `SyntaxError` on 3.11. Compute the
    `re.sub(...)` result before constructing the f-string. *(Fixed.)*
21. **Verifier seal (Master #54–#56, the master's Appendix A).** Require the Appendix A
    launcher (`setpriv --reuid=12000 … env -i … timeout -k <PER_RUN_LIMIT>`) for every
    execution of the agent's program, a root-only `/tests` and root-owned `/work` in the
    verifier Dockerfile, artifact symlinks deleted before grading, and kill-to-exhaustion
    + `rm -f` reward before the reward write (auditor `T3-SETPRIV`, `T3-SANDBOX`,
    `T3-SEAL`, `T3-SYMLINK`, `T3-REWARD-LAST`, `T3-THREADS`).
22. **Leads, not findings.** Test-suite length, missing test docstrings, ordinary bold
    text, and phrases such as "Your goal is…" are review leads, never automatic findings.
23. **Remediation text** references the `## Verification` section of
    `authoring/<task>/write-ups.md` or
    the supplied audit evidence — never a retired `*_explanation` key in `task.toml`.
24. **A static-screen pass never produces a final "Ready to Submit" verdict by itself.**
    Readiness requires valid package evidence, current-digest trajectories, a complete
    master record, a `verify_package.py` PASS on the ZIP itself, and the auditor's judged
    review of that ZIP linting `✅ Ready to Submit` with zero warnings.
25. **PII and internal names.** Zero `/Users/`, `/private/tmp/`, host `/home/<user>/`
    (in-container homes such as `/home/agent` are fine), word-boundary case-sensitive
    `stb` or canary marker in any shipped file — checked per run and per control
    directory, never by one aggregate grep (Master #87, #88, #97). Packaging rewrites host
    paths in each run's `config.json`/`result.json` to repo-relative form, never touches a
    captured model-name field (Master #89), and refuses the ZIP if anything remains.
26. **Freshness.** Every shipped evidence file is newer than every task file that could
    change it: agent outputs newer than `instruction.md`/`environment/`/`solution/`,
    verifier outputs and control CTRFs newer than those and `tests/` (Master #75).
    The ZIP keeps source mtimes so a reviewer can check this.
27. **No README.md (Master #103).** A `README.md` in the inner task folder or at the
    package root is a finding (auditor `T3-README`), and no other write-up file ships.
    The write-ups are the workspace record `authoring/<task>/write-ups.md` with three
    non-empty sections, exactly `## Difficulty`, `## Reference solution` and
    `## Verification`, written for a non-domain reader, current with what `solution/`
    and `tests/` actually do, and naming where the graded reference values come from
    (Master #100). Prose caps of roughly 400 / 300 / 600 words are review leads, never
    failures; no pass rate, model score, tier or canary (Master #62, #11).
28. **Section J judgment checks.** Master #98–#103 and #106 are answered in the master
    record at Step 3b (taxonomy and scope, scientific grounding and novelty, provenance,
    tolerances, discriminating instances, write-ups, reproducibility), #104 may be
    AUTO, #105 is N/A (merged into #37, #38 and #64), and #107 (trial analysis against the eight upstream `trial-analysis.toml`
    criteria) is answered at Step 4 with Sections G/H. Packaging refuses a record that
    leaves any of them FAIL or PENDING (rule 0).
