#!/usr/bin/env python3
"""Print the canonical task-source digest used by every gate, seal, and report.

The default output is the full task digest and is byte-for-byte what it has
always been; every seal, review header, `task-digest.txt`, and `collection.json`
in this workspace is bound to it. ``--part agent`` and ``--part grader`` print
the two halves of that surface, which together partition it: the agent half is
what the solver can see (task.toml, instruction.md, environment/, solution/) and
the grader half is what only the verifier sees (tests/).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import WorkflowError, split_digests, task_digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path, help="path to tasks/<task-name>")
    parser.add_argument(
        "--part",
        choices=("full", "agent", "grader"),
        default="full",
        help="which surface to digest (default: full, the canonical task digest)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print all three digests as a JSON object instead of one value",
    )
    args = parser.parse_args(argv)
    task_dir = args.task_dir.resolve()
    try:
        if args.json:
            print(json.dumps(split_digests(task_dir), indent=2, sort_keys=True))
        elif args.part == "full":
            print(task_digest(task_dir))
        else:
            print(split_digests(task_dir)[args.part])
    except WorkflowError as exc:
        print(f"task_digest.py: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
