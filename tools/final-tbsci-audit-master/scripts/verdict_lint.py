#!/usr/bin/env python3
"""Lint one finished audit run: verdict.json against the SKILL.md output contract.

    python3.11 verdict_lint.py <run-dir>            # exit 0 = clean, 1 = errors

Errors (exit 1):
  * verdict.json still a skeleton: `status`/`note` present, or any "PENDING" value left
  * a required key or an enum value is missing or wrong
  * a static-screen finding is not dispositioned (confirmed or discarded with a reason), a
    confirmed BLOCKER/MAJOR flag is not carried by a finding's `screen_code`, or a LEAD is unanswered
  * a finding lacks gate / evidence / why_it_matters / fix
  * counts do not equal the findings by severity
  * `verdict` disagrees with the closing-line rule (blockers, majors, package evidence,
    upheld trial flags, a cheat attack that passed — and, under `terminus`, ANY minor:
    MASTER_CHECKLIST_TBSCI.md ships nothing with an open finding of any severity)
  * task_digest differs from static_screen.json
Warnings (printed, exit 0): evidence span very long; manual_probes.txt still a template;
the extracted task no longer hashes to task_digest (modified after the audit).

The closing line is DERIVED here, never typed: see closing_line().
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

GATE_KEYS = ("T", "A", "B", "C", "D", "E", "F", "G", "H", "I", "K")
GATE_VALUES = {"T": {"pass", "fail", "n/a"}, "H": {"pass", "fail", "no-evidence"}, "I": {"pass", "fail", "unmeasured"}}
DEFAULT_GATE = {"pass", "fail"}
SEVERITIES = ("BLOCKER", "MAJOR", "MINOR")
PE_VERDICTS = {"valid", "incomplete", "stale", "no-evidence"}
TOP_KEYS = ("task_name", "profile", "bundle_shape", "task_digest", "package_evidence", "gates", "static_screen",
            "alignment", "ground_truth_provenance", "execution_isolation", "must_execute", "nop_passable_tests",
            "oracle_delta", "cheat_simulation", "difficulty_source", "proposal_rubric", "trial_evidence",
            "trial_analysis", "runtime_evidence", "findings", "additional_checks", "counts", "verdict")

CLOSING = {"ready": "✅ Ready to Submit", "revise": "🔴 Revision Required", "decline": "⛔ Decline"}


def find_pending(obj, path=""):
    if isinstance(obj, str):
        return [path] if obj.strip() == "PENDING" else []
    if isinstance(obj, dict):
        return [p for k, v in obj.items() for p in find_pending(v, f"{path}.{k}" if path else k)]
    if isinstance(obj, list):
        return [p for i, v in enumerate(obj) for p in find_pending(v, f"{path}[{i}]")]
    return []


def upheld_trial_flags(ta):
    """trial_analysis values that send the task back."""
    bad = []
    for k in ("task_specification", "reward_hacking"):
        if str(ta.get(k, "")).lower() == "fail":
            bad.append(k)
    for k in ("difficulty_crux", "near_miss", "refusals", "low_timeout"):
        if str(ta.get(k, "")).lower() in ("upheld", "fail"):
            bad.append(k)
    return bad


def expected_verdict(v):
    """The closing-line rule from SKILL.md, applied to the verdict's own numbers."""
    if v.get("verdict") == "decline":
        return "decline"
    c = v.get("counts", {})
    pe = (v.get("package_evidence") or {}).get("verdict")
    cheat_pass = any(isinstance(x, dict) and x.get("passes") is True for x in (v.get("cheat_simulation") or []))
    # MASTER_CHECKLIST_TBSCI.md: severity is for triage only — a task ships with zero
    # BLOCKER, zero MAJOR and zero MINOR under the program (terminus) standard.
    minor_blocks = v.get("profile", "terminus") == "terminus" and c.get("minor", 0)
    if c.get("blocker", 0) or c.get("major", 0) or minor_blocks or pe != "valid" \
            or upheld_trial_flags(v.get("trial_analysis") or {}) or cheat_pass:
        return "revise"
    return "ready"


def closing_line(v):
    return CLOSING[expected_verdict(v)]


def lint(run):
    errors, warnings = [], []
    vp = os.path.join(run, "verdict.json")
    if not os.path.isfile(vp):
        return [f"{vp} not found"], []
    try:
        v = json.load(open(vp, encoding="utf-8"))
    except ValueError as e:
        return [f"verdict.json does not parse: {e}"], []

    if "status" in v or "note" in v:
        errors.append("verdict.json is still a skeleton: delete `status` and `note` once judgement is complete")
    pend = find_pending(v)
    if pend:
        errors.append(f"{len(pend)} value(s) still PENDING: {', '.join(pend[:8])}{' …' if len(pend) > 8 else ''}")
    for k in TOP_KEYS:
        if k not in v:
            errors.append(f"missing key: {k}")
    if errors and any(e.startswith("missing key") for e in errors):
        return errors, warnings

    # enums
    if v["profile"] not in ("terminus", "upstream"):
        errors.append(f"profile {v['profile']!r} is not terminus|upstream")
    if v["bundle_shape"] not in ("checklist-package", "dir", "zip-root", "zip-enclosing-folder"):
        errors.append(f"bundle_shape {v['bundle_shape']!r} invalid")
    pe = v["package_evidence"]
    if pe.get("verdict") not in PE_VERDICTS:
        errors.append(f"package_evidence.verdict {pe.get('verdict')!r} not in {sorted(PE_VERDICTS)}")
    for g in GATE_KEYS:
        val = str(v["gates"].get(g, "")).lower()
        allowed = GATE_VALUES.get(g, DEFAULT_GATE)
        if val not in allowed:
            errors.append(f"gates.{g} = {v['gates'].get(g)!r}; allowed {sorted(allowed)}")
    if v["verdict"] not in CLOSING:
        errors.append(f"verdict {v['verdict']!r} not in ready|revise|decline")
    for k, val in (v.get("proposal_rubric") or {}).items():
        if val not in ("pass", "fail"):
            errors.append(f"proposal_rubric.{k} = {val!r}; allowed pass|fail")
    for i, x in enumerate(v["cheat_simulation"] if isinstance(v["cheat_simulation"], list) else []):
        if not (isinstance(x, dict) and {"attack", "passes", "why"} <= set(x) and isinstance(x["passes"], bool)):
            errors.append(f"cheat_simulation[{i}] needs attack, passes (bool), why")
    if not isinstance(v["cheat_simulation"], list) or not v["cheat_simulation"]:
        errors.append("cheat_simulation is empty: SKILL.md step 8 is not optional — record every attack you ran")

    # findings
    for i, f in enumerate(v["findings"]):
        if f.get("severity") not in SEVERITIES:
            errors.append(f"findings[{i}].severity {f.get('severity')!r} not BLOCKER|MAJOR|MINOR")
        for k in ("gate", "evidence", "why_it_matters", "fix"):
            if not str(f.get(k, "")).strip():
                errors.append(f"findings[{i}] has no {k} — a finding without quoted evidence and a fix does not count")
        if len(str(f.get("evidence", ""))) > 600:
            warnings.append(f"findings[{i}].evidence is {len(f['evidence'])} chars — quote the decisive line, not the file")
    tally = {s.lower(): sum(1 for f in v["findings"] if f.get("severity") == s) for s in SEVERITIES}
    if v["counts"] != tally:
        errors.append(f"counts {v['counts']} do not equal the findings by severity {tally}")

    # the static screen must be dispositioned, not skimmed
    sp = os.path.join(run, "static_screen.json")
    screen = None
    if os.path.isfile(sp):
        try:
            screen = json.load(open(sp, encoding="utf-8"))
        except ValueError:
            screen = None
    if screen and "task_digest" in screen:
        if v["task_digest"] != screen["task_digest"]:
            errors.append(f"task_digest {v['task_digest'][:16]}… differs from static_screen.json {screen['task_digest'][:16]}…")
        ss = v["static_screen"]
        confirmed = {(x if isinstance(x, str) else x.get("code")) for x in ss.get("confirmed", [])}
        discarded = {x.get("code"): x.get("why", "") for x in ss.get("discarded", []) if isinstance(x, dict)}
        answered = {x.get("code"): x.get("answer", "") for x in ss.get("leads_answered", []) if isinstance(x, dict)}
        for c in sorted({f["code"] for f in screen.get("findings", [])}):
            if c not in confirmed and not str(discarded.get(c, "")).strip():
                errors.append(f"static-screen finding {c} is neither confirmed nor discarded with a reason")
        # a confirmed BLOCKER/MAJOR flag must become a finding (SKILL.md step 3), else "Ready" could slip past it
        sev_of = {f["code"]: f["severity"] for f in screen.get("findings", [])}
        covered = set()
        for f in v["findings"]:
            sc = f.get("screen_code") or []
            covered |= {sc} if isinstance(sc, str) else set(sc)
        for c in sorted(confirmed):
            if sev_of.get(c) in ("BLOCKER", "MAJOR") and c not in covered:
                errors.append(f"screen flag {c} ({sev_of[c]}) is confirmed but no finding carries screen_code {c!r}")
        for c in sorted({f["code"] for f in screen.get("leads", [])}):
            if not str(answered.get(c, "")).strip():
                errors.append(f"static-screen LEAD {c} has no answer in static_screen.leads_answered")
        if ss.get("flags") != len(screen.get("findings", [])):
            errors.append(f"static_screen.flags {ss.get('flags')} != {len(screen.get('findings', []))} findings in static_screen.json")
    else:
        errors.append("static_screen.json missing or unreadable in the run directory")

    # the verdict must agree with the closing-line rule
    exp = expected_verdict(v)
    if v["verdict"] != exp:
        why = []
        c = v["counts"]
        if c["blocker"] or c["major"] or (v["profile"] == "terminus" and c["minor"]):
            why.append(f"{c['blocker']} BLOCKER / {c['major']} MAJOR / {c['minor']} MINOR")
        if pe.get("verdict") != "valid":
            why.append(f"package_evidence.verdict is {pe.get('verdict')!r}, not 'valid'")
        if upheld_trial_flags(v["trial_analysis"]):
            why.append(f"upheld trial flags {upheld_trial_flags(v['trial_analysis'])}")
        if any(isinstance(x, dict) and x.get("passes") is True for x in v["cheat_simulation"]):
            why.append("a cheat attack passed")
        errors.append(f"verdict is {v['verdict']!r} but the closing-line rule gives {exp!r}" + (f" ({'; '.join(why)})" if why else ""))
    if v["verdict"] == "ready" and any(s in pe.get("verdict", "") for s in ("no-evidence", "stale", "incomplete")):
        errors.append("cannot be ready without valid package evidence")

    # advisory
    mp = os.path.join(run, "manual_probes.txt")
    if os.path.isfile(mp) and "<<UNFILLED>>" in open(mp, encoding="utf-8", errors="replace").read():
        warnings.append("manual_probes.txt still contains <<UNFILLED>> blocks — the hand-run probes are not on record")
    task_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(run)))), "extracted", os.path.basename(os.path.dirname(os.path.abspath(run))))
    # A checklist package extracts as <slug>/ holding the inner <slug>/ task folder, and the
    # screen hashes that inner folder -- hash the same thing here, or this warning always fires.
    inner = os.path.join(task_dir, os.path.basename(task_dir))
    if os.path.isdir(task_dir) and not os.path.isfile(os.path.join(task_dir, "task.toml")) \
            and os.path.isfile(os.path.join(inner, "task.toml")):
        task_dir = inner
    if os.path.isdir(task_dir):
        try:
            sys.path.insert(0, HERE)
            import tbsci_static_screen as screen_mod
            if screen_mod.task_digest(task_dir) != v["task_digest"]:
                warnings.append("extracted task no longer hashes to task_digest — it changed after this audit ran; re-run audit")
        except Exception:  # noqa: BLE001
            pass
    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    run = sys.argv[1].rstrip("/")
    errors, warnings = lint(run)
    for w in warnings:
        print(f"  warn  {w}")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        print(f"LINT_FAIL {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    v = json.load(open(os.path.join(run, "verdict.json"), encoding="utf-8"))
    print(f"LINT_OK  {closing_line(v)}  ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
