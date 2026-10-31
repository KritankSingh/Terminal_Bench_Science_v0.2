#!/usr/bin/env python3
"""Summarize Step 2b/3a gate evidence (per-test matrix, seal, NC jobs) as markdown.

Reads the per-test gate report (default: the newest artifacts/gates/<slug>/per-test-*.json
whose task_digest matches the current task), the Step 2b seal
(artifacts/gates/<slug>/step2b.json), and every nc-*/ Harbor job directory under the
evidence directory (result.json, <trial>/verifier/reward.txt, <trial>/verifier/ctrf.json,
<job>.exit-codes.txt), then prints:

- a header with the task digest, evidence path and seal status;
- the per-test matrix table (test id / agent / reward / case -> status / gate row / trial dir);
- the NC table (job / trial id / Harbor exit / reward / failing CTRF cases / verdict);
- a one-line overall verdict.

With --write the same text is inserted as (or replaces) the section
`## Gate results — <digest>` in authoring/<slug>/controls.md (created from
authoring/_templates/controls.md when missing). Only the section with the identical
digest heading is replaced; every other section is left untouched.

Exit status: 0 when the overall verdict is PASS, 1 otherwise, 2 on usage errors.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import (
    REPO_ROOT,
    WorkflowError,
    finite_number,
    load_json,
    load_test_manifest,
    portable_path,
    task_digest,
)
from evidence import check_seal
from gate_artifacts import parse_result, read_ctrf


NC_JOB_RE = re.compile(r"^nc-[0-9]+[a-z]*$")
INVESTIGATE = "NOT REJECTED — INVESTIGATE"
PLAN_ROW_RE = re.compile(r"^\|\s*`?(NC-\d+[a-z]?)\b")
CASE_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_])test_[A-Za-z0-9_]+(?![A-Za-z0-9_]|\.[A-Za-z])")


def short_case(name: str) -> str:
    """Drop the `file::` prefix from a CTRF case name."""
    return name.rsplit("::", 1)[-1]


def md_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def md_table(headers: list[str], rows: list[list[Any]], align_right: set[int] = frozenset()) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("---:" if i in align_right else "---" for i in range(len(headers))) + "|")
    for row in rows:
        lines.append("| " + " | ".join(md_cell(cell) for cell in row) + " |")
    return lines


def report_created_at(path: Path) -> float:
    try:
        payload = load_json(path)
        value = payload.get("created_at") if isinstance(payload, dict) else None
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (WorkflowError, ValueError):
        pass
    return path.stat().st_mtime


def find_gate_report(slug: str, digest: str) -> tuple[Path | None, list[Path]]:
    gates = REPO_ROOT / "artifacts" / "gates" / slug
    candidates = sorted(gates.glob("per-test-*.json")) if gates.is_dir() else []
    matching: list[Path] = []
    for path in candidates:
        try:
            payload = load_json(path)
        except WorkflowError:
            continue
        if isinstance(payload, dict) and payload.get("task_digest") == digest:
            matching.append(path)
    if not matching:
        return None, candidates
    return max(matching, key=report_created_at), candidates


def read_plan(slug: str) -> dict[str, set[str]]:
    """Planned failing CTRF cases per control, from the plan table rows of controls.md.

    Rows are `| NC-XX ... |` table lines outside generated `## Gate results` sections;
    every `test_*` token in the row counts as a planned case (module stems are ignored).
    """
    path = REPO_ROOT / "authoring" / slug / "controls.md"
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {}
    text = re.sub(r"(?ms)^## Gate results\b.*?(?=^## (?!#)|\Z)", "", text)
    plan: dict[str, set[str]] = {}
    for line in text.splitlines():
        match = PLAN_ROW_RE.match(line)
        if not match:
            continue
        job = "nc-" + match.group(1)[3:].lower()
        tokens = set(CASE_TOKEN_RE.findall(line))
        plan.setdefault(job, set()).update(tokens)
    return plan


def per_test_rows(report: dict[str, Any] | None) -> list[list[Any]]:
    rows: list[list[Any]] = []
    if not report:
        return rows
    for record in report.get("records", []) or []:
        if not isinstance(record, dict):
            continue
        statuses = record.get("case_statuses") or {}
        if statuses:
            cases = "; ".join(f"`{short_case(case)}` → {status}" for case, status in sorted(statuses.items()))
        else:
            cases = "(no CTRF cases recorded)"
        trial_dir = ""
        ctrf_path = record.get("ctrf_path")
        if isinstance(ctrf_path, str) and ctrf_path:
            trial_dir = Path(ctrf_path).parent.parent.as_posix()
        elif isinstance(record.get("job_dir"), str):
            trial_dir = record["job_dir"]
        reward = record.get("reward")
        rows.append([
            record.get("test_id"),
            record.get("agent"),
            reward if reward is not None else "—",
            cases,
            record.get("status"),
            f"`{trial_dir}`" if trial_dir else "—",
        ])
    return rows


def read_exit_codes(path: Path) -> dict[str, str]:
    codes: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                codes[key.strip()] = value.strip()
    except OSError:
        pass
    return codes


def analyze_nc_job(job_dir: Path, evidence: Path) -> dict[str, Any]:
    job = job_dir.name
    info: dict[str, Any] = {
        "job": job,
        "trial": None,
        "harbor_exit": None,
        "reward": None,
        "reward_txt": None,
        "exception": None,
        "failing": [],
        "passing": [],
        "notes": [],
    }
    codes = read_exit_codes(evidence / f"{job}.exit-codes.txt")
    if "harbor" in codes:
        info["harbor_exit"] = codes["harbor"]
    else:
        info["notes"].append("no exit-codes file")

    trial_dirs = sorted(p for p in job_dir.iterdir()
                        if p.is_dir() and ((p / "config.json").is_file() or (p / "verifier").is_dir()))
    if len(trial_dirs) == 1:
        info["trial"] = trial_dirs[0].name
    elif trial_dirs:
        info["trial"] = ", ".join(p.name for p in trial_dirs)
        info["notes"].append(f"{len(trial_dirs)} trial dirs (expected 1)")
    else:
        info["notes"].append("no trial dir")

    result_path = job_dir / "result.json"
    if result_path.is_file():
        try:
            reward, errors, exception = parse_result(load_json(result_path))
            info["reward"] = reward
            if errors or exception:
                info["exception"] = exception or f"{errors} errored trial(s)"
        except (WorkflowError, TypeError, ValueError) as exc:
            info["notes"].append(f"job result.json: {exc}")
    else:
        info["notes"].append("no job result.json")

    if len(trial_dirs) == 1:
        trial = trial_dirs[0]
        trial_result = trial / "result.json"
        if trial_result.is_file():
            try:
                payload = load_json(trial_result)
                if isinstance(payload, dict) and payload.get("exception_info"):
                    exc_info = payload["exception_info"]
                    name = exc_info.get("exception_type") if isinstance(exc_info, dict) else None
                    info["exception"] = info["exception"] or (name or str(exc_info)[:120])
                if info["reward"] is None and isinstance(payload, dict):
                    rewards = (payload.get("verifier_result") or {}).get("rewards") or {}
                    if finite_number(rewards.get("reward")):
                        info["reward"] = float(rewards["reward"])
            except WorkflowError as exc:
                info["notes"].append(f"trial result.json: {exc}")
        reward_txt = trial / "verifier" / "reward.txt"
        if reward_txt.is_file():
            try:
                info["reward_txt"] = reward_txt.read_text(encoding="utf-8").strip()
            except OSError:
                pass
        else:
            info["notes"].append("no verifier/reward.txt")
        ctrf = trial / "verifier" / "ctrf.json"
        if ctrf.is_file():
            try:
                statuses = read_ctrf(ctrf)
                info["failing"] = sorted(short_case(c) for c, s in statuses.items() if s == "failed")
                info["passing"] = sorted(short_case(c) for c, s in statuses.items() if s == "passed")
            except WorkflowError as exc:
                info["notes"].append(f"ctrf.json: {exc}")
        else:
            info["notes"].append("no verifier/ctrf.json")

    if info["reward_txt"] is not None and info["reward"] is not None:
        try:
            if float(info["reward_txt"]) != float(info["reward"]):
                info["notes"].append(f"reward.txt={info['reward_txt']} disagrees with result.json")
        except ValueError:
            info["notes"].append(f"reward.txt is not numeric: {info['reward_txt']!r}")

    rejected = (
        finite_number(info["reward"]) and info["reward"] == 0.0
        and not info["exception"]
        and info["harbor_exit"] == "0"
    )
    info["verdict"] = "REJECTED" if rejected else INVESTIGATE
    if not rejected:
        why = []
        if info["reward"] is None:
            why.append("no reward")
        elif info["reward"] != 0.0:
            why.append(f"reward {info['reward']}")
        if info["exception"]:
            why.append(f"exception: {info['exception']}")
        if info["harbor_exit"] != "0":
            why.append(f"harbor exit {info['harbor_exit']}")
        info["why"] = "; ".join(why + info["notes"])
    return info


def nc_rows(evidence: Path, plan: dict[str, set[str]]) -> tuple[list[list[Any]], list[dict[str, Any]]]:
    infos: list[dict[str, Any]] = []
    for job_dir in sorted(p for p in evidence.iterdir() if p.is_dir() and NC_JOB_RE.match(p.name)):
        info = analyze_nc_job(job_dir, evidence)
        planned = plan.get(info["job"], set())
        info["planned"] = sorted(planned)
        info["off_plan"] = bool(planned) and info["verdict"] == "REJECTED" and not (planned & set(info["failing"]))
        infos.append(info)
    rows: list[list[Any]] = []
    for info in infos:
        failing = ", ".join(f"`{c}`" for c in info["failing"]) if info["failing"] else "(none)"
        if info["passing"]:
            failing += " (passed: " + ", ".join(f"`{c}`" for c in info["passing"]) + ")"
        reward = info["reward"]
        reward_cell = "—" if reward is None else (int(reward) if float(reward).is_integer() else reward)
        verdict = info["verdict"]
        if verdict != "REJECTED" and info.get("why"):
            verdict += f" ({info['why']})"
        elif info["off_plan"]:
            verdict += " — OFF PLAN (planned " + ", ".join(f"`{c}`" for c in info["planned"]) + " did not fail)"
        elif info["notes"]:
            verdict += " (" + "; ".join(info["notes"]) + ")"
        elif not info["planned"]:
            verdict += " (no planned case in controls.md)"
        rows.append([
            info["job"],
            f"`{info['trial']}`" if info["trial"] else "—",
            info["harbor_exit"] if info["harbor_exit"] is not None else "—",
            reward_cell,
            failing,
            verdict,
        ])
    return rows, infos


def build_report(task_dir: Path, evidence: Path, gate_report: Path | None) -> tuple[list[str], bool, str]:
    slug = task_dir.name
    digest = task_digest(task_dir)
    seal_path = REPO_ROOT / "artifacts" / "gates" / slug / "step2b.json"
    seal_errors = check_seal(task_dir, seal_path) if seal_path.is_file() else [f"seal not found: {portable_path(seal_path)}"]
    seal_status = "PASS" if not seal_errors else "FAIL"

    if gate_report is None:
        gate_report, candidates = find_gate_report(slug, digest)
    report: dict[str, Any] | None = None
    report_note = ""
    if gate_report is not None and gate_report.is_file():
        try:
            loaded = load_json(gate_report)
            report = loaded if isinstance(loaded, dict) else None
        except WorkflowError as exc:
            report_note = str(exc)
        if report is not None and report.get("task_digest") != digest:
            report_note = "gate report digest does not match the current task"
    else:
        report_note = "no per-test report for the current digest under artifacts/gates/" + slug

    manifest_note = ""
    try:
        manifest = load_test_manifest(task_dir)
        expected_pairs = {(entry["id"], agent) for entry in manifest["tests"] for agent in ("oracle", "nop")}
    except WorkflowError as exc:
        manifest_note = str(exc)
        expected_pairs = set()

    evidence_digest = None
    digest_file = evidence / "task-digest.txt"
    if digest_file.is_file():
        try:
            evidence_digest = digest_file.read_text(encoding="utf-8").strip()
        except OSError:
            evidence_digest = None

    lines: list[str] = []
    lines.append(f"## Gate results — {digest}")
    lines.append("")
    lines.append(f"- Task: `{portable_path(task_dir)}`")
    lines.append(f"- Task digest: `{digest}`")
    if evidence_digest and evidence_digest != digest:
        lines.append(f"- **Evidence digest differs**: `{evidence_digest}` (evidence is stale for this task)")
    lines.append(f"- Evidence: `{portable_path(evidence)}`")
    lines.append(f"- Seal: `{portable_path(seal_path)}` — **{seal_status}**"
                 + ("" if not seal_errors else " (" + "; ".join(seal_errors) + ")"))
    if report is not None:
        lines.append(f"- Per-test report: `{portable_path(gate_report)}` — status **{report.get('status')}**"
                     + (f" ({report_note})" if report_note else ""))
    else:
        lines.append(f"- Per-test report: **missing** ({report_note})")
    if manifest_note:
        lines.append(f"- Manifest: {manifest_note}")
    lines.append(f"- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} by scripts/controls_report.py")
    lines.append("")

    lines.append("### Per-test matrix (stock agents, `--verifier-env TBENCH_TEST_ID=<id>`)")
    lines.append("")
    rows = per_test_rows(report)
    matrix_ok = False
    if rows:
        lines.extend(md_table(["Test ID", "Agent", "Reward", "CTRF case → status", "Gate row", "Trial dir"], rows, {2}))
        seen_pairs = {(row[0], row[1]) for row in rows}
        missing = sorted(expected_pairs - seen_pairs)
        all_pass = all(row[4] == "PASS" for row in rows)
        matrix_ok = bool(report) and report.get("status") == "PASS" and all_pass and not missing and not report_note
        if missing:
            lines.append("")
            lines.append("Missing rows: " + ", ".join(f"{t}/{a}" for t, a in missing))
        coverage = report.get("coverage_errors") if report else None
        if coverage:
            lines.append("")
            lines.append("Coverage errors: " + "; ".join(str(e) for e in coverage))
    else:
        lines.append("_No per-test rows available._")
    lines.append("")

    lines.append("### Negative controls (staged copies, `RecordingOracle` runs the control `solve.sh`)")
    lines.append("")
    plan = read_plan(slug)
    nc_table, infos = nc_rows(evidence, plan)
    if nc_table:
        lines.extend(md_table(["Job", "Trial", "Harbor exit", "Reward", "Failing CTRF cases", "Verdict"], nc_table, {3}))
    else:
        lines.append("_No nc-*/ job directories under the evidence path._")
    lines.append("")

    nc_ok = bool(infos) and all(info["verdict"] == "REJECTED" and not info["off_plan"] for info in infos)
    problems: list[str] = []
    if seal_status != "PASS":
        problems.append("seal not PASS")
    if not matrix_ok:
        problems.append("per-test matrix incomplete or not PASS")
    if not infos:
        problems.append("no NC jobs")
    else:
        bad = [info["job"] for info in infos if info["verdict"] != "REJECTED"]
        if bad:
            problems.append("NC not rejected: " + ", ".join(bad))
        off = [info["job"] for info in infos if info["off_plan"]]
        if off:
            problems.append("NC rejected through a case other than the planned one: " + ", ".join(off))
    overall = seal_status == "PASS" and matrix_ok and nc_ok
    cited = sum(1 for info in infos if info["planned"])
    if not plan:
        plan_note = " (no plan table found in controls.md)"
    elif cited == len(infos):
        plan_note = " (all through a planned case)"
    elif cited == 0:
        plan_note = " (none had a citable planned case in controls.md — verify the plan cells name the CTRF case)"
    else:
        plan_note = (f" ({cited}/{len(infos)} checked against a planned case; "
                     f"{len(infos) - cited} had no citable case in controls.md)")
    verdict_line = (
        f"**Overall verdict: {'PASS' if overall else 'FAIL'}** — "
        + (f"seal PASS, {len(rows)} per-test rows PASS, {len(infos)} NC job(s) rejected with no Harbor exception"
           + plan_note
           if overall else "; ".join(problems))
    )
    lines.append(verdict_line)
    return lines, overall, digest


def write_section(slug: str, digest: str, section_lines: list[str]) -> Path:
    path = REPO_ROOT / "authoring" / slug / "controls.md"
    template = REPO_ROOT / "authoring" / "_templates" / "controls.md"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        text = template.read_text(encoding="utf-8") if template.is_file() else "# Negative-control evidence — <task-name>\n"
        text = text.replace("<task-name>", slug)
        path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    heading = f"## Gate results — {digest}"
    if section_lines and section_lines[0].startswith("## Gate results — "):
        section_lines = [heading, *section_lines[1:]]
    else:
        section_lines = [heading, "", *section_lines]
    section = "\n".join(section_lines).rstrip("\n") + "\n"
    start = next((i for i, line in enumerate(lines) if line.strip() == heading), None)
    if start is None:
        # Insert right after the template's bare `## Gate results` section when present,
        # otherwise append at the end of the file.
        bare = next((i for i, line in enumerate(lines) if re.match(r"^## Gate results\s*$", line)), None)
        if bare is None:
            body = original.rstrip("\n") + "\n\n" + section if original.strip() else section
        else:
            end = len(lines)
            for j in range(bare + 1, len(lines)):
                if re.match(r"^## (?!#)", lines[j]):
                    end = j
                    break
            before = "\n".join(lines[:end]).rstrip("\n")
            after = "\n".join(lines[end:])
            body = before + "\n\n" + section + ("\n" + after if after.strip() else "")
    else:
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if re.match(r"^## (?!#)", lines[j]):
                end = j
                break
        before = "\n".join(lines[:start]).rstrip("\n")
        after = "\n".join(lines[end:])
        body = (before + "\n\n" if before else "") + section + ("\n" + after if after.strip() else "")
        if original.endswith("\n") and not body.endswith("\n"):
            body += "\n"
    path.write_text(body, encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task-dir", type=Path, required=True, help="tasks/<task>")
    parser.add_argument("--evidence", type=Path, required=True, help="evidence OUT directory holding nc-*/ job dirs")
    parser.add_argument("--gate-report", type=Path, help="per-test gate report JSON (default: newest matching digest)")
    parser.add_argument("--write", action="store_true", help="insert/replace the section in authoring/<slug>/controls.md")
    args = parser.parse_args(argv)

    task_dir = args.task_dir.resolve()
    evidence = args.evidence.resolve()
    if not task_dir.is_dir():
        parser.error(f"task directory not found: {task_dir}")
    if not evidence.is_dir():
        parser.error(f"evidence directory not found: {evidence}")
    gate_report = args.gate_report.resolve() if args.gate_report else None
    if gate_report is not None and not gate_report.is_file():
        parser.error(f"gate report not found: {gate_report}")
    try:
        lines, overall, digest = build_report(task_dir, evidence, gate_report)
    except WorkflowError as exc:
        print(f"controls_report.py: {exc}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    if args.write:
        path = write_section(task_dir.name, digest, lines)
        print(f"\nWrote section `## Gate results — {digest}` to {portable_path(path)}", file=sys.stderr)
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
