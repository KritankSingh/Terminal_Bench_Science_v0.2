# Resource and performance plan — <task-name>

Source of truth: `MASTER_CHECKLIST_TBSCI.md` (Master #26, #30, #36, #57,
#63–#65, #100, #106).

## task.toml budgets (Master #63)

Fixed from creation, not tuned down:

| Field | Value |
|---|---:|
| `[agent].timeout_sec` | 28800 |
| `[verifier].timeout_sec` | 28800 |
| `[environment].build_timeout_sec` | 28800 |

`instruction.md`'s closing paragraph names the same 28800 (#104).

## Measured resources

| Resource | Measured need | Measurement/rationale | Headroom |
|---|---:|---|---:|
| Build time | | | |
| Verifier time | | | |
| Expert solve time (`expert_time_estimate_hours`) | | | |
| CPU | | | |
| Memory | | | |
| Storage (`environment/` ≤100 MiB, no file >50 MiB) | | | |

Declared in `[environment]` (Master #65), sized so the task is hard for the
agent, not for the computer:

| Field | Value | Why |
|---|---:|---|
| `cpus` | | |
| `memory_mb` | | |
| `storage_mb` | | |
| `gpus` | 0 | local Docker, no GPU; no `gpu_types` |

Any parallelism in Dockerfiles, `test.sh` or `solve.sh` uses a fixed worker
count sized to `cpus`, never bare `nproc` (#106).

## Network policy (Master #64)

Declared on both phases; neither is a design knob for difficulty.

| Phase | Key | Value |
|---|---|---|
| Agent | `[environment].network_mode` | `"public"` (always) |
| Verifier | `[verifier.environment].network_mode` | `"no-network"` |

The agent always has open internet. If that would let it skip the work — a
published answer, a downloadable solution, a well-known result to look up — the
task is redesigned (Master #99); cutting the agent's network is not an option.

Verifier allowlist (only if the verifier genuinely needs one host; otherwise
`n/a`): `network_mode = "allowlist"`, the exact `allowed_hosts`, what it fetches
and why it cannot be baked into `tests/Dockerfile`:

## Data hosting and build-time fetches (Master #100)

Every dataset the task ships or fetches: where it lives, its size, and — for a
build-time fetch — the immutable revision written as a literal in the
Dockerfile and the checksum verified during the build. Grader-only data lands
only in the tests image. Origin and licence go in
`authoring/<task-name>/provenance/`.

| Dataset | Shipped / fetched | Location or URL | Pinned revision | Checksum | Agent or tests image |
|---|---|---|---|---|---|

## Reproducibility (Master #106)

`apt-get update` before every install and `/var/lib/apt/lists` cleaned; every
pip / uv install pinned `==` (numpy, scipy, pandas and domain libraries
included) in Dockerfiles and `solve.sh`, while `test.sh` installs nothing
(#38); no compose host bind mounts; seeds fixed. Two Oracle runs give identical results (command, outcome):

## Portability assumptions (Master #26, #36)

Architecture assumptions, digest-pinned bases, and the cold-build result
(command, date, outcome). Name the final agent base: a canonical
`public.ecr.aws/docker/library/<python|node|golang|rust|eclipse-temurin|gcc|ruby|maven|debian|ubuntu>`
image, or the reason no canonical image works (the same reason goes in a
Dockerfile comment; the bundled auditor checks for it).

## Correctness reference (Master #30)

For each named algorithm/metric/transform/estimator/KDF the task grades: the
trusted external implementation or hand derivation, the command used, and the
diff against the reference solution's output on the shipped fixtures. `n/a`
with a reason if the task grades none.

## Ground truth and tolerance calibration (Master #100–#102, #6)

Where the graded reference values come from (generating model, cited external value,
second implementation written to cross-check the oracle, or oracle-derived — then say
so and how it was defended). For every tolerance, threshold or fuzzy match: the literal
value (byte-identical in instruction.md if stated there and in tests/), what it brackets,
the legitimate variation it absorbs, and the statistic measured on the reference AND on at
least one independent correct implementation that differs structurally (the study itself
lives in `authoring/<task-name>/calibration/`). Then each trivial null (constant, mean or
median of the range, domain centre, majority class, identity / copy-through, the NOP)
scored per graded instance, with any instance a null reaches named.

| Graded quantity | Bound | Reference value | Independent impl. value | Defective approach value | Separation | Source of truth |
|---|---|---|---|---|---|---|

| Graded instance | Null | Passes the bound? |
|---|---|---|

## Deterministic work/quality methodology (Master #57)

No wall-clock latency, throughput or percentile assertion — ever. Complete this
section only when efficiency is part of the public contract, and complete it
before model trials. Correctness is checked before any threshold.

| Implementation | Scale | First-result work | Total work/quality | Peak memory | Notes |
|---|---:|---:|---:|---:|---|
| Oracle/reference | | | | | |
| Naive baseline | | | | | |
| Realistic partial | | | | | |

Threshold formula (from the public objective and the named baseline, never from
the reference's exact output or a model attempt):

Can a fundamentally different correct implementation pass?

Measured margin from the reference's own result (must exceed ~5%, or record the
explicit sign-off here):

Wall-time diagnostics and timeout headroom (never pass/fail):
