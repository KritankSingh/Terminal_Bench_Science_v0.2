#!/usr/bin/env python3
"""Mechanical client-layer checks (docs/V02_RULES.md) on a task tree or a delivery zip.

  python3 scripts/v02_checks.py instruction  tasks/<slug>
  python3 scripts/v02_checks.py environment  tasks/<slug>
  python3 scripts/v02_checks.py tests        tasks/<slug>   [--min-tests N]
  python3 scripts/v02_checks.py seal         tasks/<slug>
  python3 scripts/v02_checks.py toml         tasks/<slug>
  python3 scripts/v02_checks.py all          tasks/<slug>   [--min-tests N]
  python3 scripts/v02_checks.py zip          Task_Ready_To_Submit/<slug>.zip

Every problem is printed as `FINDING <rule> <file>:<line> <what>`; exit 1 if any. These checks
ADD to MASTER_CHECKLIST_TBSCI.md (frozen) and to scripts/task_check.py; they never replace them.
Thresholds and hygiene patterns come from config/client_rules.toml. Output is deterministic.
`python3 scripts/tbsci.py check <slug>` runs `all` as its first stage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {"", ".md", ".txt", ".sh", ".py", ".toml", ".json", ".yaml", ".yml", ".cfg", ".ini", ".r", ".jl"}
SKIP_DIRS = {"data", "__pycache__"}
MAX_BYTES = 2_000_000
PIP_RE = re.compile(r"\b(?:uv\s+pip|pip3?|python3?\s+-m\s+pip)\s+install\b(.*)")
REWARD_ECHO = re.compile(r"echo\s+(\S+)\s*>+\s*\S*reward\.(?:txt|json)")
REWARD_PY = re.compile(r"reward\.(?:txt|json)['\"]?\)?\.write_text\(\s*['\"]([^'\"]*)['\"]")


def rules() -> dict:
    path = ROOT / "config" / "client_rules.toml"
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


class Report:
    def __init__(self) -> None:
        self.findings: list[str] = []

    def add(self, rule: str, where: str, what: str) -> None:
        self.findings.append(f"FINDING {rule} {where} {what}")


def text_files(base: Path, rel_root: Path):
    if base.is_file():
        yield base
        return
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        parts = path.relative_to(rel_root).parts
        if any(p in SKIP_DIRS for p in parts[:-1]) or path.suffix.lower() not in TEXT_SUFFIXES and path.name != "Dockerfile":
            continue
        if path.stat().st_size > MAX_BYTES:
            continue
        yield path


def hygiene(report: Report, paths: list[Path], task: Path, cfg: dict) -> None:
    patterns = [re.compile(p) for p in cfg.get("hygiene_patterns", []) + cfg.get("hygiene_extra_patterns", [])]
    for base in paths:
        if not base.exists():
            continue
        for path in text_files(base, task):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for n, line in enumerate(lines, 1):
                for pattern in patterns:
                    match = pattern.search(line)
                    if match:
                        report.add("V1-hygiene", f"{path.relative_to(task.parent)}:{n}",
                                   f"internal marker {match.group(0)!r} in a shipped file")
                        break


def pins(report: Report, files: list[Path], task: Path) -> None:
    for path in files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").replace("\\\n", " ")
        for n, line in enumerate(text.splitlines(), 1):
            match = PIP_RE.search(line)
            if not match:
                continue
            tail = re.split(r"&&|;|\|", match.group(1))[0]
            tokens = tail.split()
            skip_next = False
            for token in tokens:
                if skip_next:
                    skip_next = False
                    if token.endswith(".txt"):
                        req = path.parent / token
                        if req.is_file():
                            for m, req_line in enumerate(req.read_text(encoding="utf-8").splitlines(), 1):
                                spec = req_line.split("#")[0].strip()
                                if spec and not spec.startswith("-") and "==" not in spec:
                                    report.add("V3-pin", f"{req.relative_to(task.parent)}:{m}", f"unpinned {spec!r}")
                    continue
                if token in {"-r", "--requirement", "-c", "--constraint", "--index-url", "-i", "--extra-index-url"}:
                    skip_next = True
                    continue
                if token.startswith("-") or token.startswith("/") or token.startswith(".") or "://" in token:
                    continue
                if "==" not in token and "@" not in token:
                    report.add("V3-pin", f"{path.relative_to(task.parent)}:{n}", f"unpinned package {token!r}")


def reward_literal(report: Report, task: Path) -> None:
    tests = task / "tests"
    if not tests.is_dir():
        return
    for path in sorted(list(tests.glob("*.sh")) + list(tests.glob("*.py"))):
        text = path.read_text(encoding="utf-8")
        assigned: dict[str, set[str]] = {}
        for m in re.finditer(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=(\S+)", text, re.M):
            assigned.setdefault(m.group(1), set()).add(m.group(2).strip("'\""))
        for m in re.finditer(r"&&\s*([A-Za-z_][A-Za-z0-9_]*)=(\S+)", text):
            assigned.setdefault(m.group(1), set()).add(m.group(2).strip("'\""))
        for n, line in enumerate(text.splitlines(), 1):
            for match in list(REWARD_ECHO.finditer(line)) + list(REWARD_PY.finditer(line)):
                value = match.group(1).strip("'\"")
                if value.startswith("$"):
                    name = value.strip("${}")
                    bad = sorted(v for v in assigned.get(name, set()) if v not in {"0", "1"})
                    if bad:
                        report.add("V4-reward", f"{path.relative_to(task.parent)}:{n}",
                                   f"reward variable {name} can be {bad}; only literal 0 or 1 is allowed")
                elif value not in {"0", "1"}:
                    report.add("V4-reward", f"{path.relative_to(task.parent)}:{n}",
                               f"reward written as {value!r}; only literal 0 or 1 is allowed")


def seal_checks(report: Report, task: Path) -> None:
    test_sh = task / "tests" / "test.sh"
    if not test_sh.is_file():
        report.add("V4-seal", f"{task.name}/tests/test.sh:0", "missing tests/test.sh")
        return
    for n, line in enumerate(test_sh.read_text(encoding="utf-8").splitlines(), 1):
        if re.match(r"^\s*set\s+-[a-z]*e", line):
            report.add("V4-seal", f"{task.name}/tests/test.sh:{n}", "`set -e` can skip the reward write (master #39)")
    reward_literal(report, task)


def toml_checks(report: Report, task: Path, cfg: dict) -> None:
    path = task / "task.toml"
    where = f"{task.name}/task.toml"
    if not path.is_file():
        report.add("V2-toml", f"{where}:0", "missing task.toml")
        return
    text = path.read_text(encoding="utf-8")
    for n, line in enumerate(text.splitlines(), 1):
        if re.match(r"^\s*allow_internet\s*=", line):
            report.add("V2-network", f"{where}:{n}", "deprecated allow_internet; declare network_mode instead (master #64)")
    data = tomllib.loads(text)
    env, ver = data.get("environment", {}), data.get("verifier", {})
    venv = ver.get("environment", {})
    if env.get("network_mode") != "public":
        report.add("V2-network", f"{where}:0", f"[environment].network_mode is {env.get('network_mode')!r}, must be \"public\"")
    mode = venv.get("network_mode")
    if mode == "allowlist":
        if not venv.get("allowed_hosts"):
            report.add("V2-network", f"{where}:0", "verifier allowlist with no allowed_hosts")
    elif mode != "no-network":
        report.add("V2-network", f"{where}:0", f"[verifier.environment].network_mode is {mode!r}, must be \"no-network\"")
    if env.get("gpus", 0) != 0:
        report.add("V2-resources", f"{where}:0", "gpus must be 0 for this workspace (master #65)")
    for table, name in ((env, "[environment]"), (venv, "[verifier.environment]")):
        if table.get("cpus", 0) > int(cfg.get("max_cpus", 4)):
            report.add("V2-resources", f"{where}:0", f"{name} cpus {table.get('cpus')} > {cfg.get('max_cpus', 4)}")
        if table.get("memory_mb", 0) > int(cfg.get("max_memory_mb", 16384)):
            report.add("V2-resources", f"{where}:0", f"{name} memory_mb {table.get('memory_mb')} > {cfg.get('max_memory_mb', 16384)}")
    for value, name in ((data.get("agent", {}).get("timeout_sec"), "[agent].timeout_sec"),
                        (ver.get("timeout_sec"), "[verifier].timeout_sec"),
                        (env.get("build_timeout_sec"), "[environment].build_timeout_sec")):
        if value is None or float(value) != 28800.0:
            report.add("V2-timeouts", f"{where}:0", f"{name} is {value!r}, must be 28800 (master #63)")


def test_count(report: Report, task: Path, minimum: int) -> None:
    path = task / "tests" / "test_manifest.json"
    if not path.is_file():
        report.add("V14-tests", f"{task.name}/tests/test_manifest.json:0", "missing test manifest")
        return
    ids = [t.get("id") for t in json.loads(path.read_text(encoding="utf-8")).get("tests", [])]
    if len(ids) < minimum:
        report.add("V14-tests", f"{task.name}/tests/test_manifest.json:0", f"{len(ids)} tests, the client rule needs >= {minimum}")
    if len(ids) != len(set(ids)):
        report.add("V14-tests", f"{task.name}/tests/test_manifest.json:0", "duplicate test ids")


def check_task(kind: str, task: Path, min_tests: int | None) -> Report:
    cfg = rules()
    report = Report()
    minimum = min_tests if min_tests is not None else int(cfg.get("min_tests", 10))
    dockerfiles = sorted(task.glob("environment/**/Dockerfile*")) + [task / "tests" / "Dockerfile"]
    scripts = [task / "tests" / "test.sh", task / "solution" / "solve.sh"]
    if kind in {"instruction", "all"}:
        hygiene(report, [task / "instruction.md"], task, cfg)
        instr = task / "instruction.md"
        if instr.is_file():
            body = instr.read_text(encoding="utf-8")
            for n, line in enumerate(body.splitlines(), 1):
                if re.search(r"\b(grader|test suite|verifier|pytest|rubric)\b", line, re.I):
                    report.add("V6-instruction", f"{task.name}/instruction.md:{n}", "pipeline word in the instruction (master #5)")
    if kind in {"environment", "all"}:
        hygiene(report, [task / "environment"], task, cfg)
        pins(report, sorted(task.glob("environment/**/Dockerfile*")), task)
        for path in text_files(task / "environment", task) if (task / "environment").is_dir() else []:
            for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if re.search(r"(?<![\w-])nproc(?![\w-])", line) and not line.lstrip().startswith("#"):
                    report.add("V3-portable", f"{path.relative_to(task.parent)}:{n}", "bare nproc (master #106(a))")
    if kind in {"tests", "all"}:
        hygiene(report, [task / "tests"], task, cfg)
        pins(report, [task / "tests" / "Dockerfile", task / "tests" / "test.sh"], task)
        test_count(report, task, minimum)
        reward_literal(report, task)
    if kind in {"seal", "all"}:
        seal_checks(report, task)
    if kind in {"toml", "all"}:
        hygiene(report, [task / "task.toml"], task, cfg)
        toml_checks(report, task, cfg)
    if kind == "all":
        hygiene(report, [task / "solution", task / "rubric.txt"], task, cfg)
        pins(report, [task / "solution" / "solve.sh"], task)
        if (task / "README.md").exists():
            report.add("V5-readme", f"{task.name}/README.md:0", "no README.md in the task (master #103)")
    report.findings = sorted(set(report.findings))
    return report


def check_zip(path: Path) -> Report:
    cfg = rules()
    report = Report()
    patterns = [re.compile(p) for p in cfg.get("hygiene_patterns", []) + cfg.get("hygiene_extra_patterns", [])]
    with zipfile.ZipFile(path) as zf:
        for name in sorted(zf.namelist()):
            if name.endswith("/"):
                continue
            parts = name.split("/")
            if len(parts) >= 3 and parts[1] == "trajectories" and parts[-1] in {"config.json", "result.json"}:
                data = json.loads(zf.read(name).decode("utf-8"))
                for key, value in _walk(data):
                    if key == "trials_dir" and value != "trajectories":
                        report.add("V1-trials_dir", f"{name}:0", f"trials_dir is {value!r}, must be 'trajectories'")
                    elif isinstance(value, str) and re.match(r"^(file://)?evidence-", value):
                        report.add("V1-trials_dir", f"{name}:0", f"{key} carries a workspace round path {value!r}")
            if len(parts) >= 3 and parts[1] == parts[0] and "data" not in parts[2:-1]:
                if parts[-1] == "Dockerfile" or Path(parts[-1]).suffix.lower() in TEXT_SUFFIXES:
                    try:
                        lines = zf.read(name).decode("utf-8").splitlines()
                    except UnicodeDecodeError:
                        continue
                    for n, line in enumerate(lines, 1):
                        for pattern in patterns:
                            match = pattern.search(line)
                            if match:
                                report.add("V1-hygiene", f"{name}:{n}", f"internal marker {match.group(0)!r}")
                                break
                    if parts[-1] == "task.toml" and any(re.match(r"^\s*allow_internet\s*=", l) for l in lines):
                        report.add("V2-network", f"{name}:0", "deprecated allow_internet")
            if len(parts) == 2 and parts[1] == "rubric.txt":
                for n, line in enumerate(zf.read(name).decode("utf-8").splitlines(), 1):
                    for pattern in patterns:
                        if pattern.search(line):
                            report.add("V1-hygiene", f"{name}:{n}", "internal marker in rubric.txt")
                            break
    report.findings = sorted(set(report.findings))
    return report


def _walk(value, key=""):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k, v
            yield from _walk(v, k)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v, key)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=["instruction", "environment", "tests", "seal", "toml", "all", "zip"])
    parser.add_argument("target")
    parser.add_argument("--min-tests", type=int)
    args = parser.parse_args(argv)
    target = Path(args.target)
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    if args.kind == "zip":
        report = check_zip(target)
    else:
        if not target.is_dir():
            print(f"FINDING usage {args.target}:0 not a task directory")
            return 1
        report = check_task(args.kind, target, args.min_tests)
    for finding in report.findings:
        print(finding)
    print(f"v02_checks {args.kind}: {len(report.findings)} finding(s)")
    return 1 if report.findings else 0


if __name__ == "__main__":
    sys.exit(main())
