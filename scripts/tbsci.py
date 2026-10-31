#!/usr/bin/env python3
"""Lean TB-Science workflow: five steps, one command each.

  seed     <slug>             1. create/check the one-page seed card   authoring/<slug>/seed.md
  check    <slug> [--no-docker]
                              3. run every mechanical check in one go, write
                                 authoring/<slug>/check-report.md, fill the mechanical master lines
  review   <slug>             4. create/check the 16-point review card  authoring/<slug>/review.md
                                 and fill the judgment master lines from it
  labels   <slug>             5a. check the five trial labels           authoring/<slug>/trials.md
  package  <slug> [-- extra args for package_task.py]
                              5b. build the zip and run the zip checks (only when CONFIRMED)
  status   <slug>             what is done, what is left
  selftest                    the workflow checks itself (no Docker needed)

Step 2 (build the task files) has no command: write them, then run `check`.
A FAIL anywhere: fix the file and run the same command again. Nothing else to redo.

MASTER_CHECKLIST_TBSCI.md (version 4) is frozen (md5 in FROZEN.md5). The per-task record
authoring/<slug>/master-checklist.md keeps its format `#N | VERDICT | evidence`; this tool only
fills PENDING lines and never overwrites a line someone already answered.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(os.environ.get("TBSCI_ROOT") or Path(__file__).resolve().parent.parent)
LINE_RE = re.compile(r"^#(\d+)\s*\|\s*(PASS|N/A|AUTO|FAIL|PENDING|NOT VERIFIED)\s*\|\s*(.*)$")

# Pre-trial checks the scripts enforce (MECHANICAL in master_checklist.py minus post-trial ones).
MECHANICAL_PRE = (5, 11, 13, 24, 37, 39, 58, 63, 64, 65, 67, 104)

# The review card: 16 points covering the 53 pre-trial judgment checks + the 7 pre-trial parts.
CARD = [
    (1, "Instruction: units and conventions stated, absolute paths, every number matches the tests, no contradictions", (0, 6, 7, 9)),
    (2, "Instruction says what, not how; the crux mechanism is never narrated", (3, 4, 10)),
    (3, "environment/: only needed files, honest names, no hint comments, no lore index, no answer-key helper, fair decoys", (12, 14, 16, 17, 19, 25)),
    (4, "environment/ image: archives clean, pinned and portable", (23, 26, 106)),
    (5, "No file shared between environment/ and tests/ or solution/ except stated inputs", (20,)),
    (6, "solution/ stays in scope: every touched file earns its place, no scenario-id branching, no held-out knowledge, no orphans", (27, 28, 29, 31, 32, 34)),
    (7, "Reference verified independently; one-file ablations fail tests; cold build passes", (30, 35, 36)),
    (8, "Tests assert real values, read in full, truth not computed by agent code, schemas literal, no obfuscation or dead code", (43, 44, 45, 47, 49, 50, 59)),
    (9, "Guard tests coupled to behaviour, fail-closed tests have a positive control, hold-outs change the outcome", (41, 42, 46, 52)),
    (10, "Every shortcut (empty, format-only, hard-coded, self-reported, missing artifact, fake reward) rejected by its own assertion", (60,)),
    (11, "Verifier seal: deps baked, Appendix A seal copied, artifacts untrusted, reward written last", (38, 54, 55, 56)),
    (12, "task.toml metadata correct; no difficulty or pass rate anywhere", (61, 62)),
    (13, "Rubric lines map to requirements, are satisfiable together, no double counting; a crux line exists", (66, 68, 69)),
    (14, "Science: real workflow, taxonomy right, provenance recorded, truth from planted parameters, no manufactured difficulty", (95, 98, 99, 100)),
    (15, "Nulls fail every graded instance; write-ups present with the three headings; no README.md", (102, 103)),
    (16, "Pre-trial parts: requirement<->test map, no defect-indexing doc, tests fail under NOP by design, test count, no latency assertion, independent method keeps >= 10% margin", (1, 2, 15, 40, 53, 57, 101)),
]
PRE_PARTS = {1, 2, 15, 40, 53, 57, 101}
EVIDENCE_HINT = re.compile(r"[\w./-]+:\d+|check-report|calibration\.md|run\b|\.log\b|\.json\b", re.I)


class Fail(Exception):
    pass


# ----------------------------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------------------------

def cfg(name: str) -> dict:
    path = ROOT / "config" / name
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def auth(slug: str) -> Path:
    return ROOT / "authoring" / slug


def task(slug: str) -> Path:
    return ROOT / "tasks" / slug


def table(path: Path, heading: str | None = None) -> list[dict]:
    """Rows of the first markdown table in the file (or after `heading`), as dicts."""
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    start = 0
    if heading:
        start = next((i for i, l in enumerate(lines) if l.strip().lower().startswith(heading.lower())), len(lines))
    block: list[str] = []
    for line in lines[start:]:
        if line.strip().startswith("|"):
            block.append(line.strip())
        elif block:
            break
    if len(block) < 2:
        return []
    header = [c.strip().lower() for c in block[0].strip("|").split("|")]
    rows = []
    for raw in block[2:]:
        cells = [c.strip() for c in raw.strip("|").split("|")]
        cells += [""] * (len(header) - len(cells))
        rows.append(dict(zip(header, cells)))
    return rows


def run(cmd: list[str], timeout: int = 7200) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def digest(slug: str) -> str:
    code, out = run([sys.executable, "scripts/task_digest.py", f"tasks/{slug}"], 120)
    return out.strip().splitlines()[-1] if code == 0 and out.strip() else "unknown"


def record(slug: str) -> Path:
    """The master record, bound to the current task digest. A record made for an older digest is
    moved aside (master-checklist.stale.md) and a fresh one started: `check` and `review` refill it."""
    path = auth(slug) / "master-checklist.md"
    if path.is_file():
        head = re.search(r"^Task digest:\s*(\S+)", path.read_text(encoding="utf-8"), re.M)
        if head and head.group(1) != digest(slug):
            path.replace(path.with_name("master-checklist.stale.md"))
            print(f"task changed: old record moved to authoring/{slug}/master-checklist.stale.md")
    if not path.is_file():
        code, out = run([sys.executable, "scripts/master_checklist.py", "init", f"tasks/{slug}"], 120)
        if code != 0 or not path.is_file():
            raise Fail(f"cannot create {path.relative_to(ROOT)}: {out.strip()}")
    return path


def fill(slug: str, answers: dict[int, str]) -> int:
    """Write answers into PENDING lines only. Returns how many lines changed."""
    path = record(slug)
    out, changed = [], 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = LINE_RE.match(raw.strip())
        if match and int(match.group(1)) in answers and match.group(2) == "PENDING" and not match.group(3).strip():
            out.append(answers[int(match.group(1))])
            changed += 1
        else:
            out.append(raw)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


# ----------------------------------------------------------------------------------------------
# 1. seed
# ----------------------------------------------------------------------------------------------

SEED_TEMPLATE = """# Seed card: {slug}

Domain / field / subfield:
Workflow (who does this work for real):
Crux (the one decision that separates a careful expert from a quick answer):
Data source or generator (fictional names; truth from planted parameters):
Upstream overlap check (query + result):

## Naive defaults that must fail
-

## Tests planned (one requirement each; at least {min_tests})
-

Decision: (GO or NO-GO)
"""


def _bullets(text: str, heading: str) -> list[str]:
    part = text.split(heading, 1)[1] if heading in text else ""
    part = part.split("\n## ", 1)[0].split("\nDecision:", 1)[0]
    return [l[1:].strip() for l in part.splitlines() if l.strip().startswith("-") and l[1:].strip()]


def seed(slug: str) -> list[str]:
    path = auth(slug) / "seed.md"
    minimum = int(cfg("client_rules.toml").get("min_tests", 10))
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SEED_TEMPLATE.format(slug=slug, min_tests=minimum), encoding="utf-8")
        return [f"created {path.relative_to(ROOT)}; fill it and run the command again"]
    text = path.read_text(encoding="utf-8")
    errors = []
    for field in ("Domain / field / subfield:", "Workflow", "Crux", "Data source or generator", "Upstream overlap check"):
        line = next((l for l in text.splitlines() if l.startswith(field)), "")
        if not line.split(":", 1)[-1].strip():
            errors.append(f"seed.md: `{field.rstrip(':')}` is empty")
    if not _bullets(text, "## Naive defaults that must fail"):
        errors.append("seed.md: list at least one naive default that must fail")
    tests = _bullets(text, "## Tests planned")
    if len(tests) < minimum:
        errors.append(f"seed.md: {len(tests)} tests planned, need at least {minimum}")
    if not re.search(r"^Decision:\s*GO\b", text, re.M):
        errors.append("seed.md: write `Decision: GO` when the seed is ready")
    return errors


# ----------------------------------------------------------------------------------------------
# 3. check
# ----------------------------------------------------------------------------------------------

def calibration(slug: str) -> list[str]:
    """authoring/<slug>/calibration.md: | method | class | tests-failed | min-margin-pct |"""
    rows = table(auth(slug) / "calibration.md")
    rules = cfg("client_rules.toml")
    need = float(rules.get("correct_margin_pct", 10))
    if not rows:
        return ["calibration.md: add the table | method | class | tests-failed | min-margin-pct | "
                "(one independent correct method + every naive default and null from the seed)"]
    errors = []
    correct = [r for r in rows if r.get("class", "").lower() == "correct"]
    if not correct:
        errors.append("calibration.md: no independent correct method")
    for r in rows:
        cls, failed = r.get("class", "").lower(), r.get("tests-failed", "").strip().lower()
        name = r.get("method", "?")
        if cls == "correct":
            if failed not in {"", "none", "-"}:
                errors.append(f"calibration.md: correct method {name} fails {failed} (false fail risk)")
            try:
                if float(r.get("min-margin-pct", "")) < need:
                    errors.append(f"calibration.md: correct method {name} margin {r.get('min-margin-pct')}% < {need}%")
            except ValueError:
                errors.append(f"calibration.md: {name} min-margin-pct is not a number")
        elif cls in {"defective", "naive", "null"}:
            if failed in {"", "none", "-"}:
                errors.append(f"calibration.md: {cls} method {name} passes every test (false pass)")
        else:
            errors.append(f"calibration.md: {name} class must be correct, defective, naive or null")
    return errors


def check(slug: str, docker: bool) -> int:
    if not task(slug).is_dir():
        raise Fail(f"tasks/{slug} does not exist")
    record(slug)  # start (or re-start, after an edit) the master record for this digest
    stages: list[tuple[str, list[str] | None]] = [
        ("client rules (v02_checks all)", [sys.executable, "scripts/v02_checks.py", "all", f"tasks/{slug}"]),
        ("structure and policy (task_check --strict)", [sys.executable, "scripts/task_check.py", f"tasks/{slug}", "--strict"]),
        ("bundled auditor screen (audit_task tree)", [sys.executable, "scripts/audit_task.py", "tree", f"tasks/{slug}"]),
        ("oracle passes in Docker (dev_verify)", ["bash", "scripts/dev_verify.sh", f"tasks/{slug}"] if docker else None),
    ]
    results = []
    for name, cmd in stages:
        if cmd is None:
            results.append((name, "NOT RUN", "--no-docker"))
            continue
        code, out = run(cmd)
        tail = "\n".join(out.strip().splitlines()[-15:])
        results.append((name, "PASS" if code == 0 else "FAIL", tail))
    cal = calibration(slug)
    results.append(("calibration (independent method margin, naive defaults and nulls fail)",
                    "PASS" if not cal else "FAIL", "\n".join(cal)))
    stamp = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    task_digest = digest(slug)
    lines = [f"# Check report: {slug}", f"Task digest: {task_digest}", f"Run: {stamp}", "",
             "| Stage | Result |", "|---|---|"] + [f"| {n} | {r} |" for n, r, _ in results] + [""]
    for n, r, tail in results:
        if r != "PASS" and tail:
            lines += [f"## {n}: {r}", "```", tail, "```", ""]
    report = auth(slug) / "check-report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")
    for n, r, _ in results:
        print(f"{r:<8} {n}")
    static_ok = all(r == "PASS" for n, r, _ in results[:3])
    if static_ok:
        docker_note = "" if docker else " (Docker stage NOT RUN)"
        changed = fill(slug, {c: f"#{c} | AUTO | enforced by scripts; authoring/{slug}/check-report.md digest {task_digest}{docker_note}"
                              for c in MECHANICAL_PRE})
        print(f"filled {changed} mechanical line(s) in authoring/{slug}/master-checklist.md")
    print(f"report: authoring/{slug}/check-report.md")
    return 0 if all(r in {"PASS", "NOT RUN"} for _, r, _ in results) else 1


# ----------------------------------------------------------------------------------------------
# 4. review
# ----------------------------------------------------------------------------------------------

def card_template(slug: str) -> str:
    out = [f"# Review card: {slug}", "", f"Task digest: {digest(slug)}", "",
           "Read the task once, top to bottom. For each point write PASS, FAIL or N/A and the evidence",
           "(file:line with the words, or a line of authoring/<slug>/check-report.md). The full text of each",
           "master check is in MASTER_CHECKLIST_TBSCI.md under its number. Point 16 is recorded before",
           "the trials; its final verdict comes after them.", "",
           "| # | Point | Checks | Verdict | Evidence |", "|---|---|---|---|---|"]
    for n, text, checks in CARD:
        out.append(f"| {n} | {text} | {', '.join('#' + str(c) for c in checks)} |  |  |")
    return "\n".join(out) + "\n"


def review(slug: str) -> list[str]:
    path = auth(slug) / "review.md"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(card_template(slug), encoding="utf-8")
        return [f"created {path.relative_to(ROOT)}; fill Verdict and Evidence for all 16 points, then run again"]
    head = re.search(r"^Task digest:\s*(\S+)", path.read_text(encoding="utf-8"), re.M)
    now = digest(slug)
    if not head or head.group(1) != now:
        return [f"review.md: the task changed since this card was written. Re-check the points your fix "
                f"touched, update their evidence, then set `Task digest: {now}`"]
    rows = {r.get("#", ""): r for r in table(path)}
    errors, answers = [], {}
    for n, _, checks in CARD:
        row = rows.get(str(n))
        if row is None:
            errors.append(f"review.md: point {n} is missing")
            continue
        verdict, evidence = row.get("verdict", "").upper(), row.get("evidence", "")
        if verdict not in {"PASS", "FAIL", "N/A"}:
            errors.append(f"review.md: point {n} verdict must be PASS, FAIL or N/A")
            continue
        if verdict == "FAIL":
            errors.append(f"review.md: point {n} is FAIL -> fix the task, run `check`, then review this point again")
            continue
        if verdict == "N/A" and len(evidence.split()) < 3:
            errors.append(f"review.md: point {n} N/A needs a reason")
            continue
        if verdict == "PASS" and not EVIDENCE_HINT.search(evidence):
            errors.append(f"review.md: point {n} evidence needs a file:line or a check-report/calibration reference")
            continue
        for c in checks:
            if c in PRE_PARTS:
                answers[c] = f"#{c} | PENDING | PRE (review card {n}): {evidence}"
            else:
                answers[c] = f"#{c} | {verdict} | review card {n}: {evidence}"
    if errors:
        return errors
    changed = fill(slug, answers)
    print(f"filled {changed} line(s) in authoring/{slug}/master-checklist.md from the review card")
    code, out = run([sys.executable, "scripts/master_checklist.py", "check", f"tasks/{slug}", "--stage", "review"], 300)
    print(out.strip())
    return [] if code == 0 else ["master_checklist.py check --stage review reports open lines (see above)"]


# ----------------------------------------------------------------------------------------------
# 5. labels, package
# ----------------------------------------------------------------------------------------------

TRIALS_TEMPLATE = """# Trials: {slug}

Labels: legit-pass, hack-pass, legit-fail, false-fail. A hack-pass or false-fail means the task has a
defect: fix it, re-run `check` and `review`, and run a new round.

| run | reward | label | evidence |
|---|---|---|---|
| run-01 |  |  |  |
| run-02 |  |  |  |
| run-03 |  |  |  |
| run-04 |  |  |  |
| run-05 |  |  |  |
"""


def labels(slug: str) -> list[str]:
    path = auth(slug) / "trials.md"
    if cfg("round.toml").get("status") != "CONFIRMED":
        return ["config/round.toml is PARKED: trials wait for the client's confirmation"]
    if not path.is_file():
        path.write_text(TRIALS_TEMPLATE.format(slug=slug), encoding="utf-8")
        return [f"created {path.relative_to(ROOT)}; fill it after the five trials"]
    sys.path.insert(0, str(ROOT / "scripts"))
    import trial_labels  # noqa: E402
    errors, summary = trial_labels.check_rows(table(path), task(slug), cfg("round.toml"))
    c = summary["counts"]
    print(f"legit-pass {c['legit-pass']}  legit-fail {c['legit-fail']}  hack-pass {c['hack-pass']}  "
          f"false-fail {c['false-fail']}  band {summary['band']}")
    return errors


def package(slug: str, extra: list[str]) -> int:
    if cfg("round.toml").get("status") != "CONFIRMED":
        raise Fail("config/round.toml is PARKED: packaging needs the trials, which wait for the client")
    code, out = run([sys.executable, "scripts/package_task.py", f"tasks/{slug}", *extra])
    print(out.strip())
    if code != 0:
        return code
    zip_path = ROOT / "Task_Ready_To_Submit" / f"{slug}.zip"
    if not zip_path.is_file():
        zips = sorted((ROOT / "artifacts" / "package-candidates" / slug).glob("*.zip")) if (ROOT / "artifacts").is_dir() else []
        zip_path = zips[-1] if zips else zip_path
    worst = 0
    for cmd in ([sys.executable, "scripts/verify_package.py", str(zip_path)],
                [sys.executable, "scripts/v02_checks.py", "zip", str(zip_path)]):
        code, out = run(cmd)
        print(out.strip())
        worst = max(worst, code)
    return worst


def status(slug: str) -> None:
    a = auth(slug)
    rows = [("1 seed", a / "seed.md"), ("2 build", task(slug) / "instruction.md"), ("3 check", a / "check-report.md"),
            ("4 review", a / "review.md"), ("5 trials", a / "trials.md")]
    for name, path in rows:
        print(f"{name:<9} {'yes' if path.exists() else '-':<4} {path.relative_to(ROOT)}")
    rec = a / "master-checklist.md"
    if rec.is_file():
        counts: dict[str, int] = {}
        for raw in rec.read_text(encoding="utf-8").splitlines():
            m = LINE_RE.match(raw.strip())
            if m:
                counts[m.group(2)] = counts.get(m.group(2), 0) + 1
        print("master record:", ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print("round:", cfg("round.toml").get("status", "PARKED"))


# ----------------------------------------------------------------------------------------------
# selftest
# ----------------------------------------------------------------------------------------------

def _fixture(src: Path, base: Path) -> str:
    for rel in ("scripts", "config", "docs", "tools"):
        shutil.copytree(src / rel, base / rel, ignore=shutil.ignore_patterns("__pycache__", "reference"))
    for rel in ("MASTER_CHECKLIST_TBSCI.md", "FROZEN.md5"):
        shutil.copy2(src / rel, base / rel)
    slug = "demo-task"
    t = base / "tasks" / slug
    for d in ("environment/data", "solution", "tests"):
        (t / d).mkdir(parents=True)
    (t / "instruction.md").write_text(
        "Estimate the decay constant of the sample in `/app/data/counts.csv`.\n\n"
        "The decay constant is defined as k in N(t) = N0 exp(-k t), with t in hours.\n"
        "Write `/app/output/result.json` with the key `k_per_hour`.\n\n"
        "You have 28800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.\n",
        encoding="utf-8")
    (t / "environment" / "Dockerfile").write_text("FROM python:3.12\nRUN pip install numpy==2.1.3\n", encoding="utf-8")
    (t / "environment" / "data" / "counts.csv").write_text("t,n\n0,1000\n1,905\n", encoding="utf-8")
    (t / "solution" / "solve.sh").write_text("#!/bin/bash\necho fit\n", encoding="utf-8")
    (t / "tests" / "test_manifest.json").write_text(json.dumps(
        {"tests": [{"id": f"t{i:02d}", "cases": [f"test_outputs.py::test_t{i:02d}"]} for i in range(1, 11)]}), encoding="utf-8")
    (t / "tests" / "test.sh").write_text("#!/bin/bash\nREWARD=0\npytest /tests && REWARD=1\n"
                                         "echo $REWARD > /logs/verifier/reward.txt\nexit 0\n", encoding="utf-8")
    (t / "tests" / "Dockerfile").write_text("FROM python:3.12\nRUN pip install pytest==8.3.3\n", encoding="utf-8")
    (t / "task.toml").write_text(
        'name = "demo-task"\n[environment]\nnetwork_mode = "public"\ncpus = 2\nmemory_mb = 4096\ngpus = 0\n'
        'build_timeout_sec = 28800.0\n[agent]\ntimeout_sec = 28800.0\n[verifier]\ntimeout_sec = 28800.0\n'
        'environment_mode = "separate"\n[verifier.environment]\nnetwork_mode = "no-network"\n', encoding="utf-8")
    (t / "rubric.txt").write_text("Agent fits an exponential decay and reports k, +3\n", encoding="utf-8")
    return slug


def selftest() -> int:
    global ROOT
    results: list[str] = []

    def expect(name: str, errors: list[str], needle: str | None) -> None:
        ok = (not errors) if needle is None else any(needle in e for e in errors)
        results.append(f"{'ok  ' if ok else 'FAIL'} {name}" + ("" if ok else f"  -> got {errors[:3]}"))

    frozen = (ROOT / "FROZEN.md5").read_text(encoding="utf-8").split()[0]
    now = hashlib.md5((ROOT / "MASTER_CHECKLIST_TBSCI.md").read_bytes()).hexdigest()
    expect("master checklist v4 unchanged (FROZEN.md5)", [] if now == frozen else [f"md5 {now} != {frozen}"], None)
    covered = [c for _, _, cs in CARD for c in cs]
    sys.path.insert(0, str(ROOT / "scripts"))
    import master_checklist as mc  # noqa: E402
    live = set(range(108)) - set(mc.MERGED)
    expected = (live - mc.POST_TRIAL - {96, 97} - mc.MECHANICAL) | PRE_PARTS
    expect("review card covers every pre-trial judgment check exactly once",
           [] if sorted(covered) == sorted(expected) and len(covered) == len(set(covered))
           else [f"missing {sorted(expected - set(covered))}, extra {sorted(set(covered) - expected)}"], None)
    expect("mechanical list matches master_checklist.py",
           [] if set(MECHANICAL_PRE) == mc.MECHANICAL - mc.POST_TRIAL - {96, 97} else ["mismatch"], None)

    real_root = ROOT
    with tempfile.TemporaryDirectory() as tmp:
        ROOT = Path(tmp)
        try:
            slug = _fixture(real_root, ROOT)
            expect("seed: a new card is created", seed(slug), "created")
            expect("seed: an empty card is refused", seed(slug), "empty")
            s = auth(slug) / "seed.md"
            s.write_text(s.read_text().replace("Domain / field / subfield:", "Domain / field / subfield: physical / physics / decay")
                         .replace("Workflow (who does this work for real):", "Workflow (who does this work for real): lab")
                         .replace("Crux (the one decision that separates a careful expert from a quick answer):", "Crux (...): dead time")
                         .replace("Data source or generator (fictional names; truth from planted parameters):", "Data source or generator: gen.py")
                         .replace("Upstream overlap check (query + result):", "Upstream overlap check: none found")
                         .replace("## Naive defaults that must fail\n-", "## Naive defaults that must fail\n- linear fit")
                         .replace("Decision: (GO or NO-GO)", "Decision: GO"))
            expect("seed: too few planned tests is refused", seed(slug), "tests planned")
            s.write_text(s.read_text().replace("## Tests planned (one requirement each; at least 10)\n-",
                                               "## Tests planned (one requirement each; at least 10)\n" +
                                               "\n".join(f"- t{i}" for i in range(1, 11))))
            expect("seed: a complete card passes", seed(slug), None)
            cal = auth(slug) / "calibration.md"
            cal.write_text("| method | class | tests-failed | min-margin-pct |\n|---|---|---|---|\n"
                           "| ref-b | correct | none | 8 |\n| linear | naive | none | 0 |\n", encoding="utf-8")
            errs = calibration(slug)
            expect("calibration: thin correct margin is caught", errs, "margin 8")
            expect("calibration: a naive default that passes is caught", errs, "false pass")
            cal.write_text("| method | class | tests-failed | min-margin-pct |\n|---|---|---|---|\n"
                           "| ref-b | correct | none | 25 |\n| linear | naive | t01 t02 | 0 |\n", encoding="utf-8")
            expect("calibration: a good table passes", calibration(slug), None)
            expect("review: a new card is created", review(slug), "created")
            card = auth(slug) / "review.md"
            text = card.read_text(encoding="utf-8")
            filled = re.sub(r"\|  \|  \|$", f"| PASS | tasks/{slug}/instruction.md:3 defined as k |", text, flags=re.M)
            card.write_text(filled.replace("| #60 | PASS |", "| #60 | FAIL |"), encoding="utf-8")
            expect("review: a FAIL point blocks", review(slug), "point 10 is FAIL")
            card.write_text(filled.replace(f"| #60 | PASS | tasks/{slug}/instruction.md:3 defined as k |", "| #60 | PASS | looked fine |"),
                            encoding="utf-8")
            expect("review: evidence without a reference is refused", review(slug), "point 10 evidence")
            card.write_text(filled, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                review(slug)
            rec = (auth(slug) / "master-checklist.md").read_text(encoding="utf-8")
            expect("review: card fills judgment lines", [] if "#10 | PASS | review card 2:" in rec else ["#10 not filled"], None)
            expect("review: pre-trial parts stay PENDING with evidence",
                   [] if "#101 | PENDING | PRE (review card 16):" in rec else ["#101 wrong"], None)
            lines = rec.splitlines()
            answered = [l for l in lines if l.startswith("#33 ")]
            expect("review: post-trial checks are left alone", [] if answered and answered[0].strip() == "#33 | PENDING |" else answered, None)
            ins = task(slug) / "instruction.md"
            ins.write_text(ins.read_text() + "\nReport k to three significant figures.\n")
            expect("review: a card for an older task digest is refused", review(slug), "task changed")
            with contextlib.redirect_stdout(io.StringIO()):
                rc = check(slug, docker=False)
            expect("check: a record for an older digest is moved aside",
                   [] if (auth(slug) / "master-checklist.stale.md").is_file() else ["no stale record"], None)
            rec = (auth(slug) / "master-checklist.md").read_text(encoding="utf-8")
            rep = (auth(slug) / "check-report.md").read_text(encoding="utf-8")
            expect("check: an incomplete task fails (no tmux, no metadata, no CTRF)", [] if rc == 1 else [f"rc {rc}"], None)
            expect("check: mechanical lines stay PENDING when a stage fails",
                   [] if "#63 | PENDING |" in rec else ["#63 filled although check failed"], None)
            expect("check: Docker stage is reported NOT RUN, never PASS",
                   [] if "| oracle passes in Docker (dev_verify) | NOT RUN |" in rep else ["Docker row wrong"], None)
            expect("labels: refused while PARKED", labels(slug), "PARKED")
            v = lambda *a: [l for l in run([sys.executable, "scripts/v02_checks.py", *a])[1].splitlines() if l.startswith("FINDING")]
            expect("v02: the demo task is clean", v("all", f"tasks/{slug}"), None)
            ts = task(slug) / "tests" / "test.sh"
            ts.write_text(ts.read_text() + "# see Master #58(c)\n")
            expect("v02: a checklist citation is caught", v("tests", f"tasks/{slug}"), "Master")
            ts.write_text(ts.read_text().replace("echo $REWARD", "echo 0.5"))
            expect("v02: a fractional reward is caught", v("seal", f"tasks/{slug}"), "reward")
            tt = task(slug) / "task.toml"
            tt.write_text(tt.read_text().replace('network_mode = "no-network"', "allow_internet = false"))
            expect("v02: allow_internet is caught", v("toml", f"tasks/{slug}"), "network")
            df = task(slug) / "environment" / "Dockerfile"
            df.write_text(df.read_text() + "RUN pip install pandas\n")
            expect("v02: an unpinned package is caught", v("environment", f"tasks/{slug}"), "pandas")
            import zipfile
            zp = ROOT / "x.zip"
            with zipfile.ZipFile(zp, "w") as zf:
                zf.writestr(f"{slug}/trajectories/run-01/config.json", json.dumps({"trials_dir": "evidence-x-r2/x"}))
            expect("v02: a round-tagged trials_dir is caught", v("zip", str(zp)), "trials_dir")
            import trial_labels  # noqa: E402
            for i, r in enumerate("10000", 1):
                p = task(slug) / "trajectories" / f"run-{i:02d}" / "verifier" / "reward.txt"
                p.parent.mkdir(parents=True)
                p.write_text(r + "\n")
            rows = [{"run": "run-01", "reward": "1", "label": "hack-pass", "evidence": "read /tests"},
                    {"run": "run-02", "reward": "1", "label": "legit-pass", "evidence": "x"}]
            errs = trial_labels.check_rows(rows, task(slug), {"band": {"band_min": 0, "band_max": 3}})[0]
            expect("labels: a hack-pass is a task defect", errs, "hack-pass")
            expect("labels: a reward that disagrees with reward.txt is caught", errs, "run-02")
        finally:
            ROOT = real_root
    print("\n".join(results))
    failed = sum(r.startswith("FAIL") for r in results)
    print(f"\nselftest: {len(results) - failed}/{len(results)} passed")
    return 1 if failed else 0


# ----------------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    extra: list[str] = []
    if "--" in argv:
        cut = argv.index("--")
        argv, extra = argv[:cut], argv[cut + 1:]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("seed", "review", "labels", "package", "status"):
        sub.add_parser(name).add_argument("slug")
    p = sub.add_parser("check"); p.add_argument("slug"); p.add_argument("--no-docker", action="store_true")
    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "selftest":
            return selftest()
        if args.cmd == "check":
            return check(args.slug, not args.no_docker)
        if args.cmd == "package":
            return package(args.slug, extra)
        if args.cmd == "status":
            status(args.slug)
            return 0
        errors = {"seed": seed, "review": review, "labels": labels}[args.cmd](args.slug)
        for e in errors:
            print(e if e.startswith("created") else f"FAIL {e}")
        if not errors:
            print(f"{args.cmd}: PASS")
        return 0 if not errors or all(e.startswith("created") for e in errors) else 1
    except Fail as exc:
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
