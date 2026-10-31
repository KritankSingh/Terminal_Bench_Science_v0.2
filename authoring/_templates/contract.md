# Public contract — <task-name>

Source of truth: `MASTER_CHECKLIST_TBSCI.md` (Master #0–#11, #12, #98,
#99, #104). Read only solver-visible material when constructing this table. Each
requirement is a "what" (#3); a "how"-shaped requirement is allowed only when it
is a genuine interface contract the tests assert (#4) — say which.

## Scientific scope (Master #98, #99)

- Domain / field / subfield (`docs/TASK_TAXONOMY.md`):
- The expertise indispensable to solve it — with the tool names removed, who
  would call this their work:
- The real research workflow, paper, dataset or pipeline it comes from (named
  again in `write-ups.md`):
- Why the answer is not one web search or one remembered published result
  away (the agent has open internet):

## Expert-solvability (Master #0)

Conventions standard in the field that the instruction may leave out, each
choice between two defensible conventions the instruction states, and every
thing the field does not determine (paths, schemas, a held-out input drawn
differently, limits on submitted code) that the instruction states.

| Item | Standard in the field / stated choice / always stated | Where (instruction.md line) |
|---|---|---|

| ID | Requirement | Public source (instruction.md sentence or environment doc) | EXPLICIT/DERIVABLE | Interface contract? (#4) | Semantic invariant | Allowed equivalents | Failure mode |
|---|---|---|---|---|---|---|---|
| R-01 | | | | | | | |

## Stated constants, tolerances and formats (Master #6)

Every number, tolerance, threshold and format the prompt or a doc states, with
the exact literal the tests enforce. The two columns must be byte-identical;
each tolerance also gets its scientific justification in `traceability.md`
(#101).

| Constant | Literal in instruction.md / doc | Literal in tests/ (file:line) |
|---|---|---|

## Closing paragraph (Master #104)

`instruction.md` ends with exactly this paragraph (blank line before, one
newline after); it is not a requirement row and needs no test:

`You have 28800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.`

## Exactness rules (Master #47)

"Exactly these keys", "sorted ascending", "no other fields" — each enforced by
set equality, and satisfied by the reference itself.

## Artifacts and persisted state

Every output path (absolute, #0, #7); the same list becomes top-level
`artifacts` in `task.toml` (#37).

## Protected inputs and preconditions

## Non-requirements

Implementation details and Oracle-specific representations that the verifier
must not enforce.
