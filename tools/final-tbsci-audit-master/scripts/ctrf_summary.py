#!/usr/bin/env python3
"""Summarise one or more pytest CTRF reports (ctrf.json) and, optionally,
diff their test names against the shipped suite (TB-Science: any tests/**/test_*.py).

  python3 ctrf_summary.py <ctrf.json> [...] [--task <task dir>] [--expect oracle|nop|cheat] [--pretty]

Use it to verify with your own eyes:
  * oracle:  every row "passed" (every run)                     -> --expect oracle  (Master #72)
  * nop:     every row "failed" — not error/skipped/passed       -> --expect nop     (Master #73)
  * cheat:   not N/N          (a cheat oracle must not pass)  -> --expect cheat
  * evidence binds to the shipped tests: names in the ctrf == names in
    tests/test_*.py (a mismatch means the run graded a different task)

Exit 2 when an --expect check fails or the suite is stale; 0 otherwise.
"""
import argparse
import glob
import json
import os
import re
import sys


def load(p):
    d = json.load(open(p))
    res = d.get("results") or d
    tests = res.get("tests") or []
    summ = res.get("summary") or {}
    by = {}
    for t in tests:
        by.setdefault(t.get("status", "?"), []).append(t.get("name", ""))
    return {
        "file": p,
        "tool": (res.get("tool") or {}).get("name"),
        "total": summ.get("tests", len(tests)),
        "passed": summ.get("passed", len(by.get("passed", []))),
        "failed": summ.get("failed", len(by.get("failed", []))),
        "skipped": summ.get("skipped", len(by.get("skipped", []))),
        "passed_names": by.get("passed", []),
        "failed_names": by.get("failed", []),
        "names": [t.get("name", "") for t in tests],
        "not_failed": [f"{t.get('name', '')}={t.get('status', '?')}" for t in tests if t.get("status") != "failed"],
        "not_passed": [f"{t.get('name', '')}={t.get('status', '?')}" for t in tests if t.get("status") != "passed"],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ctrf", nargs="+")
    ap.add_argument("--task")
    ap.add_argument("--expect", choices=["oracle", "nop", "cheat"])
    ap.add_argument("--pretty", action="store_true")
    a = ap.parse_args()

    shipped = None
    if a.task:
        names = set()
        for p in glob.glob(os.path.join(a.task, "tests", "**", "test_*.py"), recursive=True):
            names |= set(re.findall(r'(?m)^\s*(?:async\s+)?def\s+(test_\w+)\s*\(',
                                    open(p, encoding="utf-8", errors="replace").read()))
        shipped = names or None
    out, bad = [], False
    for p in a.ctrf:
        try:
            r = load(p)
        except Exception as e:  # noqa: BLE001
            out.append({"file": p, "error": str(e)})
            bad = True
            continue
        r["verdict"] = "ok"
        # per-test CTRF must actually be per-test: named rows, no duplicates
        if not r["names"] or any(not n for n in r["names"]):
            r["verdict"] = "INVALID-CTRF: rows without a test name — the report is not per-test"
            bad = True
        elif len(set(r["names"])) != len(r["names"]):
            dupes = sorted({n for n in r["names"] if r["names"].count(n) > 1})
            r["verdict"] = f"INVALID-CTRF: duplicate test ids {dupes[:5]} — per-test rows must be uniquely identified"
            bad = True
        elif r["total"] != len(r["names"]):
            r["verdict"] = f"INVALID-CTRF: summary claims {r['total']} tests but {len(r['names'])} rows are present"
            bad = True
        if a.expect == "oracle" and (r["passed"] != r["total"] or r["not_passed"]):
            r["verdict"] = f"ORACLE-FAIL: {r['passed']}/{r['total']} — rows not passed: {r['not_passed'][:8]}"
            bad = True
        if a.expect == "nop" and r["passed"] != 0:
            r["verdict"] = f"NOP-PASS: {r['passed']}/{r['total']} pass with no work — {r['passed_names'][:10]}"
            bad = True
        elif a.expect == "nop" and r["not_failed"]:
            r["verdict"] = (f"NOP-NOT-FAILED: {len(r['not_failed'])} row(s) are not status \"failed\" "
                            f"(error/skipped masks a real result, Master #73): {r['not_failed'][:8]}")
            bad = True
        if a.expect == "cheat" and r["passed"] == r["total"] and r["total"]:
            r["verdict"] = f"HACKED: the cheat oracle passed {r['passed']}/{r['total']} — hardening failed"
            bad = True
        if shipped is not None:
            got = {n.split("::")[-1].split("[")[0] for n in r["names"]}
            if got != shipped:
                r["stale"] = {"missing_in_ctrf": sorted(shipped - got), "extra_in_ctrf": sorted(got - shipped),
                              "ctrf_count": len(got), "shipped_count": len(shipped)}
                r["verdict"] += " | STALE: ctrf does not match the shipped suite"
                bad = True
        out.append(r)
    print(json.dumps({"reports": out, "shipped_test_count": len(shipped) if shipped is not None else None},
                     indent=1 if a.pretty else None))
    sys.exit(2 if bad else 0)


if __name__ == "__main__":
    main()
