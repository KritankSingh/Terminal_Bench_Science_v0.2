# Client v0.2 checklist diff (fill when the checklist arrives)

Until this file is filled and every row is closed, `config/round.toml` stays `PARKED`.

1. Paste or link the client's checklist: ____________ (date received: ____).
2. One row per client rule. Mark whether V1–V20 (docs/V02_RULES.md) or the frozen master already
   cover it. A new or stricter rule becomes a new V-rule and, if mechanical, a check in
   `scripts/v02_checks.py` with a selftest scenario.
3. For each parked task, list what has to change. Packaging-only changes (names, zip layout, a
   README emitted from write-ups.md) need a repackage. Any behavioural edit (instruction, tests,
   solution, data, functional task.toml keys) sends the task back to step 3 (check) and step 4 (review).

| Client rule | Covered by (V# / master #) | New or stricter? | Mechanical? | Action |
|---|---|---|---|---|
| | | | | |

| Task | Rules it fails | Packaging-only or behavioural | Review points to redo |
|---|---|---|---|
| | | | |

Confirmed model id: ______  reasoning setting: ______  harness: ______
Then: docs/GPT6_SWITCH.md, `tbsci.py selftest`, set `status = "CONFIRMED"`.
