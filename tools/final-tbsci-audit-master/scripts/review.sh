#!/usr/bin/env bash
# Review-repo workflow: Inbox zip -> extracted/ -> audit/
#
#   ./scripts/review.sh extract [zip...]            # unpack Inbox zips into extracted/
#   ./scripts/review.sh audit <task-id> [profile]   # run the legs -> audit/<id>/<timestamp>/
#   ./scripts/review.sh lint <task-id>              # lint audit/<id>/latest/verdict.json
#   ./scripts/review.sh report <task-id>            # lint, then render report.md
#   ./scripts/review.sh all [zip...]                # extract, then audit every extracted task
#
# profile: terminus (default) | upstream.  Judgement is yours: `audit` only fills the mechanical
# fields; you read the task, fill verdict.json + manual_probes.txt, then `lint` and `report`.
# Requires Python 3.11+ (tomllib). No Docker probe is included in this version.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INBOX="$ROOT/Inbox"
EXTRACTED="$ROOT/extracted"
AUDIT="$ROOT/audit"
SC="$ROOT/scripts"

# --- Python >= 3.11 ---------------------------------------------------------------------------
PY=()
for c in python3.11 python3.12 python3.13 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    PY=("$c"); break
  fi
done
if [[ ${#PY[@]} -eq 0 ]] && command -v uv >/dev/null 2>&1; then
  PY=(uv run --quiet --python 3.11 python)
fi
if [[ ${#PY[@]} -eq 0 ]]; then
  echo "Python 3.11+ is required (tomllib). Install it, e.g.: uv python install 3.11" >&2
  exit 1
fi

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
stamp() { date +%Y%m%d-%H%M%S; }

# Resolve the task root inside an extracted tree (a delivery package wraps it in
# one <task-slug>/ level; a legacy zip may wrap one top-level folder).
find_task_dir() {
  local base="$1"
  if [[ -f "$base/task.toml" ]]; then echo "$base"; return; fi
  local hit
  hit="$(find "$base" -mindepth 2 -maxdepth 2 -type f -name task.toml 2>/dev/null | head -1)"
  [[ -n "$hit" ]] && { dirname "$hit"; return; }
  return 1
}

extract_one() {
  local zip="$1"
  [[ -f "$zip" && "$zip" == *.zip ]] || { echo "not a zip: $zip" >&2; return 1; }
  if unzip -Z1 "$zip" | grep -q '\\'; then
    echo "EXTRACT_FAIL zip=$zip reason=backslash_separators (built on Windows; would extract flat on Linux)" >&2
    return 1
  fi
  local tmp; tmp="$(mktemp -d)"
  unzip -q -o "$zip" -d "$tmp"
  local shape name src
  if [[ -f "$tmp/task.toml" ]]; then
    shape="zip-root"; src="$tmp"
    name="$(basename "$zip" .zip)"
  else
    local subs=("$tmp"/*/)
    if [[ ${#subs[@]} -eq 1 && -f "${subs[0]}task.toml" ]]; then
      shape="zip-enclosing-folder"; src="${subs[0]%/}"
      name="$(basename "$src")"
    elif [[ ${#subs[@]} -eq 1 ]] && \
         [[ -n "$(find "${subs[0]%/}" -mindepth 2 -maxdepth 2 -type f -name task.toml 2>/dev/null | head -1)" ]]; then
      # DELIVERY_CHECKLIST.md layout: <task-slug>/<task-slug>/task.toml with
      # rubric.txt / oracle-nop-evidence/ / trajectories/ as siblings. Keep the
      # WHOLE delivery package — the screen grades all four members.
      shape="checklist-package"; src="${subs[0]%/}"
      name="$(basename "$(dirname "$(find "$src" -mindepth 2 -maxdepth 2 -type f -name task.toml | head -1)")")"
    else
      rm -rf "$tmp"
      echo "EXTRACT_FAIL zip=$zip reason=no_task.toml_at_root_or_one_level_down" >&2
      return 1
    fi
  fi
  # the directory basename IS the slug the screen validates the manifest name against, so keep it exact
  [[ "$name" =~ ^[A-Za-z0-9._-]+$ ]] || { rm -rf "$tmp"; echo "EXTRACT_FAIL zip=$zip reason=unsafe_name:$name" >&2; return 1; }
  rm -rf "${EXTRACTED:?}/$name"
  mv "$src" "$EXTRACTED/$name"
  rm -rf "$tmp"
  printf '%s\n' "$shape" > "$EXTRACTED/$name.shape"
  echo "EXTRACT_OK task_id=$name shape=$shape zip=$(basename "$zip")"
}

cmd_extract() {
  local zips=() z
  if [[ $# -eq 0 ]]; then
    shopt -s nullglob; zips=("$INBOX"/*.zip); shopt -u nullglob
    [[ ${#zips[@]} -gt 0 ]] || { echo "Inbox is empty: drop a task .zip into $INBOX" >&2; exit 1; }
  else
    for z in "$@"; do
      if   [[ -f "$z" ]];            then zips+=("$z")
      elif [[ -f "$INBOX/$z" ]];     then zips+=("$INBOX/$z")
      elif [[ -f "$INBOX/$z.zip" ]]; then zips+=("$INBOX/$z.zip")
      else echo "zip not found: $z" >&2; exit 1; fi
    done
  fi
  local ok=0
  for z in "${zips[@]}"; do extract_one "$z" && ok=$((ok + 1)) || true; done
  echo "extracted $ok / ${#zips[@]} zip(s) -> $EXTRACTED"
}

cmd_audit() {
  local id="${1:?usage: review.sh audit <task-id> [terminus|upstream]}" profile="${2:-terminus}"
  local task="$EXTRACTED/$id"
  [[ -d "$task" ]] || { echo "not extracted: $id (expected $task)" >&2; exit 1; }
  find_task_dir "$task" >/dev/null || { echo "no task.toml under $task" >&2; exit 1; }
  local shape="dir"
  [[ -f "$EXTRACTED/$id.shape" ]] && shape="$(cat "$EXTRACTED/$id.shape")"
  local run="$AUDIT/$id/$(stamp)"
  mkdir -p "$run"
  "${PY[@]}" "$SC/audit_run.py" "$task" "$run" --profile "$profile" --shape "$shape"
  ln -sfn "$(basename "$run")" "$AUDIT/$id/latest"
  echo "AUDIT_OK task_id=$id profile=$profile run=$run"
  echo "Next: read the task (SKILL.md step 2), then replace every PENDING in $run/verdict.json,"
  echo "      fill $run/manual_probes.txt, and run: $0 lint $id"
}

cmd_lint()   { local id="${1:?usage: review.sh lint <task-id>}";   "${PY[@]}" "$SC/verdict_lint.py"   "$AUDIT/$id/latest"; }
cmd_report() { local id="${1:?usage: review.sh report <task-id>}"; "${PY[@]}" "$SC/report_render.py" "$AUDIT/$id/latest"; }

cmd_all() {
  cmd_extract "$@"
  local d id
  shopt -s nullglob
  for d in "$EXTRACTED"/*/; do
    id="$(basename "$d")"
    [[ -f "$d/task.toml" ]] || continue
    cmd_audit "$id"
  done
  shopt -u nullglob
}

case "${1:-}" in
  extract) shift; cmd_extract "$@" ;;
  audit)   shift; cmd_audit "$@" ;;
  lint)    shift; cmd_lint "$@" ;;
  report)  shift; cmd_report "$@" ;;
  all)     shift; cmd_all "$@" ;;
  *)       usage ;;
esac
