# Step 1 — Idea generation and seed screen (OPTIONAL)

**This whole step is optional.** The owner normally starts at **Step 2a**
(`prompts/step2a.md`) with their own idea, and Step 2a performs the seed screen
itself. Use Step 1 only when there is no idea yet: to generate candidate ideas
and screen them, so that one `GO` seed is handed to Step 2a. Nothing in Step 1
is a prerequisite for any later gate.

`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth for everything a
task must pass; this step screens candidate ideas against it before anything is
built. Read it (Section J, Master #98–#107, for the science), then
`docs/WORKFLOW.md` Step 1, `docs/reference/WHAT_MAKES_A_GOOD_TASK.md`,
`docs/reference/DIFFICULTY_GUIDELINES.md`, `docs/reference/QUALITY_GUIDELINES.md`,
`docs/TBSCI_HARDENING_RULES.md`, `docs/reference/TBSCI_CAPABILITY_HARDENING_RULES.md`,
`docs/reference/idea-validation.md`, and `docs/TASK_TAXONOMY.md`.

## Generating ideas

Start from real research practice in a field the owner knows, not from the
benchmark: a pipeline stage that is easy to get subtly wrong, an instrument
whose raw data needs domain-aware correction, a numerical method whose naive
form fails on realistic inputs, a model fit whose identifiability depends on
the right parameterisation. Good sources are the owner's own work, a paper's
methods section, or a public dataset whose interesting result is not itself
published. Do not mine upstream benchmark tasks for ideas, and never generate
many candidates to keep only the ones a current model misses — that is the
adversarial filtering upstream `CONTRIBUTING.md` ("Task Difficulty") warns
against.

## Screening

Write `authoring/<slug>/seed-review.md` from `authoring/_templates/seed-review.md`
for each candidate worth screening. The template folds in the seven criteria of
upstream `rubrics/task-proposal.md` — Verifiable, Well-specified, Solvable,
Difficult, Scientifically Grounded & Interesting, Scope, Outcome-verified —
plus domain/field/subfield, data provenance and web-lookup risk. Test the idea
for clarification collapse, public-solution copying, refusal risk, portability,
novelty (not a reskin of an upstream benchmark task, any earlier benchmark
edition or your own tasks), saturation, whether at least two constraints
genuinely interact, and whether a credible expert solution requires at least
five non-clerical terminal commands with intermediate reasoning.

Also answer, in the seed review, the master checks an idea can already fail:

- **Master #98 — taxonomy and scope.** One `domain` and `field` from
  `docs/TASK_TAXONOMY.md` and a `subfield`, chosen by the scientific expertise
  indispensable to solve it. An in-scope method on an out-of-scope subject is
  out of scope.
- **Master #99 — scientific grounding and novelty.** A research-level workflow
  a scientist would be paid to do, needing judgment about what to compute and
  why — not a textbook exercise, course project, or generic coding in
  scientific vocabulary. Name the paper, dataset, pipeline or project it comes
  from. The answer is not reachable by an obvious web lookup or by memorizing a
  published result; agents have open internet.
- **Master #100 — data and ground-truth provenance.** Where the data comes
  from (real: source, version, licence; synthetic: generator) and where the
  graded reference values come from (independent, or oracle-derived and
  disclosed).
- **Master #95 — no manufactured difficulty.** Say in plain language what makes
  the task hard (domain judgment, multi-stage inference with cascading errors,
  real artefacts in the data, edge cases). Obscurity, trick questions,
  tedium/volume, spec transcription, decoys with no fair signal, contradictory
  requirements, compliance walls and tight numbers are not difficulty. Never a
  tier, a percentage or a pass count.
- **Master #0–#11 — the prompt can be written fairly.** An independent domain
  expert could solve it from the instruction alone; every requirement can be
  stated as a "what" in `instruction.md` (#1–#4) without naming each defect's
  mechanism (#10) and without pipeline vocabulary (#5).
- **Master #12 — environment docs are requirements.** If the idea ships docs
  under `environment/`, every one of them will need its own tests. An idea that
  needs a large doc set to be fair is a warning sign; so is one that would need
  a lore or notes file to be solvable (#15).
- **Master #30 — independent correctness.** If the task grades a named
  algorithm, transform, estimator, law or physical model, name the trusted
  external reference (library, paper, hand derivation) you will use to prove
  the reference solution correct.
- **Master #46 / #102 — holdouts that discriminate.** Name the hidden variation
  that changes the graded outcome, and confirm no trivial null (constant,
  centre of the range, majority class, identity) reaches any graded instance.
- **Master #101 — tolerances.** Say what legitimate variation each bound will
  have to absorb, what independent correct implementation it will be measured
  on, and that margins will be taken on the shipped graded instances (no
  fresh-draw study). Where instances come from a generator and a method's
  smallest shipped-set margin is under 20%, the default internal check is 3
  fresh unselected draws (6 only if those 3 are borderline or inconsistent); not running it
  is never a finding.
- **Master #57 — no wall-clock gate.** An idea whose crux is latency,
  throughput or percentile timing is rejected; redesign it around deterministic
  work, bounded memory, or scientific quality.
- **Master #26 / #64 / #106 — portability and network.** No
  architecture-specific artifact without a fallback; the agent always runs with
  `network_mode = "public"`, so an idea that is only hard offline is rejected.
- **The bundled auditor (`tools/final-tbsci-audit-master/`).** The task will be
  screened by it from the first file (`scripts/audit_task.py tree` blocks the
  Step 2b gate) and judged by it at Step 4, so the idea must fit its
  construction rules, which are all master rules: the agent image can sit on a
  canonical `public.ecr.aws/docker/library/<python|node|golang|rust|eclipse-temurin|gcc|ruby|maven|debian|ubuntu>`
  base or has a stated reason why it cannot (#26); anything agent-written the
  verifier must run can be run unprivileged as uid 12000 behind a root-only
  `/tests`, with every expected value baked into `/tests` rather than read from an
  artifact (#54–#56, the master's Appendix); the graded outcome depends on inputs the verifier
  holds out or regenerates (#46); and the output schema can be stated in words
  in `instruction.md` (#47).

Return exactly `GO`, `REDESIGN`, or `REJECT` with reasons for each candidate.
Only a `GO` seed proceeds to Step 2a, which re-reads the seed review and
completes it; do not create task files in this step.
