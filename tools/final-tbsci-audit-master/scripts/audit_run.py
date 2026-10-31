#!/usr/bin/env python3
"""One audit run: run the three legs on one extracted task and write the evidence
files plus a verdict.json SKELETON into the run directory.

    python3.11 audit_run.py <task-dir> <run-dir> [--profile terminus|upstream] [--shape dir|zip-root|zip-enclosing-folder]

Writes into <run-dir>:
    static_screen.json    tbsci_static_screen.py output (flags, leads, task digest)
    trial_evidence.json   trial_evidence.py over <task>/trajectories/ (or a no-evidence stub)
    ctrf_summary.json     ctrf_summary.py over every oracle / NOP trial's verifier/ctrf.json
    manual_probes.txt     template for the attacks YOU run by hand (SKILL.md steps 5, 6, 8)
    verdict.json          mechanical fields filled; every judgement field is the string
                          "PENDING" and "status" is "pending_judgement" until you replace them

Nothing here judges. A flag is a lead, a pass is silence.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PENDING = "PENDING"


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def jload(text):
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


def write(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(obj if isinstance(obj, str) else json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def rubric_summary(task):
    p = os.path.join(task, "rubric.txt")
    if not os.path.isfile(p):
        return "missing", {"positive_total": 0, "negative_criteria": 0, "scores_ok": False}
    pos = neg = 0
    for line in open(p, encoding="utf-8", errors="replace"):
        m = re.search(r",\s*([+-]?\d+)\s*$", line.strip())
        if m:
            n = int(m.group(1))
            pos += max(n, 0)
            neg += n < 0
    return "valid", {"positive_total": pos, "negative_criteria": neg, "scores_ok": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("run")
    ap.add_argument("--profile", choices=["terminus", "upstream"], default="terminus")
    ap.add_argument("--shape", default="dir")
    a = ap.parse_args()
    task, run_dir = a.task.rstrip("/"), a.run.rstrip("/")
    # DELIVERY_CHECKLIST.md layout: <task-slug>/<task-slug>/task.toml, with
    # rubric.txt / oracle-nop-evidence/ / trajectories/ as siblings of the inner
    # folder.  `pkg` is what the screen takes; `inner` is what needs tests/.
    pkg = task
    inner = task
    if not os.path.exists(os.path.join(task, "task.toml")):
        cand = [d for d in sorted(os.listdir(task))
                if os.path.isdir(os.path.join(task, d)) and os.path.exists(os.path.join(task, d, "task.toml"))]
        if len(cand) == 1:
            inner = os.path.join(task, cand[0])
    slug = os.path.basename(os.path.abspath(inner))
    os.makedirs(run_dir, exist_ok=True)

    # 1 · static screen
    rc, out, err = run([sys.executable, os.path.join(HERE, "tbsci_static_screen.py"), "--task", pkg,
                        "--profile", a.profile, "--slug", slug, "--pretty"])
    screen = jload(out)
    write(os.path.join(run_dir, "static_screen.json"), out if screen is not None else json.dumps({"error": err or out}))
    write(os.path.join(run_dir, "static_screen.exit"), f"{rc}\n")
    if screen is None or "error" in screen:
        print(f"STATIC_SCREEN_FAIL {(screen or {}).get('error') or err.strip()[:300]}", file=sys.stderr)
        return 3
    print(f"static_screen: exit={rc} verdict={screen.get('screen_verdict')} counts={screen.get('counts')}")

    # 2 · trial evidence
    runs = [d for d in (os.path.join(pkg, "trajectories"), os.path.join(pkg, "oracle-nop-evidence"))
            if os.path.isdir(d)]
    trial = None
    if runs:
        rc2, out2, err2 = run([sys.executable, os.path.join(HERE, "trial_evidence.py"), "--runs", *runs,
                               "--task", inner, "--profile", a.profile, "--pretty"])
        trial = jload(out2) or {"error": err2.strip() or out2.strip()}
    else:
        trial = {"error": "no trajectories/ or oracle-nop-evidence/ directory in the package"}
    write(os.path.join(run_dir, "trial_evidence.json"), trial)
    print("trial_evidence:", "error: " + trial["error"] if "error" in trial else f"flags={len(trial.get('flags', []))}")

    # 3 · per-trial ctrf for the controls
    ctrf = {"oracle": [], "nop": []}
    for arm, expect in (("oracle", "oracle"), ("nop", "nop")):
        for rec in ((trial.get("arms") or {}).get(arm) or {}).get("trials", []):
            p = os.path.join(rec["trial"], "verifier", "ctrf.json")
            if not os.path.isfile(p):
                p = os.path.join(rec["trial"], "ctrf.json")       # checklist control dirs are flat
            if not os.path.isfile(p):
                ctrf[arm].append({"file": p, "error": "no ctrf.json in this trial"})
                continue
            _, o, e = run([sys.executable, os.path.join(HERE, "ctrf_summary.py"), p, "--task", inner, "--expect", expect])
            ctrf[arm].append(jload(o) or {"file": p, "error": (e or o).strip()[:300]})
    write(os.path.join(run_dir, "ctrf_summary.json"), ctrf)

    # 4 · manual probes template
    write(os.path.join(run_dir, "manual_probes.txt"), MANUAL_TEMPLATE.format(slug=slug, digest=screen["task_digest"][:16]))

    # 5 · verdict skeleton
    write(os.path.join(run_dir, "verdict.json"), skeleton(pkg, inner, slug, a, screen, trial, ctrf))
    print(f"AUDIT_RUN_OK {run_dir}")
    return 0


MANUAL_TEMPLATE = """# manual_probes.txt — {slug} (digest {digest}…)
# The attacks and reasoning YOU ran by hand. Scripts cannot do these; this file is the evidence
# verdict.json quotes. Replace every block; delete this line and every <<UNFILLED>> marker.
# One block per probe: what you did, the exact patch or command, the decisive output line.

<<UNFILLED>>
## Step 5 · Ground-truth provenance and grade-time reachability (attacker's seat)
EXPECTED VALUE: <name>   ORIGIN: sealed constant | sealed reference | derived from an artifact
GRADED PROCESS THAT RUNS AGENT CODE: <which>   UID: <root|12000>   /logs/verifier 700 before it runs: <yes|no>
ONE open('/tests/...') FROM THE GRADED PROCESS RETURNS: <...>
MUST EXECUTE FOR THE SUITE TO PASS: <what the agent has to run, or 'nothing'>

<<UNFILLED>>
## Step 6 · NOP reasoning
TEST: <name>   PASSABLE WITH NO WORK: <yes|no>   WHY: <...>

<<UNFILLED>>
## Step 7 · Oracle diff
FILE: <path>   BROKEN->FIXED DELTA: <one line>   REQUIREMENTS COVERED: <...>

<<UNFILLED>>
## Step 8 · Cheat simulation (one block per attack)
ATTACK: <hardcode | force success flag | fix one of several defects | stub graded component | hand-written artifact | edit artifact the verifier derives expectations from | shim a tool the verifier calls | planted daemon | protected file edited | answer in history/layers/online>
PATCH/COMMAND: <exact>
PASSES: <yes|no>
DECISIVE LINE: <quote, under ~200 chars>
"""


def skeleton(task, inner, slug, a, screen, trial, ctrf):
    findings_all = (screen.get("findings") or []) + (screen.get("leads") or [])
    codes = sorted({f["code"] for f in screen.get("findings") or []})
    rubric_state, rubric_sum = rubric_summary(task)
    if any(c.startswith("T3-RUBRIC") for c in codes):
        rubric_state = "missing" if "T3-RUBRIC-MISSING" in codes else "malformed"
        rubric_sum["scores_ok"] = False

    have_trial = "error" not in trial
    rnd = trial.get("required_round") or {}
    arms = trial.get("arms") or {}
    ev = trial.get("evidence") or {}
    n_or = (arms.get("oracle") or {}).get("attempts", 0)
    n_nop = (arms.get("nop") or {}).get("attempts", 0)
    stale = list(ev.get("stale_traces", [])) + [x["trial"] for x in trial.get("stale_evidence", [])]
    # The round's one binding is trajectories/SUMMARY.txt's `sha=` — the BUNDLE sha
    # recomputed over the inner task folder (Master #80) — plus evidence mtimes newer
    # than every graded file (Master #75) and ctrf test counts that match the
    # shipped suite (Master #53).  Any of those failing makes the evidence stale.
    binding = [f["where"] for f in screen.get("findings", [])
               if f["code"] in ("T3-BUNDLE-SHA", "T3-MTIME", "T3-TESTCOUNT")]
    stale += binding
    unbound = []
    unrelated = [f["where"] for f in screen.get("findings", []) if f["code"] == "T3-TRAJ" and "different task" in f["evidence"]]
    untrunc = not ev.get("truncated") and not ev.get("empty") if have_trial else False
    attempts = rnd.get("attempts", 0)
    efforts = rnd.get("efforts", [])
    digest_bound = have_trial and not stale and not unrelated

    if not have_trial:
        pe_verdict = "no-evidence"
    elif stale or unbound or unrelated:
        pe_verdict = "stale"
    elif (rubric_state != "valid" or attempts < 5 or not efforts or n_or < 3 or not untrunc
          or n_nop < 2
          or any(f["code"] in ("T3-TRAJ", "T3-RUBRIC", "T3-RUBRIC-MISSING", "T3-CONTROLS", "T3-SUMMARY",
                               "T3-RUBRIC-SCORE", "T3-RUBRIC-SCORE-DUP", "T3-EFFORT", "T3-LAYOUT", "T3-BANNED",
                               "T3-ROUND-NAME", "T3-NOP-ERROR", "T3-DUPLICATE", "T3-AGENT-FILES", "T3-EXCEPTION",
                               "T3-PII", "T3-REWARD-HACK", "T3-RUN-ORDER") for f in screen.get("findings", []))):
        pe_verdict = "incomplete"
    else:
        pe_verdict = "valid"

    def ctrf_pair(arm):
        out = []
        for r in ctrf[arm]:
            rep = (r.get("reports") or [{}])[0]
            out.append({"reward": None, "ctrf": f"{rep.get('passed')}/{rep.get('total')}" if rep.get("total") is not None else None})
        return out

    or_runs = ctrf_pair("oracle")
    for rec, pair in zip(((arms.get("oracle") or {}).get("trials", [])), or_runs):
        pair["reward"] = rec.get("reward")
    nop_trials = (arms.get("nop") or {}).get("trials", [])
    nop = ctrf_pair("nop")[0] if ctrf["nop"] else {"reward": None, "ctrf": None}
    if nop_trials:
        nop["reward"] = nop_trials[0].get("reward")

    return {
        "status": "pending_judgement",
        "note": "Mechanical fields are filled. Replace every \"PENDING\" and delete this status/note before lint.",
        "task_name": screen.get("task") or slug,
        "profile": a.profile,
        "bundle_shape": a.shape if a.shape != "dir" else screen.get("bundle_shape", "dir"),
        "task_digest": screen["task_digest"],
        "package_evidence": {
            "rubric_txt": rubric_state,
            "rubric_summary": rubric_sum,
            "round": {"model": "gpt-5.6", "effort": "xhigh" if efforts else None, "attempts": attempts, "need": 5,
                      "untruncated": untrunc},
            "controls": {"oracle": n_or, "nop": n_nop, "need": {"oracle": 3, "nop": 2}},
            "digest_bound": digest_bound,
            "stale_or_unrelated": sorted(set(stale + unbound + unrelated)),
            "verdict": pe_verdict,
        },
        "gates": {g: PENDING for g in ("T", "A", "B", "C", "D", "E", "F", "G", "H", "I", "K")},
        "static_screen": {"ran": True, "flags": len(screen.get("findings") or []),
                          "confirmed": [], "discarded": [], "leads_answered": [],
                          "_codes_to_disposition": codes,
                          "_leads_to_answer": sorted({f["code"] for f in screen.get("leads") or []})},
        "alignment": {"graded_unlicensed": PENDING, "stated_ungraded": PENDING, "do_not_modify_unenforced": PENDING,
                      "licence_sources_used": PENDING},
        "ground_truth_provenance": {"sealed": PENDING, "from_artifacts": PENDING, "verdict": PENDING},
        "execution_isolation": {"runs_agent_code": PENDING, "uid": PENDING, "setpriv_reuid_12000": PENDING,
                                "reward_dir_700_before": PENDING, "tests_700_in_dockerfile": PENDING,
                                "negative_control": PENDING, "verdict": PENDING},
        "must_execute": PENDING,
        "nop_passable_tests": PENDING,
        "oracle_delta": {"files": PENDING, "readable_as_defect": PENDING, "scope_matches_instruction": PENDING,
                         "precomputed_artifact": PENDING},
        "cheat_simulation": PENDING,
        "difficulty_source": PENDING,
        "proposal_rubric": {k: PENDING for k in ("verifiable", "well_specified", "solvable", "difficult",
                                                 "interesting", "outcome_verified")},
        "trial_evidence": {"ran": have_trial,
                           "per_arm": {k: {"attempts": v.get("attempts"), "solved": v.get("solved"), "rate": v.get("rate")}
                                       for k, v in arms.items()},
                           "pooled_pass_at_1": trial.get("pooled_pass_at_1"),
                           "saturated": trial.get("saturated"), "all_fail": trial.get("all_fail"),
                           "flags": trial.get("flags", [trial.get("error")] if not have_trial else [])},
        "trial_analysis": {k: PENDING for k in ("task_specification", "reward_hacking", "difficulty_crux",
                                                 "near_miss", "refusals", "low_timeout")},
        "runtime_evidence": {"env_builds": "unknown", "verifier_builds": "unknown", "oracle_runs": or_runs,
                             "nop": nop, "cheat": {"reward": ((arms.get("cheat") or {}).get("trials") or [{}])[0].get("reward")},
                             "ctrf_matches_suite": have_trial and not trial.get("stale_evidence")},
        "findings": [],
        "additional_checks": [],
        "counts": {"blocker": 0, "major": 0, "minor": 0},
        "verdict": PENDING,
    }


if __name__ == "__main__":
    sys.exit(main())
