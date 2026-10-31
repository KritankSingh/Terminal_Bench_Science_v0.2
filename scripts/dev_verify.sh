#!/usr/bin/env bash
# dev_verify.sh — local dry run of the Harbor separate-verifier flow before any Harbor job.
#
# Usage:
#   scripts/dev_verify.sh tasks/<task> [--keep-image] [--extra '<shell snippet>']
#
# What it does:
#   1. docker build tasks/<task>/tests/ as image dev-verify-<slug>
#   2. If environment/Dockerfile exists and solution/data does not (Harbor oracle:
#      inputs and language deps live only in the agent image), two-phase:
#        a. docker build tasks/<task>/environment as dev-verify-<slug>-agent
#        b. run bash /solution/solve.sh in that image with /solution mounted
#        c. copy /app/output into the verifier image and run tests/test.sh there
#      Otherwise the original combined-container path: solve.sh and test.sh both
#      run in the verifier image (solve.sh must then be self-contained given
#      /solution/* plus what tests/Dockerfile provides under /app).
#   3. print /logs/verifier/reward.txt, the CTRF summary and per-case status
#   4. remove the image(s) unless --keep-image
#
# Exit status: 0 iff /logs/verifier/reward.txt == 1 (and every step could run);
#              2 for usage/build errors; 1 otherwise.
#
# Contract notes:
#   * Harbor's Oracle runs in the agent image; the separate verifier only sees
#     declared artifacts. The two-phase path matches that. The combined path is
#     kept for tasks that still ship a /solution/data fallback for the dry run.
#   * TBENCH_TEST_ID is never inherited into the container, so the full suite runs.
#   * Processes that solve.sh leaves running are killed before test.sh, because
#     Harbor's separate verifier container never sees agent-side processes. A
#     control that depends on a lingering agent process (NC-06b) is therefore only
#     evidence when run through Harbor (gate_step2b.sh), not through this dry run.
#   * Nothing under tasks/ is modified; /solution is mounted read-only.
set -uo pipefail

usage() {
  sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

TASK_ARG=""
KEEP_IMAGE=0
EXTRA=""
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --keep-image) KEEP_IMAGE=1; shift ;;
    --extra)
      [ $# -ge 2 ] || { echo "error: --extra requires a shell snippet" >&2; exit 2; }
      EXTRA="$2"; shift 2 ;;
    --extra=*) EXTRA="${1#--extra=}"; shift ;;
    --) shift; break ;;
    -*) echo "error: unknown option: $1" >&2; usage >&2; exit 2 ;;
    *)
      if [ -n "$TASK_ARG" ]; then echo "error: unexpected argument: $1" >&2; exit 2; fi
      TASK_ARG="$1"; shift ;;
  esac
done
[ -n "$TASK_ARG" ] || { usage >&2; exit 2; }

TASK="$(realpath -e "$TASK_ARG" 2>/dev/null)" || { echo "error: task directory not found: $TASK_ARG" >&2; exit 2; }
SLUG="$(basename "$TASK")"
for rel in task.toml tests/Dockerfile tests/test.sh solution/solve.sh; do
  [ -f "$TASK/$rel" ] || { echo "error: missing $rel under $TASK" >&2; exit 2; }
done
command -v docker >/dev/null 2>&1 || { echo "error: docker is required" >&2; exit 2; }

IMAGE="dev-verify-${SLUG}"
AGENT_IMAGE="dev-verify-${SLUG}-agent"
TWO_PHASE=0
if [ -f "$TASK/environment/Dockerfile" ] && [ ! -d "$TASK/solution/data" ]; then
  TWO_PHASE=1
fi
T_START=$(date +%s)
echo "== dev_verify: task=$TASK"
if [ "$TWO_PHASE" -eq 1 ]; then
  echo "== dev_verify: two-phase (solve in agent image $AGENT_IMAGE, test in $IMAGE)"
else
  echo "== dev_verify: image=$IMAGE (verifier image from tests/Dockerfile; solve.sh must be self-contained)"
fi

BUILD_LOG="$(mktemp "${TMPDIR:-/tmp}/dev-verify-build.XXXXXX")"
WORKDIR=""
SOLVE_CTR=""
cleanup() {
  rm -f "$BUILD_LOG"
  [ -n "$SOLVE_CTR" ] && docker rm -f "$SOLVE_CTR" >/dev/null 2>&1 || true
  [ -n "$WORKDIR" ] && rm -rf "$WORKDIR"
  if [ "$KEEP_IMAGE" -eq 0 ]; then
    docker rmi -f "$IMAGE" >/dev/null 2>&1 && echo "== dev_verify: removed image $IMAGE"
    if [ "$TWO_PHASE" -eq 1 ]; then
      docker rmi -f "$AGENT_IMAGE" >/dev/null 2>&1 && echo "== dev_verify: removed image $AGENT_IMAGE"
    fi
  else
    echo "== dev_verify: kept image $IMAGE (--keep-image)"
    [ "$TWO_PHASE" -eq 1 ] && echo "== dev_verify: kept image $AGENT_IMAGE (--keep-image)"
  fi
}
trap cleanup EXIT

echo "== dev_verify: docker build $TASK/tests -> $IMAGE"
T_BUILD0=$(date +%s)
if ! docker build -t "$IMAGE" "$TASK/tests" >"$BUILD_LOG" 2>&1; then
  echo "== dev_verify: docker build FAILED (last 40 lines):"
  tail -n 40 "$BUILD_LOG"
  exit 2
fi
T_BUILD1=$(date +%s)
echo "== dev_verify: image built in $((T_BUILD1 - T_BUILD0))s"

read -r -d '' VERIFY_INNER <<'INNER_EOF'
set -uo pipefail
unset TBENCH_TEST_ID
mkdir -p /logs/verifier /tmp/dev-verify
T0=$(date +%s)
if [ "${DEV_VERIFY_SKIP_SOLVE:-0}" != "1" ]; then
  echo "== [container] bash /solution/solve.sh"
  bash /solution/solve.sh >/tmp/dev-verify/solve.log 2>&1
  SOLVE_RC=$?
  T1=$(date +%s)
  echo "== [container] solve.sh exit=$SOLVE_RC in $((T1 - T0))s; last 20 lines:"
  tail -n 20 /tmp/dev-verify/solve.log | sed 's/^/   | /'
else
  T1=$T0
  echo "== [container] solve.sh already ran in the agent image; artifacts mounted at /app/output"
fi
# Harbor's separate verifier never sees processes left behind in the agent container
# (e.g. a detached reward-writer loop); mirror that by killing every stray process
# before the verifier phase. Only this shell (PID $$) survives.
STRAY=0
for pid in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  [ "$pid" = "$$" ] && continue
  [ -d "/proc/$pid" ] || continue
  kill -9 "$pid" 2>/dev/null && STRAY=$((STRAY + 1))
done
echo "== [container] stray agent-side processes killed before verification: $STRAY (Harbor's separate verifier never sees them)"
echo "== [container] cd /app && bash /tests/test.sh"
( cd /app && bash /tests/test.sh ) >/tmp/dev-verify/test.log 2>&1
TEST_RC=$?
T2=$(date +%s)
echo "== [container] test.sh exit=$TEST_RC in $((T2 - T1))s; last 60 lines:"
tail -n 60 /tmp/dev-verify/test.log | sed 's/^/   | /'
REWARD="$(cat /logs/verifier/reward.txt 2>/dev/null || echo '<missing>')"
echo "== [container] /logs/verifier/reward.txt = ${REWARD}"
if [ -f /logs/verifier/ctrf.json ]; then
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY'
import json
try:
    data = json.load(open("/logs/verifier/ctrf.json"))
    results = data["results"]
    summary = results.get("summary", {})
    keys = ("tests", "passed", "failed", "skipped", "pending", "other")
    print("== [container] CTRF summary:", ", ".join(f"{k}={summary.get(k)}" for k in keys),
          f"collection_errors={results.get('collection_errors', 0)}")
    for case in results.get("tests", []):
        raw = case.get('raw_status') or ''
        print(f"   {case.get('status', '?'):8s} {case.get('name')}" + (f"  ({raw})" if raw else ''))
except Exception as exc:  # noqa: BLE001 - diagnostics only
    print(f"== [container] CTRF parse error: {exc}")
PY
  else
    echo "== [container] CTRF (python3 unavailable in verifier image; raw):"
    cat /logs/verifier/ctrf.json
  fi
else
  echo "== [container] /logs/verifier/ctrf.json is MISSING"
fi
echo "== [container] wall time: solve=$((T1 - T0))s verify=$((T2 - T1))s total=$((T2 - T0))s"
if [ -n "${DEV_VERIFY_EXTRA:-}" ]; then
  echo "== [container] --extra diagnostics:"
  ( eval "$DEV_VERIFY_EXTRA" ) 2>&1 | sed 's/^/   | /'
fi
[ "$REWARD" = "1" ]
INNER_EOF

if [ "$TWO_PHASE" -eq 1 ]; then
  echo "== dev_verify: docker build $TASK/environment -> $AGENT_IMAGE"
  T_AB0=$(date +%s)
  if ! docker build -t "$AGENT_IMAGE" "$TASK/environment" >"$BUILD_LOG" 2>&1; then
    echo "== dev_verify: agent image build FAILED (last 40 lines):"
    tail -n 40 "$BUILD_LOG"
    exit 2
  fi
  T_AB1=$(date +%s)
  echo "== dev_verify: agent image built in $((T_AB1 - T_AB0))s"

  WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/dev-verify-${SLUG}.XXXXXX")"
  mkdir -p "$WORKDIR/output"
  SOLVE_CTR="dev-verify-${SLUG}-solve-$$"
  echo "== [container] bash /solution/solve.sh (agent image)"
  T_S0=$(date +%s)
  docker run --name "$SOLVE_CTR" \
    -v "$TASK/solution:/solution:ro" \
    "$AGENT_IMAGE" \
    bash /solution/solve.sh >"$WORKDIR/solve.log" 2>&1
  SOLVE_RC=$?
  T_S1=$(date +%s)
  echo "== [container] solve.sh exit=$SOLVE_RC in $((T_S1 - T_S0))s; last 20 lines:"
  tail -n 20 "$WORKDIR/solve.log" | sed 's/^/   | /'
  docker cp "$SOLVE_CTR:/app/output/." "$WORKDIR/output/" 2>/dev/null || true
  docker rm -f "$SOLVE_CTR" >/dev/null 2>&1 || true
  SOLVE_CTR=""

  docker run --rm \
    -e DEV_VERIFY_EXTRA="$EXTRA" \
    -e DEV_VERIFY_SKIP_SOLVE=1 \
    -v "$WORKDIR/output:/app/output" \
    "$IMAGE" bash -c "$VERIFY_INNER"
  RUN_RC=$?
else
  docker run --rm \
    -e DEV_VERIFY_EXTRA="$EXTRA" \
    -v "$TASK/solution:/solution:ro" \
    "$IMAGE" bash -c "$VERIFY_INNER"
  RUN_RC=$?
fi

T_END=$(date +%s)
echo "== dev_verify: total wall time $((T_END - T_START))s (build $((T_BUILD1 - T_BUILD0))s)"
if [ "$RUN_RC" -eq 0 ]; then
  echo "== dev_verify: RESULT reward=1 -> PASS"
  exit 0
fi
echo "== dev_verify: RESULT reward!=1 (docker run exit $RUN_RC) -> FAIL"
exit 1
