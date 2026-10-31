# Workspace rules (binding, short)

1. **Frozen master.** Never edit `MASTER_CHECKLIST_TBSCI.md` (version 4; md5 in `FROZEN.md5`,
   checked by `tbsci.py selftest`). The per-task record `authoring/<slug>/master-checklist.md` keeps
   the format `#N | PASS|N/A|AUTO|FAIL|PENDING|NOT VERIFIED | evidence`.
2. **Five steps.** Seed → Build → Check → Review → Trials + package (`docs/WORKFLOW.md`).
   Build the whole task in step 2; do not stop to check each file.
3. **A FAIL:** fix the file, run the same command again. That is all.
4. **Evidence is short but real.** Each review point cites `path:line` plus the words, or a line of
   `check-report.md` / `calibration.md`. Never type command output by hand; `check` captures it.
5. **Never weaken a gate.** Client rules (`docs/V02_RULES.md`) only add checks.
6. **Calibration before review.** One independent correct method keeps >= 10% margin on every
   bound; every naive default from the seed and every null fails at least one test.
7. **Definitions, not methods.** The instruction defines every graded quantity (unit, sign, epoch,
   estimator) and never narrates the crux.
8. **Truth from planted parameters.** Generator and seeds stay in `authoring/<slug>/provenance/`;
   never derive truth from `solution/`.
9. **Hygiene.** No "Master #", step or round tags, digests, dates or `authoring/` paths in
   `tasks/<slug>/` (`check` enforces it).
10. **Trials.** None until `config/round.toml` says CONFIRMED. Five per task. Label every one; a
    hack-pass or false-fail is a task defect and voids the round.
11. **Say what you did not verify.** NOT VERIFIED with what would settle it. It blocks shipping
    like a FAIL.
