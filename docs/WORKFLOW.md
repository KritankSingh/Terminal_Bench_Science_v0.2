# Workflow (five steps)

```
1 Seed ──► 2 Build ──► 3 Check ──► 4 Review ──► [PARKED until CONFIRMED] ──► 5 Trials + package
   seed.md    all files    one command     16-point card                      5 trials, labels, zip
```

A FAIL anywhere: fix the file, run the same command again. Nothing else to redo.
Times are estimates (not measured): 15–20 + 60–90 + 20–40 + 20–30 min, about 2–3 hours per task.

## 1 Seed (`python3 scripts/tbsci.py seed <slug>`)

The first run creates `authoring/<slug>/seed.md`. Fill one page: domain/field/subfield, real workflow,
the crux, data source or generator, upstream overlap check, the naive defaults that must fail, at
least 10 planned tests (one requirement each), `Decision: GO`. Run again until it says PASS.
`docs/reference/idea-validation.md` and `prompts/step1.md` are there if you want depth.

## 2 Build (no command)

Write everything in one go, no stops for checks:

- `tasks/<slug>/`: `instruction.md`, `environment/`, `solution/solve.sh`, `tests/` (test_outputs.py,
  test_manifest.json, test.sh, Dockerfile), `task.toml`, `rubric.txt`.
- `authoring/<slug>/provenance/`: generator, seeds, freeze hash (truth from planted parameters).
- `authoring/<slug>/write-ups.md`: Difficulty, Reference solution, Verification (master #103).
- `authoring/<slug>/calibration.md`: one row per method you ran against the tests:

  | method | class | tests-failed | min-margin-pct |
  |---|---|---|---|
  | independent fit (blind to generator) | correct | none | 24 |
  | linear fit (naive default from seed) | naive | t03 t07 | 0 |
  | constant output | null | t01 t02 t03 ... | 0 |

  `class` is correct, defective, naive or null. A correct method must fail nothing and keep
  >= 10% margin on every bound; every other row must fail at least one test.

`docs/reference/step2b-construction-rules.md` and `HARD_BUT_FAIR_AUTHORING.md` hold the long rules.

## 3 Check (`python3 scripts/tbsci.py check <slug>`, `--no-docker` to skip the Docker stage)

Runs in one go and writes `authoring/<slug>/check-report.md`:

| Stage | Script |
|---|---|
| client rules V1–V4, V14 | `v02_checks.py all` |
| structure and policy | `task_check.py --strict` |
| bundled auditor screen | `audit_task.py tree` |
| oracle passes, NOP fails, in Docker | `dev_verify.sh` (NOT RUN with `--no-docker`, never PASS) |
| calibration | reads `calibration.md` (rules above) |

When the three static stages pass, it writes AUTO into the mechanical master lines
#5 #11 #13 #24 #37 #39 #58 #63 #64 #65 #67 #104. If the task changed since the master record was made, the old record is moved to
`master-checklist.stale.md` and a fresh one is started.

## 4 Review (`python3 scripts/tbsci.py review <slug>`)

The first run creates `authoring/<slug>/review.md` (bound to the task digest). Read the task once,
top to bottom, and give each point PASS, FAIL or N/A plus evidence (`path:line` and the words, or a
line of `check-report.md` / `calibration.md`). The full text of every check is in the master under
its number; open it when a point is unclear. A fresh session for this step is better (advisory).

| # | Point | Master checks |
|---|---|---|
| 1 | Instruction: units and conventions stated, absolute paths, every number matches the tests, no contradictions | #0 #6 #7 #9 |
| 2 | Instruction says what, not how; the crux mechanism is never narrated | #3 #4 #10 |
| 3 | environment/: only needed files, honest names, no hint comments, no lore index, no answer-key helper, fair decoys | #12 #14 #16 #17 #19 #25 |
| 4 | environment/ image: archives clean, pinned and portable | #23 #26 #106 |
| 5 | No file shared between environment/ and tests/ or solution/ except stated inputs | #20 |
| 6 | solution/ stays in scope: every touched file earns its place, no scenario-id branching, no held-out knowledge, no orphans | #27 #28 #29 #31 #32 #34 |
| 7 | Reference verified independently; one-file ablations fail tests; cold build passes | #30 #35 #36 |
| 8 | Tests assert real values, read in full, truth not computed by agent code, schemas literal, no obfuscation or dead code | #43 #44 #45 #47 #49 #50 #59 |
| 9 | Guard tests coupled to behaviour, fail-closed tests have a positive control, hold-outs change the outcome | #41 #42 #46 #52 |
| 10 | Every shortcut (empty, format-only, hard-coded, self-reported, missing artifact, fake reward) rejected by its own assertion | #60 |
| 11 | Verifier seal: deps baked, Appendix A seal copied, artifacts untrusted, reward written last | #38 #54 #55 #56 |
| 12 | task.toml metadata correct; no difficulty or pass rate anywhere | #61 #62 |
| 13 | Rubric lines map to requirements, are satisfiable together, no double counting; a crux line exists | #66 #68 #69 |
| 14 | Science: real workflow, taxonomy right, provenance recorded, truth from planted parameters, no manufactured difficulty | #95 #98 #99 #100 |
| 15 | Nulls fail every graded instance; write-ups present with the three headings; no README.md | #102 #103 |
| 16 | Pre-trial parts: requirement<->test map, no defect-indexing doc, tests fail under NOP by design, test count, no latency assertion, independent method keeps >= 10% margin | #1 #2 #15 #40 #53 #57 #101 |

Run again: each point fills its master lines; point 16 (pre-trial parts) is recorded as
`PENDING | PRE ...` and gets its final verdict after the trials. The run ends with
`master_checklist.py check --stage review`; it must say PASS. If you edit the task after the
review, re-check only the points your fix touched and update the `Task digest:` line.

## 5 Trials + package (parked until `config/round.toml` says CONFIRMED)

1. Five trials on the client's model: `prompts/step3c.md` (engine flow, `run_step3c_eval.sh`).
2. `python3 scripts/tbsci.py labels <slug>`: fill `authoring/<slug>/trials.md` (run, reward, label,
   evidence). A hack-pass or false-fail is a task defect: fix, re-check, re-review, new round.
   Otherwise the band (0–3 legit passes of 5) is judged.
3. Answer the post-trial master lines (#1 #2 #15 #33 #40 #53 #57 #70–#94 #101 #107) from the
   trial evidence (`prompts/step4.md`).
4. `python3 scripts/tbsci.py package <slug> -- <package_task.py args>`: builds the zip, then
   `verify_package.py` and `v02_checks.py zip`.
