#!/usr/bin/env python3
"""Render report.md from a linted verdict.json. The report is derived, never hand-edited, so the
JSON and the markdown cannot disagree; the closing line comes from verdict_lint.closing_line().

    python3.11 report_render.py <run-dir>      # refuses to render while lint has errors
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verdict_lint import closing_line, lint  # noqa: E402


def cell(x):
    return str(x).replace("|", "\\|").replace("\n", " ")


def lst(x):
    if isinstance(x, list):
        return "; ".join(map(str, x)) if x else "none"
    return str(x)


def render(v):
    pe, c = v["package_evidence"], v["counts"]
    o = []
    o.append(f"# Audit — `{v['task_name']}`")
    o.append("")
    o.append(f"Profile **{v['profile']}** · bundle `{v['bundle_shape']}` · task digest `{v['task_digest']}`")
    o.append("")
    o.append(f"**{closing_line(v)}** — {c['blocker']} BLOCKER · {c['major']} MAJOR · {c['minor']} MINOR · package evidence `{pe['verdict']}`")
    o.append("")
    o.append("## Package evidence")
    o.append("")
    rs = pe["rubric_summary"]
    r = pe["round"]
    o += ["| Item | State |", "|---|---|",
          f"| rubric.txt | {pe['rubric_txt']} (+{rs['positive_total']} positive, {rs['negative_criteria']} negative, scores ok: {rs['scores_ok']}) |",
          f"| GPT-5.6 round | {r['attempts']}/{r['need']} attempts, effort {r['effort']}, untruncated: {r['untruncated']} |",
          f"| Controls | oracle {pe['controls']['oracle']}/{pe['controls']['need']['oracle']} · NOP {pe['controls']['nop']}/{pe['controls']['need']['nop']} |",
          f"| Digest bound | {pe['digest_bound']} |",
          f"| Stale or unrelated | {lst(pe['stale_or_unrelated'])} |"]
    o.append("")
    o.append("## Gates")
    o.append("")
    o.append(" · ".join(f"**{g}** {val}" for g, val in v["gates"].items()))
    o.append("")

    for sev in ("BLOCKER", "MAJOR", "MINOR"):
        fs = [f for f in v["findings"] if f["severity"] == sev]
        if not fs:
            continue
        o.append(f"## {sev} ({len(fs)})")
        o.append("")
        for i, f in enumerate(fs, 1):
            o.append(f"### {sev[0]}{i} · {f['gate']}" + (f" · {f['master']}" if f.get("master") else "")
                     + (f" · {f['upstream']}" if f.get("upstream") not in (None, "", "—") else ""))
            o.append("")
            o.append(f"- **Evidence:** {f['evidence']}")
            o.append(f"- **Why it matters:** {f['why_it_matters']}")
            o.append(f"- **Fix:** {f['fix']}")
            o.append("")

    o.append("## Alignment")
    o.append("")
    al = v["alignment"]
    o.append(f"- Graded but unlicensed: {lst(al['graded_unlicensed'])}")
    o.append(f"- Stated but ungraded: {lst(al['stated_ungraded'])}")
    o.append(f"- Do-not-modify unenforced: {lst(al['do_not_modify_unenforced'])}")
    o.append(f"- Licence sources: {lst(al['licence_sources_used'])}")
    o.append("")
    gp, ei = v["ground_truth_provenance"], v["execution_isolation"]
    o.append("## Provenance and isolation")
    o.append("")
    o.append(f"- Expected values sealed: {lst(gp['sealed'])} · from artifacts: {lst(gp['from_artifacts'])} · **{gp['verdict']}**")
    o.append(f"- Agent code run by the verifier: {ei['runs_agent_code']} as `{ei['uid']}`; setpriv reuid 12000: {ei['setpriv_reuid_12000']}; "
             f"/logs/verifier 700 before: {ei['reward_dir_700_before']}; `chmod 700 /tests`: {ei['tests_700_in_dockerfile']}; "
             f"negative control: {ei['negative_control']} → **{ei['verdict']}**")
    o.append(f"- Agent must execute: {v['must_execute']}")
    o.append(f"- NOP-passable tests: {lst(v['nop_passable_tests'])}")
    od = v["oracle_delta"]
    o.append(f"- Oracle delta: files {lst(od['files'])}; readable as the defect: {od['readable_as_defect']}; "
             f"scope matches instruction: {od['scope_matches_instruction']}; precomputed artifact: {od['precomputed_artifact']}")
    o.append("")
    o.append("## Cheat simulation")
    o.append("")
    o += ["| Attack | Passes | Why |", "|---|---|---|"]
    for x in v["cheat_simulation"]:
        o.append(f"| {cell(x['attack'])} | {'**YES**' if x['passes'] else 'no'} | {cell(x['why'])} |")
    o.append("")
    o.append("## Difficulty")
    o.append("")
    o.append(f"- Source: {v['difficulty_source']}")
    o.append("- Proposal rubric: " + " · ".join(f"{k} {val}" for k, val in v["proposal_rubric"].items()))
    te, ta = v["trial_evidence"], v["trial_analysis"]
    o.append(f"- Trials: pooled pass@1 {te['pooled_pass_at_1']} · saturated {te['saturated']} · all-fail {te['all_fail']}")
    for arm, d in te["per_arm"].items():
        o.append(f"  - {arm}: {d['solved']}/{d['attempts']} (rate {d['rate']})")
    o.append("- Trial analysis: " + " · ".join(f"{k} {val}" for k, val in ta.items()))
    o.append("")
    ss = v["static_screen"]
    o.append("## Static screen disposition")
    o.append("")
    o.append(f"{ss['flags']} flag(s). Confirmed: {lst([x if isinstance(x, str) else x.get('code') for x in ss['confirmed']])}.")
    for x in ss["discarded"]:
        o.append(f"- discarded `{x['code']}` — {x['why']}")
    for x in ss["leads_answered"]:
        o.append(f"- lead `{x['code']}` — {x['answer']}")
    if v["additional_checks"]:
        o.append("")
        o.append("## Additional checks")
        o.append("")
        for x in v["additional_checks"]:
            o.append(f"- `{x['code']}` — {x['note']}")
    o.append("")
    o.append("---")
    o.append("")
    o.append(closing_line(v))
    o.append("")
    return "\n".join(o)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    run = sys.argv[1].rstrip("/")
    errors, _ = lint(run)
    if errors:
        for e in errors:
            print(f"  ERROR {e}")
        print("REPORT_REFUSED lint has errors — finish judgement first")
        return 1
    v = json.load(open(os.path.join(run, "verdict.json"), encoding="utf-8"))
    with open(os.path.join(run, "report.md"), "w", encoding="utf-8") as fh:
        fh.write(render(v))
    print(f"REPORT_OK {os.path.join(run, 'report.md')}  {closing_line(v)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
