#!/usr/bin/env python3
"""Run the mechanical MASTER_CHECKLIST_TBSCI.md checks over a built delivery ZIP.

  python3 scripts/verify_package.py Task_Ready_To_Submit/<task>.zip

MASTER_CHECKLIST_TBSCI.md is the source of truth. This script answers, from the ZIP
alone, every check a machine can answer without judgment, and prints each finding
with its master number (``Master #N``). ``package_task.py`` runs it on every ZIP it
writes and deletes the ZIP when anything fails, so this is also the literal last step
before a ZIP exists (Master #97). Checks that need judgment -- reading a trajectory
to confirm a verdict, deciding whether a decoy is fair -- stay in the per-task record
``authoring/<task>/master-checklist.md``.

Covered here: structure and banned names (#71, #96); rubric.txt format (#67); Oracle
x3 / NOP x2 rewards, per-test statuses and genuine NOP failures (#40, #58, #72-#74);
CTRF case sets against the shipped manifest (#53); SUMMARY.txt format, rewards and
bundle sha (#77, #79, #80); rubric_score.txt format, arithmetic, per-verdict evidence
and pairwise distinctness (#70, #78, #85, #86); evidence bound by digest, mtimes
secondary (#75); independent controls and runs (#76, #83); agent/ and
verifier/ file sets, full-fidelity capture and exception_info (#90-#93); reward-hack
command scan (#93); per-directory PII / ``stb`` / canary grep over the whole bundle
(#87, #88, #97); the five runs in launch order at one run config -- distinct trial IDs,
strictly increasing result.json ``started_at``, one task checksum and one agent
configuration (#94 item 1; which trials were candidates is composition.json's job,
``scripts/compose_step3c.py``, and stays in the workspace).
"""

from __future__ import annotations

import argparse
from datetime import datetime
import getpass
import itertools
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from check_trajectory import check_trial
from common import WorkflowError, bundle_sha, load_json, nop_infrastructure_errors
from gate_artifacts import read_ctrf


TASK_MEMBERS = ("instruction.md", "task.toml", "environment", "solution", "tests")
ORACLE_JOBS = ("oracle-1", "oracle-2", "oracle-3")
NOP_JOBS = ("nop-1", "nop-2")
CONTROL_FILES = ("ctrf.json", "reward.txt", "test-stdout.txt")
RUNS = tuple(f"run-{index:02d}" for index in range(1, 6))
RUN_FILES = ("config.json", "result.json", "rubric_score.txt")
RUN_TREES = ("agent", "verifier")
AGENT_REQUIRED = ("api-calls.jsonl", "recording.cast", "trajectory.json")
VERIFIER_REQUIRED = ("ctrf.json", "reward.txt", "test-stdout.txt")
MODEL = "@openai/gpt-5.6"
EFFORT = "xhigh"

BANNED_DIRS = frozenset({"__MACOSX", ".git", "__pycache__", ".cursor", ".claude", ".aider"})
BANNED_FILES = frozenset({"SOURCE.txt", ".DS_Store", "AGENTS.md", "CLAUDE.md", "skills.md",
                          "rubrics.txt"})

RUBRIC_LINE = re.compile(r"^Agent .+, ([+-]\d+)$")
ALLOWED_SCORES = frozenset({1, 2, 3, 5})
RUBRIC_CITATION = re.compile(r"\[tests?\s*:|::|\btest_[A-Za-z0-9_]+\b", re.I)
SCORE_VERDICT = re.compile(r"^(MET|NOT MET|TRIGGERED|NOT TRIGGERED)(?:\s+\((.*)\))?$")
GRADIENT = re.compile(r"^gradient:\s*(\d+)/(\d+) positive met, (\d+)/(\d+) negative triggered$")
SUMMARY_HEAD = re.compile(r"^(\S+) sha=([0-9a-f]{64}) model=(\S+) \(reasoning_effort=([^)]+)\)$")
SUMMARY_TAIL = re.compile(r"^(\d+) runs, rewards: \[([^\]]*)\]$")

# Master #93: the agent never reads or writes the grading side.
HACK_PATTERNS = (
    ("/tests", re.compile(r"(?<![\w./-])/tests(?:/|\b)")),
    ("test_outputs.py", re.compile(r"\btest_outputs\.py\b")),
    ("ctrf.json", re.compile(r"\bctrf\.json\b")),
    ("reward.txt", re.compile(r"\breward\.txt\b")),
    ("/logs/verifier", re.compile(r"/logs/verifier\b")),
    ("/solution", re.compile(r"(?<![\w./-])/solution(?:/|\b)")),
)
# Master #87/#97. `stb` is case-sensitive and word-bounded; `/home/<name>` is legitimate
# only for an in-container account (the agent image's own users plus common defaults).
STB_RE = re.compile(r"\bstb\b")
HOME_RE = re.compile(r"/home/([A-Za-z0-9._-]+)")
MAC_RE = re.compile(r"/Users/|/private/tmp/")
CANARY_MARKER_RE = re.compile(
    r"BENCHMARK DATA SHOULD NEVER APPEAR|canary[\s_-]*(?:GUID|string|token)|terminal-bench-canary|"
    r"\bcanary\s*[:=]?\s*['\"]?[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-", re.I)
CONTAINER_HOMES = frozenset({"agent", "user", "ubuntu", "runner", "app", "node", "nonroot", "appuser",
                             "vscode", "jovyan", "coder", "dev", "tester", "worker", "builder"})
ADDRESS_RE = re.compile(r"\b0x[0-9a-f]{8,}\b")


class Report:
    def __init__(self) -> None:
        self.findings: list[tuple[str, str]] = []

    def fail(self, check: str, message: str) -> None:
        self.findings.append((check, message))


# --------------------------------------------------------------------------- rubric helpers
# Imported by package_task.py so the packager and this verifier apply one rule set.

def rubric_criteria(text: str) -> list[str]:
    return [line for line in text.split("\n") if line.strip()]


def validate_rubric_text(text: str) -> list[str]:
    """rubric.txt per Master #67: criterion lines only, exactly `Agent <behavior>, +N|-N`."""
    errors: list[str] = []
    if "\r" in text:
        errors.append("uses CR line endings")
    body = text[:-1] if text.endswith("\n") else text
    lines = body.split("\n") if body else []
    positive_total = negatives = 0
    for number, line in enumerate(lines, 1):
        if not line.strip():
            errors.append(f"line {number} is blank; the file is criterion lines only")
            continue
        match = RUBRIC_LINE.match(line)
        if not match:
            errors.append(f"line {number} is not exactly `Agent <behavior>, +N` or `, -N`: {line[:70]!r}")
            continue
        if RUBRIC_CITATION.search(line):
            errors.append(f"line {number} cites a test; state the behavior in product language: {line[:70]!r}")
        if re.search(r"\.,\s*[+-]\d+$", line):
            errors.append(f"line {number} has a period before the comma")
        raw = match.group(1)
        score = int(raw)
        if abs(score) not in ALLOWED_SCORES:
            errors.append(f"line {number} score {raw} is not one of 1, 2, 3, 5 (never 4)")
        if score > 0:
            positive_total += score
        else:
            negatives += 1
    if not lines:
        errors.append("no criteria")
    elif not negatives:
        errors.append("at least one negative criterion is required")
    if not 10 <= positive_total <= 40:
        errors.append(f"positive points total {positive_total}, must be between 10 and 40")
    return errors


def validate_rubric_score_text(text: str, criteria: list[str], reward: float, passed: int,
                               total: int) -> list[str]:
    """One run's rubric_score.txt against the rubric and that run's own results.

    Master #78/#86: data plus a parenthetical evidence citation on EVERY verdict line,
    nothing else. Master #70: the gradient line is the arithmetic of the verdicts.
    """
    errors: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != f"reward={reward}":
        errors.append(f"first line must be `reward={reward}`")
    if len(lines) < 2 or lines[1].strip() != f"tests_passed={passed}/{total}":
        errors.append(f"second line must be `tests_passed={passed}/{total}`")
    verdicts: dict[str, str] = {}
    for line in lines[2:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("gradient:"):
            continue
        head, sep, tail = stripped.partition(" -- ")
        if not sep:
            errors.append(f"line is neither a criterion verdict nor the gradient: {stripped[:60]!r}")
            continue
        match = SCORE_VERDICT.match(tail)
        if not match:
            errors.append(f"unknown verdict for {head[:50]!r}: {tail[:40]!r}")
            continue
        if not (match.group(2) or "").strip():
            errors.append(f"verdict for {head[:50]!r} carries no parenthetical evidence citation "
                          "from this run's trajectory (Master #86)")
        if head not in criteria:
            errors.append(f"line does not quote a rubric.txt criterion verbatim: {head[:60]!r}")
            continue
        if head in verdicts:
            errors.append(f"criterion scored twice: {head[:60]!r}")
            continue
        verdicts[head] = match.group(1)
    positives_met = negatives_triggered = positives = negatives = 0
    for criterion in criteria:
        match = RUBRIC_LINE.match(criterion)
        positive = bool(match) and int(match.group(1)) > 0
        positives += positive
        negatives += not positive
        verdict = verdicts.get(criterion)
        if verdict is None:
            errors.append(f"criterion is not scored: {criterion[:60]!r}")
            continue
        allowed = ("MET", "NOT MET") if positive else ("TRIGGERED", "NOT TRIGGERED")
        if verdict not in allowed:
            errors.append(f"criterion {criterion[:50]!r} scored {verdict}, expected one of {allowed}")
            continue
        positives_met += positive and verdict == "MET"
        negatives_triggered += (not positive) and verdict == "TRIGGERED"
    gradients = [line for line in lines if line.strip().startswith("gradient:")]
    if len(gradients) != 1:
        errors.append("exactly one `gradient:` line is required")
    else:
        match = GRADIENT.match(gradients[0].strip())
        if not match:
            errors.append("gradient line must read `gradient: X/Y positive met, X/Y negative triggered`")
        else:
            counted = tuple(int(group) for group in match.groups())
            expected = (positives_met, positives, negatives_triggered, negatives)
            if counted != expected:
                errors.append(f"gradient line says {counted}, the verdicts give {expected} (Master #70)")
    return errors


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


def summary_model_name(raw: str) -> str:
    """Master #77: strip through the last '/', then a leading '@'.

    ``@openai/gpt-5.6`` and ``openai/@openai/gpt-5.6`` both become ``gpt-5.6``.
    """
    name = raw.rsplit("/", 1)[-1]
    return name[1:] if name.startswith("@") else name


def summary_text(slug: str, sha: str, model: str, rewards: list[float],
                 effort: str = EFFORT) -> bytes:
    """The two-line trajectories/SUMMARY.txt -- data only (Master #77)."""
    rewards_text = ", ".join(f"{value}" for value in rewards)
    return (f"{slug} sha={sha} model={summary_model_name(model)} "
            f"(reasoning_effort={effort})\n"
            f"{len(rewards)} runs, rewards: [{rewards_text}]\n").encode("utf-8")


# --------------------------------------------------------------------------- readers

def read_binary_reward(path: Path) -> float:
    text = path.read_text(encoding="utf-8").strip()
    if text not in {"0", "1", "0.0", "1.0"}:
        raise WorkflowError(f"{path.name} is {text[:20]!r}; reward is binary, exactly 0 or 1 (Master #58)")
    return float(text)


def ctrf_rows(path: Path) -> tuple[dict[str, str], Any]:
    cases = read_ctrf(path)
    payload = load_json(path)
    start = payload.get("results", {}).get("summary", {}).get("start")
    return cases, start


def text_of(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="replace")


def manifest_cases(task_root: Path) -> list[str]:
    manifest = load_json(task_root / "tests" / "test_manifest.json")
    cases: list[str] = []
    for entry in manifest.get("tests", []) if isinstance(manifest, dict) else []:
        if isinstance(entry, dict):
            cases.extend(case for case in entry.get("cases", []) if isinstance(case, str))
    return cases


def container_users(task_root: Path) -> set[str]:
    users: set[str] = set(CONTAINER_HOMES)
    for dockerfile in (task_root / "environment").rglob("Dockerfile*"):
        for match in re.finditer(r"\b(?:useradd|adduser)\b([^\n&;|]*)", text_of(dockerfile)):
            tokens = [token for token in match.group(1).replace("\\", " ").split() if not token.startswith("-")]
            if tokens:
                users.add(tokens[-1])
    return users


def command_strings(value: Any) -> list[str]:
    """Every string inside tool-call arguments of an ATIF trajectory."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "arguments":
                found.extend(all_strings(item))
            else:
                found.extend(command_strings(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(command_strings(item))
    return found


def all_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in all_strings(item)]
    if isinstance(value, list):
        return [text for item in value for text in all_strings(item)]
    return []


# --------------------------------------------------------------------------- the checks

def check_structure(report: Report, names: list[str], zip_name: str) -> str | None:
    """Master #71/#96: exactly the four siblings, nothing else, no banned names."""
    for name in names:
        parts = PurePosixPath(name).parts
        if name.startswith("/") or ".." in parts:
            report.fail("#96", f"unsafe member path: {name}")
            return None
        for part in parts[:-1]:
            if part in BANNED_DIRS:
                report.fail("#96", f"banned directory in the ZIP: {name}")
        base = parts[-1] if parts else ""
        if base in BANNED_FILES or base.startswith("._") or base.endswith(".pyc") or base in BANNED_DIRS:
            report.fail("#96", f"banned file in the ZIP: {name}")
        # No README.md at the package root or the inner task root (Master #96, #103).
        if base == "README.md" and len(parts) <= 3:
            report.fail("#103", f"README.md does not ship: {name}")
    tops = {PurePosixPath(name).parts[0] for name in names if PurePosixPath(name).parts}
    if len(tops) != 1:
        report.fail("#96", f"the ZIP must hold exactly one top-level <task-slug>/ folder; found {sorted(tops)}")
        return None
    slug = tops.pop()
    if slug in {"task", "bundle"}:
        report.fail("#96", "the folder is named after the task, never the literal word task/bundle")
    if Path(zip_name).stem != slug:
        report.fail("#96", f"ZIP is named {Path(zip_name).name!r} but its folder is {slug!r}")
    allowed_top = {slug, "rubric.txt", "oracle-nop-evidence", "trajectories"}
    seen_top: set[str] = set()
    for name in names:
        parts = PurePosixPath(name).parts
        if len(parts) < 2:
            continue
        seen_top.add(parts[1])
        if parts[1] not in allowed_top:
            report.fail("#96", f"unexpected top-level member: {'/'.join(parts[:2])}")
        elif parts[1] == slug:
            if len(parts) < 3 or parts[2] not in TASK_MEMBERS:
                report.fail("#96", f"the inner task folder holds only {', '.join(TASK_MEMBERS)}: {name}")
        elif parts[1] == "oracle-nop-evidence":
            if len(parts) != 4 or parts[2] not in ORACLE_JOBS + NOP_JOBS or parts[3] not in CONTROL_FILES:
                report.fail("#71", f"oracle-nop-evidence holds only {{oracle-1..3,nop-1..2}}/{{{','.join(CONTROL_FILES)}}}: {name}")
        elif parts[1] == "trajectories":
            if len(parts) == 3 and parts[2] == "SUMMARY.txt":
                continue
            if len(parts) < 4 or parts[2] not in RUNS:
                report.fail("#96", f"trajectories holds only run-01..run-05 and SUMMARY.txt: {name}")
            elif len(parts) == 4 and parts[3] not in RUN_FILES:
                report.fail("#96", f"unexpected file in {parts[2]}: {parts[3]}")
            elif len(parts) > 4 and parts[3] not in RUN_TREES:
                report.fail("#96", f"unexpected tree in {parts[2]}: {parts[3]}")
    for member in allowed_top - seen_top:
        report.fail("#96", f"missing top-level member: {member}")
    return slug


def check_controls(report: Report, root: Path, cases: list[str], starts: dict[str, Any]) -> None:
    """Master #40, #53, #58, #72-#74."""
    for job in ORACLE_JOBS + NOP_JOBS:
        directory = root / "oracle-nop-evidence" / job
        missing = [name for name in CONTROL_FILES if not (directory / name).is_file()]
        if missing:
            report.fail("#71", f"{job} is missing {', '.join(missing)}")
            continue
        oracle = job.startswith("oracle")
        try:
            reward = read_binary_reward(directory / "reward.txt")
            statuses, starts[job] = ctrf_rows(directory / "ctrf.json")
        except WorkflowError as exc:
            label = "#58" if "binary" in str(exc) else ("#72" if oracle else "#74")
            report.fail(label, f"{job}: {exc}")
            continue
        if sorted(statuses) != sorted(cases):
            report.fail("#53", f"{job}: CTRF cases {len(statuses)} do not match the {len(cases)} shipped "
                               "manifest cases; the evidence was captured against a different tests/")
        wanted = "passed" if oracle else "failed"
        wrong = sorted(name for name, status in statuses.items() if status != wanted)
        if oracle and (reward != 1.0 or wrong):
            report.fail("#72", f"{job}: reward {reward}, non-passing cases {wrong[:5]}")
        if not oracle and (reward != 0.0 or wrong):
            report.fail("#40", f"{job}: reward {reward}; tests passing or not explicitly failed under NOP: {wrong[:5]}")
        if not oracle:
            infra = nop_infrastructure_errors(text_of(directory / "test-stdout.txt"))
            if infra:
                report.fail("#74", f"{job}: failures are infrastructure, not assertions ({', '.join(infra)})")


def check_independence(report: Report, root: Path, starts: dict[str, Any]) -> None:
    """Master #76: three Oracle and two NOP executions, not copies."""
    for group in (ORACLE_JOBS, NOP_JOBS):
        for first, second in itertools.combinations(group, 2):
            a, b = (root / "oracle-nop-evidence" / job for job in (first, second))
            if not ((a / "ctrf.json").is_file() and (b / "ctrf.json").is_file()):
                continue
            # Master #76 names the run-specific values to compare: the CTRF start timestamp
            # and embedded object addresses. Byte-identical grader output is NOT evidence by
            # itself: two genuine executions of a deterministic failure print the same bytes
            # when the CTRF carries no per-run field, and when it does, the start timestamp
            # below already differs between genuine runs.
            if starts.get(first) is not None and starts.get(first) == starts.get(second):
                report.fail("#76", f"{first} and {second} share the ctrf start timestamp {starts[first]!r}")
            if (a / "test-stdout.txt").is_file() and (b / "test-stdout.txt").is_file():
                ids_a = set(ADDRESS_RE.findall(text_of(a / "test-stdout.txt")))
                ids_b = set(ADDRESS_RE.findall(text_of(b / "test-stdout.txt")))
                if ids_a and ids_a == ids_b:
                    report.fail("#76", f"{first} and {second} carry identical object addresses; duplicated evidence")


def check_runs(report: Report, root: Path, cases: list[str], criteria: list[str]) -> list[float]:
    """Master #53, #58, #70, #78, #79, #83, #85, #86, #90-#93."""
    rewards: list[float] = []
    bodies: dict[str, list[str]] = {}
    blobs: dict[str, tuple[bytes, bytes]] = {}
    for run in RUNS:
        directory = root / "trajectories" / run
        if not directory.is_dir():
            report.fail("#96", f"missing trajectories/{run}")
            continue
        for name in RUN_FILES:
            if not (directory / name).is_file():
                report.fail("#90", f"{run} is missing {name}")
        for name in AGENT_REQUIRED:
            if not (directory / "agent" / name).is_file():
                report.fail("#90", f"{run}/agent is missing {name}")
        if not list((directory / "agent").glob("*.pane")):
            report.fail("#90", f"{run}/agent has no terminal pane capture (*.pane)")
        for name in VERIFIER_REQUIRED:
            if not (directory / "verifier" / name).is_file():
                report.fail("#90", f"{run}/verifier is missing {name}")
        try:
            reward = read_binary_reward(directory / "verifier" / "reward.txt")
            statuses, _ = ctrf_rows(directory / "verifier" / "ctrf.json")
        except (WorkflowError, OSError) as exc:
            report.fail("#58" if "binary" in str(exc) else "#79", f"{run}: {exc}")
            continue
        rewards.append(reward)
        passed = sum(status == "passed" for status in statuses.values())
        if sorted(statuses) != sorted(cases):
            report.fail("#53", f"{run}: CTRF cases do not match the shipped manifest ({len(statuses)} vs {len(cases)})")
        if (reward == 1.0) != (passed == len(statuses)):
            report.fail("#90", f"{run}: reward.txt {reward} disagrees with ctrf.json {passed}/{len(statuses)} passed")
        result = load_json(directory / "result.json")
        recorded = (((result or {}).get("verifier_result") or {}).get("rewards") or {}).get("reward")
        if recorded is None or float(recorded) != reward:
            report.fail("#79", f"{run}: result.json reward {recorded!r} disagrees with reward.txt {reward}")
        config = load_json(directory / "config.json")
        efforts = find_reasoning_effort(config)
        if not efforts or any(effort != EFFORT for effort in efforts):
            report.fail("#91", f"{run}: config.json reasoning_effort is {efforts!r}; must be {EFFORT!r} and never renamed")
        for problem in check_trial(str(directory), EFFORT).get("problems", []):
            report.fail("#92" if "exception" in problem or "reward" in problem else "#93", f"{run}: {problem}")
        commands: list[str] = []
        for segment in sorted((directory / "agent").glob("trajectory*.json")):
            try:
                commands += command_strings(load_json(segment))
            except WorkflowError as exc:
                report.fail("#93", f"{run}: {exc}")
        for label, pattern in HACK_PATTERNS:
            hit = next((text for text in commands if pattern.search(text)), None)
            if hit is not None:
                report.fail("#93", f"{run}: agent command touches {label}: {hit.strip()[:100]!r}")
        score_path = directory / "rubric_score.txt"
        if score_path.is_file():
            text = text_of(score_path)
            for error in validate_rubric_score_text(text, criteria, reward, passed, len(statuses)):
                report.fail("#78", f"{run}/rubric_score.txt: {error}")
            bodies[run] = [line.strip() for line in text.splitlines()[2:] if line.strip()]
        trajectory = directory / "agent" / "trajectory.json"
        if trajectory.is_file():
            blobs[run] = ((directory / "result.json").read_bytes(), trajectory.read_bytes())
    for first, second in itertools.combinations(sorted(bodies), 2):
        if bodies[first] == bodies[second]:
            report.fail("#85", f"{first} and {second} rubric_score.txt are identical below the header; "
                               "each must cite its own run's evidence")
    for first, second in itertools.combinations(sorted(blobs), 2):
        if blobs[first][0] == blobs[second][0] or blobs[first][1] == blobs[second][1]:
            report.fail("#83", f"{first} and {second} share a byte-identical result.json or trajectory.json")
    return rewards


def _utc(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo is not None else None


def check_launch_order(report: Report, root: Path) -> None:
    """Master #94 item 1: run-01..run-05 are the first five fidelity-complete trials at one
    digest and run config, in launch order. From the shipped files alone: every run is its
    own trial (distinct result.json ``id``), the runs start in strictly increasing
    ``started_at`` order, and they share one task checksum and one agent configuration."""
    rows = []
    for run in RUNS:
        result = load_json(root / "trajectories" / run / "result.json") \
            if (root / "trajectories" / run / "result.json").is_file() else None
        config = load_json(root / "trajectories" / run / "config.json") \
            if (root / "trajectories" / run / "config.json").is_file() else None
        if not isinstance(result, dict) or not isinstance(config, dict):
            continue  # a missing file is already a #90 finding
        agent = config.get("agent") if isinstance(config.get("agent"), dict) else {}
        rows.append((run, result.get("id"), _utc(result.get("started_at")), result.get("task_checksum"),
                     json.dumps({k: agent.get(k) for k in ("name", "model_name", "kwargs")}, sort_keys=True)))
    ids = [row[1] for row in rows]
    if any(not isinstance(value, str) or not value for value in ids):
        report.fail("#94", "a run's result.json has no trial id; launch order cannot be checked")
    elif len(set(ids)) != len(ids):
        report.fail("#94", "two runs carry the same result.json trial id")
    for (run_a, _, start_a, _, _), (run_b, _, start_b, _, _) in zip(rows, rows[1:]):
        if start_a is None or start_b is None:
            report.fail("#94", f"{run_a if start_a is None else run_b}: result.json has no UTC started_at")
        elif not start_a < start_b:
            report.fail("#94", f"{run_b} started at {start_b.isoformat()}, not after {run_a} "
                               f"({start_a.isoformat()}); runs must ship in launch order")
    if len({row[3] for row in rows}) > 1:
        report.fail("#94", "the runs record different task checksums; they are not one task revision")
    if len({row[4] for row in rows}) > 1:
        report.fail("#94", "the runs record different agent configurations (name, model_name, kwargs)")


def check_summary(report: Report, root: Path, slug: str, rewards: list[float]) -> None:
    """Master #77/#79/#80."""
    path = root / "trajectories" / "SUMMARY.txt"
    if not path.is_file():
        report.fail("#77", "trajectories/SUMMARY.txt is missing")
        return
    text = text_of(path)
    lines = text.split("\n")
    if lines[-1] == "":
        lines = lines[:-1]
    if len(lines) != 2:
        report.fail("#77", f"SUMMARY.txt has {len(lines)} lines; it is exactly two, no notes")
        return
    head, tail = SUMMARY_HEAD.match(lines[0]), SUMMARY_TAIL.match(lines[1])
    if not head:
        report.fail("#77", f"SUMMARY line 1 is not `<slug> sha=<hex> model=<stripped> (reasoning_effort=<setting>)`: {lines[0][:90]!r}")
    else:
        if head.group(1) != slug:
            report.fail("#77", f"SUMMARY names {head.group(1)!r}, not {slug!r}")
        expected_model = summary_model_name(MODEL)
        if head.group(3) != expected_model:
            report.fail("#77", f"SUMMARY model is {head.group(3)!r}, not {expected_model!r} "
                               f"(Master #77 strips the provider prefix from {MODEL!r})")
        if head.group(4) != EFFORT:
            report.fail("#91", f"SUMMARY reasoning_effort is {head.group(4)!r}, not {EFFORT!r}")
        fresh = bundle_sha(root / slug)
        if head.group(2) != fresh:
            report.fail("#80", f"SUMMARY sha {head.group(2)[:16]}... does not match the fresh recompute "
                               f"{fresh[:16]}... from inside {slug}/{slug}/")
    if not tail:
        report.fail("#77", f"SUMMARY line 2 is not `5 runs, rewards: [...]`: {lines[1][:90]!r}")
        return
    try:
        declared = [float(value) for value in tail.group(2).split(",") if value.strip()]
    except ValueError:
        report.fail("#77", "SUMMARY rewards are not numbers")
        return
    if int(tail.group(1)) != 5 or declared != rewards:
        report.fail("#79", f"SUMMARY rewards {declared} do not match run-01..05 reward.txt {rewards}")


def check_freshness(report: Report, infos: dict[str, zipfile.ZipInfo], slug: str) -> None:
    """Master #75: mtimes are a secondary sanity check; binding is by digest.

    The agent side (instruction.md, environment/, solution/) must predate every file the
    runs and controls produced; tests/ must predate every verifier output (a
    tests/-only regrade re-runs verification, so agent files may legitimately predate a
    later tests/ edit -- verifier outputs may not). task.toml is descriptive and excluded.
    """
    prefix = f"{slug}/{slug}/"
    agent_side = [info.date_time for name, info in infos.items() if name.startswith(prefix)
                  and name[len(prefix):].split("/")[0] in {"instruction.md", "environment", "solution"}]
    grader_side = [info.date_time for name, info in infos.items() if name.startswith(prefix + "tests/")]
    newest_agent = max(agent_side, default=None)
    newest_task = max(agent_side + grader_side, default=None)
    for name, info in infos.items():
        relative = name[len(slug) + 1:]
        parts = relative.split("/")
        verifier_output = (parts[0] == "oracle-nop-evidence") or (
            parts[0] == "trajectories" and len(parts) > 3 and parts[2] == "verifier")
        agent_output = parts[0] == "trajectories" and len(parts) > 3 and parts[2] == "agent"
        if verifier_output and newest_task and info.date_time <= newest_task:
            report.fail("#75", f"{relative} predates a task file it was graded against; regenerate the evidence")
        elif agent_output and newest_agent and info.date_time <= newest_agent:
            report.fail("#75", f"{relative} predates an agent-facing task file; the run is from an older task")


def check_leaks(report: Report, root: Path, slug: str) -> None:
    """Master #87/#88/#97: per directory, never one aggregate grep."""
    host_users = {getpass.getuser(), Path.home().name}
    in_container = container_users(root / slug) - host_users
    scopes = [root / slug, root / "rubric.txt", root / "trajectories" / "SUMMARY.txt"]
    scopes += [root / "oracle-nop-evidence" / job for job in ORACLE_JOBS + NOP_JOBS]
    scopes += [root / "trajectories" / run for run in RUNS]
    for scope in scopes:
        files = [scope] if scope.is_file() else sorted(path for path in scope.rglob("*") if path.is_file())
        for path in files:
            text = text_of(path)
            where = path.relative_to(root).as_posix()
            if MAC_RE.search(text):
                report.fail("#87", f"{where}: host path {MAC_RE.search(text).group(0)!r}")
            for match in HOME_RE.finditer(text):
                if match.group(1) not in in_container:
                    report.fail("#87", f"{where}: host home path /home/{match.group(1)}/")
                    break
            stb = STB_RE.search(text)
            if stb:
                line = text[max(0, stb.start() - 40):stb.end() + 40].replace("\n", " ")
                report.fail("#87", f"{where}: internal tool name `stb` ({line!r})")
            if CANARY_MARKER_RE.search(text):
                report.fail("#88", f"{where}: canary marker {CANARY_MARKER_RE.search(text).group(0)!r}")


def verify_zip(path: Path) -> list[tuple[str, str]]:
    report = Report()
    with zipfile.ZipFile(path) as package:
        if package.testzip() is not None:
            return [("#96", "ZIP failed its CRC check")]
        infos = {info.filename: info for info in package.infolist() if not info.is_dir()}
        slug = check_structure(report, list(infos), path.name)
        if slug is None:
            return report.findings
        with tempfile.TemporaryDirectory(prefix="verify-package-") as scratch:
            package.extractall(scratch)
            root = Path(scratch) / slug
            rubric = root / "rubric.txt"
            criteria: list[str] = []
            if rubric.is_file():
                text = text_of(rubric)
                for error in validate_rubric_text(text):
                    report.fail("#67", f"rubric.txt: {error}")
                criteria = rubric_criteria(text)
            try:
                cases = manifest_cases(root / slug)
            except WorkflowError as exc:
                report.fail("#53", f"cannot read the shipped tests/test_manifest.json: {exc}")
                cases = []
            starts: dict[str, Any] = {}
            check_controls(report, root, cases, starts)
            check_independence(report, root, starts)
            rewards = check_runs(report, root, cases, criteria)
            check_launch_order(report, root)
            check_summary(report, root, slug, rewards)
            check_freshness(report, infos, slug)
            check_leaks(report, root, slug)
    return report.findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("zip", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        findings = verify_zip(args.zip)
    except (OSError, zipfile.BadZipFile, WorkflowError, ValueError) as exc:
        findings = [("#96", f"cannot verify {args.zip}: {exc}")]
    if args.json:
        print(json.dumps({"zip": str(args.zip), "status": "FAIL" if findings else "PASS",
                          "findings": [{"master": check, "detail": detail} for check, detail in findings]},
                         indent=2))
    else:
        print(f"Verify package: {'FAIL' if findings else 'PASS'} ({len(findings)} finding(s)) {args.zip}")
        for check, detail in findings:
            print(f"FAIL Master {check}: {detail}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
