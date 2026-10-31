# Terminal-Bench Science — taxonomy

Source: the official TB-Science taxonomy (`harbor-framework/terminal-bench-science`,
`CONTRIBUTING.md` "Task Diversity" and its `tasks/<domain>/<field>/` tree). The workspace
copy with scope notes and example subfields is `docs/TASK_TAXONOMY.md`.
`tools/final-tbsci-audit-master/scripts/tbsci_static_screen.py` (`DOMAINS`, `TAXONOMY`) checks the names mechanically;
this file is what a `category_and_tags` / `scope` finding quotes, and what the fit
judgement is made against.

| Domain | Fields |
|---|---|
| `life-sciences` | `biology`, `ecology`, `medicine`, `neuroscience` |
| `physical-sciences` | `astronomy`, `chemistry`, `materials-science`, `physics` |
| `earth-sciences` | `atmospheric-sciences`, `environmental-sciences`, `geosciences`, `ocean-sciences` |
| `mathematical-sciences` | `applied-mathematics`, `formal-mathematics`, `operations-research`, `statistics` |
| `engineering-sciences` | `chemical-engineering`, `civil-engineering`, `electrical-engineering`, `mechanical-engineering` |

`subfield` is free text (kebab-case recommended), e.g. `single-cell-genomics`,
`data-assimilation`, `powder-diffraction`, `causal-inference`.

## What the screen decides vs. what you decide

- **Screen (mechanical, `TOML-05`):** `domain` is one of the five values, exact
  kebab-case (MAJOR); `field` is one of the four fields listed under that domain
  (MAJOR); `subfield` is a non-empty string (MAJOR). The retired `category` /
  `subcategory` / `languages` keys are residue (MAJOR, `T3-RESIDUE`).
- **You (judgement):** the declared field matches the scientific expertise
  indispensable to solve the task, not incidental tooling, and the task genuinely
  belongs to it (upstream rubric criteria `scope` and `category_and_tags`).

## Fit questions (answer before passing `category_and_tags` / `scope`)

1. What final scientific result does the verifier observe?
2. What domain expertise must a solver exercise after basic repository navigation?
3. With the tool names removed, what would a reviewer in that field call this work?
4. Is the subject itself in the covered sciences, or is an in-scope method (statistics,
   optimization, ML) being applied to an out-of-scope subject?
5. Do `subfield` and `tags` name the real research specialty, methods and data, not decoration?

A mismatch is a `category_and_tags` / `scope` finding (MAJOR) with the field the task
belongs to and the question above that it fails, quoted.
