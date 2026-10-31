#!/usr/bin/env python3
"""Re-grade a captured Step 3c round against a hardened verifier, with no model re-runs.

Every task here sets ``[verifier].environment_mode = "separate"``, so a trial's reward is
a pure function of ``tests/`` plus the artifacts that trial captured. ``harbor job
regrade`` re-runs verification for every trial of a recorded job against a new ``tests/``
tree and writes a *new* job directory; the recorded round is never modified. That makes
it possible to fix a verifier defect after Step 3c and re-score the five paid GPT-5.6
attempts and the Oracle/NOP controls instead of buying five fresh trials.

The whole licence for that rests on the agent-facing surface not moving, and Harbor does
not check it (it only matches task *names*). This script does:

  bind    Run BEFORE editing ``tests/``. Binds the captured round to the current task:
          all three digests, a per-path source inventory, the declared artifacts, the
          seed-parity map, a fold of the round's bytes, and per-trial rewards and CTRF
          case statuses. Copies the Step 2b seal and its per-test report aside so the
          pre-capture evidence survives a later reseal. The record is immutable.

  run     Run AFTER editing ``tests/``. Refuses to start a container unless the agent
          digest is byte-identical to the bound one, the grader digest actually moved,
          and the task name, declared artifacts, seed parity and captured round are all
          exactly as bound. Then one ``harbor job regrade`` per source job, reusing the
          source job names so the regraded round is structurally a Step 3c round, and
          requires every reward back exactly identical.

  verify  Re-check a finished regrade record. ``check_regrade_record`` is the importable
          core, the way ``package_task.py`` already imports ``evidence.check_seal``.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from common import (
    AGENT_SURFACE,
    GRADER_SURFACE,
    REPO_ROOT,
    WorkflowError,
    assert_digest_partition,
    finite_number,
    load_json,
    load_test_manifest,
    manifest_ids,
    portable_path,
    require_outside_task,
    resolve_recorded_path,
    seed_parity,
    sha256_file,
    split_digests,
    symlink_sha256,
    task_digest,
    task_paths,
    trial_artifact_symlink,
    write_json,
)
from evidence import check_seal

# Mirror of tools/final-tbsci-audit-master/scripts/tbsci_static_screen.py T3_ROUND_NAME_BAN.
ROUND_NAME_BAN = re.compile(
    r'(?<![a-z])(?:hardened|hardening|harden\d*|regrade\d*|rerun\d*|aborted|void|'
    r'k\d+-\d{6,}|round-?\d+|attempt-?\d+|fixes?-pending|scratch|wip|tmpfix)(?![a-z])', re.I)
from gate_artifacts import parse_ctrf, parse_result

try:  # The workspace .venv is 3.12; the system interpreter is 3.10 and only compiles.
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised only on Python 3.10
    tomllib = None


BIND_SCHEMA_VERSION = "1.0"
BIND_KIND = "step3c-regrade-bind"
REGRADE_SCHEMA_VERSION = "1.0"
REGRADE_KIND = "step3c-regrade"

# harbor.models.trial.paths.EnvironmentPaths.artifacts_dir: Harbor injects this entry
# into every collection set, so a regrade demands a manifest entry for it too.
CONVENTION_ARTIFACT_SOURCE = "/logs/artifacts"
# harbor.constants.MAIN_SERVICE_NAME. Only used as a sentinel, and both sides of every
# comparison default to it, so the literal never leaks into a verdict.
MAIN_SERVICE_NAME = "main"

ROUND_DIGEST_PREFIX = b"tbench-regrade-round-v1\0"
DEFAULT_JOB_TIMEOUT_SEC = 7200.0


# --------------------------------------------------------------------------- task.toml


def read_task_toml(task_dir: Path) -> dict[str, Any]:
    if tomllib is None:
        raise WorkflowError("Python 3.11+ is required to read task.toml; activate the workspace .venv")
    path = task_dir / "task.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"missing task.toml: {path}") from exc
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise WorkflowError(f"invalid task.toml: {exc}") from exc
    if not isinstance(data, dict):
        raise WorkflowError("task.toml must parse to a table")
    return data


def task_name(task_dir: Path, data: dict[str, Any]) -> str:
    """Terminal-Bench Science carries the name at the top level; ``[task]`` is the 2.1 form."""
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise WorkflowError("task.toml has no top-level string name")
    if name != task_dir.name:
        raise WorkflowError(f"task.toml name {name!r} does not match the directory slug {task_dir.name!r}")
    return name


def declared_artifacts(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize the top-level ``artifacts`` declaration to source/service/destination."""
    entries = data.get("artifacts", [])
    if not isinstance(entries, list):
        raise WorkflowError("task.toml artifacts must be a list")
    normalized: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if isinstance(entry, str):
            normalized.append({"source": entry, "service": None, "destination": None})
            continue
        if not isinstance(entry, dict) or not isinstance(entry.get("source"), str):
            raise WorkflowError(f"task.toml artifacts[{index}] must be a string or a table with a source")
        service = entry.get("service")
        destination = entry.get("destination")
        if service is not None and not isinstance(service, str):
            raise WorkflowError(f"task.toml artifacts[{index}].service must be a string")
        if destination is not None and not isinstance(destination, str):
            raise WorkflowError(f"task.toml artifacts[{index}].destination must be a string")
        normalized.append({"source": entry["source"], "service": service, "destination": destination})
    return normalized


def artifact_key(entry: dict[str, Any]) -> str:
    """The identity Harbor matches a declaration against a manifest entry by."""
    service = entry.get("service") or MAIN_SERVICE_NAME
    return f"{service}:{str(entry.get('source') or '').rstrip('/')}"


def artifact_keys(entries: list[dict[str, Any]]) -> list[str]:
    """Order-insensitive, ``source.rstrip('/')``-normalized declaration identity."""
    return sorted({artifact_key(entry) for entry in entries})


def with_convention_entry(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    convention = {"source": CONVENTION_ARTIFACT_SOURCE, "service": None, "destination": None}
    if any(artifact_key(entry) == artifact_key(convention) for entry in entries):
        return list(entries)
    return [convention, *entries]


def artifact_host_relpath(entry: dict[str, Any]) -> PurePosixPath:
    """harbor.trial.artifact_handler.artifact_host_path, re-implemented dependency-free."""
    raw = entry.get("destination") or entry.get("source") or ""
    parts = [part for part in PurePosixPath(raw).parts if part not in ("", "/", "..")]
    return PurePosixPath(*parts) if parts else PurePosixPath(".")


def artifact_symlinks(trial_dir: Path) -> list[str]:
    """Symlinks inside a trial's captured artifacts.

    Harbor 0.23.0 replays a single-step trial's artifacts with
    ``shutil.copytree(symlinks=False)`` (``harbor/trial/regrade.py``,
    ``_replay_recorded_outputs(preserve_symlinks=False)``): a link into the agent's /app
    aborts the copy on the host, and any other link is replaced by a regular file. Either
    way the verifier would not see what the agent submitted (Master #55 keeps in-tree links),
    so such a trial cannot be regraded faithfully: it needs a fresh Step 3c round.
    """
    root = trial_dir / "artifacts"
    if not root.is_dir():
        return []
    return sorted(str(p.relative_to(trial_dir)) for p in root.rglob("*") if p.is_symlink())


def artifact_coverage_problems(trial_dir: Path, entries: list[dict[str, Any]]) -> list[str]:
    """Harbor's ``RegradeTrial._validate_artifact_coverage``, without importing Harbor.

    Every artifact the task declares (plus the implicit ``/logs/artifacts`` convention
    dir) needs a manifest entry that is not ``failed``/``skipped``; ``empty`` is an
    honest empty directory, and anything else must have its bytes on disk at the exact
    host path the replay will read.
    """
    manifest_path = trial_dir / "artifacts" / "manifest.json"
    manifest = load_json(manifest_path)
    if not isinstance(manifest, list):
        raise WorkflowError(f"{manifest_path} must contain a JSON list")
    recorded: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(manifest):
        if not isinstance(item, dict) or not isinstance(item.get("source"), str):
            raise WorkflowError(f"{manifest_path}: entry {index} has no string source")
        recorded[artifact_key(item)] = item
    problems: list[str] = []
    for entry in with_convention_entry(entries):
        source = entry["source"]
        found = recorded.get(artifact_key(entry))
        if found is None:
            problems.append(f"{source}: never collected (no manifest entry); the verifier would grade without it")
            continue
        status = found.get("status")
        if status == "failed":
            problems.append(f"{source}: collection failed in the source trial; the record does not contain it")
            continue
        if status == "skipped":
            problems.append(f"{source}: skipped in the source trial (host-path collision); the bytes belong elsewhere")
            continue
        if status == "empty":
            continue
        replay = trial_dir / "artifacts" / Path(*artifact_host_relpath(entry).parts)
        if replay.exists():
            continue
        destination = found.get("destination")
        if isinstance(destination, str) and (trial_dir / destination).exists():
            problems.append(
                f"{source}: recorded at {destination}, but the declaration reads "
                f"artifacts/{artifact_host_relpath(entry)}; align the artifact destination"
            )
        else:
            problems.append(f"{source}: collected artifact no longer exists on disk; the trial directory is incomplete")
    return problems


def manifest_cases(task_dir: Path) -> list[str]:
    """Every CTRF case the test manifest declares; a full-suite run must emit exactly these."""
    payload = load_test_manifest(task_dir)
    cases: list[str] = []
    for entry in payload["tests"]:
        cases.extend(entry["cases"])
    return sorted(cases)


# ------------------------------------------------------------------------- inventories


def source_inventory(task_dir: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Per-path content hashes and modes over exactly what the task digest folds."""
    task_dir = task_dir.resolve()
    contents: dict[str, str] = {}
    modes: dict[str, str] = {}
    for path in task_paths(task_dir):
        relative = path.relative_to(task_dir).as_posix()
        modes[relative] = format(stat.S_IMODE(path.stat().st_mode), "04o")
        contents[relative] = "dir" if path.is_dir() else f"sha256:{sha256_file(path)}"
    return contents, modes


def _in_surface(relative: str, roots: tuple[str, ...]) -> bool:
    return relative.split("/", 1)[0] in roots


def inventory_diff(
    recorded: dict[str, str],
    recorded_modes: dict[str, str],
    current: dict[str, str],
    current_modes: dict[str, str],
    roots: tuple[str, ...] | None = None,
) -> dict[str, list[Any]]:
    """Per-path added/removed/modified, optionally narrowed to one digest surface."""

    def keep(relative: str) -> bool:
        return roots is None or _in_surface(relative, roots)

    old = {key: value for key, value in recorded.items() if keep(key)}
    new = {key: value for key, value in current.items() if keep(key)}
    modified: list[dict[str, str]] = []
    for key in sorted(set(old) & set(new)):
        if old[key] != new[key]:
            modified.append({"path": key, "recorded": old[key], "current": new[key], "change": "content"})
        elif recorded_modes.get(key) != current_modes.get(key):
            modified.append(
                {
                    "path": key,
                    "recorded": f"mode {recorded_modes.get(key)}",
                    "current": f"mode {current_modes.get(key)}",
                    "change": "mode",
                }
            )
    return {
        "added": sorted(set(new) - set(old)),
        "removed": sorted(set(old) - set(new)),
        "modified": modified,
    }


def render_diff(diff: dict[str, list[Any]], limit: int = 40) -> list[str]:
    lines: list[str] = []
    for relative in diff["added"][:limit]:
        lines.append(f"  + {relative}")
    for relative in diff["removed"][:limit]:
        lines.append(f"  - {relative}")
    for row in diff["modified"][:limit]:
        lines.append(f"  M {row['path']}: {row['recorded']} -> {row['current']}")
    total = len(diff["added"]) + len(diff["removed"]) + len(diff["modified"])
    if total > limit:
        lines.append(f"  ... and {total - limit} more path(s)")
    return lines


def round_fingerprint(round_dir: Path) -> dict[str, Any]:
    """Fold the captured round's bytes into one digest, plus file count and total size.

    A symlink inside a trial's ``artifacts/`` (Master #55: a valid submission) is folded
    as its own ``L`` record from its link text and never followed; the result then also
    lists those links. Any other symlink is refused. A round without symlinks folds
    exactly as before, so existing bind/regrade records stay valid.
    """
    round_dir = round_dir.resolve()
    if not round_dir.is_dir():
        raise WorkflowError(f"captured round directory not found: {round_dir}")
    digest = hashlib.sha256()
    digest.update(ROUND_DIGEST_PREFIX)
    files = 0
    total = 0
    links: dict[str, str] = {}
    for path in sorted(round_dir.rglob("*")):
        if path.is_symlink():
            link = trial_artifact_symlink(round_dir, path)
            if link is None:
                raise WorkflowError(
                    f"captured round contains a symlink outside a trial's artifacts/; inspect it by hand: {path}")
            relative = path.relative_to(round_dir).as_posix()
            encoded = relative.encode("utf-8")
            digest.update(b"L")
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
            digest.update(bytes.fromhex(symlink_sha256(link)))
            links[relative] = link
            continue
        relative = path.relative_to(round_dir).as_posix().encode("utf-8")
        if path.is_dir():
            digest.update(b"D")
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            continue
        if not path.is_file():
            raise WorkflowError(f"captured round contains a non-regular file: {path}")
        size = path.stat().st_size
        digest.update(b"F")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(size.to_bytes(8, "big"))
        digest.update(bytes.fromhex(sha256_file(path)))
        files += 1
        total += size
    fingerprint: dict[str, Any] = {"digest": f"sha256:{digest.hexdigest()}", "file_count": files, "total_bytes": total}
    if links:
        fingerprint["symlinks"] = links
    return fingerprint


# ------------------------------------------------------------------- round/job scanning


def job_kind(job_name: str) -> str:
    if job_name == "oracle" or job_name.startswith("oracle-"):
        return "oracle"
    if job_name == "nop" or job_name.startswith("nop-"):
        return "nop"
    return "model"


def job_dirs(round_dir: Path) -> list[Path]:
    found = [child for child in sorted(round_dir.iterdir()) if child.is_dir() and (child / "config.json").is_file()]
    if not found:
        raise WorkflowError(f"no Harbor job directories (config.json) under {round_dir}")
    return found


def sole_trial_dir(job_dir: Path) -> Path:
    """A Step 3c job holds exactly one trial; anything else is not a regradable round."""
    trials = [child for child in sorted(job_dir.iterdir()) if child.is_dir() and (child / "config.json").is_file()]
    if len(trials) != 1:
        raise WorkflowError(f"{job_dir.name}: expected exactly one trial directory, found {len(trials)}")
    trial = trials[0]
    for required in ("config.json", "result.json", "artifacts/manifest.json"):
        if not (trial / required).is_file():
            raise WorkflowError(f"{job_dir.name}/{trial.name}: missing {required}")
    return trial


def read_reward_txt(trial_dir: Path) -> tuple[str | None, float | None]:
    path = trial_dir / "verifier" / "reward.txt"
    if not path.is_file():
        return None, None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise WorkflowError(f"cannot read {path}: {exc}") from exc
    try:
        return raw, float(raw)
    except ValueError:
        return raw, None


def describe_trial(job_dir: Path, trial_dir: Path) -> dict[str, Any]:
    """Reward, CTRF statuses and artifact hashes read from the raw files, not from text."""
    result_path = trial_dir / "result.json"
    payload = load_json(result_path)
    reward, errors, exception = parse_result(payload)
    raw_reward_txt, reward_txt = read_reward_txt(trial_dir)
    row: dict[str, Any] = {
        "job": job_dir.name,
        "kind": job_kind(job_dir.name),
        "trial": trial_dir.name,
        "trial_dir": portable_path(trial_dir),
        "task_name": payload.get("task_name") if isinstance(payload, dict) else None,
        "reward": reward,
        "errors": errors,
        "exception": exception,
        "reward_txt": raw_reward_txt,
        "reward_txt_value": reward_txt,
        "result_sha256": f"sha256:{sha256_file(result_path)}",
    }
    try:
        ctrf_path, case_statuses = parse_ctrf(result_path)
    except WorkflowError as exc:
        row.update({"ctrf_error": str(exc), "cases": [], "case_statuses": {}, "ctrf_sha256": None, "ctrf_path": None})
        return row
    row.update(
        {
            "ctrf_error": None,
            "cases": sorted(case_statuses),
            "case_statuses": case_statuses,
            "ctrf_sha256": f"sha256:{sha256_file(ctrf_path)}",
            "ctrf_path": portable_path(ctrf_path),
        }
    )
    return row


# ---------------------------------------------------------------------------- bind


def build_bind_record(task_dir: Path, round_dir: Path, seal_path: Path | None) -> dict[str, Any]:
    name_of_task = task_name(task_dir, read_task_toml(task_dir))

    # 1. The round must bind to the task as it stands right now. Once tests/ has moved,
    #    the captured round no longer proves anything about the current grader surface.
    digest_file = round_dir / "task-digest.txt"
    try:
        recorded_digest = digest_file.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise WorkflowError(f"captured round has no readable task-digest.txt: {exc}") from exc
    current_full = task_digest(task_dir)
    if recorded_digest != current_full:
        raise WorkflowError(
            f"captured round binds to {recorded_digest or '<empty>'} but the task is now {current_full}: "
            "you already edited the task; bind must run first"
        )

    # 2. The two digest halves must still partition the digested tree.
    assert_digest_partition(task_dir)
    digests = split_digests(task_dir)

    # 3/4/5. Inventory every job, match the task name, and prove artifact coverage.
    entries = declared_artifacts(read_task_toml(task_dir))
    trials: list[dict[str, Any]] = []
    kinds: set[str] = set()
    for job in job_dirs(round_dir):
        trial = sole_trial_dir(job)
        row = describe_trial(job, trial)
        if row["task_name"] != name_of_task:
            raise WorkflowError(
                f"{job.name}/{trial.name}: result.json task_name {row['task_name']!r} does not match {name_of_task!r}"
            )
        problems = artifact_coverage_problems(trial, entries)
        links = artifact_symlinks(trial)
        if links:
            message = (f"{len(links)} symlink(s) in the captured artifacts ({', '.join(links[:3])}"
                       f"{', …' if len(links) > 3 else ''}): Harbor's single-step regrade replay follows "
                       "symlinks on the host, so the verifier would not see what was submitted")
            if row["kind"] == "model":
                raise WorkflowError(f"{job.name}/{trial.name}: not regradable: {message}. "
                                    "Take a fresh Step 3c round at the current digest instead.")
            problems = [*problems, message]
        if problems:
            # A control that produces nothing (NOP, or an Oracle whose declared
            # artifacts are agent outputs) has no bytes to re-grade, and Harbor
            # would refuse it. That is not a defect in the round: controls are
            # local and free, so they are RE-RUN against the hardened verifier
            # rather than re-graded. Only a model trial must be regradable --
            # those are the paid evidence this whole mechanism exists to save.
            if row["kind"] == "model":
                raise WorkflowError(
                    f"{job.name}/{trial.name}: artifact coverage: " + "; ".join(problems)
                )
            row["artifact_coverage"] = "unavailable"
            row["regradable"] = False
            row["not_regradable_reason"] = "; ".join(problems)
        else:
            row["artifact_coverage"] = "ok"
            row["regradable"] = True
        row["job_dir"] = portable_path(job)
        kinds.add(row["kind"])
        trials.append(row)
    has_controls = bool(kinds & {"oracle", "nop"})

    # 6. The Step 2b seal, when supplied, must still check out against this task.
    seal_summary: dict[str, Any] | None = None
    if seal_path is not None:
        seal_errors = check_seal(task_dir, seal_path)
        if seal_errors:
            raise WorkflowError("Step 2b seal does not check out: " + "; ".join(seal_errors))
        seal = load_json(seal_path)
        seal_summary = {
            "path": portable_path(seal_path),
            "sha256": f"sha256:{sha256_file(seal_path)}",
            "schema_version": seal.get("schema_version") if isinstance(seal, dict) else None,
            "task_digest": seal.get("task_digest") if isinstance(seal, dict) else None,
        }

    # 7. Seed parity between tests/seed and environment/.
    parity = seed_parity(task_dir)

    contents, modes = source_inventory(task_dir)
    return {
        "schema_version": BIND_SCHEMA_VERSION,
        "kind": BIND_KIND,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task_slug": task_dir.name,
        "task_name": name_of_task,
        "task_dir": portable_path(task_dir),
        "round_name": round_dir.name,
        "round_dir": portable_path(round_dir),
        "round_task_digest": recorded_digest,
        "digests": digests,
        "task_toml_sha256": f"sha256:{sha256_file(task_dir / 'task.toml')}",
        "manifest_test_ids": manifest_ids(task_dir),
        "manifest_cases": manifest_cases(task_dir),
        "declared_artifacts": entries,
        "artifact_keys": artifact_keys(entries),
        "convention_artifact_source": CONVENTION_ARTIFACT_SOURCE,
        "seed_parity": parity,
        "task_paths": contents,
        "task_modes": modes,
        "round": round_fingerprint(round_dir),
        "has_controls": has_controls,
        "seal": seal_summary,
        "precapture": None,
        "trials": trials,
    }


def copy_precapture(task_dir: Path, round_name: str, seal_path: Path) -> dict[str, Any]:
    """Freeze the seal and its per-test report, so a later reseal cannot rewrite history."""
    target = REPO_ROOT / "artifacts" / "regrade" / task_dir.name / round_name / "precapture"
    require_outside_task(task_dir, target)
    target.mkdir(parents=True, exist_ok=True)
    seal = load_json(seal_path)
    if not isinstance(seal, dict) or not isinstance(seal.get("per_test_report"), str):
        raise WorkflowError("Step 2b seal has no per-test report path")
    report_path = resolve_recorded_path(seal["per_test_report"]).resolve()
    if not report_path.is_file():
        raise WorkflowError(f"sealed per-test report is missing: {seal['per_test_report']}")
    copies: dict[str, Any] = {}
    for label, origin in (("seal", seal_path), ("per_test_report", report_path)):
        destination = target / origin.name
        shutil.copy2(origin, destination)
        copies[label] = {
            "source": portable_path(origin),
            "copy": portable_path(destination),
            "sha256": f"sha256:{sha256_file(destination)}",
        }
    return copies


def render_bind(record: dict[str, Any]) -> str:
    lines = [
        f"Step 3c regrade bind: PASS ({record['task_slug']} @ {record['round_name']})",
        f"  full   digest {record['digests']['full']}",
        f"  agent  digest {record['digests']['agent']}",
        f"  grader digest {record['digests']['grader']}",
        f"  artifacts {', '.join(record['artifact_keys']) or '<none>'} (+ implicit {record['convention_artifact_source']})",
        f"  manifest {len(record['manifest_test_ids'])} test id(s), {len(record['manifest_cases'])} CTRF case(s)",
        f"  seed parity {len(record['seed_parity'])} file(s); source inventory {len(record['task_paths'])} path(s)",
        f"  round {record['round']['file_count']} file(s), {record['round']['total_bytes']} bytes, {record['round']['digest']}"
        + (f", {len(record['round']['symlinks'])} in-artifacts symlink(s)" if record["round"].get("symlinks") else ""),
        f"  controls {'present' if record['has_controls'] else 'ABSENT (oracle/nop checks will be skipped)'}",
    ]
    if record.get("seal"):
        lines.append(f"  seal {record['seal']['path']} {record['seal']['sha256']} (schema {record['seal']['schema_version']})")
    if record.get("precapture"):
        for label, copied in sorted(record["precapture"].items()):
            lines.append(f"  precapture {label}: {copied['copy']} {copied['sha256']}")
    for row in record["trials"]:
        lines.append(
            f"  {row['kind']:6s} {row['job']:42s} reward={row['reward']} errors={row['errors']} "
            f"cases={len(row['cases'])} passed={sum(1 for s in row['case_statuses'].values() if s == 'passed')}"
        )
    return "\n".join(lines)


def command_bind(args: argparse.Namespace) -> int:
    task_dir = args.task_dir.resolve()
    round_dir = args.round.resolve()
    if not task_dir.is_dir():
        raise WorkflowError(f"task directory not found: {task_dir}")
    if not round_dir.is_dir():
        raise WorkflowError(f"round directory not found: {round_dir}")
    require_outside_task(task_dir, round_dir)
    seal_path = args.seal.resolve() if args.seal else None
    if seal_path is not None and not seal_path.is_file():
        raise WorkflowError(f"Step 2b seal not found: {seal_path}")
    output = args.output.resolve() if args.output else (
        REPO_ROOT / "artifacts" / "regrade" / task_dir.name / f"{round_dir.name}.bind.json"
    )
    require_outside_task(task_dir, output)
    if output.exists() and not args.force:
        raise WorkflowError(
            f"a bind record already exists and is immutable: {portable_path(output)}; "
            "move it aside or pass --force to deliberately re-bind"
        )
    record = build_bind_record(task_dir, round_dir, seal_path)
    if seal_path is not None:
        record["precapture"] = copy_precapture(task_dir, round_dir.name, seal_path)
    write_json(output, record)
    print(render_bind(record))
    print(f"Bind record: {portable_path(output)}")
    return 0


# ----------------------------------------------------------------------------- harbor


def harbor_provenance(harbor_bin: str) -> dict[str, Any]:
    """Harbor's version and the sha256 of the ``regrade.py`` that will actually run."""
    tokens = shlex.split(harbor_bin)
    executable = tokens[0] if tokens else harbor_bin
    resolved = shutil.which(executable) or executable
    info: dict[str, Any] = {"bin": harbor_bin, "resolved_bin": str(resolved), "version": None,
                            "regrade_source": None, "regrade_source_sha256": None}
    try:
        completed = subprocess.run([*tokens, "--version"], capture_output=True, text=True, timeout=120)
        info["version"] = (completed.stdout or completed.stderr).strip().split()[-1] if (completed.stdout or completed.stderr).strip() else None
    except (OSError, subprocess.SubprocessError, IndexError):
        pass
    candidate: Path | None = None
    launcher = Path(resolved)
    try:
        shebang = launcher.read_bytes().split(b"\n", 1)[0]
    except OSError:
        shebang = b""
    if shebang.startswith(b"#!"):
        words = shebang[2:].decode("utf-8", errors="replace").split()
        interpreter = words[1] if len(words) > 1 and words[0].rsplit("/", 1)[-1] == "env" else (words[0] if words else "")
        if interpreter:
            try:
                completed = subprocess.run(
                    [interpreter, "-c", "import harbor.trial.regrade as m; print(m.__file__)"],
                    capture_output=True, text=True, timeout=120,
                )
                if completed.returncode == 0 and completed.stdout.strip():
                    candidate = Path(completed.stdout.strip())
            except (OSError, subprocess.SubprocessError):
                candidate = None
    if candidate is None or not candidate.is_file():
        matches = sorted(launcher.resolve().parent.parent.glob("lib/python*/site-packages/harbor/trial/regrade.py"))
        candidate = matches[0] if len(matches) == 1 else None
    if candidate is not None and candidate.is_file():
        info["regrade_source"] = str(candidate)
        info["regrade_source_sha256"] = f"sha256:{sha256_file(candidate)}"
    return info


def regrade_command(harbor_bin: str, source_job: Path, task_dir: Path, out_dir: Path, job_name: str, jobs: int) -> list[str]:
    return [
        *shlex.split(harbor_bin),
        "job",
        "regrade",
        str(source_job.resolve()),
        "-p",
        str(task_dir.resolve()),
        "-o",
        str(out_dir.resolve()),
        "--job-name",
        job_name,
        "-n",
        str(jobs),
    ]


def run_regrade_job(command: list[str], out_dir: Path, job_name: str, timeout_sec: float) -> tuple[int | None, str]:
    """One ``harbor job regrade``, its console captured, its process group killed on timeout."""
    console = out_dir / f"{job_name}.console.log"
    environment = {key: value for key, value in os.environ.items() if key != "TBENCH_TEST_ID"}
    # Re-run controls import scripts.harbor_recording from Harbor's own interpreter,
    # which does not put the working directory on sys.path (gate_step2b.sh does the same).
    environment["PYTHONPATH"] = str(REPO_ROOT) + (os.pathsep + environment["PYTHONPATH"]
                                                   if environment.get("PYTHONPATH") else "")
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    returncode: int | None = None
    message = ""
    with console.open("w", encoding="utf-8") as handle:
        handle.write(f"=== Starting regrade job: {job_name} at {started} ===\n")
        handle.write(f"$ {shlex.join(command)}\n")
        handle.flush()
        try:
            process = subprocess.Popen(command, cwd=REPO_ROOT, stdout=handle, stderr=subprocess.STDOUT,
                                       env=environment, start_new_session=True)
            try:
                returncode = process.wait(timeout=timeout_sec)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    try:
                        os.killpg(process.pid, sig)
                    except ProcessLookupError:
                        break
                    try:
                        process.wait(timeout=5)
                        break
                    except subprocess.TimeoutExpired:
                        continue
                if isinstance(exc, KeyboardInterrupt):
                    raise
                message = f"Harbor exceeded the local deadline of {timeout_sec:g}s"
                returncode = 124
        except OSError as exc:
            message = f"could not launch Harbor: {exc}"
        finished = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        handle.write(f"=== Finished regrade job: {job_name} with harbor={returncode} at {finished} ===\n")
    (out_dir / f"{job_name}.exit-codes.txt").write_text(f"harbor={returncode}\n", encoding="utf-8")
    return returncode, message


def evaluate_regraded_job(
    *,
    out_dir: Path,
    job_name: str,
    source_row: dict[str, Any],
    expected_cases: list[str],
    returncode: int | None,
    launch_error: str,
    enforce_controls: bool,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "job": job_name,
        "kind": source_row["kind"],
        "source_trial": source_row["trial"],
        "source_reward": source_row["reward"],
        "source_cases": source_row["cases"],
        "exit_code": returncode,
        "console_log": portable_path(out_dir / f"{job_name}.console.log"),
        "new_trial": None,
        "new_trial_dir": None,
        "reward": None,
        "errors": None,
        "exception": None,
        "reward_txt": None,
        "cases": [],
        "case_statuses": {},
        "result_sha256": None,
        "ctrf_sha256": None,
        "job_result_sha256": None,
        "status": "FAIL",
        "message": launch_error,
    }
    if launch_error:
        return row
    if returncode != 0:
        row["message"] = f"harbor job regrade exited {returncode}"
        return row
    job_dir = out_dir / job_name
    try:
        trial_dir = sole_trial_dir(job_dir)
        new = describe_trial(job_dir, trial_dir)
    except WorkflowError as exc:
        row["message"] = str(exc)
        return row
    job_result = job_dir / "result.json"
    if job_result.is_file():
        row["job_result_sha256"] = f"sha256:{sha256_file(job_result)}"
    row.update(
        {
            "new_trial": new["trial"],
            "new_trial_dir": new["trial_dir"],
            "reward": new["reward"],
            "errors": new["errors"],
            "exception": new["exception"],
            "reward_txt": new["reward_txt"],
            "cases": new["cases"],
            "case_statuses": new["case_statuses"],
            "result_sha256": new["result_sha256"],
            "ctrf_sha256": new["ctrf_sha256"],
        }
    )
    problems: list[str] = []
    if new["ctrf_error"]:
        problems.append(new["ctrf_error"])
    if new["errors"] or new["exception"]:
        problems.append(f"regraded trial reports errors={new['errors']} exception={new['exception']!r}")
    if new["reward"] != source_row["reward"]:
        problems.append(f"reward moved: source {source_row['reward']!r} -> regrade {new['reward']!r}")
    if new["reward_txt_value"] is None or new["reward_txt_value"] != new["reward"]:
        problems.append(f"verifier/reward.txt {new['reward_txt']!r} disagrees with result.json reward {new['reward']!r}")
    if new["cases"] != expected_cases:
        problems.append(f"CTRF cases {new['cases']!r} do not match the manifest's {expected_cases!r}")
    if enforce_controls and source_row["kind"] == "oracle":
        if new["reward"] != 1.0:
            problems.append(f"oracle control regraded to {new['reward']!r}, expected 1.0")
        failed = sorted(name for name, status in new["case_statuses"].items() if status != "passed")
        if failed:
            problems.append(f"oracle control has non-passing cases: {', '.join(failed)}")
    if enforce_controls and source_row["kind"] == "nop" and new["reward"] != 0.0:
        problems.append(f"nop control regraded to {new['reward']!r}, expected 0.0")
    row["status"] = "FAIL" if problems else "PASS"
    row["message"] = "; ".join(problems) if problems else "reward and CTRF case set reproduced exactly"
    return row


# ------------------------------------------------------------------------------- run


class PreconditionFailure(WorkflowError):
    """A guard that must hold before any container starts."""


def load_bind_record(path: Path) -> dict[str, Any]:
    record = load_json(path)
    if not isinstance(record, dict):
        raise WorkflowError("bind record must be a JSON object")
    if record.get("kind") != BIND_KIND or record.get("schema_version") != BIND_SCHEMA_VERSION:
        raise WorkflowError(f"{path} is not a {BIND_KIND} record of schema {BIND_SCHEMA_VERSION}")
    for key in ("task_slug", "round_dir", "digests", "task_paths", "trials"):
        if key not in record:
            raise WorkflowError(f"bind record is missing {key!r}")
    return record


def run_preconditions(
    *,
    task_dir: Path,
    record: dict[str, Any],
    out_dir: Path,
    allow_identical_grader: bool,
) -> tuple[dict[str, str], list[str]]:
    """Everything that must hold before a single container starts. Returns (digests, notes)."""
    notes: list[str] = []
    if record["task_slug"] != task_dir.name:
        raise WorkflowError(f"bind record is for {record['task_slug']!r}, not {task_dir.name!r}")
    assert_digest_partition(task_dir)
    current = split_digests(task_dir)
    recorded = record["digests"]

    # The decisive gate: the agent-facing surface must be byte-identical to capture.
    if current["agent"] != recorded["agent"]:
        contents, modes = source_inventory(task_dir)
        diff = inventory_diff(record["task_paths"], record.get("task_modes", {}), contents, modes, AGENT_SURFACE)
        lines = [
            "agent digest moved since the round was captured:",
            f"  recorded {recorded['agent']}",
            f"  current  {current['agent']}",
            *render_diff(diff),
            "this is a behavioral edit, not grader hardening; re-enter Step 2b and re-run Step 3c",
        ]
        raise PreconditionFailure("\n".join(lines))

    if current["grader"] == recorded["grader"] and not allow_identical_grader:
        raise PreconditionFailure(
            f"grader digest is unchanged ({current['grader']}): there is nothing to regrade. "
            "Edit tests/ first, or pass --allow-identical-grader to run the determinism null control."
        )
    if current["grader"] == recorded["grader"]:
        notes.append("null control: the grader surface is unchanged, so this run only proves verifier determinism")

    name_of_task = task_name(task_dir, read_task_toml(task_dir))
    if name_of_task != record.get("task_name"):
        raise PreconditionFailure(
            f"task.toml name moved from {record.get('task_name')!r} to {name_of_task!r}; "
            "Harbor matches recorded trials by name, so every captured trial is unregradable"
        )

    entries = declared_artifacts(read_task_toml(task_dir))
    if artifact_keys(entries) != record.get("artifact_keys"):
        raise PreconditionFailure(
            "declared artifacts changed: "
            f"recorded {record.get('artifact_keys')!r}, current {artifact_keys(entries)!r}; "
            "an added entry silently invalidates every captured trial for regrade"
        )

    parity = seed_parity(task_dir)
    if parity != record.get("seed_parity"):
        raise PreconditionFailure("tests/seed parity with environment/ changed since the round was captured")

    round_dir = resolve_recorded_path(record["round_dir"]).resolve()
    require_outside_task(task_dir, round_dir)
    fingerprint = round_fingerprint(round_dir)
    if fingerprint != record.get("round"):
        raise PreconditionFailure(
            f"captured round no longer hashes as bound: recorded {record.get('round', {}).get('digest')}, "
            f"current {fingerprint['digest']}"
        )

    # Records bound before the symlink rule existed: refuse here too, before any job runs.
    for row in record.get("trials", []):
        if row.get("kind") == "model" and row.get("job_dir"):
            try:
                links = artifact_symlinks(sole_trial_dir(resolve_recorded_path(row["job_dir"])))
            except (WorkflowError, OSError):
                links = []
            if links:
                raise PreconditionFailure(
                    f"{row['job']}: {len(links)} symlink(s) in the captured artifacts ({', '.join(links[:3])}); "
                    "Harbor's single-step regrade replay follows symlinks on the host, so this trial cannot be "
                    "regraded faithfully. Take a fresh Step 3c round at the current digest instead.")

    require_outside_task(task_dir, out_dir)
    if out_dir.exists():
        raise PreconditionFailure(f"choose a fresh output directory for this regrade round: {out_dir} already exists")
    # Harbor bakes the output path into every trial's config.json/result.json, which ship.
    # The bundled auditor rejects process-history words there (T3-ROUND-NAME), and a
    # finished regrade cannot be renamed afterwards, so refuse such a name up front.
    banned = ROUND_NAME_BAN.search(out_dir.name)
    if banned:
        raise PreconditionFailure(
            f"output directory name {out_dir.name!r} contains {banned.group(0)!r}, which the auditor bans from "
            "shipped trajectory paths (T3-ROUND-NAME); name it after the task alone, e.g. "
            f"evidence-{task_dir.name}-b")
    if out_dir.resolve() == round_dir or out_dir.resolve().is_relative_to(round_dir) or round_dir.is_relative_to(out_dir.resolve()):
        raise PreconditionFailure("the regrade output must not live inside the captured round")
    return current, notes


def write_run_provenance(out_dir: Path, task_dir: Path, record: dict[str, Any], digests: dict[str, str],
                         harbor: dict[str, Any], bind_path: Path, source_jobs: list[str]) -> None:
    (out_dir / "task-digest.txt").write_text(digests["full"] + "\n", encoding="utf-8")
    (out_dir / "agent-digest.txt").write_text(digests["agent"] + "\n", encoding="utf-8")
    (out_dir / "grader-digest.txt").write_text(digests["grader"] + "\n", encoding="utf-8")
    lines = [
        f"task {task_dir.name}, task digest {digests['full']}",
        f"agent digest {digests['agent']} (identical to capture; regrade is licensed only while this holds)",
        f"grader digest {record['digests']['grader']} -> {digests['grader']}",
        f"regrade of {record['round_dir']} ({record['round']['file_count']} files, {record['round']['digest']})",
        f"source jobs {', '.join(source_jobs)}; one `harbor job regrade` each, job names reused",
        f"harbor {harbor.get('version')} at {harbor.get('resolved_bin')}, "
        f"regrade.py {harbor.get('regrade_source_sha256')} ({harbor.get('regrade_source')})",
        f"bind record {portable_path(bind_path)} sha256:{sha256_file(bind_path)}",
        "TBENCH_TEST_ID stripped from the child environment (full-suite grading)",
        f"arch {platform.machine()}, started {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}, "
        f"console logs {portable_path(out_dir)}/<job>.console.log",
    ]
    (out_dir / "REGRADE-SOURCE.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_run(report: dict[str, Any]) -> str:
    lines = [
        f"Step 3c regrade: {report['status']} ({report['task_slug']} @ {report['round_name']})",
        f"  agent  digest {report['current_digests']['agent']} (bound {report['recorded_digests']['agent']})",
        f"  grader digest {report['recorded_digests']['grader']} -> {report['current_digests']['grader']}",
        f"  null control: {report['null_control']}; controls {'enforced' if report['has_controls'] else 'SKIPPED (round has no oracle-*/nop-* jobs)'}",
    ]
    diff = report["tests_diff"]
    lines.append(f"  tests/ diff: +{len(diff['added'])} -{len(diff['removed'])} ~{len(diff['modified'])}")
    lines.extend(render_diff(diff))
    for row in report["jobs"]:
        lines.append(
            f"  {row['status']:7s} {row['job']:42s} source={row['source_reward']} regrade={row['reward']} "
            f"exit={row['exit_code']}"
        )
        if row["status"] != "PASS":
            lines.append(f"    {row['message']}")
    for error in report.get("errors", []):
        lines.append(f"  FAIL {error}")
    return "\n".join(lines)


def command_run(args: argparse.Namespace) -> int:
    task_dir = args.task_dir.resolve()
    if not task_dir.is_dir():
        raise WorkflowError(f"task directory not found: {task_dir}")
    bind_path = args.record.resolve()
    record = load_bind_record(bind_path)
    out_dir = args.out.resolve()
    if args.jobs < 1:
        raise WorkflowError("--jobs must be at least 1")
    try:
        digests, notes = run_preconditions(
            task_dir=task_dir,
            record=record,
            out_dir=out_dir,
            allow_identical_grader=args.allow_identical_grader,
        )
    except PreconditionFailure as exc:
        print(f"Step 3c regrade: PRECONDITION FAILED\n{exc}", file=sys.stderr)
        return 2

    harbor_exe = shlex.split(args.harbor_bin)[0] if args.harbor_bin.strip() else ""
    if not args.dry_run and not shutil.which(harbor_exe) and not Path(harbor_exe).is_file():
        print(f"Step 3c regrade: PRECONDITION FAILED\nHarbor executable not found: {harbor_exe}", file=sys.stderr)
        return 2

    round_dir = resolve_recorded_path(record["round_dir"]).resolve()
    source_rows = {row["job"]: row for row in record["trials"]}
    # Trials bind recorded as not regradable (a control with no captured artifacts)
    # are re-run against the hardened verifier instead, not re-graded here.
    skipped_rows = {job: row for job, row in source_rows.items() if row.get("regradable") is False}
    source_jobs = sorted(job for job in source_rows if job not in skipped_rows)
    for job, row in sorted(skipped_rows.items()):
        notes.append(
            f"{job} ({row['kind']}) is not regradable and is skipped: {row.get('not_regradable_reason', 'no captured artifacts')}"
            " -- re-run this control against the new verifier instead"
        )
    if not source_jobs:
        print("Step 3c regrade: PRECONDITION FAILED\nno regradable trials in this round", file=sys.stderr)
        return 2
    expected_cases = manifest_cases(task_dir)
    contents, modes = source_inventory(task_dir)
    tests_diff = inventory_diff(record["task_paths"], record.get("task_modes", {}), contents, modes, GRADER_SURFACE)

    if args.dry_run:
        print(f"Step 3c regrade plan: {task_dir.name} @ {record['round_name']}")
        print(f"  agent  digest {digests['agent']} == bound (guard satisfied)")
        print(f"  grader digest {record['digests']['grader']} -> {digests['grader']}")
        for note in notes:
            print(f"  note: {note}")
        print(f"  tests/ diff: +{len(tests_diff['added'])} -{len(tests_diff['removed'])} ~{len(tests_diff['modified'])}")
        for line in render_diff(tests_diff):
            print(line)
        print(f"  output round {portable_path(out_dir)} (not created by --dry-run)")
        print(f"  expected CTRF cases per trial: {len(expected_cases)}")
        for job_name in source_jobs:
            command = regrade_command(args.harbor_bin, round_dir / job_name, task_dir, out_dir, job_name, args.jobs)
            print(f"  $ {shlex.join(command)}")
        print(f"  record would be written to {portable_path(regrade_output_path(task_dir, record['round_name']))}")
        return 0

    harbor = harbor_provenance(args.harbor_bin)
    out_dir.mkdir(parents=True, exist_ok=False)
    write_run_provenance(out_dir, task_dir, record, digests, harbor, bind_path, source_jobs)

    output = regrade_output_path(task_dir, record["round_name"])
    require_outside_task(task_dir, output)
    report: dict[str, Any] = {
        "schema_version": REGRADE_SCHEMA_VERSION,
        "kind": REGRADE_KIND,
        "status": "RUNNING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "task_slug": task_dir.name,
        "task_name": record["task_name"],
        "task_dir": portable_path(task_dir),
        "round_name": record["round_name"],
        "round_dir": record["round_dir"],
        "round": record["round"],
        "bind_record": portable_path(bind_path),
        "bind_record_sha256": f"sha256:{sha256_file(bind_path)}",
        "out_dir": portable_path(out_dir),
        "recorded_digests": record["digests"],
        "current_digests": digests,
        "final_digests": None,
        "null_control": digests["grader"] == record["digests"]["grader"],
        "allow_identical_grader": bool(args.allow_identical_grader),
        "has_controls": bool(record.get("has_controls")),
        "control_checks": "enforced" if record.get("has_controls") else "skipped: round has no oracle-*/nop-* jobs",
        "notes": notes,
        "tests_diff": tests_diff,
        "manifest_test_ids": manifest_ids(task_dir),
        "expected_cases": expected_cases,
        "harbor": harbor,
        "jobs_concurrency": args.jobs,
        "job_timeout_sec": args.job_timeout_sec,
        # Every job the round accounts for: re-graded plus re-run controls.
        "source_jobs": sorted([*source_jobs, *skipped_rows]),
        "jobs": [],
        "errors": [],
    }
    write_json(output, report)

    rows: list[dict[str, Any]] = []
    for job_name in source_jobs:
        command = regrade_command(args.harbor_bin, round_dir / job_name, task_dir, out_dir, job_name, args.jobs)
        returncode, launch_error = run_regrade_job(command, out_dir, job_name, args.job_timeout_sec)
        row = evaluate_regraded_job(
            out_dir=out_dir,
            job_name=job_name,
            source_row=source_rows[job_name],
            expected_cases=expected_cases,
            returncode=returncode,
            launch_error=launch_error,
            enforce_controls=bool(record.get("has_controls")),
        )
        row["command"] = command
        rows.append(row)
        report["jobs"] = rows
        # Rewritten after every job, so an interrupt still leaves a readable partial.
        write_json(output, report)

    # Controls that could not be re-graded (no captured artifacts) are RE-RUN fresh
    # against the hardened verifier, so the round still carries a control trace the
    # shipped grader actually produced. A control is local and free, so this costs
    # nothing; the alternative is shipping a NOP trace no current verifier ever saw.
    for job_name in sorted(skipped_rows):
        source_row = skipped_rows[job_name]
        kind = source_row.get("kind")
        adapter = {"nop": "scripts.harbor_recording:RecordingNop",
                   "oracle": "scripts.harbor_recording:RecordingOracle"}.get(kind)
        if adapter is None:
            continue
        command = [*shlex.split(args.harbor_bin), "run", "-p", str(task_dir), "-a", adapter,
                   "-n", "1", "--max-retries", "0", "-o", str(out_dir), "--job-name", job_name, "--yes"]
        returncode, launch_error = run_regrade_job(command, out_dir, job_name, args.job_timeout_sec)
        row = evaluate_regraded_job(
            out_dir=out_dir,
            job_name=job_name,
            source_row=source_row,
            expected_cases=expected_cases,
            returncode=returncode,
            launch_error=launch_error,
            enforce_controls=bool(record.get("has_controls")),
        )
        row["command"] = command
        row["rerun_not_regraded"] = True
        row["rerun_reason"] = source_row.get("not_regradable_reason", "no captured artifacts to re-grade")
        rows.append(row)
        report["jobs"] = rows
        write_json(output, report)

    errors: list[str] = []
    final = split_digests(task_dir)
    report["final_digests"] = final
    if final != digests:
        errors.append("the task changed while the regrade was running; rerun the whole round")
    if round_fingerprint(round_dir) != record["round"]:
        errors.append("the captured round changed while the regrade was running")
    if sorted(row["job"] for row in rows) != sorted([*source_jobs, *skipped_rows]):
        errors.append("not every source job produced a regraded or re-run job")
    if any(row["status"] != "PASS" for row in rows):
        errors.append("one or more regraded jobs failed")
    if not record.get("has_controls"):
        report["notes"] = [*report["notes"],
                           "oracle/nop control checks were skipped: the captured round has no control jobs"]
    report["errors"] = sorted(set(errors))
    report["status"] = "FAIL" if report["errors"] else "PASS"
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    write_json(output, report)
    print(render_run(report))
    print(f"Regrade record: {portable_path(output)}")
    print(f"Regrade round: {portable_path(out_dir)}")
    if report["status"] == "PASS":
        # Workspace disk rule: a regrade that PASSED retires this task's stale rounds (never
        # the bound source round, this output, or anything a live record still names).
        subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "prune_evidence.py"), "rounds",
                        "--task-dir", str(task_dir), "--exclude", out_dir.name, "--exclude", round_dir.name,
                        "--apply", "--reason", f"regrade {out_dir.name} PASS"], check=False)
    return 1 if report["status"] == "FAIL" else 0


def regrade_output_path(task_dir: Path, round_name: str) -> Path:
    return REPO_ROOT / "artifacts" / "regrade" / task_dir.name / f"{round_name}.regrade.json"


# ---------------------------------------------------------------------------- verify


def check_regrade_record(task_dir: Path, record_path: Path) -> list[str]:
    """Re-check a finished regrade record against the task as it stands now.

    Importable the way ``package_task.py`` already imports ``evidence.check_seal``: a
    nonempty list is the reason the regrade evidence must not be trusted.
    """
    task_dir = task_dir.resolve()
    try:
        record = load_json(record_path)
    except WorkflowError as exc:
        return [str(exc)]
    if not isinstance(record, dict):
        return ["regrade record must be a JSON object"]
    errors: list[str] = []
    if record.get("kind") != REGRADE_KIND or record.get("schema_version") != REGRADE_SCHEMA_VERSION:
        return [f"not a {REGRADE_KIND} record of schema {REGRADE_SCHEMA_VERSION}; rerun the regrade"]
    if record.get("status") != "PASS":
        errors.append(f"regrade status is {record.get('status')!r}, expected 'PASS'")
    if record.get("task_slug") != task_dir.name:
        errors.append(f"regrade record is for {record.get('task_slug')!r}, not {task_dir.name!r}")
    try:
        current = split_digests(task_dir)
    except WorkflowError as exc:
        return sorted({*errors, str(exc)})
    recorded = record.get("recorded_digests")
    final = record.get("final_digests")
    if not isinstance(recorded, dict) or not isinstance(final, dict):
        return sorted({*errors, "regrade record is missing its digest triples"})
    if final != current:
        errors.append("the task changed after the regrade; the record no longer describes this task")
    if recorded.get("agent") != current.get("agent"):
        errors.append("the agent-facing surface moved: the captured trajectories no longer belong to this task")
    if record.get("null_control") is not True and recorded.get("grader") == current.get("grader"):
        errors.append("the grader surface is identical to the bound one but the record is not a null control")
    for key in ("bind_record", "bind_record_sha256"):
        if not isinstance(record.get(key), str):
            errors.append(f"regrade record is missing {key}")
    bind_value = record.get("bind_record")
    if isinstance(bind_value, str):
        bind_path = resolve_recorded_path(bind_value)
        if not bind_path.is_file():
            errors.append(f"bind record is missing: {bind_value}")
        elif f"sha256:{sha256_file(bind_path)}" != record.get("bind_record_sha256"):
            errors.append("bind record changed after the regrade")
    rounds = record.get("round")
    round_value = record.get("round_dir")
    if isinstance(round_value, str) and isinstance(rounds, dict):
        round_dir = resolve_recorded_path(round_value)
        if not round_dir.is_dir():
            errors.append(f"captured round is gone; the regrade cannot be re-verified: {round_value}")
        else:
            try:
                if round_fingerprint(round_dir) != rounds:
                    errors.append("the captured round changed after the regrade")
            except WorkflowError as exc:
                errors.append(str(exc))
    else:
        errors.append("regrade record does not bind a captured round")
    expected_cases = record.get("expected_cases")
    try:
        if expected_cases != manifest_cases(task_dir):
            errors.append("the test manifest's CTRF cases changed after the regrade")
    except WorkflowError as exc:
        errors.append(str(exc))
    enforce_controls = bool(record.get("has_controls"))
    rows = record.get("jobs")
    source_jobs = record.get("source_jobs")
    if not isinstance(rows, list) or not rows:
        return sorted({*errors, "regrade record has no job rows"})
    if isinstance(source_jobs, list) and sorted(row.get("job") for row in rows if isinstance(row, dict)) != sorted(source_jobs):
        errors.append("the regraded job set does not match the bound source jobs")
    kinds: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"regrade row {index} must be an object")
            continue
        label = row.get("job", f"row {index}")
        kinds.add(str(row.get("kind")))
        if row.get("status") != "PASS":
            errors.append(f"{label}: status {row.get('status')!r}: {row.get('message')}")
        if row.get("exit_code") != 0:
            errors.append(f"{label}: harbor exited {row.get('exit_code')!r}")
        if row.get("reward") != row.get("source_reward"):
            errors.append(f"{label}: reward moved {row.get('source_reward')!r} -> {row.get('reward')!r}")
        if not finite_number(row.get("reward")):
            errors.append(f"{label}: regraded reward is not a finite number")
        if row.get("errors") or row.get("exception"):
            errors.append(f"{label}: verifier/Harbor error recorded")
        if isinstance(expected_cases, list) and row.get("cases") != expected_cases:
            errors.append(f"{label}: CTRF cases {row.get('cases')!r} do not match the manifest")
        if enforce_controls and row.get("kind") == "oracle":
            statuses = row.get("case_statuses")
            if row.get("reward") != 1.0:
                errors.append(f"{label}: oracle control reward {row.get('reward')!r}, expected 1.0")
            if not isinstance(statuses, dict) or any(status != "passed" for status in statuses.values()):
                errors.append(f"{label}: oracle control has non-passing CTRF cases")
        if enforce_controls and row.get("kind") == "nop" and row.get("reward") != 0.0:
            errors.append(f"{label}: nop control reward {row.get('reward')!r}, expected 0.0")
        for kind in ("result", "ctrf"):
            value = row.get(f"{kind}_sha256")
            if not isinstance(value, str):
                errors.append(f"{label}: missing regraded {kind} hash")
                continue
            trial_value = row.get("new_trial_dir")
            if not isinstance(trial_value, str):
                errors.append(f"{label}: regrade record has no trial directory")
                continue
            trial_dir = resolve_recorded_path(trial_value)
            path = trial_dir / "result.json" if kind == "result" else trial_dir / "verifier" / "ctrf.json"
            if not path.is_file():
                errors.append(f"{label}: regraded {kind} artifact is missing: {portable_path(path)}")
            elif f"sha256:{sha256_file(path)}" != value:
                errors.append(f"{label}: regraded {kind} artifact changed after the regrade")
    if enforce_controls and not {"oracle", "nop"} <= kinds:
        errors.append("controls were declared present but the regraded round has no oracle and nop jobs")
    return sorted(set(errors))


def command_verify(args: argparse.Namespace) -> int:
    task_dir = args.task_dir.resolve()
    if not task_dir.is_dir():
        raise WorkflowError(f"task directory not found: {task_dir}")
    errors = check_regrade_record(task_dir, args.record.resolve())
    print(f"Step 3c regrade evidence: {'FAIL' if errors else 'PASS'}")
    for error in errors:
        print(f"- {error}")
    return 1 if errors else 0


# ------------------------------------------------------------------------------- cli


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    bind = subparsers.add_parser(
        "bind",
        help="bind a captured Step 3c round to the current task (run BEFORE editing tests/)",
        description="Bind a captured Step 3c round to the current task. Run before editing tests/.",
    )
    bind.add_argument("--task-dir", type=Path, required=True, help="path to tasks/<task-name>")
    bind.add_argument("--round", type=Path, required=True, help="captured Step 3c round directory (holds the job dirs)")
    bind.add_argument("--seal", type=Path, help="Step 2b seal to check and freeze alongside the record")
    bind.add_argument("--output", type=Path,
                      help="bind record (default: artifacts/regrade/<task>/<round>.bind.json)")
    bind.add_argument("--force", action="store_true",
                      help="overwrite an existing bind record; the record is otherwise immutable")
    bind.set_defaults(func=command_bind)

    run = subparsers.add_parser(
        "run",
        help="regrade every captured trial against the hardened tests/ (run AFTER editing tests/)",
        description="Re-grade every trial of a bound round with `harbor job regrade`. Run after editing tests/.",
    )
    run.add_argument("--task-dir", type=Path, required=True, help="path to tasks/<task-name>")
    run.add_argument("--record", type=Path, required=True, help="the bind record written before tests/ was edited")
    run.add_argument("--out", type=Path, required=True, help="fresh directory for the regraded round, outside tasks/")
    run.add_argument("--harbor-bin", default="harbor", help="local Harbor executable (never stb)")
    run.add_argument("--allow-identical-grader", action="store_true",
                     help="permit an unchanged grader surface; that run is the verifier-determinism null control")
    run.add_argument("--dry-run", action="store_true",
                     help="print the planned harbor commands and the tests/ diff; start nothing, write nothing")
    run.add_argument("--jobs", type=int, default=1,
                     help="harbor --n-concurrent per regrade job (a Step 3c job holds one trial, so 1 is enough)")
    run.add_argument("--job-timeout-sec", type=float, default=DEFAULT_JOB_TIMEOUT_SEC,
                     help="local deadline for each `harbor job regrade` (default: 7200)")
    run.set_defaults(func=command_run)

    verify = subparsers.add_parser(
        "verify",
        help="re-check a finished regrade record against the task as it stands now",
        description="Re-check a finished regrade record. The core is check_regrade_record().",
    )
    verify.add_argument("--task-dir", type=Path, required=True, help="path to tasks/<task-name>")
    verify.add_argument("--record", type=Path, required=True, help="a <round>.regrade.json written by `run`")
    verify.set_defaults(func=command_verify)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return args.func(args)
    except WorkflowError as exc:
        print(f"regrade_step3c.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
