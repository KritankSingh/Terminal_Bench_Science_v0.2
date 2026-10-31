#!/usr/bin/env bash
# gate_step2b.sh — the whole Step 2b mechanical gate as one command.
#
# Usage:
#   scripts/gate_step2b.sh tasks/<task> [--out <dir>] [--with-nc] [--nc-only]
#                          [--reseal-only] [--foreground]
#
# By default the gate re-executes itself detached (setsid nohup ... &), prints the OUT
# directory and returns immediately, so it survives the 10-minute tool timeout of an
# agent shell. Follow it with `tail -f <OUT>/progress`; the last line is
# `VERDICT: PASS|FAIL`. Use --foreground to run inline (blocking).
#
# OUT defaults to authoring/<slug>/evidence/step2b-<YYYYmmdd-HHMMSS>; an existing OUT is
# refused so evidence from different digests is never mixed. Every step writes its log
# to $OUT and appends one line to $OUT/progress:
#   (a) doctor.py --strict-tools                      -> doctor.log
#   (b) task_check.py --strict (abort on FAIL)        -> task_check.log
#   (c) hardening_check.py                            -> hardening_check.log
#   (c1) audit_task.py tree: tools/final-tbsci-audit-master's static screen on the task
#       staged in delivery layout; any BLOCKER/MAJOR/MINOR aborts   -> auditor-tree.log
#   (c2) master_checklist.py auto (informational: mechanical findings + review leads per
#       MASTER_CHECKLIST_TBSCI.md check; creates authoring/<slug>/master-checklist.md
#       with `init` if absent)                        -> master-checklist-auto.log
#   (d) task_digest.py                                -> task-digest.txt
#   (e) dev_verify.sh --keep-image (abort unless reward == 1) -> dev_verify.log
#   (f) per_test_gate.py --agents oracle,nop --jobs N -> per_test_gate.console.log,
#       jobs in $OUT/per-test, report artifacts/gates/<slug>/per-test-step2b-<stamp>.json
#   (g) evidence.py seal -> artifacts/gates/<slug>/step2b.json     -> evidence-seal.log
#   (h) evidence.py check (abort unless PASS)                      -> evidence-check.log
#   (i) only with --with-nc: stage_controls.sh -> $OUT/nc, then one local
#       `harbor run -p <copy> -a scripts.harbor_recording:RecordingOracle -k 1 -n 1
#        --max-retries 0 -o $OUT --job-name nc-XX --yes` per control
#       (console log + exit-codes file per job, PYTHONPATH=$PWD, TBENCH_TEST_ID unset)
#   (j) controls_report.py --write                    -> controls_report.md (+ controls.md section)
#   (k) one-screen summary and `VERDICT: PASS|FAIL` in $OUT/progress
#       (PASS = seal PASS and every NC reward 0, Harbor exit 0, no exception, rejected
#       through a case named in the controls.md plan).
#
# --nc-only skips (a)-(h); it requires an existing seal (artifacts/gates/<slug>/step2b.json)
# that checks PASS for the current task digest, then runs (i)-(k).
# --reseal-only runs (b)-(d) and then `evidence.py reseal` + `evidence.py check` in place
# of (e)-(h): no dev_verify, no per-test matrix, no controls. It exists for ONE edit --
# a descriptive `[metadata]`-only change to task.toml, such as correcting
# expert_time_estimate_hours after a rerun (MASTER_CHECKLIST_TBSCI.md #94 item 4; task.toml
# carries no difficulty field, Master #62). Such an edit moves the FULL task digest while leaving the agent and the
# grader surfaces byte-identical, so re-running the per-test matrix would measure an
# unchanged grader against an unchanged Oracle and NOP: the result is determined, and the
# 8-55 minutes it costs buy nothing. `evidence.py reseal` REFUSES unless both graded
# digests are unchanged, so a behavioral edit lands back in the full gate. It still ends
# with `VERDICT: PASS|FAIL` in $OUT/progress.
#
# Negative controls are opt-in diagnostics (docs/PACKAGE_RULES.md rules 14-15): the
# gate PASSES on static checks + dev_verify + the per-test Oracle/NOP matrix + seal.
# --with-nc additionally stages and runs the control matrix and writes controls.md.
#
# Speed tuning lives in authoring/<slug>/gate.conf (outside tasks/, so it can never
# change a task digest). Plain KEY=VALUE lines, `#` comments, unknown keys ignored:
#   jobs=3                                  how many Harbor jobs run at once (default 3)
#   exclusive_tests=peak-rss-large,...      manifest test IDs that must run alone
# `jobs` drives both the per-test matrix (--jobs) and the negative-control batch;
# `exclusive_tests` is passed through as --exclusive-test and is how a task whose
# verifier measures peak RSS or work-counter growth keeps those rows uncontended.
# Set jobs=1 for a task where any container contention would corrupt a measurement.
#
# Oracle/NOP/NC jobs run on local `harbor` against the native Docker socket, never stb.
set -uo pipefail

usage() { sed -n '2,60p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"

TASK_ARG=""
OUT=""
WITH_NC=0
NC_ONLY=0
RESEAL_ONLY=0
FOREGROUND=0
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --out) [ $# -ge 2 ] || { echo "error: --out requires a directory" >&2; exit 2; }; OUT="$2"; shift 2 ;;
    --out=*) OUT="${1#--out=}"; shift ;;
    --with-nc) WITH_NC=1; shift ;;
    --nc-only) NC_ONLY=1; shift ;;
    --reseal-only) RESEAL_ONLY=1; shift ;;
    --foreground) FOREGROUND=1; shift ;;
    --) shift; break ;;
    -*) echo "error: unknown option: $1" >&2; usage >&2; exit 2 ;;
    *) if [ -n "$TASK_ARG" ]; then echo "error: unexpected argument: $1" >&2; exit 2; fi; TASK_ARG="$1"; shift ;;
  esac
done
[ -n "$TASK_ARG" ] || { usage >&2; exit 2; }
if [ "$WITH_NC" -eq 1 ] && [ "$NC_ONLY" -eq 1 ]; then
  echo "error: --with-nc and --nc-only are mutually exclusive" >&2; exit 2
fi
# A reseal carries the existing matrix over unchanged; it never runs Harbor, so pairing it
# with a control matrix would be asking for evidence this mode is not entitled to produce.
if [ "$RESEAL_ONLY" -eq 1 ] && { [ "$WITH_NC" -eq 1 ] || [ "$NC_ONLY" -eq 1 ]; }; then
  echo "error: --reseal-only cannot be combined with --with-nc or --nc-only" >&2; exit 2
fi

cd "$REPO_ROOT" || exit 2
TASK="$(realpath -e "$TASK_ARG" 2>/dev/null)" || { echo "error: task directory not found: $TASK_ARG" >&2; exit 2; }
[ -f "$TASK/task.toml" ] || { echo "error: not a task tree (no task.toml): $TASK" >&2; exit 2; }
SLUG="$(basename "$TASK")"
STAMP="${GATE_STEP2B_STAMP:-$(date +%Y%m%d-%H%M%S)}"
export GATE_STEP2B_STAMP="$STAMP"
[ -n "$OUT" ] || OUT="authoring/$SLUG/evidence/step2b-$STAMP"
OUT="$(realpath -m "$OUT")"
case "$OUT/" in
  "$TASK/"*|"$REPO_ROOT/tasks/"*) echo "error: OUT must be outside tasks/: $OUT" >&2; exit 2 ;;
esac

# The detached child inherits an OUT that the parent just created (holding only the
# launcher log); everybody else must get a fresh directory.
if [ "${GATE_STEP2B_DETACHED:-0}" != "1" ] && [ -e "$OUT" ]; then
  echo "error: OUT already exists; choose a fresh directory for this round: $OUT" >&2
  exit 2
fi
mkdir -p "$OUT" || exit 2

if [ "$FOREGROUND" -eq 0 ] && [ "${GATE_STEP2B_DETACHED:-0}" != "1" ]; then
  child_args=("$TASK" --out "$OUT" --foreground)
  [ "$WITH_NC" -eq 1 ] && child_args+=(--with-nc)
  [ "$NC_ONLY" -eq 1 ] && child_args+=(--nc-only)
  [ "$RESEAL_ONLY" -eq 1 ] && child_args+=(--reseal-only)
  {
    echo "launched: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo "command: $SCRIPT_PATH ${child_args[*]}"
    echo "cwd: $REPO_ROOT"
  } > "$OUT/launcher.txt"
  GATE_STEP2B_DETACHED=1 setsid nohup bash "$SCRIPT_PATH" "${child_args[@]}" > "$OUT/gate.nohup.log" 2>&1 < /dev/null &
  child=$!
  echo "$child" > "$OUT/gate.pid"
  echo "Step 2b gate started detached (pid $child)."
  echo "OUT:      $OUT"
  echo "Progress: tail -f \"$OUT/progress\"      (last line: VERDICT: PASS|FAIL)"
  echo "Console:  tail -f \"$OUT/gate.nohup.log\""
  exit 0
fi

# ---------------------------------------------------------------------------------
# Foreground execution (inline or as the detached child).
# ---------------------------------------------------------------------------------
if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.venv/bin/activate"
fi
unset TBENCH_TEST_ID
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
# Legacy upstream compatibility variable consumed by scripts/recording.py.
export TERMINUS_MAX_OUTPUT_BYTES="${TERMINUS_MAX_OUTPUT_BYTES:-10000000}"

PROGRESS="$OUT/progress"
GATES="$REPO_ROOT/artifacts/gates/$SLUG"
PER_TEST_REPORT="$GATES/per-test-step2b-$STAMP.json"
SEAL="$GATES/step2b.json"
mkdir -p "$GATES"
VERDICT_REASON=""

log() { printf '[%s] %s\n' "$(date -u +'%H:%M:%S')" "$*" | tee -a "$PROGRESS"; }

finish() {
  local verdict="$1"
  echo "" | tee -a "$PROGRESS" >/dev/null
  log "SUMMARY task=$SLUG digest=${DIGEST:-unknown}"
  log "SUMMARY out=$OUT"
  log "SUMMARY seal=${SEAL_STATUS:-not run} per-test=${GATE_STATUS:-not run} nc=${NC_STATUS:-not run}"
  [ -n "$VERDICT_REASON" ] && log "SUMMARY reason: $VERDICT_REASON"
  echo "VERDICT: $verdict" | tee -a "$PROGRESS"
  # Workspace disk rule: once a verdict exists, this gate's staged control copies (nc/) and
  # the bulky payloads of the task's older gate OUTs are deleted (logs and reports stay).
  # Older gates are trimmed only after a PASS; Docker loses dangling images and build cache
  # above DOCKER_CACHE_KEEP (default 10GB). Tagged images (dev-verify-*) stay.
  { python3 "$REPO_ROOT/scripts/prune_evidence.py" gates --task-dir "$TASK" --keep-out "$OUT" --apply \
      --reason "gate $(basename "$OUT") finished"
    python3 "$REPO_ROOT/scripts/prune_evidence.py" docker --apply --reason "gate $(basename "$OUT") finished"
  } > "$OUT/prune.log" 2>&1 || true
  [ "$verdict" = "PASS" ]
  exit $?
}

{
  echo "gate: scripts/gate_step2b.sh"
  echo "task: $TASK"
  echo "out: $OUT"
  echo "stamp: $STAMP"
  echo "with_nc: $WITH_NC  nc_only: $NC_ONLY  reseal_only: $RESEAL_ONLY"
  echo "started: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  echo "harbor: $(command -v harbor || echo missing)  python: $(command -v python3)"
} > "$OUT/gate.env.txt"
log "start task=$SLUG out=$OUT stamp=$STAMP"

# Speed tuning: authoring/<slug>/gate.conf. Parsed line by line rather than sourced,
# so a config file can never execute anything.
GATE_CONF="$REPO_ROOT/authoring/$SLUG/gate.conf"
GATE_JOBS=3
GATE_EXCLUSIVE=""
if [ -f "$GATE_CONF" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"
    line="$(printf '%s' "$line" | tr -d '[:space:]')"
    [ -n "$line" ] || continue
    case "$line" in *=*) ;; *) log "gate.conf: ignoring malformed line: $line"; continue ;; esac
    key="${line%%=*}"
    value="${line#*=}"
    case "$key" in
      jobs) GATE_JOBS="$value" ;;
      exclusive_tests) GATE_EXCLUSIVE="$value" ;;
      *) log "gate.conf: ignoring unknown key: $key" ;;
    esac
  done < "$GATE_CONF"
fi
case "$GATE_JOBS" in
  ''|*[!0-9]*) echo "error: gate.conf: jobs must be a positive integer, got '$GATE_JOBS'" >&2
               VERDICT_REASON="gate.conf jobs is not a positive integer"; finish FAIL ;;
esac
[ "$GATE_JOBS" -ge 1 ] || { VERDICT_REASON="gate.conf jobs must be >= 1"; finish FAIL; }
PER_TEST_ARGS=(--agents oracle,nop --jobs "$GATE_JOBS")
if [ -n "$GATE_EXCLUSIVE" ]; then
  IFS=',' read -r -a gate_exclusive_ids <<< "$GATE_EXCLUSIVE"
  for id in "${gate_exclusive_ids[@]}"; do
    [ -n "$id" ] && PER_TEST_ARGS+=(--exclusive-test "$id")
  done
fi
if [ -f "$GATE_CONF" ]; then
  log "gate.conf: jobs=$GATE_JOBS exclusive_tests=${GATE_EXCLUSIVE:-<none>} (authoring/$SLUG/gate.conf)"
else
  log "gate.conf: absent; using defaults jobs=$GATE_JOBS exclusive_tests=<none>"
fi
{ echo "gate_conf: ${GATE_CONF}"; echo "jobs: $GATE_JOBS"; echo "exclusive_tests: ${GATE_EXCLUSIVE:-<none>}"; } >> "$OUT/gate.env.txt"

if [ "$RESEAL_ONLY" -eq 1 ]; then
  # Descriptive-only re-seal: the static screen still runs in full (it is the part that
  # can genuinely fail, since task_check validates the descriptive values), the measured
  # per-test matrix is carried over, and `evidence.py reseal` refuses if either graded
  # surface moved. doctor --strict-tools is skipped with the rest of the Harbor path:
  # this mode starts no container.
  log "reseal-only: static checks + evidence.py reseal; dev_verify, per-test matrix and controls skipped"

  # (b) task_check --strict
  python3 scripts/task_check.py "$TASK" --strict > "$OUT/task_check.log" 2>&1; rc=$?
  log "task_check --strict: $(head -n 1 "$OUT/task_check.log" 2>/dev/null) (exit $rc) -> task_check.log"
  if [ "$rc" -ne 0 ]; then VERDICT_REASON="task_check --strict FAIL"; finish FAIL; fi

  # (c) hardening_check
  python3 scripts/hardening_check.py "$TASK" > "$OUT/hardening_check.log" 2>&1; rc=$?
  log "hardening_check: $(grep -m1 '^summary:' "$OUT/hardening_check.log" 2>/dev/null || tail -n 1 "$OUT/hardening_check.log") (exit $rc) -> hardening_check.log"

  # (c1) the bundled TB-Science auditor on the task staged in delivery layout (abort on FAIL).
  # The reviewer runs this same tool on the ZIP at Step 4; every construction rule it
  # enforces must already hold here, so nothing it says can be new at the end.
  python3 scripts/audit_task.py tree "$TASK" --json-out "$OUT/auditor-tree.json" > "$OUT/auditor-tree.log" 2>&1; rc=$?
  log "auditor tree: $(head -n 1 "$OUT/auditor-tree.log" 2>/dev/null) (exit $rc) -> auditor-tree.log"
  if [ "$rc" -ne 0 ]; then VERDICT_REASON="TB-Science auditor (tree) FAIL"; finish FAIL; fi

  # (d) digest
  python3 scripts/task_digest.py "$TASK" > "$OUT/task-digest.txt" 2>"$OUT/task-digest.err"; rc=$?
  DIGEST="$(cat "$OUT/task-digest.txt" 2>/dev/null)"
  log "task_digest: ${DIGEST:-<failed>} (exit $rc) -> task-digest.txt"
  if [ "$rc" -ne 0 ] || [ -z "$DIGEST" ]; then VERDICT_REASON="task_digest failed"; finish FAIL; fi

  if [ ! -f "$SEAL" ]; then
    log "evidence reseal: no seal at $(realpath --relative-to="$REPO_ROOT" "$SEAL"); run the full gate first"
    VERDICT_REASON="--reseal-only requires an existing seal"; finish FAIL
  fi
  cp -p "$SEAL" "$OUT/step2b.before-reseal.json" 2>/dev/null

  # (r) reseal, in place of (e)-(g)
  python3 scripts/evidence.py reseal "$TASK" --evidence "$SEAL" > "$OUT/evidence-reseal.log" 2>&1; rc=$?
  log "evidence reseal: $(head -n 1 "$OUT/evidence-reseal.log" 2>/dev/null) (exit $rc) -> evidence-reseal.log"
  if [ "$rc" -ne 0 ]; then
    VERDICT_REASON="reseal refused: a graded surface moved or the static screen failed (see evidence-reseal.log); run the full gate: scripts/gate_step2b.sh $TASK_ARG"
    finish FAIL
  fi

  # (h) check
  python3 scripts/evidence.py check "$TASK" --evidence "$SEAL" > "$OUT/evidence-check.log" 2>&1; rc=$?
  SEAL_STATUS="$(head -n 1 "$OUT/evidence-check.log" 2>/dev/null | sed 's/^Evidence readiness: //')"
  SEAL_RC=$rc
  GATE_STATUS="carried over from the sealed matrix (not re-measured)"
  log "evidence check: ${SEAL_STATUS:-no output} (exit $rc) -> evidence-check.log"
  if [ "$rc" -ne 0 ]; then VERDICT_REASON="resealed evidence does not check PASS"; finish FAIL; fi
elif [ "$NC_ONLY" -eq 0 ]; then
  # (a) doctor
  python3 scripts/doctor.py --strict-tools > "$OUT/doctor.log" 2>&1; rc=$?
  log "doctor: $(head -n 1 "$OUT/doctor.log" 2>/dev/null) (exit $rc) -> doctor.log"
  if [ "$rc" -ne 0 ]; then VERDICT_REASON="doctor --strict-tools failed"; finish FAIL; fi

  # (b) task_check --strict
  python3 scripts/task_check.py "$TASK" --strict > "$OUT/task_check.log" 2>&1; rc=$?
  log "task_check --strict: $(head -n 1 "$OUT/task_check.log" 2>/dev/null) (exit $rc) -> task_check.log"
  if [ "$rc" -ne 0 ]; then VERDICT_REASON="task_check --strict FAIL"; finish FAIL; fi

  # (c) hardening_check
  python3 scripts/hardening_check.py "$TASK" > "$OUT/hardening_check.log" 2>&1; rc=$?
  log "hardening_check: $(grep -m1 '^summary:' "$OUT/hardening_check.log" 2>/dev/null || tail -n 1 "$OUT/hardening_check.log") (exit $rc) -> hardening_check.log"

  # (c1) the bundled TB-Science auditor on the task staged in delivery layout (abort on FAIL).
  # The reviewer runs this same tool on the ZIP at Step 4; every construction rule it
  # enforces must already hold here, so nothing it says can be new at the end.
  python3 scripts/audit_task.py tree "$TASK" --json-out "$OUT/auditor-tree.json" > "$OUT/auditor-tree.log" 2>&1; rc=$?
  log "auditor tree: $(head -n 1 "$OUT/auditor-tree.log" 2>/dev/null) (exit $rc) -> auditor-tree.log"
  if [ "$rc" -ne 0 ]; then VERDICT_REASON="TB-Science auditor (tree) FAIL"; finish FAIL; fi

  # (c2) master checklist: the record Step 3b/Step 4 fill in, and the leads they answer.
  # Informational here -- task_check --strict above already blocks every mechanical FAIL.
  if [ ! -f "authoring/$SLUG/master-checklist.md" ]; then
    python3 scripts/master_checklist.py init "$TASK" >> "$OUT/master-checklist-auto.log" 2>&1
  fi
  python3 scripts/master_checklist.py auto "$TASK" >> "$OUT/master-checklist-auto.log" 2>&1; rc=$?
  log "master_checklist auto: $(grep -c 'LEAD ' "$OUT/master-checklist-auto.log" 2>/dev/null || echo 0) lead(s) for Step 3b (exit $rc) -> master-checklist-auto.log"

  # (d) digest
  python3 scripts/task_digest.py "$TASK" > "$OUT/task-digest.txt" 2>"$OUT/task-digest.err"; rc=$?
  DIGEST="$(cat "$OUT/task-digest.txt" 2>/dev/null)"
  log "task_digest: ${DIGEST:-<failed>} (exit $rc) -> task-digest.txt"
  if [ "$rc" -ne 0 ] || [ -z "$DIGEST" ]; then VERDICT_REASON="task_digest failed"; finish FAIL; fi
  sha256sum scripts/harbor_recording.py scripts/recording.py > "$OUT/recording-source.sha256" 2>/dev/null

  # (e) dev_verify
  # --keep-image leaves the dev-verify-<slug> verifier image in place instead of
  # `docker rmi`-ing it at the end, so this step does not throw away the image layers
  # the very next gate run has to rebuild. It does not change what dev_verify checks.
  bash scripts/dev_verify.sh "$TASK" --keep-image > "$OUT/dev_verify.log" 2>&1; rc=$?
  log "dev_verify: $(grep -m1 'RESULT' "$OUT/dev_verify.log" 2>/dev/null || echo 'no RESULT line') (exit $rc) -> dev_verify.log"
  if [ "$rc" -ne 0 ]; then VERDICT_REASON="dev_verify reward != 1"; finish FAIL; fi

  # (f) per-test matrix
  log "per_test_gate: starting (one Harbor job per test/agent, $GATE_JOBS at a time; jobs in per-test/)"
  python3 scripts/per_test_gate.py "$TASK" "${PER_TEST_ARGS[@]}" \
    --jobs-dir "$OUT/per-test" --output "$PER_TEST_REPORT" > "$OUT/per_test_gate.console.log" 2>&1; rc=$?
  GATE_STATUS="$(head -n 1 "$OUT/per_test_gate.console.log" 2>/dev/null | sed 's/^Per-test Harbor gate: //')"
  log "per_test_gate: ${GATE_STATUS:-no output} (exit $rc) -> per_test_gate.console.log, $(realpath --relative-to="$REPO_ROOT" "$PER_TEST_REPORT")"

  # (g) seal
  python3 scripts/evidence.py seal "$TASK" --per-test-report "$PER_TEST_REPORT" --output "$SEAL" > "$OUT/evidence-seal.log" 2>&1; rc=$?
  log "evidence seal: $(head -n 1 "$OUT/evidence-seal.log" 2>/dev/null) (exit $rc) -> evidence-seal.log"

  # (h) check
  python3 scripts/evidence.py check "$TASK" --evidence "$SEAL" > "$OUT/evidence-check.log" 2>&1; rc=$?
  SEAL_STATUS="$(head -n 1 "$OUT/evidence-check.log" 2>/dev/null | sed 's/^Evidence readiness: //')"
  SEAL_RC=$rc
  log "evidence check: ${SEAL_STATUS:-no output} (exit $rc) -> evidence-check.log"
  if [ "$rc" -ne 0 ]; then
    # Controls are only meaningful on an Oracle-passing, sealed digest.
    VERDICT_REASON="seal not PASS (per-test matrix or static checks failed; see evidence-seal.log / per_test_gate.console.log); NC matrix not run"
    finish FAIL
  fi
else
  python3 scripts/task_digest.py "$TASK" > "$OUT/task-digest.txt" 2>"$OUT/task-digest.err"; rc=$?
  DIGEST="$(cat "$OUT/task-digest.txt" 2>/dev/null)"
  log "task_digest: ${DIGEST:-<failed>} (exit $rc) -> task-digest.txt"
  if [ "$rc" -ne 0 ] || [ -z "$DIGEST" ]; then VERDICT_REASON="task_digest failed"; finish FAIL; fi
  sha256sum scripts/harbor_recording.py scripts/recording.py > "$OUT/recording-source.sha256" 2>/dev/null
  if [ ! -f "$SEAL" ]; then
    log "evidence check: no seal at $(realpath --relative-to="$REPO_ROOT" "$SEAL"); run the full gate first"
    VERDICT_REASON="--nc-only requires an existing seal"; finish FAIL
  fi
  python3 scripts/evidence.py check "$TASK" --evidence "$SEAL" > "$OUT/evidence-check.log" 2>&1; rc=$?
  SEAL_STATUS="$(head -n 1 "$OUT/evidence-check.log" 2>/dev/null | sed 's/^Evidence readiness: //')"
  SEAL_RC=$rc
  GATE_STATUS="from seal"
  log "evidence check (existing seal): ${SEAL_STATUS:-no output} (exit $rc) -> evidence-check.log"
  if [ "$rc" -ne 0 ]; then VERDICT_REASON="existing seal does not check PASS for the current digest"; finish FAIL; fi
fi

# (i) negative controls — opt-in diagnostics (docs/PACKAGE_RULES.md rules 14-15)
NC_STATUS="not requested"
NC_FAILED=0
NC_RAN=0
if [ "$WITH_NC" -eq 1 ] || [ "$NC_ONLY" -eq 1 ]; then
  NC_RAN=1
  bash scripts/stage_controls.sh "$TASK" "$OUT/nc" > "$OUT/stage_controls.log" 2>&1; rc=$?
  log "stage_controls: $(head -n 1 "$OUT/stage_controls.log" 2>/dev/null) (exit $rc) -> stage_controls.log"
  if [ "$rc" -ne 0 ]; then
    NC_STATUS="staging failed"
    VERDICT_REASON="stage_controls failed (no authoring/$SLUG/staged_controls/nc*.sh?)"
    finish FAIL
  fi

  # Step 3a run discipline: one local Harbor job per trial, retries disabled,
  # console log + exit codes retained per job.
  run_logged() {
    local job="$1"
    shift
    harbor run "$@" --job-name "$job" --yes 2>&1 | tee "$OUT/$job.console.log"
    local codes=("${PIPESTATUS[@]}")
    printf 'harbor=%s\ntee=%s\n' "${codes[0]}" "${codes[1]}" > "$OUT/$job.exit-codes.txt"
    return "${codes[0]}"
  }

  nc_jobs=()
  nc_copies=()
  for copy in "$OUT"/nc/NC-*; do
    [ -d "$copy" ] || continue
    id="$(basename "$copy")"                        # NC-06b
    nc_jobs+=("nc-$(printf '%s' "${id#NC-}" | tr '[:upper:]' '[:lower:]')")   # nc-06b
    nc_copies+=("$copy")
  done
  nc_count="${#nc_jobs[@]}"

  # Verdict accounting reads the per-job artifacts run_logged wrote rather than $?, so
  # it is identical whether the job ran in this shell or as a background job (a
  # parallel job's exit status cannot reach this shell's NC_FAILED). A missing
  # exit-codes file counts as a failure rather than silently passing. Never call this
  # from a subshell: it updates NC_FAILED.
  nc_account() {
    local job="$1" hrc reward
    hrc="$(sed -n 's/^harbor=//p' "$OUT/$job.exit-codes.txt" 2>/dev/null | head -n 1)"
    reward="$(cat "$OUT/$job"/*/verifier/reward.txt 2>/dev/null | head -n 1)"
    log "$job: harbor=${hrc:-<missing>} reward=${reward:-<missing>} -> $job.console.log, $job.exit-codes.txt"
    if [ "${hrc:-1}" != "0" ] || [ "${reward:-x}" != "0" ]; then NC_FAILED=$((NC_FAILED + 1)); fi
  }

  # Controls are the same shape of local Harbor job as the per-test matrix, so they
  # honour the same gate.conf jobs= setting; jobs=1 keeps the batch strictly serial
  # (and keeps reporting each control as it finishes, for `tail -f $OUT/progress`).
  nc_running=0
  for i in "${!nc_jobs[@]}"; do
    job="${nc_jobs[$i]}"
    copy="${nc_copies[$i]}"
    log "$job: starting (harbor run -p $(realpath --relative-to="$REPO_ROOT" "$copy") -a scripts.harbor_recording:RecordingOracle -k 1 -n 1 --max-retries 0)"
    if [ "$GATE_JOBS" -le 1 ]; then
      run_logged "$job" -p "$copy" -a scripts.harbor_recording:RecordingOracle -k 1 -n 1 --max-retries 0 -o "$OUT"
      nc_account "$job"
    else
      run_logged "$job" -p "$copy" -a scripts.harbor_recording:RecordingOracle -k 1 -n 1 --max-retries 0 -o "$OUT" &
      nc_running=$((nc_running + 1))
      if [ "$nc_running" -ge "$GATE_JOBS" ]; then wait -n; nc_running=$((nc_running - 1)); fi
    fi
  done
  if [ "$GATE_JOBS" -gt 1 ]; then
    wait
    for job in "${nc_jobs[@]}"; do nc_account "$job"; done
  fi
  NC_STATUS="$nc_count jobs, $NC_FAILED not rejected (pre-report count)"
fi

# (j) controls report
# Without controls there are no results to record, so controls.md is left alone.
# A reseal produces no new measurements at all: the matrix it carries over was measured
# at the superseded full digest and is reported by the round that measured it, so asking
# controls_report to re-narrate it here would only print a digest mismatch as a FAIL.
if [ "$RESEAL_ONLY" -eq 1 ]; then
  REPORT_RC=0
  log "controls_report: skipped (reseal-only re-stamps the seal; the carried-over matrix is reported by the round that measured it)"
  finish_reseal=1
fi
report_args=(--task-dir "$TASK" --evidence "$OUT")
[ "$NC_RAN" -eq 1 ] && report_args+=(--write)
[ -f "$PER_TEST_REPORT" ] && report_args+=(--gate-report "$PER_TEST_REPORT")
if [ "${finish_reseal:-0}" -ne 1 ]; then
  python3 scripts/controls_report.py "${report_args[@]}" > "$OUT/controls_report.md" 2>"$OUT/controls_report.err"; rc=$?
  REPORT_RC=$rc
  report_dest="controls_report.md"
  [ "$NC_RAN" -eq 1 ] && report_dest="controls_report.md, authoring/$SLUG/controls.md"
  log "controls_report: $(grep -m1 'Overall verdict' "$OUT/controls_report.md" 2>/dev/null | sed 's/\*//g' || echo 'no verdict line') (exit $rc) -> $report_dest"
fi

# (k) verdict
# PASS = sealed per-test Oracle/NOP matrix. Controls only affect the verdict when
# they were requested: a control that runs must still be rejected through its plan.
if [ "${SEAL_RC:-1}" -eq 0 ] && [ "$NC_FAILED" -eq 0 ] && { [ "$NC_RAN" -eq 0 ] || [ "$REPORT_RC" -eq 0 ]; }; then
  if [ "$NC_RAN" -eq 1 ]; then
    VERDICT_REASON="seal PASS and every NC job rewarded 0 with Harbor exit 0 and no exception"
  elif [ "$RESEAL_ONLY" -eq 1 ]; then
    VERDICT_REASON="seal re-stamped at the new full digest; agent and grader surfaces byte-identical, per-test matrix carried over (not re-measured)"
  else
    VERDICT_REASON="seal PASS (negative controls not requested; run --with-nc or --nc-only for the optional matrix)"
  fi
  finish PASS
fi
reasons=()
[ "${SEAL_RC:-1}" -eq 0 ] || reasons+=("seal not PASS")
[ "$NC_FAILED" -eq 0 ] || reasons+=("$NC_FAILED NC job(s) not rejected")
{ [ "$NC_RAN" -eq 0 ] || [ "$REPORT_RC" -eq 0 ]; } || reasons+=("controls_report verdict FAIL (see controls_report.md)")
VERDICT_REASON="$(IFS='; '; echo "${reasons[*]}")"
finish FAIL
