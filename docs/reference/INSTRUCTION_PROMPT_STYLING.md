# Instruction Prompt Styling (Terminal-Bench Science)

`MASTER_CHECKLIST_TBSCI.md` Section A (Master #0–#11) plus Master #104 (the
required suffix) are the source of truth for `instruction.md`; this page expands
on them and the master wins where they differ. (The old TB4 portal text in
`docs/archive/tb4-portal/` is an archived TB4 reference, not current guidance.)

Prompts should read like how a researcher hands a problem to a capable colleague —
not like LLM-polished specs. **Vary style task to task.** instruction.md may be
drafted and revised by an AI assistant; human-only authorship is not required
(Master preamble). All scientific, styling and validation requirements still apply.

## Seven principles

1. **Concise** — ~2 short paragraphs or ≤20 bullets as a guide; more room OK when
   complexity requires it (length is Medium severity, not automatic High).
   Extra length from the problem, not step lists.
2. **Well specified** — clear goal; every stated requirement is tested and every
   tested behavior is stated (#1, #2); every constant, tolerance and format
   matches the tests byte for byte (#6); every path exists (#7); schemas are
   checked with the exactness the prose implies (#47); no two sentences
   contradict (#9). Tasks hard only from edge-case laundry lists → reject.
3. **Interesting** — a real research-level scientific workflow that someone in
   the field would be paid to do (Master #99).
4. **No answers / hints** — requirements OK; stepwise how-to and detection guides
   are not (#3). Only genuine interface contracts — paths, flags, exit codes,
   output schemas the tests assert — may be prescriptive (#4). Describe what is
   wrong, never each defect's mechanism or why a naive path fails (#10).
   One-shot user→agent framing.
5. **Unique** — not a reskin of any prior benchmark edition, and not a problem
   whose answer an agent with open internet can look up (Master #99).
6. **Absolute paths** — `/app/...` only.
7. **No canary or GUID-shaped strings** — anywhere in the task (#11).

## The expert-solvability bar (Master #0)

Adapted from upstream `CONTRIBUTING.md` ("instruction.md"): give the instruction,
and nothing else, to an independent domain expert in the task's field who cannot
ask you anything. They must be able to solve it. Everything they need is either
written down or standard knowledge in that field; nothing depends on something
only the author knows. Sort every choice the tests depend on into one of three
bins:

| The choice is… | Then | Examples |
|---|---|---|
| Standard in the field — one accepted convention | **Leave it out.** An expert applies it unprompted; spelling it out is padding and reads as a tutorial | the usual units of a well-established quantity, a textbook definition every practitioner shares |
| Split between two or more defensible conventions | **State which one.** Otherwise the tests reward a guess, and a competent solver who picked the other convention made no real error | index origin, sign or normalisation of a transform, which of several standard estimators, units where the field uses more than one, tie-breaking |
| Not determined by the field at all | **Always state it.** No expertise recovers an author's arbitrary choice | output paths and bespoke schemas, a held-out input drawn differently from the shipped one, a runtime or dependency set other than the agent's, limits applied to submitted code |

**Metrics vs thresholds.** Name every metric that gates the result (an expert aims
to be correct, so they need to know *what* is measured). The numeric thresholds
themselves may be withheld — a researcher handed a problem is not given the
marking scheme. Any threshold the instruction *does* state still matches the tests
byte for byte (#6), and Master #101 still requires every bound to be justified
by the science in the workspace write-ups' `## Verification`
(`authoring/<task>/write-ups.md`).

**Execution-contract divergence.** When the tests run code the agent was asked to
write (a solver, an importable module, a CLI), the agent reasonably assumes it runs
as it did in the environment it was given. Parity needs no sentence; every
divergence does: a held-out input that is a different draw from the same family
(saying so leaks nothing), a different interpreter or pinned dependency set, or
rlimits / a sandbox / resource accounting applied to the submission (the verifier
seal's uid-12000 `timeout -k` launcher counts when it binds a limit the agent could
hit). Beware partial lists: naming some limits of a family implies the list is
complete, so either state the whole family or point to an authoritative spec file
in `environment/` that does (Master #12).

## Required ending (Master #104)

`instruction.md` ends with exactly this paragraph — preceded by a blank line,
followed by a single newline, with N equal to `[agent].timeout_sec` (always 28800,
Master #63). Adopted from upstream `check-instruction-suffix.sh`:

```text
You have 28800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
```

The suffix is required, not padding, and it is exempt from the pipeline-vocabulary
rule below (Master #5). It is the only timeout statement the instruction carries;
do not add a second one elsewhere in the prose.

## No pipeline vocabulary (Master #5)

The prompt never mentions "the grader", "the test suite", "the verifier",
"pytest", `/tests`, `/opt/verifier`, `test_outputs`, a reward file, or any
other pipeline term. Anti-reward-hacking language ("hardcoded outputs will not
pass", "your solution must handle inputs it hasn't seen") is fine, and so is the
Master #104 suffix.

## Voice

- Prefer human tone over "You are an expert…"
- Minimal markdown; no emojis; avoid decorative unicode / em dashes as LLM tells
- Do not name the task inside `instruction.md`
- Use the field's own vocabulary; do not explain what an expert already knows

## Environment docs (no length loophole)

- Env specs define **what** (schemas/protocols), never step-by-step **how**
- Do not split logical instructions into env files to shorten `instruction.md`
- Specs must look like real engineering or lab docs, not polished prompt extensions
- Every environment doc is a graded requirement with its own tests and never
  contradicts `instruction.md` (#12)
- No lore, notes, history or attempt-log file that itemizes the defects (#15)

## Anti-patterns

| Bad | Why |
|-----|-----|
| Step walkthrough with magic constants | Gives the solution |
| "Detection Guidance" sections | Hints |
| Spelling out a convention every expert in the field already applies | Padding; tutorial voice |
| Leaving a two-convention choice unstated | Grades a coin flip (#2) |
| Excessive markdown API catalogs | Spec prose, not human prompt |
| Exact function signatures / build recipes | Over-prescriptive how |
| Bold markers on solution details | Spotlighting answers |
| Missing or reworded timeout suffix | Master #104 failure (mechanical) |

## Sufficiency vs LLMaJ

Brevity never excuses omitting tested requirements.
Every behavior asserted in tests must be recoverable from `instruction.md`
(`behavior_in_task_description`, Master #2). Every stated requirement needs a
test (`behavior_in_tests`, Master #1). Keep the sentence → test map in
`authoring/<task>/traceability.md`.
