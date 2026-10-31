# Lessons from the first 7 tasks (v0.1 round, GPT-5.6 xhigh, 120 runs)

Source: TBSCI_Trajectory_and_Revision_Analysis (2026-10-30) and its re-check. Each lesson names
the step or review point that now guards it.

## The 10 failure classes and where they are caught now

| Class | Tasks hit | Example | Guarded in |
|---|---|---|---|
| C6 Delivery hygiene | 7/7 | `trials_dir` with `-r5`, "Master #58(c)" in a comment | check (hygiene), package |
| C1 Tolerance / boundary fairness | 6/7 | catalyst order window 3% from a correct fit; tide SE margin 1.8% | calibration.md, R16 |
| C2 Unstated convention | 5/7 | tide nodal phase, ML vs REML | R1 |
| C10 Infra / process loss | 5/7 | shared key exhausted; broad pkill | trials rules |
| C3 Generator/truth/instruction disagree | 4/7 | embankment load timing; induced grid | R14 |
| C4 Null / shortcut in the verifier | 4/7 | induced round constants earned reward 1 | calibration.md (nulls), R11 |
| C5 Rubric defects | 4/7 | no crux line; negatives never fired | R13 |
| C7 Verifier seal scaffolding | 3/7 | unpinned verifier deps | R11 |
| C8 Difficulty swings | 3/7 | deletion 4 passes then 0/5 | seed (naive defaults), calibration.md |
| C9 Provenance / independence | 3/7 + all self-reviewed | tdm lost generator | R14, fresh reviewer (advisory) |

Why one late edit is so expensive: any behavioural edit moves the digest and voids the gate, the
review, the master record, the five trials and the package. Two comment lines in solution/ cost
embankment a full re-gate and five paid trials. The check and review steps exist to catch these before any paid trial.

## How GPT-5.6 failed (and what current models lack)

| Mode | What the run did | Example |
|---|---|---|
| F1 Simplest model, never tested outside the fit | straight line; squared denominator | deletion 5/5; catalyst t5 dropped its own correct fit "for parsimony" |
| F2 Wrong mechanism for the residual | gap called secondary compression | embankment 5/5 |
| F3 Skipped a check it said it needed | wrote "needs a likelihood comparison", then did not | induced t5 |
| F4 Replaced fits by round "generator" numbers | Vmax 900, Km 1.8 | tdm t4 |
| F5 Incomplete exception screening | 0 of 5 contaminating cells found in 25 attempts | kv |
| F6 Mis-dated structural breaks | onset 2003 vs 1997 | tide t1 |
| F7 Biased joint fit | one data type biased the other | embankment t2/t5 |

Runs took a median of 9 minutes and 16 steps out of 480 minutes. Passing runs did not work longer;
they did the one comparison or diagnostic the task hid behind a default. What the models lack is
scientific scepticism: they stop at the first plausible answer.

## Design lessons for new tasks

- One lever controlling every graded output swings a task from too easy to 0/5 in one edit. Use
  several independent decisions so different runs fail in different places (induced: 5–14 of 14).
- Five trials are noisy: the same task gave 0/5 and 2/5 after a comment-only edit. A 0/5 is
  consistent with a true rate up to ~43%; it proves neither "hard" nor "broken". Solvability is
  shown offline (blind independent solution, hinted run), not by the pass count.
- Since 0/5 ships, the difficulty gate never catches a broken task. Only quality checks do.
- Vary the skill across tasks: the first 7 all tested "do not accept the default".
