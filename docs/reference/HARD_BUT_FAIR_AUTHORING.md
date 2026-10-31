# Hard but Fair Authoring (Terminal-Bench Science)

`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth; this page
summarizes its fairness and difficulty checks (Master #0–#11, #12, #57, #95,
#99–#102, #104) and defers to it.

Difficulty must come from the **science**, never from the description, the
data volume or a tolerance.

## Fairness bar

- Everything needed to succeed is obtainable from `instruction.md` + `environment/`
  + standard knowledge in the field. The test (upstream `CONTRIBUTING.md`,
  "instruction.md"; Master #0): an independent domain expert with no access to
  the author could solve it from the instruction alone
  - a convention standard in the field is left out (spelling it out is padding);
  - a choice between two defensible conventions — index origin, sign or
    normalisation of a transform, which standard estimator, units where the
    field uses several, tie-breaking — is stated, or the tests grade a coin flip;
  - anything the field does not determine — output paths, bespoke schemas, a
    held-out input drawn differently from the shipped one, a different runtime
    or limits applied to submitted code — is always stated. Parity needs no
    statement; divergence does, and a partial list of limits implies it is
    complete
- Thresholds need not be published: name every metric that gates the result,
  and withhold the numbers if you wish — but any number the instruction does
  state matches the tests byte for byte (Master #6)
- Tests never require unstated schemas/paths/tolerances (Master #2, #6)
- Every environment doc is a graded requirement with tests (Master #12)
- No lore/notes file indexing the defects; no answer-key module (Master #15, #19)
- Oracle and agent face identical verifier logic
- No planted answers, readable `tests/`/`solution/`, or reward-file shortcuts;
  grader-only data lands only in the tests image (Master #100)
- Deterministic: seeded randomness, no wall-clock flukes, no live web data,
  build-time data pinned to an immutable revision and checksum-verified
  (Master #100, #106)
- Every meaningful verifier assertion maps to an explicit or uniquely derivable
  public requirement; every stated requirement has an independent test
- Equivalent correct artifacts pass after semantic normalization — and an
  alternative valid estimator, discretization or quadrature lands inside the
  tolerance (Master #101)
- Metrics and expected values are independently recomputed from pristine inputs;
  reference values come from an independent source or are disclosed as
  oracle-derived and defended in the write-ups' `## Verification`
  (`authoring/<task>/write-ups.md`, Master #100)
- Persisted state is reloaded before verification

## Hardness bar (TB-Science style)

Prefer research-level workflows that need real domain judgment — interacting
constraints, inferred models, multi-stage pipelines with cascading errors,
native scientific artifacts — over long instruction-following laundry lists
(Master #99). No manufactured difficulty: obscurity, trick questions, spec
transcription, unfair decoys, contradictions, compliance walls, tedium and
tolerances tighter than the science do not count (Master #95, #101). The answer
must not be reachable by obvious web lookup or memorization of a published
result — agents run with open internet (Master #64, #99). See
`docs/reference/WHAT_MAKES_A_GOOD_TASK.md`, `docs/reference/DIFFICULTY_GUIDELINES.md` and
`TBSCI_CAPABILITY_HARDENING_RULES.md`.

## Tolerances and graded instances (Master #101, #102)

Every inequality the tests apply states what it brackets and what legitimate
variation it absorbs (floating point, alternative valid methods,
nondeterminism), and is measured on at least one independent correct
implementation that differs from `solution/` in a structural choice — the
estimator, the statistic, the inversion scheme, the discretization. Classify
every named method as correct or defective; separation must be achieved on the
shipped graded instances (10% margin). No fresh-draw study is required. Where
instances come from a generator and a method's smallest shipped-set margin is
under 20%, the default internal check is 3 fresh unselected draws (6 only if
those 3 are borderline or inconsistent). Not running the probe is never a finding. Score
comparators with the real tests and report the ones that pass as passing. Where
several withheld instances are graded, run the trivial nulls (a constant, the
centre of the range, the majority class, the identity, the public answer
replayed) against each instance separately; every instance is one no null
reaches — a null that reaches an instance is a finding to fix, not something to
disclose and ship.

NOP is only the empty-state control. Master #60 requires format-only output,
public hard-codes, self-reported metrics, missing artifacts, and reward
tampering each to be rejected by its own named assertion; the negative-control
catalogue in `docs/TBSCI_HARDENING_RULES.md` §3 is how that is proven.

## Separate verifier discipline

The agent cannot see tests. That does **not** allow hidden contracts: if a test
checks it, the instruction (or realistic env spec the instruction points at)
must make it discoverable. The Step 3c trajectory audit classifies every trial
against `specification_completeness` and `solution_discoverability` (Master
#107, upstream `rubrics/trial-analysis.toml`); a failure of either is a task
defect fixed at a fresh digest. If the verifier runs code the agent wrote, the
execution contract — a held-out input drawn differently, a different
interpreter or dependency set, limits applied — is part of the specification
and is stated (Master #0).

## Timeout fairness

Do not manufacture difficulty through time pressure. Every task sets
`[agent].timeout_sec`, `[verifier].timeout_sec` and
`[environment].build_timeout_sec` to `28800` from creation (Master #63), and
`instruction.md` ends with the suffix naming the same budget (Master #104), so
a failure is a real rule violation, never the clock running out.

Wall-clock latency/throughput tests are prohibited outright (Master #57). Deterministic score/work
thresholds come from the public objective and realistic baselines, not model
outcomes, and must not require near-replication of Oracle. Refusal,
infrastructure faults, spec gaps, and reward hacks are invalid difficulty
evidence (Master #107: `policy_refusal`, `execution_blocked`,
`specification_completeness`, `unearned_credit`).
