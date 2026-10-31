# Seed review — <task-name>

Decision: GO | REDESIGN | REJECT

Source of truth: `MASTER_CHECKLIST_TBSCI.md`. Answer every section; the
master checks named below are the ones an idea can already fail. Written at
the start of Step 2a for the owner's own idea (or at the optional Step 1). The
seven proposal criteria fold in upstream `rubrics/task-proposal.md`,
paraphrased: for each, list reasons it holds, reasons it might not, then a
one-line judgement (Strong Reject / Reject / Uncertain / Accept / Strong
Accept).

## Problem statement

The idea restated in your own words: inputs, the scientific question, the
expected outputs.

## Domain, field, subfield, tags

`domain` and `field` exact from `docs/TASK_TAXONOMY.md`, a free-text
`subfield` naming the research specialty, 3–6 specific tags — classified by the
scientific expertise indispensable to solve the task, not by tooling (Master
#61, #98).

## Paid-work outcome and user

Who does this work in the real world, and why someone would care about (or pay
for) the result.

## 1. Verifiable

Concrete, checkable outputs (numerical results, fitted parameters, generated
files, data products) that a program separates correct from incorrect
reliably, repeatably and in a way experts would agree on. No open-ended or
subjective grading (hypothesis generation, literature review). Any
nondeterminism is always verified correctly.

Judgement:

## 2. Well-specified

Two experts reading the instruction would write verifiers that agree. Not hard
mainly because of a mass of corner cases. An independent domain expert could
solve it from the instruction alone: field-standard conventions omitted,
defensible alternatives chosen and stated, field-independent choices stated
(Master #0).

Judgement:

## 3. Solvable

A reference solution will exist, or a compelling argument that one can.
Dependencies, data and compute are realistic and available in a container (no
GPU; `cpus` / `memory_mb` / `storage_mb` sized to the task).

Judgement:

## 4. Difficult (Master #95)

Plain language only — the domain judgment, multi-stage inference with
cascading errors, real artefacts in the data, edge cases. Would it need years
of domain expertise (PhD-level)? Could an average undergraduate finish it in a
few days (too easy)? Not obscure facts, trick questions, LLM quirks,
tedium/volume, spec transcription, unfair decoys, contradictions, compliance
walls or tolerances tighter than the science. Never a tier, percentage or pass
count.

Judgement:

## 5. Scientifically grounded & interesting (Master #99)

A research-level workflow — not a textbook exercise, tutorial, toy problem or
course project, and not generic coding, data munging or a canned fit dressed in
scientific vocabulary. What must the solver decide about *what* to compute and
*why*? Name the paper, dataset, pipeline or project the work comes from.

Judgement:

## 6. Scope (Master #98)

Does the task genuinely belong to the claimed field, and is that field one of
the covered sciences? Judge the actual subject, not the label: an in-scope
method on an out-of-scope subject is out of scope.

Judgement:

## 7. Outcome-verified

Graded on the final result, not on the tools or steps used. Any constraint is
mechanistic and exists only to prevent cheating. Output format
straightforward, not dozens of mandated attributes.

Judgement:

## Data provenance and ground truth (Master #100)

| Dataset / reference value | Real or synthetic | Source (version/DOI/URL, or generator + parameters) | Licence / redistribution | Where it will live (`environment/data/`, build-time fetch, tests image only) |
|---|---|---|---|---|
| | | | | |

Where the graded reference values will come from: generating model, cited
external value, second implementation written to cross-check the oracle — or
oracle-derived, disclosed and defended.

## Web-lookup and memorization risk (Master #99)

Agents have open internet (Master #64). Is the answer a published value, a
well-known benchmark result, a closed form, or a widely available
implementation? Fill the public-solution search below with that question in
mind.

| Query | Closest result | Why copying does not satisfy the task |
|---|---|---|
| | | |
| | | |
| | | |

## Capability crux and interacting constraints

## Multi-step expert path

List a credible path with at least five terminal commands, intermediate state,
and investigation/branching/recovery. Do not add clerical commands to inflate it.

## Clarification-collapse test

Every requirement stated as a "what" (Master #1–#4): does meaningful difficulty
remain, and can the prompt avoid narrating each defect's mechanism (#10)?

## Environment docs and files (Master #12, #15, #19)

Docs you expect to ship under `environment/` (each becomes a graded
requirement), and confirmation that no lore/notes file and no answer-key module
is needed.

## Correctness reference (Master #30)

Named algorithm/estimator/transform/physical model graded, if any, and the
trusted external reference that will prove the reference solution correct — or
`n/a`.

## Holdouts and trivial nulls (Master #46, #102)

Hidden variation that changes the graded outcome, and the trivial nulls
(constant, centre of the range, majority class, identity) that must not reach
any graded instance.

## Tolerances and thresholds (Master #57, #101)

Confirm no wall-clock latency/throughput gate. For each numerical tolerance:
the legitimate variation it must absorb and the independent correct
implementation it will be measured on. Any deterministic score/work threshold:
public objective and realistic baseline it will come from.

## Refusal risk and framing

## Portability and network (Master #26, #64, #106)

Canonical ECR base available, or why not; arch-specific binaries and their
fallback. The agent runs with `network_mode = "public"` and the verifier with
`"no-network"` — the idea must not depend on cutting the agent's network. If
the verifier will run agent-written code: can it run as uid 12000 via the
Appendix `setpriv` launcher behind a root-only `/tests`, with every expected
value baked into `/tests` (#54–#56)?

## Saturation hypothesis and realistic partial solutions

## Novelty comparison

Not a reskin of an upstream benchmark task, any earlier benchmark edition or
your own tasks; not a well-known problem with cookbook solutions.

## Decision rationale

One sentence on the main reason, then the decision above.
