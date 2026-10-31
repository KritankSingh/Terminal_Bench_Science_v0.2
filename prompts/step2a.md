# Step 2a — Seed screen, contract and hardening spec lock (entry point)

**This is where a task starts.** The owner brings their own idea; Step 2a
screens it, then designs the task so that, once built, it passes every master
check. (Step 1, `prompts/step1.md`, is optional and only for generating ideas
when there are none; a `GO` seed from it is re-read and completed here.)

`MASTER_CHECKLIST_TBSCI.md` is the source of truth — Section J (Master
#98–#107) holds the TB-Science checks. The records below are where the design
is written down and later cited as evidence. Cite checks as "Master #N".

Order: **seed screen → `GO` → spec lock.** Using `docs/WORKFLOW.md`
Step 2a, complete (templates in `authoring/_templates/`; copy the folder to
`authoring/<slug>/` first):

- `authoring/<slug>/seed-review.md` (the seed screen — first, and `GO` before
  anything else is written)
- `specs/<slug>.md`
- `authoring/<slug>/contract.md`
- `authoring/<slug>/traceability.md`
- `authoring/<slug>/threat-model.md`
- `authoring/<slug>/resource-plan.md`
- `authoring/<slug>/controls.md` (plan table only; the gate fills the results)
- `authoring/<slug>/provenance/` (data and ground-truth provenance records)
- `authoring/<slug>/hint.md` — optional (see **Optional hint** below)

Do not create `tasks/<slug>/` yet. Everything author-side — generators,
provenance, independent reference implementations, calibration studies, the
hint — stays in `authoring/<slug>/` (`provenance/` records where things came
from; `calibration/` tests whether the result and the bounds are right — upstream
TB-Science calls it `evidence/`, a name this workspace reserves for gate rounds), never in
the task tree.

## Seed screen (owner's idea → GO / REDESIGN / REJECT)

Write `authoring/<slug>/seed-review.md` from the template. It folds in the
seven criteria of upstream `rubrics/task-proposal.md` — paraphrased, never
pasted — and adds the workspace's own screens. Answer each with reasons for
and against, then a decision:

- **Verifiable** — concrete, checkable outputs (numbers, fitted parameters,
  generated files, data products) that a program separates correct from
  incorrect reliably and repeatably; no open-ended or subjective grading.
- **Well-specified** — two experts reading the instruction would write
  verifiers that agree; not hard mainly because of a mass of corner cases;
  describable in a few paragraphs.
- **Solvable** — a reference solution will exist, or a compelling argument it
  can; dependencies, data and compute are realistic for a container.
- **Difficult** — needs years of domain expertise (PhD-level); not something an
  average undergraduate finishes in a few days; hard for a genuine reason, not
  obscure facts, trick questions, tedium or tight numbers (Master #95).
- **Scientifically Grounded & Interesting** — a research-level workflow a
  scientist would be paid to do, needing judgment about what to compute and
  why; not a textbook exercise, course project or generic coding in scientific
  vocabulary. Name the paper, dataset, pipeline or project (Master #99).
- **Scope** — genuinely belongs to its `domain` / `field` (Master #98).
- **Outcome-verified** — graded on the result, not on the tools or steps used.
- **Web-lookup risk** — three likely searches and the closest hit; the answer
  is not a published value, a well-known benchmark result or a widely
  available implementation (agents have open internet, Master #64, #99).
- **Data provenance** — where the data comes from and whether it may be
  redistributed (Master #100).

Also run the workspace screens in `docs/reference/idea-validation.md`: clarification
collapse, refusal risk, portability, saturation, interacting constraints, and a
credible expert path of at least five non-clerical terminal commands. Only
`GO` proceeds; `REDESIGN` loops back on the idea; `REJECT` stops.

## Science design (Master #98–#103)

Write each of these into `specs/<slug>.md` (and the named record) before
designing tests:

- **Taxonomy (#61, #98).** `domain` and `field` exact from
  `docs/TASK_TAXONOMY.md`, `subfield` the research specialty, classified by the
  scientific expertise indispensable to solve the task — with the tool names
  removed, a reviewer in that field would call this their work.
- **Data provenance plan (#100).** For every dataset the task ships or fetches:
  real (source, version/DOI or URL, licence that permits redistribution,
  preprocessing) or realistic synthetic (generator, parameters, seeds — the
  generator lives in `authoring/<slug>/provenance/`). Small inputs go in
  `environment/data/`; anything over the 100 MiB / 50 MiB limits is fetched at
  build time from an immutable revision written as a literal and
  checksum-verified (`docs/reference/DOCKERFILE_BEST_PRACTICES.md`). Grader-only data
  goes only into the tests image.
- **Ground-truth plan (#100).** For every graded reference value: where it
  comes from — the generating model (written out at generation time), a cited
  external value (published number, instrument reading, curated labels), or a
  second implementation written specifically to cross-check the oracle. If no
  independent truth exists (real measured data with no analytic form), plan to
  disclose it as oracle-derived and to defend it by varying an oracle stage and
  showing the reference is reproduced within tolerance.
- **Tolerance-calibration plan (#101, #6).** Record in `resource-plan.md`
  (its "Ground truth and tolerance calibration" section): each bound, what it
  brackets, the legitimate variation it absorbs (floating point, alternative
  valid estimators or discretizations, nondeterminism), the independent correct
  implementation — differing from `solution/` in a structural choice, not a
  constant — it will be measured on, and the defective approach it must
  separate from, with the expected separation. Bounds come from the science,
  never from the reference's own margin; the evidence goes in
  `authoring/<slug>/calibration/`.
- **Graded instances and nulls (#102).** List each withheld instance and the
  trivial nulls (constant, mean/median of the allowed range, centre of the
  domain, majority class, identity/copy-through, the task's own NOP) to run
  against it separately. Prefer asymmetric placements; a non-discriminating
  instance that cannot be avoided is named in `authoring/<slug>/write-ups.md`.
- **Write-up plan (#103).** Draft the three sections now in
  `authoring/<slug>/write-ups.md` (workspace only; the task carries no
  README.md), for a
  technically literate non-specialist: `## Difficulty` (what makes it hard for
  an expert and an agent; real or synthetic data; who does this work),
  `## Reference solution` (strategy and key insight, matching `solution/`),
  `## Verification` (what the tests check, where the reference values come
  from, how each bound was calibrated and on what independent implementation,
  which instances a null clears, if any). Name the source paper, dataset or
  pipeline (#99). No pass rate, tier or model score (#62).

## Optional hint

`authoring/<slug>/hint.md` (adapted from upstream `task-hint-template.md`, with
no canary) is optional. Write the hints a competent colleague would give when
stuck, as numbered `## Hint 1`, `## Hint 2`, … sections from gentlest (where the
difficulty lives) to most explicit (the procedure, never the result, the
thresholds or the answer). It is used only for an optional Step 3a hinted
diagnostic run that tells a hard task from a broken one; it never enters Step
3c, never ships, and is never copied into the task tree. If an agent passes on a
hint that is really missing context, move that context into `instruction.md`
and drop the hint.

## Instruction design (Master #0–#11, #104)

- Apply the expert-solvability bar (upstream `CONTRIBUTING.md`
  "instruction.md"; Master #0): an independent domain expert could solve it
  from the instruction alone. Leave out conventions standard in the field;
  state the choice wherever competent practitioners would differ (index origin,
  transform sign or normalisation, which standard estimator, units,
  tie-breaking); always state what the field does not determine (paths,
  bespoke schemas, a held-out input drawn differently, a different runtime or
  limits applied to submitted code). Thresholds may be withheld, but name every
  metric that gates the result.
- Draft the requirement list in `contract.md` as "what" statements (#3); the
  only "how"-shaped sentences allowed are genuine interface contracts the tests
  assert against: paths, flags, exit codes, output schemas (#4).
- Every requirement will be exercised by at least one test, and every test
  will enforce only stated requirements (#1, #2). `traceability.md` carries the
  **instruction sentence → test** map from the start.
- Every constant, tolerance, threshold and format you intend to state is written
  once in `contract.md` with the exact literal the tests will enforce (#6).
- "Exactly these keys"-style rules are planned as set-equality checks (#47).
- No pipeline vocabulary in the prompt: grader, test suite, verifier, pytest,
  `/tests`, `/opt/verifier`, `test_outputs`, reward file (#5). No canary (#11).
- Describe symptoms, not each planted defect's mechanism; do not explain why a
  naive path fails (#10). Absolute paths only; name every output file (#0, #7).
- The last paragraph is exactly
  `You have 28800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.`
  preceded by a blank line (#104).

## Environment design (Master #12–#26)

- List every file you intend to ship under `environment/` and why it is needed
  (#12, #18). No unused module that already implements the core capability
  (#19). No lore, notes, history, attempt-log or debug-notes file that itemizes
  the defects (#15). No comment that names the bug or the fix, or echoes your
  own wording (#13, #14). No opaque names like `k7`/`qp7` and no names that
  mislabel behavior (#16, #17). Decoys, if any, are reachable, fair and never
  labelled as decoys (#25).
- **#12: every doc under `environment/` is a graded requirement.** For each
  doc, `traceability.md` lists doc → requirement ID → test. A doc with no test
  is either tested or removed. Docs never contradict `instruction.md` (#12).
- **#20: no leaked oracle.** Plan which files, if any, exist on both the agent
  side and the verifier/solution side, and make sure none can compute any part
  of the graded quantity. Byte-identical environment/tests files are a finding
  unless they are pristine inputs the verifier re-reads independently (#45).
- Dockerfile plan (#24, #26, #106; `docs/reference/DOCKERFILE_BEST_PRACTICES.md`):
  digest-pinned `FROM`; the final agent base is
  `public.ecr.aws/docker/library/<python|node|golang|rust|eclipse-temurin|gcc|ruby|maven|debian|ubuntu>@sha256:…`
  or the Dockerfile carries a comment justifying why no canonical image works
  (the auditor's screen reports a missing one as MAJOR); tmux + asciinema;
  language packages pinned exactly — numpy, scipy, pandas and every domain
  library `==`; apt packages **not** version-pinned, with `apt-get update` and
  `rm -rf /var/lib/apt/lists/*`; no `FROM --platform` (arch-specific binaries
  chosen by `uname -m` with a fallback); no bare `nproc` (a fixed thread count
  sized to `cpus`); no compose host binds; ≤100 MiB total and no file >50 MiB;
  build-time data fetches pinned to an immutable revision literal and
  checksum-verified; nothing copied or created under `/tests`, `/solution`,
  `/oracle`, `/logs/verifier`, `/logs/artifacts`, and no reference to
  `solve.sh`, `test.sh` or `test_*.py`.

## Solution and verifier design

- **#30 independent correctness plan.** For a named algorithm, transform,
  metric, law, estimator or physical model, record in `resource-plan.md`
  (correctness section) the external library or hand derivation you will diff
  the reference output against. Oracle 3/3 is never the proof. This is the
  same independent implementation the tolerance calibration (#101) and the
  ground-truth plan (#100) lean on.
- **#31/#32:** the reference computes every graded value; it never branches on
  a scenario id and never uses knowledge the agent cannot see.
- **#35:** list each file `solve.sh` will touch and the tests you expect to fail
  when that one fix is reverted — this becomes the ablation plan for Step 2b.
- **#46 holdouts:** for each hidden/held-out case, write down how its expected
  value differs from the public case. An inert perturbation is a defect.
- **#57 thresholds:** no wall-clock latency, throughput or percentile assertion
  of any kind. A deterministic score/work threshold is allowed only when
  efficiency is part of the public contract; fix it now from the public
  objective and a named realistic baseline, show a fundamentally different
  correct strategy can pass, and keep it more than ~5% from the reference's own
  result unless you record an explicit sign-off. Correctness is checked first.
- **#41/#42/#52/#60:** plan every guard test coupled to a behavioral assertion
  in the same test function; every fail-closed test carries a known-good
  positive control in the same function; each of the #60 shortcuts (empty,
  format-only, hardcoded public answer, self-reported metric, missing artifact,
  fake reward/report incl. a detached writer) has its own named assertion.

## Auditor construction rules (plan them now)

The task is built to clear both the master and the bundled auditor
(`tools/final-tbsci-audit-master/`, gates T and A–K in its `CHECKLIST.md`) from
the first file. `scripts/audit_task.py tree` runs its static screen as a
blocking step of the Step 2b gate, and its judged review of the candidate ZIP
decides promotion at Step 4. Write these into the spec:

- **Verifier image (#54):** `tests/Dockerfile` ends with the master's Appendix A
  step 1 (uid 12000 `sandbox`, `chmod -R go-rwx /tests`, root-owned `/logs/verifier`
  and `/work` at 755).
- **Agent code in the verifier (#54):** if the verifier executes anything the
  agent wrote, it runs it via the Appendix A launcher
  `setpriv --reuid=12000 --regid=12000 --clear-groups --no-new-privs env -i
  PATH=/usr/local/bin:/usr/bin:/bin HOME=/work timeout -k 5 <PER_RUN_LIMIT>`, never as an
  in-process import, and reads its output back as data. State `<PER_RUN_LIMIT>` in
  instruction.md (#57(a)); set the #106(a) thread-count variables on `env -i`.
- **Artifacts are untrusted (#55):** before grading, `test.sh` deletes every artifact
  symlink whose resolved target escapes the artifact paths (in-tree links are kept); every expected-side file is baked into `/tests`.
- **Reward last (#56):** after grading, kill-to-exhaustion (`pkill -9 -u 12000` until
  `pgrep` is empty), then `rm -f /logs/verifier/reward.txt`, then the 0/1 write from
  baked grader logic.
- **CTRF:** pytest writes `--ctrf /logs/verifier/ctrf.json`, loading the
  workspace `tests/ctrf_reporter.py` as a plugin (for example `-p ctrf_reporter`).
- **Assertions:** tests assert values computed from the agent's output against
  independently derived expectations, never constants the agent could echo;
  held-out or regenerated inputs live in the verifier (#46).
- **Output schema (#47):** every key, column and format the tests check is named
  in words in `instruction.md`.
- **`rubric.txt`:** plan it now; `tasks/<slug>/rubric.txt` must exist before the
  Step 2b gate because the auditor screen stages it beside the inner task folder.

Plan the verifier at the manifest level: list the `tests/test_manifest.json`
entries you intend to ship (ID, requirement, one CTRF case each, per
`docs/TESTING_POLICY.md`) in `traceability.md`. Fill the `controls.md` plan
table so each control you intend to run names one of those manifest cases as
its expected failure, with the assertion or failure reason. "Reward 0" is not
a plan. The #60 shortcuts map to NC-01..NC-06/06b.

## task.toml plan (Master #61–#65, #103, #104)

Write the intended `task.toml` into the spec now so nothing is "fixed later"
(template: `docs/TASK_COMPONENTS.md`):

- no top-level `version` key and no `[task]` table (no
  `terminal-bench-science/` namespace, `description`, `authors` or
  `keywords`); `schema_version` is optional;
- top-level `name` = directory slug and top-level `artifacts = [...]`;
- `[metadata]`: `domain` + `field` (exact kebab-case, `docs/TASK_TAXONOMY.md`)
  and a non-empty `subfield`, classified by the scientific expertise
  indispensable to solve the task (#61, #98); 3–6 specific `tags`;
  `expert_time_estimate_hours`; substantive `relevant_experience`; author
  fields (`author_name`, `author_email`, `author_organization`) optional and
  non-empty when present. The retired `category` / `subcategory` /
  `languages` keys are not used;
- the write-ups are **not** task.toml keys: they are
  `authoring/<slug>/write-ups.md`'s `## Difficulty`, `## Reference solution`
  and `## Verification`, never shipped (#103); the task has no README.md;
- **no `difficulty` field**, and no tier word, percentage or pass count anywhere
  in the task or in `write-ups.md` (#62);
- `[agent].timeout_sec = 28800`, `[verifier].timeout_sec = 28800`,
  `[environment].build_timeout_sec = 28800` from creation (#63), matching the
  instruction suffix (#104);
- `[verifier].environment_mode = "separate"`;
- `[environment].network_mode = "public"` and
  `[verifier.environment].network_mode = "no-network"`, both declared; a
  verifier `"allowlist"` with `allowed_hosts` only with the reason recorded in
  `resource-plan.md` (#64). The agent network is never cut to make a task
  hard — a web-lookupable answer is redesigned (#99);
- `cpus`, `memory_mb`, `storage_mb` declared and sized to the task, `gpus = 0`,
  no `gpu_types` (#65);
- no milestone fields, `codebase_size`, `*_min` estimates, generator
  bookkeeping, or real local paths; `is_multi_container = true` only for a
  genuinely multi-container task (#65).

Stop if clarity makes the task trivial, if the answer turns out to be
reachable by web lookup, if the data or ground truth has no defensible
provenance, or if the verifier cannot distinguish genuine work from
public/example hard-coding.
