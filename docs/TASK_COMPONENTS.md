# Task Components (Terminal-Bench Science)

`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth; this page is the
construction view of its Sections B–E. A task built from the templates below passes the
mechanical master checks (`scripts/task_check.py --strict`) from its first commit.

## Directory layout

```
your-task-name/
├── task.toml
├── instruction.md            # ends with the "You have 28800 seconds…" suffix (Master #104)
├── environment/
│   ├── Dockerfile            # OR docker-compose.yaml
│   └── data/                 # optional bundled inputs (provenance recorded, Master #100)
├── solution/
│   └── solve.sh
├── tests/
│   ├── Dockerfile            # verifier image (required)
│   ├── test.sh
│   ├── test_manifest.json    # one entry per logical test (docs/TESTING_POLICY.md)
│   ├── ctrf_reporter.py
│   └── test_outputs.py
├── rubric.txt                # workspace only; ships as a SIBLING of the inner task folder
└── trajectories/             # workspace only; Step 3c rounds, never inside the shipped task
```

The shipped inner `<task-slug>/` holds only `instruction.md`, `task.toml`,
`environment/`, `solution/` and `tests/` — no `README.md` (Master #96, #103);
`package_task.py` places `rubric.txt`, `oracle-nop-evidence/` and `trajectories/`
beside it. Author-side material that never runs in a trial — the write-ups
(`write-ups.md`), data generators, provenance records (manifests, checksums, source
URLs), independent reference implementations, the optional `hint.md` — lives in the
workspace's `authoring/<task>/` (`provenance/`, `calibration/`), never in the task tree. (Upstream TB-Science keeps it in `<task>/authoring/`; this
workspace keeps the task tree to the five shipped entries so the digest and the ZIP stay
exact — see the v4 workspace's TBSCI_REVAMP notes (not carried here).)

## Separate verifier

```toml
[verifier]
environment_mode = "separate"
```

Consequences:

1. `tests/` and `solution/` must be absent from the agent image.
2. The verifier only sees paths listed in top-level `artifacts`.
3. Parent directories for those artifacts must exist in `tests/Dockerfile`.

```toml
artifacts = ["/app/output.json", "/app/results/"]
```

`artifacts` must be **top-level**. Nesting under `[verifier]` silently drops it.

```dockerfile
# tests/Dockerfile
RUN mkdir -p /app
```

## task.toml template

Aligned with upstream `task-template.toml` (harbor-framework/terminal-bench-science)
minus the Harbor Hub publish fields: no canary, no `[task]` table / namespace / authors /
keywords, no `author_profile` / `conflicts_of_interest` / `referred_by`. No `difficulty`
field (Master #62); all three timeouts at 28800 from creation (Master #63); the network
policy declared on both phases (Master #64):

```toml
artifacts = ["/app/output.json"]
name = "your-task-name"

[metadata]
domain = "physical-sciences"          # exact value, docs/TASK_TAXONOMY.md
field = "astronomy"                   # exact value listed under the domain
subfield = "exoplanet-transit-vetting"   # free text, kebab-case recommended
tags = ["transit-photometry", "period-search", "false-positives", "tess"]
expert_time_estimate_hours = 6.0      # best-case hours for a focused domain expert
relevant_experience = "A sentence or two on the author's background relevant to this task."
# author_name = "..."                 # optional
# author_email = "..."                # optional

[verifier]
timeout_sec = 28800
environment_mode = "separate"

[verifier.environment]
network_mode = "no-network"           # the verifier grades agent code: no egress

[agent]
timeout_sec = 28800

[environment]
build_timeout_sec = 28800
cpus = 2
memory_mb = 8192
storage_mb = 10240
gpus = 0
network_mode = "public"               # the agent phase runs with open internet
```

### Field notes

| Field | Rules |
|-------|--------|
| `name` | Top-level; equals the directory slug (kebab-case, a name not a sentence; 2–4 tokens typical, Master #61). No `[task]` table, no `terminal-bench-science/` namespace |
| `artifacts` | Top-level only — nested under `[verifier]` it is silently dropped (Master #37) |
| `domain` / `field` / `subfield` | Exact kebab-case `domain` and `field` from `docs/TASK_TAXONOMY.md`; `subfield` non-empty free text; classify by the scientific expertise indispensable to solve the task (Master #61, #98) |
| `tags` | 3–6 specific keywords (methods, data, instruments — not "science" or "python") |
| `expert_time_estimate_hours` | Required; best-case hours for a focused domain expert; never a minute-based field |
| `relevant_experience` | Required, substantive (Master #61) |
| `author_name` / `author_email` / `author_organization` | Optional; non-empty when present |
| `difficulty_explanation` / `solution_explanation` / `verification_explanation` | **Not task.toml fields** — `## Difficulty` / `## Reference solution` / `## Verification` in the workspace record `authoring/<task>/write-ups.md` (Master #103) |
| `category` / `subcategory` / `languages` | **Retired** TB4 keys — rejected |
| `difficulty` | **Banned** (Master #62). The measured k=5 rate lives only in workspace reports |
| `schema_version` | Optional (upstream template carries one; nothing in Harbor branches on it) |
| `version`, `codebase_size`, `*_min`, milestones, `[reference_pattern]`, host paths | **Banned** (Master #65) |
| `is_multi_container` | `true` only for a genuinely multi-container task; omit otherwise |
| `[environment].network_mode` | `"public"`, declared (Master #64) |
| `[verifier.environment].network_mode` | `"no-network"`, declared; `"allowlist"` + `allowed_hosts` only with a recorded reason (Master #64) |
| `[agent]`/`[verifier]`.`timeout_sec`, `[environment].build_timeout_sec` | 28800, all three, from creation (Master #63); instruction.md's suffix names the same number (#104) |
| `cpus` / `memory_mb` / `storage_mb` | Declared, sized to the task — hard for the agent, not the computer (Master #65) |
| `gpus` | Declared `0`; no `gpu_types` (local Docker, no GPU) |

## Write-ups template

`authoring/<task>/write-ups.md`, copied from `authoring/_templates/write-ups.md`. It is a
workspace record — it never ships, is never given to the agent, and the task carries no
`README.md` (Master #103; upstream `task-readme-template.md` is not adopted). Editing it
touches no task file, so it needs no re-seal. Each section is required and non-empty; soft caps of ~400 / 300 / 600 words of prose
(tables and code blocks are free). No pass rates, model scores or tiers (Master #62).

```markdown
# Write-ups — your-task-name

## Difficulty

What makes the task fundamentally hard for a human expert and for an agent: the
reasoning, domain knowledge or multi-step problem solving. One sentence on the data
(real or synthetic, and where it comes from); one on who does this work in the real world.

## Reference solution

The strategy and the key insight — what approach solves it and why it works — matching
what solution/ actually does.

## Verification

What the tests check and why that is sufficient; where the reference values come from
(independent, or oracle-derived and disclosed); how every tolerance or threshold was
calibrated, including at least one independent correct implementation that differs from
solution/ structurally, and which graded instances a trivial null clears, if any
(Master #100–#102).
```

## instruction.md ending

The last paragraph is exactly (preceded by a blank line, followed by one newline;
Master #104, upstream `check-instruction-suffix.sh`):

```text
You have 28800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
```

Descriptive fields under `[metadata]` only — top-level copies are ignored by
structure checks.

## Component roles

| Path | Role |
|------|------|
| `instruction.md` | Human-voiced, outcome-focused prompt (what, not how), solvable by an independent domain expert from the text alone; ends with the timeout suffix |
| `environment/` | Agent sandbox; apt unpinned (with `apt-get update` and list cleanup), language packages — numpy, scipy, pandas and domain libraries included — pinned exactly; tmux + asciinema; no bare `nproc` |
| `solution/solve.sh` | Deterministic oracle; may call helpers in `solution/` |
| `tests/Dockerfile` | Verifier image; bake pytest + plugins; `COPY . /tests/` |
| `tests/test.sh` | Entrypoint; no `set -e`; reward on every path; `TBENCH_TEST_ID`; last line `exit 0` |
| `tests/test_outputs.py` | Semantic pytest assertions with docstrings |
| `rubric.txt` | Locally authored scoring criteria; ships beside the task folder |
| `trajectories/` | Workspace Step 3c rounds; the package ships five runs + SUMMARY beside the task folder |
| `authoring/<task>/write-ups.md` | Workspace-only reviewer write-ups (Difficulty / Reference solution / Verification); never ships, never given to the agent |

## Hardened verifier contract

The task tree is necessary but not sufficient. Follow
`docs/TBSCI_HARDENING_RULES.md` and keep authoring evidence outside the task under
`authoring/<task>/`.

- every meaningful assertion maps to an explicit or uniquely derivable public requirement;
- every public requirement has independent coverage;
- verifier truth is independently recomputed from pristine inputs;
- semantically equivalent correct outputs are accepted;
- persisted state is reloaded before scoring;
- the verifier seal (Master #54–#56, the master's Appendix A): `/tests` root-only, `/work`
  root-owned 755, agent code run as uid 12000 through `setpriv … env -i … timeout -k
  <PER_RUN_LIMIT>`, artifact symlinks deleted before grading, kill-to-exhaustion, and
  the reward written last by root;
- every test fails under NOP through a real assertion, and guard-only checks are coupled
  to a behavioral assertion in the same test (Master #40–#42, #74);
- every fail-closed test also runs a known-good positive control (Master #52);
- each shortcut (empty output, format-only fake, hardcoded answer, self-reported metric,
  missing artifact, forged reward) is rejected by its own named assertion (Master #60);
- Oracle and agent use identical testing with no actor detection; reward is exactly 0 or 1;
- no wall-clock latency/throughput tests at all, and no runtime web data fetches;
- every non-standard `test.sh` environment variable has a default;
- deterministic score/work gates follow correctness and are not near-Oracle replicas.

## Canonical tests/Dockerfile

```dockerfile
FROM public.ecr.aws/docker/library/python:3.12-slim-bookworm@sha256:<digest>

RUN pip install --no-cache-dir pytest==9.1.1

RUN apt-get update \
 && apt-get install -y --no-install-recommends util-linux procps \
 && rm -rf /var/lib/apt/lists/*

COPY . /tests/

RUN useradd --uid 12000 --user-group --no-create-home --shell /usr/sbin/nologin sandbox \
 && mkdir -p /logs/verifier /work /app \
 && chown -R root:root /tests /logs/verifier /work \
 && chmod -R go-rwx /tests \
 && chmod 755 /logs/verifier /work
```

`tests/ctrf_reporter.py` writes the CTRF report (docs/TESTING_POLICY.md), so no CTRF
plugin is installed; every verifier dependency is pinned exactly (Master #38).
The last two `RUN`s are the master's Appendix A step 1, copied as given (plus `/app`, the
artifact landing directory, Master #37): `util-linux` supplies `setpriv`, `procps`
supplies `pkill`, `/tests` is root-only so agent code running as uid 12000 cannot
read expected values or fixtures, and `/work` stays root-owned 755 so the sandbox
cannot rename a sibling run directory (Master #54(c)). The bundled auditor fails a
verifier image without the seal (Master #54, `T3-SEAL`). Every expected-side file is
`COPY`ed into `/tests` here, never read from `/app` or an artifact path (Master #55).
On Alpine, `apk add util-linux procps shadow` replaces the apt line.

The final **agent** image (`environment/Dockerfile`) uses a canonical base the auditor
recognises — `public.ecr.aws/docker/library/<python|node|golang|rust|eclipse-temurin|gcc|
ruby|maven|debian|ubuntu>@sha256:<digest>` — or carries a comment explaining why no
canonical base works (Master #26).

When a test runs agent-produced code, it never imports it; it launches it through the
Appendix launcher and reads the output back as data (Master #54, Appendix step 3):

```python
# PER_RUN_LIMIT: stated in instruction.md; >= 10× the reference's measured per-run runtime (#57(a))
PER_RUN_LIMIT = "<seconds>"
UNTRUSTED = ["setpriv", "--reuid=12000", "--regid=12000", "--clear-groups", "--no-new-privs",
             "env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/work",
             "OMP_NUM_THREADS=2", "OPENBLAS_NUM_THREADS=2", "MKL_NUM_THREADS=2",
             "NUMEXPR_NUM_THREADS=2",
             "timeout", "-k", "5", PER_RUN_LIMIT]
r = subprocess.run(UNTRUSTED + ["/bin/bash", "run.sh"], cwd="/work/build",
                   capture_output=True, text=True)
# kill_all equivalent, then read /work/build as data
```

Expected values come from files under `/tests`; counts and metrics are recomputed from
them, never read from `r.stdout` or from rows the agent wrote (Master #55).

Pin versions to whatever the current skeleton publishes when it lands; skeleton wins.

## Canonical tests/test.sh

The full selector contract (manifest lookup, CTRF case check, unknown IDs) is in
`docs/TESTING_POLICY.md`; this is its shape:

```bash
#!/bin/bash
chown root:root /logs/verifier 2>/dev/null; chmod 755 /logs/verifier 2>/dev/null
echo 0 > /logs/verifier/reward.txt          # reward exists on every path from here on
# PER_RUN_LIMIT: stated in instruction.md; >= 10× the reference's measured per-run runtime (#57(a))
PER_RUN_LIMIT=<seconds>
UNTRUSTED="setpriv --reuid=12000 --regid=12000 --clear-groups --no-new-privs env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/work OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2 timeout -k 5 $PER_RUN_LIMIT"
kill_all() { pkill -9 -u 12000 2>/dev/null; while pgrep -u 12000 >/dev/null 2>&1; do pkill -9 -u 12000 2>/dev/null; sleep 0.2; done; }
find /app/out -type l -exec sh -c 'case "$(readlink -f -- "$1")" in /app/out|/app/out/*) exit 1;; esac' _ {} \; -delete   # Master #55: drop links escaping the artifact paths
# if the agent's code must be built/run first (Master #54):
#   cp -a /app/build /work/build && chown -R sandbox:sandbox /work/build   # /work stays root-owned
#   (cd /work/build && $UNTRUSTED <build or run the agent's code>)
#   kill_all
#   find /work/build -type l -exec sh -c 'case "$(readlink -f -- "$1")" in /work/build|/work/build/*) exit 1;; esac' _ {} \; -delete

case "${TBENCH_TEST_ID:-all}" in
  primary-behavior) selection="test_outputs.py::test_primary_behavior" ;;
  all)              selection="test_outputs.py" ;;
  *)                echo "unknown TBENCH_TEST_ID: $TBENCH_TEST_ID"; selection="" ;;
esac

if [ -n "$selection" ]; then
  # CTRF comes from tests/ctrf_reporter.py (replaces pytest-json-ctrf), wired as the scaffold does it
  cd /tests && python3 -m pytest -p ctrf_reporter --ctrf /logs/verifier/ctrf.json --tb=no -rN "$selection"
  rc=$?
  kill_all                                  # nothing the sandbox uid started survives (Master #56)
  rm -f /logs/verifier/reward.txt           # never write through a planted file or symlink
  if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
  else
    echo 0 > /logs/verifier/reward.txt
  fi
  # One line per failed case with its assertion message (Master #84)
  python3 -c '
import json
for t in json.load(open("/logs/verifier/ctrf.json"))["results"]["tests"]:
    if t["status"] != "passed":
        print(t["status"].upper(), t["name"], "-", t.get("message", ""))
' 2>/dev/null
fi

exit 0
```

No `set -e` (Master #39). Reward written on every path. The last command is `exit 0` —
the reward file, not the exit status, decides pass/fail. `--tb=no -rN` so no verifier source or expected value is printed; the failure
lines come from the `message` field `tests/ctrf_reporter.py` records (the assertion's
own message only), so a failing run's `test-stdout.txt` still names its cause (Master
#84, `docs/TESTING_POLICY.md` rule 7). No runtime installs.
