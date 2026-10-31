# Difficulty Guidelines (Terminal-Bench Science)

`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth — Master #62,
#92, #94, #95, #99, #101, #102 and #107 above all — and wins where this page
differs.

Difficulty is **empirical**, not self-assessed, and it is **never written into
the task**. What the measurement is allowed to reward is set by the science:
a task is hard because a research-level workflow is hard to get right, never
because the description, the data volume or a tolerance makes it so.

## What "hard" means in TB-Science

Adapted from upstream `CONTRIBUTING.md` ("Task Difficulty") and
`rubrics/task-proposal.md` ("Difficult"), paraphrased:

- **Well beyond the frontier, for a meaningful reason.** Agents should fail
  the task (reliably or at all) because of real failures — a wrong method, a
  missed artefact in the data, an error that propagates through the pipeline —
  not because of a trap.
- **Never arbitrary, never adversarially filtered.** Do not add complexity
  for its own sake, and do not generate many candidate tasks and keep the ones
  today's best model misses: that finds narrow, model-specific gaps that close
  in the next release. A hard task does not need a complicated instruction or
  a complicated verifier.
- **Judged mainly by human difficulty.** The bar is a task that needs years of
  domain expertise or professional experience (PhD-level in the field) to do
  reliably. If an average undergraduate could finish it in a few days, or it
  reads like a course project (a simple analysis, a textbook algorithm, a
  standard protocol), it is too easy. Work that experts do routinely can still
  qualify when doing it correctly takes that training.
- **No upper bound on expert time.** A task an expert who already knows the
  approach would need many hours to carry out is fine — often a sign of a
  substantive task — provided the length comes from real work, not padding.

Strategies upstream names for genuinely harder tasks, which this workspace
adopts:

1. **Longer horizons with cascading errors** — multi-stage scientific
   pipelines where a mistake in an early stage silently corrupts everything
   downstream and only a domain-aware check catches it.
2. **Richer environments** — real research codebases, instrument data with
   its native formats and artefacts, published analysis frameworks the agent
   must understand rather than call blindly.
3. **Specialized, expert-level knowledge** — the agent must decide *what* to
   compute and *why* (which estimator, which correction, which convention
   the data actually follows), not only how to compute it.
4. **Real research workflows** — drawn from work a scientist would be paid to
   do on a computer, not toy problems or textbook exercises (Master #99).

### What is not difficulty

These never count, however low the measured rate (Master #95, #99, #101;
upstream `rubrics/task-implementation.toml` `difficult`, `novel`,
`essential_difficulty`):

- **Obscure facts and trick questions.** A task solved by knowing one
  specific fact is a trick question, and frontier models likely know the fact
  anyway. A failure mode that exploits an LLM quirk (tokenization-style
  counting) is not interesting unless a well-motivated scientific problem
  genuinely has it.
- **Web lookup or memorization.** Agents run with open internet
  (`[environment].network_mode = "public"`, Master #64). A task whose answer
  is reachable by an obvious search, or that reproduces a well-known
  published result or a widely available implementation, is a design
  defect (Master #99) — never fixed by cutting the network. A fact that helps
  but is non-obvious to find is allowed.
- **Tedium and volume.** Many steps make a task more *likely* to be hard, not
  hard. Large volumes of work that is not fundamentally difficult — clerical
  transcription, many near-identical cases — are contrived instruction
  following.
- **Tolerances tighter than the science.** A bound narrowed until only the
  reference's own pipeline clears it measures agreement with one
  implementation, not command of the problem (Master #101). Precision finer
  than the measurement, the model or the method supports is a finding, not a
  difficulty source.
- **Formatting, units and clerical conventions as the crux.** Getting output
  formatting, coordinate conventions or unit strings exactly right must not be
  where most failures come from (upstream `essential_difficulty`).

## Metric

Five attempts, GPT-5.6 only, `reasoning_effort=xhigh`, via the STB full-fidelity
kit (`scripts/run_step3c_eval.sh`). There is no cross-model requirement, no
predeclared-plus-confirmation split, and no anti-saturation gate.

Raw reward is not enough on its own: an attempt enters the pass count only
after full-trajectory classification under `prompts/step3c.md`
(`VALIDATION.md`'s `VALID_PASS` / `VALID_FAIL` / `FALSE_FAIL_SPEC_GAP` /
`INVALID_PASS_REWARD_HACK` / `INFRA_FAILURE` taxonomy) and against the eight
trial-analysis criteria of Master #107 (see **Trial analysis** below).
Specification gaps, refusals, reward hacks, infrastructure failures, runs with
`exception_info` (Master #92), and missing evidence are excluded. A trial that
is not fidelity-complete is replaced by the next fidelity-complete trial at the
same digest and run config — the five shipped runs are the first five valid
trials in launch order across rounds, none skipped (Master #94 item 1,
`scripts/compose_step3c.py`); a task or verifier defect still needs repair and
a fresh digest. After any rerun the rest of the Master #94 set moves with the
five.

## Where the measured rate lives

- Written as `k/5` in `authoring/<task>/step3c-report.md` and
  `artifacts/difficulty/<task>.md`, and nowhere else in the workspace records.
- At packaging it appears only as `trajectories/SUMMARY.txt`'s reward array.
- **Never in the task.** `task.toml` has no `difficulty` field, and no tier
  label, percentage, pass count or model score appears anywhere in the task
  (Master #62), nor in the workspace write-ups. Their `## Difficulty` section
  (`authoring/<task>/write-ups.md`) is a
  plain-language account of what makes the task hard for an expert and for an
  agent, what the data is, and who does this work (Master #95, #103).

A measured **0/5, 1/5, 2/5 or 3/5** is shippable. A higher rate is reported honestly
and the task is hardened at a fresh digest — a trial is never discarded or
re-rolled because its result is inconvenient. (Upstream aims for frontier
success of roughly 10–20% at release, per `rubrics/task-proposal.md`; this
workspace's measurable bar is the k=5 rule above.) Hardening means adding real
scientific depth — a further pipeline stage, real artefacts in the data, a
held-out instance drawn differently — never tightening a tolerance or adding
volume.

### Retired schemes — history only

Earlier revisions of this workspace wrote a tier into `task.toml`: first
Frontier / Advanced / Core / Base (8 runs across two model families with an
anti-saturation split), then `hard` / `medium` / `easy` / `too easy` read off
the k=5 rate. Both are retired as task fields; do not reintroduce either, or
any three-tier variant. The design guidance below still reads true without the
labels.

## Designing for genuine difficulty (Master #95)

Difficulty comes from how much must be true **simultaneously**, not from
obscurity or volume. Strong signals: a method chosen from domain evidence; a
native scientific artifact; interacting correctness axes; a clear goal with an
unclear path; state carried across pipeline stages; punishing but stated edge
cases. `docs/reference/TBSCI_CAPABILITY_HARDENING_RULES.md` (repo root) catalogs capability
patterns from 22 official TB-Science tasks spanning all 20 scientific fields,
with pinned sources, explicit evidence limits, and local calibration procedures.

### Works
- Infer the model or convention from the data itself (a systematic in the
  instrument record, a non-stationarity, a mislabelled unit that only a domain
  check reveals) rather than from a checklist
- Demand structurally valid native artifacts the field actually uses (a
  catalogue, a fitted model file, a mesh, a proof that checks, a calibrated
  data product), graded on their values
- Add interacting correctness axes: the estimate, its uncertainty, and a
  physical or statistical consistency condition that constrain each other
- Multi-stage pipelines where an early-stage error propagates and is caught
  downstream by an independent check (cascading errors)
- Hidden variations and metamorphic checks: a held-out instance drawn
  differently from the shipped one (stated as such in the instruction,
  Master #0), so a solver specialised to the example fails (Master #46)
- Degenerate or edge-input meaning that isn't the obvious default (a gap in a
  time series, a zero-count bin, a sample below detection) stated explicitly
  rather than left to the agent's judgment call
- Genuine partial-fix ablations: a multi-defect task where a real researcher
  could plausibly stop after fixing only some of the defects, and each
  remaining one fails through its own distinct, named assertion

### Does not work (manufactured difficulty, Master #95)
- Piling unrelated independent requirements
- Ambiguity, under-specification, or contradictory requirements — including an
  unstated choice between two defensible conventions (Master #0)
- Obscure trivia, opaque names, or decoys with no fair signal
- Spec transcription and compliance walls
- Non-determinism (a stochastic task fixes its seeds, Master #106)
- Any wall-clock latency/throughput gate (Master #57)
- A threshold moved just beyond the best model attempt, or set within
  roughly 5% of Oracle/reference performance — this requires Oracle
  replication, not genuine capability
- A tolerance tightened to the reference's own margin instead of what the
  science supports (Master #101)
- Manufactured tolerances or timing races that exist only because the spec
  demands them, with no in-world justification
- An answer that is a published number, a textbook closed form or the output
  of one canned tool call (Master #99)

## Why tasks unexpectedly turn out easy

Measured difficulty diverges from design intent through a small number of
specific collapse patterns far more often than from "the crux just wasn't hard
enough." Check for these explicitly before trusting a k=5 result, and classify
which one (if any) is in play — a passing task and a task nobody classified are
different findings:

- **Literature-lookup collapse.** The scenario, dataset or target value is a
  well-known published result, or a public repository already contains the
  pipeline. The agent finds it or recalls it instead of doing the work
  (Master #99). Use data whose answer is not published, or a realistic
  synthetic variant with recorded provenance (Master #100).
- **Canned-tool collapse.** One standard package call — a default fit, a
  stock pipeline with default parameters — produces an answer inside the
  bounds. The domain judgment the task claims to need was never exercised;
  either the defaults must genuinely fail on this data (and the separation is
  measured, Master #101) or the task is generic work (Master #99).
- **Null-instance collapse.** A constant, the centre of the domain, the mean of
  the prior or the majority class clears one or more graded instances
  (Master #102). The suite does the work of fewer instances than it shows;
  run every trivial null per instance and either move the instance off-centre
  or record it in the write-ups' `## Verification`.
- **Doc-diff collapse.** A repair-style task where every defect corresponds
  1:1 to a sentence in an authoritative doc gets solved fast (field-tested:
  ~9 minutes, 3/3) once the agent frames it as "read the doc, diff the state."
  The hardness has to live in *constructing or deriving* the defect, not in
  transcribing a spec the agent can read verbatim and diff against.
- **Lore/notes leak (Master #15).** An in-fiction notes, history, attempt-log,
  lab-notebook or debug-notes file whose bullets map 1:1 onto the planted
  defects (or onto rubric lines) is an answer index. The telltale is in the
  trajectories: runs pass exactly the axes the notes describe and fail exactly
  the one they don't.
- **Public-budget collapse.** A public per-family work/resource budget plus
  any measurement or introspection tool the agent can run gives a fast
  measure-and-fix loop (field-tested: 4/5 solved in ~20 minutes in one case)
  unless there's a genuine bottleneck the agent cannot discover just by
  measuring. If the agent can run the same instrument the verifier does, the
  task is teaching it where the wall is, not testing whether it can find it.
- **Generator invariant replay gaps.** A task built on generated data needs its
  invariants checked against the *entire* generated artifact, hidden seeds
  included — not spot-checked on a visible prefix. Generators drift late; an
  invariant that's true on the first N items and false past them is both a
  silent correctness hole and a silent difficulty hole, because an agent that
  only checks the visible prefix looks like it succeeded for the wrong reason.
- **Near-oracle traps that fail in the other direction.** A threshold set too
  close to Oracle doesn't make a task harder — many near-misses just show the
  threshold, not the underlying problem, is producing the difficulty.
  Genuinely different correct strategies must still clear the bar; if only
  Oracle-shaped implementations do, the gate is the crux, not the science.
- **Post-hoc thresholds.** A score/work/quality gate calibrated after seeing
  model or reference output — rather than fixed beforehand from the public
  objective, a realistic baseline and an independent correct implementation
  (Master #101) — tends to fit whatever the reference happened to do, not a
  real bar. This reads as principled calibration in a code comment
  ("threshold verified against baseline") but is reverse-engineered from one
  implementation; don't accept the comment at face value, re-derive the
  margin.
- **Measure-and-fix on a self-checkable subset.** If any file the agent can
  read is byte-identical to a file the verifier grades against, that's a
  leaked oracle for whatever fraction of the reward that file covers — the
  agent can iterate against it directly instead of reasoning about the rest.
  Byte-diff `environment/` against `tests/` and `solution/` explicitly; don't
  assume a shared file is harmless without checking what it actually leaks.
  Grader-only data lands only in the tests image (Master #100).

## Measuring locally

```bash
python3 scripts/patch_stb_harbor.py          # once per stb install/upgrade
scripts/run_step3c_eval.sh tasks/<task>      # GPT-5.6 x5 @ xhigh + Oracle x3 / NOP x2; must end "fidelity PASS"
```

A bare `stb harbor run` at default effort with the stock observation cap is
void as difficulty evidence. Fix failures from unclear instructions, env
defects, or flaky tests first — those are bugs, not difficulty.

Wall-clock latency/throughput assertions are prohibited outright (Master #57).
Deterministic score or work thresholds must be fixed before model trials from
the public objective and realistic baselines, must admit different correct
strategies, and must not sit within roughly 5% of the reference without a
recorded sign-off. Numerical tolerances are justified by the science and
measured on at least one independent correct implementation that differs from
`solution/` structurally (Master #101). Moving a gate just beyond the best
model attempt is not hardening.

An optional hinted diagnostic (Step 3a, from `authoring/<task>/hint.md`) can
tell a hard task from a broken one when every trial fails: if a run passes on
a hint that is really missing context, move that context into
`instruction.md` and re-seal. Hinted runs are never difficulty evidence and
never enter Step 3c.

## Trial analysis (Master #107)

Every Step 3c trial — passing and failing — is classified from its full
trajectory against the eight upstream `rubrics/trial-analysis.toml` criteria
and recorded in `authoring/<task>/step3c-report.md`:

| Criterion | Question (paraphrased) | Action when it fails |
|-----------|------------------------|----------------------|
| `specification_completeness` | Were the instruction, public environment and tests aligned and non-misleading for every scientifically defensible solution? | Task defect: state the requirement or relax the test; fresh digest |
| `solution_discoverability` | Could an expert discover a robust passing solution from the instruction, environment, domain knowledge and allowed tools? | Task defect: expose the missing context; fresh digest |
| `verifier_correctness` | Do the tests accept what should pass and reject what should not, against scientifically correct references independent enough of the oracle? | Task defect: fix the reference or test (Master #100); fresh digest |
| `boundary_fairness` | Near the pass boundary, does the bound separate scientific quality rather than equivalent methods, luck or unsupported precision? | Task defect: re-justify and re-measure the tolerance (Master #101); fresh digest |
| `unearned_credit` | Was a pass earned by the intended work, not by exploiting the evaluation or knowing the answer already? | Close the hole (Master #93); a lookup-able answer is a #99 defect |
| `meaningful_difficulty` | Did the outcome turn on scientifically meaningful work rather than procedural or accidental difficulty? | Redesign the crux or rewrite the write-ups' `## Difficulty` |
| `policy_refusal` | Did the agent stop itself on policy grounds rather than after genuine work? | Not difficulty evidence; reframe content |
| `execution_blocked` | Did a configured limit or harness fault stop the trial? | Not difficulty evidence; infra per Master #92 (timeouts are already 28800, Master #63) |

The four task-side criteria (`specification_completeness`,
`solution_discoverability`, `verifier_correctness`, `boundary_fairness`) and
`unearned_credit` are definite send-backs: a task with any of them failing is
fixed at a fresh digest, never shipped.
