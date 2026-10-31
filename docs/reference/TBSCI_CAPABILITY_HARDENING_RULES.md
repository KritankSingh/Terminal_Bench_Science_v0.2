# TB-Science Capability Hardening Rules

This guide helps turn an original scientific task into a stronger test of research
judgment. Its evidence base is **Terminal-Bench Science**, reviewed on **2026-10-06**,
starting from the [official Harbor Hub task catalog][hub]. It replaces the previous
Terminal-Bench 4.0 capability study completely.

**Authority:** [MASTER_CHECKLIST_TBSCI.md](MASTER_CHECKLIST_TBSCI.md) >
[delivery checklist](docs/reference/DELIVERY_CHECKLIST.md) >
[package rules](docs/reference/PACKAGE_RULES.md) > this guide. The recommendations below add
no gate and waive no master check. Use them within the
[authoring workflow](docs/WORKFLOW.md), alongside the
[hardening rules](docs/TBSCI_HARDENING_RULES.md) and
[hard-but-fair guidance](HARD_BUT_FAIR_AUTHORING.md).

The design target is a scientific distinction: **a plausible incomplete method
fails for a scientific reason, while structurally different correct methods
succeed.** More files, longer instructions, more compute, and tighter tolerances
do not establish that distinction. A lower model success rate alone does not
establish it either.

## 1. How to use this guide

Start at Step 2a with your own research problem. For an existing task, start by
reading its actual solution, assertions, calibration evidence, and any captured
trajectories.

1. Name the research decision and the expertise indispensable to making it.
   Use the [official local taxonomy](docs/TASK_TAXONOMY.md), not a tooling category
   (Master #98, #99).
2. Name the simplest plausible method that currently succeeds without resolving
   that decision. Measure it before proposing a change.
3. Choose one relevant pattern from the evidence map and rules below. Write the
   scientific reason it belongs in this workflow.
4. State what new information lets an expert solve the harder problem. If the
   answer is not identifiable from that information, redesign the task.
5. Plan a named assertion, a targeted incomplete solution, an independent correct
   implementation, and a per-instance null check. Use the existing authoring
   records; do not create a second checklist.
6. Measure the separation using the actual verifier before model trials. A
   credible incomplete method that still passes is useful evidence: either accept
   it as a valid solution or redesign the scientific problem.
7. Run the existing gate, independent review, and frozen difficulty evaluation.
   Interpret every outcome causally before deciding whether the change helped.

The rule IDs `SCI-01`–`SCI-14` are navigation aids, **not new requirements or
task metadata**. Select the ones that serve the research objective. Do not try
to maximize the number of rules used.

## 2. Evidence base and limits

### Snapshot identity

| Item | Verified snapshot |
|---|---|
| Requested catalog | `terminal-bench-science/terminal-bench-science@latest` on [Harbor Hub][hub] |
| Hub resolution at access | Dataset revision **10**, package version **7.0.1**, tagged `latest`, `0.1.0` and `v0.1` |
| Catalog inventory | **70** available tasks; task-name set checked against the release tree |
| Versioned source used here | GitHub release tag [`v0.1.0`][release], commit `f81afac4f11048e77a15dfc8fb1dbfb897fea0ce` |
| Source selection | **22 tasks**, covering every one of the **20 fields** |
| Primary material inspected | Public instruction and README sections for those tasks; selected assertion bodies in five task verifiers |
| Additional guidance | Upstream [implementation criteria][implementation] and [trial-analysis criteria][trial-analysis] |
| Execution evidence produced by this review | **None**: no upstream container runs or model-trial reproductions |

The task inventory was obtained from the Hub's [tasks response][hub-tasks], not
inferred from the README's headline count. The Hub revision/version and GitHub
tag/commit are different identifiers. **Matching names does not establish
byte-for-byte identity between Hub task revisions and GitHub files.** All
task-design citations below use the pinned GitHub commit; none asserts that a
later `latest` revision has the same contents.

| Domain | Tasks in the 70-task inventory | Fields | Tasks selected for this guide |
|---|---:|---:|---:|
| `life-sciences` | 19 | 4 | 5 |
| `physical-sciences` | 17 | 4 | 4 |
| `earth-sciences` | 8 | 4 | 4 |
| `mathematical-sciences` | 17 | 4 | 5 |
| `engineering-sciences` | 9 | 4 | 4 |
| **Total** | **70** | **20** | **22** |

Coverage is deliberately bounded. Instructions and README sections were inspected
for their scientific contracts and stated verification designs, with excerpts
used for long files. This is not an exhaustive audit of all 70 tasks, every file
in the selected tasks, or the correctness of their scientific claims.

Evidence labels used in this guide:

- **S — source observation:** a cited instruction, README, or assertion contains
  the described contract or check. A README's account of calibration remains the
  author's report, not an independently reproduced result.
- **I — inference:** an explanation of the capability a design may exercise.
- **R — recommendation:** an authoring transformation proposed for this workspace.
  Its value must be measured on the new task.
- **O — observed local outcome:** reserve this for a command result or a full
  trajectory at a recorded local task digest. This guide contains no new O claims.

There is no model failure census here, no claimed GPT-5.6 weakness inferred from
task names, and no predicted success rate for these recommendations. Neither a
published task nor its README proves that a pattern causes model failures.

### What transfers, and what does not

Official examples are scientific evidence, not permission to copy their entire
design. Some source conventions conflict with this workspace.

| Source feature | Transfer to this workspace |
|---|---|
| Coupled inference, physical validation, meaningful holdouts, uncertainty, certificates | Adapt the scientific principle using original data and an original task (Master #30, #46, #59, #99–#102). |
| Waveguide runtime ratio; hydrology optimizer wall-time condition | Do **not** adopt these speed gates. Master #57 bans wall-clock latency, throughput, and percentile-latency assertions, including relative-to-reference timing. |
| Reactor batch time | This is **simulated physical process time**, not the host's execution time. It can be an outcome metric when justified; the source's numerical margins are not imported. |
| Reference-relative score or certificate-size caps | Do not reuse source thresholds. Master #57 requires a public objective, realistic baseline, alternative correct strategy, pre-trial calibration, and recorded sign-off for a threshold within roughly 5% of reference performance. |
| Source-specific partial scoring, resource limits, tool restrictions, schemas, or sandbox conventions | Use local binary reward, resources, execution contract, and verifier seal. No automatic adoption (Master #0–#4, #37–#39, #54–#58, #61–#65). |
| Published theorem formalization | Transfer statement integrity and kernel verification. A local task must independently clear novelty and public-answer review; a known result with a copyable solution does not qualify (Master #99). |
| Upstream publication fields, canaries, proposals, task paths | Follow the local personal-use format. No canary, proposal process, upstream submission, or Hub publishing. |

[Waveguide source][waveguide] · [Hydrology source][hbv] ·
[Reactor source][reactor] · [Certificate source][certificate] ·
[Formal-proof source][formal]. These distinctions supplement the recorded
decisions in [TBSCI_REVAMP.md](the v4 workspace's TBSCI_REVAMP notes (not carried here)).

## 3. Scientific evidence map

The **S** column reports source design, not an observed model failure. The **R**
column is this guide's proposed transfer. Each task link opens its pinned README;
the matching instruction links are provided in Section 11. Field names follow
the local canonical taxonomy even where an upstream metadata value uses spaces.

### Life sciences

| Field / source task | S: scientific work and stated verification | R: reusable hardening direction |
|---|---|---|
| `biology` — [ambient-rna-correction][ambient] | Removes ambient contamination while preserving native biological variation; checks correction, burden estimates, batches, and rare-cell signal. | Make nuisance removal compete with preservation of real signal; reject both copy-through and indiscriminate subtraction (SCI-03, SCI-04). |
| `biology` — [protein-active-learning][protein] | Selects successive assay batches and ranks unseen variants with more mutations; documents transcript checks and ranking metrics. | Make each experiment inform a later choice; evaluate transfer beyond the assayed combinations (SCI-05, SCI-09). |
| `ecology` — [animal-reid][animal] | Groups known and unseen individuals; evaluates partitions independently of label spelling and also checks abundance. | Require discovery as well as matching; combine individual-level consistency with population-level validity (SCI-04, SCI-08). |
| `medicine` — [clinical-metadata-recovery][clinical] | Infers annotations across heterogeneous cohorts, including batch confounding and a cohort without local labels; documents cohort-specific balanced metrics. | Break accidental study-label correlations while retaining observable biological signal; inspect each transfer regime (SCI-03, SCI-05). |
| `neuroscience` — [eeg-erp-recovery][eeg] | Connects acquisition QC and event alignment to recovered ERP features and waveforms; discusses convention-sensitive alternatives. | Couple acquisition diagnosis to downstream estimates, while explicitly resolving defensible aggregation and timing conventions (SCI-02, SCI-13). |

### Physical sciences

| Field / source task | S: scientific work and stated verification | R: reusable hardening direction |
|---|---|---|
| `astronomy` — [cmb-cross-inference][cmb] | Links map-derived spectra, likelihoods, parameter estimates, posterior samples, and a model extension for stressed observations. | Check both scientific inference and consistency across its products; an attractive summary cannot substitute for valid samples or predictions (SCI-04, SCI-06, SCI-10). |
| `chemistry` — [rdkit-ic-constraints][chemistry] | Combines geometric restraints, stereochemistry, ambiguous constraints, and conformer diversity; evaluates constraints rather than one coordinate solution. | Accept the feasible equivalence class; distinguish a contradiction certificate from an unsuccessful search (SCI-08, SCI-10). |
| `materials-science` — [xrd-multiphase-qpa][xrd] | Quantifies mixtures with incomplete phase libraries and amorphous content; checks identification and per-sample composition. | Include scientifically identifiable unknown components and competing explanations for unassigned signal (SCI-02, SCI-04). |
| `physics` — [inverse-waveguide-shape][waveguide] | Recovers a constrained refractive-index profile, then tests its propagated exit field using a separate forward calculation. | Judge an inverse answer through independently predicted observables; retain the physics, omit the runtime gate (SCI-02, SCI-07). |

### Earth sciences

| Field / source task | S: scientific work and stated verification | R: reusable hardening direction |
|---|---|---|
| `atmospheric-sciences` — [sparse-network-assimilation][assimilation] | Jointly estimates a field, trajectory, and sensor timing from partial observations; states a convention fixing the global time origin. | Couple nuisance calibration to state recovery, remove exact gauge ambiguity, and require dynamical and forecast consistency (SCI-02, SCI-03). |
| `environmental-sciences` — [hysteretic-aquifer-control][aquifer] | Links constitutive inference, repeated-incident calibration, forecasts, and intervention under uncertain delivery. | Require a learned local law to remain useful inside a downstream simulator and control decision (SCI-04, SCI-05, SCI-09). |
| `geosciences` — [hbv-calibration-1][hbv] | Calibrates a hydrologic model and reports later-period behavior, with a reusable optimizer interface. | Separate warm-up, calibration, and validation semantics; grade transfer and hydrologic outcomes without a wall-time discriminator (SCI-05, SCI-11). |
| `ocean-sciences` — [masked-spherical-remap][remap] | Combines spherical geometry, conservative transfer, constrained equilibrium, and sensitivity calculations; documents covariance and derivative identities. | Require geometry, budgets, and derivatives to describe the same operator; use representation changes as additional checks (SCI-07, SCI-08). |

### Mathematical sciences

| Field / source task | S: scientific work and stated verification | R: reusable hardening direction |
|---|---|---|
| `applied-mathematics` — [ode-law-discovery][ode] | Discovers compact equations from noisy trajectories; checks new rollouts and the vector field away from the observed curves. | Separate interpolation of observations from discovery of a predictive law; accept equivalent equations (SCI-05, SCI-08, SCI-11). |
| `formal-mathematics` — [finite-free-stam][formal] | Formalizes a fixed theorem; rebuilds source, pins its statement, and checks transitive axioms. | Verify the actual claim and its trusted assumptions; compilation alone is insufficient (SCI-10). |
| `operations-research` — [certified-sparse-regression][certificate] | Requires a candidate optimum and a covering certificate whose bounds are recomputed. | Pair a good solution with independently checkable global validity; choose original instances and justified limits (SCI-10, SCI-11). |
| `operations-research` — [noisy-blackbox-optimization][blackbox] | Allocates objective queries under deterministic noise and evaluates progress over multiple problem structures. | Use trusted informative-query counts when experimental budget is intrinsic; test exploration versus refinement trade-offs (SCI-09, SCI-11). |
| `statistics` — [highdim-mediation-debiasing][mediation] | Composes transported mechanisms and estimates causal functionals with uncertainty; documents regime, coverage, and intervention checks. | Require correct estimands, informative uncertainty, and invariance to irrelevant pairing changes (SCI-05–SCI-07). |

### Engineering sciences

| Field / source task | S: scientific work and stated verification | R: reusable hardening direction |
|---|---|---|
| `chemical-engineering` — [reactor-safety-control][reactor] | Controls a partially observed exothermic process under faults; checks safety, completion, and simulated productivity. | Prevent “do nothing safely” and “finish unsafely” from satisfying the objective; disclose the disturbance envelope (SCI-04, SCI-09). |
| `civil-engineering` — [rolling-shutter-oma][modal] | Infers structural modes and damage from video with acquisition effects and changing excitation; reports one-correction ablations. | Make measurement physics matter to the scientific inference; separate acquisition error from structural change (SCI-03, SCI-13). |
| `electrical-engineering` — [navigation-sensor-calibration][navigation] | Couples spatial, temporal, thermal, and stochastic calibration with fault rejection and pose recovery in survey gaps. | Make calibration earn its value on corrected residuals and reconstructed motion in new sessions (SCI-03, SCI-05, SCI-06). |
| `mechanical-engineering` — [inelastic-constitutive-discovery][constitutive] | Distinguishes confounded material mechanisms and predicts unseen loading histories; also checks physical admissibility. | Use history-dependent protocols that separate mechanisms and test their consequences (SCI-02, SCI-05, SCI-07). |

### Checks corroborated in verifier source

Selected assertion bodies were inspected in addition to the write-ups. These
are static observations, not executed results or endorsements of the complete
upstream verifiers.

| Source | S: inspected assertion behavior | Local lesson |
|---|---|---|
| [Ambient RNA tests][ambient-tests] | `test_batch_fidelity` and `test_rare_marker_fidelity` compute separate truth-relative conditions. | A global improvement can coexist with damage to a scientifically important subgroup. |
| [ODE tests][ode-tests] | `test_stress_rollout_nrmse` integrates submitted expressions; `test_vector_field_error` evaluates a domain grid. | Check a proposed law outside the training trajectory, as well as its submitted predictions. |
| [XRD tests][xrd-tests] | `test_identification` checks missing and spurious components; `test_quantification` evaluates each sample. | Reject compensating errors and unknown-component shortcuts in both directions. |
| [Formal-proof tests][formal-tests] | `test_phase4_kernel_axiom_traversal` follows dependencies of the target theorem and a witness. | A success message is not evidence of a proof under the permitted assumptions. |
| [Reactor tests][reactor-tests] | `test_mean_productivity_ratio` reads batch-time metrics from simulated scenario runs. | Keep domain-time metrics distinct from execution speed; calibrate local margins independently. |

## 4. Scientific hardening rules

### SCI-01 — Preserve a research decision after removing the tool names

**R.** Describe the task without package names, file extensions, or implementation
language. A domain expert should still recognize a research problem: choosing a
measurement model, separating biological signal from nuisance variation,
identifying a mechanism, establishing a numerical result, or designing a useful
intervention.

Write the crux as “To obtain [scientific outcome], the solver must distinguish
[plausible explanations] using [available evidence].” If the remaining work is
only conversion, a stock fit, or transcription, additional schemas will not
repair the scientific scope.

A task may involve extensive programming; that programming should implement a
scientific decision. The expert path must involve investigation and intermediate
reasoning, not five padded terminal commands.

**Evidence:** the cohort-transfer, modal-identification, and constitutive-inference
examples in Section 3. **Validation:** have an independent reviewer name the crux
from the public task, then demonstrate a plausible incomplete method that misses
it. **Master:** #95, #98, #99.

### SCI-02 — Make the answer identifiable; grade the identifiable quantity

**I.** Several source tasks distinguish fitting observed data from identifying
the latent explanation. Extra latent variables can make a problem impossible
rather than harder.

**R.** Before grading a recovered parameter or label, audit exact symmetries,
near-degeneracies, and information content. State any necessary gauge convention.
Where multiple latent answers are observationally equivalent, either add a
realistic discriminating measurement, accept the equivalence class, or grade the
predicted observable instead.

For example, an inverse profile can be graded through a trusted forward model.
If the task also demands the true profile, provide evidence that the observations
identify it to the required accuracy. A low residual alone does not prove that.
Likewise, distinguish “an unknown component is present” from “its identity and
fraction are recoverable.”

**Evidence:** [assimilation][assimilation], [waveguide inversion][waveguide],
[XRD][xrd], and [constitutive discovery][constitutive].
**Validation:** perturb plausible parameter combinations, compare residuals and
target changes, and test a structurally different recovery method. Record
unresolved null directions. **Master:** #0, #2, #30, #95, #101.

### SCI-03 — Couple nuisance estimation to the scientific target

**R.** Introduce a scientifically realistic nuisance that a naive method can
mistake for the target: instrument drift for motion, batch structure for disease,
ambient contamination for expression, or acquisition phase for a physical mode.
Preserve enough calibration, replication, or auxiliary information to separate
them.

The purpose is not to hide units or withhold a convention. Publish the measurement
model and all choices the field does not determine. Leave unknown values and
their diagnosis to the solver. Test the recovered science after nuisance
correction; a plausible calibration table without improved predictions is weak
evidence.

Use correlated nuisances only where the real workflow supports them. Varying
several independent random offsets does not automatically create a meaningful
joint estimation problem.

**Evidence:** [ambient RNA][ambient], [clinical transfer][clinical],
[navigation][navigation], and [modal identification][modal].
**Validation:** an ablation that omits one correction should fail its designated
scientific assertion; an alternative joint estimator should pass.
**Master:** #1–#3, #10, #30, #35, #59, #99–#101.

### SCI-04 — Require complementary scientific outcomes

**R.** Choose a small set of outcomes that rule out different plausible mistakes.
Examples include contamination removal **and** native-signal preservation;
identity grouping **and** abundance; fit **and** physical feasibility; safety
**and** completed production; phase detection **and** quantitative composition.

Each condition needs a scientific purpose, a public requirement, and a targeted
incomplete solution. Correlated restatements of one error are not independent
capabilities. A report, plot, and CSV derived from one number are not three
scientific achievements.

Use aggregate metrics where meaningful, but add justified subgroup or regime
checks when pooling would hide a consequential failure. Do not impose a
per-group bound unsupported by the sample size or measurement noise.

**Evidence:** [ambient RNA][ambient], [animal re-identification][animal],
[XRD][xrd], and [reactor control][reactor].
**Validation:** find examples that satisfy one outcome and violate another; run
them through the intended cases. **Master:** #1, #2, #43, #58–#60, #101, #102.

### SCI-05 — Test transfer that changes the scientific answer

**R.** Choose held-out variation from the task's research claim: new subjects,
cohorts, loading histories, initial states, fault combinations, sensor layouts,
or intervention conditions. State the regime and any departure from the public
inputs. Hide realizations, labels, or parameters, not the existence of the regime.

Audit leakage at the correct scientific unit. Replicate measurements from one
specimen, neighboring frames, or variants sharing a parent can invalidate a
nominal train/test split. Feature scaling, model selection, and tuning must not
use hidden outcomes through an author-side convenience function.

Distinguish two tests:

- **Answer-changing holdout:** a frozen public answer becomes wrong; required by
  Master #46 for every held-out scenario.
- **Metamorphic check:** a known transformation preserves or predictably changes
  the answer. Useful additional evidence, but an invariant relabeling alone does
  not satisfy the answer-changing holdout requirement.

**Evidence:** [protein experiments][protein], [clinical transfer][clinical],
[ODE discovery][ode], [constitutive discovery][constitutive], and
[mediation][mediation].
**Validation:** public-answer replay and per-instance trivial nulls must expose
the intended gap. **Master:** #0, #32, #46, #60, #99, #102.

### SCI-06 — Make uncertainty scientifically informative

**R.** Where uncertainty is part of the research deliverable, grade it alongside
the estimate. Distinguish measurement noise, finite-sample uncertainty, numerical
error, and model inadequacy. Specify the estimand, interval meaning, aggregation
unit, and any choice between defensible statistical conventions.

Coverage by itself rewards arbitrarily wide intervals; narrow intervals by
themselves reward overconfidence. Use justified combinations of bias or error,
coverage, interval width, and uncertainty-to-error calibration over a suitable
fixed ensemble. Account for the sampling variability of the calibration study.

For posterior artifacts, recompute summaries from the submitted samples, check
scores under the declared model, and test whether the samples represent the
requested distribution. Repeated MAP points do not become a posterior because a
summary reports a standard deviation.

**Evidence:** [CMB inference][cmb], [mediation][mediation], and
[navigation calibration][navigation].
**Validation:** include accurate-but-overconfident, inflated-uncertainty, and
fabricated-sample controls where relevant, plus a different valid estimator or
sampler. **Master:** #30, #44, #59, #60, #100, #101.

### SCI-07 — Connect numerical accuracy to physical or mathematical structure

**R.** Check the laws the output must obey: conservation, positivity, boundary
conditions, passivity, covariance under a change of coordinates, or consistency
of derivatives with the underlying operator.

Choose the discretization and norm deliberately. A conserved total can coexist
with an incorrect spatial field; a small residual can coexist with a wrong
boundary condition; a derivative can agree with a bug in the same forward
implementation. Combine structural checks with independently grounded values.

For derivative outputs, suitable checks can include directional finite
differences with a step-size study, adjoint inner-product identities, and
symmetry where the mathematics guarantees it. Do not demand Hessian symmetry
for an object that is not the Hessian of a scalar function.

**Evidence:** [spherical remapping][remap], [waveguide inversion][waveguide],
[constitutive discovery][constitutive], and [assimilation][assimilation].
**Validation:** introduce a specific sign, flux, boundary, or derivative omission
and establish that the named assertion detects it. **Master:** #30, #35,
#44–#46, #59, #101.

### SCI-08 — Accept scientifically equivalent answers

**R.** Define correctness on the appropriate object: a partition rather than its
cluster names, feasible molecular geometry rather than one coordinate array,
a dynamical law rather than one algebraic spelling, or a mode shape modulo
its permitted phase and scale.

Normalize only genuine symmetries. A rigid rotation can preserve a molecular
conformation; a reflection may change chirality. A change of units is acceptable
only under the declared interface. Preserve literal schema exactness wherever
the public contract requires it (Master #47).

Do not grade unidentifiable latent labels or demand the oracle's basis,
optimizer, clustering method, quadrature, or intermediate representation.
Algorithm requirements need a scientific or interface reason, not an authoring
convenience.

**Evidence:** [animal partitions][animal], [molecular restraints][chemistry],
[ODE equations][ode], and [remapping covariance][remap].
**Validation:** create a valid alternative representation that must pass and a
nearby scientifically different object that must fail.
**Master:** #2–#4, #30, #47, #95, #101.

### SCI-09 — Make experiments and controls depend on available information

**R.** Use sequential decisions when the workflow naturally contains them:
selecting assays, choosing observations, allocating evaluations, or controlling
a partially observed process. Define the observation/action interface, cost,
reset behavior, and allowed information.

Grade the resulting science or intervention with trusted state. Keep hidden
future disturbances, truth, and scenario identifiers out of the decision
interface. A submitted controller should not earn credit by knowing which
private case is running. A reported assay history should not be trusted without
an authoritative record.

Separate adaptation from a ritual requirement to be adaptive. If a fixed design
achieves every legitimate outcome, it is a valid solution unless adaptive
behavior itself is a justified public requirement. To measure the value of
adaptation, design realistic conditions where fixed decisions are insufficient.

**Evidence:** [protein active learning][protein], [noisy optimization][blackbox],
[reactor control][reactor], and [aquifer control][aquifer].
**Validation:** compare fixed, open-loop, and adaptive strategies; test reset and
information boundaries. **Master:** #2–#4, #32, #44, #54–#60, #99, #102.

### SCI-10 — Require evidence that can be checked independently

**R.** Where the research claim needs a certificate, request one that a trusted
checker can validate. Examples include a proof term, a feasible solution with
valid global bounds, a model plus reproducible predictions, or chains plus
linked posterior summaries.

Recompute the claim. A submitted lower bound is not a certificate unless its
validity and coverage are checked. A compiled theorem is not the intended proof
unless the statement, definitions, and transitive assumptions are preserved.
A fit report is not evidence unless its metrics follow from the submitted model
and trusted inputs.

Keep trusted checking smaller and more independently defensible than the search
procedure where possible. Certificate complexity can be a legitimate research
objective; arbitrary formatting constraints cannot substitute for soundness.

**Evidence:** [sparse-regression certification][certificate],
[formal proof][formal], and [CMB artifacts][cmb].
**Validation:** reject a strong candidate with a false certificate, and accept a
different correct certificate. **Master:** #30, #44, #54–#60, #95, #100, #101.

### SCI-11 — Harden computational reasoning without making the computer the obstacle

**R.** Favor problems that benefit from scientific structure: sparse operators,
stable formulations, conditional independence, reduced models, informative
experiment selection, or reusable computations. Keep the data and runtime within
the local CPU, memory, storage, and timeout contract.

A deterministic budget is justified only when it expresses the research problem.
An informative-query limit can model assay cost; certificate size can model
checkability; symbolic complexity can express interpretability. Count work in a
trusted evaluator. Self-reported iteration counts, timing, or operation counts
are not evidence.

Do not simply increase dimensions until an ordinary implementation times out.
Do not forbid standard scientific libraries to force busywork. A method-development
task may need an interface restriction, but its necessity and fairness must be
defensible under Master #3 and #95.

**Evidence:** [ODE discovery][ode], [black-box optimization][blackbox],
[certification][certificate], and [hydrologic calibration][hbv].
**Validation:** show correctness first, alternative correct strategies, a
realistic incomplete baseline, and pre-trial margins.
**Master:** #3, #57, #63, #65, #95, #101, #106.

### SCI-12 — Calibrate the acceptance region independently

**R.** Separate three questions: where truth came from, how much correct
implementations vary, and which scientific defect a bound detects. Oracle
reward 1 answers none of these by itself.

Use independent measurement, an independently checked generator, analytic
results, or a structurally different implementation. If reference values are
oracle-derived, disclose and defend that in `authoring/<task>/write-ups.md`. Changing only a
random seed or optimizer tolerance in the oracle is a robustness check, not a
structurally independent implementation.

For each inequality, measure legitimate variation and the targeted defect with
the actual scoring code. When their ranges overlap, improve the observable,
instances, or research question. Do not tune the bound until one favored solver
wins. Section 6 gives the recording procedure.

**Evidence:** the contrasting calibration accounts in [ambient RNA][ambient],
[remapping][remap], [navigation][navigation], and [XRD][xrd] motivate this
recommendation; their reported results are not local measurements.
**Master:** #6, #30, #57, #95, #100–#102.

### SCI-13 — Prove which scientific components matter

**R.** Build a dependency map from measurements through intermediate estimates to
the final outcome. Ablate every solution fix individually as Master #35
requires. Name the case expected to detect each omission, and distinguish its
direct failure from downstream consequences.

Ten failed metrics caused by one timing mistake are one causal bottleneck, not
ten independently demonstrated capabilities. Conversely, a required diagnosis
that can be omitted without affecting any assertion has no demonstrated role.

When two independent scientific routes solve the problem, a successful ablation
may show useful redundancy rather than a defect. Keep the legitimate route.
Do not close it merely to force the reference strategy; revise any claim that
the omitted component was necessary.

**Evidence:** [modal identification][modal] reports correction ablations;
[XRD][xrd] explicitly reports that its chemistry-free route still succeeds.
**Validation:** record the actual per-case effects, including unexpected passes.
**Master:** #1, #2, #28–#35, #43, #60, #95.

### SCI-14 — Treat model trials as a validity audit before a difficulty measurement

**R.** Read every completed passing and failing trajectory. Tie the outcome to
the public contract, submitted artifacts, and actual assertions. Distinguish a
scientific error from a defensible alternative, underspecification, an
incorrect reference, infrastructure failure, refusal, or unearned credit.

Do not infer an internal reasoning failure from reward 0. Cite the observable
decision or artifact that caused the outcome. A scientifically valid simpler
method that passes is evidence about the task, not a loophole by definition.

Local Step 3c uses five GPT-5.6 trials at `reasoning_effort=xhigh`. Preserve the
first five fidelity-complete same-config trials in launch order, with only the
outcome-independent exclusions allowed by the workflow. Do not cherry-pick a
harder-looking set or pool behavioral revisions.

**Evidence:** upstream [trial-analysis criteria][trial-analysis]; local
[workflow](docs/WORKFLOW.md) and
[difficulty guidance](docs/reference/DIFFICULTY_GUIDELINES.md).
**Master:** #83–#94, #95, #107.

## 5. Recipes for common starting points

These are **R** design options, not task templates. Use original scientific
questions, data, parameters, and implementations.

| Starting point | Scientific change to consider | What to verify | Incomplete method to probe | Fairness requirement |
|---|---|---|---|---|
| One clean parameter fit | Add a realistic nuisance confounded with the target, plus calibration or replication that separates them. | Target behavior and corrected observations on new conditions. | Fit with the nuisance fixed or ignored. | Demonstrate identifiability; publish the measurement convention. |
| Denoising that rewards deleting signal | Require preservation of a weak, meaningful population or feature as well as nuisance reduction. | Both removal and subgroup fidelity. | Uniform shrinkage, smoothing, or marker deletion. | Signal strength and tolerance must support recovery from the supplied observations. |
| A classifier on a random row split | Separate by study, subject, instrument, or experimental family; include a disclosed transfer regime. | Balanced and regime-specific scientific outcomes. | Majority class, study-ID prediction, leakage through duplicates. | Preserve learnable signal and sufficient public information about the shift. |
| A numerical answer on one fixture | Submit an executable model or solver; add new physical regimes and structural checks. | Values, laws, and behavior on answer-changing inputs. | Constant output or a local surrogate that fails off the fitted trajectory. | New cases remain in the stated envelope; accept different valid numerical methods. |
| A plausible inverse solution | Add an independent observable, or judge through forward predictions where the inverse is nonunique. | Data fit, physical feasibility, and the identifiable target. | Correct-looking parameters with a wrong predicted experiment. | Never demand recovery of an unidentifiable planted value. |
| A point estimate only | Add scientifically required uncertainty and a fixed ensemble of meaningful regimes. | Bias/error, coverage, informativeness, and artifact consistency. | Accurate estimate with zero or inflated uncertainty. | Allow defensible inferential variation; justify finite-ensemble bounds. |
| A high objective value without a proof | Require a checkable bound, covering certificate, or formal proof of the claimed property. | Feasibility, soundness, coverage, and the unchanged claim. | Strong candidate with an invalid bound or strengthened hypotheses. | The certificate is necessary to the research deliverable and feasible under resources. |
| A static experiment or control schedule | Introduce observable uncertainty where later information can improve decisions. | Scientific yield or safe completed intervention. | A frozen schedule, always-stop controller, or leaked scenario lookup. | A fixed policy that truly meets the outcomes remains valid. |
| Several independent mini-problems | Connect stages through a single scientific object and a meaningful downstream decision. | Cross-stage consistency and final scientific consequence. | Locally plausible stages whose conventions or inferred states disagree. | Avoid unrelated obligations; check each stage's necessity by ablation. |

Compose only as much as the workflow supports. A useful progression is one crux,
one realistic interaction, and one independent validation axis. A longer chain
needs an explicit scientific reason and a tractable independent solution.
More mechanisms can reduce fairness if the observations no longer distinguish
them.

## 6. Calibration and control protocol

Keep measurements under `authoring/<task>/calibration/` and data origins under
`authoring/<task>/provenance/`, as the workflow already prescribes. Summarize
truth provenance, acceptance bounds, and justified exceptions in
`authoring/<task>/write-ups.md`, especially `## Verification`. These authoring records never ship.

### Establish the reference independently

For each target, record its origin, units, normalization, uncertainty, generating
assumptions, and access boundary. For synthetic data, record the model, parameters,
seeds, preprocessing, and why its regimes are realistic. Cross-check the
generating equations or important limiting cases; a generator and oracle with the
same bug are not independent.

For real data, record version, license, preprocessing, alignment, missingness,
and label uncertainty. Avoid a public identifier or metadata trail that directly
reveals the withheld answer. Internet remains available to the agent; a reachable
answer is a design problem (Master #64, #99, #100).

### Measure correct and defective alternatives through the real scoring code

Use a table like this in the existing calibration records; fill it with outputs,
not prospective PASS labels.

| Assertion / manifest case | Quantity and scientific reason | Reference result | Structurally different correct result | Incomplete-method result | Chosen bound and margin | Evidence path / digest |
|---|---|---|---|---|---|---|

For an upper-bound error gate `E <= T`, record `T - E` for each correct method and
`E - T` for each targeted defect. Reverse the direction for a lower-bound score.
Include the worst relevant regime, not just the mean. Explain absolute and
relative tolerances separately, including behavior near zero. Units and
normalization are part of the metric.

Calibration precedes model trials. Thresholds must serve the science and comply
with Master #57 and #101. If the exact number is not public, the acceptance
objective still must be discoverable and fair. Every number that is public
matches the tests byte for byte (Master #6).

### Check every graded instance

Run relevant trivial nulls separately on every withheld instance:

- Constant, range midpoint, mean/median, geometric centre, or zero correction.
- Majority class, one cluster, one cluster per item, or input copied unchanged.
- Public-answer replay and any task-specific method-free prediction.

A suite-level failure does not prove that each instance discriminates. Prefer
instances for which these nulls fail. If an instance does not discriminate,
identify it in `write-ups.md` `## Verification` as Master #102 requires; do not
claim that it contributes demonstrated hardness. It must still comply with
Master #46 if it is a held-out scenario.

### Distinguish three kinds of control

| Control | What it establishes | What it does not establish |
|---|---|---|
| NOP | Every case requires work beyond the untouched task. | Rejection of plausible but scientifically wrong outputs. |
| Targeted scientific ablation | The intended assertion detects a particular omitted capability. | Correctness of the reference or every tolerance. |
| Shortcut / tamper control | A named trust or scoring boundary rejects the planned bypass. | Scientific difficulty. |

Map every planned control to the manifest case it must fail in
`authoring/<task>/controls.md`. The fixed NC-01..NC-14 catalog is not mandatory.
The control launcher remains opt-in; rejection of all shortcut classes in
Master #60 is mandatory. When controls are run, an unrelated assertion failure
does not count, and `controls_report.py` owns the generated gate-results section.

A rejection-only test also needs a known-good positive control in the same test
function (Master #52). A preservation or security guard must be coupled to a
real behavioral assertion so it cannot pass under NOP (Master #40–#42).
Do not turn NOP into an import error or fixture crash.

## 7. Scientific verifier design

A harder task needs stronger evidence of correctness, not a more opinionated
verifier.

1. **Trace every assertion to its requirement.** Include schemas, physical
   conventions, metrics, and all authoritative environment documents. Classify
   a choice as field-standard, explicitly selected between defensible options,
   or task-specific and therefore stated (Master #0–#7, #12).
2. **Read final artifacts as untrusted data.** Validate identity alignment, shape,
   units, finite values, and stated exactness before computing quantities.
   Existence and plausible formatting alone never establish scientific success
   (Master #43, #47, #59).
3. **Own the expected side.** Bake pristine fixtures, reference inputs, and
   expected values into the separate verifier image. Recompute metrics there.
   Never use an agent-editable generator, label file, or reported score as truth
   (Master #30, #44, #45, #55).
4. **Handle scientific equivalence explicitly.** Accept allowed label
   permutations, gauges, representations, and alternative valid methods.
   Document what may vary and what must remain fixed (SCI-08).
5. **Link products through independent calculations.** Predictions must follow
   from the submitted model; summaries from the submitted samples; intervention
   claims from trusted rollouts. Agreeing self-reports do not validate one another.
6. **Use the master's exact execution boundary.** Copy its Appendix into
   `tests/Dockerfile` and `tests/test.sh`. Agent code runs through the prescribed
   uid-12000 `setpriv` launcher with a clean environment and bounded execution;
   never import it into the privileged test process. The security timeout is
   not a scientific speed objective (Master #54).
7. **Preserve the full artifact/reward seal.** Delete artifact symlinks that
   resolve outside the declared artifact paths; preserve in-tree links. Keep
   `/tests` root-only and `/logs/verifier` root-owned 755. Kill sandbox processes,
   remove any old reward file, then write the binary reward last (Master #55, #56).
8. **Keep outcomes diagnostic without partial rewards.** Emit named CTRF cases
   and values that explain failures; reward remains exactly 0 or 1 with identical
   logic for Oracle and agent. Honor `TBENCH_TEST_ID` and the declared manifest
   (Master #39–#43, #53, #58).
9. **Keep execution reproducible.** Bake pinned dependencies and private data at
   build time; declare verifier `no-network` or the justified allowlist exception.
   Fix stochastic seeds and test scientific reproducibility with the independent
   method, not just identical reruns (Master #38, #64, #100, #106).

Source-specific sandbox code is not a substitute for the local Appendix.
Unsafe checkpoint loading, dynamic imports, submitted build hooks, and embedded
expressions must not execute with grader privileges. Parsing a scientific model
as data does not authorize arbitrary code execution.

## 8. Applying changes in this workspace

Use [commands.md](commands.md) for complete invocations and
[AUTHORING_WORKFLOW.md](docs/WORKFLOW.md) for stage order.

| Existing record | Hardening information to put there |
|---|---|
| `seed-review.md` / `specs/<task>.md` | Research origin, originality, scientific crux, plausible incomplete methods. |
| `contract.md` | Observable outcomes, conventions, identifiable targets, equivalent valid answers. |
| `traceability.md` | Requirement-to-assertion mapping, manifest cases, holdouts, ablation dependencies. |
| `threat-model.md` | Answer leakage, metadata shortcuts, self-reports, executable artifacts, reward boundaries. |
| `resource-plan.md` | CPU/memory/storage feasibility, dependency/runtime parity, declared evaluation differences. |
| `provenance/` / `calibration/` | Data origins, truth independence, alternate correct implementation, margins and per-instance nulls. |
| `controls.md` | Control plan naming manifest cases; generated results are written by the gate. |
| `master-checklist.md` | Existing one-line-per-Master record, bound to the current task digest. |
| `write-ups.md` | `## Difficulty`, `## Reference solution`, `## Verification`: scientific difficulty, reference strategy, truth provenance and bound calibration (Master #103). |
| `step3b-review.md` / `step3c-report.md` | Independent review and causal interpretation of each complete trial. |

Except for `specs/<task>.md`, the authoring paths above are relative to
`authoring/<task>/`. The task itself carries no README (Master #103);
`write-ups.md` explains its scientific difficulty, reference solution, and
verification, never ships, and contains no measured rate or tier (Master #62). Write actual task instructions as a human under Master #0;
this guide and its prompt below are author-side planning material.

### Before the seal

Complete the seed decision and Step 2a contract first. During construction, use
the real reference, alternate implementation, nulls, and ablations to establish
the scientific distinction. Useful existing commands, after replacing
`<task-name>`:

```bash
source .venv/bin/activate
python3 scripts/doctor.py --strict-tools
python3 scripts/task_check.py tasks/<task-name> --strict
python3 scripts/hardening_check.py tasks/<task-name>
python3 scripts/audit_task.py tree tasks/<task-name>
scripts/dev_verify.sh tasks/<task-name>
scripts/gate_step2b.sh tasks/<task-name> --with-nc
```

Here `--with-nc` deliberately opts into the planned control matrix. The ordinary
gate can run without it. The gate performs static checks, the blocking auditor
tree screen, master auto findings, reference verification, the per-test
Oracle/NOP matrix, sealing, and requested controls. Check its actual
`VERDICT: PASS` output before claiming completion.

Step 3b independently reviews the seal, the full applicable master sections, and
the bundled auditor's checklist; every LEAD is answered. Validate the record:

```bash
python3 scripts/master_checklist.py check tasks/<task-name> --stage review
```

### After capture

| Change | Required path |
|---|---|
| Behavioral change to instructions, environment, solution, or functional configuration | Fresh Step 2b gate and digest; fresh review and model evidence. Never combine old and new behavioral revisions. |
| `tests/`-only verifier repair | Bind with `regrade_step3c.py` **before editing**, run the full fresh gate and regrade, then fresh review. Apply all conditions of [§8.2](docs/TBSCI_HARDENING_RULES.md#82-grader-surface-rebinding), including identical outcomes by default and its narrow per-trial defect waiver. No threshold tuning. |
| Descriptive `[metadata]` correction only (a `write-ups.md` edit touches no task file and needs no re-seal) | Use `gate_step2b.sh --reseal-only` and the review/report rebindings in [§8.3](docs/TBSCI_HARDENING_RULES.md#83-descriptive-only-re-seal). Both graded digests must be unchanged. |

Step 3c remains GPT-5.6 x5 at `reasoning_effort=xhigh` with full-fidelity capture,
plus full-suite Oracle x3 / NOP x2. Local `harbor` runs Oracle/NOP and negative
controls; `stb` is only for the model trials. Use the launcher and key guard;
never manually refresh a shared key. A cut-short round is composed only by the
existing same-digest, same-config process. Every shipped Oracle case passes;
every NOP case fails by genuine assertion (Master #40, #72–#74, #91, #92, #94).

For every model run, answer the eight Master #107 criteria:
`specification_completeness`, `solution_discoverability`, `verifier_correctness`,
`boundary_fairness`, `unearned_credit`, `meaningful_difficulty`,
`policy_refusal`, and `execution_blocked`. Keep invalid difficulty evidence out
of the defensible rate without using that classification to cherry-pick trials.

A measured 0/5, 1/5, 2/5, or 3/5 is only the workspace's difficulty condition, never
proof of task quality. All validity, evidence, review, and package checks still
apply. A higher valid rate is reported honestly; further hardening creates a new
behavioral revision. Model results never retroactively set thresholds.

Step 4 stays **build → audit → promote**, with complete package-stage master
records, per-run rubric evidence, mechanical package verification, and the
auditor's judged candidate review linting Ready with zero warnings. Only
`package_task.py --promote` produces the deliverable ZIP. A documentation rewrite
or a hardening proposal is not a task PASS or shipping approval.

## 9. Stop-hardening conditions

| Warning sign | Correct response |
|---|---|
| Correct methods disagree because a convention was unstated. | Clarify the convention or accept the valid alternatives; invalidate affected evidence. |
| The target lies in an unresolved null direction. | Add information, grade the identifiable observable, or redesign. |
| The incomplete method passes every legitimate outcome. | Accept it as valid; change the scientific objective only if a real research need justifies it. |
| The threshold must sit between nearly identical correct implementations. | Revisit the metric and scientific precision; do not force oracle imitation. |
| More data only causes resource failure. | Reduce scale or redesign the computational question; retain all 28800-second task timeouts. |
| Nulls succeed on particular hidden cases. | Redesign those cases or document them under Master #102; do not conceal them in an average. |
| A source task supplies a ready-made story, parameter set, fixture, or solution. | Stop copying; retain only the abstract design principle and develop an original workflow. |
| The apparent failure comes from refusal, missing dependencies, capture loss, or a harness limit. | Repair the task or infrastructure; this is not capability evidence. |
| New checks reward compliance or forbid a valid method without scientific purpose. | Remove the manufactured difficulty and re-check bidirectional coverage. |

No upstream benchmark tasks, datasets, generators, answer keys, or verifier
implementations are copied into this workspace. Citations support a design
study, not a template library. Originality remains an author judgment; do not
build an upstream similarity corpus.

## 10. Copyable author-side hardening prompt

Use this with an existing task or Step 2a idea. It requests analysis and evidence,
not an AI-written `instruction.md`.

```text
Harden the scientific capability tested by <task-name> using
docs/reference/TBSCI_CAPABILITY_HARDENING_RULES.md.

Read MASTER_CHECKLIST_TBSCI.md first; it is authoritative. Follow the existing
authoring workflow, records, and digest rules. This is a personal-use TB-Science
task, not an upstream submission. Do not copy benchmark tasks, data, solutions,
or tests. Do not generate the human-authored instruction.md.

1. Read the current public contract, environment, reference solution, tests,
   authoring records, and available trajectories. Separate source observations,
   hypotheses, recommendations, and measured local outcomes.
2. State the research decision, indispensable expertise, current scientific
   crux, and simplest plausible incomplete method. Explain why the problem is
   identifiable from the public evidence.
3. Propose a small, coherent change using relevant SCI rules. For each change
   name the research justification, observable outcome, public requirement,
   permissible alternatives, and information needed by an independent expert.
4. Map it to the existing traceability and controls plans: named manifest case,
   targeted ablation, answer-changing holdout, per-instance trivial null, and
   structurally different correct implementation. Identify any redundant route
   honestly; do not reject a scientifically valid alternative.
5. Plan or perform the authorized independent validation. Record truth provenance,
   every tolerance's scientific basis, actual scoring margins, and the effect
   of each solution-fix ablation. A prospective result remains PENDING.
6. Preserve the master verifier seal, binary reward, per-test Oracle/NOP behavior,
   28800-second task timeouts, public agent network, offline verifier, and CPU-only
   resources. No wall-clock performance gate, hidden convention, tighter
   oracle-matching tolerance, lookup-solvable answer, or arbitrary tool ban.
7. Route edits through the correct gate and invalidation path. Report evidence
   paths and unresolved findings. Never claim PASS, READY, or improved measured
   difficulty without the relevant command output and causal trial review.

Return the smallest scientifically justified hardening plan or authorized
implementation, with its validation evidence. Keep task instructions and
author-only calibration material separate.
```

## 11. Pinned source index and maintenance

Each task row above links to its README at the fixed source commit. These paired
instruction links allow the public contract to be checked independently of the
author's explanation:

| Domain | Selected public instructions |
|---|---|
| Life sciences | [Ambient RNA][ambient-instruction] · [Protein experiments][protein-instruction] · [Animal identities][animal-instruction] · [Clinical metadata][clinical-instruction] · [EEG][eeg-instruction] |
| Physical sciences | [CMB][cmb-instruction] · [Molecular restraints][chemistry-instruction] · [XRD][xrd-instruction] · [Waveguide][waveguide-instruction] |
| Earth sciences | [Assimilation][assimilation-instruction] · [Aquifer][aquifer-instruction] · [Hydrology][hbv-instruction] · [Remapping][remap-instruction] |
| Mathematical sciences | [ODEs][ode-instruction] · [Formal proof][formal-instruction] · [Certificate][certificate-instruction] · [Noisy optimization][blackbox-instruction] · [Mediation][mediation-instruction] |
| Engineering sciences | [Reactor][reactor-instruction] · [Modal identification][modal-instruction] · [Navigation][navigation-instruction] · [Constitutive discovery][constitutive-instruction] |

When refreshing this guide, resolve the Hub tag again, record its revision and
package version, pin the source commit, reconcile task-name sets, and state
exactly which contracts, checks, and trajectories were inspected. Changed task
names alone do not justify carrying old source observations forward. Update
recommendations when the scientific evidence changes; do not silently turn
author-reported calibration into independently observed outcomes.

[hub]: https://hub.harborframework.com/datasets/terminal-bench-science/terminal-bench-science/latest?tab=tasks
[hub-tasks]: https://hub.harborframework.com/api/datasets/terminal-bench-science/terminal-bench-science/latest/tasks
[release]: https://github.com/harbor-framework/terminal-bench-science/tree/v0.1.0
[implementation]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/rubrics/task-implementation.toml
[trial-analysis]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/rubrics/trial-analysis.toml
[ambient]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/life-sciences/biology/ambient-rna-correction/README.md
[ambient-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/life-sciences/biology/ambient-rna-correction/instruction.md
[ambient-tests]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/life-sciences/biology/ambient-rna-correction/tests/test_state.py
[protein]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/life-sciences/biology/protein-active-learning/README.md
[protein-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/life-sciences/biology/protein-active-learning/instruction.md
[animal]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/life-sciences/ecology/animal-reid/README.md
[animal-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/life-sciences/ecology/animal-reid/instruction.md
[clinical]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/life-sciences/medicine/clinical-metadata-recovery/README.md
[clinical-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/life-sciences/medicine/clinical-metadata-recovery/instruction.md
[eeg]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/life-sciences/neuroscience/eeg-erp-recovery/README.md
[eeg-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/life-sciences/neuroscience/eeg-erp-recovery/instruction.md
[cmb]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/physical-sciences/astronomy/cmb-cross-inference/README.md
[cmb-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/physical-sciences/astronomy/cmb-cross-inference/instruction.md
[chemistry]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/physical-sciences/chemistry/rdkit-ic-constraints/README.md
[chemistry-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/physical-sciences/chemistry/rdkit-ic-constraints/instruction.md
[xrd]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/physical-sciences/materials-science/xrd-multiphase-qpa/README.md
[xrd-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/physical-sciences/materials-science/xrd-multiphase-qpa/instruction.md
[xrd-tests]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/physical-sciences/materials-science/xrd-multiphase-qpa/tests/test_xrd.py
[waveguide]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/physical-sciences/physics/inverse-waveguide-shape/README.md
[waveguide-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/physical-sciences/physics/inverse-waveguide-shape/instruction.md
[assimilation]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/earth-sciences/atmospheric-sciences/sparse-network-assimilation/README.md
[assimilation-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/earth-sciences/atmospheric-sciences/sparse-network-assimilation/instruction.md
[aquifer]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/earth-sciences/environmental-sciences/hysteretic-aquifer-control/README.md
[aquifer-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/earth-sciences/environmental-sciences/hysteretic-aquifer-control/instruction.md
[hbv]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/earth-sciences/geosciences/hbv-calibration-1/README.md
[hbv-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/earth-sciences/geosciences/hbv-calibration-1/instruction.md
[remap]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/earth-sciences/ocean-sciences/masked-spherical-remap/README.md
[remap-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/earth-sciences/ocean-sciences/masked-spherical-remap/instruction.md
[ode]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/mathematical-sciences/applied-mathematics/ode-law-discovery/README.md
[ode-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/mathematical-sciences/applied-mathematics/ode-law-discovery/instruction.md
[ode-tests]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/mathematical-sciences/applied-mathematics/ode-law-discovery/tests/test_outputs.py
[formal]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/mathematical-sciences/formal-mathematics/finite-free-stam/README.md
[formal-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/mathematical-sciences/formal-mathematics/finite-free-stam/instruction.md
[formal-tests]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/mathematical-sciences/formal-mathematics/finite-free-stam/tests/test_outputs.py
[certificate]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/mathematical-sciences/operations-research/certified-sparse-regression/README.md
[certificate-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/mathematical-sciences/operations-research/certified-sparse-regression/instruction.md
[blackbox]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/mathematical-sciences/operations-research/noisy-blackbox-optimization/README.md
[blackbox-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/mathematical-sciences/operations-research/noisy-blackbox-optimization/instruction.md
[mediation]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/mathematical-sciences/statistics/highdim-mediation-debiasing/README.md
[mediation-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/mathematical-sciences/statistics/highdim-mediation-debiasing/instruction.md
[reactor]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/engineering-sciences/chemical-engineering/reactor-safety-control/README.md
[reactor-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/engineering-sciences/chemical-engineering/reactor-safety-control/instruction.md
[reactor-tests]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/engineering-sciences/chemical-engineering/reactor-safety-control/tests/test_outputs.py
[modal]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/engineering-sciences/civil-engineering/rolling-shutter-oma/README.md
[modal-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/engineering-sciences/civil-engineering/rolling-shutter-oma/instruction.md
[navigation]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/engineering-sciences/electrical-engineering/navigation-sensor-calibration/README.md
[navigation-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/engineering-sciences/electrical-engineering/navigation-sensor-calibration/instruction.md
[constitutive]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/engineering-sciences/mechanical-engineering/inelastic-constitutive-discovery/README.md
[constitutive-instruction]: https://github.com/harbor-framework/terminal-bench-science/blob/f81afac4f11048e77a15dfc8fb1dbfb897fea0ce/tasks/engineering-sciences/mechanical-engineering/inelastic-constitutive-discovery/instruction.md
