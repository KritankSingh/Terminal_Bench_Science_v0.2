# Task Taxonomy (Terminal-Bench Science)

Every task sets exactly one `domain`, one `field` and one `subfield` under
`[metadata]`. This is the official Terminal-Bench Science (TB-Science) taxonomy:
the five domains and twenty fields below are exactly the `tasks/<domain>/<field>/`
tree of the upstream benchmark (`harbor-framework/terminal-bench-science`,
`CONTRIBUTING.md` → "Task Diversity", verified against its `tasks/` tree and
`tasks/dataset.toml`). `MASTER_CHECKLIST_TBSCI.md` Master #61 and #98 are the
governing checks.

```toml
[metadata]
domain = "physical-sciences"     # exact kebab-case value from the table below
field = "astronomy"              # exact kebab-case value listed under that domain
subfield = "exoplanet-transits"  # free text, kebab-case recommended, never empty
```

Mechanical rules (enforced by `scripts/task_check.py` and the bundled auditor's
`tbsci_static_screen.py`, code `TOML-05`):

- `domain` is one of the five values below, exact case and spelling — otherwise **MAJOR**.
- `field` is one of the four values listed under that domain — otherwise **MAJOR**.
- `subfield` is a non-empty string — otherwise **MAJOR**. It is free text; use
  kebab-case (`single-cell-genomics`, `data-assimilation`). It names the
  research specialty a domain expert would use, not a tool or a programming
  language.
- The retired TB4 keys `category` / `subcategory` (and `languages`) are stale
  residue and are rejected.

Unlike upstream, tasks in this workspace live flat at `tasks/<task-name>/`; the
domain/field come from `task.toml`, not from the folder path.

## How to classify

**Classify by the scientific expertise indispensable to solve the task** — the
knowledge a solver must bring after the computing is stripped away — not by the
tools, the programming language, or the fact that the agent writes code.
Upstream files a task "under the field its *core computational work* belongs
to"; ask:

1. With the tool names removed, what would a reviewer in that discipline call this work?
2. Which expert, handed only the instruction, could solve it — and which could not?
3. Does the task genuinely belong to that field, or is it shoehorned in? An
   in-scope method (statistics, optimization, simulation, ML) applied to an
   out-of-scope subject is still out of scope (upstream rubric `scope`).

Cross-cutting work routes by dominant content (upstream example — nuclear:
neutronics → `physics`, thermal-hydraulics → `mechanical-engineering`, fuel
cycle → `chemical-engineering`). `chemical-engineering` is process, reactor and
transport at scale; `physical-sciences/chemistry` is molecular science. If a task
spans two fields, pick the one whose domain knowledge is indispensable.

**Fields are broad umbrellas.** The slug is shorter than what it covers; the
"Umbrella" column gives the full name (upstream `CONTRIBUTING.md`).

## Domains

### `life-sciences`
Living systems, health and the brain.

| Field | Umbrella | Scope | Example subfields |
|-------|----------|-------|-------------------|
| `biology` | Biology & Biotechnology | Bioimaging, genomics, molecular/cell biology, synthetic biology | `single-cell-genomics`, `epigenomics`, `cancer-genomics`, `protein-engineering`, `cell-biology`, `antimicrobial-resistance` |
| `ecology` | Ecology & Evolutionary Biology | Populations, biodiversity, phylogenetics, population genetics | `population-monitoring`, `phylogenetics`, `species-distribution-modeling` |
| `medicine` | Medicine & Health Sciences | Clinical data, medical imaging, epidemiology, public health, pathology | `radiology`, `clinical-transcriptomics`, `computational-pathology`, `spatial-proteomics`, `epidemiology` |
| `neuroscience` | Neuroscience & Cognitive Science | Neuroimaging, electrophysiology, psychophysics, behavior and cognitive modeling | `eeg-event-related-potentials`, `cognitive-modeling`, `mri-harmonization`, `quantitative-susceptibility-mapping` |

### `physical-sciences`
Matter, energy and the universe.

| Field | Umbrella | Scope | Example subfields |
|-------|----------|-------|-------------------|
| `astronomy` | Astronomy & Astrophysics | Cosmology, instrumentation, time-domain and planetary astronomy, astrodynamics | `cosmology`, `exoplanet-transit-vetting`, `astrodynamics`, `stellar-variability` |
| `chemistry` | Chemistry | Molecular structure, spectroscopy, cheminformatics, docking, reactivity | `cheminformatics`, `molecular-docking`, `spectroscopy`, `computational-chemistry` |
| `materials-science` | Materials Science & Engineering | Characterization, crystallography, diffraction, computational materials, mechanics of materials | `powder-diffraction`, `crystallography`, `nanoindentation`, `fracture-mechanics` |
| `physics` | Physics | Condensed matter, statistical physics, optics and photonics, computational physics | `statistical-physics`, `computational-condensed-matter`, `integrated-photonics`, `computational-lithography` |

### `earth-sciences`
The planet's solid earth, water, air and environment.

| Field | Umbrella | Scope | Example subfields |
|-------|----------|-------|-------------------|
| `atmospheric-sciences` | Atmospheric & Climate Sciences | Climate modeling, meteorology, data assimilation | `data-assimilation`, `climate-modeling`, `numerical-weather-prediction` |
| `environmental-sciences` | Environmental & Sustainability Sciences | Pollution, contaminant transport, energy systems, land use | `contaminant-hydrogeology`, `air-quality`, `life-cycle-assessment` |
| `geosciences` | Geosciences & Planetary Science | Seismology, hydrology, glaciology, geodesy, remote sensing, planetary science | `hydrology`, `glaciology`, `geodesy`, `seismology`, `cryosphere` |
| `ocean-sciences` | Ocean & Marine Sciences | Physical and biological oceanography, coupled ocean models | `physical-oceanography`, `conservative-remapping`, `marine-biogeochemistry` |

### `mathematical-sciences`
Mathematics, statistics and optimization as research disciplines.

| Field | Umbrella | Scope | Example subfields |
|-------|----------|-------|-------------------|
| `applied-mathematics` | Applied Mathematics & Scientific Computing | Numerics, PDEs, numerical linear algebra, coding theory, HPC | `numerical-pde-solvers`, `numerical-linear-algebra`, `coding-theory`, `hyperbolic-conservation-laws` |
| `formal-mathematics` | Formal Mathematics & Theorem Proving | Lean / Coq / Isabelle proofs, autoformalization | `autoformalization`, `formal-theorem-proving` |
| `operations-research` | Operations Research & Optimization | Convex and combinatorial optimization, scheduling, routing, game theory | `mixed-integer-optimization`, `vehicle-routing`, `derivative-free-optimization`, `game-theory` |
| `statistics` | Statistics & Machine Learning | Inference, ML methods, probabilistic modeling, survey statistics | `causal-inference`, `small-area-estimation`, `symbolic-regression`, `bayesian-inference` |

### `engineering-sciences`
Engineering research disciplines.

| Field | Umbrella | Scope | Example subfields |
|-------|----------|-------|-------------------|
| `chemical-engineering` | Chemical & Biomolecular Engineering | Process control, reactors, transport, energy, bioprocessing | `process-control`, `reactor-design`, `separation-processes` |
| `civil-engineering` | Civil & Structural Engineering | Structural, geotechnical and transportation engineering | `structural-health-monitoring`, `geotechnical-engineering`, `traffic-engineering` |
| `electrical-engineering` | Electrical & Computer Engineering | Computer hardware, signals, control, power, robotics sensing | `computer-architecture`, `signal-processing`, `sensor-calibration`, `power-systems` |
| `mechanical-engineering` | Mechanical & Aerospace Engineering | Aerospace, robotics, thermofluids, solid mechanics, nondestructive evaluation | `solid-mechanics`, `guided-wave-nde`, `task-and-motion-planning`, `computational-fluid-dynamics` |

Example subfields are drawn from the kinds of subfields the official TB-Science
tasks use; they are suggestions, not an allowlist.

## Out of scope

General software engineering, systems administration, security, finance and
business operations, media and other non-science work have no home in this
taxonomy. A task whose real subject is one of those is out of scope even if it
uses scientific vocabulary (upstream rubric `scientifically_grounded`: "generic
coding or data-munging dressed in scientific vocabulary").
