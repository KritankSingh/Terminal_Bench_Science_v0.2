#!/usr/bin/env bash
# stage_controls.sh — stage each negative control as a full, independent copy of
# the task with solution/solve.sh replaced by the control script.
#
# Usage:
#   scripts/stage_controls.sh tasks/<task> <outroot>
#
# For every authoring/<slug>/staged_controls/nc*.sh (slug = basename of the task
# directory) this creates <outroot>/NC-XX/ (nc01_x.sh -> NC-01, nc06b_x.sh -> NC-06b)
# as a full copy of the task (rsync -a) and overwrites solution/solve.sh with the
# control (mode 0755). It refuses to write inside any tasks/ tree and prints the
# created paths. Existing <outroot>/NC-XX/ copies are replaced.
set -uo pipefail

usage() { sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then usage; exit 0; fi
if [ "$#" -ne 2 ]; then usage >&2; exit 2; fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK="$(realpath -e "$1" 2>/dev/null)" || { echo "error: task directory not found: $1" >&2; exit 2; }
OUTROOT="$2"
SLUG="$(basename "$TASK")"
CTL_DIR="$REPO_ROOT/authoring/$SLUG/staged_controls"

[ -f "$TASK/task.toml" ] || { echo "error: not a task tree (no task.toml): $TASK" >&2; exit 2; }
[ -d "$CTL_DIR" ] || { echo "error: staged_controls dir not found: $CTL_DIR (run scripts/nc_generate.py first)" >&2; exit 2; }
command -v rsync >/dev/null 2>&1 || { echo "error: rsync is required" >&2; exit 2; }

# Refuse to write inside a frozen task tree (the repo's tasks/ or any .../tasks/... path).
abs_out="$(realpath -m "$OUTROOT")"
case "$abs_out/" in
  "$REPO_ROOT/tasks/"*|*/tasks/*)
    echo "error: refusing to write OUTROOT inside a tasks/ tree: $abs_out" >&2
    exit 2 ;;
esac
case "$abs_out/" in
  "$TASK/"*) echo "error: OUTROOT must be outside the task directory: $abs_out" >&2; exit 2 ;;
esac

shopt -s nullglob
scripts=("$CTL_DIR"/nc*.sh)
if [ "${#scripts[@]}" -eq 0 ]; then
  echo "error: no control scripts (nc*.sh) in $CTL_DIR" >&2
  exit 2
fi

mkdir -p "$abs_out" || exit 2
created=()
failed=0
for script in "${scripts[@]}"; do
  base="$(basename "$script")"          # nc06b_detached_reward.sh
  token="${base#nc}"                     # 06b_detached_reward.sh
  token="${token%%_*}"                   # 06b
  token="${token%.sh}"                   # (handles nc06b.sh without a suffix)
  num="${token//[!0-9]/}"                # 06
  suffix="${token//[0-9]/}"              # b (or empty)
  if [ -z "$num" ]; then
    echo "warn: cannot derive an NC id from $base; skipping" >&2
    continue
  fi
  ncid="NC-${num}${suffix}"
  dest="$abs_out/$ncid"
  rm -rf "$dest"
  mkdir -p "$dest"
  # trajectories/ (captured runs) and caches are not part of the task and only bloat the copy.
  if ! rsync -a --exclude=/trajectories/ --exclude=__pycache__/ --exclude='*.pyc' "$TASK"/ "$dest"/; then
    echo "error: rsync failed for $ncid" >&2; failed=1; continue
  fi
  if ! install -m 0755 "$script" "$dest/solution/solve.sh"; then
    echo "error: could not install $base as $dest/solution/solve.sh" >&2; failed=1; continue
  fi
  created+=("$dest|$base")
done

echo "Staged ${#created[@]} controls under: $abs_out"
for entry in "${created[@]}"; do
  echo "  ${entry%%|*}  (solution/solve.sh <- ${entry##*|})"
done
[ "$failed" -eq 0 ] && [ "${#created[@]}" -gt 0 ] || exit 1
