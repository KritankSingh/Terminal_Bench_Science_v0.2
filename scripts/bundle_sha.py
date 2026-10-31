#!/usr/bin/env python3
"""Print the SUMMARY.txt ``sha=`` value for a task folder (MASTER_CHECKLIST_TBSCI.md #80).

  python3 scripts/bundle_sha.py tasks/<task>              # the workspace task tree
  python3 scripts/bundle_sha.py <unzipped>/<slug>/<slug>  # the shipped inner folder

Run on the shipped inner folder, it prints exactly what a reviewer gets from

  cd <slug>/<slug> && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum

On the workspace tree it hashes only what ships there (instruction.md, task.toml,
environment/, solution/, tests/), leaving out rubric.txt and trajectories/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import WorkflowError, bundle_sha_lines

SHIPPED = ("instruction.md", "task.toml", "environment", "solution", "tests")


def shipped_bundle_sha(task_dir: Path) -> str:
    root = task_dir.resolve()
    files: list[tuple[str, bytes | Path]] = []
    for name in SHIPPED:
        path = root / name
        candidates = [path] if path.is_file() else sorted(path.rglob("*")) if path.is_dir() else []
        for candidate in candidates:
            if candidate.is_symlink():
                raise WorkflowError(f"symlinks are not allowed in a shipped task: {candidate}")
            if candidate.is_file():
                files.append((candidate.relative_to(root).as_posix(), candidate))
    extra = sorted(p.name for p in root.iterdir() if p.name not in SHIPPED + ("rubric.txt", "trajectories"))
    if extra:
        raise WorkflowError(f"{root} holds files that do not ship: {', '.join(extra)}")
    return bundle_sha_lines(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        print(shipped_bundle_sha(args.task_dir))
    except (OSError, WorkflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
