#!/usr/bin/env python3
"""Bind human review decisions to the exact task and preceding review artifact."""

from __future__ import annotations

import argparse
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from common import REPO_ROOT, WorkflowError, load_json, portable_path, sha256_file, task_digest

REVIEW_VERDICT = "READY FOR DIFFICULTY EVAL"
DIGEST_LINE = re.compile(r"^Task digest: (.+)$", re.MULTILINE)


def check_stage_report(task_dir: Path, path: Path, stage: str,
                       *, review_path: Path | None = None) -> list[str]:
    verdicts = {"review": REVIEW_VERDICT, "difficulty": "READY FOR PACKAGING"}
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
        expected = {"Task": task_dir.name, "Task digest": task_digest(task_dir),
                    "Verdict": verdicts[stage]}
        if stage == "difficulty":
            if review_path is None or not review_path.is_file():
                return ["difficulty report requires the current paper review"]
            expected["Review SHA256"] = f"sha256:{sha256_file(review_path)}"
        for field, value in expected.items():
            matches = re.findall(rf"^{re.escape(field)}: (.+)$", text, flags=re.MULTILINE)
            if matches != [value]:
                detail = f"{stage} report: require exactly one '{field}: {value}' line"
                # The commonest way this fires is not tampering: re-binding a review's
                # digest header changes the review's bytes, so the difficulty report that
                # pins its SHA256 has to be re-headed afterwards. Say so instead of
                # leaving the operator staring at two hashes.
                if field == "Review SHA256":
                    detail += (" — the paper review's bytes changed (a digest re-bind does"
                               " that); re-head the difficulty report with the new"
                               " Review SHA256 and Task digest")
                errors.append(detail)
        if stage == "difficulty":
            for field in ("Evaluation policy", "Trial evidence"):
                values = re.findall(rf"^{field}: (.+)$", text, flags=re.MULTILINE)
                if len(values) != 1 or not values[0].strip() or re.search(r"<[a-z][a-z0-9 -]*>", values[0]):
                    errors.append(f"difficulty report: missing concrete {field} reference")
    except (OSError, UnicodeError, WorkflowError) as exc:
        errors.append(f"{stage} report unavailable: {exc}")
    return errors


# ---------------------------------------------------------------------------------
# Descriptive-only digest re-bind.
#
# A Step 3b review's SUBSTANCE is about the task's agent-facing contract and its grader.
# Neither moves when a descriptive [metadata] key does (task.toml carries no difficulty
# field -- MASTER_CHECKLIST_TBSCI.md #62 -- so this is e.g. expert_time_estimate_hours
# corrected after a rerun, Master #94 item 4). What does move is the FULL
# task digest the review's header pins, which makes check_stage_report fail and
# package_task.py refuse the review. Re-pointing that one line is therefore a book-keeping
# repair, not a re-review -- and the guard below keeps it that way: the re-bind is refused
# unless the Step 2b seal proves both graded surfaces are byte-identical to the ones the
# review was issued against.
# ---------------------------------------------------------------------------------

def seal_digest_lineage(seal: dict[str, Any]) -> list[str]:
    """Every full task digest this seal has bound to, oldest first.

    A seal that was never resealed has a lineage of one. `evidence.py reseal` appends the
    superseded digest each time it re-stamps, so a review issued at any digest in the
    lineage was issued against THIS seal -- and the seal's own checks prove the agent and
    grader surfaces have not moved across the whole lineage.
    """
    lineage: list[str] = []
    record = seal.get("reseal")
    if isinstance(record, dict) and isinstance(record.get("superseded_task_digests"), list):
        lineage = [item for item in record["superseded_task_digests"] if isinstance(item, str)]
    current = seal.get("task_digest")
    if isinstance(current, str):
        lineage.append(current)
    return lineage


def provenance_note(old: str, new: str, seal: dict[str, Any], seal_path: Path,
                    today: str) -> str:
    """The paragraph appended to the review body, so no reader thinks it was re-reviewed."""
    return (
        "\n---\n\n"
        f"**Digest re-bind — {today}.** The header above was re-pointed from\n"
        f"`{old}` to\n"
        f"`{new}` after a descriptive `[metadata]`-only edit to `task.toml`\n"
        f"(a descriptive field such as `expert_time_estimate_hours`; MASTER_CHECKLIST_TBSCI.md\n"
        f"#94 item 4). The agent surface (`{seal.get('agent_digest')}`)\n"
        f"and the grader surface (`{seal.get('grader_digest')}`)\n"
        f"are byte-identical to the ones this review was issued against; the Step 2b seal\n"
        f"`{portable_path(seal_path)}` records that as\n"
        f"`reseal.reason`. **Nothing in this review was re-examined and no finding was\n"
        f"re-opened — only the digest header moved.** Written by\n"
        f"`scripts/stage_reports.py rebind-review`.\n"
    )


def rebind_review_digest(task_dir: Path, review_path: Path, seal_path: Path,
                         *, today: str | None = None) -> tuple[str | None, list[str], list[str]]:
    """Rewrite only a review's ``Task digest:`` line, under the descriptive-only guard.

    Returns ``(text, notes, errors)``. A ``None`` text with no errors means the review is
    already bound to the current digest and nothing should be written.
    """
    from evidence import check_seal  # local: package_task imports this module at load time

    task_dir = task_dir.resolve()
    if not seal_path.is_file():
        return None, [], [f"no Step 2b seal at {portable_path(seal_path)}; "
                          "a re-bind needs the seal that proves the surfaces are unmoved"]
    seal_errors = check_seal(task_dir, seal_path)
    if seal_errors:
        return None, [], [
            "the Step 2b seal does not bind to the current task, so it cannot license a "
            "digest re-bind: " + "; ".join(seal_errors),
            "run scripts/gate_step2b.sh --reseal-only (descriptive edit) or the full gate "
            "(behavioral edit) first"]
    try:
        seal = load_json(seal_path)
        text = review_path.read_text(encoding="utf-8")
        current = task_digest(task_dir)
    except (OSError, UnicodeError, WorkflowError) as exc:
        return None, [], [str(exc)]
    if not isinstance(seal, dict):
        return None, [], ["Step 2b seal must be a JSON object"]

    found = DIGEST_LINE.findall(text)
    if len(found) != 1:
        return None, [], [f"{portable_path(review_path)}: require exactly one "
                          f"'Task digest: ...' line, found {len(found)}"]
    old = found[0].strip()
    if old == current:
        return None, [f"{portable_path(review_path)} already binds to {current}"], []

    lineage = seal_digest_lineage(seal)
    if old not in lineage:
        return None, [], [
            f"the review binds to {old}, which is not a digest this seal has carried "
            f"({', '.join(lineage)}); it was issued against a different task revision, so "
            "it must be re-reviewed rather than re-bound"]

    for field, value in (("Task", task_dir.name), ("Verdict", REVIEW_VERDICT)):
        if re.findall(rf"^{re.escape(field)}: (.+)$", text, flags=re.MULTILINE) != [value]:
            return None, [], [f"{portable_path(review_path)}: not a current Step 3b review "
                              f"(require exactly one '{field}: {value}' line)"]

    today = today or date.today().isoformat()
    rewritten = DIGEST_LINE.sub(f"Task digest: {current}", text, count=1)
    rewritten = rewritten.rstrip("\n") + "\n" + provenance_note(old, current, seal, seal_path, today)

    # Prove the result on disk rather than by construction: the appended paragraph must
    # not have introduced a second header line that check_stage_report would reject.
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as handle:
        handle.write(rewritten)
        probe = Path(handle.name)
    try:
        probe_errors = check_stage_report(task_dir, probe, "review")
    finally:
        probe.unlink(missing_ok=True)
    if probe_errors:
        return None, [], ["the re-bound review would not validate: " + "; ".join(probe_errors)]

    notes = [f"task digest: {old} -> {current}",
             f"agent digest: {seal.get('agent_digest')} UNCHANGED",
             f"grader digest: {seal.get('grader_digest')} UNCHANGED",
             "review body: unchanged except for one appended provenance paragraph"]
    return rewritten, notes, []


def command_rebind_review(args: argparse.Namespace) -> int:
    task_dir = args.task_dir.resolve()
    if not task_dir.is_dir():
        print(f"Review re-bind: FAIL\n- task directory not found: {task_dir}")
        return 1
    slug = task_dir.name
    review = (args.review or REPO_ROOT / "artifacts" / "reviews" / f"{slug}.md").resolve()
    default_copy = REPO_ROOT / "authoring" / slug / "step3b-review.md"
    copies = [path.resolve() for path in (args.copy or ([default_copy] if default_copy.is_file() else []))]
    seal = (args.seal or REPO_ROOT / "artifacts" / "gates" / slug / "step2b.json").resolve()
    if not review.is_file():
        print(f"Review re-bind: FAIL\n- review not found: {portable_path(review)}")
        return 1

    text, notes, errors = rebind_review_digest(task_dir, review, seal)
    if errors:
        print("Review re-bind: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    if text is None:
        print("Review re-bind: PASS (nothing to do)")
        for note in notes:
            print(f"- {note}")
        return 0
    if args.dry_run:
        print("Review re-bind: DRY RUN")
        for note in notes:
            print(f"- {note}")
        print(f"- would rewrite: {', '.join(portable_path(p) for p in [review, *copies])}")
        return 0

    for path in [review, *copies]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    divergent = [portable_path(p) for p in copies if p.read_bytes() != review.read_bytes()]
    if divergent:
        print("Review re-bind: FAIL")
        print(f"- copies are not byte-identical to the review: {', '.join(divergent)}")
        return 1
    remaining = check_stage_report(task_dir, review, "review")
    if remaining:
        print("Review re-bind: FAIL")
        for error in remaining:
            print(f"- {error}")
        return 1

    print("Review re-bind: PASS")
    for note in notes:
        print(f"- {note}")
    for path in [review, *copies]:
        print(f"- wrote {portable_path(path)}")
    print(f"Review SHA256: sha256:{sha256_file(review)}")
    print("Next: re-head authoring/<task>/master-checklist.md's `Task digest:` after re-walking it, and "
          "note the difficulty report pins the review's SHA256, so re-head "
          f"artifacts/difficulty/{slug}.md with the Task digest and Review SHA256 above.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    rebind = subparsers.add_parser(
        "rebind-review",
        help="re-point a Step 3b review's 'Task digest:' header at the current digest "
             "after a descriptive [metadata]-only edit (never a re-review)")
    rebind.add_argument("task_dir", type=Path)
    rebind.add_argument("--review", type=Path, default=None,
                        help="default: artifacts/reviews/<task>.md")
    rebind.add_argument("--copy", type=Path, action="append", default=None,
                        help="further copies to keep byte-identical "
                             "(default: authoring/<task>/step3b-review.md)")
    rebind.add_argument("--seal", type=Path, default=None,
                        help="default: artifacts/gates/<task>/step2b.json")
    rebind.add_argument("--dry-run", action="store_true")
    rebind.set_defaults(func=command_rebind_review)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
