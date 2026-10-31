#!/usr/bin/env python3
"""Keep the per-task MASTER_CHECKLIST_TBSCI.md record: every check answered with evidence.

MASTER_CHECKLIST_TBSCI.md (repo root) is the source of truth for Terminal-Bench Science
delivery. A task may only be packaged once every check in it has been performed against
the task on disk and answered. This script keeps that answer sheet honest:

  init   tasks/<task>                 write authoring/<task>/master-checklist.md, one
                                      PENDING line per master check, bound to the
                                      current task digest
  auto   tasks/<task>                 print the mechanical findings (task_check.py,
                                      grouped by master number) and review leads the
                                      reviewer must resolve, check by check
  check  tasks/<task> --stage review  Step 3b: every check answered except those
                                      whose single verdict reads the five packaged
                                      runs (POST_TRIAL) plus #96 and #97. A
                                      PASS/N/A/AUTO/FAIL on a POST_TRIAL line is
                                      rejected: that verdict is recorded at Step 4.
  check  tasks/<task> --stage package Step 4: every check answered, zero FAIL
                                      or NOT VERIFIED

Record line format (one per check, in master order):

  #<N> | <VERDICT> | <evidence>

VERDICT is PASS (evidence: file:line, quoted text or command output), N/A (reason;
conditional checks and the nine merged placeholders), AUTO (only for checks the
scripts enforce mechanically -- see MECHANICAL), FAIL (a finding; blocks),
NOT VERIFIED (a probe or record the check needs has not been produced; blocks
shipping exactly as FAIL does), or PENDING (not yet walked). There is no
severity that ships: one FAIL or NOT VERIFIED of any size blocks the stage.

A record is bound to the task digest, not to the bytes of MASTER_CHECKLIST_TBSCI.md:
editing the master's wording does not void existing records. ``check`` instead matches
the record to the master's structure -- every check number in the master has exactly
one line, and no line cites a number the master does not have -- so a renumbered master
with an un-remapped record fails loudly. (Records made before 2026-09-30 carry a
``Master checklist: ... sha256:...`` header; it is ignored.)
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

from common import MASTER_CHECKLIST_PATH, REPO_ROOT, WorkflowError, task_digest, task_paths


# Checks a script answers completely: task_check.py/hardening_check.py (static),
# per_test_gate.py (per-test NOP genuineness), package_task.py + verify_package.py (the
# ZIP). AUTO is refused anywhere else -- judgment checks need a PASS with evidence.
MECHANICAL = frozenset({
    5, 11, 13, 24, 37, 39, 40, 53, 58, 63, 64, 65, 67, 71, 72, 73, 74, 75, 76, 77, 78, 79,
    80, 87, 88, 89, 90, 91, 92, 96, 97, 104,
})
# Merged placeholders (Master v2+): recorded N/A, answered by the surviving check.
MERGED = {
    8: "47",
    18: "12",
    21: "12",
    22: "12",
    48: "6",
    51: "43",
    81: "75",
    82: "76",
    105: "37, 38 and 64",
}
# Single verdict recorded only after the five packaged runs (master preamble).
# Pre-trial parts of #1, #2, #15, #40, #53, #57 and #101 are done at Step 3b;
# the line stays PENDING until Step 4. #1, #2, #15, #40, #53, #57 and #101
# have a pre-trial part: at review the PENDING line must already carry that
# evidence. #33 has no pre-trial part. An answer recorded before the trials
# existed is not an answer, so --stage review rejects anything but PENDING on
# these lines. At package the verdict's evidence must cite the packaged runs
# or oracle/NOP record. Merged placeholders 81 and 82 sit inside 71-94
# numerically and stay N/A from init.
POST_TRIAL = frozenset({1, 2, 15, 33, 40, 53, 57, 70, *range(71, 95), 101, 107}) - set(MERGED)
PRETRIAL = frozenset({1, 2, 15, 40, 53, 57, 101})
# A packaged-evidence citation. "looked fine" is not one.
TRIAL_CITE = re.compile(
    r"run-0\d|trajector|\boracle\b|nop-\d|\bnop\b|ctrf|step3c|result\.json|reward\.txt",
    re.IGNORECASE,
)
# #96 and #97 judge the zip, which does not exist at Step 3b. PENDING is
# allowed then; a verdict recorded early is not rejected.
PACKAGE_STAGE = POST_TRIAL | frozenset({96, 97})
VERDICTS = ("PASS", "N/A", "AUTO", "FAIL", "PENDING", "NOT VERIFIED")
LINE_RE = re.compile(r"^#(\d+)\s*\|\s*(PASS|N/A|AUTO|FAIL|PENDING|NOT VERIFIED)\s*\|\s*(.*)$")
CHECK_RE = re.compile(r"^(\d+)\.\s+(.*)$")
SECTION_RE = re.compile(r"^SECTION\s+([A-Z])\s+[—-]+\s+(.*)$")
APPENDIX_RE = re.compile(r"^APPENDIX\b")


def parse_master(path: Path = MASTER_CHECKLIST_PATH) -> list[tuple[int, str, str]]:
    """[(number, section letter, first line of the check)] in file order."""
    if not path.is_file():
        raise WorkflowError(f"master checklist not found: {path}")
    checks: list[tuple[int, str, str]] = []
    section = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if APPENDIX_RE.match(line.strip()):
            break  # the Appendix's numbered steps (the verifier seal) are not checks
        heading = SECTION_RE.match(line.strip())
        if heading:
            section = heading.group(1)
            continue
        match = CHECK_RE.match(line)
        if match and section:
            checks.append((int(match.group(1)), section, match.group(2).strip()))
    numbers = [number for number, _, _ in checks]
    if len(numbers) != len(set(numbers)) or not numbers:
        raise WorkflowError(f"cannot parse unique numbered checks from {path}")
    return checks


def record_path(task: Path) -> Path:
    return REPO_ROOT / "authoring" / task.name / "master-checklist.md"


def cmd_init(task: Path, force: bool) -> int:
    path = record_path(task)
    if path.exists() and not force:
        print(f"refusing to overwrite {path.relative_to(REPO_ROOT)} (use --force to start over)")
        return 1
    checks = parse_master()
    lines = [
        f"Task: {task.name}",
        f"Task digest: {task_digest(task)}",
        "",
        "<!-- One line per check: `#N | PASS|N/A|AUTO|FAIL|PENDING|NOT VERIFIED | evidence`.",
        "     PASS needs evidence (file:line, quoted text, or command output) re-verified on",
        "     disk now, never from memory or an earlier pass. AUTO only where the scripts",
        "     enforce the check completely. Merged placeholders are N/A at init. Any FAIL or",
        "     NOT VERIFIED, of any severity, blocks shipping. -->",
    ]
    section = None
    for number, letter, title in checks:
        if letter != section:
            section = letter
            lines += ["", f"## Section {letter}"]
        lines.append(f"<!-- {number}. {title[:150]} -->")
        if number in MERGED:
            lines.append(
                f"#{number} | N/A | merged placeholder; answered by #{MERGED[number]}"
            )
        else:
            lines.append(f"#{number} | PENDING |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(REPO_ROOT)} ({len(checks)} checks)")
    return 0


def read_record(task: Path) -> tuple[dict[str, str], dict[int, tuple[str, str]], list[str]]:
    path = record_path(task)
    if not path.is_file():
        raise WorkflowError(f"missing {path.relative_to(REPO_ROOT)}; run: python3 scripts/master_checklist.py init {task}")
    headers: dict[str, str] = {}
    entries: dict[int, tuple[str, str]] = {}
    errors: list[str] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        for key in ("Task", "Task digest"):
            if line.startswith(f"{key}:") and key not in headers:
                headers[key] = line.split(":", 1)[1].strip()
        if not line.startswith("#") or line.startswith("##"):
            continue
        match = LINE_RE.match(line)
        if not match:
            errors.append(f"line {number}: not `#N | VERDICT | evidence`: {line[:70]!r}")
            continue
        check = int(match.group(1))
        if check in entries:
            errors.append(f"line {number}: check #{check} answered twice")
        entries[check] = (match.group(2), match.group(3).strip())
    return headers, entries, errors


def check_record(task: Path, stage: str) -> tuple[list[str], str]:
    """Errors in the record for ``stage`` (empty when it passes) and a one-line status."""
    headers, entries, errors = read_record(task)
    checks = parse_master()
    if headers.get("Task") != task.name:
        errors.append(f"record names task {headers.get('Task')!r}, not {task.name!r}")
    current = task_digest(task)
    if headers.get("Task digest") != current:
        errors.append(f"record is bound to {headers.get('Task digest')!r}; the task is now {current} -- "
                      "re-walk the checks against the task on disk and re-head the record")
    # Structural match with the current master (replaces the old master-file hash):
    # exactly one line per master check, nothing the master does not number.
    numbers = {number for number, _, _ in checks}
    extra = sorted(set(entries) - numbers)
    missing = sorted(numbers - set(entries))
    if extra or missing:
        errors.append(
            f"record does not match the structure of MASTER_CHECKLIST_TBSCI.md "
            f"(checks {min(numbers)}-{max(numbers)}, {len(numbers)} total): "
            + (f"cites {', '.join(f'#{n}' for n in extra)}, not in the master; " if extra else "")
            + (f"has no line for {', '.join(f'#{n}' for n in missing)}; " if missing else "")
            + "if the master was renumbered, remap the record's numbers through the old->new table "
              "in docs/WORKFLOW_HARDENING_CHANGELOG.md; otherwise add/remove the lines and walk them")
    open_checks: list[int] = []
    for number, _, _ in checks:
        if number not in entries:
            continue
        verdict, evidence = entries[number]
        if stage == "review" and number in POST_TRIAL:
            if verdict != "PENDING":
                errors.append(
                    f"#{number} is {verdict} before the trials; its single verdict is recorded "
                    "after the five packaged runs (master preamble). Leave it PENDING through Step 3b"
                )
            elif number in PRETRIAL and len(evidence) < 8:
                errors.append(
                    f"#{number} pre-trial part has no evidence on the PENDING line; "
                    "record what was checked (file:line, quote, or command output). "
                    "The verdict is written at Step 4"
                )
            continue
        required = stage == "package" or number not in PACKAGE_STAGE
        if verdict == "FAIL":
            errors.append(f"#{number} is FAIL: {evidence[:90]} -- fix it; nothing ships with an open finding")
        elif verdict == "NOT VERIFIED":
            errors.append(
                f"#{number} is NOT VERIFIED: {evidence[:90]} -- resolve to PASS or FAIL; "
                "a NOT VERIFIED blocks shipping (Master preamble)"
            )
        elif verdict == "PENDING":
            if required:
                open_checks.append(number)
        elif verdict == "AUTO" and number not in MECHANICAL:
            errors.append(f"#{number} needs judgment; AUTO is only for {sorted(MECHANICAL)}")
        elif verdict in {"PASS", "N/A"} and len(evidence) < 8:
            errors.append(f"#{number} is {verdict} without evidence; cite file:line, quoted text or command output")
        elif (
            stage == "package"
            and number in POST_TRIAL
            and verdict in {"PASS", "N/A", "AUTO"}
            and not TRIAL_CITE.search(evidence)
        ):
            errors.append(
                f"#{number} evidence does not cite the packaged runs or oracle/NOP record "
                "(run-0N, trajectories/, oracle-N, nop-N, ctrf, step3c, result.json, or reward.txt)"
            )
    if open_checks:
        errors.append(f"not yet answered for stage {stage}: " + ", ".join(f"#{n}" for n in open_checks))
    answered = sum(1 for number, _, _ in checks if entries.get(number, ("PENDING",))[0] != "PENDING")
    return errors, f"{answered}/{len(checks)} checks answered, bound to {current}"


def cmd_check(task: Path, stage: str) -> int:
    try:
        errors, status = check_record(task, stage)
    except WorkflowError as exc:
        print(f"Master checklist ({stage}): FAIL\n- {exc}")
        return 1
    if errors:
        print(f"Master checklist ({stage}): FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Master checklist ({stage}): PASS -- {status}, 0 FAIL")
    return 0


def static_findings(task: Path) -> dict[int, list[str]]:
    from task_check import validate_task

    grouped: dict[int, list[str]] = {}
    for issue in validate_task(task, strict=True)["issues"]:
        numbers = [int(n) for n in re.findall(r"Master #(\d+)", issue["detail"])] or [-1]
        for number in numbers:
            grouped.setdefault(number, []).append(f"{issue['level']} [{issue['check']}] {issue['detail']}")
    return grouped


def leads(task: Path) -> dict[int, list[str]]:
    """Heuristic pointers for judgment checks. A lead is a question, not a verdict."""
    found: dict[int, list[str]] = {}

    def lead(number: int, text: str) -> None:
        found.setdefault(number, []).append(text)

    files = [path for path in task_paths(task) if path.is_file()]
    rel = {path: path.relative_to(task).as_posix() for path in files}
    texts: dict[Path, str] = {}
    for path in files:
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" not in data[:8192] and len(data) < 4 * 1024 * 1024:
            texts[path] = data.decode("utf-8", errors="replace")
    env = [path for path in files if rel[path].startswith("environment/")]
    for path in env:
        lead(12, f"read in full: {rel[path]}")
    # Master #15: notes/lore/history files that could index the planted defects.
    for path in env:
        if re.search(r"(?i)(note|lore|history|changelog|attempt|debug|postmortem|incident|todo)", path.name):
            lead(15, f"{rel[path]} -- map it line by line against rubric.txt before accepting it as color")
    # Master #12 (absorbs former #18): files whose basename nothing else mentions.
    for path in env:
        if path.name == "Dockerfile":
            continue
        mentioned = any(path.name in text or path.stem in text for other, text in texts.items() if other != path)
        if not mentioned:
            lead(12, f"{rel[path]} is referenced by no other task file -- dead code or a disclosed decoy?")
    # Master #20: byte-identical files between the agent image and the grader/solution side.
    digests: dict[str, list[str]] = {}
    for path in files:
        digests.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), []).append(rel[path])
    for group in digests.values():
        sides = {name.split("/", 1)[0] for name in group}
        if "environment" in sides and sides & {"tests", "solution"}:
            lead(20, "byte-identical across the agent image and grader/solution: " + ", ".join(sorted(group))
                 + " -- does it compute any graded quantity?")
    # Master #12 (absorbs former #22): every environment doc is a requirement with a test.
    for path in env:
        if path.suffix.lower() in {".md", ".rst", ".txt", ".adoc"} or "/docs/" in rel[path]:
            lead(12, f"{rel[path]} -- which requirement does it state, and which test grades it?")
    # Master #23: vendored archives carrying authoring-machine ownership.
    import tarfile
    for path in env:
        if re.search(r"\.(?:tar|tgz|tar\.gz|tar\.bz2|tar\.xz)$", path.name):
            try:
                with tarfile.open(path) as archive:
                    owners = {(m.uname, m.gname, m.uid, m.gid) for m in archive.getmembers()}
            except (tarfile.TarError, OSError) as exc:
                lead(23, f"{rel[path]}: cannot read ({exc})")
                continue
            bad = sorted(o for o in owners if o[0] not in {"", "root"} or o[2] != 0)
            if bad:
                lead(23, f"{rel[path]} carries owner {bad[0][0]!r} uid {bad[0][2]}; re-tar with --owner=0 --group=0")
    # Master #34: solution files solve.sh never names.
    solve = task / "solution" / "solve.sh"
    solve_text = texts.get(solve, "")
    for path in files:
        if rel[path].startswith("solution/") and path != solve and path.name not in solve_text:
            lead(34, f"{rel[path]} is not referenced by solution/solve.sh -- orphaned copy?")
    # Master #50/#53: test functions vs the manifest; helpers nobody calls.
    try:
        import json
        manifest = json.loads((task / "tests" / "test_manifest.json").read_text(encoding="utf-8"))
        cases = {case.split("::")[-1] for entry in manifest.get("tests", []) for case in entry.get("cases", [])}
    except (OSError, ValueError, AttributeError):
        cases = set()
    test_texts = {path: text for path, text in texts.items() if rel[path].startswith("tests/") and path.suffix == ".py"}
    joined = "\n".join(test_texts.values())
    for path, text in test_texts.items():
        for name in re.findall(r"(?m)^\s*def\s+(test_[A-Za-z0-9_]+)\s*\(", text):
            if cases and name not in cases:
                lead(53, f"{rel[path]}::{name} is not a manifest case")
        for name in re.findall(r"(?m)^def\s+(_?[a-z][A-Za-z0-9_]*)\s*\(", text):
            if not name.startswith("test_") and len(re.findall(rf"\b{re.escape(name)}\b", joined)) < 2:
                lead(50, f"{rel[path]}: helper {name}() is defined but never used")
    # Master #6 (absorbs former #48): numeric constants the instruction states that the tests never spell.
    instruction = texts.get(task / "instruction.md", "")
    for constant in sorted(set(re.findall(r"(?<![\w.])(\d+\.\d+(?:e-?\d+)?|\d+e-?\d+)(?![\w.])", instruction))):
        if constant not in joined:
            lead(6, f"instruction states {constant} but no test file spells it literally -- same tolerance?")
    # Master #7: paths the instruction names.
    for named in sorted(set(re.findall(r"`(/[^`\s]+)`", instruction))):
        base = Path(named).name
        if not any(path.name == base for path in env):
            lead(7, f"{named}: no file with that name under environment/ (fine only if it is an output)")
    # Master #52: rejection-only tests.
    for path, text in test_texts.items():
        for match in re.finditer(r"(?ms)^def\s+(test_[A-Za-z0-9_]+)\s*\(.*?(?=^def\s|\Z)", text):
            body = match.group(0)
            if re.search(r"returncode\s*!=\s*0|pytest\.raises|nonzero|non-zero", body) and not re.search(
                    r"returncode\s*==\s*0|check=True", body):
                lead(52, f"{rel[path]}::{match.group(1)} looks rejection-only -- where is its positive control?")
    return found


def auditor_findings(task: Path) -> tuple[dict[int, list[str]], dict[int, list[str]]]:
    """The bundled TB-Science auditor's view of the task (scripts/audit_task.py tree), by master number."""
    from audit_task import audit_tree

    grouped: dict[int, list[str]] = {}
    lead_rows: dict[int, list[str]] = {}
    try:
        failures, auditor_leads, _ = audit_tree(task)
    except (WorkflowError, OSError) as exc:
        return {-1: [f"FAIL [auditor] could not run: {exc}"]}, {}
    for rows, target, prefix in ((failures, grouped, "FAIL [auditor]"), (auditor_leads, lead_rows, "AUDITOR")):
        for row in rows:
            for number in [int(n) for n in re.findall(r"Master #(\d+)", row)] or [-1]:
                target.setdefault(number, []).append(f"{prefix} {row}")
    return grouped, lead_rows


def cmd_auto(task: Path) -> int:
    checks = parse_master()
    static = static_findings(task)
    hints = leads(task)
    audit_fail, audit_leads = auditor_findings(task)
    for number, rows in audit_fail.items():
        static.setdefault(number, []).extend(rows)
    for number, rows in audit_leads.items():
        hints.setdefault(number, []).extend(rows)
    print(f"Master checklist auto-scan: {task.name} ({task_digest(task)})")
    print("Static findings must be fixed; leads must be answered in the record with evidence.\n")
    for number, _, title in checks:
        rows = static.get(number, []) + [f"LEAD {text}" for text in hints.get(number, [])]
        tag = "AUTO-eligible" if number in MECHANICAL else "judgment"
        if rows:
            print(f"#{number} ({tag}) {title[:90]}")
            for row in rows:
                print(f"    {row}")
    unnumbered = static.get(-1, []) + [f"LEAD {text}" for text in hints.get(-1, [])]
    if unnumbered:
        print("(no master number -- answer these in the Step 3b review)")
        for row in unnumbered:
            print(f"    {row}")
    return 1 if any(row.startswith("FAIL") for rows in static.values() for row in rows) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("task_dir", type=Path)
    init.add_argument("--force", action="store_true")
    auto = sub.add_parser("auto")
    auto.add_argument("task_dir", type=Path)
    check = sub.add_parser("check")
    check.add_argument("task_dir", type=Path)
    check.add_argument("--stage", choices=("review", "package"), required=True)
    args = parser.parse_args(argv)
    task = args.task_dir.resolve()
    if not task.is_dir():
        parser.error(f"task directory not found: {task}")
    try:
        if args.command == "init":
            return cmd_init(task, args.force)
        if args.command == "auto":
            return cmd_auto(task)
        return cmd_check(task, args.stage)
    except WorkflowError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
