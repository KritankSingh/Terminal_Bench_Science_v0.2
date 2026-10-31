#!/usr/bin/env python3
"""Copy and hash all Step 3c jobs, including failed runs, into tasks/<task>/trajectories/.

The task-local copy is made with hard links where the filesystem allows (same bytes,
no second copy on disk; files the user cannot link, e.g. root-owned Harbor output,
are copied). A local evidence zip is written only when --zip is given: nothing in the
workflow reads it, so by default the round is not stored a third time (workspace disk
rule, see scripts/prune_evidence.py)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import time
import zipfile

from common import (WorkflowError, evidence_inventory, sha256_file, split_digests, symlink_sha256,
                    task_digest, write_json)


# Full-fidelity policy (docs/reference/stb-full-fidelity-kit/): a model attempt at any
# other reasoning effort, with a truncated observation, or without the raw API log is
# not difficulty evidence.
REQUIRED_REASONING_EFFORT = "xhigh"
_TRUNCATED = re.compile(r"\[\.\.\. output limited to \d+ bytes; \d+ interior bytes omitted \.\.\.\]")

# docs/DELIVERY_CHECKLIST.md: oracle x3 (reward 1.0, every test passing) and
# nop x2 (reward 0.0, every test failing). One NOP cannot show the zero reproduces.
_CONTROL_JOBS = {"oracle-1": (1, "oracle"), "oracle-2": (1, "oracle"), "oracle-3": (1, "oracle"),
                 "nop-1": (1, "nop"), "nop-2": (1, "nop")}
_PER_TRIAL_MODEL = re.compile(r"(?:^|-)gpt56-t([1-5])$")
_BATCH_MODEL = re.compile(r"^gpt56-k([1-9][0-9]*)$")


def inventory(root: Path, links: dict[str, str] | None = None) -> dict[str, str]:
    # Master #55: a symlink inside a trial's artifacts/ is hashed from its link text and
    # kept as a link; any other symlink is refused.
    return evidence_inventory(
        root, "Evidence contains a symlink outside a trial's artifacts/; preserve and inspect it manually",
        links=links)


def zip_symlink(package: zipfile.ZipFile, path: Path, arcname: str) -> None:
    """Store a symlink as a symlink entry (S_IFLNK mode, link text as data), never its target."""
    info = zipfile.ZipInfo(arcname, time.localtime(path.lstat().st_mtime)[:6])
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    package.writestr(info, os.fsencode(os.readlink(path)))


def expected_jobs(jobs: Path) -> dict[str, tuple[int, str]]:
    """Discover model jobs: ``gpt56-kN``, legacy ``gpt56-k5``, or per-attempt ``*-gpt56-tN``."""
    found: dict[str, tuple[int, str]] = {}
    for child in jobs.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        batch = _BATCH_MODEL.fullmatch(name)
        if batch:
            found[name] = (int(batch.group(1)), "model")
        elif name == "gpt56-k5":
            found[name] = (5, "model")
        elif _PER_TRIAL_MODEL.search(name):
            found[name] = (1, "model")
    if not found:
        # Default full Step 3c layout when nothing has been written yet.
        for i in range(1, 6):
            found[f"gpt56-t{i}"] = (1, "model")
    found.update(_CONTROL_JOBS)
    return found


def read_optional_digest(path: Path) -> str:
    """Read a recorded digest file, or return '' when the round does not carry one."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return ""


def _link_or_copy_under(root: Path):
    """copy_function for copytree: hard-link trial files; COPY the round's top-level files
    (fidelity-check.log, audit-dossier.md, ... can be re-written in place later, which
    would otherwise change the task-local copy too)."""
    def _copy(src: str, dst: str) -> None:
        if Path(src).parent == root:
            shutil.copy2(src, dst)
            return
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
    return _copy


def collect(task: Path, jobs: Path, archive: Path | None) -> dict:
    task, jobs = task.resolve(), jobs.resolve()
    archive = archive.resolve() if archive is not None else None
    if not task.is_dir() or not jobs.is_dir():
        raise WorkflowError("Task and jobs directories must already exist")
    if jobs == task or jobs.is_relative_to(task) or task.is_relative_to(jobs):
        raise WorkflowError("Jobs must be outside the task tree and must not contain it")
    if archive is not None and (archive.is_relative_to(jobs) or archive.is_relative_to(task)):
        raise WorkflowError("Evidence zip must be outside jobs and the task tree")
    destination = task / "trajectories" / jobs.name
    manifest = jobs / "collection.json"
    if destination.exists() or (archive is not None and archive.exists()) or manifest.exists():
        raise WorkflowError("Refusing to overwrite an existing archive, collection, or trial copy; use a fresh output directory")
    current_digest = task_digest(task)
    try:
        recorded_digest = (jobs / "task-digest.txt").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise WorkflowError(f"Step 3c jobs have no readable task-digest.txt: {exc}") from exc
    digest_note = None
    if recorded_digest != current_digest:
        # A descriptive [metadata] edit (e.g. expert_time_estimate_hours corrected after
        # the runs, MASTER_CHECKLIST_TBSCI.md #94 item 4) moves the FULL digest while
        # leaving both graded surfaces untouched. The agent saw the same bytes and the
        # grader scored them the same way, so the round is still evidence for this task.
        # Accept only when BOTH halves match, and record that the full digests differ and
        # why, rather than rewriting the round's own stamp.
        recorded_agent = read_optional_digest(jobs / "agent-digest.txt")
        recorded_grader = read_optional_digest(jobs / "grader-digest.txt")
        current = split_digests(task)
        if not (recorded_agent and recorded_grader):
            raise WorkflowError(
                f"Step 3c jobs bind to {recorded_digest or '<empty>'}, current task is "
                f"{current_digest}, and the round records no agent/grader digest to fall back on"
            )
        if recorded_agent != current["agent"] or recorded_grader != current["grader"]:
            raise WorkflowError(
                f"Step 3c jobs bind to {recorded_digest or '<empty>'}, current task is {current_digest}; "
                f"agent {recorded_agent} -> {current['agent']}, grader {recorded_grader} -> {current['grader']}"
            )
        digest_note = {
            "captured_task_digest": recorded_digest,
            "current_task_digest": current_digest,
            "agent_digest": current["agent"],
            "grader_digest": current["grader"],
            "reason": "descriptive [metadata] only; agent and grader surfaces byte-identical",
        }
    links: dict[str, str] = {}
    hashes = inventory(jobs, links)
    errors, records = [], []
    job_plan = expected_jobs(jobs)
    model_trial_count = sum(
        expected for name, (expected, kind) in job_plan.items() if kind == "model" and (jobs / name).is_dir())
    if model_trial_count != 5:
        errors.append(
            f"model jobs: expected 5 attempts for full Step 3c, found {model_trial_count} "
            f"({', '.join(sorted(n for n, (_, k) in job_plan.items() if k == 'model' and (jobs / n).is_dir())) or 'none'})")


    if "gpt56-k5" not in job_plan and not any(_BATCH_MODEL.fullmatch(n) for n in job_plan):
        attempt_ids = sorted(
            int(match.group(1)) for name, (_, kind) in job_plan.items()
            if kind == "model" and (jobs / name).is_dir()
            and (match := _PER_TRIAL_MODEL.search(name)))
        if attempt_ids != [1, 2, 3, 4, 5]:
            errors.append(f"model attempt identities: expected t1 through t5 exactly once, found {attempt_ids}")

    def require_json(path):
        try:
            value = json.loads(path.read_text())
            if not isinstance(value, dict):
                raise ValueError("expected a JSON object")
            return value
        except (OSError, ValueError) as exc:
            errors.append(f"{path.relative_to(jobs)}: {exc}")
            return {}

    for job_name, (expected, kind) in sorted(job_plan.items()):
        job = jobs / job_name
        if not job.is_dir():
            if kind != "model":
                errors.append(f"{job_name}: missing job directory")
            continue
        require_json(job / "config.json")
        require_json(job / "result.json")
        trials = sorted(path for path in job.iterdir() if path.is_dir() and any(
            (path / marker).exists() for marker in ("config.json", "result.json", "agent", "verifier")))
        if len(trials) != expected:
            errors.append(f"{job_name}: expected {expected} trials, found {len(trials)}")
        for trial in trials:
            config = require_json(trial / "config.json")
            result = require_json(trial / "result.json")
            recorded_task = result.get("task_name")
            # Harbor may record org/slug (task.toml [task].name) or bare slug.
            if recorded_task is not None and Path(str(recorded_task)).name != task.name:
                errors.append(f"{trial.relative_to(jobs)}: task_name does not match {task.name}")
            configured_task = (config.get("task") if isinstance(config.get("task"), dict) else {}).get("path")
            if configured_task is not None and (not isinstance(configured_task, str)
                                                or Path(configured_task).name != task.name):
                errors.append(f"{trial.relative_to(jobs)}: configured task does not match {task.name}")
            ctrf = require_json(trial / "verifier/ctrf.json")
            cases = (ctrf.get("results") if isinstance(ctrf.get("results"), dict) else {}).get("tests")
            if not isinstance(cases, list) or not cases:
                errors.append(f"{trial.relative_to(jobs)}: missing CTRF test records")
            required = ["trial.log", "verifier/reward.txt"]
            if kind == "model":
                trajectory = require_json(trial / "agent/trajectory.json")
                if not isinstance(trajectory.get("steps"), list) or not trajectory["steps"]:
                    errors.append(f"{trial.relative_to(jobs)}: ATIF steps missing")
                elif _TRUNCATED.search(json.dumps(trajectory["steps"])):
                    errors.append(f"{trial.relative_to(jobs)}: truncated observation in ATIF steps (output cap was active)")
                recording = require_json(trial / "agent/recording_config.json")
                if recording.get("max_output_bytes") != 0:
                    errors.append(f"{trial.relative_to(jobs)}: uncapped adapter setting was not recorded")
                if recording.get("reasoning_effort") != REQUIRED_REASONING_EFFORT:
                    errors.append(f"{trial.relative_to(jobs)}: reasoning_effort is "
                                  f"{recording.get('reasoning_effort')!r}, required {REQUIRED_REASONING_EFFORT!r}")
                if not recording.get("raw_api_log"):
                    errors.append(f"{trial.relative_to(jobs)}: raw API log was not enabled (stb-bundled harbor unpatched?)")
                api_log = trial / "agent/api-calls.jsonl"
                if not api_log.is_file() or api_log.stat().st_size == 0:
                    errors.append(f"{trial.relative_to(jobs)}/agent/api-calls.jsonl: missing or empty")
                required += ["agent/recording.cast"]
                if not list((trial / "agent/terminal-output").glob("*.txt")):
                    errors.append(f"{trial.relative_to(jobs)}: raw terminal observations missing")
            else:
                required += ["agent/execution_trace.jsonl"]
                try:
                    events = [json.loads(line) for line in
                              (trial / "agent/execution_trace.jsonl").read_text().splitlines()]
                    if (not events or any(not isinstance(event, dict) for event in events)
                            or events[0].get("event") != "run_start"
                            or events[-1].get("event") not in ("run_end", "run_error")):
                        raise ValueError("execution trace lacks start/end or error records")
                except (OSError, ValueError) as exc:
                    errors.append(f"{trial.relative_to(jobs)}/agent/execution_trace.jsonl: {exc}")
                if kind == "oracle":
                    required += ["agent/oracle.txt"]
            for relative in required:
                if not (trial / relative).is_file():
                    errors.append(f"{trial.relative_to(jobs)}/{relative}: missing")
            records.append({"job": job_name, "trial": trial.name, "kind": kind,
                            "source": str(trial), "copy": str(destination / job_name / trial.name),
                            "reward": (result.get("verifier_result") if isinstance(result.get("verifier_result"), dict) else {}).get("rewards"),
                            "exception": result.get("exception_info"),
                            "trace_format": "ATIF" if kind == "model" else "execution-trace-jsonl"})

    if inventory(jobs) != hashes:
        raise WorkflowError("Job files changed during collection; wait for every job to finish")
    report = {"schema_version": "1.1", "task": task.name, "task_digest": current_digest,
              "capture_status": "INCOMPLETE" if errors else "COMPLETE",
              "note": "Capture completeness is not a task validity or difficulty verdict.",
              "errors": errors, "trials": records, "source_sha256": hashes,
              "copy": str(destination), "zip": str(archive) if archive is not None else None}
    if digest_note is not None:
        # The round was captured before a descriptive [metadata] edit. Both graded
        # surfaces are byte-identical, so the evidence still binds; the record says so
        # explicitly rather than leaving two different full digests unexplained.
        report["digest_note"] = digest_note
    if links:
        # In-artifacts symlinks (Master #55), by path, with their exact link text. Their
        # source_sha256 entry is sha256(b"symlink\0" + link text); the link is never followed.
        report["symlinks"] = links
    write_json(manifest, report)
    hashes["collection.json"] = sha256_file(manifest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(jobs, destination, symlinks=True, copy_function=_link_or_copy_under(jobs))
    if inventory(destination) != hashes or inventory(jobs) != hashes:
        raise WorkflowError("Evidence changed while copying; retained copies require inspection")
    if archive is None:
        return report
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED, allowZip64=True) as package:
        for path in sorted(destination.rglob("*")):
            arcname = (Path(jobs.name) / path.relative_to(destination)).as_posix()
            if path.is_symlink():
                zip_symlink(package, path, arcname)
            else:
                package.write(path, arcname)
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise WorkflowError("Evidence zip failed its integrity check")
        # Compare decompressed bytes against the retained originals, not just CRCs.
        import hashlib
        for relative, expected in hashes.items():
            with package.open(f"{jobs.name}/{relative}") as handle:
                data = handle.read()
                actual = (symlink_sha256(os.fsdecode(data)) if relative in links
                          else hashlib.sha256(data).hexdigest())
                if actual != expected:
                    raise WorkflowError(f"Evidence zip differs from source: {relative}")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", type=Path, required=True)
    parser.add_argument("--jobs-dir", type=Path, required=True)
    parser.add_argument("--zip", type=Path, default=None,
                        help="optional local evidence zip (not read by any later step; omitted by default)")
    args = parser.parse_args(argv)
    try:
        report = collect(args.task_dir, args.jobs_dir, args.zip)
    except (OSError, ValueError, WorkflowError, zipfile.BadZipFile) as exc:
        parser.exit(2, f"archive_step3c.py: {exc}\n")
    print(json.dumps(report, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
