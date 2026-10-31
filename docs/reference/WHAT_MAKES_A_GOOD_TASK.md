# What Makes a Good Task (Terminal-Bench Science)

`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth for what a task
must pass; this page is about what makes one worth building.

Terminal-Bench Science asks agents to do a piece of **research-level scientific
computing**: read real or realistic data, decide what to compute and why, run a
multi-stage workflow correctly, and deliver a result that an independent check
confirms — not merely execute a hard terminal chore with scientific vocabulary
attached (Master #98, #99).

## The quality bar

Paraphrased from upstream `CONTRIBUTING.md` ("Task Quality") and
`rubrics/task-proposal.md` ("Scientifically Grounded & Interesting"). A good
TB-Science task is:

- **Drawn from a real research workflow** — a data-analysis pipeline, a
  simulation set-up, a numerical solver, a model fit, instrument-data or
  image/signal processing that a practising researcher builds, runs or debugs.
  Not a toy problem, a textbook exercise, a tutorial or a university course
  project. Ideally you can name the paper, dataset, pipeline or project the
  work comes from (it goes in `authoring/<task>/write-ups.md`, Master #99, #103).
- **Something a scientist would be paid to do on a computer.** Some audience,
  however small, would care about the result.
- **Genuinely in need of domain knowledge.** If a competent generalist could
  solve it with general data and software skills alone — merging and
  reformatting files, running one standard tool, a canned statistics or ML fit
  — it is generic work, whatever the scientific dressing. Judge the work the
  agent does, not the topic.
- **Solvable by an independent domain expert from the instruction alone** —
  conventions standard in the field left out, a choice between defensible
  conventions stated, everything the field does not determine (paths, schemas,
  a held-out input drawn differently) always stated (Master #0).
- **Verified on outcomes, not process** — a solution passes if and only if it
  completes the instruction; the grade never depends on which tool or method
  the agent used (upstream `rubrics/task-proposal.md` "Outcome-verified").
- **Robust across time and hardware** that meets the declared resources:
  pinned stacks, build-time data pinned and checksum-verified, no live
  services (Master #100, #106).

## Strong-task chain

```
real or realistic scientific data (recorded provenance)
        ↓
domain judgment: which model, estimator, correction, convention
        ↓
multi-stage computation (errors cascade between stages)
        ↓
native scientific artifact (catalogue, fit, mesh, proof, data product)
        ↓
independent verification: reference values not produced by solution/,
tolerances the science justifies, held-out instances no null can reach
```

## Six properties

1. **Method inferred** — not a checklist; the right model, correction or
   convention is read off the data and the domain, not handed over.
2. **Output semantics** — native valid artifacts the field uses (a calibrated
   catalogue, a fitted parameter set with uncertainties, a proof that checks,
   a simulation output that obeys its conservation laws). Appearance-only
   must fail.
3. **Multidimensional correctness** — the estimate, its uncertainty, a
   physical or statistical consistency condition, provenance of the result.
4. **Interacting constraints** — axes that affect one another, not a laundry list.
5. **State is part of the problem** — stage outputs feed later stages; an
   early error silently corrupts downstream results.
6. **Hidden checks probe understanding** — held-out instances drawn
   differently (and said to be, Master #0), metamorphic variations, graded
   instances a trivial null cannot reach (Master #46, #102).

## Still disqualifies

Ambiguity, non-determinism, unstated requirements, hidden knowledge the agent
cannot obtain, shortcuts (reading tests, planted answers, fake-passing checks),
manufactured difficulty (Master #95), lore/notes files that index the defects
(Master #15), any wall-clock latency/throughput gate (Master #57), an answer
reachable by obvious web lookup or memorization of a published result
(Master #99), data with no recorded origin or reference values of unstated
provenance (Master #100), tolerances tightened to the reference's margin
(Master #101), and a subject outside the five covered domains or shoehorned
into a field it does not belong to (Master #98). Obscure-fact and trick
questions are not difficulty; neither is tedium or volume
(`docs/reference/DIFFICULTY_GUIDELINES.md`).

TB-Science adds four practical survival tests: the task must not be saturated
after clarification, reducible to a public answer, refusal-prone by framing, or
tied to one architecture/platform. See `docs/TBSCI_HARDENING_RULES.md`.

## Requirements snapshot

| Rule | Notes |
|------|-------|
| Scientific | Research-level workflow needing real domain knowledge (Master #99) |
| Taxonomy | `[metadata] domain` / `field` exact from `docs/TASK_TAXONOMY.md`, free-text `subfield`, by the expertise indispensable to solve it (Master #61, #98) |
| Data | Real or realistic, provenance in `authoring/<task>/provenance/`; ground truth independent or oracle-derived and disclosed (Master #100) |
| Tolerances | Justified by the science, measured on an independent correct implementation (Master #101) |
| Novel | Not a reskin of an upstream benchmark task, a prior benchmark edition or your own tasks; not a well-known problem with cookbook solutions |
| Multi-step | Intermediate state + reacting; "≥5 steps" heuristic |
| Testable | Deterministic final-state verification on outcomes |
| Standalone | No human mid-run input |
| Runtime | `[agent]`, `[verifier]` and build timeouts all 28800s (Master #63); instruction ends with the 28800-second suffix (Master #104) |
| Network | Agent `public` always; verifier `no-network`; both declared (Master #64) |
| Compute | `cpus` / `memory_mb` / `storage_mb` declared, `gpus = 0`; ~2 CPU / 8 GB / 10 GB (Master #65) |
| Write-ups | `## Difficulty` / `## Reference solution` / `## Verification` in the workspace record `authoring/<task>/write-ups.md`; the task carries no README.md (Master #103) |
| No canaries | Training dataset |
| Instruction | AI drafting allowed; expert-solvability bar still applies (Master preamble, #0) |
| Pins | Digest-pinned FROM; numpy/scipy/pandas and domain libraries pinned `==`, apt unpinned (Master #26, #106) |
| Rubric | Local `tasks/<task>/rubric.txt`; Step 4 packages it |

The old Edition 2 "Python must be Hard" rule is **gone**, and there is no
difficulty field or tier label in the task at all, nor in the workspace
write-ups (Master #62, #103).

For this program, the multi-step heuristic is enforced as a credible expert path
of at least five terminal commands plus intermediate reasoning. Wall-clock
latency tests, Oracle/agent-specific verifier logic, runtime data downloads, and
near-Oracle replication thresholds are disallowed; see
`docs/reference/QUALITY_GUIDELINES.md`.
