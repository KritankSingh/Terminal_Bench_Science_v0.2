"""Validate raw Harbor/CTRF artifacts, rather than trusting report summaries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common import WorkflowError, finite_number, load_json, resolve_recorded_path, sha256_file


def parse_result(payload: dict[str, Any]) -> tuple[float | None, int, str | None]:
    if not isinstance(payload, dict):
        raise WorkflowError("Harbor result must be an object")
    stats = payload.get("stats")
    if isinstance(stats, dict):
        evals = stats.get("evals")
        if not isinstance(evals, dict) or len(evals) != 1:
            raise WorkflowError("per-test result must contain exactly one evaluation")
        evaluation = next(iter(evals.values()))
        if not isinstance(evaluation, dict):
            raise WorkflowError("Harbor evaluation must be an object")
        counts = [stats.get("n_errored_trials", 0), evaluation.get("n_errors", 0)]
        if any(type(value) is not int or value < 0 for value in counts):
            raise WorkflowError("invalid Harbor error count")
        errors = max(counts)
        exception_stats = evaluation.get("exception_stats")
        exception = str(exception_stats) if exception_stats else None
        if isinstance(exception_stats, dict) and exception_stats:
            exception = ", ".join(sorted(exception_stats))
        if not errors and not exception:
            if type(evaluation.get("n_trials")) is not int or evaluation["n_trials"] != 1:
                raise WorkflowError("per-test result must contain exactly one completed trial")
            for key in ("n_total_trials", "n_completed_trials"):
                if key in stats and (type(stats[key]) is not int or stats[key] != 1):
                    raise WorkflowError(f"Harbor {key} must be 1")
        metrics = evaluation.get("metrics", [])
        means = [m["mean"] for m in metrics if isinstance(m, dict) and "mean" in m] if isinstance(metrics, list) else []
        if len(means) != 1 or not finite_number(means[0]):
            raise WorkflowError("expected exactly one finite Harbor reward mean")
        reward_stats = evaluation.get("reward_stats", {}).get("reward") if isinstance(evaluation.get("reward_stats", {}), dict) else None
        if reward_stats is not None and not errors and not exception:
            if not isinstance(reward_stats, dict) or len(reward_stats) != 1:
                raise WorkflowError("reward distribution must describe one trial")
            value, trials = next(iter(reward_stats.items()))
            count = len(trials) if isinstance(trials, list) else trials
            if type(count) is not int or count != 1 or float(value) != means[0]:
                raise WorkflowError("reward distribution disagrees with single-trial mean")
        return float(means[0]), errors, exception
    verifier = payload.get("verifier_result")
    rewards = verifier.get("rewards") if isinstance(verifier, dict) else None
    reward = rewards.get("reward") if isinstance(rewards, dict) else None
    exception = payload.get("exception_info")
    if reward is not None and not finite_number(reward):
        raise WorkflowError("trial reward must be finite and numeric")
    return reward, 1 if exception else 0, str(exception) if exception else None


def read_ctrf(path: Path) -> dict[str, str]:
    payload = load_json(path)
    results = payload.get("results") if isinstance(payload, dict) else None
    tests = results.get("tests") if isinstance(results, dict) else None
    if not isinstance(tests, list) or not tests:
        raise WorkflowError("CTRF results.tests must be a nonempty list")
    if results.get("collection_errors", 0):
        raise WorkflowError("CTRF reports a collection/setup error")
    cases: dict[str, str] = {}
    for item in tests:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"]:
            raise WorkflowError("every CTRF entry must have a nonempty name")
        if item["name"] in cases:
            raise WorkflowError(f"duplicate CTRF case: {item['name']}")
        if item.get("status") not in {"passed", "failed"}:
            raise WorkflowError(f"CTRF case did not execute normally: {item['name']}: {item.get('status')!r}")
        if item.get("raw_status") in {"setup_failed", "teardown_failed"}:
            raise WorkflowError(f"CTRF reports infrastructure/setup failure: {item['name']}")
        cases[item["name"]] = item["status"]
    return cases


def parse_ctrf(result_path: Path) -> tuple[Path, dict[str, str]]:
    candidates = sorted(result_path.parent.rglob("verifier/ctrf.json"))
    if len(candidates) != 1:
        raise WorkflowError(f"expected one trial CTRF artifact, found {len(candidates)}")
    return candidates[0], read_ctrf(candidates[0])


def validate_raw_records(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    records = report.get("records")
    if not isinstance(records, list):
        return ["gate records must be a list"]
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue  # Schema validation reports this separately.
        try:
            paths = {}
            for kind in ("result", "ctrf"):
                value = record.get(f"{kind}_path")
                if not isinstance(value, str) or not value:
                    raise WorkflowError(f"missing {kind} artifact path")
                path = resolve_recorded_path(value).resolve()
                if not path.is_file():
                    raise WorkflowError(f"missing raw artifact: {path}")
                if record.get(f"{kind}_sha256") != f"sha256:{sha256_file(path)}":
                    raise WorkflowError(f"raw {kind} artifact changed after the trial")
                paths[kind] = path
            if not paths["ctrf"].is_relative_to(paths["result"].parent):
                raise WorkflowError("CTRF artifact is outside its recorded job")
            reward, count, exception = parse_result(load_json(paths["result"]))
            if (reward, count, exception) != (record.get("reward"), record.get("errors"), record.get("exception")):
                raise WorkflowError("raw Harbor result disagrees with the gate summary")
            ctrf_path, cases = parse_ctrf(paths["result"])
            if ctrf_path.resolve() != paths["ctrf"] or cases != record.get("case_statuses"):
                raise WorkflowError("raw CTRF disagrees with the gate summary")
            if sorted(cases) != record.get("executed_cases"):
                raise WorkflowError("raw CTRF case list disagrees with the gate summary")
        except (WorkflowError, OSError, ValueError, TypeError) as exc:
            errors.append(f"raw evidence row {index}: {exc}")
    return errors
