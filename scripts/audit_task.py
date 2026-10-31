#!/usr/bin/env python3
"""Run the bundled TB-Science auditor (tools/final-tbsci-audit-master/) the way the workspace gates need it.

The auditor grades a delivery against MASTER_CHECKLIST_TBSCI.md. A task is built to clear
it from the first file, not only at the end:

  tree    tasks/<task>          Step 2b gate (and any time while building). Stages the task in
                                delivery layout -- <slug>/<slug>/{5 members} + <slug>/rubric.txt --
                                and runs tbsci_static_screen.py. Every BLOCKER/MAJOR/MINOR finding
                                fails, except the ones that can only be satisfied by Step 3c/4
                                evidence (no oracle-nop-evidence/, trajectories/ or SUMMARY yet).
                                LEADs are printed for Step 3b to answer.
  package <zip>                 Step 4, on the candidate ZIP: tbsci_static_screen.py and
                                trial_evidence.py. Zero findings of any severity, zero trial
                                flags/errors, no stale evidence.
  verdict <zip>                 Step 4, before promotion: the auditor's own judged review of that
                                ZIP (tools/final-tbsci-audit-master/audit/<slug>/latest) must lint
                                clean with the closing line "Ready to Submit", and its task digest
                                must equal a fresh screen of the ZIP -- the review was of THIS ZIP.

Exit 0 = clean. Needs Python 3.11+ (the auditor parses task.toml with tomllib).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from common import REPO_ROOT, WorkflowError

AUDITOR = REPO_ROOT / "tools" / "final-tbsci-audit-master"
SCREEN = AUDITOR / "scripts" / "tbsci_static_screen.py"
TRIAL = AUDITOR / "scripts" / "trial_evidence.py"
LINT = AUDITOR / "scripts" / "verdict_lint.py"
TASK_MEMBERS = ("instruction.md", "task.toml", "environment", "solution", "tests")
SEVERE = ("BLOCKER", "MAJOR", "MINOR")
# Satisfiable only once Step 3c evidence exists and Step 4 lays it out; everything else the
# auditor says about a task is a construction rule and must hold from Step 2b on.
PACKAGE_ONLY = frozenset({"T3-CONTROLS", "T3-TRAJ", "T3-SUMMARY"})
PACKAGE_MEMBERS = frozenset({"oracle-nop-evidence", "trajectories", "trajectories/SUMMARY.txt"})


def package_only(finding: dict) -> bool:
    if finding.get("code") in PACKAGE_ONLY:
        return True
    return finding.get("code") == "T3-LAYOUT" and str(finding.get("where", "")).rstrip("/") in PACKAGE_MEMBERS


def _python() -> str:
    if sys.version_info < (3, 11):
        raise WorkflowError("the auditor needs Python 3.11+ (tomllib); activate the workspace .venv")
    return sys.executable


def _run_json(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"{Path(cmd[1]).name} did not return JSON (exit {proc.returncode}): "
                            f"{(proc.stderr or proc.stdout).strip()[:300]}") from exc
    if isinstance(data, dict) and "error" in data and "findings" not in data and "flags" not in data:
        raise WorkflowError(f"{Path(cmd[1]).name}: {data['error']}")
    return data


def screen(target: Path, slug: str | None = None) -> dict:
    cmd = [_python(), str(SCREEN), "--task", str(target), "--profile", "terminus"]
    if slug:
        cmd += ["--slug", slug]
    return _run_json(cmd)


def _describe(finding: dict) -> str:
    master = f" [{finding['master']}]" if finding.get("master") else ""
    return f"{finding['severity']} {finding['code']}{master} {finding.get('where', '')}: {finding.get('evidence', '')}"


def audit_tree(task: Path) -> tuple[list[str], list[str], dict]:
    """(failures, leads, raw screen) for an authoring tree staged in delivery layout."""
    task = task.resolve()
    slug = task.name
    with tempfile.TemporaryDirectory(prefix="audit-tree-") as scratch:
        root = Path(scratch) / slug
        inner = root / slug
        inner.mkdir(parents=True)
        for name in TASK_MEMBERS:
            source = task / name
            if source.is_dir():
                shutil.copytree(source, inner / name, symlinks=True,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
            elif source.is_file():
                shutil.copy2(source, inner / name)
        if (task / "rubric.txt").is_file():
            shutil.copy2(task / "rubric.txt", root / "rubric.txt")
        data = screen(root, slug)
    failures, leads = [], []
    for finding in data.get("findings", []):
        if finding.get("severity") in SEVERE and not package_only(finding):
            failures.append(_describe(finding))
        elif finding.get("severity") == "LEAD":
            leads.append(_describe(finding))
    for lead in data.get("leads", []):
        if isinstance(lead, dict):
            leads.append(_describe(lead))
    return failures, list(dict.fromkeys(leads)), data


def audit_package(zip_path: Path) -> tuple[list[str], list[str], dict]:
    """(failures, leads, raw) for a delivery ZIP: screen + trial evidence, zero tolerance."""
    zip_path = zip_path.resolve()
    data = screen(zip_path)
    failures = [_describe(f) for f in data.get("findings", []) if f.get("severity") in SEVERE]
    leads = [_describe(f) for f in data.get("findings", []) if f.get("severity") == "LEAD"]
    leads += [_describe(lead) for lead in data.get("leads", []) if isinstance(lead, dict)]
    with tempfile.TemporaryDirectory(prefix="audit-package-") as scratch:
        with zipfile.ZipFile(zip_path) as package:
            package.extractall(scratch)
        tops = [path for path in Path(scratch).iterdir() if path.is_dir()]
        if len(tops) != 1:
            raise WorkflowError(f"{zip_path.name}: expected one top-level <task-slug>/ folder")
        root = tops[0]
        trial = _run_json([_python(), str(TRIAL), "--runs", str(root / "trajectories"),
                           str(root / "oracle-nop-evidence"), "--task", str(root / root.name),
                           "--profile", "terminus"])
    for flag in trial.get("flags", []) or []:
        if flag.startswith("0% solved"):
            # A measured 0/5 ships (AGENTS.md rule 10). The per-failure reasons this flag asks
            # for are the Step 3c report's trajectory audit (Master #84), so it is a lead.
            leads.append(f"trial_evidence lead: {flag}")
            continue
        failures.append(f"trial_evidence flag: {flag}")
    for error in trial.get("errors", []) or []:
        failures.append(f"trial_evidence error: {error}")
    if trial.get("stale_evidence"):
        failures.append(f"trial_evidence: stale evidence {trial['stale_evidence']}")
    for lead in trial.get("leads", []) or []:
        leads.append(f"trial_evidence lead: {lead}")
    return list(dict.fromkeys(failures)), list(dict.fromkeys(leads)), {"screen": data, "trial_evidence": trial}


def audit_verdict(zip_path: Path) -> list[str]:
    """The auditor's judged review of this exact ZIP must be clean and 'Ready to Submit'."""
    zip_path = zip_path.resolve()
    fresh = screen(zip_path)
    slug = fresh.get("slug") or zip_path.stem
    run = AUDITOR / "audit" / slug / "latest"
    errors: list[str] = []
    if not (run / "verdict.json").is_file():
        return [f"no auditor review for {slug}: run tools/final-tbsci-audit-master/scripts/review.sh "
                f"extract {zip_path} && review.sh audit {slug}, judge it per SKILL.md, then review.sh lint {slug}"]
    proc = subprocess.run([_python(), str(LINT), str(run)], capture_output=True, text=True)
    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        errors.append(f"verdict_lint failed for {run.resolve().relative_to(REPO_ROOT)}: {output[-600:]}")
    elif "Ready to Submit" not in output:
        errors.append(f"auditor closing line is not Ready to Submit: {output.splitlines()[-1] if output else ''}")
    # Clean means clean: a lint warning (unfilled manual probes, a task that changed after
    # the audit) is a review that is not finished.
    for line in output.splitlines():
        if line.strip().startswith("warn"):
            errors.append(f"auditor review warning: {line.strip()[4:].strip()}")
    errors += _extracted_matches_zip(slug, zip_path)
    try:
        verdict = json.loads((run / "verdict.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return errors + [f"cannot read verdict.json: {exc}"]
    if verdict.get("verdict") != "ready":
        errors.append(f"auditor verdict is {verdict.get('verdict')!r}, not 'ready'")
    counts = verdict.get("counts") or {}
    open_counts = {key: counts.get(key) for key in ("blocker", "major", "minor") if counts.get(key)}
    if open_counts:
        errors.append(f"auditor review has open findings {open_counts}; nothing ships with an open finding")
    if verdict.get("task_digest") != fresh.get("task_digest"):
        errors.append("the auditor review was of a different package: its task_digest "
                      f"{str(verdict.get('task_digest'))[:16]} != this ZIP's {str(fresh.get('task_digest'))[:16]}; "
                      "re-extract this ZIP and re-audit it")
    return errors


def _extracted_matches_zip(slug: str, zip_path: Path) -> list[str]:
    """The auditor reviewed exactly this ZIP: its extracted copy is byte-identical, evidence included."""
    import hashlib

    extracted = AUDITOR / "extracted" / slug
    if not extracted.is_dir():
        return [f"the auditor has no extracted copy of {slug}; run review.sh extract {zip_path}"]
    on_disk = {path.relative_to(extracted).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in extracted.rglob("*") if path.is_file()}
    in_zip = {}
    with zipfile.ZipFile(zip_path) as package:
        for info in package.infolist():
            if info.is_dir():
                continue
            relative = info.filename.split("/", 1)[1] if "/" in info.filename else info.filename
            in_zip[relative] = hashlib.sha256(package.read(info)).hexdigest()
    if on_disk != in_zip:
        changed = sorted(name for name in set(on_disk) | set(in_zip) if on_disk.get(name) != in_zip.get(name))
        return [f"the auditor reviewed a different package than {zip_path.name} ({len(changed)} file(s) differ, e.g. "
                f"{changed[:3]}); re-extract this ZIP, re-audit and re-judge it"]
    return []


def _print(title: str, failures: list[str], leads: list[str]) -> None:
    print(f"{title}: {'FAIL' if failures else 'PASS'} ({len(failures)} finding(s), {len(leads)} lead(s))")
    for failure in failures:
        print(f"FAIL {failure}")
    for lead in leads:
        print(f"LEAD {lead}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    tree = sub.add_parser("tree")
    tree.add_argument("task_dir", type=Path)
    tree.add_argument("--json-out", type=Path)
    package = sub.add_parser("package")
    package.add_argument("zip", type=Path)
    package.add_argument("--json-out", type=Path)
    verdict = sub.add_parser("verdict")
    verdict.add_argument("zip", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "tree":
            failures, leads, raw = audit_tree(args.task_dir)
            _print(f"Auditor (tree) {args.task_dir.resolve().name}", failures, leads)
        elif args.command == "package":
            failures, leads, raw = audit_package(args.zip)
            _print(f"Auditor (package) {args.zip.name}", failures, leads)
        else:
            failures = audit_verdict(args.zip)
            print(f"Auditor (verdict) {args.zip.name}: {'FAIL' if failures else 'PASS'}")
            for failure in failures:
                print(f"FAIL {failure}")
            return 1 if failures else 0
    except (OSError, WorkflowError, zipfile.BadZipFile) as exc:
        print(f"Auditor: FAIL\n- {exc}")
        return 1
    if getattr(args, "json_out", None):
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps({"failures": failures, "leads": leads, "raw": raw}, indent=1) + "\n",
                                 encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
