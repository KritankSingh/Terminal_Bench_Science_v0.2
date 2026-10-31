Task: <task-name>
Task digest: sha256:<digest>
Verdict: READY FOR DIFFICULTY EVAL

# Step 3b review — <task-name>

Reviewer:
Gate evidence: artifacts/gates/<task-name>/step2b.json; authoring/<task-name>/evidence/step2b-<stamp>/
Master record: authoring/<task-name>/master-checklist.md
Auditor: tools/final-tbsci-audit-master/ (CHECKLIST.md gates T, A–K; SKILL.md calibration)
Copy at: artifacts/reviews/<task-name>.md

Exactly one `Task:`, `Task digest:`, and `Verdict:` line (`scripts/stage_reports.py`).
Source of truth: `MASTER_CHECKLIST_TBSCI.md`. `Verdict: READY FOR DIFFICULTY EVAL`
only when `python3 scripts/master_checklist.py check tasks/<task-name> --stage review`
passes, `python3 scripts/audit_task.py tree tasks/<task-name>` passes with every
auditor lead answered, and no finding of any severity is open; any finding of
any severity means `Verdict: NEEDS REVISION`. BLOCKER / MAJOR / MINOR order the fix work; none of
them ships.

## Master checklist walk

Paste the `master_checklist.py check --stage review` output. Every check this
step answers is walked on disk, verdict + evidence on its line
(`#<N> | <VERDICT> | <evidence>`). The pre-trial parts of #1, #2, #15, #40,
#53, #57 and #101 are the evidence on those PENDING lines, and are also written
below. An empty PENDING line on those checks fails review. Those lines, plus
#33, #70, #71–#94, #96, #97, #101 and #107, stay PENDING until Step 4.

## Bundled auditor (tree)

Paste the first line of `python3 scripts/audit_task.py tree tasks/<task-name>`
(`Auditor (tree) <task-name>: PASS (0 finding(s), N lead(s))`) and the gate's
`$OUT/auditor-tree.log` path. Any `FAIL` line is a finding below.

Auditor leads — one row per `LEAD` line printed by `audit_task.py tree` (the same
leads appear as `AUDITOR` rows under their master number in
`master_checklist.py auto`). Each answer on a check this step closes also goes
on that master line. A lead on #1, #2, #15, #40, #53, #57 or #101 is the
evidence on that PENDING line and is also in this table. A lead on #33 is
answered in this table; that line stays PENDING. Step 4's verdict cites the
answer.

| Lead (code, master #, where) | Answer | Evidence (file:line, quote, or command output) |
|---|---|---|

Auditor gate walk on the tree (`tools/final-tbsci-audit-master/CHECKLIST.md`):
pass / fail / n/a with quoted evidence per gate; items that need packaged
evidence are marked `Step 4` (answered by the auditor's review of the candidate ZIP).

| Gate | Result | Evidence |
|---|---|---|
| T · package standard | | |
| A · bundle, name & manifest | | |
| B · instruction.md | | |
| C · environment/ | | |
| D · verifier wiring | | |
| E · grading integrity | | |
| F · solution/ | | |
| G · reviewer-facing write-ups (`authoring/<task>/write-ups.md`; no README.md in the task, #103) | | |
| H · runtime evidence | Step 4 | |
| I · difficulty & trial analysis | | |
| J · novelty (out of the auditor's scope; Master #95 still walked) | n/a | |
| K · fresh-eyes | | |

## Findings

| Severity (BLOCKER/MAJOR/MINOR) | Master # | File:line | Finding and evidence | Required action |
|---|---|---|---|---|

## Contract and verifier alignment (#1–#9, #12, #43, #47)

## Semantic equivalence and independent truth (#30–#33, #44–#46, #59)

## Reward-hacking and execution isolation (#20, #24, #37, #54–#56, #58, #60)

## Solution ablation and cold build (#35, #36)

## Public solution, refusal, portability, and resources (#26, #63–#65, #106)

## Science, provenance and calibration (Section J, #98–#103)

- Field and scope — domain / field / subfield, and why a reviewer in that field
  would call this their work (#98):
- Research grounding; the obvious web searches tried and what they returned (#99):
- Data origin and ground-truth source, from `authoring/<task-name>/provenance/`;
  independent or oracle-derived and disclosed (#100):
- Each tolerance: what it brackets, the independent implementation that measured
  it, the correct/defective classification, and the 10% margins on the shipped
  instances (#101; no fresh-draw study required). Where instances come from a
  generator and a method's smallest shipped-set margin is under 20%, the default
  internal check is 3 fresh unselected draws (6 only if those 3 are borderline or inconsistent);
  not running it is never a finding:
- Trivial nulls per graded instance; an instance a null reaches is a finding to
  fix, not something to disclose and ship (#102):
- No README.md in the task; `write-ups.md`'s three sections read against
  `solution/` and `tests/` (#103):

## Lettered checks (walk these; the master owns the wording)

- Materiality (preamble, #2, #6, #102): a defect is a FAIL only when it could change a graded verdict. An epsilon slack at the data's precision, an accepted equivalent such as 3.0 for 3, or a round value that lands in a wide band with no method producing it, is a NOTE. A test stricter than the instruction is still a BLOCKER (#6):
- #26(a): every `FROM` / compose `image:` digest is a multi-arch manifest, or the task records the one architecture it supports. A silent single-platform digest is a finding; if the media type is not in the tree, NOT VERIFIED naming the registry query:
- #54(c): after agent code runs, root never writes inside a directory the sandbox can write. Multi-run scratch lives under root-owned `/work`. A breach that can read a grader secret or write the reward is BLOCKER; a (c) breach that needs a surviving sandbox process, with no reachable path shown, is MAJOR:
- #58(c): a subset selector (`TBENCH_TEST_ID` or similar) never writes reward 1 for the whole task. An unknown or empty selector fails closed:
- #59(c): a capped decision procedure accepts every submission that meets the stated condition within the stated tolerance. Build a certificate that clears by a comfortable multiple of the margin and confirm the grader accepts it. N/A when grading is not a capped search. A cap that rejects a valid answer is a BLOCKER:

## What makes the task hard (#95)

Plain language; no tier, percentage or pass count.

## Program quality scenarios

- No wall-clock latency/throughput assertion (#57):
- Identical Oracle/agent test logic (#58):
- Multi-container metadata (#65):
- No runtime web data fetch (#38):
- Agent image leaves reserved paths untouched (#24):
- Reward written on every path; no `set -e`; ends `exit 0` (#39):
- Test environment-variable defaults:
- No near-Oracle threshold (#57):
- NOP rows fail on genuine assertions (#40, #74):
- task.toml: top-level `name` + `artifacts`; `domain`/`field`/`subfield`, `tags`, `expert_time_estimate_hours`, `relevant_experience`; no `difficulty`, top-level `version`, `category`/`subcategory`/`languages` or `*_explanation` key; timeouts 28800; `cpus`/`memory_mb`/`storage_mb`, `gpus = 0` (#61–#65):
- Network declared on both phases: agent `"public"`, verifier `"no-network"` or a justified allowlist (#64):
- instruction.md ends with the exact 28800-second closing paragraph (#104):
- No bare `nproc`, no compose host binds, apt lists cleaned, every pip/uv install pinned `==` (#106):
- Final agent base canonical ECR or justified (#26):
- Verifier seal per the master's Appendix — `tests/Dockerfile` step 1 lines; agent code via `setpriv --reuid=12000 … env -i … timeout -k`, never imported (#54):
- Artifact symlinks that escape the artifact paths deleted before grading, in-tree links kept and honoured (live plant of both); every expected-side read traced to `/tests` (#55):
- kill-to-exhaustion then `rm -f` reward then the write; background-writer submission scores 0 (#56):
- Appendix SELF-TEST output from the built verifier image (every FAIL line fails) (#54–#56):
- pytest writes `--ctrf /logs/verifier/ctrf.json` (`-p ctrf_reporter`):

## Negative-control evidence (#60)

## Open risks
