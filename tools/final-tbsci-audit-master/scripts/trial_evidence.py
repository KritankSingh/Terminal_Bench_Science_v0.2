#!/usr/bin/env python3
"""Runtime-evidence and measured-rate leg for ONE Terminal-Bench Science task.

  python3 trial_evidence.py --runs <dir> [...] [--task <task dir>] [--pretty]

Under the DELIVERY_CHECKLIST.md layout the controls live in `oracle-nop-evidence/`
(oracle-1..3, nop-1..2) and the round in `trajectories/` (run-01..run-05); pass
both to --runs.  Harbor job directories still work unchanged.

Walks harbor job directories for trial folders (<task>__<id>/ containing
result.json and verifier/{reward.txt, ctrf.json}), groups trials by
arm — `oracle`, `nop`, `cheat`, or "<agent>:<model>" from result.json (falls
back to path segments) — and reports what the TB-Science review pipeline looks at:

  * oracle runs: every one must pass the FULL suite (reward 1.0, ctrf N/N);
    3 separate runs are required package evidence under `terminus` (2 upstream)
  * nop runs:    reward 0 AND ctrf 0 of N passed — per-test, not reward (F-053);
    2 NOP control traces are required package evidence under `terminus`
    (DELIVERY_CHECKLIST.md: nop-1/ and nop-2/; NOP x1 was the previous edition)
  * negative controls: reviewed when supplied (they must score 0); their
    ABSENCE is not a finding — anti-cheat is established by isolation, hidden-
    test protection, independent recomputation and reward-channel integrity
  * real-agent arms: per-arm and pooled pass@1, the SATURATION flag and the
    ALL-FAIL flag (a written reason for every failure is required before a low
    rate means anything). Under `terminus` the required round is GPT-5.6 at
    xhigh (confirmed on EVERY run, Master #91), five complete attempts, failures
    included.  The measured k=5 rate is REPORTED (`measured_pass_rate`) — it is
    never compared against a task field: task.toml carries no `difficulty`
    (Master #62), so its presence is flagged instead.
  * errored trials (exception_info set / no reward) — excluded and listed (Master #92)
  * with --task on a delivery package: SUMMARY.txt's `sha=` is compared with the
    bundle sha recomputed over the inner task folder (Master #80)
  * with --task: every ctrf's test names are diffed against the shipped
    tests/test_*.py so stale evidence is dropped, not counted (F-081), and the
    package digest is recomputed so trajectories that do not belong to THIS
    bundle are named as stale rather than counted
  * every packaged trace is checked for truncation markers and empty files —
    trajectories must be complete and untruncated
  * harbor analyze output (analysis*.json / *analysis*.json beside the trials)
    is summarised per flag when present: task_specification, reward_hacking,
    difficulty_crux, near_miss, refusals, low_timeout

Rewards are read from reward.txt (control dirs) or verifier/reward.txt, then
result.json. verifier/reward.json is not a reward (Master #58: Harbor prefers
it over reward.txt) and is reported as a flag. stdlib only (Python 3.11+).
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys

MODEL_HINT = re.compile(r'gpt|opus|claude|sonnet|gemini|codex|grok|glm|devin|sol\b', re.I)
FLAGS = ("task_specification", "reward_hacking", "difficulty_crux", "near_miss", "refusals", "low_timeout")

# terminus packaged-evidence quorum (MASTER_CHECKLIST_TBSCI.md Sections G/H).
# The measured k=5 rate is reported only; there is no task field to compare it
# with (Master #62 bans `difficulty`).
T3_ORACLE_RUNS = 3
T3_NOP_RUNS = 2                # DELIVERY_CHECKLIST.md: nop-1/ and nop-2/
T3_AGENT_ROUND = 5
T3_ROUND_MODEL = re.compile(r'gpt[-_. ]?5[-_. ]?6', re.I)
T3_ROUND_EFFORT = re.compile(r'x[-_ ]?high', re.I)
# DELIVERY_CHECKLIST.md entry names: trajectories/run-01..run-05 and
# oracle-nop-evidence/{oracle-1..3,nop-1..2}
CHECKLIST_ENTRY = re.compile(r'^(?:run-\d{2}|oracle-\d+|nop-\d+)$')
TRUNCATION = re.compile(
    r'\[\s*(?:\.\.\.\s*)?(?:truncated|output truncated|content truncated|omitted)[^\]]{0,60}\]'
    r'|\.\.\.\s*\(?truncated\b|<\s*truncated\s*>|\btruncated for (?:brevity|length)\b'
    r'|\[\s*\.\.\.\s*\d+\s+(?:lines?|chars?|characters?|tokens?)\s+(?:omitted|truncated|skipped)[^\]]*\]', re.I)


def task_digest(task_dir):
    """sha256 over the SUBMITTED package (evidence excluded) — must match
    tbsci_static_screen.task_digest exactly."""
    # NB: iterate the walk lazily — sorted(os.walk(...)) consumes the generator
    # before dn[:] pruning can take effect.
    files = []
    for dp, dn, fn in os.walk(task_dir):
        dn[:] = [d for d in dn if d not in ("trajectories", "evidence", "__MACOSX", ".git",
                                            "__pycache__", ".pytest_cache", "node_modules")]
        for f in fn:
            if f == ".DS_Store" or f.startswith("._"):
                continue
            p = os.path.join(dp, f)
            files.append((os.path.relpath(p, task_dir).replace(os.sep, "/"), p))
    h = hashlib.sha256()
    for rel, p in sorted(files):
        try:
            with open(p, "rb") as fh:
                body = fh.read()
        except OSError:
            continue
        h.update(rel.encode("utf-8") + b"\0" + hashlib.sha256(body).digest())
    return h.hexdigest()


def bundle_sha(inner_dir):
    """Master #80 — identical to, from inside the inner task folder,
        find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
    (must match tbsci_static_screen.bundle_sha exactly)."""
    entries = []
    for dp, dn, fn in os.walk(inner_dir):
        for f in fn:
            p = os.path.join(dp, f)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            rel = os.path.relpath(p, inner_dir).replace(os.sep, "/")
            entries.append((os.fsencode("./" + rel), p))
    entries.sort(key=lambda e: e[0])
    outer = hashlib.sha256()
    for name, p in entries:
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        if b"\\" in name or b"\n" in name or b"\r" in name:
            name = name.replace(b"\\", b"\\\\").replace(b"\n", b"\\n").replace(b"\r", b"\\r")
            outer.update(b"\\" + h.hexdigest().encode() + b"  " + name + b"\n")
        else:
            outer.update(h.hexdigest().encode() + b"  " + name + b"\n")
    return outer.hexdigest()


def summary_sha(run_dirs):
    """(path, sha) from the first trajectories/SUMMARY.txt among the --runs dirs."""
    for rd in run_dirs:
        p = os.path.join(rd, "SUMMARY.txt")
        if os.path.isfile(p):
            m = re.search(r'\bsha=([0-9a-fA-F]+)', open(p, encoding="utf-8", errors="replace").read())
            return p, (m.group(1).lower() if m else None)
    return None, None


def effort_of(trial):
    """reasoning effort recorded for the trial, if any — result.json, or the
    config.json the checklist layout ships beside it."""
    blob = os.path.basename(trial)
    for f in ("result.json", "config.json"):
        rp = os.path.join(trial, f)
        if os.path.isfile(rp):
            try:
                blob += " " + json.dumps(json.load(open(rp)))[:8000]
            except Exception:  # noqa: BLE001
                pass
    m = T3_ROUND_EFFORT.search(blob)
    return m.group(0) if m else None


def scan_evidence(run_dirs, digest):
    """Untruncated traces, and binding of EVERY trace to the current package digest."""
    truncated, empty, stamps = [], [], set()
    unbound, stale = [], []
    text_re = re.compile(r'\.(json|jsonl|ndjson|txt|log|md|cast|yaml|yml|html)$', re.I)
    for rd in run_dirs:
        base = os.path.dirname(os.path.abspath(rd.rstrip(os.sep))) or rd
        per_entry, root_stamps = {}, set()
        for dp, dn, fn in os.walk(rd):
            dn[:] = [d for d in dn if d not in ("__MACOSX", ".git", "__pycache__")]
            rel_dir = os.path.relpath(dp, rd)
            entry = None if rel_dir == "." else rel_dir.split(os.sep)[0]
            for f in fn:
                if f == ".DS_Store" or f.startswith("._"):
                    continue
                p = os.path.join(dp, f)
                short = os.path.relpath(os.path.abspath(p), base)
                try:
                    if os.path.getsize(p) == 0:
                        empty.append(short)
                        continue
                except OSError:
                    continue
                if not text_re.search(f):
                    continue
                try:
                    txt = open(p, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                m = TRUNCATION.search(txt)
                if m:
                    truncated.append("{}: {!r}".format(short, m.group(0)[:40]))
                if digest:
                    found = set(re.findall(r'\b[0-9a-f]{64}\b', txt))
                    stamps |= found
                    (root_stamps if entry is None else per_entry.setdefault(entry, set())).update(found)
        if digest:
            entries = [e for e in os.listdir(rd) if os.path.isdir(os.path.join(rd, e)) and e not in ("__MACOSX", ".git", "__pycache__")]
            for e in sorted(entries):
                got = per_entry.get(e) or root_stamps
                label = os.path.join(os.path.basename(rd.rstrip(os.sep)), e)
                if not got:
                    unbound.append(label)
                elif digest not in got:
                    stale.append(label)
    return {"truncated": truncated, "empty": empty, "digest_recorded": sorted(stamps),
            "unbound_traces": unbound, "stale_traces": stale,
            "digest_matches": bool(digest) and not unbound and not stale}


def read_reward(trial):
    # the checklist's control dirs put reward.txt at the entry root
    for flat in ("reward.txt",):
        fp = os.path.join(trial, flat)
        if os.path.isfile(fp):
            try:
                txt = open(fp).read().strip()
                if txt:
                    return float(re.search(r'-?\d+(?:\.\d+)?', txt).group(0))
            except Exception:  # noqa: BLE001
                pass
    p = os.path.join(trial, "verifier", "reward.txt")
    if os.path.isfile(p):
        try:
            txt = open(p).read().strip()
            return float(txt) if txt else None
        except ValueError:
            return None
    rp = os.path.join(trial, "result.json")
    if os.path.isfile(rp):
        try:
            d = json.load(open(rp))
            r = ((d.get("verifier_result") or {}).get("rewards") or {}).get("reward")
            return float(r) if r is not None else None
        except Exception:  # noqa: BLE001
            return None
    return None


def read_ctrf(trial):
    p = os.path.join(trial, "verifier", "ctrf.json")
    if not os.path.isfile(p):
        p = os.path.join(trial, "ctrf.json")     # checklist control dirs are flat
    if not os.path.isfile(p):
        return None
    try:
        d = json.load(open(p))
    except Exception:  # noqa: BLE001
        return None
    res = d.get("results") or d
    summ = res.get("summary") or {}
    tests = res.get("tests") or []
    passed = [t["name"] for t in tests if t.get("status") == "passed"]
    return {"total": summ.get("tests", len(tests)), "passed": summ.get("passed", len(passed)),
            "failed": summ.get("failed"), "passed_names": passed, "names": [t.get("name", "") for t in tests]}


def arm_of(trial):
    rp = os.path.join(trial, "result.json")
    exc = task_name = None
    if os.path.isfile(rp):
        try:
            d = json.load(open(rp))
            task_name = d.get("task_name")
            exc = (d.get("exception_info") or {}).get("exception_type")
            ai = d.get("agent_info") or {}
            name = ai.get("name")
            mi = ai.get("model_info") or {}
            model = mi.get("name") if isinstance(mi, dict) else None
            cfg = (d.get("config") or {}).get("agent") or {}
            model = model or cfg.get("model_name") or d.get("model")
            name = name or cfg.get("name") or d.get("agent")
            cp = os.path.join(trial, "config.json")      # checklist layout
            if not model and os.path.isfile(cp):
                try:
                    c = json.load(open(cp))
                    model = c.get("model") or c.get("model_name") or ((c.get("agent") or {}) if isinstance(c.get("agent"), dict) else {}).get("model")
                    name = name or (c.get("agent") if isinstance(c.get("agent"), str) else None)
                except Exception:  # noqa: BLE001
                    pass
            if name in ("oracle", "nop"):
                return name, exc, task_name
            if name and "cheat" in str(name).lower():
                return "cheat", exc, task_name
            if model:
                # NB: compute the substitution first — a backslash inside an
                # f-string expression is a SyntaxError before Python 3.12.
                short = re.sub(r'^@?[\w.-]+/', '', model)
                return "{}:{}".format(name or "agent", short), exc, task_name
            if name:
                return name, exc, task_name
        except Exception:  # noqa: BLE001
            pass
    # The ENTRY name decides first: under the checklist layout every control sits
    # under `oracle-nop-evidence/`, so matching the whole path would call nop-1 an
    # oracle run.
    base = os.path.basename(trial.rstrip(os.sep)).lower()
    for hay in (base, trial.lower()):
        if re.search(r'(^|[/_-])oracle([/_-]|$)', hay):
            return "oracle", exc, task_name
        if re.search(r'(^|[/_-])nop([/_-]|$)', hay):
            return "nop", exc, task_name
        if "cheat" in hay or "hack" in hay:
            return "cheat", exc, task_name
    seg = next((s for s in trial.split(os.sep) if MODEL_HINT.search(s)), None)
    return (seg or "unknown"), exc, task_name


def shipped_tests(task_dir):
    names = set()
    for p in glob.glob(os.path.join(task_dir, "tests", "**", "test_*.py"), recursive=True):
        src = open(p, encoding="utf-8", errors="replace").read()
        names |= set(re.findall(r'(?m)^\s*(?:async\s+)?def\s+(test_\w+)\s*\(', src))
    return names or None


def find_analysis(root_dirs):
    """harbor analyze output: any json under the job dirs whose name contains 'analy'."""
    out = {}
    for rd in root_dirs:
        for p in glob.glob(os.path.join(rd, "**", "*analy*.json"), recursive=True):
            try:
                d = json.load(open(p))
            except Exception:  # noqa: BLE001
                continue
            # accept {trial: {criterion: {...}}} or a list of {trial_name, criteria:{...}}
            items = d.items() if isinstance(d, dict) else [(x.get("trial_name") or x.get("trial") or str(i), x) for i, x in enumerate(d)]
            for tname, rec in items:
                if not isinstance(rec, dict):
                    continue
                crit = rec.get("criteria") or rec.get("checks") or rec
                for f in FLAGS:
                    v = crit.get(f)
                    if v is None:
                        continue
                    verdict = v.get("verdict") or v.get("result") or v.get("status") if isinstance(v, dict) else v
                    out.setdefault(f, {}).setdefault(str(verdict).upper(), []).append(str(tname))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--task", help="task dir — cross-check ctrf test names against the shipped suite")
    ap.add_argument("--task-name", help="only count trials whose folder/result.json names this task")
    ap.add_argument("--profile", choices=["terminus", "upstream"], default="terminus",
                    help="terminus (default, MASTER_CHECKLIST_TBSCI.md): required round = GPT-5.6 xhigh x5, "
                         "oracle x3, NOP x2, SUMMARY.txt sha = bundle sha; the measured k=5 rate is reported, never "
                         "compared with a task field (task.toml has no difficulty); upstream: oracle x2")
    ap.add_argument("--pretty", action="store_true")
    a = ap.parse_args()

    trials = []
    for root_dir in a.runs:
        for root, dirs, files in os.walk(root_dir):
            base = os.path.basename(root)
            if base == os.path.basename(root_dir):
                continue
            harbor = "result.json" in files and "__" in base
            checklist = bool(CHECKLIST_ENTRY.match(base)) and bool(
                {"result.json", "reward.txt", "ctrf.json"} & set(files))
            if harbor or checklist:
                trials.append(root)
                dirs[:] = []
    if not trials:
        print(json.dumps({"error": "no trial dirs (<task>__<id>/result.json) found under the given dirs"}))
        sys.exit(1)

    shipped = shipped_tests(a.task) if a.task else None
    arms, errors, stale, reward_json = {}, [], [], []
    for tr in sorted(trials):
        arm, exc, task_name = arm_of(tr)
        if a.task_name and task_name and task_name != a.task_name and a.task_name not in os.path.basename(tr):
            continue
        reward = read_reward(tr)
        if os.path.isfile(os.path.join(tr, "verifier", "reward.json")) or os.path.isfile(os.path.join(tr, "reward.json")):
            reward_json.append(os.path.relpath(tr))
        ctrf = read_ctrf(tr)
        rec = {"trial": os.path.relpath(tr), "reward": reward, "ctrf": f"{ctrf['passed']}/{ctrf['total']}" if ctrf else None}
        if exc or reward is None:
            rec["error"] = exc or "no reward (RewardFileNotFound?)"
            errors.append({"arm": arm, **rec})
            continue
        if shipped is not None and ctrf:
            got = {n.split("::")[-1].split("[")[0] for n in ctrf["names"]}
            if got and got != shipped:
                stale.append({"arm": arm, "trial": rec["trial"], "reward": reward, "ctrf_tests": len(got), "shipped_tests": len(shipped),
                              "missing_in_ctrf": sorted(shipped - got)[:8], "extra_in_ctrf": sorted(got - shipped)[:8]})
                continue
        if arm in ("nop", "cheat") and ctrf:
            rec["passing_tests"] = ctrf["passed_names"]
        arms.setdefault(arm, []).append(rec)

    report = {"arms": {}, "oracle": None, "nop": None, "cheat": None, "agents": {}, "errors": errors, "stale_evidence": stale, "flags": [], "leads": []}
    if reward_json:
        report["flags"].append(
            "reward.json is present (Master #58: the verifier writes only reward.txt; "
            "Harbor prefers reward.json, so it decides the score): " + ", ".join(reward_json[:5])
        )
    for arm, recs in sorted(arms.items()):
        n = len(recs)
        solved = sum(1 for r in recs if r["reward"] is not None and r["reward"] >= 1.0)
        report["arms"][arm] = {"attempts": n, "solved": solved, "rate": round(solved / n, 3), "trials": recs}
        partial = [r["trial"] for r in recs if r["reward"] is not None and 0 < r["reward"] < 1]
        if partial:
            report["flags"].append(f"{arm}: {len(partial)} trial(s) carry a partial reward in (0,1) — binary_reward violation: {partial[:3]}")

    if "oracle" in arms:
        recs = arms["oracle"]
        fails = [r for r in recs if r["reward"] is None or r["reward"] < 1.0]
        not_full = [r["trial"] for r in recs if r["ctrf"] and r["ctrf"].split("/")[0] != r["ctrf"].split("/")[1]]
        v = "ORACLE-FAIL" if len(fails) == len(recs) else "FLAKY" if fails else "PASS"
        report["oracle"] = {"runs": len(recs), "verdict": v, "failing_runs": [r["trial"] for r in fails], "not_N_of_N": not_full}
        need = T3_ORACLE_RUNS if a.profile == "terminus" else 2
        if len(recs) < need:
            report["flags"].append(f"only {len(recs)} oracle run(s) — {need} separate runs are required "
                                   "(single-run QA cannot detect flakiness)")
        if not_full:
            report["flags"].append(f"oracle did not pass the FULL suite in {len(not_full)} run(s): {not_full[:3]} — "
                                   "full-suite success is the gate, not reward 1.0")
        if v != "PASS":
            report["flags"].append(f"oracle verdict {v} — the task cannot ship")
    else:
        report["flags"].append("no oracle control trace found — H2 is no-evidence"
                               + (f" ({T3_ORACLE_RUNS} oracle runs are required package evidence)" if a.profile == "terminus" else ""))

    if "nop" in arms:
        recs = arms["nop"]
        passing = sorted({t for r in recs for t in (r.get("passing_tests") or [])})
        rewarded = [r["trial"] for r in recs if r["reward"]]
        report["nop"] = {"runs": len(recs), "verdict": "NOP-PASS" if (passing or rewarded) else "PASS",
                         "tests_passing_on_nop": passing, "rewarded_runs": rewarded}
        if passing:
            report["flags"].append(f"NOP passes {len(passing)} test(s) — per-test zero violated: {passing[:6]}")
        if any(r["ctrf"] is None for r in recs):
            report["flags"].append("a NOP run has no ctrf.json — reward 0 alone is not the gate; 0 of N is")
        if a.profile == "terminus" and len(recs) < T3_NOP_RUNS:
            report["flags"].append(f"{len(recs)} NOP control trace(s); {T3_NOP_RUNS} is required package evidence")
    else:
        report["flags"].append("no NOP control trace found — H3/E1 is no-evidence"
                               + (f" ({T3_NOP_RUNS} NOP run is required package evidence)" if a.profile == "terminus" else ""))

    if "cheat" in arms:
        recs = arms["cheat"]
        rewarded = [r["trial"] for r in recs if r["reward"]]
        report["cheat"] = {"runs": len(recs), "verdict": "HACKED" if rewarded else "PASS", "rewarded_runs": rewarded}
        if rewarded:
            report["flags"].append(f"cheat run(s) scored reward: {rewarded[:3]} — hardening failed (E3/E6); read the trajectory for the exploit")

    agent_arms = {k: v for k, v in report["arms"].items() if k not in ("oracle", "nop", "cheat", "unknown")}
    if agent_arms:
        n_tot = sum(v["attempts"] for v in agent_arms.values())
        s_tot = sum(v["solved"] for v in agent_arms.values())
        report["agents"] = {k: {"attempts": v["attempts"], "solved": v["solved"], "rate": v["rate"]} for k, v in agent_arms.items()}
        report["pooled_pass_at_1"] = round(s_tot / n_tot, 3)
        report["saturated"] = s_tot == n_tot
        report["all_fail"] = s_tot == 0
        if s_tot == n_tot:
            report["flags"].append("SATURATED — every real-agent trial solved the task; 4.0 removes saturated tasks (erp-procurement-planning: 5/5 on ten arms). Decline unless trials are too few to judge")
        if s_tot == 0:
            report["flags"].append("0% solved — a written reason for EVERY failure is required (task_specification? environment? refusal? timeout?) before it counts as capability evidence (Master #84)")
        rates = [v["rate"] for v in agent_arms.values()]
        mean = sum(rates) / len(rates)
        report["mean_pass_at_1"] = round(mean, 3)
        if a.profile == "terminus":
            # The measured k=5 rate is reported; it is recorded only in workspace
            # records and SUMMARY.txt's reward array, never as a task field.
            if s_tot == n_tot:
                report["flags"].append("100% across every arm — >=1 failure is required to reach review")
            # the required round: GPT-5.6 at xhigh, five complete attempts
            round_arms = {k: v for k, v in agent_arms.items() if T3_ROUND_MODEL.search(k)}
            attempts = sum(v["attempts"] for v in round_arms.values())
            report["required_round"] = {"model": "gpt-5.6", "effort": "xhigh", "need": T3_AGENT_ROUND,
                                        "arms": sorted(round_arms), "attempts": attempts,
                                        "solved": sum(v["solved"] for v in round_arms.values()),
                                        "efforts": sorted({e for e in (effort_of(t["trial"]) for v in round_arms.values() for t in v["trials"]) if e})}
            solved = report["required_round"]["solved"]
            if attempts == T3_AGENT_ROUND:
                report["measured_pass_rate"] = f"{solved}/{T3_AGENT_ROUND}"
            # Master #91: reasoning_effort=xhigh confirmed on EVERY run individually
            no_xhigh = [t["trial"] for v in round_arms.values() for t in v["trials"] if not effort_of(t["trial"])]
            if round_arms and no_xhigh:
                report["flags"].append(f"{len(no_xhigh)} GPT-5.6 run(s) record no xhigh reasoning effort: {no_xhigh[:5]} "
                                       "— confirm reasoning_effort=xhigh on every run individually (Master #91)")
            if not round_arms:
                report["flags"].append(f"no GPT-5.6 arm among {sorted(agent_arms)} — the required evidence is a complete "
                                       f"{T3_AGENT_ROUND}-attempt GPT-5.6 xhigh round")
            elif attempts < T3_AGENT_ROUND:
                report["flags"].append(f"GPT-5.6 round is incomplete: {attempts}/{T3_AGENT_ROUND} attempts "
                                       "— package every attempt of the round, failures included")
            elif not report["required_round"]["efforts"]:
                report["flags"].append("GPT-5.6 round present but no xhigh reasoning effort is recorded in the trial "
                                       "metadata — the evidence cannot be checked against the required setting")
        elif len(agent_arms) < 2:
            report["flags"].append(f"only {len(agent_arms)} agent arm(s) — the maintainers' /run uses 2 (claude-code + Opus 5 max, codex + GPT-5.6-sol xhigh), 3 trials each")
        for k, v in agent_arms.items():
            thin = T3_AGENT_ROUND if (a.profile == "terminus" and T3_ROUND_MODEL.search(k)) else 3
            if v["attempts"] < thin:
                report["flags"].append(f"{k}: {v['attempts']} attempt(s) — thin evidence (need {thin})")
            if v["rate"] == 1.0 and v["attempts"] >= 3:
                report["flags"].append(f"{k} solved every attempt — a saturated arm is a strong too-easy signal")
    else:
        report["saturated"] = None
        report["flags"].append("no real-agent trials — the pass rate is unmeasured"
                               + (f" (the required evidence is a complete {T3_AGENT_ROUND}-attempt GPT-5.6 xhigh round)"
                                  if a.profile == "terminus" else
                                  " (run `harbor run -p <task> -a claude-code -m anthropic/claude-opus-5` and codex/gpt-5.6-sol)"))

    analysis = find_analysis(a.runs)
    if analysis:
        report["trial_analysis"] = analysis
        for f in ("task_specification", "reward_hacking"):
            if analysis.get(f, {}).get("FAIL"):
                report["flags"].append(f"harbor analyze flagged {f} on {analysis[f]['FAIL'][:3]} — definite issue, send back")
        for f in ("difficulty_crux", "near_miss", "refusals", "low_timeout"):
            if analysis.get(f, {}).get("FAIL"):
                report["flags"].append(f"harbor analyze flagged {f} on {len(analysis[f]['FAIL'])} trial(s) — examine each; uphold with the reason or dismiss in writing")
    if a.task and shipped is not None:
        report["shipped_test_count"] = len(shipped)
    if a.task and a.profile == "terminus":
        # Master #62: task.toml carries NO difficulty field — presence is flagged,
        # never compared with the measured rate.
        raw = ""
        try:
            raw = open(os.path.join(a.task, "task.toml"), encoding="utf-8", errors="replace").read()
        except OSError:
            pass
        if re.search(r'(?m)^\s*difficulty\s*=', raw):
            report["flags"].append("task.toml carries a `difficulty` field — banned (Master #62); the measured rate "
                                   "lives only in workspace records and SUMMARY.txt's reward array")
        # Master #80: SUMMARY.txt's sha= is the bundle sha over the inner task folder
        sp, declared = summary_sha(a.runs)
        if sp:
            got = bundle_sha(a.task)
            report["bundle_sha"] = got
            report["summary_sha"] = declared
            if declared is None:
                report["flags"].append(f"{sp} carries no sha= (Master #80)")
            elif declared != got:
                report["flags"].append(f"SUMMARY.txt sha={declared[:16]}… but the bundle sha recomputed over "
                                       f"{os.path.basename(os.path.abspath(a.task))}/ is {got[:16]}… — the evidence does "
                                       "not describe the shipped task folder (Master #80)")
    if stale:
        report["flags"].append(f"{len(stale)} trial(s) graded a different test suite than the one shipped — stale evidence, EXCLUDED from all rates")
    if errors:
        report["flags"].append(f"{len(errors)} errored trial(s) excluded from rates (listed under errors) — exception_info / "
                               "no reward: re-run, never ship with an assumed reward (Master #92)")

    # packaged-evidence integrity: untruncated traces bound to the current digest
    digest = task_digest(a.task) if a.task else None
    if digest:
        report["task_digest"] = digest
    # Under terminus the round's ONE binding is SUMMARY.txt's sha= (the bundle sha,
    # compared above).  Per-trace 64-hex strings (image digests in config.json,
    # hashes an agent printed, the SUMMARY sha itself) are not digest stamps, so
    # the per-trace binding scan runs only under upstream.
    ev = scan_evidence(a.runs, digest if a.profile != "terminus" else None)
    report["evidence"] = ev
    if ev["truncated"]:
        report["flags"].append(f"{len(ev['truncated'])} trajectory file(s) carry truncation markers — trajectories must be "
                               f"complete and untruncated: {ev['truncated'][:3]}")
    if ev["empty"]:
        report["flags"].append(f"{len(ev['empty'])} empty trajectory file(s): {ev['empty'][:3]}")
    if digest and ev["stale_traces"]:
        report["flags"].append(f"{len(ev['stale_traces'])} trace(s) record a digest that is not the shipped package's "
                               f"{digest[:16]}… — stale or unrelated trajectories, not evidence: {ev['stale_traces'][:4]}")
    if digest and ev["unbound_traces"]:
        # The delivery layout binds the round in exactly one place — SUMMARY.txt's
        # `sha=`, the BUNDLE sha (Master #80), compared above.  A per-trace stamp of
        # this script's package digest is not something a compliant package
        # carries, so its absence is expected, never a flag.
        report.setdefault("leads", []).append(
            f"{len(ev['unbound_traces'])} trace(s) carry no digest stamp of their own: {ev['unbound_traces'][:4]}. "
            "Expected under the delivery layout — the binding is trajectories/SUMMARY.txt's `sha=` (the bundle sha, "
            "checked above as bundle_sha vs summary_sha). A matching sha is still not proof of freshness: check the "
            "evidence mtimes against every graded file (Master #75, secondary).")

    report["readiness_note"] = ("Readiness requires valid package evidence AND current-digest trajectories: a clean "
                               "static screen is never a 'Ready to Submit' verdict on its own.")
    print(json.dumps(report, indent=1 if a.pretty else None))


if __name__ == "__main__":
    main()
