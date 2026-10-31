# Packaging Checklist (Terminal-Bench Science)

`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth; this is the
Step 4 quick list over it. Every box maps to master checks (in brackets), and
the authoritative record is `authoring/<task>/master-checklist.md`. Layout and
file formats: `docs/reference/DELIVERY_CHECKLIST.md`. This is a packaging checklist for
private delivery to a buyer: nothing is submitted anywhere (no upstream PR, no portal, no Harbor
Hub), and no upload or external project step is part of this workspace (the file
keeps its old name because other docs link to it). Nothing ships with any open finding of any severity,
and nothing ships that the bundled auditor (`tools/final-tbsci-audit-master/`) has
not judged `✅ Ready to Submit` on the exact candidate ZIP.

## Task design

- [ ] Clear goal; requirements inferable from provided materials [#1, #2]
- [ ] Clarification-collapse, public-solution, refusal, portability, and
      saturation screens passed
- [ ] Concise instruction (AI drafting allowed); absolute paths; every output
      file named; solvable by an independent domain expert from the text alone
      (field-standard conventions omitted, two-convention choices stated) [#0, #7]
- [ ] Ends with the exact suffix `You have 28800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.` [#104]
- [ ] No pipeline vocabulary; no canary strings [#5, #11]
- [ ] Multi-step (not one-shot / straight-line burst); credible expert path
      needs at least five terminal commands plus intermediate reasoning
- [ ] No manufactured difficulty; what makes it hard stated in plain language [#95]
- [ ] Novel (not a reskin); research-level scientific workflow, not a textbook
      exercise; answer not reachable by web lookup or memorization [#99]
- [ ] Exact `domain` + `field` from `docs/TASK_TAXONOMY.md`, non-empty `subfield`;
      the task genuinely belongs to that field [#61, #98]
- [ ] Data provenance recorded (`authoring/<task>/provenance/`); ground truth
      independent or oracle-derived and disclosed [#100]
- [ ] Every tolerance justified by the science and measured on an independent
      correct implementation with 10% margins on the shipped instances (no
      fresh-draw study; under-20% generator margins: 3 fresh draws, 6 if
      borderline or inconsistent; skipping the probe is never a finding); every withheld instance is one no trivial null reaches [#101, #102]

## Required files

- [ ] `task.toml` — all required fields; descriptive under `[metadata]` [#61–#65]
- [ ] `instruction.md` — ends with the timeout suffix [#104]
- [ ] No `README.md` in the task; `authoring/<task>/write-ups.md` (workspace, never
      shipped) — `## Difficulty`, `## Reference solution`, `## Verification`, each
      non-empty; no pass rate, tier or canary [#62, #103]
- [ ] `rubric.txt` — non-empty; locally authored before the Step 2b gate [#66–#69, #70]
- [ ] `environment/Dockerfile` — builds cold; digest-pinned FROM; final base
      `public.ecr.aws/docker/library/<python|node|golang|rust|eclipse-temurin|gcc|ruby|maven|debian|ubuntu>`
      or a justification comment; tmux+asciinema; language packages pinned
      exactly (numpy/scipy/pandas and domain libraries included), apt unpinned
      with `apt-get update` and list cleanup; no bare `nproc`, no compose host
      binds, never names solve.sh/test.sh/test_*.py [#26, #36, #106]
- [ ] `solution/solve.sh` — deterministic; no orphaned files [#34]
- [ ] `tests/Dockerfile` — verifier deps baked at exact pins; ends with the
      master's Appendix step 1 (uid 12000, `chmod -R go-rwx /tests`) [#38, #54]
- [ ] `tests/test.sh` — no `set -e`; reward always written; last command `exit 0`;
      pytest writes `--ctrf /logs/verifier/ctrf.json` (`-p ctrf_reporter`) [#39]
- [ ] `tests/test_manifest.json`, `tests/ctrf_reporter.py`, `tests/test_outputs.py`

Do not zip `rubrics.txt` or any `README.md`; the write-ups stay in
`authoring/<task>/write-ups.md`.

## Environment

- [ ] Every file needed; no dead files [#12, #18]
- [ ] No hint or author-echoing comments; literal grep clean [#13, #14]
- [ ] No lore/notes file indexing defects [#15]
- [ ] No opaque or mislabelling names; no unused answer-key module [#16, #17, #19]
- [ ] No byte-identical environment/tests file that computes a graded quantity [#20]
- [ ] Every environment doc consistent with the instruction and tested [#12]
- [ ] Vendored archives re-tarred `--owner=0 --group=0` [#23]
- [ ] Agent Dockerfile never copies/touches `/tests`, `/solution`, `/oracle`,
      `/logs/verifier`, `/logs/artifacts` [#24]
- [ ] Decoys fair and undisclosed [#25]

## Solution

- [ ] Every touched file maps to a stated defect; nothing out of scope [#27–#29]
- [ ] Independently verified correct for any named algorithm/metric [#30]
- [ ] No scenario-id branching or privileged knowledge [#31, #32]
- [ ] Every fix ablated one file at a time, each failing its expected tests [#35]

## Verifier

- [ ] `environment_mode = "separate"`; top-level `artifacts` lists every needed
      path; artifact parent dirs exist in verifier image [#37]
- [ ] Zero tests pass under NOP; guards coupled to behavior [#40–#42]
- [ ] Test bodies match names/docstrings; no dead code; no obfuscation [#43, #49–#51]
- [ ] Ground truth never from agent-editable code or tamperable fixtures [#44, #45]
- [ ] Holdouts change the graded outcome [#46]
- [ ] Exactness and tolerances literally as documented [#47, #6]
- [ ] Fail-closed tests run a positive control in the same function [#52]
- [ ] Agent code executed via the Appendix A launcher (`setpriv --reuid=12000
      --regid=12000 --clear-groups --no-new-privs env -i … timeout -k 5 <PER_RUN_LIMIT>`),
      never imported in-process [#54]
- [ ] before grading, `test.sh` deletes every artifact symlink whose resolved target
      escapes the artifact paths (in-tree links kept);
      every expected-side file comes from `/tests` [#55]
- [ ] `test.sh` kill-to-exhaustion, then `rm -f
      /logs/verifier/reward.txt`, then writes the reward [#56]
- [ ] Appendix SELF-TEST run in the built verifier image: every FAIL line fails;
      a /tests-reading, symlink-planting, reward-rewriting submission scores 0 [#54–#56]
- [ ] No wall-clock latency/throughput assertion; any deterministic threshold
      predeclared, admits a different correct strategy, >~5% from the reference
      or signed off [#57]
- [ ] Binary reward; identical Oracle/agent logic [#58]
- [ ] Value checks, not existence checks [#59]
- [ ] Each #60 shortcut rejected by its own named assertion [#60]
- [ ] Every non-standard variable read by `tests/test.sh` has a default
- [ ] `tests/test.sh` performs no trial-time fetch or install; tooling baked in
      `tests/Dockerfile` [#38]

## Configuration

- [ ] No top-level `version` key, no `[task]` table; `schema_version` optional [#65]
- [ ] No `difficulty` field; no tier, percentage or pass count anywhere in the task [#62]
- [ ] `[agent].timeout_sec`, `[verifier].timeout_sec`,
      `[environment].build_timeout_sec` all `28800` [#63]
- [ ] `[environment].network_mode = "public"` declared;
      `[verifier.environment].network_mode = "no-network"` declared (allowlist only
      with a reason in `resource-plan.md`) [#64]
- [ ] `domain`/`field`/`subfield`; 3–6 tags; `expert_time_estimate_hours`;
      substantive `relevant_experience`; author fields optional but non-empty when
      present; no `category`/`subcategory`/`languages`, no `*_explanation` keys [#61]
- [ ] `cpus`/`memory_mb`/`storage_mb` declared and sized to the task; `gpus = 0`,
      no `gpu_types` [#65]
- [ ] Multi-container tasks set `[metadata].is_multi_container = true`; others omit it [#65]

## Evidence

- [ ] Step 2a contract, traceability, threat model, resource plan, and controls complete
- [ ] `scripts/hardening_check.py --workflow` has no errors
- [ ] `scripts/audit_task.py tree` PASS (Step 2b gate step c1)
- [ ] Step 3b: `master_checklist.py check --stage review` passed on the current
      digest, every auditor LEAD answered with evidence
- [ ] `oracle-nop-evidence/`: Oracle x3 reward 1.0 every test passing; NOP x2
      reward 0.0 every test failing on a genuine assertion [#71–#74]
- [ ] Evidence bound to the current digest; runs independent [#75, #76]
- [ ] Step 3c model attempts ran at `reasoning_effort=xhigh` with full-fidelity
      capture (`fidelity PASS`); no `exception_info` [#91, #92]
- [ ] Measured rate 0/5–3/5, recorded in workspace reports only
- [ ] Every trial causally classified against the eight trial-analysis criteria;
      no reward hacking [#84, #93, #107]
- [ ] No trials pooled across revisions or run configs; the five runs are the first five
      fidelity-complete trials in launch order across rounds, none skipped (strictly
      increasing `result.json` `started_at`, distinct ids); the rest of the set moved
      with them after any rerun [#94]

## Trajectories

- [ ] `SUMMARY.txt` exactly two lines; rewards match each run's `reward.txt`
      and `ctrf.json`; bundle sha matches a fresh recompute [#77, #79, #80]
- [ ] Five `rubric_score.txt`, each citing its own run on every verdict line [#78, #85, #86]
- [ ] Canonical `agent/` and `verifier/` files in every run [#90]
- [ ] PII/`stb`/canary clean per run/job directory; model-name fields untouched [#87–#89]

## Commands

Packaging is build → auditor review → promote. There is no single command that
packages straight to `Task_Ready_To_Submit/`; only a promoted ZIP is a deliverable.

```bash
python3 scripts/task_check.py <task-folder> --strict
python3 scripts/hardening_check.py --workflow <task-folder>
python3 scripts/evidence.py check <task-folder> --evidence artifacts/gates/<task>/step2b.json
python3 scripts/master_checklist.py check <task-folder> --stage package

# 1. build the candidate (runs verify_package.py + audit_task.py package; deleted on any finding)
python3 scripts/package_task.py <task-folder> \
  --step3c-dir <task-folder>/trajectories/<step3c-round>
# -> artifacts/package-candidates/<task>/<task>.zip

# 2. the auditor's judged review of that exact candidate (tools/final-tbsci-audit-master/SKILL.md)
tools/final-tbsci-audit-master/scripts/review.sh extract artifacts/package-candidates/<task>/<task>.zip
tools/final-tbsci-audit-master/scripts/review.sh audit <task>
#    read every file; walk CHECKLIST.md gates T, A–K; answer every LEAD; manual probes and
#    cheat simulation; fill verdict.json + manual_probes.txt (no PENDING, no <<UNFILLED>>)
tools/final-tbsci-audit-master/scripts/review.sh lint <task>     # LINT_OK  ✅ Ready to Submit  (0 warning(s))
tools/final-tbsci-audit-master/scripts/review.sh report <task>

# 3. promote the exact audited bytes
python3 scripts/package_task.py <task-folder> --promote
# -> Task_Ready_To_Submit/<task>.zip
```

Step 4 never reruns Oracle, NOP, negative controls, or model trials. Rebuilding
the candidate invalidates the earlier auditor review automatically (`--promote`
checks that the auditor's extracted copy and task digest match the candidate);
re-extract and re-judge it.

- [ ] Build: `Package: PASS (candidate)`, including `verify_package.py` and
      `audit_task.py package` (zero findings, zero trial flags/errors, no stale evidence)
- [ ] Auditor review of this candidate: `LINT_OK  ✅ Ready to Submit  (0 warning(s))`,
      verdict `ready`, zero open findings; `report.md` rendered
- [ ] Promote: `Package: PASS (promoted)` (`audit_task.py verdict` passed; candidate
      and task digest unchanged since the build)
- [ ] Step 3c verdict is `READY FOR PACKAGING`
- [ ] ZIP is exactly the inner `<task-slug>/` (`instruction.md`, `task.toml`,
      `environment/`, `solution/`, `tests/`), `rubric.txt`,
      `oracle-nop-evidence/`, `trajectories/` [#96]
- [ ] ZIP excludes Step 2b/3b records, `SOURCE.txt`, authoring documents
      (`write-ups.md`, `provenance/`, `calibration/`, `hint.md`), staged
      negative controls, unrelated evidence, and workspace scaffolding [#96]
- [ ] Final PII/`stb`/canary grep ran after the last edit [#97]
