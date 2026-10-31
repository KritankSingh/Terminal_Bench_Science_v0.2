#!/usr/bin/env python3
"""Run dependency-free structural and policy checks on one Terminal-Bench Science task.

MASTER_CHECKLIST_TBSCI.md is the source of truth; findings cite its checks as
``Master #N``. Only the mechanical checks live here -- the rest are answered, with
evidence, in ``authoring/<task>/master-checklist.md`` (``scripts/master_checklist.py``).

This is the strict structural gate used by Step 2b sealing (`evidence.py seal`)
and Steps 3b/3c/4 (Step 3a is optional diagnostics). It combines:

- the Terminal-Bench Science hardening rules from `hardening_check.py` (task.toml schema,
  digest-pinned Dockerfiles, separate verifier, reserved paths, latency signals,
  runtime fetches, test-variable defaults);
- the per-test contract from `docs/TESTING_POLICY.md` (tests/test_manifest.json,
  TBENCH_TEST_ID selector, CTRF case mapping, `--tb=no` with failure messages
  recorded in CTRF and echoed to stdout, no runtime installs);
- package hygiene (banned files, build-artifact leaks, .dockerignore drift, the
  task-root allowlist of upstream check-task-structure.sh);
- the TB-Science format (Master #61-#65, #103-#106): domain/field/subfield,
  no README.md in the task (Master #103), the instruction suffix
  (check-instruction-suffix.sh), declared network policy on both phases
  (check-allow-internet.sh), resource fields, slug shape (check-task-slug.sh);
- digest integrity (`digest_partition`, every digested task-root entry falls in the
  agent or grader surface; `seed_parity`, tests/seed and environment/ agree on
  every path they both carry);
- the negative-control plan (`controls_plan`, WARN): every `test_*` token named
  after the `## Negative controls` heading of authoring/<slug>/controls.md must be
  a CTRF case function from tests/test_manifest.json, and that heading must exist.

Findings are `FAIL` or `WARN`; `--strict` treats warnings as failures.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

from common import (
    REPO_ROOT,
    SLUG_RE,
    TEST_ID_RE,
    WorkflowError,
    assert_digest_partition,
    finite_number,
    load_test_manifest,
    seed_parity,
    task_paths,
)
from hardening_check import Check as HardeningCheck


REQUIRED_FILES = (
    "instruction.md",
    "task.toml",
    "environment/Dockerfile",
    "solution/solve.sh",
    "tests/Dockerfile",
    "tests/test.sh",
    "tests/test_manifest.json",
)
REQUIRED_DIRS = ("environment", "solution", "tests")
BANNED_PARTS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
    "trajectories",
    "jobs",
    "artifacts",
    ".cursor",
    ".claude",
    ".aider",
    "__MACOSX",
}
BANNED_FILENAMES = {
    ".DS_Store",
    "rubrics.txt",
    "AGENTS.md",
    "CLAUDE.md",
    "skills.md",
    "SOURCE.txt",
    ".step2b-checksum",
}
# Master #61: present, substantive and accurate. The task write-ups (what makes it hard,
# the reference strategy, how verification was calibrated) are workspace records under
# authoring/<task>/ (Master #103) -- never task.toml keys, never a shipped README.md.
REQUIRED_TEXT_METADATA = ("relevant_experience",)
WRITEUP_KEYS = ("difficulty_explanation", "solution_explanation", "verification_explanation")
OPTIONAL_AUTHOR_METADATA = ("author_name", "author_email", "author_organization")
# Master #104 (upstream check-instruction-suffix.sh).
INSTRUCTION_SUFFIX = ("You have {n} seconds to complete this task. Do not cheat by using online "
                      "solutions or hints specific to this task.")
# Upstream check-task-structure.sh, adapted: the task root holds only the Harbor entries --
# no README.md (Master #103); author-side material lives in the workspace's authoring/<task>/;
# rubric.txt and trajectories/ are workspace packaging inputs excluded from the digest.
TASK_ROOT_ALLOWED = {"instruction.md", "task.toml", "environment", "solution", "tests",
                     "rubric.txt", "trajectories", ".gitignore", ".gitattributes"}
# Master #61: kebab-case, a name not a sentence; 2–4 tokens is typical. Length is
# not itself a finding (the auditor may LEAD past 4 tokens).
# Master #62/#65: stale-schema residue and anything that grades difficulty inside the task.
BANNED_TOP_LEVEL_KEYS = {
    "version": "a top-level version key is stale-schema residue (Master #65)",
    "task": "[task] table duplicates the top-level name; TB-Science uses top-level name/artifacts (Master #65)",
    "reference_pattern": "[reference_pattern] is generator bookkeeping that leaks how the task was produced (Master #65)",
    "steps": "milestone/step tasks are removed in Terminal-Bench Science (Master #65)",
}
TIER_TEXT_RE = re.compile(
    r"\b[0-5]\s*/\s*5\b|\bpass[- ]?rate\b|\bpass@\d|\bk\s*=\s*5\b|\btoo easy\b|"
    r"\b(?:Frontier|Advanced|Core|Base)\s+(?:tier|difficulty)\b|\bdifficulty\s*(?:tier|level|rating)\b",
    re.I,
)
HOST_PATH_RE = re.compile(r"(?:/home/[A-Za-z0-9._-]+/|/Users/|/private/tmp/|/mnt/[a-z]/|[A-Za-z]:\\{1,2}[A-Za-z])")
GUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
# A canary is a training-data marker, not the word "canary" (a canary-deployment task is
# legitimate): the benchmark banner, a canary GUID/string label, or a canary assignment.
CANARY_RE = re.compile(
    r"BENCHMARK DATA SHOULD NEVER APPEAR|canary[\s_-]*(?:GUID|string|token)|terminal-bench-canary|"
    r"\bcanary\s*[:=]?\s*['\"]?[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-",
    re.I,
)
PLACEHOLDER_RE = re.compile(
    r"<(?:task-slug|task-name|official-domain|primary-language|author-name|author-email|domain-anchor|"
    r"technology|one-sentence description of evaluated behavior|test-id)>"
)
NETWORK_INSTALL_RE = re.compile(
    r"(?im)^\s*(?!#).*\b(?:"
    r"apt(?:-get)?\s+(?:update|install)|"
    r"pip(?:3)?\s+install|python(?:3)?\s+-m\s+pip\s+install|"
    r"npm\s+install|pnpm\s+(?:add|install)|yarn\s+(?:add|install)|"
    r"cargo\s+(?:install|fetch)|go\s+get|uv\s+(?:add|sync|tool\s+install)|uvx|"
    r"git\s+clone"
    r")"
)
# Master #5: pipeline/tooling vocabulary that breaks the task's fictional framing.
AGENT_FACING_BANNED = (
    re.compile(r"(?:/tests(?:/|\b)|/logs/verifier(?:/|\b)|/opt/verifier\b|test_manifest\.json|test_outputs(?:\.py)?\b)", re.IGNORECASE),
    re.compile(r"solution/solve\.sh|reward\.txt|ctrf", re.IGNORECASE),
    re.compile(r"\b(?:the\s+)?grader\b|\btest[- ]suite\b|\bverifiers?\b|\bpytest\b", re.IGNORECASE),
)
TAXONOMY_PATH = REPO_ROOT / "docs" / "TASK_TAXONOMY.md"


@dataclass(frozen=True)
class Issue:
    level: str
    check: str
    detail: str


def add(issues: list[Issue], level: str, check: str, detail: str) -> None:
    issues.append(Issue(level=level, check=check, detail=detail))


def read_text(path: Path, issues: list[Issue], check: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        add(issues, "FAIL", check, f"cannot read UTF-8 text {path}: {exc}")
        return ""


def load_taxonomy() -> dict[str, set[str]]:
    """Parse docs/TASK_TAXONOMY.md into {domain: {field, ...}} (Master #61, #98).

    Domains are the ``### `domain` `` headings; fields are the backticked first cell of
    each table row below a domain heading."""
    taxonomy: dict[str, set[str]] = {}
    if not TAXONOMY_PATH.is_file():
        return taxonomy
    current: str | None = None
    for line in TAXONOMY_PATH.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^###\s+`([a-z0-9-]+)`\s*$", line)
        if heading:
            current = heading.group(1)
            taxonomy.setdefault(current, set())
            continue
        if line.startswith("## "):
            current = None
            continue
        if current and line.startswith("|"):
            first = line.strip().strip("|").split("|")[0].strip()
            cell = re.fullmatch(r"`([a-z0-9-]+)`", first)
            if cell:
                taxonomy[current].add(cell.group(1))
    return taxonomy


def check_layout(task_dir: Path, issues: list[Issue]) -> None:
    if not task_dir.is_dir():
        add(issues, "FAIL", "layout", f"task directory not found: {task_dir}")
        return
    if not SLUG_RE.fullmatch(task_dir.name):
        add(issues, "FAIL", "layout", f"task directory name is not a kebab-case slug: {task_dir.name}")
    for entry in sorted(task_dir.iterdir()) if task_dir.is_dir() else []:
        if entry.name == "README.md":
            continue  # reported by check_readme
        if entry.name not in TASK_ROOT_ALLOWED and not entry.name.startswith(("LICENSE", "NOTICE", "COPYRIGHT")):
            add(issues, "FAIL", "task_structure", f"unexpected task-root entry {entry.name!r}: only instruction.md, "
                                                  "task.toml, environment/, solution/ and tests/ belong "
                                                  "there; author-side material (generators, provenance, hints) goes "
                                                  "in authoring/<task>/ (upstream check-task-structure.sh, Master #96)")
    for relative in REQUIRED_DIRS:
        if not (task_dir / relative).is_dir():
            add(issues, "FAIL", "layout", f"missing directory: {relative}/")
    for relative in REQUIRED_FILES:
        if not (task_dir / relative).is_file():
            add(issues, "FAIL", "layout", f"missing required file: {relative}")
    try:
        paths = task_paths(task_dir)
    except WorkflowError as exc:
        add(issues, "FAIL", "package_hygiene", str(exc))
        return
    for path in paths:
        relative = path.relative_to(task_dir)
        if any(part in BANNED_PARTS for part in relative.parts):
            add(issues, "FAIL", "package_hygiene", f"banned path: {relative}")
        if path.is_file() and path.name.lower() in {name.lower() for name in BANNED_FILENAMES}:
            add(issues, "FAIL", "package_hygiene", f"banned filename: {relative}")
        if path.name.startswith("._") or path.suffix == ".pyc":
            add(issues, "FAIL", "package_hygiene", f"banned filename: {relative} (Master #96)")
        if relative.parts and relative.parts[0] == "environment":
            if "CMakeFiles" in relative.parts or path.name in {"CMakeCache.txt", "cmake_install.cmake"}:
                add(issues, "FAIL", "package_hygiene", f"generated build artifact must not ship: {relative}")
            if path.is_file() and path.suffix in {".o", ".a", ".so"} and "src" not in relative.parts:
                add(issues, "FAIL", "package_hygiene", f"compiled object must not ship: {relative}")
    for dockerignore in (task_dir / "environment").rglob(".dockerignore"):
        if not dockerignore.is_file():
            continue
        base = dockerignore.parent
        try:
            lines = dockerignore.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            add(issues, "FAIL", "package_hygiene", f"cannot read {dockerignore.relative_to(task_dir)}: {exc}")
            continue
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            if any(ch in line for ch in "*?[]"):
                continue
            target = (base / line.rstrip("/")).resolve()
            try:
                target.relative_to(task_dir.resolve())
            except ValueError:
                continue
            if target.exists():
                add(
                    issues,
                    "FAIL",
                    "package_hygiene",
                    f"{dockerignore.relative_to(task_dir)} excludes {line!r} but it is present in task source",
                )


def check_toml(task_dir: Path, issues: list[Issue]) -> dict[str, Any]:
    """Terminal-Bench Science task.toml schema (docs/TASK_COMPONENTS.md); hardening_check covers the rest."""
    path = task_dir / "task.toml"
    if tomllib is None:
        add(issues, "FAIL", "task_toml", "Python 3.11+ is required to validate TOML; activate the workspace .venv")
        return {}
    if not path.is_file():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        add(issues, "FAIL", "task_toml", f"invalid task.toml: {exc}")
        return {}
    name = data.get("name")
    if name != task_dir.name:
        add(issues, "FAIL", "task_toml", f"top-level name must equal the directory slug {task_dir.name!r}; got {name!r}")
    for key, reason in BANNED_TOP_LEVEL_KEYS.items():
        if key in data:
            add(issues, "FAIL", "task_toml", reason)
    raw = path.read_text(encoding="utf-8")
    host = HOST_PATH_RE.search(raw)
    if host:
        add(issues, "FAIL", "task_toml", f"real local machine path in task.toml: {host.group(0)!r} (Master #65)")
    if re.search(r"(?m)^\s*\[\s*(?:task\.authors|\[\s*task\.authors)", raw):
        add(issues, "FAIL", "task_toml", "[[task.authors]] duplicates top-level authorship (Master #65)")
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        add(issues, "FAIL", "task_toml", "missing [metadata] table")
        metadata = {}
    for key in OPTIONAL_AUTHOR_METADATA:
        if key in metadata and (not isinstance(metadata[key], (str, list)) or not metadata[key]
                                or (isinstance(metadata[key], str) and not metadata[key].strip())):
            add(issues, "FAIL", "task_toml", f"metadata.{key} is optional, but when present it must be non-empty "
                                             f"(Master #61); got {metadata.get(key)!r}")
    for key in WRITEUP_KEYS:
        if key in metadata:
            add(issues, "FAIL", "task_toml", f"metadata.{key} is not a task.toml field here; the write-ups are "
                                             "workspace records under authoring/<task>/ and never ship (Master #61, #103)")
    if "difficulty" in metadata or "difficulty" in data:
        add(issues, "FAIL", "task_toml", "task.toml must carry no difficulty field; the measured k=5 rate lives only in "
                                         "workspace reports (Master #62)")
    for key in list(metadata) + list(data):
        lowered = str(key).lower()
        if lowered == "codebase_size" or lowered.endswith("_min") or "milestone" in lowered:
            add(issues, "FAIL", "task_toml", f"stale-schema field {key!r} (Master #65)")
    taxonomy = load_taxonomy()
    domain = metadata.get("domain")
    field = metadata.get("field")
    subfield = metadata.get("subfield")
    if not taxonomy:
        add(issues, "FAIL", "taxonomy", f"cannot parse the domain/field table in {TAXONOMY_PATH}")
    elif domain not in taxonomy:
        add(issues, "FAIL", "taxonomy", f"metadata.domain must be one of {sorted(taxonomy)}; got {domain!r} (Master #61)")
    elif field not in taxonomy[domain]:
        add(issues, "FAIL", "taxonomy", f"metadata.field {field!r} is not a field of {domain!r}; one of "
                                        f"{sorted(taxonomy[domain])} (docs/TASK_TAXONOMY.md, Master #61)")
    if not isinstance(subfield, str) or not subfield.strip():
        add(issues, "FAIL", "taxonomy", "metadata.subfield must be a non-empty string (free text, kebab-case "
                                        "recommended; Master #61)")
    for key in ("category", "subcategory", "languages"):
        if key in metadata:
            add(issues, "FAIL", "taxonomy", f"metadata.{key} is a retired TB4 key; TB-Science classifies by "
                                            "domain / field / subfield (Master #61)")
    hours = metadata.get("expert_time_estimate_hours")
    if isinstance(hours, bool) or not finite_number(hours) or hours <= 0:
        add(issues, "FAIL", "task_toml", "metadata.expert_time_estimate_hours must be a positive number (Master #61)")
    for key in REQUIRED_TEXT_METADATA:
        if not isinstance(metadata.get(key), str) or len(metadata[key].strip()) < 40:
            add(issues, "FAIL", "task_toml", f"metadata.{key} must be substantive text, not a placeholder (Master #61)")
    for key, value in metadata.items():
        if isinstance(value, str) and TIER_TEXT_RE.search(value):
            add(issues, "FAIL", "task_toml", f"metadata.{key} carries a tier label, rate or pass-count "
                                             f"{TIER_TEXT_RE.search(value).group(0)!r}; write plain language (Master #62)")
    if "number_of_milestones" in data or "number_of_milestones" in metadata:
        add(issues, "FAIL", "task_structure", "milestone/step tasks are removed in Terminal-Bench Science")
    verifier = data.get("verifier")
    if not isinstance(verifier, dict):
        add(issues, "FAIL", "task_toml", "missing [verifier] table")
        verifier = {}
    agent = data.get("agent")
    if not isinstance(agent, dict):
        add(issues, "FAIL", "task_toml", "missing [agent] table")
        agent = {}
    # Timeouts (28800 everywhere, Master #63) and the declared network policy on both
    # phases (Master #64) are enforced by hardening_check.
    if "network_mode" in agent:
        add(issues, "FAIL", "task_toml", "[agent].network_mode is not a Harbor field; the agent phase is "
                                         "[environment].network_mode and the verifier phase "
                                         "[verifier.environment].network_mode (Master #64)")
    for section in ("verifier", "environment", "solution", "agent"):
        value = data.get(section)
        if isinstance(value, dict) and "env" in value:
            add(issues, "WARN", "task_toml", f"[{section}.env] is present; verify every value has a default in tests/test.sh")
    environment = data.get("environment")
    if not isinstance(environment, dict):
        add(issues, "FAIL", "task_toml", "missing [environment] table")
        environment = {}
    for key in ("cpus", "memory_mb", "storage_mb"):
        if type(environment.get(key)) is not int or environment[key] <= 0:
            add(issues, "FAIL", "task_toml", f"[environment].{key} must be a positive integer (Master #65)")
    if environment.get("gpus") != 0 or isinstance(environment.get("gpus"), bool):
        add(issues, "FAIL", "task_toml", f"[environment].gpus must be declared as 0 -- tasks run on local Docker "
                                         f"with no GPU (Master #65); got {environment.get('gpus')!r}")
    if "gpu_types" in environment:
        add(issues, "FAIL", "task_toml", "[environment].gpu_types is not used: tasks require no GPU (Master #65)")
    return data


# Master #103: the write-ups are a workspace record with these exact headings.
WRITEUP_SECTIONS = ("Difficulty", "Reference solution", "Verification")


def check_readme(task_dir: Path, issues: list[Issue]) -> None:
    """Master #103: the task carries no README.md. The write-ups (what makes the task hard,
    the reference strategy, how verification and every tolerance were calibrated -- #95,
    #99-#102) are the workspace record authoring/<task>/write-ups.md, which never ships."""
    if (task_dir / "README.md").exists():
        add(issues, "FAIL", "readme", "README.md does not belong in the task: the write-ups are the workspace record "
                                      "authoring/<task>/write-ups.md, and only instruction.md, task.toml, "
                                      "environment/, solution/ and tests/ ship in the task folder (Master #103)")
    path = REPO_ROOT / "authoring" / task_dir.name / "write-ups.md"
    if not path.is_file():
        add(issues, "FAIL", "writeups", f"missing workspace write-ups {path.relative_to(REPO_ROOT)} with "
                                        "'## Difficulty', '## Reference solution' and '## Verification' (Master #103)")
        return
    text = read_text(path, issues, "writeups")
    body = re.sub(r"(?s)<!--.*?-->", "", text)
    for title in WRITEUP_SECTIONS:
        match = re.search(rf"(?m)^##[ \t]+{re.escape(title)}[ \t]*$", body)
        if not match:
            add(issues, "FAIL", "writeups", f"write-ups.md has no '## {title}' section (Master #103)")
            continue
        following = re.search(r"(?m)^#{1,2}[ \t]+\S", body[match.end():])
        section = body[match.end(): match.end() + following.start()] if following else body[match.end():]
        if len(section.strip()) < 40:
            add(issues, "FAIL", "writeups", f"write-ups.md '## {title}' is empty or a placeholder (Master #103)")
    if PLACEHOLDER_RE.search(text) or "REPLACE" in text:
        add(issues, "FAIL", "placeholders", "write-ups.md still contains template placeholders")
    tier = TIER_TEXT_RE.search(body)
    if tier:
        add(issues, "FAIL", "writeups", f"write-ups.md carries a tier label, rate or pass-count {tier.group(0)!r}; "
                                        "the write-ups are plain language (Master #62, #103)")


def check_instruction(task_dir: Path, issues: list[Issue], task_toml: dict[str, Any] | None = None) -> None:
    path = task_dir / "instruction.md"
    if not path.is_file():
        return
    text = read_text(path, issues, "instruction")
    agent = (task_toml or {}).get("agent") if isinstance(task_toml, dict) else None
    timeout = agent.get("timeout_sec") if isinstance(agent, dict) else None
    if finite_number(timeout) and not isinstance(timeout, bool) and float(timeout).is_integer() and timeout > 0:
        suffix = INSTRUCTION_SUFFIX.format(n=int(timeout))
        if not text.endswith("\n\n" + suffix + "\n") or text.endswith("\n\n\n" + suffix + "\n"):
            add(issues, "FAIL", "instruction_suffix",
                f"instruction.md must end with a blank line, then exactly {suffix!r} and one newline -- N is "
                "[agent].timeout_sec (upstream check-instruction-suffix.sh, Master #104)")
    else:
        add(issues, "FAIL", "instruction_suffix", "cannot check the instruction suffix: [agent].timeout_sec is not a "
                                                  "positive whole number (Master #63, #104)")
    if len(text.strip()) < 100:
        add(issues, "FAIL", "instruction", "instruction.md is too short to define a complete contract")
    if PLACEHOLDER_RE.search(text) or "Replace this text" in text:
        add(issues, "FAIL", "placeholders", "instruction.md still contains template placeholders")
    for pattern in AGENT_FACING_BANNED:
        match = pattern.search(text)
        if match:
            add(issues, "FAIL", "instruction_leak", f"agent-facing instruction contains pipeline term {match.group(0)!r}; "
                                                    "it breaks the task's framing (Master #5)")
    for pattern in (CANARY_RE, GUID_RE):
        match = pattern.search(text)
        if match:
            add(issues, "FAIL", "canary", f"instruction.md contains a canary/GUID-shaped string {match.group(0)!r} (Master #11)")
    if HOST_PATH_RE.search(text):
        add(issues, "FAIL", "instruction", "instruction.md names a real local machine path")


def check_canaries(task_dir: Path, issues: list[Issue]) -> None:
    """Master #11/#88/#97: no canary string anywhere in the task source."""
    try:
        paths = task_paths(task_dir)
    except WorkflowError:
        return  # reported by check_layout
    for path in paths:
        if not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8192]:
            continue
        text = data.decode("utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
            if CANARY_RE.search(line):
                add(issues, "FAIL", "canary", f"{path.relative_to(task_dir)}:{number}: canary marker must not ship (Master #11, #97)")
                break


def check_verifier_image(task_dir: Path, task_toml: dict[str, Any], issues: list[Issue]) -> None:
    """Separate-verifier rules: artifacts declared, parents pre-created, tests baked."""
    dockerfile = task_dir / "tests" / "Dockerfile"
    if not dockerfile.is_file():
        return
    text = read_text(dockerfile, issues, "verifier_image")
    if NETWORK_INSTALL_RE.search(text) and "--require-hashes" not in text and "==" not in text:
        add(issues, "WARN", "verifier_image", "tests/Dockerfile installs packages without visible pins; pin versions or use --require-hashes")
    artifacts = task_toml.get("artifacts") if isinstance(task_toml, dict) else None
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if not isinstance(artifact, str):
                continue
            parent = artifact.rstrip("/").rsplit("/", 1)[0] or "/"
            if parent != "/" and parent not in text and "mkdir -p /app" not in text:
                add(issues, "WARN", "verifier_image", f"parent directory {parent} for artifact {artifact} is not visibly pre-created in tests/Dockerfile")


def check_scripts(task_dir: Path, task_toml: dict[str, Any], issues: list[Issue]) -> str:
    test_path = task_dir / "tests" / "test.sh"
    solve_path = task_dir / "solution" / "solve.sh"
    test_text = read_text(test_path, issues, "test_sh") if test_path.is_file() else ""
    solve_text = read_text(solve_path, issues, "solution") if solve_path.is_file() else ""
    for path in (test_path, solve_path):
        if path.is_file() and not os.access(path, os.X_OK):
            add(issues, "FAIL", "shell_mode", f"script is not executable: {path.relative_to(task_dir)}")
        if path.is_file():
            try:
                result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True, timeout=10)
                if result.returncode:
                    add(issues, "FAIL", "shell_syntax", f"{path.relative_to(task_dir)}: {result.stderr.strip()}")
            except (OSError, subprocess.TimeoutExpired) as exc:
                add(issues, "FAIL", "shell_syntax", f"cannot check shell syntax: {exc}")
    if PLACEHOLDER_RE.search(solve_text) or "Replace solution/solve.sh" in solve_text:
        add(issues, "FAIL", "placeholders", "solution/solve.sh still contains template placeholders")
    # Selector and reward behavior are checked dynamically by per_test_gate.py; only the
    # static contract is enforced here.
    if "TBENCH_TEST_ID" not in test_text:
        add(issues, "FAIL", "test_selector", "tests/test.sh does not honor the TBENCH_TEST_ID selector")
    if "pytest" in test_text and "--tb=no" not in test_text:
        add(issues, "FAIL", "test_leak", "pytest invocation must use --tb=no to suppress verifier source")
    # Master #84: a failing run's own test-stdout.txt must name why it failed, and --tb=no
    # prints nothing, so the reporter records each failure's message and test.sh echoes it.
    reporter_path = task_dir / "tests" / "ctrf_reporter.py"
    if "pytest" in test_text and reporter_path.is_file():
        if '"message"' not in reporter_path.read_text(encoding="utf-8", errors="replace"):
            add(issues, "FAIL", "test_failure_messages",
                "tests/ctrf_reporter.py must record each failed case's assertion message in ctrf.json")
        if '"message"' not in test_text:
            add(issues, "FAIL", "test_failure_messages",
                "tests/test.sh must print one line per failed case with its ctrf.json message")
    if NETWORK_INSTALL_RE.search(test_text):
        add(issues, "FAIL", "test_dependencies", "tests/test.sh may not install or download dependencies at runtime")
    return test_text


def check_manifest(task_dir: Path, test_text: str, issues: list[Issue]) -> list[str]:
    try:
        manifest = load_test_manifest(task_dir)
    except WorkflowError as exc:
        add(issues, "FAIL", "test_manifest", str(exc))
        return []
    entries = manifest.get("tests", [])
    ids: list[str] = []
    for index, entry in enumerate(entries):
        prefix = f"tests[{index}]"
        if not isinstance(entry, dict):
            add(issues, "FAIL", "test_manifest", f"{prefix} must be an object")
            continue
        test_id = entry.get("id")
        if not isinstance(test_id, str) or not TEST_ID_RE.fullmatch(test_id):
            add(issues, "FAIL", "test_manifest", f"{prefix}.id is invalid: {test_id!r}")
            continue
        ids.append(test_id)
        if len(str(entry.get("description", "")).strip()) < 20:
            add(issues, "FAIL", "test_manifest", f"{test_id}: description is not substantive")
        requirement = entry.get("requirement")
        if not isinstance(requirement, str) or "instruction.md" not in requirement:
            add(issues, "FAIL", "test_manifest", f"{test_id}: requirement must point to instruction.md")
        if test_text and not re.search(rf"(?m)^\s*{re.escape(test_id)}\)", test_text):
            add(issues, "FAIL", "test_selector", f"tests/test.sh has no selector branch for manifest id {test_id!r}")
    duplicates = sorted({test_id for test_id in ids if ids.count(test_id) > 1})
    if duplicates:
        add(issues, "FAIL", "test_manifest", f"duplicate test IDs: {', '.join(duplicates)}")
    return ids


CONTROLS_HEADING_RE = re.compile(r"(?m)^## (?:Negative controls|Plan)\b.*$")
GATE_RESULTS_HEADING_RE = re.compile(r"(?m)^## Gate results\b.*$")
CONTROLS_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_])test_[A-Za-z0-9_]+(?![A-Za-z0-9_]|\.[A-Za-z])")


def check_controls_plan(task_dir: Path, issues: list[Issue]) -> None:
    """WARN when authoring/<slug>/controls.md names tests that do not exist in the manifest.

    Only the text after the `## Negative controls` (or `## Plan`, the template's name for
    it) heading is scanned so that round history recorded above it may cite historical
    names; generated `## Gate results` sections are skipped as well. Tokens are `test_*`
    identifiers; a `.py`/`.json` suffix (`test_outputs.py`) is not a case name and is
    ignored. Allowed names are the manifest CTRF cases with their `file::` prefix
    stripped, plus the module stems of those files.
    """
    path = REPO_ROOT / "authoring" / task_dir.name / "controls.md"
    if not path.is_file():
        return
    text = read_text(path, issues, "controls_plan")
    if not text:
        return
    try:
        manifest = load_test_manifest(task_dir)
    except WorkflowError:
        return  # reported by check_manifest
    allowed: set[str] = set()
    for entry in manifest["tests"]:
        for case in entry.get("cases", []):
            module, _, function = case.rpartition("::")
            allowed.add(function)
            if module:
                allowed.add(Path(module).stem)
    heading = CONTROLS_HEADING_RE.search(text)
    if heading is None:
        add(issues, "WARN", "controls_plan",
            f"{path.relative_to(REPO_ROOT)} has no '## Negative controls' (or '## Plan') section")
        return
    scanned = text[heading.end():]
    # Drop generated results sections (they end at the next level-2 heading).
    scanned = re.sub(r"(?ms)^## Gate results\b.*?(?=^## (?!#)|\Z)", "", scanned)
    unknown = sorted({token for token in CONTROLS_TOKEN_RE.findall(scanned) if token not in allowed})
    for token in unknown:
        add(issues, "WARN", "controls_plan",
            f"{path.relative_to(REPO_ROOT)} names '{token}' after '## Negative controls' but it is not a "
            f"CTRF case function in tests/test_manifest.json")


def check_digest_partition(task_dir: Path, issues: list[Issue]) -> None:
    """FAIL when a digested task-root entry sits outside both digest surfaces.

    Such an entry moves the full task digest while being invisible to both the
    agent and the grader digest, so a split-digest reader would see no change.
    """
    try:
        assert_digest_partition(task_dir)
    except WorkflowError as exc:
        add(issues, "FAIL", "digest_partition", str(exc))


def check_seed_parity(task_dir: Path, issues: list[Issue]) -> None:
    """FAIL when a file exists in both tests/seed/ and environment/ but differs.

    Files only one of the two trees carries are fine and expected; a shared path
    that has drifted means the grader reseeds from something other than what the
    agent's image was built with.
    """
    try:
        parity = seed_parity(task_dir)
    except WorkflowError as exc:
        add(issues, "FAIL", "seed_parity", str(exc))
        return
    # A seed file with no environment/ counterpart is compared against nothing, so the
    # check passes whatever the file contains. That is legitimate when tests/seed/ carries
    # a generator the image never ships -- and silent when the counterpart merely sits at a
    # different path, which is how phase-coherent's tests/seed/generate_session.py drifted
    # from environment/src/generate_session.py while parity reported success. WARN so the
    # next one is visible; the author confirms it is unpaired by intent.
    environment_root = task_dir / "environment"
    unpaired = [rel for rel in parity if not (environment_root / rel).is_file()]
    if unpaired:
        add(issues, "WARN", "seed_parity",
            "tests/seed/ file(s) with no environment/ counterpart, so parity compares nothing: "
            f"{', '.join(sorted(unpaired))}")


def check_hardening(task_dir: Path, issues: list[Issue]) -> None:
    """Fold the Terminal-Bench Science hardening rules in as FAIL/WARN findings."""
    try:
        findings = HardeningCheck(task_dir, require_workflow=False).collect()
    except Exception as exc:  # pragma: no cover - defensive: never hide a checker crash
        add(issues, "FAIL", "hardening", f"hardening_check crashed: {exc}")
        return
    for finding in findings:
        level = "FAIL" if finding.severity == "ERROR" else "WARN"
        add(issues, level, "hardening", f"{finding.path}: {finding.message}")


def validate_task(task_dir: Path, *, strict: bool = False) -> dict[str, Any]:
    task_dir = task_dir.resolve()
    issues: list[Issue] = []
    check_layout(task_dir, issues)
    if task_dir.is_dir():
        task_toml = check_toml(task_dir, issues)
        check_instruction(task_dir, issues, task_toml)
        check_readme(task_dir, issues)
        check_verifier_image(task_dir, task_toml, issues)
        test_text = check_scripts(task_dir, task_toml, issues)
        check_manifest(task_dir, test_text, issues)
        check_digest_partition(task_dir, issues)
        check_seed_parity(task_dir, issues)
        check_controls_plan(task_dir, issues)
        check_hardening(task_dir, issues)
        check_canaries(task_dir, issues)
        for relative in REQUIRED_FILES:
            path = task_dir / relative
            if path.is_file():
                text = read_text(path, issues, "placeholders")
                if PLACEHOLDER_RE.search(text):
                    add(issues, "FAIL", "placeholders", f"template placeholder remains in {relative}")
    fail_count = sum(issue.level == "FAIL" for issue in issues)
    warn_count = sum(issue.level == "WARN" for issue in issues)
    failed = bool(fail_count or (strict and warn_count))
    return {
        "status": "FAIL" if failed else "PASS",
        "task_dir": str(task_dir),
        "strict": strict,
        "summary": {"fail": fail_count, "warn": warn_count},
        "issues": [asdict(issue) for issue in issues],
    }


def render(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        f"Task check: {report['status']} ({summary.get('fail', 0)} FAIL, {summary.get('warn', 0)} WARN)",
        f"Task: {report['task_dir']}",
    ]
    for issue in report.get("issues", []):
        lines.append(f"{issue['level']} [{issue['check']}] {issue['detail']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = validate_task(args.task_dir, strict=args.strict)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render(report))
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
