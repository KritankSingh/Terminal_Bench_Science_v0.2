#!/usr/bin/env python3
"""Build the delivery ZIP described by MASTER_CHECKLIST_TBSCI.md.

MASTER_CHECKLIST_TBSCI.md (repo root) is the source of truth, then
docs/DELIVERY_CHECKLIST.md, then docs/PACKAGE_RULES.md. Packaging refuses unless the
per-task record authoring/<task>/master-checklist.md answers every master check for the
current digest. It works in two phases. BUILD writes a candidate ZIP to
artifacts/package-candidates/<task>/ and runs scripts/verify_package.py and the bundled
TB-Science auditor's scripted legs (scripts/audit_task.py package) on it, deleting it on any
finding. PROMOTE (--promote) copies that exact candidate to Task_Ready_To_Submit/ only
after the auditor's judged review of it lints clean as "Ready to Submit" with zero
warnings (scripts/audit_task.py verdict) and nothing moved since the build. The ZIP holds one top-level ``<task-slug>/`` folder with exactly
four members:

    <task-slug>/<task-slug>/   instruction.md, task.toml, environment/, solution/, tests/
    <task-slug>/rubric.txt
    <task-slug>/oracle-nop-evidence/   oracle-1..3 (reward 1.0), nop-1..2 (reward 0.0)
    <task-slug>/trajectories/          run-01..run-05 plus SUMMARY.txt

The five GPT-5.6 trials of the archived Step 3c round are renamed ``run-01``..``run-05``
in launch order (``t1..t5``; a round assembled by ``compose_step3c.py`` is already
numbered in launch order across its source rounds, and ``verify_package.py`` refuses
runs whose ``result.json`` ``started_at`` does not strictly increase -- Master #94
item 1), carrying only that trial's ``agent/``, ``verifier/``, ``config.json``,
``result.json`` and the ``rubric_score.txt`` written for it. The Oracle and NOP controls
are reduced to ``ctrf.json``, ``reward.txt`` and ``test-stdout.txt`` each. Every reward
and the SUMMARY line are recomputed here from what is on disk; nothing is carried
forward from an earlier package. SUMMARY's ``sha=`` is the bundle sha a reviewer
recomputes inside the inner folder (Master #80, scripts/bundle_sha.py). Host paths in
each shipped config.json/result.json are rewritten repo-relative (Master #87); captured
model-name fields are never touched (Master #89).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile

from common import (
    split_digests,
    REPO_ROOT,
    WorkflowError,
    bundle_sha_lines,
    finite_number,
    load_json,
    nop_infrastructure_errors,
    portable_path,
    resolve_recorded_path,
    sha256_file,
    symlink_sha256,
    task_digest,
    trial_artifact_symlink,
)
from evidence import check_seal, sealed_report_digest
from master_checklist import check_record
from regrade_step3c import check_regrade_record
from stage_reports import check_stage_report
from task_check import validate_task
from audit_task import audit_package, audit_verdict
from verify_package import (
    RUBRIC_LINE as _RUBRIC_LINE,
    find_reasoning_effort,
    rubric_criteria as rubric_criteria_text,
    summary_text,
    validate_rubric_score_text,
    validate_rubric_text,
    verify_zip,
)


TASK_ROOT_FILES = ("task.toml", "instruction.md")
TASK_ROOT_DIRS = ("environment", "solution", "tests")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# docs/DELIVERY_CHECKLIST.md: five GPT-5.6 xhigh trials, three Oracle and two NOP
# controls. NOP x2 replaces the older NOP x1 rule.
MODEL_TRIALS = 5
ORACLE_JOBS = ("oracle-1", "oracle-2", "oracle-3")
NOP_JOBS = ("nop-1", "nop-2")
TRIAL_MEMBERS = ("config.json", "result.json")
TRIAL_TREES = ("agent",)
CONTROL_FILES = ("ctrf.json", "reward.txt", "test-stdout.txt")
# A model run's verifier/ ships only its canonical files (Master #90), as the controls do;
# task-specific extras (e.g. a compiler log a clean build leaves empty) stay in the round.
VERIFIER_FILES = CONTROL_FILES

# Nothing with these names may appear anywhere in the ZIP (Master #96).
BANNED_DIR_NAMES = frozenset({"__MACOSX", ".git", "__pycache__", ".cursor", ".claude", ".aider"})
BANNED_BASENAMES = frozenset({"SOURCE.txt", ".DS_Store", "AGENTS.md", "CLAUDE.md", "skills.md",
                              "rubrics.txt"})

DELIVERY_TIMEOUTS = (("agent", "timeout_sec"), ("verifier", "timeout_sec"),
                     ("environment", "build_timeout_sec"))
DELIVERY_TIMEOUT_SEC = 28800

# Directory names the external TB-Science audit tool prunes from its own package digest,
# and the file names it skips. Kept byte-identical to
# tools/final-tbsci-audit-master/scripts/tbsci_static_screen.py:task_digest (mirrored in that
# tool's trial_evidence.py); changing either side desynchronises the digest.
AUDITOR_PRUNED_DIRS = frozenset({
    "trajectories", "evidence", "__MACOSX", ".git", "__pycache__", ".pytest_cache",
    "node_modules",
})


def auditor_package_digest(entries: dict[str, tuple[Path | bytes, str]], prefix: str) -> str:
    """The audit tool's digest of the packaged task files, as a reportable number.

    The delivery layout has no legal home for a ``package-digest.txt`` member -- the
    ZIP's top level is exactly four folders and ``trajectories/`` is exactly
    ``run-01..05`` plus ``SUMMARY.txt`` -- so this is no longer written into the
    package. It is still computed from the member set being written and returned in the
    packaging report, so the audit tool's digest can be quoted without re-deriving it.
    """
    members = []
    for name, (_, member_digest) in entries.items():
        if not name.startswith(prefix):
            continue
        relative = name[len(prefix):]
        parts = relative.split("/")
        if any(part in AUDITOR_PRUNED_DIRS for part in parts[:-1]):
            continue
        base = parts[-1]
        if base == ".DS_Store" or base.startswith("._"):
            continue
        members.append((relative, member_digest))
    digest = hashlib.sha256()
    for name, member_digest in sorted(members):
        digest.update(name.encode("utf-8") + b"\0" + bytes.fromhex(member_digest))
    return digest.hexdigest()


def inventory(root: Path, *, exclude: set[str] | None = None,
              round_root: Path | None = None) -> dict[str, str]:
    """Return relative file hashes after rejecting symlinks and special files.

    With ``round_root`` (the Step 3c round ``<job>/<trial>/`` lives under), a symlink
    inside a trial's ``artifacts/`` is a valid submission (Master #55): it is never
    followed and is hashed from its link text, as archive_step3c.py recorded it in
    collection.json (common.symlink_sha256). Every other symlink is refused. Nothing
    under ``artifacts/`` ships, so the package itself stays symlink-free.
    """
    excluded = exclude or set()
    result: dict[str, str] = {}
    if not root.is_dir():
        raise WorkflowError(f"evidence directory not found: {root}")
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        if path.is_symlink():
            link = trial_artifact_symlink(round_root, path) if round_root is not None else None
            if link is None:
                raise WorkflowError(f"package input contains a symlink: {path}")
            result[relative] = symlink_sha256(link)
            continue
        if path.is_dir():
            continue
        if not path.is_file():
            raise WorkflowError(f"package input is not a regular file: {path}")
        result[relative] = sha256_file(path)
    return result


def validate_step3c(task: Path, root: Path, digest: str) -> tuple[dict, dict[str, str]]:
    collection_path = root / "collection.json"
    collection = load_json(collection_path)
    if not isinstance(collection, dict):
        raise WorkflowError(f"{collection_path} must contain a JSON object")
    errors: list[str] = []
    if collection.get("capture_status") != "COMPLETE" or collection.get("errors") != []:
        errors.append("Step 3c collection is not COMPLETE with an empty errors list")
    if collection.get("task") != task.name:
        errors.append("Step 3c collection task does not match the task directory")
    recorded_manifest_digest = collection.get("task_digest")
    # A round is stamped with the full digest at CAPTURE time. A later descriptive
    # [metadata] edit -- e.g. expert_time_estimate_hours corrected after the runs,
    # Master #94 item 4 -- moves the full digest while leaving both graded surfaces
    # byte-identical, so the round is still evidence for this task. archive_step3c.py
    # accepts that and records a `digest_note` in collection.json; Step 4 honours the
    # same note. Anything else is still refused.
    note = collection.get("digest_note") if isinstance(collection, dict) else None
    descriptive_only = False
    if isinstance(note, dict):
        current = split_digests(task)
        descriptive_only = (note.get("agent_digest") == current["agent"]
                            and note.get("grader_digest") == current["grader"]
                            and note.get("current_task_digest") == digest)
        if not descriptive_only:
            errors.append("Step 3c collection carries a digest_note that does not bind this task")

    if (recorded_manifest_digest is not None and recorded_manifest_digest != digest
            and not descriptive_only):
        errors.append("Step 3c collection task_digest does not match the current task")

    digest_path = root / "task-digest.txt"
    try:
        recorded_digest = digest_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise WorkflowError(f"cannot read Step 3c task-digest.txt: {exc}") from exc
    if recorded_digest != digest and not descriptive_only:
        errors.append("Step 3c task-digest.txt does not match the current task")

    expected = collection.get("source_sha256")
    if not isinstance(expected, dict) or not expected:
        errors.append("Step 3c collection has no source_sha256 inventory")
        expected = {}
    elif any(not isinstance(k, str) or not isinstance(v, str) or not SHA256_RE.fullmatch(v)
             for k, v in expected.items()):
        errors.append("Step 3c source_sha256 inventory is malformed")
    actual = inventory(root, exclude={"collection.json"}, round_root=root)
    if actual != expected:
        errors.append("Step 3c files differ from collection.json source_sha256")

    trials = collection.get("trials")
    if not isinstance(trials, list):
        errors.append("Step 3c collection has no trial records")
    else:
        counts = {kind: sum(1 for row in trials if isinstance(row, dict) and row.get("kind") == kind)
                  for kind in ("model", "oracle", "nop")}
        wanted = {"model": MODEL_TRIALS, "oracle": len(ORACLE_JOBS), "nop": len(NOP_JOBS)}
        if counts != wanted:
            errors.append(f"Step 3c trial inventory must be {wanted}; found {counts}")
    if errors:
        raise WorkflowError("; ".join(errors))
    return collection, inventory(root, round_root=root)


def rubric_criteria(rubric: Path) -> list[str]:
    return rubric_criteria_text(rubric.read_text(encoding="utf-8"))


def validate_rubric(rubric: Path) -> list[str]:
    """rubric.txt per Master #67 (the rule set lives in verify_package.py)."""
    return validate_rubric_text(rubric.read_text(encoding="utf-8"))


def load_task_toml(task: Path) -> dict:
    try:
        import tomllib
    except ModuleNotFoundError as exc:  # pragma: no cover - 3.10 only compiles here
        raise WorkflowError(
            "reading task.toml needs Python 3.11+; activate the workspace .venv"
        ) from exc
    path = task / "task.toml"
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"missing task.toml: {path}") from exc
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise WorkflowError(f"invalid task.toml: {exc}") from exc


def validate_delivery_task_toml(task: Path, data: dict) -> list[str]:
    """Delivery rules MASTER_CHECKLIST_TBSCI.md #62/#63/#65 put on task.toml.

    task_check.py already refuses these; they are re-asserted here because they are the
    rules most often reverted by hand just before packaging.
    """
    errors: list[str] = []
    if "version" in data:
        errors.append("task.toml must not carry a top-level version key (stale-schema residue, Master #65; "
                      "schema_version is optional)")
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    if "difficulty" in data or "difficulty" in metadata:
        errors.append("task.toml must not carry a difficulty field (Master #62)")
    for section, key in DELIVERY_TIMEOUTS:
        value = data.get(section, {}).get(key) if isinstance(data.get(section), dict) else None
        if not finite_number(value) or float(value) != DELIVERY_TIMEOUT_SEC:
            errors.append(f"[{section}].{key} must be {DELIVERY_TIMEOUT_SEC}")
    return errors


def validate_per_test(task: Path, seal_path: Path, digest: str) -> tuple[dict, dict, list[dict]]:
    errors = check_seal(task, seal_path)
    if errors:
        raise WorkflowError("Step 2b seal is not current: " + "; ".join(errors))
    seal = load_json(seal_path)
    if not isinstance(seal, dict) or seal.get("task_digest") != digest:
        raise WorkflowError("Step 2b seal does not bind to the current task digest")
    report_value = seal.get("per_test_report")
    if not isinstance(report_value, str):
        raise WorkflowError("Step 2b seal has no per-test report path")
    report_path = resolve_recorded_path(report_value).resolve()
    report = load_json(report_path)
    # The per-test matrix binds to the digest it was MEASURED at, which is the seal's own
    # digest unless the seal was re-stamped by `evidence.py reseal` for a descriptive
    # [metadata]-only edit. check_seal above has already proved that re-stamp legitimate
    # (both graded surfaces byte-identical, report hash and manifest IDs unmoved), so the
    # report is held to its measured digest rather than to the newer full digest.
    measured_digest = sealed_report_digest(seal)
    if measured_digest is None:
        raise WorkflowError("Step 2b seal records no task digest for its per-test report")
    if not isinstance(report, dict) or report.get("task_digest") != measured_digest:
        raise WorkflowError("per-test report does not bind to the digest its seal was measured at")
    records = report.get("records")
    if not isinstance(records, list) or not records:
        raise WorkflowError("per-test report has no Oracle/NOP records")

    jobs: list[dict] = []
    seen: set[Path] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise WorkflowError(f"per-test row {index} is not an object")
        job_value, job_name = record.get("job_dir"), record.get("job_name")
        if not isinstance(job_value, str) or not isinstance(job_name, str):
            raise WorkflowError(f"per-test row {index} has no job_dir/job_name")
        job = resolve_recorded_path(job_value).resolve()
        if not job.is_dir() or job.name != job_name:
            raise WorkflowError(f"per-test job directory is missing or mismatched: {job}")
        if job in seen:
            raise WorkflowError(f"per-test job directory is reused: {job}")
        seen.add(job)
        files = inventory(job)
        if not files:
            raise WorkflowError(f"per-test job is empty: {job}")
        jobs.append({
            "test_id": record.get("test_id"),
            "agent": record.get("agent"),
            "repeat": record.get("repeat"),
            "job_name": job_name,
            "source": job,
            "source_path": portable_path(job),
            "files_sha256": files,
        })
    return seal, report, jobs


def check_member_name(name: str) -> None:
    parts = name.split("/")
    for part in parts[:-1]:
        if part in BANNED_DIR_NAMES:
            raise WorkflowError(f"banned directory in package member: {name}")
    base = parts[-1]
    if base in BANNED_BASENAMES or base in BANNED_DIR_NAMES:
        raise WorkflowError(f"banned file in package member: {name}")
    # No README.md at the package root or the inner task root (Master #96, #103).
    if base == "README.md" and len(parts) <= 3:
        raise WorkflowError(f"README.md does not ship (Master #103): {name}")
    if base.startswith("._") or base.endswith(".pyc"):
        raise WorkflowError(f"banned file in package member: {name}")


def add_file(entries: dict[str, tuple[Path | bytes, str]], name: str, source: Path | bytes) -> None:
    if name in entries:
        raise WorkflowError(f"duplicate ZIP entry: {name}")
    check_member_name(name)
    if isinstance(source, Path):
        if source.is_symlink() or not source.is_file():
            raise WorkflowError(f"package source is not a regular file: {source}")
        digest = sha256_file(source)
    else:
        digest = hashlib.sha256(source).hexdigest()
    entries[name] = (source, digest)


def add_tree(entries: dict[str, tuple[Path | bytes, str]], source: Path, prefix: str) -> None:
    files = inventory(source)
    if not files:
        raise WorkflowError(f"package input directory is empty: {source}")
    for relative in sorted(files):
        add_file(entries, f"{prefix}/{relative}", source / relative)


def trial_dir(root: Path, row: dict, kind: str) -> tuple[str, Path]:
    job, trial = row.get("job"), row.get("trial")
    if not isinstance(job, str) or not isinstance(trial, str) or not job or not trial:
        raise WorkflowError(f"Step 3c {kind} trial record has no job/trial name")
    if "/" in job or "/" in trial or job.startswith(".") or trial.startswith("."):
        raise WorkflowError(f"Step 3c {kind} trial record has an unusable name: {job}/{trial}")
    path = root / job / trial
    if not path.is_dir():
        raise WorkflowError(f"Step 3c {kind} trial directory is missing: {path}")
    return job, path


def read_reward(trial: Path) -> float:
    """The reward this trial actually recorded, read fresh from the trial itself."""
    reward_path = trial / "verifier" / "reward.txt"
    try:
        text = reward_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise WorkflowError(f"cannot read {reward_path}: {exc}") from exc
    try:
        value = float(text)
    except ValueError as exc:
        raise WorkflowError(f"{reward_path} is not a number: {text[:40]!r}") from exc
    if not 0.0 <= value <= 1.0:
        raise WorkflowError(f"{reward_path} is outside 0.0-1.0: {value}")
    result = load_json(trial / "result.json")
    recorded = result.get("verifier_result") if isinstance(result, dict) else None
    recorded = recorded.get("rewards") if isinstance(recorded, dict) else None
    recorded = recorded.get("reward") if isinstance(recorded, dict) else None
    if not finite_number(recorded) or float(recorded) != value:
        raise WorkflowError(
            f"{trial}: verifier/reward.txt ({value}) and result.json ({recorded}) disagree")
    return value


def ctrf_summary(trial: Path) -> tuple[int, int, list[str]]:
    """(passed, total, statuses) from the trial's CTRF report."""
    data = load_json(trial / "verifier" / "ctrf.json")
    results = data.get("results") if isinstance(data, dict) else None
    summary = results.get("summary") if isinstance(results, dict) else None
    tests = results.get("tests") if isinstance(results, dict) else None
    if not isinstance(summary, dict) or not isinstance(tests, list) or not tests:
        raise WorkflowError(f"{trial}: verifier/ctrf.json has no usable results")
    statuses = []
    for row in tests:
        if not isinstance(row, dict) or not isinstance(row.get("status"), str):
            raise WorkflowError(f"{trial}: verifier/ctrf.json has a malformed test row")
        statuses.append(row["status"])
    total = summary.get("tests")
    passed = summary.get("passed")
    if not isinstance(total, int) or not isinstance(passed, int) or total != len(tests):
        raise WorkflowError(f"{trial}: verifier/ctrf.json summary does not match its test rows")
    return passed, total, statuses


def find_reasoning_effort(value: object) -> list[object]:
    found: list[object] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "reasoning_effort":
                found.append(item)
            else:
                found.extend(find_reasoning_effort(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(find_reasoning_effort(item))
    return found


def model_name(config: dict, trial: Path) -> str:
    agent = config.get("agent")
    name = agent.get("model_name") if isinstance(agent, dict) else None
    if not isinstance(name, str) or not name:
        raise WorkflowError(f"{trial}: config.json has no agent.model_name")
    # Harbor records the provider-qualified form `openai/@openai/gpt-5.6`. Master #77
    # strips through the last "/" and a leading "@", so SUMMARY names `gpt-5.6`.
    marker = name.find("/@")
    return name[marker + 1:] if marker >= 0 else name


def validate_run_config(trial: Path) -> str:
    """Confirm the captured effort is intact and return the model it names."""
    config = load_json(trial / "config.json")
    if not isinstance(config, dict):
        raise WorkflowError(f"{trial}: config.json must contain a JSON object")
    efforts = find_reasoning_effort(config)
    if not efforts:
        raise WorkflowError(
            f"{trial}: config.json has no reasoning_effort key; xhigh capture metadata "
            "is required on every run and must never be renamed or removed")
    bad = [item for item in efforts if item != "xhigh"]
    if bad:
        raise WorkflowError(f"{trial}: config.json reasoning_effort is {bad!r}, must be 'xhigh'")
    return model_name(config, trial)


def validate_rubric_score(path: Path, criteria: list[str], reward: float,
                          passed: int, total: int) -> list[str]:
    """One run's rubric_score.txt against the rubric and that run's own results.

    Writing the file is not packaging's job -- scoring a run needs its trajectory read --
    but shipping one that is missing, malformed, missing its per-verdict evidence, or
    carrying numbers from an earlier draft is (Master #70, #78, #86).
    """
    if path.is_symlink() or not path.is_file():
        return [f"missing rubric_score.txt: {path}"]
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"cannot read {path}: {exc}"]
    return [f"{path.name}: {error}" for error in validate_rubric_score_text(text, criteria, reward, passed, total)]


# Master #87: a run's config.json/result.json records where the capture ran
# (task.path, trials_dir, job and log dirs). Those host paths are rewritten
# repo-relative; nothing else in the file changes, least of all model names (#89).
def _host_prefixes() -> list[tuple[str, str]]:
    pairs = {}
    for root, replacement in ((REPO_ROOT, ""), (Path.home(), "~/")):
        for variant in {str(root), str(root.resolve())}:
            pairs[variant.rstrip("/") + "/"] = replacement
    return sorted(pairs.items(), key=lambda item: len(item[0]), reverse=True)


def scrub_host_paths(value: object, prefixes: list[tuple[str, str]]) -> object:
    if isinstance(value, str):
        for prefix, replacement in prefixes:
            if value == prefix.rstrip("/"):
                return replacement.rstrip("/") or "."
            value = value.replace(prefix, replacement)
        return value
    if isinstance(value, dict):
        return {key: scrub_host_paths(item, prefixes) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_host_paths(item, prefixes) for item in value]
    return value


# A run's config.json/result.json also records the workspace round directory the capture ran
# from (``trials_dir``, ``trial_uri``, and the ``path`` of a regrade's source trial). Those carry
# workspace round and trial tags (``evidence-<task>-b/<task>-gpt56-t1``), which are process
# history rather than part of a run. They are rewritten to the shipped layout; every other field,
# model names above all (#89), is left alone.
_ROUND_DIR = re.compile(r"^(?:file://)?evidence-[^/]+(?:/|$)")


def neutralize_round_paths(value: object, run: str) -> object:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if isinstance(item, str) and _ROUND_DIR.match(item):
                item = f"file://trajectories/{run}" if key == "trial_uri" else "trajectories"
            else:
                item = neutralize_round_paths(item, run)
            out[key] = item
        return out
    if isinstance(value, list):
        return [neutralize_round_paths(item, run) for item in value]
    return value


def scrubbed_capture(path: Path, run: str | None = None) -> Path | bytes:
    """The file itself when it carries no host path, else a scrubbed copy's bytes."""
    raw = path.read_bytes()
    prefixes = _host_prefixes()
    text = raw.decode("utf-8")
    if run is None and not any(prefix.rstrip("/") in text for prefix, _ in prefixes):
        return path
    data = json.loads(text)
    cleaned = scrub_host_paths(data, prefixes)
    if run is not None:
        cleaned = neutralize_round_paths(cleaned, run)
        if cleaned == data:
            return path
    if _model_names(cleaned) != _model_names(data):
        raise WorkflowError(f"{path}: scrubbing would change a captured model name (Master #89)")
    return (json.dumps(cleaned, indent=4, ensure_ascii=False) + "\n").encode("utf-8")


def _model_names(value: object, key: str = "") -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    if isinstance(value, dict):
        for name, item in value.items():
            if "model" in name.lower() and not isinstance(item, (dict, list)):
                found.append((name, item))
            found.extend(_model_names(item, name))
    elif isinstance(value, list):
        for item in value:
            found.extend(_model_names(item, key))
    return found


def package_task(
    task: Path,
    step3c: Path,
    output: Path,
    seal_path: Path,
    review_path: Path,
    difficulty_path: Path,
    rubric_scores: Path,
) -> dict:
    task, step3c, output = task.resolve(), step3c.resolve(), output.resolve()
    seal_path, review_path, difficulty_path, rubric_scores = (
        p.resolve() for p in (seal_path, review_path, difficulty_path, rubric_scores))
    if not task.is_dir():
        raise WorkflowError(f"task directory not found: {task}")
    trajectory_root = (task / "trajectories").resolve()
    if step3c.parent != trajectory_root:
        raise WorkflowError(
            f"Step 3c directory must be a direct child of {trajectory_root}: {step3c}"
        )
    if output.exists():
        raise WorkflowError(f"refusing to overwrite existing package: {output}")
    if output.is_relative_to(task):
        raise WorkflowError("package ZIP must be outside the task directory")

    record_errors, record_status = check_record(task, "package")
    if record_errors:
        raise WorkflowError("authoring/<task>/master-checklist.md is not complete for packaging "
                            "(python3 scripts/master_checklist.py check <task> --stage package): "
                            + "; ".join(record_errors))

    static = validate_task(task, strict=True)
    static_errors = [f"{row['check']}: {row['detail']}" for row in static["issues"]
                     if row["level"] in {"FAIL", "WARN"}]
    if static_errors:
        raise WorkflowError("task_check --strict failed: " + "; ".join(static_errors))

    digest = task_digest(task)
    toml_data = load_task_toml(task)
    toml_errors = validate_delivery_task_toml(task, toml_data)
    if toml_errors:
        raise WorkflowError("task.toml is not in delivery format: " + "; ".join(toml_errors))

    rubric = task / "rubric.txt"
    if rubric.is_symlink() or not rubric.is_file() or not rubric.read_text(encoding="utf-8").strip():
        raise WorkflowError(f"required local rubric is missing or empty: {rubric}")
    rubric_errors = validate_rubric(rubric)
    if rubric_errors:
        raise WorkflowError("rubric.txt is not valid: " + "; ".join(rubric_errors))
    criteria = rubric_criteria(rubric)

    seal, report, jobs = validate_per_test(task, seal_path, digest)
    report_errors = check_stage_report(task, review_path, "review")
    report_errors += check_stage_report(task, difficulty_path, "difficulty", review_path=review_path)
    if report_errors:
        raise WorkflowError("stage reports are not current: " + "; ".join(report_errors))
    try:
        difficulty_text = difficulty_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise WorkflowError(f"cannot read difficulty report: {exc}") from exc
    if portable_path(step3c) not in difficulty_text and step3c.name not in difficulty_text:
        raise WorkflowError("difficulty report does not name the selected Step 3c trajectory round")

    collection, step3c_files = validate_step3c(task, step3c, digest)

    # A round that was re-graded after capture may only ship if that regrade still
    # checks out: same agent surface, and every captured trial's reward reproduced.
    # Without this a grader change could quietly rewrite what the trials proved.
    # The record is named after the CAPTURED round, while the round being packaged is
    # the regrade OUTPUT, so match on out_dir rather than on the directory name.
    regrade_summary = None
    regrade_dir = REPO_ROOT / "artifacts" / "regrade" / task.name
    for candidate in sorted(regrade_dir.glob("*.regrade.json")) if regrade_dir.is_dir() else []:
        try:
            recorded_out = load_json(candidate).get("out_dir")
        except WorkflowError:
            continue
        if not isinstance(recorded_out, str):
            continue
        if Path(recorded_out).name != step3c.name:
            continue
        regrade_errors = check_regrade_record(task, candidate)
        if regrade_errors:
            raise WorkflowError("regrade record does not check out: " + "; ".join(regrade_errors))
        regrade_summary = portable_path(candidate)
        break

    trials = collection["trials"]
    slug = task.name
    root = f"{slug}"
    entries: dict[str, tuple[Path | bytes, str]] = {}

    # 1. The task itself, in its own folder: exactly the five checklist members.
    task_prefix = f"{root}/{slug}"
    for name in TASK_ROOT_FILES:
        add_file(entries, f"{task_prefix}/{name}", task / name)
    for name in TASK_ROOT_DIRS:
        add_tree(entries, task / name, f"{task_prefix}/{name}")

    # 2. rubric.txt, a sibling of the task folder rather than a member of it.
    add_file(entries, f"{root}/rubric.txt", rubric)

    # 3. Oracle x3 and NOP x2, reduced to the three files that carry the verdict.
    controls: list[dict] = []
    for kind, wanted in (("oracle", ORACLE_JOBS), ("nop", NOP_JOBS)):
        rows = [row for row in trials if isinstance(row, dict) and row.get("kind") == kind]
        found = sorted(trial_dir(step3c, row, kind)[0] for row in rows)
        if found != sorted(wanted):
            raise WorkflowError(f"{kind} control jobs must be {list(wanted)}; found {found}")
        for row in sorted(rows, key=lambda item: item["job"]):
            job, trial = trial_dir(step3c, row, kind)
            reward = read_reward(trial)
            passed, total, statuses = ctrf_summary(trial)
            if kind == "oracle":
                if reward != 1.0 or passed != total or set(statuses) != {"passed"}:
                    raise WorkflowError(
                        f"{job} must be reward 1.0 with every test passing; "
                        f"reward={reward}, passed={passed}/{total}, statuses={sorted(set(statuses))}")
            elif reward != 0.0 or passed != 0 or set(statuses) != {"failed"}:
                raise WorkflowError(
                    f"{job} must be reward 0.0 with every test failing; "
                    f"reward={reward}, passed={passed}/{total}, statuses={sorted(set(statuses))}")
            else:
                stdout = (trial / "verifier" / "test-stdout.txt").read_text(encoding="utf-8", errors="replace")
                infra = nop_infrastructure_errors(stdout)
                if infra:
                    raise WorkflowError(f"{job} fails through infrastructure, not assertions (Master #74): "
                                        + ", ".join(infra))
            for name in CONTROL_FILES:
                add_file(entries, f"{root}/oracle-nop-evidence/{job}/{name}",
                         trial / "verifier" / name)
            controls.append({"control": job, "kind": kind, "reward": reward,
                             "tests_passed": f"{passed}/{total}",
                             "source": portable_path(trial)})

    # 4. The five model trials as run-01..run-05, in launch order (Master #94 item 1). Only that trial's
    # own agent/, verifier/, config.json, result.json and rubric_score.txt ship; the
    # agent's submitted output artifacts do not (for a media task they are hundreds of
    # MB of WAV per trial against a few MB of trajectory), and neither do the job-level
    # console logs, which belong to the workspace round rather than to one run.
    model_rows = [row for row in trials if isinstance(row, dict) and row.get("kind") == "model"]
    ordered = sorted(model_rows, key=lambda row: (trial_order(row.get("job")), row.get("job")))
    rewards: list[float] = []
    models: set[str] = set()
    runs: list[dict] = []
    omitted_files = omitted_bytes = 0
    score_errors: list[str] = []
    for index, row in enumerate(ordered, 1):
        job, trial = trial_dir(step3c, row, "model")
        run = f"run-{index:02d}"
        models.add(validate_run_config(trial))
        reward = read_reward(trial)
        passed, total, _ = ctrf_summary(trial)
        rewards.append(reward)
        score = rubric_scores / f"{run}.txt"
        score_errors += validate_rubric_score(score, criteria, reward, passed, total)
        for name in TRIAL_MEMBERS:
            add_file(entries, f"{root}/trajectories/{run}/{name}", scrubbed_capture(trial / name, run))
        for name in TRIAL_TREES:
            add_tree(entries, trial / name, f"{root}/trajectories/{run}/{name}")
        for name in VERIFIER_FILES:
            add_file(entries, f"{root}/trajectories/{run}/verifier/{name}", trial / "verifier" / name)
        if score.is_file() and not score.is_symlink():
            add_file(entries, f"{root}/trajectories/{run}/rubric_score.txt", score)
        artifacts = trial / "artifacts"
        if artifacts.is_dir():
            # Counted, never shipped; an in-artifacts link (Master #55) counts its own
            # size, never its target's.
            for relative, _ in inventory(artifacts, round_root=step3c).items():
                omitted_files += 1
                omitted_bytes += (artifacts / relative).lstat().st_size
        runs.append({"run": run, "job": job, "trial": trial.name, "reward": reward,
                     "tests_passed": f"{passed}/{total}", "rubric_score": portable_path(score)})
    if score_errors:
        raise WorkflowError("rubric_score.txt files are not in delivery format: "
                            + "; ".join(score_errors))
    if len(models) != 1:
        raise WorkflowError(f"the five runs do not name one model: {sorted(models)}")
    model = models.pop()

    # 5. The two-line SUMMARY, computed from the rewards just read off disk. Its sha is
    # the bundle sha of exactly the task files entered above (Master #80).
    inner = f"{task_prefix}/"
    bundle = bundle_sha_lines([(name[len(inner):], source) for name, (source, _) in entries.items()
                               if name.startswith(inner)])
    add_file(entries, f"{root}/trajectories/SUMMARY.txt",
             summary_text(slug, bundle, model, rewards))
    # The measured rate is reported, never written into the task (Master #62).
    passes = sum(1 for reward in rewards if reward == 1.0)

    # Step 2b evidence (the seal, its per-test report and the sealed Oracle/NOP job
    # bundles) is verified above but never shipped: it proves the task is sound to us
    # and is not part of the artifact. See docs/PACKAGE_RULES.md.
    report_path = resolve_recorded_path(seal["per_test_report"]).resolve()
    auditor_digest = auditor_package_digest(entries, f"{root}/{slug}/")

    before = {name: digest_value for name, (_, digest_value) in entries.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED, allowZip64=True) as package:
            for name, (source, _) in sorted(entries.items()):
                if isinstance(source, Path):
                    package.write(source, name)
                else:
                    package.writestr(name, source)
        if task_digest(task) != digest:
            raise WorkflowError("task source changed while packaging")
        for name, (source, expected) in entries.items():
            if isinstance(source, Path) and sha256_file(source) != expected:
                raise WorkflowError(f"package source changed while writing: {source}")
        with zipfile.ZipFile(output) as package:
            if package.testzip() is not None:
                raise WorkflowError("package ZIP failed its CRC check")
            names = package.namelist()
            if len(names) != len(set(names)) or set(names) != set(entries):
                raise WorkflowError("package ZIP entry set differs from the validated input set")
            for name in names:
                check_member_name(name)
            for name, expected in before.items():
                with package.open(name) as handle:
                    if hashlib.sha256(handle.read()).hexdigest() != expected:
                        raise WorkflowError(f"package entry differs from its source: {name}")
        # The literal last step before a ZIP exists: every mechanical master check,
        # re-run over the finished archive rather than over its inputs (Master #97).
        findings = verify_zip(output)
        if findings:
            raise WorkflowError("verify_package.py rejected the ZIP: "
                                + "; ".join(f"Master {check}: {detail}" for check, detail in findings))
        # The bundled auditor's scripted legs (tbsci_static_screen.py + trial_evidence.py) over
        # the same ZIP: the reviewer will run them too, so nothing may surface there first.
        audit_failures, audit_leads, _ = audit_package(output)
        if audit_failures:
            raise WorkflowError("the TB-Science auditor rejected the ZIP (scripts/audit_task.py package): "
                                + "; ".join(audit_failures))
    except BaseException:
        output.unlink(missing_ok=True)
        raise

    return {
        "package": portable_path(output),
        "package_sha256": f"sha256:{sha256_file(output)}",
        "task": slug,
        "task_digest": digest,
        "entries": len(entries),
        "step3c_round": step3c.name,
        "step3c_files": len(step3c_files),
        "runs": runs,
        "rewards": rewards,
        "pass_rate": f"{passes}/{len(rewards)}",
        "bundle_sha": bundle,
        "master_checklist": record_status,
        "verify_package": "PASS",
        "auditor_package": "PASS",
        "auditor_leads": audit_leads,
        "model": model,
        "controls": controls,
        "artifacts_omitted": {"files": omitted_files, "bytes": omitted_bytes},
        # Informational: the external TB-Science audit tool's digest of the packaged task
        # files. The delivery layout has no member it could be written to.
        "auditor_task_digest": auditor_digest,
        # Verified, not shipped (docs/PACKAGE_RULES.md).
        "per_test_jobs_verified": len(jobs),
        "per_test_report": portable_path(report_path),
        "rubric": portable_path(rubric),
        "rubric_scores": portable_path(rubric_scores),
        "regrade_record_verified": regrade_summary,
    }


_TRAILING_INDEX = re.compile(r"(\d+)$")


def trial_order(job: object) -> tuple[int, int]:
    """Order model jobs by their trailing trial number: `<slug>-gpt56-t1` first.

    Names without one fall behind those with one and are then ordered by name, so the
    run-0N mapping is deterministic for any round.
    """
    match = _TRAILING_INDEX.search(job) if isinstance(job, str) else None
    return (0, int(match.group(1))) if match else (1, 0)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--step3c-dir", type=Path,
                        help="build: archived COMPLETE Step 3c directory named by the difficulty report")
    parser.add_argument("--promote", action="store_true",
                        help="promote the audited candidate to Task_Ready_To_Submit/<task>.zip")
    parser.add_argument("--candidate-dir", type=Path,
                        help="where candidates live (default: artifacts/package-candidates/<task>/)")
    parser.add_argument("--output", type=Path,
                        help="promote: final ZIP (default: Task_Ready_To_Submit/<task-name>.zip)")
    parser.add_argument("--seal", type=Path,
                        help="Step 2b seal (default: artifacts/gates/<task>/step2b.json)")
    parser.add_argument("--review", type=Path,
                        help="paper review (default: artifacts/reviews/<task>.md)")
    parser.add_argument("--difficulty", type=Path,
                        help="difficulty report (default: artifacts/difficulty/<task>.md)")
    parser.add_argument("--rubric-scores", type=Path,
                        help="directory holding run-01.txt..run-05.txt "
                             "(default: artifacts/rubric-scores/<task>/<round>/)")
    args = parser.parse_args(argv)
    if not args.promote and args.step3c_dir is None:
        parser.error("--step3c-dir is required to build a candidate")
    return args


def promote(task: Path, candidate: Path, record_path: Path, output: Path) -> dict:
    """Phase 2: ship the candidate only if nothing moved and the auditor judged THIS ZIP ready."""
    task = task.resolve()
    if output.exists():
        raise WorkflowError(f"refusing to overwrite existing package: {output}")
    if not candidate.is_file() or not record_path.is_file():
        raise WorkflowError(f"no candidate for {task.name}; build it first: "
                            f"python3 scripts/package_task.py {portable_path(task)} --step3c-dir <round>")
    record = load_json(record_path)
    errors: list[str] = []
    if f"sha256:{sha256_file(candidate)}" != record.get("package_sha256"):
        errors.append("the candidate ZIP changed after it was built; rebuild it")
    if task_digest(task) != record.get("task_digest"):
        errors.append("the task changed after the candidate was built; it goes back to its gate")
    record_errors, _ = check_record(task, "package")
    errors += [f"master record: {error}" for error in record_errors]
    errors += [f"Master {check}: {detail}" for check, detail in verify_zip(candidate)]
    audit_failures, _, _ = audit_package(candidate)
    errors += audit_failures
    errors += audit_verdict(candidate)
    if errors:
        raise WorkflowError("; ".join(errors))
    output.parent.mkdir(parents=True, exist_ok=True)
    data = candidate.read_bytes()
    with output.open("xb") as handle:
        handle.write(data)
    stat = candidate.stat()
    os.utime(output, (stat.st_atime, stat.st_mtime))
    if f"sha256:{sha256_file(output)}" != record["package_sha256"]:
        output.unlink(missing_ok=True)
        raise WorkflowError("promoted ZIP differs from the audited candidate")
    return {"package": portable_path(output), "package_sha256": record["package_sha256"],
            "task_digest": record["task_digest"], "bundle_sha": record.get("bundle_sha"),
            "auditor_verdict": "Ready to Submit", "verify_package": "PASS", "master_checklist": "PASS"}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    slug = args.task_dir.resolve().name
    candidate_dir = args.candidate_dir or REPO_ROOT / "artifacts" / "package-candidates" / slug
    candidate = candidate_dir / f"{slug}.zip"
    record_path = candidate_dir / f"{slug}.candidate.json"
    try:
        if args.promote:
            output = args.output or REPO_ROOT / "Task_Ready_To_Submit" / f"{slug}.zip"
            result = promote(args.task_dir, candidate, record_path, output)
            print("Package: PASS (promoted)")
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        round_name = args.step3c_dir.resolve().name
        seal = args.seal or REPO_ROOT / "artifacts" / "gates" / slug / "step2b.json"
        review = args.review or REPO_ROOT / "artifacts" / "reviews" / f"{slug}.md"
        difficulty = args.difficulty or REPO_ROOT / "artifacts" / "difficulty" / f"{slug}.md"
        scores = args.rubric_scores or REPO_ROOT / "artifacts" / "rubric-scores" / slug / round_name
        # A candidate is not a deliverable: rebuilding replaces it, and any auditor review of
        # the old one stops matching (audit_task.py verdict compares the bytes).
        candidate_dir.mkdir(parents=True, exist_ok=True)
        candidate.unlink(missing_ok=True)
        record_path.unlink(missing_ok=True)
        result = package_task(args.task_dir, args.step3c_dir, candidate, seal, review, difficulty,
                              scores)
        record_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, UnicodeError, ValueError, WorkflowError, zipfile.BadZipFile) as exc:
        print(f"Package: FAIL\n- {exc}")
        return 1
    print("Package: PASS (candidate)")
    print(json.dumps(result, indent=2, sort_keys=True))
    auditor = "tools/final-tbsci-audit-master/scripts/review.sh"
    print(f"""
Next -- the auditor's judged review of THIS candidate (SKILL.md), then promote:
  {auditor} extract {portable_path(candidate)}
  {auditor} audit {slug}          # read the task; fill verdict.json + manual_probes.txt; answer every LEAD
  {auditor} lint {slug}           # must end: LINT_OK  ✅ Ready to Submit  (0 warning(s))
  python3 scripts/package_task.py {portable_path(args.task_dir.resolve())} --promote""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
