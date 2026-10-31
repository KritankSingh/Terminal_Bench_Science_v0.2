#!/usr/bin/env python3
"""Lightweight TB-Science authoring-environment doctor."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out.strip()
    except FileNotFoundError:
        return 127, f"not found: {cmd[0]}"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    print(f"repo: {root}")

    checks = [
        (["python3", "--version"], "python3"),
        (["docker", "version", "--format", "{{.Server.Version}}"], "docker"),
        (["docker", "context", "show"], "docker-context"),
        (["stb", "--version"], "stb"),
        (["uv", "--version"], "uv"),
        (["harbor", "--version"], "harbor (optional)"),
    ]

    worst = 0
    for cmd, label in checks:
        code, out = run(cmd)
        status = "OK" if code == 0 else "MISSING/FAIL"
        if code != 0 and label != "harbor (optional)":
            worst = 1
        line = out.splitlines()[0] if out else ""
        print(f"[{status}] {label}: {line}")

    sock = Path("/var/run/docker.sock")
    print(f"[{'OK' if sock.exists() else 'MISS'}] docker.sock: {sock}")

    required_docs = [
        "AGENTS.md",
        "commands.md",
        "docs/WORKFLOW.md",
        "scripts/tbsci.py",
        "docs/TBSCI_HARDENING_RULES.md",
        "docs/TASK_TAXONOMY.md",
        "docs/TASK_COMPONENTS.md",
        ".cursor/rules/00-tbsci-workflow.mdc",
        "scripts/hardening_check.py",
    ]
    for rel in required_docs:
        p = root / rel
        print(f"[{'OK' if p.is_file() else 'MISS'}] {rel}")
        if not p.is_file():
            worst = 1

    if shutil.which("docker"):
        code, out = run(["docker", "context", "show"])
        if code == 0 and out.strip() == "desktop-linux":
            print("[WARN] docker context is desktop-linux — use default on WSL")
            worst = 1

    return worst


if __name__ == "__main__":
    sys.exit(main())
