#!/usr/bin/env bash
# Step 3c launcher: five GPT-5.6 attempts at reasoning_effort=xhigh with full-fidelity
# capture, plus Oracle x3 and NOP x2 through the local recording adapters.
# Usage: scripts/run_step3c_eval.sh tasks/<task-name> [OUT-dir]
#
# Model attempts follow the STB full-fidelity kit (docs/reference/stb-full-fidelity-kit/):
#   model @openai/gpt-5.6, reasoning_effort xhigh, no truncated observation, every
#   prompt/reply stored, raw API request+response log, asciinema recording, console log,
#   and a digest-bound SOURCE.txt. A run at default effort or with a 10 000-byte cap is
#   not evidence of difficulty and is void.
# MODEL= / EFFORT= overrides exist for diagnostics only; archive_step3c.py rejects a round
# whose recorded effort is not xhigh.
#
# CONTROLS_ONLY=1 runs only oracle-1..3 and nop-1..2 (local harbor, same flags, no stb,
# no credential refresh) and writes task-digest.txt, agent/grader digests, SOURCE.txt and
# recording-source.sha256 exactly like a full round. Use it when the model trials come
# from one or more rounds without controls; scripts/compose_step3c.py then pools the first
# five fidelity-complete trials at this digest and run config (MASTER_CHECKLIST_TBSCI.md
# #94 item 1) and takes the controls from here. OUT defaults to ./evidence-<task>-controls.
# Workspace parking guard (config/round.toml): no model trials until the client has confirmed
# the checklist and the model. Overrides are not offered on purpose.
ROUND_CFG="$(cd "$(dirname "$0")/.." && pwd)/config/round.toml"
if ! grep -qE '^status *= *"CONFIRMED"' "$ROUND_CFG" 2>/dev/null; then
  echo "ABORT: config/round.toml status is not CONFIRMED; Step 3c is parked (docs/CLIENT_CHECKLIST_DIFF.md)." >&2
  exit 3
fi

set -uo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 tasks/<task-name> [OUT-dir]" >&2
  exit 2
fi

# Legacy upstream compatibility variables consumed by scripts/recording.py and the
# patched stb-bundled Harbor (scripts/patch_stb_harbor.py).
export TERMINUS_MAX_OUTPUT_BYTES=100000000
export TERMINUS_RAW_API_LOG=1
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
unset TBENCH_TEST_ID

TASK="$(realpath "$1")"
SLUG="$(basename "$TASK")"
CONTROLS_ONLY="${CONTROLS_ONLY:-0}"
if [ "$CONTROLS_ONLY" = "1" ]; then
  OUT="${2:-./evidence-$SLUG-controls}"
else
  OUT="${2:-./evidence-$SLUG}"
fi
MODEL="${MODEL:-@openai/gpt-5.6}"
EFFORT="${EFFORT:-xhigh}"

if [ -e "$OUT" ]; then
  echo "Choose a fresh OUT directory for this round: $OUT already exists" >&2
  exit 2
fi

# The raw API log and the lifted observation cap live in the Harbor copy bundled
# inside stb. Any `uv tool install snorkelai-stb ... --reinstall` -- including the one
# stb itself prints when it blocks on an outdated version -- silently reverts the patch,
# so the guard runs before every model attempt and once after the last, not only here
# (docs/reference/stb-full-fidelity-kit/HARBOR-0.23-PORT.md). --check verifies source
# markers, imported modules, harbor version and content digests, not behaviour alone.
patch_guard() {
  local label="$1" out rc
  out="$(python3 scripts/patch_stb_harbor.py --check 2>&1)"
  rc=$?
  printf '%s patch guard (%s): rc=%s\n%s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$label" "$rc" "$out" \
    >> "${PATCH_LOG:-/dev/null}"
  if [ "$rc" -ne 0 ]; then
    printf '%s\n' "$out" >&2
    echo "stb-bundled harbor is not patched before $label — run: python3 scripts/patch_stb_harbor.py" >&2
    return 1
  fi
}
if [ "$CONTROLS_ONLY" = "1" ]; then
  # Controls run on local harbor and never touch the stb-bundled copy; the guard result is
  # only recorded (SOURCE.txt), so a controls-only round never blocks on it.
  if patch_guard preflight 2>/dev/null; then BUNDLED_PATCHED=yes; else BUNDLED_PATCHED=no; fi
else
  patch_guard preflight || exit 3
  BUNDLED_PATCHED=yes
  python3 scripts/patch_stb_harbor.py --check-agent \
    || { echo "the Step 3c --ak set does not validate against scripts.harbor_recording:RecordingTerminus2" >&2; exit 3; }
fi

# Credential policy (workspace rule): a key from `stb keys refresh` carries a $10 budget
# and lasts 30 days, and the account allows only 20 refreshes; every refresh also revokes
# the previous key, which kills the trials of any other round still running on it. So the
# key is NEVER refreshed before an attempt. scripts/stb_key_guard.py `ensure` probes the
# stored key with a ~20-token completion before each attempt (under a machine-wide lock)
# and refreshes it only when the gateway rejects it for its usage limit (Portkey error
# code 04). An invalid or expired key stops the round for the operator instead. Every
# refresh is logged with key fingerprints in ~/.cache/tb4-workflow/stb-key-ledger.jsonl
# and in $OUT/keys-refresh.log. `stb keys verify` alone cannot see an exhausted budget
# (it only lists models), which is why the probe exists.
#
# STB_KEYS_NO_REFRESH=1 keeps the probe but forbids even the exhaustion refresh: the
# round stops before an attempt once the key's budget is gone.
refresh_keys() {
  local label="$1" extra=()
  [ "${STB_KEYS_NO_REFRESH:-0}" = "1" ] && extra=(--no-refresh)
  python3 scripts/stb_key_guard.py ensure --label "$label" --log "${KEYS_LOG:-/dev/null}" ${extra[@]+"${extra[@]}"}
}
if [ "$CONTROLS_ONLY" != "1" ]; then
  refresh_keys preflight || exit 2
fi

mkdir -p "$OUT"
KEYS_LOG="$OUT/keys-refresh.log"
PATCH_LOG="$OUT/patch-guard.log"
sha256sum scripts/harbor_recording.py scripts/recording.py scripts/archive_step3c.py \
  scripts/check_trajectory.py scripts/patch_stb_harbor.py > "$OUT/recording-source.sha256"
python3 scripts/task_digest.py "$TASK" > "$OUT/task-digest.txt"
DIGEST="$(cat "$OUT/task-digest.txt")"
# Record the split digests alongside the full one. A descriptive [metadata] edit after
# this round exists (e.g. expert_time_estimate_hours, MASTER_CHECKLIST_TBSCI.md #94 item 4)
# moves the full digest while leaving both graded surfaces untouched. archive_step3c.py accepts that only when the round can prove its agent and
# grader digests still match, so a round without these files can never be archived
# afterwards (see docs/TBSCI_HARDENING_RULES.md 8.3).
python3 scripts/task_digest.py "$TASK" --part agent  > "$OUT/agent-digest.txt"
python3 scripts/task_digest.py "$TASK" --part grader > "$OUT/grader-digest.txt"
python3 scripts/prune_evidence.py docker --apply --reason "round $(basename "$OUT") started" >/dev/null 2>&1 || true
STB_VERSION="$(stb --version 2>/dev/null | awk '{print $NF}')"
HARBOR_VERSION="$(harbor --version 2>/dev/null | awk '{print $NF}')"
if [ "$CONTROLS_ONLY" = "1" ]; then
cat > "$OUT/SOURCE.txt" <<EOS
task $SLUG, task digest $DIGEST
model none, k=0 (controls-only round: no model attempts; model trials come from other rounds at this digest via scripts/compose_step3c.py)
controls oracle-1, oracle-2, oracle-3, nop-1, nop-2 via local harbor $HARBOR_VERSION (RecordingOracle / RecordingNop)
credential policy: not used (no model attempts)
arch $(uname -m), started $(date -u +'%Y-%m-%dT%H:%M:%SZ'), stb $STB_VERSION (bundled harbor patched: $BUNDLED_PATCHED), console logs $OUT/<job>.console.log
EOS
echo "controls-only round $OUT  task $SLUG  digest $DIGEST  (oracle x3, nop x2)"
else
cat > "$OUT/SOURCE.txt" <<EOS
task $SLUG, task digest $DIGEST
model $MODEL, reasoning_effort $EFFORT, k=5 (one Harbor job per attempt: ${SLUG}-gpt56-t1..t5), agent scripts.harbor_recording:RecordingTerminus2 via stb harbor
TERMINUS_MAX_OUTPUT_BYTES=$TERMINUS_MAX_OUTPUT_BYTES, max_output_bytes=0 (uncapped), store_all_messages=true, TERMINUS_RAW_API_LOG=1 (agent/api-calls.jsonl), recording.cast on
controls oracle-1, oracle-2, oracle-3, nop-1, nop-2 via local harbor $HARBOR_VERSION (RecordingOracle / RecordingNop)
credential policy: $([ "${STB_KEYS_NO_REFRESH:-0}" = "1" ] && echo 'probe before each attempt, never refreshed (STB_KEYS_NO_REFRESH=1)' || echo 'probe before each attempt; refreshed only on budget exhaustion (scripts/stb_key_guard.py)')
arch $(uname -m), started $(date -u +'%Y-%m-%dT%H:%M:%SZ'), stb $STB_VERSION (bundled harbor patched: yes), console logs $OUT/<job>.console.log
EOS
echo "round $OUT  task $SLUG  digest $DIGEST  model $MODEL  effort $EFFORT  k=5"
fi

# Model attempts go through stb (Portkey credentials + attribution headers);
# Oracle/NOP controls run on local Harbor and never touch stb.
run_logged() {
  local launcher="$1" job="$2"
  shift 2
  echo "=== Starting job: $job at $(date -u +'%Y-%m-%dT%H:%M:%SZ') ==="
  $launcher run "$@" --job-name "$job" --yes 2>&1 | tee "$OUT/$job.console.log"
  local codes=("${PIPESTATUS[@]}")
  printf 'harbor=%s\ntee=%s\n' "${codes[0]}" "${codes[1]}" > "$OUT/$job.exit-codes.txt"
  echo "=== Finished job: $job with harbor=${codes[0]} at $(date -u +'%Y-%m-%dT%H:%M:%SZ') ==="
}

# Five model attempts, one Harbor job each, retries disabled; the key is probed before
# each attempt and refreshed only when its budget is exhausted (stb_key_guard.py).
# A round that stops early (quota, operator stop) is not void by itself: its
# fidelity-complete trials are candidates for scripts/compose_step3c.py.
MODEL_ATTEMPTS="${MODEL_ATTEMPTS-1 2 3 4 5}"   # override only to top up a round that was stopped early (compose_step3c.py pools rounds)
[ "$CONTROLS_ONLY" = "1" ] && MODEL_ATTEMPTS=""
for i in $MODEL_ATTEMPTS; do
  refresh_keys "${SLUG}-gpt56-t${i}" || {
    echo "ABORT: no usable stb key before ${SLUG}-gpt56-t${i} (invalid/expired, budget exhausted with no refresh allowed, refresh quota reached, or gateway unreachable — see $OUT/keys-refresh.log). Round $OUT stopped before t${i}; its completed trials remain candidates for scripts/compose_step3c.py." | tee -a "$OUT/SOURCE.txt" >&2
    exit 4
  }
  patch_guard "${SLUG}-gpt56-t${i}" || {
    echo "ABORT: stb-bundled harbor lost its full-fidelity patch before ${SLUG}-gpt56-t${i}; the attempt would run capped with no api-calls.jsonl. Round $OUT stopped before t${i}; re-patch, and check its completed trials with scripts/check_trajectory.py before pooling them." | tee -a "$OUT/SOURCE.txt" >&2
    exit 3
  }
  run_logged "stb harbor" "${SLUG}-gpt56-t${i}" -p "$TASK" -a scripts.harbor_recording:RecordingTerminus2 \
    -m "$MODEL" -n 1 --max-retries 0 \
    --ak max_output_bytes=0 --ak reasoning_effort="$EFFORT" --ak store_all_messages=true -o "$OUT"
done
if [ "$CONTROLS_ONLY" != "1" ]; then
  patch_guard "after ${SLUG}-gpt56-t5" || {
    echo "stb-bundled harbor lost its full-fidelity patch during the round; check every attempt's recording_config.json and api-calls.jsonl" | tee -a "$OUT/SOURCE.txt" >&2
  }
fi

# Baseline controls with execution traces.
run_logged harbor oracle-1 -p "$TASK" -a scripts.harbor_recording:RecordingOracle -n 1 --max-retries 0 -o "$OUT"
run_logged harbor oracle-2 -p "$TASK" -a scripts.harbor_recording:RecordingOracle -n 1 --max-retries 0 -o "$OUT"
run_logged harbor oracle-3 -p "$TASK" -a scripts.harbor_recording:RecordingOracle -n 1 --max-retries 0 -o "$OUT"
run_logged harbor nop-1 -p "$TASK" -a scripts.harbor_recording:RecordingNop -n 1 --max-retries 0 -o "$OUT"
# docs/DELIVERY_CHECKLIST.md requires NOP x2: two separate no-op runs, each reward 0.0
# with every test failing. One NOP cannot show the zero is reproducible.
run_logged harbor nop-2 -p "$TASK" -a scripts.harbor_recording:RecordingNop -n 1 --max-retries 0 -o "$OUT"

echo "finished $(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$OUT/SOURCE.txt"

if [ "$CONTROLS_ONLY" = "1" ]; then
  echo "=== All 5 controls completed at $(date -u +'%Y-%m-%dT%H:%M:%SZ') ==="
  # Oracle must reward 1.0 and NOP 0.0; the full per-test reading happens in
  # audit_step3c.py (composed round) and package_task.py. Missing rewards fail here.
  CONTROLS_RC=0
  for job in oracle-1 oracle-2 oracle-3 nop-1 nop-2; do
    reward="$(cat "$OUT/$job"/*/verifier/reward.txt 2>/dev/null | head -1)"
    case "$job:$reward" in
      oracle-*:1|oracle-*:1.0|nop-*:0|nop-*:0.0) verdict=OK ;;
      *) verdict=BAD; CONTROLS_RC=1 ;;
    esac
    echo "$verdict $job: reward=${reward:-missing}"
  done | tee "$OUT/controls-check.log"
  grep -q '^BAD' "$OUT/controls-check.log" && CONTROLS_RC=1
  echo "SUMMARY $(basename "$OUT"): controls $([ "$CONTROLS_RC" -eq 0 ] && echo PASS || echo FAIL)" | tee -a "$OUT/controls-check.log"
  exit "$CONTROLS_RC"
fi
echo "=== All 10 trials completed at $(date -u +'%Y-%m-%dT%H:%M:%SZ') ==="

# Fidelity check on the five model attempts; the last line must read
# "SUMMARY <OUT>: x/5 solved; fidelity PASS". On FAIL the BAD trials are never evidence;
# the OK ones remain candidates for scripts/compose_step3c.py (Master #94 item 1).
python3 scripts/check_trajectory.py "$OUT" --effort "$EFFORT" | tee "$OUT/fidelity-check.log"
FIDELITY=${PIPESTATUS[0]}
if [ "$FIDELITY" -eq 0 ]; then
  # Workspace disk rule: only a round that ends fidelity PASS retires this task's stale
  # rounds (other digests, not in a live regrade chain, not behind a built candidate),
  # with their task-local copies and zips. A round that dies early deletes nothing.
  python3 scripts/prune_evidence.py rounds --task-dir "$TASK" --exclude "$(basename "$OUT")" --apply \
    --reason "round $(basename "$OUT") fidelity PASS" | head -n 1 || true
fi
if [ "$FIDELITY" -ne 0 ]; then
  echo "fidelity FAIL — this round cannot be archived as it stands. The BAD trials are not candidates; the OK ones still are: fix the cause, run another round at this digest, and pool with scripts/compose_step3c.py (first five fidelity-complete trials in launch order)" >&2
fi
exit "$FIDELITY"
