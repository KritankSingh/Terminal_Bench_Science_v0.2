# Client-layer rules (V1–V20)

These rules come from three places: the client's v0.1 delivery reviews, the upstream TB-Science
v0.2 docs (CONTRIBUTING.md, TASK_REVIEW_AUTOMATION.md, read 2026-10-30), and the 7-task revision
analysis (docs/LESSONS.md). They ADD to the frozen master checklist and never override it. When
the client's real v0.2 checklist arrives, diff it against this list (docs/CLIENT_CHECKLIST_DIFF.md).

"Mech" = enforced by `scripts/tbsci.py check` (v02_checks, task_check, calibration table);
"Judg" = a point of the review card (R1–R16, docs/WORKFLOW.md). "Master" = the nearest master check.

| # | Rule | Source | How | Where | Master |
|---|---|---|---|---|---|
| V1 | No round tags, digests, dates, "Master #", "Appendix", "authoring/", step tags in shipped files; packaged `trials_dir` = `trajectories` | client D1/D2/D4/D5 | Mech (hygiene patterns, zip) | check, package | #97 |
| V2 | `[environment].network_mode="public"`, `[verifier.environment].network_mode="no-network"`, no `allow_internet`, `gpus=0`, `cpus<=4`, `memory_mb<=16384`, timeouts 28800 | upstream v0.2 + master | Mech (toml) | check | #63–#65 |
| V3 | Every pip/uv package pinned `==`; no bare `nproc` | upstream v0.2 + master | Mech (pins) | check | #26, #106 |
| V4 | Reward only literal 0 or 1; no `set -e`; reward 1 only when every declared case passes on any selector | upstream v0.2 + induced B2 | Mech (reward, seal) | check | #39, #58 |
| V5 | Explanations live in `authoring/<slug>/write-ups.md` (Difficulty, Reference solution, Verification); no README.md in the task | master #103 (upstream v0.2 wants README; advisory) | Mech | check, R15 | #103 |
| V6 | Every graded number has a definition sentence (unit, sign, epoch, estimator); definitions, never methods; no crux-narrating sentence | 5/7 tasks (C2), tdm | Judg + Mech (pipeline words) | R1, R2 | #0, #2, #10 |
| V7 | Plain expert voice; fictional names so nothing is web-reachable | upstream AI-authorship check (advisory), master #99 | Judg | R1, R14 | #99 |
| V8 | Planted-parameter generator, freeze hash before final generation, truth from planted parameters | kv Route B, tdm lost generator | Judg | R14 | #100 |
| V9 | Generator unit-tested sentence by sentence against the instruction | embankment M1, induced grid, tide noise | Judg | R14 | #100 |
| V10 | Instances and hold-outs never on round values | catalyst, tide, kv | Judg | R14, R16 | #102 |
| V11 | Identifiability screen before any bound | tdm, tide, induced, kv | Judg | R16 | #101 |
| V12 | Correct + defective ensemble first; correct methods keep >= 10% margin; every defective method fails a test | induced template | Mech (calibration.md: 1 independent correct method, >= 10% margin; every naive default and null fails) | check | #101 |
| V13 | Null battery clears every bound by >= 1.1x | induced B1, tide, kv | Mech (nulls fail in calibration.md) + Judg (1.1x clearance) | check, R15 | #102 |
| V14 | >= 10 independent tests; each fails for a named defective method; one lever decides <= 3 tests | owner rule; 25/82 tests never failed | Mech (count) + seed (>= 10 planned) | seed, check | #59, #102 |
| V15 | Bounds frozen before trials; a moved bound voids the round | induced, tdm | Judg | R16, trials | #57, #94 |
| V16 | Rubric has a crux line; negatives describe real wrong routes | 22 failed runs got full positives | Judg | R13 | #66–#70 |
| V17 | Two independent implementations, one blind to the generator | self-review gap | Mech (correct row in calibration.md) + Judg | check, R7 | #30, #101 |
| V18 | `authoring/<slug>/hint.md` written before trials (used only in Step 3a) | upstream v0.2 hinted trials | Judg | before trials | #107 |
| V19 | Review card filled by a session that did not build the task | author = reviewer in all 7 tasks | advisory (lean) | R1–R16 | — |
| V20 | Trials only when CONFIRMED; label every trial; hack-pass or false-fail voids the round | owner rule (5 trials, client model) | Mech (round.toml, trials.md) | trials | #92–#94, #107 |
