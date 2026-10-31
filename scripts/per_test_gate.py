#!/usr/bin/env python3
"""Run each manifest test in fresh Harbor Oracle/NOP trials (one job per test/agent/repeat).

Each row injects --verifier-env TBENCH_TEST_ID=<id>, then reads the raw result.json and
verifier/ctrf.json instead of trusting console text. Evidence lands under artifacts/.

--jobs N runs N rows at a time (default 1 = strictly serial). Row order in the report is
fixed up front, so a report is identical whatever --jobs was used. Rows of a test named by
--exclusive-test always run alone, for tests whose measurement (peak RSS, work counters,
wall-clock growth ratios) would be corrupted by a second container competing for the box.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import tempfile
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import (
    REPO_ROOT,
    finite_number,
    per_test_expected_reward,
    require_outside_task,
    sha256_file,
    WorkflowError,
    load_test_manifest,
    nop_infrastructure_errors,
    portable_path,
    task_digest,
    validate_gate_coverage,
    write_json,
)

from gate_artifacts import parse_result, parse_ctrf


def run_one(
    *,
    harbor_bin: str,
    task_dir: Path,
    jobs_dir: Path,
    test_id: str,
    expected_cases: list[str],
    agent: str,
    repeat: int,
    stamp: str,
    no_pty: bool,
    trial_timeout_sec: float = 7200,
) -> dict[str, Any]:
    expected = per_test_expected_reward(task_dir, agent)
    job_name = f"pt-{task_dir.name}-{test_id}-{agent}-r{repeat}-{stamp}"
    inner = [
        *shlex.split(harbor_bin),
        "run",
        "-p",
        str(task_dir.resolve()),
        "-a",
        agent,
        "--verifier-env",
        f"TBENCH_TEST_ID={test_id}",
        "-k",
        "1",
        "-n",
        "1",
        "--jobs-dir",
        str(jobs_dir.resolve()),
        "--job-name",
        job_name,
        "--quiet",
        "--yes",
    ]
    command = inner
    if not no_pty and shutil.which("script"):
        command = ["script", "-q", "-e", "-c", shlex.join(inner), "/dev/null"]
    job_dir = jobs_dir / job_name
    if job_dir.exists():
        raise WorkflowError(f"refusing to reuse an existing Harbor job: {job_dir}")
    returncode = None
    launch_error = ""
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            process = subprocess.Popen(command, cwd=REPO_ROOT, stdout=stdout, stderr=stderr,
                                       env=os.environ.copy(), start_new_session=True)
            try:
                returncode = process.wait(timeout=trial_timeout_sec)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)
                if isinstance(exc, KeyboardInterrupt):
                    raise
                launch_error = f"Harbor exceeded local deadline of {trial_timeout_sec:g}s"
                returncode = 124
        except OSError as exc:
            launch_error = f"could not launch Harbor: {exc}"
        tails = []
        for handle in (stdout, stderr):
            size = handle.seek(0, 2)
            handle.seek(max(0, size - 2000))
            tails.append(handle.read().decode("utf-8", errors="replace"))
    exact = job_dir / "result.json"
    result_path = exact if exact.is_file() else None
    reward: float | None = None
    errors = 0
    exception: str | None = None
    ctrf_path: Path | None = None
    executed_cases: list[str] = []
    case_statuses: dict[str, str] = {}
    message = launch_error
    if returncode != 0:
        message = message or f"Harbor exited {returncode}"
    elif result_path is None:
        message = "result.json was not found; terminal text is not accepted as evidence"
    else:
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            reward, errors, exception = parse_result(payload)
            ctrf_path, case_statuses = parse_ctrf(result_path)
            executed_cases = sorted(case_statuses)
            if sorted(executed_cases) != sorted(expected_cases):
                message = (
                    f"selected CTRF cases {executed_cases!r}, expected exactly {expected_cases!r}"
                )
            elif agent == "nop":
                # MASTER_CHECKLIST_TBSCI.md #74: a NOP row counts only as a real assertion
                # failure against do-nothing behavior, never a setup/import/collection error.
                stdout_path = ctrf_path.parent / "test-stdout.txt"
                stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.is_file() else ""
                if not stdout_text:
                    message = "NOP row has no verifier/test-stdout.txt to prove a genuine assertion failure"
                elif infra := nop_infrastructure_errors(stdout_text):
                    message = "NOP failure is infrastructure, not an assertion: " + ", ".join(infra)
        except (OSError, ValueError, TypeError) as exc:
            message = f"could not parse result.json: {exc}"
    passed = (
        not message
        and returncode == 0
        and result_path is not None
        and finite_number(reward)
        and reward == expected
        and errors == 0
        and not exception
        and sorted(executed_cases) == sorted(expected_cases)
        and all(status == ("passed" if agent == "oracle" else "failed") for status in case_statuses.values())
    )
    if not message and not passed:
        message = f"reward/errors mismatch: reward={reward!r}, expected={expected}, errors={errors}"
    if not message:
        message = "result.json matched the required per-test reward"
    return {
        "test_id": test_id,
        "agent": agent,
        "repeat": repeat,
        "expected_reward": expected,
        "reward": reward,
        "errors": errors,
        "exception": exception,
        "expected_cases": expected_cases,
        "executed_cases": executed_cases,
        "case_statuses": case_statuses,
        "result_sha256": f"sha256:{sha256_file(result_path)}" if result_path else None,
        "ctrf_sha256": f"sha256:{sha256_file(ctrf_path)}" if ctrf_path else None,
        "trial_timeout_sec": trial_timeout_sec,
        "ctrf_path": portable_path(ctrf_path) if ctrf_path else None,
        "status": "PASS" if passed else "FAIL",
        "message": message,
        "job_name": job_name,
        "job_dir": portable_path(result_path.parent) if result_path else None,
        "result_path": portable_path(result_path) if result_path else None,
        "command": inner,
        "executed_command": command,
        "exit_code": returncode,
        "stdout_tail": tails[0],
        "stderr_tail": tails[1],
    }


def planned_record(
    task_dir: Path,
    jobs_dir: Path,
    test_id: str,
    expected_cases: list[str],
    agent: str,
    repeat: int,
    stamp: str,
    harbor_bin: str,
) -> dict[str, Any]:
    expected = per_test_expected_reward(task_dir, agent)
    job_name = f"pt-{task_dir.name}-{test_id}-{agent}-r{repeat}-{stamp}"
    return {
        "test_id": test_id,
        "agent": agent,
        "repeat": repeat,
        "expected_reward": expected,
        "reward": None,
        "errors": None,
        "exception": None,
        "expected_cases": expected_cases,
        "executed_cases": [],
        "status": "DRY_RUN",
        "message": "command planned but not executed",
        "job_name": job_name,
        "command": [
            *shlex.split(harbor_bin),
            "run",
            "-p",
            str(task_dir.resolve()),
            "-a",
            agent,
            "--verifier-env",
            f"TBENCH_TEST_ID={test_id}",
            "-k",
            "1",
            "-n",
            "1",
            "--jobs-dir",
            str(jobs_dir.resolve()),
            "--job-name",
            job_name,
            "--quiet",
            "--yes",
        ],
    }


def render(report: dict[str, Any]) -> str:
    lines = [
        f"Per-test Harbor gate: {report['status']}",
        f"Task digest: {report['task_digest']}",
    ]
    for record in report["records"]:
        lines.append(
            f"{record['status']:7s} {record['test_id']}/{record['agent']}/r{record['repeat']}: "
            f"reward={record.get('reward')} expected={record['expected_reward']} errors={record.get('errors')}"
        )
        if record["status"] == "FAIL":
            lines.append(f"  {record['message']}")
    for error in report.get("coverage_errors", []):
        lines.append(f"FAIL coverage: {error}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--agents", default="oracle,nop", help="comma-separated: oracle,nop")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--trial-timeout-sec", type=float, default=7200, help="local deadline for each complete Harbor run")
    parser.add_argument("--only", action="append", default=[], help="run only this manifest test ID; repeatable")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--jobs-dir", type=Path)
    parser.add_argument("--harbor-bin", default="harbor",
                        help="local Harbor executable (Oracle/NOP never go through stb)")
    parser.add_argument("--no-pty", action="store_true")
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="how many Harbor rows to run at the same time (default 1 = the old strictly serial matrix)",
    )
    parser.add_argument(
        "--exclusive-test",
        action="append",
        default=[],
        metavar="ID",
        help="manifest test ID whose rows must run alone, never beside any other row; repeatable",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    task_dir = args.task_dir.resolve()
    if not task_dir.is_dir():
        parser.error(f"task directory not found: {task_dir}")
    if not finite_number(args.trial_timeout_sec) or args.trial_timeout_sec <= 0:
        parser.error("--trial-timeout-sec must be positive and finite")
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    agents = tuple(value.strip() for value in args.agents.split(",") if value.strip())
    if not agents or any(agent not in {"oracle", "nop"} for agent in agents) or len(set(agents)) != len(agents):
        parser.error("--agents must be a unique comma-separated subset of oracle,nop")
    try:
        manifest = load_test_manifest(task_dir)
        all_ids = [entry["id"] for entry in manifest["tests"]]
        current_digest = task_digest(task_dir)
    except (WorkflowError, KeyError, TypeError) as exc:
        print(f"per_test_gate.py: {exc}", file=sys.stderr)
        return 2
    unknown = sorted(set(args.only) - set(all_ids))
    if unknown:
        parser.error(f"unknown --only test IDs: {', '.join(unknown)}")
    unknown_exclusive = sorted(set(args.exclusive_test) - set(all_ids))
    if unknown_exclusive:
        # Fail loudly: silently dropping an unknown ID would let a resource-sensitive
        # test run beside others and quietly corrupt its measurement.
        parser.error(f"unknown --exclusive-test test IDs: {', '.join(unknown_exclusive)}")
    selected_ids = [test_id for test_id in all_ids if not args.only or test_id in set(args.only)]
    harbor_exe = shlex.split(args.harbor_bin)[0] if args.harbor_bin.strip() else ""
    if not args.dry_run and not shutil.which(harbor_exe) and not Path(harbor_exe).is_file():
        print(f"per_test_gate.py: Harbor executable not found: {harbor_exe}", file=sys.stderr)
        return 2
    jobs_dir = args.jobs_dir or REPO_ROOT / "artifacts" / "harbor" / task_dir.name
    output = args.output or REPO_ROOT / "artifacts" / "gates" / task_dir.name / "per-test.json"
    try:
        require_outside_task(task_dir, jobs_dir)
        require_outside_task(task_dir, output)
    except WorkflowError as exc:
        parser.error(str(exc))
    if not args.dry_run:
        jobs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    cases_by_id = {entry["id"]: entry.get("cases", []) for entry in manifest["tests"]}
    records: list[dict[str, Any]] = []
    status = "DRY_RUN" if args.dry_run else "RUNNING"
    report: dict[str, Any] = {
        "schema_version": "1.1",
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task_slug": task_dir.name,
        "task_digest": current_digest,
        "selector_env": manifest.get("selector_env"),
        "selected_test_ids": selected_ids,
        "agents": list(agents),
        "repeat_count": args.repeat,
        "records": records,
    }
    write_json(output, report)

    # The row order is decided here, once, and never depends on completion order: each
    # row owns a pre-allocated slot, so the report is identical whatever --jobs says.
    rows = [
        (test_id, agent, repeat)
        for test_id in selected_ids
        for agent in agents
        for repeat in range(1, args.repeat + 1)
    ]
    slots: list[dict[str, Any] | None] = [None] * len(rows)
    report_lock = threading.Lock()

    def publish() -> None:
        # Caller holds report_lock. Only finished rows are published, so an in-progress
        # report has exactly the shape it had when the matrix was strictly serial.
        report["records"] = [record for record in slots if record is not None]
        write_json(output, report)

    def execute(index: int) -> None:
        test_id, agent, repeat = rows[index]
        if args.dry_run:
            record = planned_record(
                task_dir,
                jobs_dir,
                test_id,
                cases_by_id[test_id],
                agent,
                repeat,
                stamp,
                args.harbor_bin,
            )
        else:
            record = run_one(
                harbor_bin=args.harbor_bin,
                task_dir=task_dir,
                jobs_dir=jobs_dir,
                test_id=test_id,
                expected_cases=cases_by_id[test_id],
                agent=agent,
                repeat=repeat,
                stamp=stamp,
                no_pty=args.no_pty,
                trial_timeout_sec=args.trial_timeout_sec,
            )
        with report_lock:
            slots[index] = record
            publish()

    exclusive_ids = set(args.exclusive_test)
    shared = [index for index, row in enumerate(rows) if row[0] not in exclusive_ids]
    solo = [index for index, row in enumerate(rows) if row[0] in exclusive_ids]
    if args.jobs > 1 and shared:
        # Two phases instead of a shared/exclusive lock: every non-exclusive row goes
        # through the pool, and the --exclusive-test rows run afterwards, one at a time,
        # in this thread. A global lock would not be enough -- a shared row already
        # inside the pool would keep running beside the exclusive row that took it --
        # and draining the pool first is both simpler and provably alone.
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = [pool.submit(execute, index) for index in shared]
            try:
                for future in futures:
                    future.result()
            except BaseException:
                for pending in futures:
                    pending.cancel()
                raise
    else:
        # --jobs 1 (the default) keeps the original strictly serial path: no pool, no
        # worker threads, every row executed inline in manifest order.
        solo = sorted(shared + solo)
        shared = []
    for index in solo:
        execute(index)
    records = [record for record in slots if record is not None]
    report["records"] = records
    report["status"] = "DRY_RUN" if args.dry_run else "PASS"
    if not args.dry_run:
        coverage_errors = validate_gate_coverage(
            report,
            expected_ids=selected_ids,
            required_agents=agents,
            minimum_repeats=args.repeat,
            expected_cases_by_id=cases_by_id,
        )
        if task_digest(task_dir) != current_digest:
            coverage_errors.append("task changed while the per-test matrix was running; rerun all rows")
        if any(record["status"] != "PASS" for record in records):
            coverage_errors.append("one or more Harbor rows failed")
        report["coverage_errors"] = sorted(set(coverage_errors))
        report["status"] = "FAIL" if report["coverage_errors"] else "PASS"
    write_json(output, report)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render(report))
    print(f"Report: {portable_path(output)}")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
