---
description: Idea validation for Terminal-Bench Science — scientific grounding, taxonomy fit (domain/field/subfield), data provenance, web-lookup risk, anti-trivialization, six strong-task properties, spec output format. Use before creating task files.
alwaysApply: false
---

# Idea Validation (Terminal-Bench Science)

Use `docs/reference/idea-validation.md` explicitly when screening a seed (the owner's own
idea at Step 2a, or a generated idea at the optional Step 1) and writing
`specs/<task>.md`. Not auto-applied.

Source of truth: `MASTER_CHECKLIST_TBSCI.md` (Section J, Master #98–#107, for
the science). Also: `docs/reference/WHAT_MAKES_A_GOOD_TASK.md`,
`docs/reference/DIFFICULTY_GUIDELINES.md`, `docs/TASK_TAXONOMY.md`,
`docs/reference/QUALITY_GUIDELINES.md`, `docs/reference/TBSCI_CAPABILITY_HARDENING_RULES.md`. The seed
criteria fold in upstream `rubrics/task-proposal.md` (Verifiable,
Well-specified, Solvable, Difficult, Scientifically Grounded & Interesting,
Scope, Outcome-verified) — paraphrased, never pasted.

## Reject before drafting

- Not science: generic software, data munging/reformatting, a standard tool
  run with defaults, or a canned statistics/ML fit dressed in scientific
  vocabulary — a competent generalist could do it (Master #99)
- Not research level: a textbook exercise, tutorial, toy problem or
  university course project; standard methods on a well-trodden teaching
  dataset; a closed-form problem (Master #99)
- Out of scope: the subject is outside the five covered domains, or the task
  is shoehorned into a field it does not belong to — an in-scope method on an
  out-of-scope subject is still out of scope (Master #98)
- Web-lookup or memorized answer: the result is a published value, a
  well-known benchmark outcome, or a widely available implementation; agents
  have open internet (Master #64, #99)
- No data provenance: data of unknown origin, a licence that forbids
  redistribution, or reference values with no account of where they came from
  (Master #100)
- Not verifiable: open-ended outputs (hypothesis generation, literature
  review, "draw conclusions") or grading that experts would dispute
- Difficulty only from obscure facts, trick questions, LLM-specific quirks,
  tedium/volume, or a tolerance tighter than the science supports (Master #95,
  #101)
- Process-graded: the grade depends on which tool or method was used rather
  than on the outcome (upstream "Outcome-verified")
- Milestone / multi-stage TB milestone designs
- Stale metadata mindset (any `difficulty` field or tier label, a top-level
  `version`, `allow_internet`, `codebase_size`, the retired TB4
  `category`/`subcategory`/`languages`, write-ups planned as task.toml
  `*_explanation` keys)
- Reskins of an upstream benchmark task, any prior benchmark edition or your
  own earlier tasks
- Single-command or straight-line burst tasks
- GPU-required designs
- Ambiguous or under-specified "gotcha" difficulty, including an unstated
  choice between two defensible conventions (Master #0)
- Public/near-complete deliverable that a constant, the centre of the domain
  or a fixture can satisfy (Master #102)
- Refusal-prone premise that measures model policy instead of capability
- Architecture-specific design without a portable path (Master #26, #106)
- Idea whose difficulty disappears when every necessary requirement is clarified
- Credible expert solution path has fewer than five terminal commands or no
  intermediate reasoning/recovery (clerical splitting does not count)
- Task whose crux requires wall-clock latency/throughput assertions (Master #57)
- Difficulty that is manufactured: obscurity, spec transcription, unfair decoys,
  contradictions, compliance walls (Master #95)
- A design that needs a lore/notes file indexing the defects to be solvable (#15)
- A design that only works if the agent's network is cut — the agent phase is
  always `public` (Master #64)

## Accept signal (TB-Science style)

Prefer ideas that chain: real or realistic scientific data with provenance →
domain judgment about what to compute and why → multi-stage computation where
errors cascade → native scientific artifact → independent verification with
tolerances the science justifies. Constraints should **interact**. The idea
comes from work a scientist would be paid to do on a computer, and you can name
the paper, dataset, pipeline or project it comes from (upstream
`CONTRIBUTING.md` "Task Quality"). Difficulty is well beyond the frontier for a
meaningful reason, never arbitrary or found by filtering many candidates
against today's model (upstream `CONTRIBUTING.md` "Task Difficulty").

## Taxonomy

Exactly one `domain` + `field` (exact kebab-case values from
`docs/TASK_TAXONOMY.md`, `field` listed under `domain`) and a non-empty
free-text `subfield` naming the research specialty — classified by the
scientific expertise indispensable to solve the task, never by tooling or the
fact that code is written (Master #61, #98). No `difficulty` field or tier
label, provisional or final — the measured rate stays in workspace reports
(Master #62).

## Instruction commitment (Step 2a)

Pick a human voice (terse / casual / structured). Reject seeds whose public
prompt would be GPT-style, hint-heavy, or emoji/em-dash decorated. Apply the
expert-solvability bar now: field-standard conventions left out, defensible
alternatives chosen and stated, field-independent choices (paths, schemas,
held-out draws, execution limits) stated (Master #0). The prompt will end with
`You have 28800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.`
(Master #104).

## Spec output (`specs/<task>.md`)

Include at least:

1. **Title / slug** (kebab-case, a name not a sentence; 2–4 tokens typical, Master #61)
2. **Domain / field / subfield / tags (3–6)** (Master #61, #98)
3. **What makes it hard** (Master #95, plain language) + `write-ups.md`
   `## Difficulty` draft (Master #103)
4. **Problem narrative** (domain + crux) and the real workflow it comes from
   (paper, dataset, pipeline or project — Master #99)
5. **Data provenance plan** — real (source, version/DOI or URL, licence,
   preprocessing) or realistic synthetic (generator and parameters); where it
   lives (`environment/data/` or a build-time fetch pinned to an immutable
   revision with a checksum); grader-only data only in the tests image;
   records under `authoring/<task>/provenance/` (Master #100)
6. **Ground-truth plan** — where every graded reference value comes from:
   generating model, cited external value, or a second implementation written
   to cross-check the oracle; or oracle-derived, disclosed, and defended by a
   varied oracle stage (Master #100)
7. **Tolerance-calibration plan** — each bound, what it brackets, the
   legitimate variation it absorbs, the independent correct implementation
   (structurally different from `solution/`) it will be measured on, and the
   defective approach it must separate from (Master #101)
8. **Graded instances and nulls** — each withheld instance and the trivial
   nulls it will be checked against, per instance (Master #102)
9. **Artifacts** list (verifier-visible paths)
10. **Oracle sketch** (how solve.sh derives the result) + `write-ups.md`
    `## Reference solution` draft
11. **Verifier sketch** (semantic axes; separate container notes; how any
    agent-written code is run as uid 12000 via `setpriv` behind a root-only `/tests`,
    artifacts treated as untrusted data and the reward written last, Master #54–#56 and
    the master's Appendix — the bundled auditor `tools/final-tbsci-audit-master/` checks it)
    + `write-ups.md` `## Verification` draft
12. **Triviality ledger** — how agent might cheat; mitigations
13. **Network** — agent `public`, verifier `no-network`, both declared
    (Master #64); web-lookup risk assessed (Master #99)
14. **Timeouts and resources** — agent, verifier and build all `28800`
    (Master #63); `cpus` / `memory_mb` / `storage_mb`, `gpus = 0` (Master #65);
    expert time estimate in hours
15. **Initial draft commitments** — exact files to create in Step 2b
    (no `README.md`; write-ups go in `authoring/<task>/write-ups.md`)
16. **Novelty notes** — why not a reskin, and why not a well-known problem
    with cookbook solutions
17. **Public-solution review** — three likely searches and closest result
18. **Refusal / portability / saturation analysis**
19. **Contract IDs** — public requirement and semantic invariant list; every
    environment doc mapped to a requirement and test (Master #12)
20. **Threat model + negative controls** — the Master #60 shortcuts (NC-01..NC-06b)
    each with its own named assertion
21. **Resource plan** — deterministic baselines/scales/threshold rationale and
    near-Oracle-replication check when relevant; timing only for timeout headroom
22. **Correctness reference** for any named algorithm (Master #30) and the
    holdouts that change the outcome (Master #46)
23. **Optional hint plan** — whether to write `authoring/<task>/hint.md`
    (gentlest-first `## Hint N`; never the answer; Step 3a diagnostic only)

## GO / NO-GO

**GO** only if the work is research-level science in its claimed field, the
data and ground truth have a credible provenance, the answer is not
web-lookupable, novelty is plausible, separate-verifier feasible, the fairness
bar is clear, public copying/refusal/platform collapse is controlled, the idea
remains multi-step with interacting constraints after clarification, and it can
be built to the bundled auditor's construction rules from the first file
(canonical ECR base or a justified exception, #26; unprivileged execution of
agent code, #54; verifier-side holdouts, #46; output schema stated in words, #47).

Pull `docs/reference/TBSCI_REVIEW_BLOCKERS.md` § idea items before GO.
