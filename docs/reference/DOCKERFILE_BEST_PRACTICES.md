# Dockerfile & Image Best Practices (Terminal-Bench Science)

`MASTER_CHECKLIST_TBSCI.md` (repo root) is the source of truth — chiefly
Master #23, #24, #26, #36, #37, #38, #100, #64 and #106 — and wins where this
page differs. Upstream sources paraphrased here: `CONTRIBUTING.md`
("Environment", "Hosting large task data") and the upstream Dockerfile CI checks
reviewed in the v4 workspace's CI_CHECKS_REVIEW notes (not carried here). (The Terminal-Bench 4 portal guide under
`docs/archive/tb4-portal/` is archived TB4 reference, not current guidance.)

The bundled auditor (`tools/final-tbsci-audit-master/`) checks both images and is
enforced at the Step 2b gate (`scripts/audit_task.py tree`, step c1, blocking)
and at Step 4 (`audit_task.py package` on the candidate ZIP, then the auditor's
judged review before `package_task.py --promote`). `scripts/hardening_check.py`
enforces the mechanical parts of #26, #38, #64 and #106. The rules below already
include their image rules.

## Agent image (`environment/Dockerfile`)

1. Digest-pin every `FROM` and compose `image:` with `@sha256:<digest>` (#26)
2. Final runtime base: a canonical ECR image,
   `public.ecr.aws/docker/library/<python|node|golang|rust|eclipse-temurin|gcc|ruby|maven|debian|ubuntu>@sha256:…`,
   **or** a brief credible comment in the Dockerfile justifying why no
   canonical image works (#26) — e.g. a domain toolchain that only ships as a
   vendor image. The auditor screen reports a non-canonical final base with no
   such comment as MAJOR (`T3-BASE`), and the gate fails on it.
3. Install `tmux` and `asciinema` explicitly (#26)
4. **Language packages pinned to exact versions** — pip/uv `==`, npm exact,
   cargo `=`, go module versions, R/conda exact. That includes the scientific
   stack itself: `numpy`, `scipy`, `pandas` and every domain library
   (`astropy`, `biopython`, `scanpy`, `rdkit`, `xarray`, `mne`, …) are pinned
   `==`, never left to float with whatever the index serves on build day
   (#26, #106; upstream `check-pip-pinning.sh`). **apt packages installed
   WITHOUT version pins** (they go stale and break the build) — the opposite
   instinct, easy to get backwards; `scripts/hardening_check.py` flags both
   mistakes (#26)
5. apt hygiene (#106; upstream `check-dockerfile-sanity.sh`): `apt-get update`
   in the same `RUN` as `apt-get install -y --no-install-recommends`, then
   `rm -rf /var/lib/apt/lists/*`; set `DEBIAN_FRONTEND=noninteractive`
6. Do not `COPY`/`ADD` `solution/` or `tests/` into the agent image at any
   layer — including a `COPY` of a parent directory that contains them (#24) —
   and never name `solve.sh`, `test.sh` or `test_*.py` anywhere in
   `environment/Dockerfile` (#24, #106; upstream `check-dockerfile-references.sh`)
7. Do not create, copy to, modify, chown or chmod `/tests`, `/solution`,
   `/oracle`, `/logs/verifier`, `/logs/artifacts` (#24)
8. Build context ≤100 MiB total; no file >50 MiB; add `.dockerignore` when
   non-trivial (#26). Larger data is fetched at build time (below), not committed
9. No `--privileged`, docker.sock, or dangerous capabilities (#26)
10. No host bind mounts: an `environment/docker-compose.yaml` volume uses named
    volumes only, never a host path as its source (#106; upstream
    `check-compose-host-binds.sh`)
11. Portability (#26, #106; upstream `check-dockerfile-platform.sh`): no
    `FROM --platform=...` pin, and no silent amd64-only artifact. When a
    prebuilt binary or wheel is arch-specific, select it from `uname -m`
    (`x86_64` / `aarch64`) and verify a checksum per architecture, or build
    from source as the fallback
12. No bare `nproc` in any Dockerfile, `solve.sh` or `test.sh` — inside a
    container it returns the **host** CPU count, so thread counts and results
    vary by machine. Use a fixed value sized to `[environment].cpus` (e.g.
    `make -j2`, `OMP_NUM_THREADS=2`); `nproc --all` / `--help` are allowed
    (#106; upstream `check-nproc.sh`)
13. Bake task data into the image at build time; no runtime URL fetches for
    content (#26, #100)
14. Vendored archives (wheels, `.deb`s, tarballs) carry no host username or
    path — re-tar with `--owner=0 --group=0` (#23)
15. No AI scaffolding filenames in the image
16. Build it cold once (`--no-cache`) and confirm the Oracle passes on that
    image (#36); for a stochastic workflow, fix seeds and confirm repeated
    Oracle runs agree (#106)

### Pinned scientific stack (shape)

```dockerfile
FROM public.ecr.aws/docker/library/python:3.12-slim-bookworm@sha256:<digest>

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends tmux asciinema curl ca-certificates libhdf5-dev \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
      numpy==<x.y.z> scipy==<x.y.z> pandas==<x.y.z> \
      <domain-lib>==<x.y.z>

ENV OMP_NUM_THREADS=2
WORKDIR /app
COPY data/ /app/data/
```

Pick versions that are mutually compatible on the base's Python and record
them once; the numbers above are placeholders, not recommendations.

### Build-time data fetch (Master #100)

Data too large for `environment/` (over the 100 MiB / 50 MiB limits) — or
model weights — is downloaded **during the build**, never by the agent, the
solution or the verifier at trial time. Two locks make the fetch reproducible
(upstream `CONTRIBUTING.md` "Hosting large task data",
`rubrics/task-implementation.toml` `deterministic_reproducible`):

- an **immutable revision written as a literal** in the Dockerfile — a full
  commit SHA, DOI-versioned record or content-addressed URL; never `main`, a
  tag, a "latest" link, or a value supplied through `ARG`/`--build-arg`;
- a **sha256 checksum verified in the same build step**, so a host that serves
  different bytes fails the build instead of silently changing the task.

```dockerfile
RUN mkdir -p /app/data \
 && curl -fsSL -o /tmp/input.tar.gz \
      "https://<host>/<dataset>/resolve/<full-commit-sha>/<task>/input.tar.gz" \
 && echo "<sha256>  /tmp/input.tar.gz" | sha256sum -c - \
 && tar -xzf /tmp/input.tar.gz -C /app/data \
 && rm /tmp/input.tar.gz
```

For private delivery any stable host is acceptable (upstream requires its own org
dataset; that rule exists for a public benchmark). Record the source,
revision, checksum, licence and any preprocessing in
`authoring/<task>/provenance/` and name the source in
`authoring/<task>/write-ups.md` (#99, #100).
Prefer a host you control: a pinned revision protects content, not
availability. Fetch model weights the same way and point the loader at the
local path; a `from_pretrained(...)`-style first-use download makes every trial
depend on a live service.

## Verifier image (`tests/Dockerfile`)

1. Digest-pin base
2. Bake pytest and every verifier dependency at exact versions — including any
   scientific library the tests use to recompute values — **no trial-time
   installs or fetches** in `tests/test.sh` (#38)
3. `COPY . /tests/` (build context is `tests/`)
4. `RUN mkdir -p` parent dirs for every declared artifact path (#37)
5. **Grader-only data lands here and only here** — expected values, truth
   labels, held-out instances. A build-time fetch follows the same two locks as
   above and pulls only the verification payload; it is never pulled into the
   agent image or `/app` (#45, #100)
6. Same hygiene as the agent image for pins, apt, `nproc` and size
7. The verifier phase runs with `[verifier.environment].network_mode =
   "no-network"` declared in `task.toml` (#64), so everything it needs
   must already be in the image
8. End with the master's Appendix A step 1, as given (#54): `apt-get install -y
   --no-install-recommends util-linux procps`, then `useradd --uid 12000
   --user-group --no-create-home --shell /usr/sbin/nologin sandbox`, `mkdir -p
   /logs/verifier /work`, `chown -R root:root /tests /logs/verifier /work`, `chmod -R
   go-rwx /tests`, `chmod 755 /logs/verifier /work` — `/work` stays root-owned;
   agent code the verifier runs as uid 12000 cannot read fixtures, expected values
   or a reference implementation. On Alpine use `apk add util-linux procps shadow`.
   These lines go only in `tests/Dockerfile`; in `environment/Dockerfile` they
   violate #24. The auditor reports a missing seal as MAJOR (`T3-SEAL`) whether
   or not the verifier executes agent code.

## Layer order (typical)

OS packages → runtime/tooling → pinned scientific stack → build-time data fetch
(checksum-verified) → source/task files → task-specific build.
