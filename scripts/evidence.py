#!/usr/bin/env python3
"""Seal and verify Step 2b per-test evidence against task contents."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import (
    AGENT_DIGEST_VERSION,
    WorkflowError,
    legacy_agent_digest,
    load_json,
    load_test_manifest,
    manifest_ids,
    portable_path,
    require_outside_task,
    resolve_recorded_path,
    sha256_file,
    split_digests,
    task_digest,
    validate_gate_coverage,
    write_json,
)

# Seals written before the split digest existed carry "1.1" and stay valid; "1.2"
# adds agent_digest/grader_digest and is what build_seal writes now.
SEAL_SCHEMA_VERSION = "1.2"
ACCEPTED_SEAL_SCHEMA_VERSIONS = ("1.1", "1.2")

# A reseal re-stamps an existing seal at a new FULL task digest WITHOUT re-running the
# per-test Oracle/NOP matrix. It is admissible only when both graded surfaces are
# byte-identical, and that is a complete argument rather than a convenience: the full
# digest covers exactly the agent surface, the grader surface, and the descriptive
# [metadata] keys that functional_task_toml() folds out of the agent digest. So "full
# moved, neither half moved" leaves only an edit no trial could observe. Correcting
# expert_time_estimate_hours after a rerun (MASTER_CHECKLIST_TBSCI.md #94 item 4) is
# exactly that edit, and re-measuring a matrix against a byte-identical grader and a
# byte-identical Oracle/NOP surface is ceremony. (task.toml carries no difficulty field
# at all -- Master #62 -- so the measured rate never forces this.)
RESEAL_REASON = "descriptive [metadata] only; agent and grader surfaces byte-identical"
STALE_FULL_DIGEST = "Step 2b evidence is stale: task files changed after sealing"
STALE_AGENT_SURFACE = "Step 2b evidence is stale: the agent-facing surface changed after sealing"
STALE_GRADER_SURFACE = "Step 2b evidence is stale: the grader surface changed after sealing"
FULL_GATE_HINT = "run scripts/gate_step2b.sh for a full Step 2b gate"
from gate_artifacts import validate_raw_records
from task_check import validate_task


def validate_step2b_report(task_dir: Path, report: dict[str, Any],
                          expected_digest: str | None = None) -> list[str]:
    """Validate a per-test gate report against the task it was measured on.

    ``expected_digest`` is the FULL task digest the report must carry. It defaults to
    the task's current digest, which is what a freshly sealed report has. A resealed
    seal passes the digest the matrix was actually measured at (see
    ``sealed_report_digest``) rather than the digest the seal now binds to: the report
    is evidence and is never rewritten.
    """
    errors: list[str] = []
    try:
        digest = task_digest(task_dir) if expected_digest is None else expected_digest
    except WorkflowError as exc:
        return [str(exc)]
    if report.get("task_slug") != task_dir.name:
        errors.append(f"report task_slug {report.get('task_slug')!r} does not match {task_dir.name!r}")
    if report.get("task_digest") != digest:
        errors.append("per-test report task digest does not match current task")
    try:
        ids = manifest_ids(task_dir)
        manifest = load_test_manifest(task_dir)
    except WorkflowError as exc:
        return [*errors, str(exc)]
    cases_by_id = {entry["id"]: entry.get("cases", []) for entry in manifest["tests"]}
    errors.extend(
        validate_gate_coverage(
            report,
            expected_ids=ids,
            required_agents=("oracle", "nop"),
            minimum_repeats=1,
            expected_cases_by_id=cases_by_id,
        )
    )
    errors.extend(validate_raw_records(report))
    return errors


def build_seal(task_dir: Path, report_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        require_outside_task(task_dir, report_path)
        report = load_json(report_path)
    except WorkflowError as exc:
        return None, [str(exc)]
    if not isinstance(report, dict):
        return None, ["per-test report must be a JSON object"]
    errors = validate_step2b_report(task_dir, report)
    static = validate_task(task_dir, strict=True)
    errors.extend(f"task_check/{issue['check']}: {issue['detail']}" for issue in static["issues"]
                  if issue["level"] in {"FAIL", "WARN"})
    if errors:
        return None, errors
    try:
        digests = split_digests(task_dir)
        ids = manifest_ids(task_dir)
    except WorkflowError as exc:
        return None, [str(exc)]
    seal = {
        "schema_version": SEAL_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task_slug": task_dir.name,
        "task_digest": digests["full"],
        "agent_digest": digests["agent"],
        "agent_digest_version": AGENT_DIGEST_VERSION,
        "grader_digest": digests["grader"],
        "manifest_test_ids": ids,
        "per_test_report": portable_path(report_path),
        "per_test_report_sha256": f"sha256:{sha256_file(report_path)}",
        "requirements": {
            "oracle_per_test": 1.0,
            "nop_per_test": 0.0,
            "fresh_harbor_trial_per_row": True,
        },
    }
    return seal, []


def sealed_report_digest(evidence: dict[str, Any]) -> str | None:
    """The FULL task digest the sealed per-test matrix was measured at.

    Normally the seal's own ``task_digest``. After a reseal the seal binds to a newer
    full digest while the per-test report keeps the digest it was measured under, so the
    first entry of the reseal lineage is the answer. Returns None when the seal carries
    neither, which the caller reports rather than papering over.
    """
    reseal_record = evidence.get("reseal")
    if isinstance(reseal_record, dict):
        lineage = reseal_record.get("superseded_task_digests")
        if isinstance(lineage, list) and lineage and isinstance(lineage[0], str):
            return lineage[0]
        return None
    value = evidence.get("task_digest")
    return value if isinstance(value, str) else None


def sealed_surfaces_moved(
    task_dir: Path, evidence: dict[str, Any], current: dict[str, str]
) -> tuple[list[str], list[str], dict[str, str | None]]:
    """Report which graded surfaces moved since ``evidence`` was written.

    Returns ``(moved, errors, now)``: ``moved`` names "agent" and/or "grader"; ``errors``
    carries a seal-format problem that makes the comparison impossible; ``now`` gives the
    value each sealed digest was compared against, so a caller can name both sides.

    The agent half is version-aware. A seal with no ``agent_digest_version`` predates
    AGENT_DIGEST_VERSION "v2" and therefore stores a v1 fold, which hashes ``task.toml``
    byte-for-byte; comparing it against a freshly computed v2 value would report a move
    for every such seal. This is the single place that comparison is made -- ``check_seal``
    and ``reseal`` both route through it so they can never drift apart.
    """
    moved: list[str] = []
    errors: list[str] = []
    sealed_version = evidence.get("agent_digest_version") or "v1"
    if sealed_version == AGENT_DIGEST_VERSION:
        sealed_agent_now: str | None = current["agent"]
    elif sealed_version == "v1":
        sealed_agent_now = legacy_agent_digest(task_dir)
    else:
        errors.append(f"unknown agent_digest_version {sealed_version!r}; rerun gates and reseal")
        sealed_agent_now = None
    if sealed_agent_now is not None and evidence.get("agent_digest") != sealed_agent_now:
        moved.append("agent")
    if evidence.get("grader_digest") != current["grader"]:
        moved.append("grader")
    return moved, errors, {"agent": sealed_agent_now, "grader": current["grader"]}


def validate_reseal_record(evidence: dict[str, Any]) -> list[str]:
    """Check a reseal record for internal consistency with the seal that carries it."""
    record = evidence.get("reseal")
    if record is None:
        return []
    if not isinstance(record, dict):
        return ["reseal record must be a JSON object"]
    errors: list[str] = []
    lineage = record.get("superseded_task_digests")
    if (not isinstance(lineage, list) or not lineage
            or not all(isinstance(item, str) and item for item in lineage)):
        errors.append("reseal record has no superseded_task_digests lineage")
    else:
        if record.get("previous_task_digest") != lineage[-1]:
            errors.append("reseal previous_task_digest is not the last superseded digest")
        if evidence.get("task_digest") in lineage or len(set(lineage)) != len(lineage):
            errors.append("reseal lineage repeats a digest")
    for key in ("agent_digest", "grader_digest"):
        if record.get(key) != evidence.get(key):
            errors.append(f"reseal {key} disagrees with the seal's {key}")
    if record.get("reason") != RESEAL_REASON:
        errors.append("reseal record carries an unrecognized reason")
    if not isinstance(record.get("resealed_at"), str) or not record["resealed_at"]:
        errors.append("reseal record has no resealed_at timestamp")
    return errors


def check_seal(task_dir: Path, evidence_path: Path) -> list[str]:
    try:
        evidence = load_json(evidence_path)
    except WorkflowError as exc:
        return [str(exc)]
    if not isinstance(evidence, dict):
        return ["evidence must be a JSON object"]
    errors: list[str] = []
    schema_version = evidence.get("schema_version")
    if schema_version not in ACCEPTED_SEAL_SCHEMA_VERSIONS:
        errors.append("old Step 2b evidence format; rerun gates and reseal")
    try:
        current_digest = task_digest(task_dir)
        current_ids = manifest_ids(task_dir)
    except WorkflowError as exc:
        return [str(exc)]
    if evidence.get("task_slug") != task_dir.name:
        errors.append("evidence task slug does not match task directory")
    if evidence.get("task_digest") != current_digest:
        errors.append("Step 2b evidence is stale: task files changed after sealing")
    if schema_version == "1.2":
        # The full-digest comparison above already invalidates the seal on any
        # change, grader edits included; these only localize which half moved.
        try:
            current = split_digests(task_dir)
        except WorkflowError as exc:
            errors.append(str(exc))
        else:
            moved, version_errors, _ = sealed_surfaces_moved(task_dir, evidence, current)
            errors.extend(version_errors)
            if "agent" in moved:
                errors.append(STALE_AGENT_SURFACE)
            if "grader" in moved:
                errors.append(STALE_GRADER_SURFACE)
    errors.extend(validate_reseal_record(evidence))
    report_value = evidence.get("per_test_report")
    if not isinstance(report_value, str):
        errors.append("evidence has no per_test_report path")
        return errors
    report_path = resolve_recorded_path(report_value)
    if not report_path.is_file():
        errors.append(f"recorded per-test report is missing: {report_value}")
        return errors
    expected_hash = evidence.get("per_test_report_sha256")
    actual_hash = f"sha256:{sha256_file(report_path)}"
    if expected_hash != actual_hash:
        errors.append("per-test report changed after Step 2b sealing")
    try:
        report = load_json(report_path)
    except WorkflowError as exc:
        errors.append(str(exc))
        return errors
    if isinstance(report, dict):
        # A resealed seal binds to a newer full digest than the matrix was measured at;
        # the report is held to the digest it was measured at, never rewritten.
        expected_report_digest = sealed_report_digest(evidence)
        if expected_report_digest is None:
            errors.append("evidence records no task digest for its per-test report")
        else:
            errors.extend(validate_step2b_report(task_dir, report, expected_report_digest))
    else:
        errors.append("per-test report must be a JSON object")
    if evidence.get("manifest_test_ids") != current_ids:
        errors.append("test manifest IDs or order changed after Step 2b sealing")
    return sorted(set(errors))


def reseal(task_dir: Path, evidence_path: Path
           ) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    """Re-stamp an existing seal at the current FULL digest, carrying its matrix over.

    Returns ``(seal, notes, errors)``. A ``None`` seal with no errors means the seal is
    already current and nothing should be written. Everything the seal asserts other than
    the full digest -- the recorded agent and grader digests, the per-test report and its
    hash, the manifest IDs, the original ``created_at`` -- is carried over unchanged,
    because it was verified to still hold rather than re-measured.
    """
    try:
        evidence = load_json(evidence_path)
    except WorkflowError as exc:
        return None, [], [str(exc)]
    if not isinstance(evidence, dict):
        return None, [], ["evidence must be a JSON object"]
    if evidence.get("schema_version") != "1.2":
        return None, [], [
            f"seal schema_version is {evidence.get('schema_version')!r}; a reseal needs the "
            f"recorded agent/grader digests that only a '1.2' seal carries -- {FULL_GATE_HINT}"]
    if evidence.get("task_slug") != task_dir.name:
        return None, [], ["evidence task slug does not match task directory"]
    sealed_digest = evidence.get("task_digest")
    if not isinstance(sealed_digest, str) or not sealed_digest:
        return None, [], ["evidence has no task_digest to reseal from"]
    try:
        current = split_digests(task_dir)
    except WorkflowError as exc:
        return None, [], [str(exc)]

    # 1. The precondition: neither graded surface may have moved. This is the whole
    #    licence for skipping the matrix, so it is checked first and reported precisely.
    moved, version_errors, now = sealed_surfaces_moved(task_dir, evidence, current)
    if version_errors:
        return None, [], version_errors
    if moved:
        sealed_version = evidence.get("agent_digest_version") or "v1"
        errors = [
            f"the {surface} surface moved since this seal "
            f"({evidence.get(f'{surface}_digest')} -> {now[surface]}); that is a behavioral "
            f"change, not a descriptive one -- {FULL_GATE_HINT}"
            for surface in moved]
        if "agent" in moved and sealed_version == "v1":
            errors.append(
                "this seal records a v1 agent fold, which hashes task.toml byte-for-byte, so "
                "even a descriptive [metadata] edit moves it; only a full gate can reseal it "
                f"under {AGENT_DIGEST_VERSION}")
        return None, [], errors

    if sealed_digest == current["full"]:
        return None, [f"task digest is already {current['full']}; the seal is current"], []

    # 2. Everything else the seal asserts must still hold. check_seal is the single
    #    definition of that, so run it and allow exactly one residual complaint: the full
    #    digest moved, which is the thing this command is here to re-stamp.
    residual = [error for error in check_seal(task_dir, evidence_path)
                if error != STALE_FULL_DIGEST]
    if residual:
        return None, [], residual

    # 3. The static screen. This is the part that can genuinely fail here, because
    #    task_check validates the descriptive [metadata] values a reseal exists to change.
    static = validate_task(task_dir, strict=True)
    static_errors = [f"task_check/{issue['check']}: {issue['detail']}"
                     for issue in static["issues"] if issue["level"] in {"FAIL", "WARN"}]
    if static_errors:
        return None, [], static_errors

    previous = evidence.get("reseal")
    lineage: list[str] = []
    if isinstance(previous, dict) and isinstance(previous.get("superseded_task_digests"), list):
        lineage = [item for item in previous["superseded_task_digests"] if isinstance(item, str)]
    lineage.append(sealed_digest)

    seal = dict(evidence)
    seal["task_digest"] = current["full"]
    seal["reseal"] = {
        "previous_task_digest": sealed_digest,
        "superseded_task_digests": lineage,
        "reason": RESEAL_REASON,
        "agent_digest": evidence.get("agent_digest"),
        "grader_digest": evidence.get("grader_digest"),
        "resealed_at": datetime.now(timezone.utc).isoformat(),
    }
    report_value = evidence.get("per_test_report")
    notes = [
        f"task digest: {sealed_digest} -> {current['full']}",
        f"agent digest: {evidence.get('agent_digest')} UNCHANGED "
        f"({evidence.get('agent_digest_version') or 'v1'} fold)",
        f"grader digest: {evidence.get('grader_digest')} UNCHANGED",
        f"carried over: per-test Oracle/NOP matrix {report_value} "
        f"{evidence.get('per_test_report_sha256')} -- REUSED, not re-measured",
        f"carried over: {len(evidence.get('manifest_test_ids') or [])} manifest test IDs, "
        f"sealed {evidence.get('created_at')}",
        f"reason: {RESEAL_REASON}",
    ]
    return seal, notes, []


def command_reseal(args: argparse.Namespace) -> int:
    task_dir = args.task_dir.resolve()
    evidence_path = args.evidence.resolve()
    output = (args.output or args.evidence).resolve()
    if not task_dir.is_dir():
        print(f"Evidence reseal: FAIL\n- task directory not found: {task_dir}")
        return 1
    if not evidence_path.is_file():
        print(f"Evidence reseal: FAIL\n- no Step 2b seal at {portable_path(evidence_path)}; "
              f"{FULL_GATE_HINT}")
        return 1
    try:
        require_outside_task(task_dir, output)
    except WorkflowError as exc:
        print(f"Evidence reseal: FAIL\n- {exc}")
        return 1
    seal, notes, errors = reseal(task_dir, evidence_path)
    if errors:
        print("Evidence reseal: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    if seal is None:
        print("Evidence reseal: PASS (nothing to do)")
        for note in notes:
            print(f"- {note}")
        return 0
    previous_bytes = output.read_bytes() if output.is_file() else None
    write_json(output, seal)
    recheck = check_seal(task_dir, output)
    if recheck:
        if previous_bytes is None:
            output.unlink(missing_ok=True)
        else:
            output.write_bytes(previous_bytes)
        print("Evidence reseal: FAIL")
        print("- the resealed evidence did not check out; the original seal was restored")
        for error in recheck:
            print(f"- {error}")
        return 1
    print("Evidence reseal: PASS")
    for note in notes:
        print(f"- {note}")
    print(f"Task digest: {seal['task_digest']}")
    print(f"Evidence: {portable_path(output)}")
    print("Evidence readiness: PASS (evidence.py check re-verified the rewritten seal)")
    print("Next: re-bind the Step 3b review header with "
          "`scripts/stage_reports.py rebind-review`, then re-head the difficulty report "
          "(Task digest and Review SHA256).")
    return 0


def command_seal(args: argparse.Namespace) -> int:
    task_dir = args.task_dir.resolve()
    report_path = args.per_test_report.resolve()
    try:
        require_outside_task(task_dir, args.output)
        if args.output.resolve() == report_path:
            raise WorkflowError("evidence output must not overwrite the per-test report")
    except WorkflowError as exc:
        print(f"Evidence seal: FAIL\n- {exc}")
        return 1
    if not task_dir.is_dir():
        print(f"Evidence seal: FAIL\n- task directory not found: {task_dir}")
        return 1
    seal, errors = build_seal(task_dir, report_path)
    if errors or seal is None:
        print("Evidence seal: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    write_json(args.output, seal)
    print("Evidence seal: PASS")
    print(f"Task digest: {seal['task_digest']}")
    print(f"Evidence: {portable_path(args.output)}")
    return 0


def command_check(args: argparse.Namespace) -> int:
    task_dir = args.task_dir.resolve()
    if not task_dir.is_dir():
        print(f"Evidence readiness: FAIL\n- task directory not found: {task_dir}")
        return 1
    errors = check_seal(task_dir, args.evidence.resolve())
    print(f"Evidence readiness: {'FAIL' if errors else 'PASS'}")
    if not errors:
        print(f"Task digest: {task_digest(task_dir)}")
    for error in errors:
        print(f"- {error}")
    return 1 if errors else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    seal = subparsers.add_parser("seal")
    seal.add_argument("task_dir", type=Path)
    seal.add_argument("--per-test-report", type=Path, required=True)
    seal.add_argument("--output", type=Path, required=True)
    seal.set_defaults(func=command_seal)
    reseal_parser = subparsers.add_parser(
        "reseal",
        help="re-stamp an existing seal at a new full digest when both graded surfaces "
             "are byte-identical (descriptive [metadata] edits only)")
    reseal_parser.add_argument("task_dir", type=Path)
    reseal_parser.add_argument("--evidence", type=Path, required=True)
    reseal_parser.add_argument("--output", type=Path, default=None,
                               help="write the resealed evidence here (default: in place)")
    reseal_parser.set_defaults(func=command_reseal)
    check = subparsers.add_parser("check")
    check.add_argument("task_dir", type=Path)
    check.add_argument("--evidence", type=Path, required=True)
    check.set_defaults(func=command_check)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
