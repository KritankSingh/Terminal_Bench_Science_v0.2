#!/usr/bin/env python3
"""Shared, dependency-free helpers for the hardened Terminal-Bench Science workflow."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TEST_ID_RE = SLUG_RE

# The two halves of the behavioral task surface, matched against the first
# component of each path relative to the task root. Together they must cover
# every task-root entry that survives task_paths() pruning; see
# assert_digest_partition().
AGENT_SURFACE = ("task.toml", "instruction.md", "environment", "solution")
GRADER_SURFACE = ("tests",)
# Task-root entries that the FULL digest covers but neither graded surface does. None:
# tasks in this workspace carry no README.md (Master #103) -- the write-ups are workspace
# records under authoring/<task>/. Descriptive-only re-seals (gate_step2b.sh --reseal-only)
# cover the descriptive [metadata] keys below, and removing a legacy README.md, which was
# never copied into a container nor read by the grader.
DESCRIPTIVE_SURFACE: tuple[str, ...] = ()

TASK_DIGEST_PREFIX = b"tbench-task-digest-v2\0"
AGENT_DIGEST_PREFIX = b"tbench-agent-digest-v2\0"
GRADER_DIGEST_PREFIX = b"tbench-grader-digest-v1\0"

# The agent digest is versioned because its DEFINITION changed, not just its inputs:
# v1 folded task.toml byte-for-byte, v2 folds out DESCRIPTIVE_METADATA_KEYS (below).
# A seal written under v1 therefore stores a v1 value, and comparing it against a
# freshly computed v2 value reports "the agent-facing surface changed" for every
# pre-existing seal, whether or not a single agent-facing byte moved. Seals record
# which fold produced their value; check_seal() compares like with like.
AGENT_DIGEST_VERSION = "v2"
LEGACY_AGENT_DIGEST_PREFIX = b"tbench-agent-digest-v1\0"

# `task.toml` is never copied into the agent container -- Harbor reads it to configure
# the trial, and the agent reads `instruction.md`. So a descriptive [metadata] field
# cannot change what the agent saw, what it did, or how it was graded. Hashing those
# fields into the agent digest made correcting a difficulty tier (or an author email)
# invalidate five paid model trials, which is why they are folded out below. The FULL
# task digest still hashes task.toml byte-for-byte, so every existing seal, review and
# archived round stays valid -- only the agent-surface view changes. `difficulty` is
# banned from task.toml outright (MASTER_CHECKLIST_TBSCI.md #62; task_check.py FAILs it)
# but stays listed so the v2 fold, and every seal written under it, is unchanged.
DESCRIPTIVE_METADATA_KEYS = frozenset({
    "author_name", "author_email", "author_organization",
    "difficulty", "difficulty_explanation", "solution_explanation",
    "verification_explanation", "relevant_experience",
    "category", "subcategory", "tags", "languages",
    "domain", "field", "subfield",
    "expert_time_estimate_hours", "referral", "description",
})


class WorkflowError(ValueError):
    """Raised for invalid workflow artifacts."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"invalid JSON in {path}: {exc}") from exc
    except (OSError, UnicodeError) as exc:
        raise WorkflowError(f"cannot read JSON file {path}: {exc}") from exc


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# A symlink the agent left inside a trial's collected artifacts/ tree is a valid
# submission (MASTER_CHECKLIST_TBSCI.md #55: the verifier seal deletes only links whose
# resolved target escapes the artifact paths, so `/app/bin/fit -> ../model_runner.py`
# is graded as the agent left it). Step 3c evidence tools therefore keep such a link as
# a link: never followed, hashed from its link text, copied with that exact text. A
# symlink anywhere else in a round is still refused.
SYMLINK_RECORD_PREFIX = b"symlink\0"


def symlink_sha256(link_text: str) -> str:
    """Hex sha256 of a symlink record: the prefix plus the raw link text, never the target."""
    return hashlib.sha256(SYMLINK_RECORD_PREFIX + os.fsencode(link_text)).hexdigest()


def trial_artifact_symlink(root: Path, path: Path, trial_depth: int = 2) -> str | None:
    """Link text of ``path`` when it is a symlink inside a trial's ``artifacts/`` tree.

    ``root`` is the directory being walked and ``trial_depth`` the number of components
    from it to a trial directory: 2 for a round (``<job>/<trial>``), 1 for a job dir.
    Returns None for anything else (not a symlink, ``artifacts`` itself a link, a link
    under ``agent/``/``verifier/``/job files/the round top level), which the caller
    refuses.
    """
    if not path.is_symlink():
        return None
    parts = path.relative_to(root).parts
    if len(parts) < trial_depth + 2 or parts[trial_depth] != "artifacts":
        return None
    trial = root.joinpath(*parts[:trial_depth])
    if any(root.joinpath(*parts[:i]).is_symlink() for i in range(1, trial_depth + 2)):
        return None
    if not (trial / "config.json").is_file():
        return None
    return os.readlink(path)


def evidence_inventory(root: Path, refusal: str, trial_depth: int = 2,
                       links: dict[str, str] | None = None) -> dict[str, str]:
    """{relative path: hex sha256} of every regular file under ``root``.

    An in-artifacts symlink (``trial_artifact_symlink``) is recorded under its own path
    as ``symlink_sha256(link text)`` and, when ``links`` is given, its link text is
    stored there. Any other symlink raises ``WorkflowError(f"{refusal}: {path}")``. For
    a tree without symlinks the result is exactly the historical per-file inventory.
    """
    hashes = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            link = trial_artifact_symlink(root, path, trial_depth)
            if link is None:
                raise WorkflowError(f"{refusal}: {path}")
            relative = path.relative_to(root).as_posix()
            hashes[relative] = symlink_sha256(link)
            if links is not None:
                links[relative] = link
            continue
        if path.is_file():
            hashes[path.relative_to(root).as_posix()] = sha256_file(path)
    return hashes


def task_paths(task_dir: Path) -> list[Path]:
    """List behavioral source, pruning root-level packaging records from the digest.

    ``tasks/<task>/trajectories/`` and ``tasks/<task>/rubric.txt`` are omitted
    from the behavioral task digest and static source checks, then validated and
    bound separately by Step 4. Names nested under environment/ or tests/ remain
    behavioral task source and are checked normally.
    """
    if not task_dir.is_dir():
        raise WorkflowError(f"task directory not found: {task_dir}")
    paths: list[Path] = []

    def walk_error(exc: OSError) -> None:
        raise WorkflowError(f"cannot inspect task source: {exc}") from exc

    for directory, dirs, files in os.walk(task_dir, onerror=walk_error):
        parent = Path(directory)
        for name in [*dirs, *files]:
            path = parent / name
            if path.is_symlink():
                raise WorkflowError(f"symlinks are not allowed in task source: {path}")
            if parent == task_dir and name == "trajectories":
                if not path.is_dir():
                    raise WorkflowError("task-root trajectories must be an author-evidence directory")
                dirs.remove(name)
                continue
            if parent == task_dir and name == "rubric.txt":
                if not path.is_file():
                    raise WorkflowError("task-root rubric.txt must be a regular file")
                continue
            if not path.is_file() and not path.is_dir():
                raise WorkflowError(f"non-regular task source file: {path}")
            paths.append(path)
    return sorted(paths)


def task_files(task_dir: Path) -> list[Path]:
    return [path for path in task_paths(task_dir) if path.is_file()]


def functional_task_toml(task_dir: Path) -> bytes:
    """Canonical bytes for the parts of ``task.toml`` that can change a trial.

    Raw TOML bytes are not a usable identity here: a reordered key or an added
    comment changes them while meaning nothing, and parsing to a dict is not enough
    either, because Python preserves insertion order. So this sorts every key
    recursively and emits deterministic JSON. Descriptive [metadata] keys are dropped
    entirely -- see DESCRIPTIVE_METADATA_KEYS.
    """
    try:
        import tomllib
    except ModuleNotFoundError as exc:  # pragma: no cover - 3.10 only compiles here
        raise WorkflowError(
            "reading task.toml needs Python 3.11+; activate the workspace .venv"
        ) from exc
    path = task_dir / "task.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"missing task.toml: {path}") from exc
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise WorkflowError(f"invalid task.toml: {exc}") from exc
    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        data = dict(data)
        data["metadata"] = {k: v for k, v in metadata.items()
                            if k not in DESCRIPTIVE_METADATA_KEYS}

    def canonical(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: canonical(value[k]) for k in sorted(value)}
        if isinstance(value, (list, tuple)):
            return [canonical(v) for v in value]
        # 3600 and 3600.0 are the same setting; do not let the literal form move it.
        if isinstance(value, bool):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    return json.dumps(canonical(data), sort_keys=True, separators=(",", ":")).encode("utf-8")


def _fold_paths(task_dir: Path, paths: list[Path], prefix: bytes,
                overrides: dict[Path, bytes] | None = None) -> str:
    """Fold ``paths`` (already relative to a resolved ``task_dir``) into one digest.

    This is the canonical fold. ``task_digest`` is exactly this function applied to
    ``task_paths()`` under the historical prefix, so the full-task value is stable;
    the surface digests reuse the same body under their own domain-separating
    prefixes.
    """
    digest = hashlib.sha256()
    digest.update(prefix)
    for path in paths:
        relative = path.relative_to(task_dir).as_posix().encode("utf-8")
        digest.update(b"D" if path.is_dir() else b"F")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(stat.S_IMODE(path.stat().st_mode).to_bytes(2, "big"))
        if overrides and path in overrides:
            data = overrides[path]
        else:
            data = b"" if path.is_dir() else path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return f"sha256:{digest.hexdigest()}"


def task_digest(task_dir: Path) -> str:
    task_dir = task_dir.resolve()
    return _fold_paths(task_dir, task_paths(task_dir), TASK_DIGEST_PREFIX)


def surface_paths(task_dir: Path, roots: tuple[str, ...]) -> list[Path]:
    """Select the ``task_paths()`` entries whose first component is in ``roots``.

    The sorted order of ``task_paths()`` is preserved so the surface folds are
    deterministic. A root that is absent from the tree is an error rather than an
    empty selection: a task with no ``tests/`` must not quietly digest to the
    hash of nothing and then compare equal to another such task.
    """
    task_dir = task_dir.resolve()
    selected: list[Path] = []
    present: set[str] = set()
    for path in task_paths(task_dir):
        head = path.relative_to(task_dir).parts[0]
        present.add(head)
        if head in roots:
            selected.append(path)
    missing = [root for root in roots if root not in present]
    if missing:
        raise WorkflowError(
            f"{task_dir.name}: digest surface is incomplete; missing task-root "
            f"entries: {', '.join(missing)}"
        )
    return selected


def assert_digest_partition(task_dir: Path) -> None:
    """Fail when a task-root entry belongs to neither digest surface.

    The agent and grader surfaces must partition the digested tree. A stray entry
    (say ``tasks/<task>/helper.py``) would otherwise move the full task digest
    while being invisible to both halves of the split.
    """
    task_dir = task_dir.resolve()
    covered = set(AGENT_SURFACE) | set(GRADER_SURFACE) | set(DESCRIPTIVE_SURFACE)
    stray = sorted(
        {
            path.relative_to(task_dir).parts[0]
            for path in task_paths(task_dir)
            if path.relative_to(task_dir).parts[0] not in covered
        }
    )
    if stray:
        raise WorkflowError(
            f"{task_dir.name}: task-root entries belong to neither the agent nor the "
            f"grader surface: {', '.join(stray)}; every digested entry must sit under "
            f"{', '.join(sorted(covered))}"
        )


def agent_digest(task_dir: Path) -> str:
    task_dir = task_dir.resolve()
    manifest = task_dir / "task.toml"
    overrides = {manifest: functional_task_toml(task_dir)} if manifest.is_file() else None
    return _fold_paths(task_dir, surface_paths(task_dir, AGENT_SURFACE),
                       AGENT_DIGEST_PREFIX, overrides)

def legacy_agent_digest(task_dir: Path) -> str:
    """The v1 agent-surface fold: task.toml hashed whole, descriptive fields included.

    Kept only so a seal written before AGENT_DIGEST_VERSION == "v2" can be checked
    against the algorithm that produced it. Never write a new record with this.
    """
    return _fold_paths(task_dir, surface_paths(task_dir, AGENT_SURFACE),
                       LEGACY_AGENT_DIGEST_PREFIX)



def grader_digest(task_dir: Path) -> str:
    task_dir = task_dir.resolve()
    return _fold_paths(task_dir, surface_paths(task_dir, GRADER_SURFACE), GRADER_DIGEST_PREFIX)


def split_digests(task_dir: Path) -> dict[str, str]:
    """Return the full digest alongside its agent and grader halves.

    Prefer this over the three functions individually: it proves the partition
    first, so the two halves are known to account for everything the full digest
    covers.
    """
    task_dir = task_dir.resolve()
    assert_digest_partition(task_dir)
    return {
        "full": task_digest(task_dir),
        "agent": agent_digest(task_dir),
        "grader": grader_digest(task_dir),
    }


def seed_parity(task_dir: Path) -> dict[str, str]:
    """Hash every file under ``tests/seed/`` and require parity with ``environment/``.

    The two trees are deliberately not required to match as sets: ``tests/seed/``
    may carry generator scripts the image never ships, and ``environment/`` carries
    build inputs (``Dockerfile``, ``.dockerignore``) that no seed needs. Only a
    relative path present in *both* must be byte-identical, because those files are
    the shared ground truth the grader reseeds from.

    Returns ``{}`` when the task has no ``tests/seed/``.
    """
    task_dir = task_dir.resolve()
    seed_root = task_dir / "tests" / "seed"
    if not seed_root.is_dir():
        return {}
    environment_root = task_dir / "environment"
    parity: dict[str, str] = {}
    divergent: list[str] = []
    for path in sorted(seed_root.rglob("*")):
        if path.is_symlink():
            raise WorkflowError(f"symlinks are not allowed in task source: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(seed_root).as_posix()
        seed_hash = sha256_file(path)
        parity[relative] = f"sha256:{seed_hash}"
        counterpart = environment_root / relative
        if counterpart.is_file() and not counterpart.is_symlink():
            if sha256_file(counterpart) != seed_hash:
                divergent.append(relative)
    if divergent:
        raise WorkflowError(
            f"{task_dir.name}: tests/seed and environment/ disagree byte-for-byte on: "
            f"{', '.join(divergent)}"
        )
    return parity


def load_test_manifest(task_dir: Path) -> dict[str, Any]:
    path = task_dir / "tests" / "test_manifest.json"
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise WorkflowError(f"{path} must contain a JSON object")
    tests = payload.get("tests")
    if payload.get("schema_version") != "1.0" or payload.get("selector_env") != "TBENCH_TEST_ID":
        raise WorkflowError(f"{path}: require schema_version '1.0' and selector_env TBENCH_TEST_ID")
    if not isinstance(tests, list) or not tests:
        raise WorkflowError(f"{path}: at least one independently meaningful test is required")
    ids: set[str] = set()
    cases_seen: set[str] = set()
    for index, entry in enumerate(tests):
        if not isinstance(entry, dict):
            raise WorkflowError(f"{path}: tests[{index}] must be an object")
        test_id = entry.get("id")
        if not isinstance(test_id, str) or not TEST_ID_RE.fullmatch(test_id) or test_id == "all" or test_id in ids:
            raise WorkflowError(f"{path}: invalid or duplicate test id: {test_id!r}")
        ids.add(test_id)
        if entry.get("independent") is not True:
            raise WorkflowError(f"{path}: {test_id}: independent must be true")
        for field in ("description", "requirement"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise WorkflowError(f"{path}: {test_id}: {field} must be nonempty text")
        cases = entry.get("cases")
        if (not isinstance(cases, list) or len(cases) != 1
                or not isinstance(cases[0], str) or not cases[0].strip()):
            raise WorkflowError(f"{path}: {test_id}: cases must contain exactly one CTRF test name")
        if cases[0] in cases_seen:
            raise WorkflowError(f"{path}: CTRF case declared more than once: {cases[0]}")
        cases_seen.add(cases[0])
    return payload


def manifest_ids(task_dir: Path) -> list[str]:
    payload = load_test_manifest(task_dir)
    result: list[str] = []
    for index, item in enumerate(payload["tests"]):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise WorkflowError(f"test manifest entry {index} has no string id")
        result.append(item["id"])
    return result


def portable_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def resolve_recorded_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def finite_number(value: Any) -> bool:
    return type(value) is int or (type(value) is float and math.isfinite(value))


# Master #58(c): a subset selector must not write task reward 1. test.sh that gates
# the 1-write on TBENCH_TEST_ID=all leaves every per-test oracle row at reward 0
# while the selected CTRF cases still have to pass.
_FULL_SUITE_REWARD = re.compile(
    r"""\[\s*"?\$\{TBENCH_TEST_ID:?-all\}"?\s*=\s*"all"\s*\]"""
    r"""|TEST_ID="\$\{TBENCH_TEST_ID:?-all\}"[\s\S]{0,4000}\[\s*"\$TEST_ID"\s*=\s*"all"\s*\]"""
)


def task_reward_only_on_full_suite(task_dir: Path) -> bool:
    path = task_dir / "tests" / "test.sh"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return _FULL_SUITE_REWARD.search(text) is not None


def per_test_expected_reward(task_dir: Path, agent: str) -> float:
    if agent != "oracle":
        return 0.0
    if task_reward_only_on_full_suite(task_dir):
        return 0.0
    return 1.0


def require_outside_task(task_dir: Path, path: Path) -> None:
    if path.resolve().is_relative_to(task_dir.resolve()):
        raise WorkflowError(f"authoring output must be outside the task directory: {path}")


def validate_gate_coverage(
    report: dict[str, Any],
    *,
    expected_ids: list[str],
    required_agents: tuple[str, ...],
    minimum_repeats: int,
    expected_cases_by_id: dict[str, list[str]] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not expected_ids:
        errors.append("gate coverage requires a nonempty test manifest")
    if report.get("schema_version") != "1.1":
        errors.append("gate report schema_version must be '1.1'; rerun the per-test gate")
    if report.get("selector_env") != "TBENCH_TEST_ID":
        errors.append("gate selector must be TBENCH_TEST_ID")
    if report.get("status") != "PASS":
        errors.append(f"gate report status is {report.get('status')!r}, expected 'PASS'")
    records = report.get("records")
    if not isinstance(records, list):
        return [*errors, "gate report records must be a list"]

    expected = set(expected_ids)
    tuples_seen: set[tuple[str, str, int]] = set()
    results_seen: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"gate row {index} must be an object")
            continue
        test_id, agent, repeat = (record.get(key) for key in ("test_id", "agent", "repeat"))
        if not isinstance(test_id, str) or test_id not in expected:
            errors.append(f"gate row {index}: unknown test id {test_id!r}")
        if not isinstance(agent, str) or agent not in required_agents:
            errors.append(f"gate row {index}: unexpected agent {agent!r}")
        if type(repeat) is not int or repeat < 1:
            errors.append(f"gate row {index}: repeat must be a positive integer")
        elif isinstance(test_id, str) and isinstance(agent, str):
            key = (test_id, agent, repeat)
            if key in tuples_seen:
                errors.append(f"duplicate gate row: {key}")
            tuples_seen.add(key)
        result_path = record.get("result_path")
        if not isinstance(result_path, str) or not result_path:
            errors.append(f"gate row {index}: missing raw result path")
        else:
            resolved = str(resolve_recorded_path(result_path).resolve())
            if resolved in results_seen:
                errors.append(f"gate row {index}: raw result reused across trials")
            results_seen.add(resolved)

    for test_id in expected_ids:
        for agent in required_agents:
            matching = [
                record
                for record in records
                if isinstance(record, dict)
                and record.get("test_id") == test_id
                and record.get("agent") == agent
            ]
            repeats = {record.get("repeat") for record in matching if type(record.get("repeat")) is int}
            if len(matching) < minimum_repeats or len(repeats) < minimum_repeats:
                errors.append(
                    f"{test_id}/{agent}: expected at least {minimum_repeats} distinct repeat(s), "
                    f"found {len(repeats)}"
                )
                continue
            recorded_expected = matching[0].get("expected_reward") if matching else None
            if finite_number(recorded_expected) and float(recorded_expected) in (0.0, 1.0):
                expected_reward = float(recorded_expected)
            else:
                expected_reward = 1.0 if agent == "oracle" else 0.0
            for record in matching:
                if record.get("status") != "PASS":
                    errors.append(
                        f"{test_id}/{agent}/repeat-{record.get('repeat')}: status is not PASS"
                    )
                reward = record.get("reward")
                if not finite_number(reward) or reward != expected_reward:
                    errors.append(
                        f"{test_id}/{agent}/repeat-{record.get('repeat')}: "
                        f"reward {reward!r}, expected {expected_reward}"
                    )
                if type(record.get("errors")) is not int or record["errors"] != 0 or record.get("exception"):
                    errors.append(
                        f"{test_id}/{agent}/repeat-{record.get('repeat')}: verifier/Harbor exception present"
                    )
                if expected_cases_by_id is not None:
                    expected_cases = sorted(expected_cases_by_id.get(test_id, []))
                    recorded_expected = record.get("expected_cases")
                    executed_cases = record.get("executed_cases")
                    if recorded_expected != expected_cases or executed_cases != expected_cases:
                        errors.append(
                            f"{test_id}/{agent}/repeat-{record.get('repeat')}: "
                            f"CTRF cases {executed_cases!r}, expected {expected_cases!r}"
                        )
                    expected_status = "passed" if agent == "oracle" else "failed"
                    if record.get("case_statuses") != {case: expected_status for case in expected_cases}:
                        errors.append(f"{test_id}/{agent}: CTRF status must be {expected_status}; skips and errors do not qualify")
                if record.get("exit_code") != 0:
                    errors.append(f"{test_id}/{agent}: Harbor did not exit successfully")
    return errors


# --------------------------------------------------------------------------- master checklist

MASTER_CHECKLIST_PATH = REPO_ROOT / "MASTER_CHECKLIST_TBSCI.md"


def bundle_sha_lines(files: list[tuple[str, bytes | Path]]) -> str:
    """The SUMMARY.txt ``sha=`` value over ``(relative_path, content)`` pairs.

    MASTER_CHECKLIST_TBSCI.md #80 has the reviewer recompute the sha "from inside the
    inner task-slug directory using relative paths". This is byte-for-byte what

        find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum

    prints there: one ``<hex>  ./<path>\\n`` line per file, ordered by the bytes of
    ``./<path>``, hashed as one stream. Content may be bytes or a path to read.
    """
    rows = []
    for relative, content in files:
        name = "./" + relative.lstrip("/")
        if "\n" in name or "\\" in name:
            raise WorkflowError(f"file name cannot be hashed portably: {relative!r}")
        data = content.read_bytes() if isinstance(content, Path) else content
        rows.append((name.encode("utf-8"), hashlib.sha256(data).hexdigest()))
    stream = b"".join(f"{digest}  ".encode("ascii") + name + b"\n" for name, digest in sorted(rows))
    return hashlib.sha256(stream).hexdigest()


def bundle_sha(inner_task_dir: Path) -> str:
    """Bundle sha of a task folder as shipped: every regular file under it."""
    root = inner_task_dir.resolve()
    files: list[tuple[str, bytes | Path]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise WorkflowError(f"symlinks are not allowed in a shipped task: {path}")
        if path.is_file():
            files.append((path.relative_to(root).as_posix(), path))
    return bundle_sha_lines(files)


# Pytest's own markers for a test that never reached its assertion. With `--tb=no -rA`
# a setup/collection problem prints `ERROR <case>` in the short summary and an
# `N error(s)` count in the final line; an import crash prints its own banner.
_INFRA_ERROR_PATTERNS = (
    ("ERROR row in the pytest summary", re.compile(r"(?m)^ERROR\b")),
    ("collection error", re.compile(r"errors? during collection|ImportError while importing", re.I)),
    ("pytest internal error", re.compile(r"(?m)^INTERNALERROR\b")),
    ("error count in the pytest result line", re.compile(r"(?m)^=+ .*\b\d+ errors?\b.*=+\s*$")),
    # the same line under `-q`, which drops the `=` banner
    ("error count in the pytest result line",
     re.compile(r"(?m)^(?:\d+ [a-z]+, )*\d+ errors?(?:, \d+ [a-z]+)* in [\d.]+s\b")),
    ("no tests ran", re.compile(r"no tests ran", re.I)),
)


def nop_infrastructure_errors(stdout_text: str) -> list[str]:
    """Why a NOP failure is not genuine (MASTER_CHECKLIST_TBSCI.md #74), or [] if it is.

    NOP evidence counts only when the shipped code ran and produced the wrong answer.
    A setup error, collection error, import crash or a session-scoped autouse fixture
    asserting before the test body is infrastructure, not a failed requirement.
    """
    return [label for label, pattern in _INFRA_ERROR_PATTERNS if pattern.search(stdout_text)]
