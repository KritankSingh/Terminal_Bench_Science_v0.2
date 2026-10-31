# Step 2 — Build the task (lean)

Write every task file in one go, then run the checks once. No per-file sealing.

1. Read `authoring/<slug>/seed.md` (crux, naive defaults, planned tests).
2. Write `tasks/<slug>/`: instruction.md, environment/, solution/solve.sh, tests/ (test_outputs.py,
   test_manifest.json, test.sh, Dockerfile), task.toml, rubric.txt.
3. Write `authoring/<slug>/provenance/` (generator, seeds, freeze hash), `write-ups.md`
   (Difficulty, Reference solution, Verification) and `calibration.md` (docs/WORKFLOW.md, step 2).
4. Run `python3 scripts/tbsci.py check <slug>`. Fix every FAIL and run it again until all stages
   pass (Docker stage PASS, or NOT RUN only if Docker is truly unavailable; say so).
5. Go to step 4: `python3 scripts/tbsci.py review <slug>`.

Rules that cost the most last time (docs/LESSONS.md): define every graded quantity (unit, sign,
epoch, estimator); never narrate the crux; truth from planted parameters; hold-outs off round
values; a correct independent method keeps >= 10% margin; each naive default fails a test; the
rubric has a crux line; no checklist or round tags in shipped files.

Long construction rules, if needed: `docs/reference/step2b-construction-rules.md`.
