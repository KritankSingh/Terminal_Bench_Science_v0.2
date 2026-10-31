# Terminal-Bench Science — Single-Task Audit Checklist

Gates for ONE Terminal-Bench Science (TB-Science) task bundle, walked top to bottom.

**Authority.** Under the default `terminus` profile the top authority is
`reference/MASTER_CHECKLIST_TBSCI.md` (a copy of the repo-root
`MASTER_CHECKLIST_TBSCI.md`, checks 0–107, with the TB-Science checks in its
Section J, #98–#107), then `reference/DELIVERY_CHECKLIST.md`, then this file. Every gate below carries the **Master #N** check(s) it enforces;
the **Master coverage map** at the end lists every master check, the gate that
walks it, and whether the scripts enforce it mechanically (screen code) or you
answer it by reading. Where a gate here disagrees with the master, the master
wins. The master's severity rule is binding under `terminus`: BLOCKER / MAJOR /
MINOR order the fixes, but a task ships only with **zero findings of every
severity** — "Minor" is fix size, not permission.

Each gate also names the upstream artefact that enforces it — a `ci_checks/check-*`
static check, a criterion from `rubrics/task-implementation.toml` or
`rubrics/trial-analysis.toml` (`harbor-framework/terminal-bench-science`), a
trial-analysis flag, or a real Terminal-Bench 4.0 removal/fix from the auditor's
calibration history — so a finding here predicts what a maintainer's review
would say. Gates with no upstream tag come from the
TB 2.1 / Terminus 3 defect record and still hold under the separate verifier.
A defect matching nothing here is still a defect: classify it by effect.

**Severity**

- **[B] BLOCKER** — a correct solution can score 0; a wrong, empty, hand-written
  or hacked submission can score 1; the environment or verifier cannot run as
  configured; security; the difficulty is manufactured or the task is saturated /
  publicly solved. Never merges.
- **[M] MAJOR** — fails a CI static check or a rubric criterion the maintainers
  send back for, or a real quality defect. Fix before submission.
- **[m] MINOR** — polish, smaller in scope, still a real defect. Under
  `terminus` an open MINOR also blocks shipping (Master: "zero BLOCKER, zero
  MAJOR, zero MINOR").

- **[L] LEAD** — no severity. A question the read must answer, never counted in
  the verdict.

**Profiles.** The checklist is walked under one of two profiles; every script
takes `--profile terminus|upstream` (default `terminus`).

- **`terminus`** (default) — the program package standard. Validity, fairness,
  difficulty and the separate-verifier physics are graded exactly as below, plus
  gate **T** (the package standard). The upstream-PR conventions the standard
  *inverts* are **dropped, not downgraded**: canary presence, `[task] name`,
  `allow_internet`, the upstream 28800 s *norm* finding (terminus enforces exactly
  28800 itself, T10 / Master #63), the upstream pytest / CTRF version pins, and
  the treatment of `rubric.txt` / `trajectories/` as extraneous. Reporting them
  here would send the author the wrong way. The conventions the program
  *adopted* from upstream count under both profiles: the instruction suffix
  (B5), the kebab-case slug (A2; length is a lead, not a finding) and the domain / field / subfield taxonomy
  (A4). Upstream's README.md requirement is NOT adopted (Master #103,
  2026-10-07): under `terminus` a README.md in the task is the finding (T30).
  Gate T's authority is `reference/MASTER_CHECKLIST_TBSCI.md`, then `reference/DELIVERY_CHECKLIST.md`,
  both shipped beside this file.
- **`upstream`** — the task is headed for a PR to
  `harbor-framework/terminal-bench-science`; every `check-*` and rubric
  convention counts as written below and gate T does not apply. This workspace
  opens no such PR (private delivery); the profile is for comparison only.

Gates tagged **[up]** are upstream-only; gates tagged **[t]** are terminus-only.

Effect test when unsure: correct → 0? wrong → 1? cannot run? → [B]. Would CI or
the rubric FAIL it, or would a senior reviewer request changes? → [M]. Else [m].

---

## T · The terminus package standard [t]

Walked first under the default profile. Every item here is a *package* rule; the
physics gates A–K still apply on top.

**The authority for this gate is `reference/MASTER_CHECKLIST_TBSCI.md`**, with
`reference/DELIVERY_CHECKLIST.md` as its delivery-format view (both shipped beside
this file). Where anything below disagrees with the master, the master wins. Each
item names the master check(s) it enforces and the screen code that enforces it.

**The delivered layout** (checklist, *Folder structure*) — one zip per task, whose
single top-level member is `<task-slug>/`:

```
<task-slug>/
├── <task-slug>/            ONLY these 5: instruction.md, task.toml,
│                           environment/, solution/, tests/
├── rubric.txt              sibling of the task folder — NOT inside it
├── oracle-nop-evidence/    oracle-1..3, nop-1..2
│                           (each: ctrf.json, reward.txt, test-stdout.txt)
└── trajectories/           run-01..run-05 (agent/, verifier/, config.json,
                            result.json, rubric_score.txt) + SUMMARY.txt
```

- [ ] T1 [M] Master #96 · **Delivery layout** (`T3-LAYOUT`). Four siblings at the top level and
      nothing else; the inner folder holds exactly the five members above and is
      named after the actual task — never `task/`, never `bundle/`. `rubric.txt`,
      `oracle-nop-evidence/` and `trajectories/` are package members, never
      "vendor", never extraneous — their absence is the finding. A flat bundle
      (task.toml at the top level) is the *authoring* shape, not a delivery.
- [ ] T2 [M] Master #96 · **Banned anywhere in the zip** (`T3-BANNED`): `SOURCE.txt`,
      `.DS_Store`, `__MACOSX`, `._*`, `.git`, `__pycache__`, `*.pyc`, plus the
      rejected member `rubrics.txt` (plural). A `README.md` in the task is its own
      finding (T30, `T3-README`).
- [ ] T3 [M] Master #11, #88, #97 · **Canary strings are rejected** (`T3-CANARY`,
      and `T3-PII` for the evidence directories). Their *presence* is the finding,
      and so is a GUID-shaped string in `instruction.md`. Never report a missing
      canary, never recommend adding one, never recommend a GUID.
- [ ] T4 [M] Master #66–#69 · **`rubric.txt` is well formed** (`T3-RUBRIC`, #67) — criterion lines only:
      every line starts with the literal word `Agent` and flows into `, +N` /
      `, -N`; at least one negative criterion; cumulative positive score in 10–40;
      every score drawn from ±1, ±2, ±3, ±5; an explicit `+` on every positive; no
      `#` headers, titles, comments, blank lines or `[tests: …]` citations; no
      criterion referencing tests, the instruction file, metadata or the oracle
      (the agent never sees them). **Confirm the file actually has content** — a
      rubric checked only against the tests can be empty and still "consistent".
      By reading: every line maps to a real (explicit or implicit) instruction
      requirement (#66), no two lines contradict (#68), nothing is double-counted
      and no positive is re-checked as a negative (#69).
- [ ] T5 [M] Master #90, #93, #96 · **The packaged round** (`T3-TRAJ`): `trajectories/` holds exactly
      `run-01`..`run-05` and `SUMMARY.txt` — nothing else; the controls live in
      `oracle-nop-evidence/`. Every run ships `agent/`, `verifier/`,
      `config.json`, `result.json` and `rubric_score.txt`. Failures are packaged
      too; no truncated tool output, full API/message log.
- [ ] T5a [M] Master #91 · **`reasoning_effort`** (`T3-EFFORT`): present and exactly
      `xhigh` in every `run-0N/config.json`, confirmed per run. Required, legitimate capture metadata — never
      renamed (e.g. to `effort`), never downgraded (e.g. to `high`), for any reason.
- [ ] T5b [M] Master #77, #79 · **`trajectories/SUMMARY.txt`** (`T3-SUMMARY`) —
      required, exactly two lines, zero explanatory notes:
      `<task-slug> sha=<hash> model=gpt-5.6 (reasoning_effort=xhigh)` and
      `5 runs, rewards: [r1, r2, r3, r4, r5]`. The rewards match each run's own
      `verifier/reward.txt` AND `ctrf.json`, run for run, in order — both are
      diffed by the screen.
- [ ] T5c [M] Master #70, #78, #85, #86 · **`run-0N/rubric_score.txt`**
      (`T3-RUBRIC-SCORE`, `T3-RUBRIC-SCORE-DUP`) — one per run, a
      DATA file: `reward=`, `tests_passed=<N>/<M>`, one verdict line per
      `rubric.txt` criterion quoted verbatim (`MET`/`NOT MET` for positives,
      `TRIGGERED`/`NOT TRIGGERED` for negatives) with its evidence inline in
      parentheses on that same line, then `gradient: X/Y positive met, X/Y negative
      triggered` — recomputed from the verdicts. No prose, no `note:`, nothing else.
      EVERY verdict carries a parenthetical citation (#86, mechanical presence
      check; that the citation comes from THAT run is read); the five files are
      pairwise distinct — not byte-identical, not the same body under a swapped
      header, not the same citations (#85). Verify the arithmetic by hand (#70).
      **A failing test is not evidence a negative criterion was TRIGGERED.**
      A method-worded line is scored on whether that run did the method; a later
      test failure does not by itself make it NOT MET. An outcome-worded line is
      scored on that outcome. A quoted number may be a faithful rounding of the
      value at that step (#86). The rubric orders the five runs the same way the
      reward does; N/A when all five rewards match (#70(b)).
- [ ] T5d [M] Master #80 · **Bundle sha** (`T3-BUNDLE-SHA`). The layout binds a
      round to a revision in one place: `SUMMARY.txt`'s `sha=`, the bundle sha a
      reviewer recomputes from inside the inner task folder —
      `cd <slug>/<slug> && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum`.
      The screen recomputes it (`bundle_sha` in its output); a mismatch or a
      missing `sha=` is [M]. A match is not proof of freshness — see T24.
- [ ] T6 [M] Master #61 · **Authorship is optional** (`TOML-04`, `T3-AUTHOR`):
      `author_name`, `author_email` and `author_organization` may be absent; when
      present each is a non-empty string. The old `"anonymous"` rule is gone —
      never ask for it, and never ask for `author_github`.
- [ ] T7 [M] Master #61 · **Name** (checklist line 1, `T3-NAME` / `T3-ROUND-NAME`,
      `SLUG-01` / `SLUG-TOKENS`): top-level
      `name = "<directory-slug>"`; no `[task]` table, no `terminal-bench-science/<slug>`
      namespace; the slug is lowercase kebab-case (2–4 hyphen tokens typical; length is
      not itself a finding, Master #61). No version suffixes, no internal
      codenames and specifically **no `hardened`/`harden`-style suffix** in the
      slug, either folder name, `task.toml`'s name, `instruction.md` or
      `environment/`. The harness bakes the round path into every shipped
      `run-0N/config.json` and `result.json`, so an internal round name leaks there
      too — the screen greps the shipped trajectory JSON for it.
- [ ] T8 [M] Master #61, #65 · **No stale-schema residue** (`T3-SCHEMA`, `T3-RESIDUE`,
      `T3-LOCALPATH`, `T3-MULTI`): `schema_version` is **optional** — present or
      absent is not a finding (upstream `task-template.toml` carries one) — but a
      top-level `version` key is (`T3-SCHEMA`). Also none of: a `[task]` /
      `[[task.authors]]` table duplicating `name`, a milestone / steps field,
      `codebase_size`, a minute-based estimate (`*_min`), `[reference_pattern]` or
      other generator bookkeeping, the retired TB4 `[metadata]` keys `category`,
      `subcategory` and `languages` (`T3-RESIDUE`), a real local machine path, or
      an `is_multi_container` that is present but not `true` (a single-container
      task omits it). `[environment]` declares `cpus`, `memory_mb`, `storage_mb`
      (`TOML-12`) and `gpus = 0` (`T3-GPU` for a non-zero value; no `gpu_types`).
- [ ] T9 [M] Master #64 · **Network policy declared on both phases** (`T3-NET`;
      upstream `check-allow-internet.sh`): the agent phase
      `[environment].network_mode = "public"` — always, with no `"no-network"`
      exception (a task whose answer is reachable online is a design defect under
      Master #99, never a reason to cut the network); the verifier phase
      `[verifier.environment].network_mode = "no-network"`, or `"allowlist"` with a
      non-empty `allowed_hosts` justified in the workspace resource plan (the
      screen raises a LEAD asking for the record). An undeclared policy (Harbor
      defaults it to public, silently opening the verifier), the deprecated
      `allow_internet`, or an `[agent].network_mode` key is [M].
- [ ] T10 [M] Master #63 · **Timeouts** (`T3-TIMEOUT`): `[agent].timeout_sec`,
      `[verifier].timeout_sec` and `[environment].build_timeout_sec` are all
      exactly **28800** on every task, deliberately, from creation — [M] on an
      authoring tree too; there is no 1800–28800 band. A shipped failure must be a
      real, knowable rule violation, never the clock running out.
- [ ] T10a [M] Master #62 · **No difficulty field, tier label or pass-count**
      (`T3-DIFFICULTY`): no `difficulty` key anywhere in `task.toml`, and no tier
      label, percentage or pass-count anywhere in the task. This
      REVERSES the old "`[metadata].difficulty` read off the measured k=5 rate"
      rule. The rate is still measured and reported
      (`trial_evidence.py` → `measured_pass_rate`, and SUMMARY.txt's reward array);
      it is never looked for in, or compared against, the task.
- [ ] T10b [M] Master #104 · **Instruction suffix** (`INSTR-01`; upstream
      `check-instruction-suffix.sh`): `instruction.md` ends with a blank line,
      then exactly `You have 28800 seconds to complete this task. Do not cheat by
      using online solutions or hints specific to this task.` (N =
      `[agent].timeout_sec`) and a single newline. Required, and exempt from the
      Master #5 framing rule — never a concision or hint finding. Applies under
      both profiles (B5).
- [ ] T11 [M] workspace policy (supports Master #53) · **Per-test identity** (`T3-TESTID`): `TBENCH_TEST_ID` or
      `tests/test_manifest.json` — strictly required, so CTRF rows bind to
      criteria across runs. The manifest's two fields are **not** interchangeable:
      `id` is the stable selector passed in `TBENCH_TEST_ID` (unique, non-empty,
      honoured by `tests/test.sh`), and the entry's **`cases`** array carries the
      `test_file.py::test_function` node ids. It is `cases`, never `id`, that must
      correspond one-for-one with the shipped `def test_*` functions.
- [ ] T12 [M] Master #53, #72, #73 · **Valid per-test CTRF output** — named rows, unique ids, a summary
      consistent with the rows. `pytest-json-ctrf` is permitted. No
      upstream-specific pytest or CTRF package version is required.
- [ ] T13 [M] Master #26 · **Images**: every Docker `FROM` and every Compose `image:` is
      digest-pinned. The final agent base is canonical or carries a credible
      justification — **when a credible justification exists, there is no
      `T3-BASE` finding**; say why it is credible and move on.
- [ ] T14 [M] Master #23, #26 · **`environment/` size**: 100 MiB total, 50 MiB per file. Compiled
      binaries and archives do not belong in the package — carry install
      commands in the Dockerfile instead (apt-get, a pinned `pip install ==`, a
      pinned release download with a checksum).
- [ ] T15 [M] Master #26 · **`tmux` + `asciinema` in the final AGENT image only** — never
      required of the verifier image.
- [ ] T16 [M] Master #54–#56 · **The verifier seal** (`T3-SETPRIV` / `T3-SANDBOX` /
      `T3-SEAL` / `T3-SYMLINK` / `T3-REWARD-LAST`), judged against the master's
      Appendix A: agent programs run under `setpriv --reuid=12000 --regid=12000
      --clear-groups --no-new-privs env -i … timeout -k 5 <PER_RUN_LIMIT>` (#54b),
      with thread-count variables sized to `[environment].cpus` (#106(a));
      `tests/Dockerfile` makes `/tests` root-only (`chmod -R go-rwx /tests`) and
      `/work` root-owned 755 (#54a/#54c); `test.sh` deletes, before grading, every
      artifact symlink whose resolved target escapes the artifact paths, keeping
      in-tree links (#55) and, after grading, kill-to-exhaustion (`pkill -9 -u 12000`
      until `pgrep -u 12000` is empty) and `rm -f /logs/verifier/reward.txt` before
      the final reward write (#56; an early `echo 0` placeholder is fine). The uid may be written as
      a literal or built from a module-level constant (`f"--reuid={AGENT_UID}"`) —
      resolve the constant before judging; an unresolvable name is a [L], not the
      assertion that the drop is missing.
- [ ] T17 [B] Master #57 · **Reward integrity**: wall-clock latency, throughput, speedup and
      runtime thresholds must not affect the reward. Reject them; calibration
      does not rescue them, because the hardware a trial lands on is not the
      hardware anyone calibrated. Grade the property the speed stood in for, or
      report timing as a non-graded diagnostic.
- [ ] T18 [B] Master #40, #71–#74 · **Runtime gate** (`T3-CONTROLS`,
      `T3-NOP-ERROR`): `oracle-nop-evidence/` ships exactly **oracle × 3** (every
      run reward 1.0 with every ctrf row `passed`, #72) and **NOP × 2** (every run
      reward 0.0 with every ctrf row EXPLICITLY `failed` — not `error`/`skipped`,
      #73) — NOP × 1 was the previous edition. Each control directory holds exactly
      `ctrf.json`, `reward.txt` and `test-stdout.txt` (#71). Every NOP failure in
      `test-stdout.txt` is an assertion mismatch, not a collection / setup /
      import error or a session-scoped autouse fixture asserting first (#74 — the
      screen flags `ERROR` rows; read the rest). There is no fixed NC-01–NC-14
      negative-control matrix to satisfy.
- [ ] T19 [L] **Negative controls**: review one if supplied (it must score 0).
      **Absence is not a submission finding.** Establish anti-cheat directly
      instead — isolation (T16), hidden-test protection (root-only `/tests`),
      independent recomputation (E2/E14), reward-channel integrity (D6/D7).
- [ ] T20 [L] **Review leads, not automatic findings**: test-suite length,
      missing test docstrings, ordinary bold text, and phrases such as "Your
      goal is…". Raise them as questions; never count them in the verdict.
- [ ] T21 [M] Master #20, #24 · **No solution leakage into `environment/`** (checklist). If
      `solution/` is a `solve.sh`-style patch script, do **not** diff directory
      trees — that produces false positives. Check instead: (a) `environment/`'s
      Dockerfile never `COPY`s or bakes in `solution/`, (b) `instruction.md` and
      `environment/` never reference `solve.sh` or a `solution/` path, and (c) the
      NOP evidence reliably scores 0.0. Master #20 additionally asks for a byte
      diff of every same-named file between `environment/` and `tests/` /
      `solution/` (`DRIFT-01` is a lead for tests/; diff solution/ by hand) — a
      byte-identical private copy is a leaked oracle.
- [ ] T22 [M] Master #13, #16, #95 · **No manufactured difficulty, no senseless
      paths, no telltale comments** (`T3-HINT-COMMENT`, `T3-OPAQUE-NAME`): every
      graded rule traces to a sentence in `instruction.md` or a doc it points to;
      no `ak`/`bks`/`wqt`/`k7`/`qp7`-style names; the literal grep of
      `environment/` and `solution/` for `TODO`, `FIXME`, `BUG:`, `planted`,
      `deliberate`, `for the grader`, `for the test` has zero hits or a written
      justification per hit.
- [ ] T23 [M] Master #76, #83 · **Independent executions** (`T3-DUPLICATE`):
      oracle-1..3, nop-1..2 and run-01..05 are each their own execution — no
      identical `trajectory.json`, no identical ctrf start timestamps, no identical
      embedded object addresses. Identical grader output alone (`ctrf.json` /
      `test-stdout.txt` of a deterministic failure without a per-run field) is not
      duplication. By reading
      (#83): a floating-point result that should be solver-sensitive must not
      agree to 15–16 significant figures across the five runs.
- [ ] T24 [M] Master #75 · **Evidence freshness** (`T3-MTIME`): the newest
      mtime under `tests/`, `environment/`, `solution/` and `instruction.md` is
      older than every `oracle-nop-evidence/*/ctrf.json` and every run's
      `verifier/ctrf.json` (the screen restores zip mtimes before comparing). A
      matching sha does not excuse a newer graded file.
- [ ] T25 [M] Master #53 · **Test counts** (`T3-TESTCOUNT`): every control's and
      every run's `ctrf.json` reports exactly the test functions collected from
      the shipped `tests/` tree.
- [ ] T26 [M] Master #87, #88, #97 · **PII / `stb` / canary scrub** (`T3-PII`): each
      of the ten run/job directories is grepped on its own — never one aggregate
      recursive grep — for `/Users/`, `/private/tmp/`, `/home/<host user>` (in-
      container homes such as `/home/agent` excepted), a case-sensitive
      word-boundary `stb`, and canary markers; then the inner task folder,
      `rubric.txt` and `SUMMARY.txt` (#97). GUID-shaped strings in the evidence
      are read by hand (#88: a canary in a trajectory that the current
      `environment/` no longer carries means the environment changed after capture).
- [ ] T27 [M] Master #89, #90, #92 · **Capture integrity** (`T3-AGENT-FILES`,
      `T3-EXCEPTION`): every `agent/` carries the same canonical set
      (`api-calls.jsonl`, `recording.cast`, `trajectory.json`, a `*.pane`); every
      `verifier/` carries `ctrf.json`, `reward.txt`, `test-stdout.txt` with
      `reward.txt` agreeing with the ctrf outcome; no `result.json` has a
      populated `exception_info`. By reading: `result.json`'s nested model-name
      fields are raw, never hand-normalised (#89).
- [ ] T28 [M] Master #93 · **Reward-hack scan** (`T3-REWARD-HACK`, `T3-TRAJ`
      truncation): no issued command in any `trajectory.json` reads or writes
      `/tests`, `test_outputs.py`, `ctrf.json`, `reward.txt`, `/logs/verifier` or
      `/solution`; no truncation markers. By reading: no hand-written output
      artifact bypasses running the fixed code, and each run ends in a genuine
      completion step.
- [ ] T29 [M] Master #94 · **The shipped five and the set that moves with them**
      (`T3-RUN-ORDER` + read): the five runs are the first five fidelity-complete
      trials at the current digest and run config, in launch order across capture
      rounds, with no valid attempt skipped. Checkable from the shipped files:
      run-01..run-05 carry distinct `result.json` `id`s, strictly increasing
      `started_at`, one `task_checksum` and one agent configuration (`T3-RUN-ORDER`).
      Runs from more than one capture round are **not** a finding (a round cut short
      by an stb quota or an infrastructure abort is completed from the next round at
      the same digest; the author's `composition.json` stays in the workspace and does
      not ship). Runs out of launch order, at two configurations, or a best-of choice
      are. After any rerun: SUMMARY.txt sha + rewards, all five `rubric_score.txt`,
      the expert time estimate (if it materially changed), the bundle sha and a fresh
      PII grep moved with the five. T5b, T5d, T24 and T26 catch most partial moves
      mechanically.
- [ ] T30 [M] Master #103 · **No README.md** (`T3-README`; upstream
      `task-readme-template.md` / `check-task-readme.sh` NOT adopted): neither the
      inner task folder nor the package root carries a README.md, and no other
      write-up file ships; no `difficulty_explanation` / `solution_explanation` /
      `verification_explanation` key left in `task.toml` (`T3-WRITEUP`). The three
      write-ups (`## Difficulty`, `## Reference solution`, `## Verification`) live
      only in the workspace as `authoring/<task>/write-ups.md` (sections and the
      no-rate rule enforced by the workspace's `task_check.py`); it never ships, is
      never given to the agent, and touches no task file, so editing it needs no
      re-seal. Its quality is gate G, judged on the supplied workspace evidence.

---

## A · Bundle, name & manifest

- [ ] A1 [M] Master #96 · Required members present — see T1 under `terminus` (the four delivery
      siblings: the inner `<task-slug>/`, `rubric.txt`, `oracle-nop-evidence/`
      and `trajectories/`, the inner folder carrying no `README.md`) and, under
      `upstream`, `task.toml`, `instruction.md`, `README.md`, `environment/Dockerfile` (or
      `docker-compose.yaml`), `solution/solve.sh`, `tests/Dockerfile`,
      `tests/test.sh`. `LICENSE*` is always allowed; `cheat/` (a negative
      control) is a recognised extra. Nothing else unreferenced
      (`no_extraneous_files`): no `jobs/`, notes, backups, `.DS_Store`, or
      `rubrics.txt` (plural — not a member under either profile).
- [ ] A2 [M] Master #61 · Folder name: lowercase kebab-case, descriptive of the core
      challenge, not generic or misleading (`task_name`). Name must not state the
      diagnosis the instruction withholds (F-084). 2–4 hyphen-separated tokens
      typical; extra tokens alone are a lead, not a finding (`SLUG-TOKENS`, Master #61).
- [ ] A3 [M] Master #37, #61 · `task.toml` parses; the package name matches the profile ([t]
      top-level `name = "<directory-slug>"` per T7; [up] `[task] name =
      "terminal-bench-science/<folder>"`, `TOML-01`, upstream `check-task-fields.sh`); `artifacts` is
      TOP-LEVEL (nested under `[verifier]`, or written after the first
      `[section]`, it is silently dropped) and non-empty; entries are absolute
      path strings or tables `{source, destination?, exclude?, service?}`.
- [ ] A4 [M] Master #61, #98 · `[metadata]` taxonomy and fields (`TOML-04`,
      `TOML-05`, `TOML-06`, `TOML-07`, `T3-TAGS`; upstream `check-task-fields.sh`,
      rubric `scope`, `category_and_tags`, `expert_time_estimate`): `domain` and
      `field` are exact kebab-case values from `reference/TAXONOMY.md` with the
      field listed under its domain; `subfield` is non-empty free text naming the
      research specialty; `tags` 3–6 and specific (not "hard", "coding");
      `expert_time_estimate_hours` > 0 and plausible for a focused domain expert;
      `relevant_experience` substantive. **By reading** (Master #98): classify by
      the scientific expertise INDISPENSABLE to solve the task — with the tool
      names removed, would a reviewer in that field call this their work? An
      in-scope method (statistics, optimisation, ML, simulation) applied to an
      out-of-scope subject is out of scope, and so is generic software or data
      munging dressed in scientific vocabulary. The retired TB4 `category` /
      `subcategory` / `languages` keys are findings (T8).
- [ ] A5 [M][up] Master #65 · **No invented fields** (`task_toml_schema`, `TOML-08`).
      Valid: `[metadata]` author_name, author_email, author_organization, the
      three `*_explanation` write-ups (upstream only — under `terminus` they are
      `T3-WRITEUP`), domain, field, subfield, tags, expert_time_estimate_hours,
      relevant_experience, referral, name, description; `[verifier]` timeout_sec,
      env, user, environment_mode, environment, collect; `[agent]` timeout_sec,
      user; `[environment]` build_timeout_sec, docker_image, cpus, memory_mb,
      storage_mb, gpus, gpu_types, allow_internet, env, skills_dir, mcp_servers,
      healthcheck, docker_flags, network_mode; root schema_version, task,
      metadata, verifier, agent, environment, solution, source, artifacts,
      referral, name. Residue from earlier editions is `TOML-T3-RESIDUE` upstream:
      `difficulty`, `languages`, `category`, `subcategory`, `is_multi_container`,
      `expert_time_estimate_min`, `junior_time_estimate_min`, `codebase_size`,
      `number_of_milestones`, `version`. Under `terminus` the residue rule is T8
      (`is_multi_container = true` is valid there) and `difficulty` is banned
      under both profiles (T10a, Master #62).
- [ ] A6 [M] Master #63 · `[verifier].environment_mode = "separate"`; timeouts ≤ 28800
      (`check-task-timeout`). **[t]** agent, verifier and build timeouts are all
      exactly 28800 on every task — there is no band (T10). **[up]** 28800 is the
      published budget and hard cap (upstream `check-task-timeout.sh`), so a
      materially lower value earns `TOML-11-NORM` / a `low_timeout` flag (I7).
      Under both profiles the agent timeout is a positive integer, because the
      instruction suffix names it (B5). Verifier timeout covers the suite with
      headroom (Terminal-Bench 4.0's uefi-bootkit was fixed for exactly this).
- [ ] A7 [M] Master #65 · `[environment]`: `cpus`, `memory_mb`, `storage_mb`, `build_timeout_sec`
      declared and sized to what the task needs — template defaults left
      unchanged are a tell (`TOML-12`, rubric `resource_configuration`). **[t]**
      `gpus = 0` and no `gpu_types` (`T3-GPU`). **[up]** `gpus ≤ 1`; `gpu_types` ⊆
      {T4, L4, A10, L40S, A100-40GB, A100-80GB, H100, H200, B200, any}
      (`TOML-13`, `check-gpu-types.sh`). Difficulty must come from reasoning, not
      from making the computer work harder.
- [ ] A8 [M] Master #64 · **Network.** **[t]** declared on both phases — agent
      `public`, verifier `no-network` or a justified allowlist (T9, `T3-NET`).
      **[up]** open internet is mandatory for the agent: `allow_internet` in
      either polarity, or an agent-phase `network_mode = "no-network"`, is
      `TOML-14` (upstream `check-allow-internet.sh`). Under either profile,
      disabling the agent's network is not a difficulty mechanism.
- [ ] A9 Master #11, #88 · **Canary.** **[t]** REJECTED — see T3; presence is the finding and a
      missing canary is never reported. **[up]** [M] required (`CANARY-01`,
      upstream `check-canary.sh`): the exact upstream canary string (the screen's
      `CANARY_STR`; never copy it into workspace files) inside a comment in
      `instruction.md` (`<!-- … -->`), `task.toml`,
      `environment/Dockerfile`, and every text file under `solution/` and
      `tests/`. A bare (uncommented) canary also fails there.

## B · instruction.md (and everything the agent can read)

- [ ] B1 [B] Master #1, #2, #6, #47, #9 · **Well specified.** The goal is clear and success is decidable; every
      graded behaviour is licensed by something the agent can read — a sentence in
      `instruction.md`, a spec/schema/config in `environment/` the instruction
      points at, or an unambiguous domain convention. Walk every assertion to its
      licence: output path, field names, types, ordering, rounding, tie-break,
      exit codes, error/refusal path. No licence, no assertion. This is the
      `task_specification` trial flag and the `test_instruction_alignment`
      criterion, and it is the fix family behind 6 of the 19 revisions in
      Terminal-Bench 4.0.
      A task hard mainly because of a pile of corner cases is rejected here
      (proposal rubric: "reject tasks that are primarily hard because of how many
      corner cases must be handled").
- [ ] B2 [B] Master #3, #4, #10 · **No hints, no recipe** (`instruction_concision`, `outcome_verified`).
      What to achieve, not how: no step lists, "look for", detection guidance,
      solution values, exact function signatures, tool mandates ("use emacs"), or
      lists of available tools/libraries the agent should discover itself.
      Exception: endpoints / task-scoped credentials that are structurally
      undiscoverable.
- [ ] B3 [B] Master #12 · **All requirements live in `instruction.md`.** Spec/doc files in
      `environment/` may define contracts, schemas and protocols (WHAT), never
      step-by-step guides (HOW), and are not used to move the task's goals out of
      the instruction. Terminal-Bench 4.0 moved two tasks' specs *into* the
      instruction. No
      README how-to, commented walkthrough, TODO naming the fix, or config example
      that reveals the answer.
- [ ] B4 [M] Master #0 · **Absolute paths** for every referenced path (`check-task-absolute-path`).
      Backticks for paths, commands and code; `$…$` / `$$…$$` for math.
- [ ] B5 [M] Master #104 · **Instruction suffix** — required under BOTH profiles
      (`INSTR-01`, upstream `check-instruction-suffix.sh`; T10b): the file ends
      with a blank line, then exactly `You have N seconds to complete this task.
      Do not cheat by using online solutions or hints specific to this task.` with
      N == integer `[agent].timeout_sec` (28800 under `terminus`), then a single
      newline. Nothing after it.
- [ ] B6 [B] Master #95, #99 · **Novel and not online-solvable** (`novel`,
      `scientifically_grounded`; Terminal-Bench 4.0 removals gpt2-codegolf,
      lean-midpoint-proof). Not a textbook exercise, a well-known algorithm, or a
      problem whose solution is easily findable — the agent has the internet. A
      few prior solutions online are tolerated when the agent still has to do the
      work; an obvious lookup, or a memorised well-known published result, is not. A recognisable re-skin of another task you
      were shown is [B].
- [ ] B7 [M] Master #0 · **Concise** (`instruction_concision`; three
      Terminal-Bench 4.0 fixes removed Markdown headings). No unnecessary headings, preamble, roleplay
      ("You are an expert…"), fluff, restated requirements, explanation of
      expert-prerequisite knowledge. Length itself is not the finding — a long instruction
      is fine when the *problem* needs it (freight-dispatch-shift); length from
      steps or repetition is the finding. Authorship: instruction.md may be drafted
      by an AI assistant; human-only authorship is not required (Master preamble).
- [ ] B8 [M] Master #7, #47 · Every file the tests read or write is named to the agent
      (`check-test-file-references`, `file_reference_mentioned`). Structured output
      (JSON/CSV/DB/config) has a **normative** schema, not just an example
      (`structured_data_schema`).
- [ ] B9 [B] Master #5 · No exploitable verifier internals leaked to the agent: `/tests/…`
      subpaths, held-out fixture names/locations, `/logs/verifier`, `reward.txt`,
      expected values, the cheat oracle. Not a leak: "the verifier re-runs your
      program on held-out inputs", "hand-written output will not pass".
- [ ] B10 [B] Master #1, #41 · **"Do not modify / preserve X" constraints are enforced**
      (`do_not_modify_enforced`). For every phrase naming a concrete artifact
      ("do not modify", "leave unchanged", "read-only", "must remain",
      "preserve", "do not remove"): the verifier fails a violator — checksum
      against a pristine copy, functional dependence, or verifier-side isolation
      that makes the tampered copy irrelevant. A type-only / subset check does not
      count. Watch the classic gap: the verifier recomputes the expectation FROM
      the protected input the agent can edit.
- [ ] B11 [m] Master #9, #12 · Task name does not appear verbatim in the instruction; no
      contradiction between any two agent-visible documents on a graded value
      (a graded contradiction is [B], F-003); no bare magic numbers without an
      in-world anchor.

## C · environment/ (the agent image)

- [ ] C1 [B] Master #19, #20, #24 · `tests/` and `solution/` are never copied into the agent image
      (`check-dockerfile-references`); no ground truth, expected outputs, cheat
      oracle, or answer key ships in `environment/`, in image layers, or in git
      history the agent can reach (pin clones to a commit) (`anti_cheat_robustness`).
      Test-only deps (pytest, ctrf, scoring libs) do not belong in the agent image
      (`environment_hygiene`). Confirm the build context: a file at bundle root is
      invisible to the agent; the same file under `environment/` is [B].
- [ ] C2 [B] Master #26, #36, #106 · **Architecture-portable** (`ENV-02`, `ENV-16`;
      `check-dockerfile-platform.sh`; Terminal-Bench 4.0 removals
      memcached-backdoor, fix-uautomizer-soundness). No `FROM --platform=`; no
      x86-only prebuilt downloaded without a `uname -m` / `TARGETARCH` branch; no
      amd64-only vendored blobs. If a dependency genuinely has no arm64 build,
      it is recorded in the workspace resource plan, not silently pinned.
- [ ] C3 [M] Master #26 · `:latest` or otherwise floating tags on `FROM` / compose `image:` are
      a reproducibility defect (`deterministic_reproducible`). **[t]** every
      `FROM` and every compose `image:` must be digest-pinned, and the final agent
      base must be canonical or credibly justified (T13). **[up]** digest pins are
      good practice, not an upstream CI requirement — do not block on their absence.
- [ ] C4 [M] Master #26, #106 · Apt: never version-pinned (`ENV-10`,
      `check-dockerfile-sanity.sh`); `apt-get update` before install and
      `rm -rf /var/lib/apt/lists/*` after (`ENV-11` — an upstream warning, a
      finding here because no finding ships). pip / `uv pip` / `uvx --with` /
      `uv tool install` always `==`-pinned, numpy / scipy / pandas and domain
      libraries included (`ENV-09`, `check-pip-pinning.sh`; `-r manifest`,
      `-e .`, VCS `@ref` are exempt).
- [ ] C5 [M] Master #26 · Everything mutable is pinned: `git clone` to a commit, downloaded
      binaries by version (+ checksum ideally), external assets by revision
      (layout-config-recreation2 pinned Google Fonts in Terminal-Bench 4.0).
      Scientific data fetched at build time is pinned to an immutable revision
      written as a literal and checksum-verified (Master #100). No task-relevant
      dependence on live services whose content can change; standard package
      repositories count as stable infrastructure.
- [ ] C6 [M] Master #23, #26 · Package size. **[t]** `environment/` is capped at 100 MiB total and
      50 MiB per file, and compiled binaries/archives do not ship at all — carry
      install commands in the Dockerfile instead (T14). **[up]** files > 100 MB
      are not committed. Data goes in `environment/data/`.
- [ ] C7 [B] Master #24, #26 · No `--privileged`, `SYS_ADMIN` / `NET_ADMIN` / `SYS_MODULE`, docker
      socket, host bind mounts in `environment/docker-compose*.y*ml`
      (`ENV-15`, `ENV-18`; `check-compose-host-binds.sh`, Master #106; three
      Terminal-Bench 4.0 fixes removed compose volumes) —
      named volumes only. Dockerfile does not create / chown `/tests`, `/solution`,
      `/oracle`, `/logs`.
- [ ] C8 [B] (no master check) · **Security** (`task_security`, applies to every file in the bundle):
      no credential reads + exfil, no outbound calls not justified by the task, no
      `curl | sh` from untrusted URLs, no obfuscated code (base64/hex payloads,
      `eval` of built strings, invisible Unicode), no prompt injection in
      environment files, no destructive ops, no background processes that outlive
      the task.
- [ ] C9 [M] Master #106 · Bare `nproc` in Dockerfile / `test.sh` / `solve.sh` (`ENV-13`,
      `check-nproc.sh`) — reports the host CPU count; size parallelism to
      `[environment].cpus` (`nproc --all` / `--help` are fine). A stochastic task
      fixes its seeds.
- [ ] C10 [m] Master #12, #96 · Hygiene: no AI-framework scaffolding files (`CLAUDE.md`, `AGENTS.md`,
      `skills.md`, `.cursor/`) unless they are the task's subject; no `.git`,
      `.env`, caches, editor droppings in the image; source as files not
      heredocs where practical; `.dockerignore` present for non-trivial contexts.
      Multi-stage builds keep toolchains out of the runtime image unless the agent
      must compile. **[t]** `tmux` + `asciinema` are required in the final AGENT
      image only, never in the verifier image (T15).
- [ ] C11 [m] (no master check) · If the Dockerfile uses heredoc `RUN <<EOF` syntax, declare
      `# syntax=docker/dockerfile:1.6` (`ENV-04`; Terminal-Bench 4.0's
      vpp-loss-divergence fix). **[up]** tmux / asciinema are not required
      upstream (calibration fact: 4/66 Terminal-Bench 4.0 tasks install them).
- [ ] C12 [M] Master #12, #14, #15, #16, #17, #25 · The environment is navigable and honest: no gibberish module trees,
      no decoy files planted to waste time, no comments that lie about the code,
      no self-reverting mechanisms unless that is the documented subject
      (F-018/019/021). Fixtures realistic for the domain; a repair task is one
      coherent incident, not a bug zoo (F-020).
- [ ] C13 [M] Master #36 · No hidden dependence on locale, timezone, umask, hostname, wall-clock
      date; the oracle passes inside the declared resource limits.

## D · Verifier wiring (separate container)

- [ ] D1 [B] Master #37 · **Inputs are sufficient** (`separate_verifier_configured`,
      `check-separate-verifier`). Every path the verifier reads from the agent's
      world is (a) a declared artifact, (b) baked into the verifier image by
      `tests/Dockerfile`, or (c) on a persistent sidecar. The agent container is
      torn down before the verifier starts — an undeclared read arrives EMPTY and
      every agent fails, correct or not.
- [ ] D2 [M] Master #37 · `tests/Dockerfile` `COPY`s (or `ADD`s) the tests into `/tests`
      (separate mode uploads nothing); pre-creates the parent directory of every
      declared artifact with `RUN mkdir -p` (for tables, the `destination` if set,
      else `source`); every `COPY` source resolves inside the `tests/` build
      context (the image must build).
- [ ] D3 [M] Master #38 · **Verifier tooling baked** (`check-verifier-tooling-baked`) in
      `tests/Dockerfile`; never installed in `test.sh` (Master #38). **[up] only**
      for the canonical pins (`VER-02`: upstream TB-Science's
      `check-pytest-version.sh` values `pytest==8.4.1` + `pytest-json-ctrf==0.3.5`)
      — `terminus` requires no specific version, only exact
      pins and valid per-test CTRF (T12). Runtime
      installers in `test.sh` are otherwise banned — the single exception is the
      agent's own pinned manifest (`pip install -r /app/requirements.txt`,
      `npm ci`), never an arbitrary `setup.sh`.
- [ ] D4 [M] Master #38 · **No trial-time network in `test.sh`** (`VER-05`,
      `check-trial-network-fetch.sh`; the verifier phase is also declared
      `no-network`, T9):
      no `curl|sh`, `wget|sh`, `bash <(curl …)`, raw `curl`/`wget` to external
      hosts, `git clone` of external URLs. localhost / 127.0.0.1 / bare sidecar
      hostnames are fine. (The RDI/Berkeley "shim /usr/bin/curl" attack is why.)
- [ ] D5 [M] Master #53 · **CTRF** (`ctrf_reporting`): a pytest-based verifier runs with
      `--ctrf /logs/verifier/ctrf.json` (root copies it from a temp path when
      pytest runs unprivileged). The report must be genuinely per-test: named
      rows, unique ids, a summary consistent with the rows. A bash gate of
      several discrete named checks should be pytest, not a chain of `if`s. N/A
      only for a genuinely single-score bespoke scorer. **[t]** per-test identity
      via `TBENCH_TEST_ID` or `tests/test_manifest.json` is strictly required
      (T11).
- [ ] D6 [B] Master #58 · **Binary reward** (`binary_reward`; kv-live-surgery fix). Every
      reachable path writes exactly 0 or 1 to `/logs/verifier/reward.txt`. The
      verifier writes no `reward.json`: Harbor prefers that file over `reward.txt`,
      so a `reward.json` decides the score (`VER-08`, BLOCKER). No pass/total
      ratios, weighted composites, clamped formulas, penalties, or rounded
      continuous scores. Internal scores are fine when thresholded before the write.
- [ ] D7 [M] Master #39 · Reward is written on the failure path too (a missing reward file is
      a `RewardFileNotFound` trial error, which is neither pass nor fail). The
      one legitimate no-reward path: a `[[verifier.collect]]` capture that is
      *missing* — an infrastructure failure that must not be laundered into a 0.
- [ ] D8 [M] Master #58 · **Identical logic for oracle and agent.** No branch on `/oracle`,
      `EVAL_IS_ORACLE`, agent name, or any execution-mode signal in `test.sh` or
      the tests.
- [ ] D9 [M] Master #39 · Verifier timeout and any internal boot/poll timeouts leave headroom
      on slow hardware (uefi-bootkit fix); env vars used in `test.sh` have
      defaults (`${TEST_DIR:-/tests}`).
- [ ] D10 [M] Master #37, #45 · **Artifacts are narrow** (`artifact_efficiency`). Only agent-produced
      deliverables and edits ship; build-time-fixed data is baked into the
      verifier image byte-identical to the agent copy (silent drift between the
      two copies is a correctness bug). Large edited trees use a
      `[[verifier.collect]]` git-diff patch against a pinned baseline, with the
      fail-safe rules: `rm -f` stale output first, temp-file then move, missing
      capture = hard error, `git diff --binary --no-color` with exclude pathspecs,
      exact apply → reset + `--3way` → loud 0, manifest change → reinstall deps
      loudly.

## E · Grading integrity — what the verifier actually measures

- [ ] E1 [B] Master #40, #41, #42 · **NOP per-test zero.** With no work done, every test fails — 0 of N,
      not "reward 0". Existence checks on shipped files, "config unchanged" and
      "input integrity" tests that pass on the untouched environment are vacuous
      (F-010/F-053). Read the NOP ctrf yourself; a missing NOP artifact is
      `no-evidence`, never a pass.
- [ ] E2 [B] Master #44, #45 · **Ground-truth provenance.** Trace every expected value to its origin.
      Sound: a constant or reference implementation sealed in the verifier image,
      a fixture `COPY`'d into `tests/`, a spec-derived invariant, a value
      recomputed by the verifier from sealed inputs. Unsound: anything derived
      from a path under `artifacts` — the agent owns those files. Re-running the
      agent's program on artifact *inputs* is the design; deriving the *expected*
      answer from artifact files is the defect. Never grade a number the agent
      printed (F-007). Terminal-Bench 4.0 added "independent checkpoint loss
      verification" to pretrain-shard-corruption for this reason. **Science
      (Master #100):** every dataset has a recorded origin (real: source,
      version/DOI, licence, preprocessing; synthetic: generator and parameters in
      the workspace `authoring/<task>/provenance/`), and the graded reference
      values come from an independent reference or are disclosed as
      oracle-derived and defended — the write-ups' `## Verification` (README.md
      [up]; `authoring/<task>/write-ups.md` [t]) says which
      ([up] `PROV-02` lead).
- [ ] E3 [B] Master #54 · **Execution isolation** (`verifier_execution_isolation`). When the
      verifier runs anything the agent produced — its binary/CLI, a rebuilt
      source tree, an imported module (pytest collection counts) — that code runs
      inside the verifier container, as root by default. Required: (1) privilege
      drop — **[t] `setpriv --reuid=12000 --regid=12000 --clear-groups
      --no-new-privs`**, [up] any drop (`--reuid nobody`, `subprocess(user=)`,
      `runuser -u`); a `useradd` that is never used is not a drop; (2)
      `/logs/verifier` root-owned and unwritable by the sandbox uid BEFORE agent
      code runs (Appendix: `chown root:root`, `chmod 755`), and **[t] a root-only
      `/tests` in `tests/Dockerfile`** (`chmod -R go-rwx /tests`, T16); (3) root
      derives the reward from baked grader logic over the child's exit status / captured
      output; (4) in-process imports are isolated (unprivileged pytest, fork
      workers, subprocess proxy); (5) output captured to files, process group
      killed after (`pkill -9 -u 12000`, then `rm -f` reward before the write, #56);
      (6) symlinks under artifact paths deleted before any root reader follows them
      (#55). Run the Appendix SELF-TEST in the built verifier image. Also seal `/tests` (chmod 700, or delete key material after
      loading) so executed agent code cannot read expected constants or the
      reference implementation. Root execution is [B] even when only hashes are
      stored — root can overwrite them and the reward. A negative control scoring
      0 is useful proof when one ships, but its absence is not a finding (T19).
      Reading/parsing agent files is not execution.
- [ ] E4 [B] Master #59, #60 · **Something must run.** Ask what the agent must actually EXECUTE for
      the suite to go green. If a hand-written JSON/CSV/text satisfies every
      assertion, the task grades a document. Acceptable only when the expected
      content is sealed in the verifier and byte-exact (a `render.py` comparison,
      a golden hash); otherwise the fix is a held-out re-run of the agent's
      program (gpt2-codegolf was removed for a verifier that accepted a hard-coded
      answer).
- [ ] E5 [M] Master #46 · **Held-out / perturbation coverage.** The verifier exercises at least
      one input the agent never saw, or a metamorphic variation, so a solution
      fitted to the visible case is distinguished from a general one
      ("test beyond single examples provided"). [B] when the gap lets a hardcoded
      answer pass.
- [ ] E6 [B] Master #52, #60 · **Cheat simulation** (`anti_cheat_robustness`; agents run as root in
      their own container). Hardcoded output? Forced success flags? One of several
      defects fixed? Graded component stubbed or deleted? Fake tool wrapper /
      monkey-patched library in the agent image that the verifier later imports?
      Artifact data the verifier derives expectations from edited? A shimmed
      `curl` the verifier would call? A daemon planted in an artifact that
      outlives the test run? Any yes on a graded path → [B] with the attack
      written out. Run the red-team prompt in your head (hack-trial-prompt.md).
- [ ] E7 [B] (no master check) · **Determinism** (`verifiable`, `deterministic_reproducible`). "Re-running
      the verifier hundreds of times should show no failures." No wall-clock reads
      a result depends on, no unseeded randomness in tests or oracle, no
      order-dependent or side-effect-coupled tests, no dependence on the oracle's
      random order, no live mutable services. A bounded readiness poll is fine.
      Seed deliberate randomised fixtures rather than delete them (F-050). For
      stochastic tasks the tolerance must be validated over many runs ("28 of
      1,000 failing is not acceptable").
- [ ] E8 Master #57 · **Wall-clock thresholds.** **[t] [B] REJECTED** when they affect the
      reward — latency, throughput, speedup, runtime. Calibration does not rescue
      them (T17). **[up] [M]** performance tasks were allowed in Terminal-Bench 4.0
      when the
      threshold is measured relative to a baseline in the same container,
      justified in README.md `## Verification`
      (`verification_explanation_quality`), validated against alternative correct
      approaches, and leaves headroom — a bar within ~5 % of the oracle turns the
      task into "imitate the oracle" and produces `near_miss` flags (I5). Under
      BOTH profiles, numeric tolerances need float64 references, justified
      epsilons, and clearance from the noise floor (F-014/F-015). **Science
      (Master #101, [up] `TOL-01` lead; rubric `essential_difficulty`, trial criterion
      `boundary_fairness`):** every tolerance, threshold or fuzzy match states what
      it brackets and what legitimate variation it absorbs, and is measured on at
      least one independent correct implementation that differs from `solution/`
      in a structural choice. Classify every named method as correct or defective;
      separation must be achieved on the shipped graded instances (10% margin rule);
      no fresh-draw study is required. Where instances come from a generator and a
      method's smallest shipped-set margin is under 20%, the default internal
      check is 3 fresh unselected draws (6 only if those 3 are borderline or inconsistent);
      not running it is never a finding. A bound tightened until only the reference
      clears it is manufactured difficulty (I8), and precision finer than the science
      supports is a finding.
- [ ] E9 [M] Master #43, #47, #59 · **Correctness, not format** (`functional_verification`). Tests execute
      the code / call its API / check outputs; they do not grep source for
      keywords, assert only types / lengths / key presence, or match brittle exact
      strings where the contract fixed no form (freight-dispatch-shift's reason
      matching was relaxed for this; satb ignores inaudible notation). If a
      literal form IS graded, the instruction must state it (F-013). Rankings on
      float scores need a tie-break or margin (F-072).
- [ ] E10 [B] Master #1, #2, #12 · **Alignment both ways** (`test_instruction_alignment`). Every
      instruction requirement (explicit, implicit, critical edge case, error
      path) has a test; every test asserts something the agent was told or could
      discover. Build the two-way table; orphans on either side are findings
      (ctr-optimization and vba-userform-port were fixed for coverage gaps).
      Dead-branch tell: `if status == "rejected":` in a test no fixture reaches.
- [ ] E11 [M] Master #43, #49, #50 · Tests are hand-written, readable, and test distinct behaviours —
      no clone padding, no name-keyed shims, and diagnostic failure output
      ("standardized verifier diagnostics" was a Terminal-Bench 4.0 fix). **Suite length and
      missing docstrings are [L] review leads, not findings** (T20): a long suite
      is a question about over-specification, not a defect in itself.
- [ ] E12 [B] Master #59 · No test requires code to REMAIN broken, grades agent process
      ("reads the docs"), or asserts a fabricated metric (F-008/F-012). No
      LLM-as-judge inside the verifier unless documented as unavoidable with
      evidence that multiple models always agree (`verifiable`).
- [ ] E13 [M] (no master check) · **Config-claimed values are read dynamically** — only when the
      instruction says the agent must honour a config that can vary; then the
      verifier reads the config at runtime so a hardcoding agent fails. Hardcoded
      expected *results*, goldens and format constants are fine; `reviewable`
      prefers they be derived by a script in `tests/` or `solution/` so a
      non-specialist can check them.
- [ ] E14 [M] Master #30, #33 · **Adversarial fixture recompute.** For the trickiest held-out cases,
      derive the expected verdict from the STATED rules alone — never from the
      oracle. Oracle and tests agreeing proves nothing when both encode the same
      misreading.
- [ ] E15 [B] Master #102 · **Graded instances discriminate** (rubric
      `graded_instances_discriminate`). Where several withheld instances are
      graded, run the trivial nulls that need no science — a constant, the mean or
      median of the allowed range, the centre of the domain, the majority class,
      identity / copy-through, the task's own negative control — against EACH
      instance separately. Every instance is one no null reaches, or the
      non-discriminating instance is named in the write-ups' `## Verification`
      (README.md [up]; `authoring/<task>/write-ups.md` [t]). [B]
      when a null scores reward 1.

## F · solution/ (oracle)

- [ ] F1 [B] Master #28, #30 · Solves what `instruction.md` asks — every requirement, not only the
      tested ones — through genuine computation (`solution_quality`,
      `hardcoded_solution`): no `echo 42 > result`. Oracle scores 1.0 (validation
      runs it). Explores state before acting (discussion #224: "oracle solutions
      should investigate system state progressively").
- [ ] F2 [M] Master #27, #28, #29, #34, #35 · Files longer than ~20 lines live as separate files in `solution/`,
      not heredocs in `solve.sh`. Whole-file `cp` oracles are permitted — judge
      the broken-vs-fixed DELTA (F-045): no-op delta, delta beyond scope, or an
      unidentifiable planted defect is [B].
- [ ] F3 [M] Master #30 · **Precomputed-artifact exception** used correctly: only when the
      computation is inherently hours-long; generator script included; `solve.sh`
      documents provenance, runtime, that the artifact passed the verifier, and
      how to regenerate; the artifact is the script's unmodified output.
- [ ] F4 [B] Master #31, #36 · Deterministic: no unseeded randomness, unsorted `ls`, timing-dependent
      sleeps, interactive prompts, or wall-clock dependence. Consistent across
      hundreds of runs.
- [ ] F5 [B] Master #32 · Derivable: a competent expert with `instruction.md` + `environment/`
      could reach this solution. Knowledge that exists only in the oracle (magic
      constants, an unstated formula) is [B] (F-004).
- [ ] F6 [M] Master #13, #106 · Screened with the instruction (authorship is not graded); **[t]** no
      canary, **[up]** canary comment present in every text file; no
      generator/meta commentary ("so the verifier sees…"); pinned `==` installs
      if it installs anything; no bare `nproc`.

## G · Reviewer-facing write-ups

**Where they live** (Master #103): three sections — `## Difficulty`,
`## Reference solution`, `## Verification` — plus `[metadata].relevant_experience`
in `task.toml` (about the author, Master #61). Under `terminus` the three sections
are the workspace record `authoring/<task>/write-ups.md`, which never ships —
judge G1–G5 on it when supplied, `no-evidence` when not, and a README.md in the
task is T30; under `upstream` they are README.md in the task (upstream
`task-readme-template.md`). A `*_explanation` key in `task.toml` is `T3-WRITEUP`
under `terminus`. Every remediation note names the section in the profile's home
(or the supplied audit evidence).

- [ ] G1 [M] Master #103 · All three sections exist and are substantive
      ([up] `STRUCT-README`, `README-01`, `README-02`, upstream
      `check-task-readme.sh`; [t] read from the workspace write-ups), written for
      a non-domain reader; soft caps of roughly 400 / 300 / 600 words of prose
      ([up] `README-04` [L]; tables and code blocks are free). A change log is
      expected on revised tasks. `relevant_experience` is substantive
      (`T3-WRITEUP`, `TOML-16`, Master #61).
- [ ] G2 [M] Master #62, #95, #99, #103 · `## Difficulty`
      (`difficulty_explanation_quality`): names the intrinsic crux for humans AND
      agents in non-specialist terms; **no pass rates, scores, or model names**
      (      [up] `README-03`); one sentence on whether the data is synthetic or real
      ([up] `PROV-01` [L]); one sentence on who does this work in the real world, and
      the paper, dataset, pipeline or project it comes from (Master #99). Trial
      flag `difficulty_crux` (I4) is judged against this text.
- [ ] G3 [M] Master #103 · `## Reference solution` (`solution_explanation_quality`):
      strategy and key insight, congruous with `solve.sh`; if no solution is
      shipped, a rigorous justification (only "a team would need weeks"
      qualifies).
- [ ] G4 [M] Master #6, #100, #101, #102, #103 · `## Verification`
      (`verification_explanation_quality`): what is checked, how, why it is
      sufficient, congruous with the tests; where the graded reference values come
      from ([up] `PROV-02` [L], #100); **every tolerance / threshold / similarity bound
      is justified** — what it brackets, what legitimate variation it absorbs,
      which independent correct implementation it was measured on, the
      correct/defective classification and the 10% margins on the shipped
      instances ([up] `TOL-01` [L], #101); every withheld instance is one no
      trivial null reaches (#102). "Accepted range [29, 31]" with no rationale fails.
- [ ] G5 [m] Master #103 · The write-ups do not duplicate the instruction and are not
      misleading (`task_readme`); the write-ups are never shown to the agent, so
      they must not carry anything the instruction relies on.

## H · Runtime evidence (per task, retained)

- [ ] H1 [B] Master #36 · Environment image AND verifier image build (the verifier image is the
      one people forget to build locally). Compose sidecars start; healthcheck
      passes.
- [ ] H2 [B] Master #72 · Oracle passes the FULL suite — reward 1.0 and ctrf N/N — in separate
      processes: **[t] 3 runs, packaged as `oracle-nop-evidence/oracle-1..3`**
      (T18); [up] at least 2 (single-run QA
      cannot detect flakiness, F-041). Verdicts: PASS · FLAKY · ORACLE-FAIL.
- [ ] H3 [B] Master #73, #74 · NOP fails: reward 0 AND ctrf 0/N. **[t] 2 runs, packaged as
      `oracle-nop-evidence/nop-1..2`** (T18) — NOP × 1 was the previous edition.
      Keep each ctrf.
- [ ] H4 [L] Master #60 · Negative control, when one ships: scores 0. Its **absence is not a
      finding** (T19) — establish hardening via isolation, hidden-test
      protection, independent recomputation and reward-channel integrity instead.
      There is no fixed NC-01–NC-14 matrix to satisfy.
- [ ] H5 [B] Master #53, #75, #80 · Evidence binds to the shipped bundle: ctrf test names match the shipped
      suite (T25), and **[t] `SUMMARY.txt`'s `sha=` equals the recomputed bundle sha
      (T5d) with evidence newer than every graded file (T24)**; trials against an
      older suite or a different package are stale and dropped
      (F-081). Trajectories must be complete and untruncated. A trajectory
      without a reward is a transcript (F-080). Self-audit claims are claims
      (F-059).
- [ ] H6 [M][up] (no master check) · `harbor check` against the 39 criteria of
      `rubrics/task-implementation.toml` and every `ci_checks/check-*` pass. Not
      run in this workspace (AGENTS.md forbids `harbor check`; the criteria are
      folded into the master and judged by reading — `docs/CI_CHECKS_REVIEW.md`).
      Under either profile a clean static screen is where reading starts, not
      where it ends (F-052).

## I · Difficulty & trial analysis

- [ ] I1 [B] Master #84, #95, #99 · **Not saturated, not trivial.** No difficulty label
      exists (Master #62); the bar (upstream `CONTRIBUTING.md` "Task Difficulty")
      is research-level work a domain expert is paid to do, well beyond the
      current frontier of model ability — not a textbook exercise or course
      project. A task every real-agent trial solves (Terminal-Bench 4.0's
      erp-procurement-planning: 5/5 on ten arms) is removed. Report per-agent pass
      rates from the packaged trials (**[t]** the required round is GPT-5.6 at
      `xhigh`, five complete attempts; [up] the maintainers' `/run` arms —
      calibration fact from Terminal-Bench 4.0: claude-code + Opus 5 `max`,
      codex + GPT-5.6-sol `xhigh`, 3 trials each) and the fraction of failures
      that are real (not env / timeout / refusal). Failing frontier models is
      *evidence*, not proof: read why they failed.
- [ ] I2 [B] Master #2, #107 · Trial flag `task_specification` (trial criteria
      `specification_completeness`, `solution_discoverability`) — tests expect a parameter name,
      format, return value or structure the agent had to guess. Definite; send
      back (this is B1 measured).
- [ ] I3 [B] Master #93, #107 · Trial flag `reward_hacking` (trial criterion
      `unearned_credit`, which also covers a pass from an answer the agent already
      knew) — an agent reached reward by editing tests,
      writing `/logs/verifier/reward*`, reading `solution/`, or manipulating the
      harness; or a `/cheat` trial passed by a shortcut. Close the hole (E3/E6).
      Solving an easy task honestly is not a hack.
- [ ] I4 [M] Master #84, #95, #107 · `difficulty_crux` (trial criterion
      `meaningful_difficulty`) — the agent failed for a reason unrelated to
      the write-ups' `## Difficulty` (format slip, env issue, incidental bug).
      Uphold → send back (unintended difficulty or wrong write-up); dismiss with a
      written reason.
- [ ] I5 [M] Master #57, #101, #107 · `near_miss` (trial criteria `boundary_fairness`,
      `verifier_correctness`) — substantively working solutions that miss a
      quantitative bar by a small margin, or a correct answer the verifier
      rejects. Many of these = the threshold is the difficulty (E8).
- [ ] I6 [M] Master #84, #107 · `refusals` (trial criterion `policy_refusal`) — the
      agent aborted on a content/safety policy (two Terminal-Bench 4.0 removals
      were "cyber refusals"). Reframe the task; a refused trial measures
      nothing.
- [ ] I7 [M] Master #92, #107 · `low_timeout` (trial criterion `execution_blocked`) —
      still progressing at the cutoff, stopped by the harness or a limit, or finished within
      minutes of it. **[t]** the timeout is already 28800 by rule (T10), so a run
      that hit it, or whose `exception_info` records a timeout, is not a
      capability measurement — re-run it (Master #92). **[up]** raise
      `[agent].timeout_sec`; 28800 is the norm.
- [ ] I8 [B] Master #95 · **Difficulty is essential, not manufactured** (`difficult`,
      `essential_difficulty`, `agentic`). Real: domain expertise, inferred
      specification, interacting constraints, state across steps, iterative
      trial-and-error, rich environments, hidden variations. Manufactured:
      ambiguity, obscure trivia, LLM-specific tricks (tokenization), tedium /
      volume, formatting minutiae, arbitrary precision, decoys, knife-edge
      thresholds, time pressure, compute intensity. Adversarially selected
      "trivial corners of capability gaps" are explicitly unwanted. Solvable by
      an expert who knows the answer in a few hours (`solvable`); not an open
      research problem with no known answer; not "thousands of person-years".
- [ ] I9 [B] Master #95, #99 · **Scientifically grounded and realistic**
      (`scientifically_grounded`, `interesting`): drawn from a real,
      research-level workflow a scientist would be paid to do on a computer; a
      real (possibly tiny) research community would care. No gimmicks, trick
      questions, invented games, or "make it more fun".
- [ ] I10 [B] Master #95 · **Agentic / multi-step**: needs exploration, tool use, iteration —
      not a single LLM generation or one command.
- [ ] I11 [M] Master #107 · **Trial analysis recorded** (upstream
      `rubrics/trial-analysis.toml`): every Step 3c trial, passing and failing,
      is classified from its full trajectory against the eight criteria —
      `specification_completeness`, `solution_discoverability`,
      `verifier_correctness`, `boundary_fairness` (task-side: any failing indicts
      the task, fixed at a fresh digest), `unearned_credit`,
      `meaningful_difficulty`, `policy_refusal`, `execution_blocked`. The record
      lives in the workspace Step 3c report and does not ship; when it is
      supplied, read it against the trajectories. The verdict JSON's six flags
      (I2–I7) carry the result.

## J · Novelty against the corpus — OUT OF SCOPE here

Corpus-wide duplicate detection (upstream `check-similarity.py`) is not run here.
Report a re-skin only when both tasks were shown to you (B6). Within-batch cloning
belongs to a batch audit. (Gate J is not the master's Section J: the TB-Science
checks #98–#107 are walked inside gates A, B, C, D, E, G and I.) Whether the
answer is reachable by web lookup or memorisation IS in scope (B6, Master #99).

## K · Fresh-eyes

- [ ] K1 Master #95, #98 · Re-read as a senior domain expert in the declared
      `[metadata].field` (upstream `REVIEWING.md`): with the tool names removed,
      is this their work; does the story cohere, does the name match the content,
      do the write-ups match the code, would you approve
      this submission with your name on it?
      "Is this actually hard, or just tedious? Would the instruction alone let you
      write the same tests? Can an agent cheat? Do tests verify real behaviour or
      string-match?" Report what survives the gates but fails this read.

---

## Master coverage map (`reference/MASTER_CHECKLIST_TBSCI.md`, checks 0–107)

Every master check, the gate that walks it, and how it is answered. **Mechanical**
= a `tbsci_static_screen.py` code (or `trial_evidence.py` / `ctrf_summary.py`
flag) enforces it — confirm each hit against the file, as for every screen flag.
**Partial** = the screen raises a finding or LEAD for the common case and the
read decides the rest. **Read** = no automation is feasible; answer it by reading
or running, with evidence. The master is numbered continuously 0–107 (renumbered
2026-09-30; the old→new table is in the workspace's
`docs/WORKFLOW_HARDENING_CHANGELOG.md`; Section J, #98–#107, was appended on
2026-10-06 by the TB-Science revamp, `docs/TBSCI_REVAMP.md`). Every check is answered on every task;
none is marked from memory.

| Master | Check | Gate | How answered |
|---|---|---|---|
| #0 | Concise prompt (AI drafting allowed), absolute paths, names outputs, what not how | B4, B7 | Partial — `INSTR-02/03/04/05`; read |
| #1 | Every stated requirement is tested (unless NOP-passable) | B1, E10 | Read (two-way table, SKILL step 4); `DNM-01` leads |
| #2 | Every enforced requirement is stated | B1, E10, I2 | Partial — `SPEC-01`/`SPEC-02` leads; read |
| #3 | No "how"-shaped sentence where an outcome would do | B2 | Partial — `INSTR-04`; read |
| #4 | Interface contracts are not violations of #3 | B2 | Read |
| #5 | No grader / test suite / verifier / pytest / `/tests` / `/opt/verifier` framing | B9 | Mechanical — `T3-FRAMING`, `INSTR-08` |
| #6 | Every stated constant matches the test byte for byte | B1, E8 | Read (grep both sides) |
| #7 | Every path the instruction names exists in the built image | B8 | Partial — `SPEC-02`; read |
| #8 | Merged into #47 | — | N/A — answered by #47 |
| #9 | No self-contradiction | B1, B11 | Read |
| #10 | No narration of each planted defect's mechanism | B2 | Read |
| #11 | No canary / GUID in instruction.md | T3, A9 | Mechanical — `T3-CANARY` |
| #12 | Every environment/ file is required | C12 | Read |
| #13 | No hint comments (TODO/FIXME/BUG:/planted/deliberate/for the grader/test) | T22, C12 | Mechanical grep — `T3-HINT-COMMENT`; justify or fix each hit |
| #14 | No comment echoing the author near a defect | C12 | Read |
| #15 | No lore/notes file indexing the defects | C12 | Read (map against rubric.txt and trajectories) |
| #16 | No opaque letter+digit names | T22, C12 | Partial — `T3-OPAQUE-NAME`; read |
| #17 | No mislabelling names | C12 | Read |
| #18 | Merged into #12 | — | N/A — answered by #12 |
| #19 | No unused answer-key module | C1 | Partial — `ENV-LEAK` lead; read |
| #20 | Byte-diff environment/ vs tests/ and solution/ | C1, T21 | Partial — `DRIFT-01` lead; diff by hand |
| #21 | Merged into #12 | — | N/A — answered by #12 |
| #22 | Merged into #12 | — | N/A — answered by #12 |
| #23 | No authoring-machine metadata in vendored archives | T14, C6 | Partial — `T3-ENV-BINARY`; `tar tv` by hand |
| #24 | Dockerfile never COPYs tests/solution or touches reserved paths | T21, C1, C7 | Mechanical — `ENV-05`, `ENV-07` |
| #25 | Decoys fair and undisclosed | C12 | Read |
| #26 | Digest pins, canonical base, tmux+asciinema, pin rules, size, no privileged / --platform | T13–T15, C2–C7 | Mechanical — `T3-DIGEST`, `T3-BASE`, `T3-TMUX`, `ENV-02/09/10/15/16`, `T3-ENV-SIZE` |
| #27 | solve.sh diffed file by file against environment/ | F2 | Read |
| #28 | Every touched file maps to a defect the instruction asks about | F1, F2 | Read |
| #29 | No out-of-scope delta | F2 | Read |
| #30 | Reference independently verified correct | F1, F3, E14 | Read / re-derive (mandatory for named algorithms) |
| #31 | No scenario-id branching in the reference | F4 | Read |
| #32 | No privileged / held-out knowledge in the reference | F5 | Read |
| #33 | Agent consensus vs the reference checked | E14 | Read (trajectories) |
| #34 | No orphaned solution/ files | F2 | Read (grep basenames) |
| #35 | Each fix ablated one at a time | F2 | Run by hand |
| #36 | Cold, portable oracle build | H1, C2, C13, F4 | Run by hand; `ORACLE-05` partial |
| #37 | Separate verifier, top-level `artifacts`, landing dirs | A3, D1, D2, D10 | Mechanical — `TOML-02`, `TOML-09`, `PKG-01/02/03`, `ART-01` |
| #38 | Verifier deps baked at exact pins, nothing at trial time | D3, D4 | Mechanical — `VER-01/03/04`, `VER-05`, `ENV-08`, `ENV-09` |
| #39 | test.sh: no `set -e`, reward on every path, ends `exit 0` | D7, D9 | Mechanical — `T3-TESTSH`, `VER-07`; trace control flow by reading |
| #40 | Zero individual tests pass under NOP | E1, T18 | Mechanical — `T3-CONTROLS` (row level), `ctrf_summary --expect nop` |
| #41 | Guard tests coupled to a behavioural assertion | B10, E1 | Partial — `VER-18/19`; read |
| #42 | Fix is coupling, never deletion | E1 | Read (remedy rule) |
| #43 | Assertions match names / docstrings | E9, E11 | Read |
| #44 | Ground truth never from agent-editable code | E2 | Partial — `TRUST-01`; read |
| #45 | Private fixtures baked independently; tamper test | E2, D10 | Partial — `TRUST-01`; read or live tamper |
| #46 | Holdouts change the graded outcome | E5 | Partial — `HOLDOUT-01` lead; read / run |
| #47 | Exactness enforced literally, reference satisfies it | E9 | Read |
| #48 | Merged into #6 | — | N/A — answered by #6 |
| #49 | No string-literal concatenation obfuscation | E11 | Mechanical — `T3-OBFUSCATION` |
| #50 | No dead test code | E11 | Read |
| #51 | Merged into #43 | — | N/A — answered by #43 |
| #52 | Fail-closed tests carry a positive control | E6 | Read |
| #53 | ctrf test counts match the shipped suite | T25, H5, D5 | Mechanical — `T3-TESTCOUNT`; `trial_evidence` / `ctrf_summary` stale-suite check |
| #54 | The verifier seal: root-only `/tests` AND agent code through the Appendix `setpriv … env -i … timeout -k` launcher | T16, E3 | Mechanical + read — `T3-SETPRIV`, `T3-SANDBOX`, `T3-SEAL`, `ISO-01/02/03`, `SEAL-01`; Appendix SELF-TEST |
| #55 | Artifacts are untrusted data: escaping symlinks deleted (in-tree kept), expected side only from `/tests` | T16, E2 | Partial — `T3-SYMLINK`, `TRUST-01`; trace every read; live plant of an escaping and an in-tree link |
| #56 | Reward written last, by root, after kill-to-exhaustion and `rm -f` | T16, E3 | Partial — `T3-REWARD-LAST`; live background-writer submission |
| #57 | No wall-clock assertion; thresholds ≥ ~5 % from the reference | T17, E8, I5 | Partial — `T3-PERF`, `PERF-01`; measure margins by running |
| #58 | Binary reward written only to `reward.txt` (no `reward.json`); identical oracle/agent grading | D6, D8 | Mechanical — `VER-08` (a `reward.json` is a BLOCKER), `VER-09` |
| #59 | Value checks, not existence checks | E4, E9, E12 | Partial — `VER-16/18/19`; read |
| #60 | Each shortcut rejected by its own named assertion | E4, E6, H4 | Read (cheat simulation, SKILL step 8) |
| #61 | Required metadata present, accurate, current; retired `category`/`subcategory`/`languages` rejected; author fields optional | T6, T7, T8, A2, A3, A4, G1 | Mechanical presence — `T3-NAME`, `T3-ROUND-NAME`, `SLUG-01/02`, `SLUG-TOKENS`, `T3-AUTHOR`, `T3-TAGS`, `T3-WRITEUP`, `T3-RESIDUE`, `TOML-02/04–07/16`; read accuracy |
| #62 | No `difficulty` field, tier label or pass-count anywhere in the task | T10a, G2 | Mechanical — `T3-DIFFICULTY` ([up] `README-03`); read domain-word hits |
| #63 | `environment_mode = "separate"`; timeouts exactly 28800 | T10, A6 | Mechanical — `TOML-09`, `T3-TIMEOUT` |
| #64 | Network declared on both phases: agent `public`, verifier `no-network` (or justified allowlist) | T9, A8 | Mechanical + LEAD — `T3-NET` |
| #65 | No stale-schema residue (`version`, `[task]`, milestones, `*_min`, generator fields, local paths, `is_multi_container` not true); `schema_version` optional; resources declared, `gpus = 0` | T8, A5, A7 | Mechanical — `T3-SCHEMA`, `T3-RESIDUE`, `T3-LOCALPATH`, `T3-MULTI`, `TOML-12`, `T3-GPU` |
| #66 | Every rubric line maps to a real instruction | T4 | Read |
| #67 | rubric.txt format | T4 | Mechanical — `T3-RUBRIC`, `T3-RUBRIC-MISSING`, `T3-RUBRICS-PLURAL` |
| #68 | No contradictory rubric lines | T4 | Read |
| #69 | No double counting | T4 | Read |
| #70 | Rubric arithmetic consistent with rubric_score.txt | T5c | Mechanical gradient recompute — `T3-RUBRIC-SCORE`; check by hand |
| #71 | Control structure exactly oracle-1..3 / nop-1..2 × 3 files | T18 | Mechanical — `T3-CONTROLS` |
| #72 | Every oracle row passed | T18, H2 | Mechanical — `T3-CONTROLS`, `ctrf_summary --expect oracle` |
| #73 | Every NOP row explicitly `failed` | T18, H3 | Mechanical — `T3-CONTROLS`, `ctrf_summary --expect nop` |
| #74 | NOP failures are genuine assertion mismatches | T18, H3 | Partial — `T3-NOP-ERROR`; read test-stdout.txt |
| #75 | Evidence bound by digest; mtimes secondary | T24, H5 | Mechanical — `T3-MTIME` (mtime sanity); launch/digest records |
| #76 | Control evidence not duplicated | T23 | Mechanical — `T3-DUPLICATE` |
| #77 | SUMMARY.txt exactly two lines | T5b | Mechanical — `T3-SUMMARY` |
| #78 | rubric_score.txt pure data | T5c | Mechanical — `T3-RUBRIC-SCORE` |
| #79 | SUMMARY rewards match reward.txt AND ctrf.json | T5b | Mechanical — `T3-SUMMARY` |
| #80 | SUMMARY sha = fresh bundle-sha recompute | T5d, H5 | Mechanical — `T3-BUNDLE-SHA`; `trial_evidence` bundle_sha |
| #81 | Merged into #75 | — | N/A — answered by #75 |
| #82 | Merged into #76 | — | N/A — answered by #76 |
| #83 | Model runs (and their scores) not duplicated; float precision | T23 | Partial — `T3-DUPLICATE`, `T3-RUBRIC-SCORE-DUP`; compare values by hand |
| #84 | Every failing run's failure read from its own files | I1, I4, I6 | Read |
| #85 | rubric_score.txt files pairwise distinct | T5c | Mechanical — `T3-RUBRIC-SCORE-DUP` |
| #86 | Every verdict cites that run's evidence; METs spot-checked | T5c | Partial — `T3-RUBRIC-SCORE` (citation present); read provenance |
| #87 | PII / `stb` scrub per run/job directory | T26 | Mechanical — `T3-PII` (each of the ten directories) |
| #88 | No canary / GUID in the evidence | T26, T3 | Partial — `T3-PII` (canary markers); read GUID-shaped strings |
| #89 | result.json model-name fields raw | T27 | Read |
| #90 | Canonical agent/ and verifier/ file sets; reward.txt = ctrf outcome | T27, T5 | Mechanical — `T3-AGENT-FILES` |
| #91 | Same model, harness and reasoning setting on every run, matching SUMMARY | T5a | Mechanical — `T3-EFFORT`; `trial_evidence` per-run |
| #92 | No populated `exception_info` | T27, I7 | Mechanical — `T3-EXCEPTION`; `trial_evidence` errors |
| #93 | Reward-hack scan per trajectory; no truncation; genuine completion | T28, I3 | Partial — `T3-REWARD-HACK`, `T3-TRAJ`; read the end of each run |
| #94 | First five valid trials in launch order; the set moved with them | T29 | Partial — `T3-RUN-ORDER`; read (T5b / T5d / T24 / T26 catch partial moves) |
| #95 | No manufactured difficulty; difficulty classified in plain words | T22, I8–I10, K1 | Read |
| #96 | Delivery structure exact (five inner members, no README.md); no banned members | T1, T2, A1 | Mechanical — `T3-LAYOUT`, `T3-BANNED`, `STRUCT-04` |
| #97 | Final grep across the whole bundle | T26, T3 | Mechanical — `T3-PII` (task folder, rubric.txt, SUMMARY.txt), `T3-CANARY` |
| #98 | Taxonomy and scope: exact domain/field, subfield; classified by the indispensable scientific expertise | A4, K1 | Partial — `TOML-04`, `TOML-05` (values); read the fit |
| #99 | Scientific grounding and novelty; not web-lookupable or memorisable | B6, G2, I1, I9 | Read |
| #100 | Data and ground-truth provenance recorded; reference values independent or disclosed | E2, C5, G4 | Partial — [up] `PROV-01`, `PROV-02` leads; read (and the workspace `authoring/<task>/write-ups.md` and `provenance/` when supplied) |
| #101 | Tolerances justified by the science; independent implementation; method classification and 10% margins on the shipped instances (no fresh-draw study; under-20% generator margins: 3 fresh draws, increased to 6 if borderline or inconsistent; skipping never a finding) | E8, G4, I5 | Partial — [up] `TOL-01` lead; run or read the measurement (workspace calibration when supplied) |
| #102 | Graded instances defeat the trivial nulls | E15, G4 | Read / run each null per instance |
| #103 | No README.md; write-ups `## Difficulty` / `## Reference solution` / `## Verification` in `authoring/<task>/write-ups.md` | T30, G1–G5 | Mechanical — `T3-README`, `T3-WRITEUP` ([up] `STRUCT-README`, `README-01..04`); read write-up quality from workspace evidence |
| #104 | Instruction ends with the 28800 s suffix | T10b, B5 | Mechanical — `INSTR-01` |
| #105 | Merged into #37, #38 and #64 | — | N/A — answered by #37, #38 and #64 |
| #106 | Reproducible, portable environment (no bare `nproc`, no host binds, no `--platform`, apt hygiene, `==` pins, no solve/test names in the agent Dockerfile, seeds) | C2, C4, C7, C9, F6 | Mechanical — `ENV-02`, `ENV-09`, `ENV-11`, `ENV-13`, `ENV-18`, `ENV-05`; read seeds |
| #107 | Every Step 3c trial classified against the eight trial-analysis criteria | I2–I7, I11 | Read (workspace Step 3c report; not shipped) |
