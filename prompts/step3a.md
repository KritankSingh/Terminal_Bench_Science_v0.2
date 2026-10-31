# Step 3a — Optional diagnostics

Step 3a is not a stage. Step 2b's gate (`scripts/gate_step2b.sh`) already runs
the per-test Oracle/NOP matrix, the seal, and (with `--with-nc`) the
negative-control matrix, and Step 3b starts on that sealed evidence. Use this
page only when you have a concrete question about one test, one control, one
artifact, or whether failing model attempts mean "hard" or "broken" — typically a lead from
`python3 scripts/master_checklist.py auto tasks/<task-name>` or
`python3 scripts/audit_task.py tree tasks/<task-name>`, or a
`MASTER_CHECKLIST_TBSCI.md` check you cannot settle by reading. A diagnostic
result is never evidence for a master-checklist verdict by itself; the check
is re-verified on the current digest.

Name the suspect and the hypothesis before running anything (flake, order
dependence, state leak, timeout headroom, wrong named failure, a NOP row that
fails through an error instead of an assertion, "hard or broken?"). Every command
below writes outside `tasks/` and does not change the digest.

First confirm the seal still matches the task:

```bash
source .venv/bin/activate
python3 scripts/evidence.py check tasks/<task-name> \
  --evidence artifacts/gates/<task-name>/step2b.json
```

## One test, repeated

```bash
python3 scripts/per_test_gate.py tasks/<task-name> \
  --only <test-id> \
  --agents oracle,nop \
  --repeat 3 \
  --output artifacts/gates/<task-name>/diagnostic-<test-id>.json
```

Three consistent Oracle `1.0` / NOP `0.0` rows say the test is stable; anything
else is a task defect to fix under Step 2b. Diagnostic reports are not sealed
and do not replace `step2b.json`.

## Negative controls only

After editing a control script under `authoring/<task-name>/staged_controls/`
(a task edit is a different matter, see below):

```bash
scripts/gate_step2b.sh tasks/<task-name> --nc-only
tail -f authoring/<task-name>/evidence/step2b-*/progress
```

This re-stages every control against the current seal and rewrites the
`## Gate results — <digest>` section of `authoring/<task-name>/controls.md`.
Read the failing CTRF case names, not just the reward.

## The bundled auditor's screen

```bash
python3 scripts/audit_task.py tree tasks/<task-name> \
  --json-out artifacts/gates/<task-name>/diagnostic-auditor-tree.json
```

This is the same screen the gate runs as step c1: the task staged in delivery
layout under `tools/final-tbsci-audit-master/scripts/tbsci_static_screen.py`. The
JSON keeps each finding's code, master number, location and hint; use it to
localise a finding or a `LEAD` before you fix it under Step 2b. It is read-only
and does not change the digest.

## Poke at the verifier container

```bash
scripts/dev_verify.sh tasks/<task-name> --keep-image \
  --extra 'ls -la /app/submission; cat /logs/verifier/ctrf.json'
```

The snippet runs inside the verifier container after `tests/test.sh`; use it to
inspect intermediate artifacts or reproduce a single assertion by hand.

## Hinted diagnostic: hard or broken?

When model attempts fail across the board and you cannot tell whether the task
is genuinely hard or actually broken (an unstated requirement, a verifier that
rejects valid work, an environment that blocks the work), a hinted run can
separate the two. The idea is adapted from upstream TB-Science's optional
`authoring/hint.md` (upstream `task-hint-template.md`, `CONTRIBUTING.md`); here
the hints live in the workspace at `authoring/<task-name>/hint.md` (template:
`authoring/_templates/hint.md`), outside the task tree, so they never move the
digest and never ship.

A hinted run is a diagnostic. It **never counts**: it is never a Step 3c trial,
never composed, archived or packaged, never enters any pass rate, and is never
evidence for a master-checklist verdict.

Run it with **local Harbor and your own agent credentials** — never through `stb`
(AGENTS.md rule 2 keeps `stb` and its key budget for Step 3c) — on a staged copy
that carries a **different slug**, never on `tasks/<task-name>` itself:

```bash
H=authoring/<task-name>/hinted/<task-name>-hinted
mkdir -p "$(dirname "$H")" && cp -a tasks/<task-name> "$H"
rm -rf "$H/trajectories" "$H/rubric.txt"
sed -i 's/^name = ".*"/name = "<task-name>-hinted"/' "$H/task.toml"
# paste the chosen "## Hint N" bodies (HTML comments removed) into
# $H/instruction.md as one paragraph just ABOVE the final
# "You have 28800 seconds ..." paragraph, which stays last
harbor run -p "$H" -a <agent> -m <provider/model>
```

`<agent>` / `<provider/model>` are whatever agent you can run locally (for example a
Codex or Claude Code subscription credential, as upstream `CONTRIBUTING.md` describes
under "Run an AI agent"). The different slug and the edited instruction give the copy
its own name and digest, so its jobs can never be mistaken for the task's own
evidence, and no Step 3c tool (composition, archiving, pruning) ever sees it.

Hints go in gentlest first (Hint 1, then 1–2, then 1–3). Read the full
trajectories, not the rewards:

- passes appear once a hint names where the difficulty lives or the approach →
  the task is hard but fair; the unhinted failures are difficulty evidence once
  Step 3c measures them properly;
- failures persist with every hint attached, and the trajectories stop at the
  same unstated rule, verifier rejection or environment block → the task is
  broken; fix it under Step 2b (the hint never becomes the fix — a requirement
  the hints had to state belongs in `instruction.md`);
- a hint that hands over the answer measures nothing; rewrite it.

Record the outcome in a note under `authoring/<task-name>/` if it informs a
Step 2b fix. Delete the staged copy when done; it is not task source.

## Rule

If a diagnostic leads to any edit under `tasks/<task-name>/`, return to the
Step 2b gate: fresh `OUT`, fresh digest, full `scripts/gate_step2b.sh`. Do not
patch `controls.md` by hand to reflect a diagnostic outcome; only the gate
writes the results section. Step 3a has no exit phrase.
