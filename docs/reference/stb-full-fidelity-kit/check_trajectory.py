#!/usr/bin/env python3
"""Full-fidelity check for Step 3c model trials (Terminus-2 ATIF trajectories).

  python3 scripts/check_trajectory.py evidence-<task>            # every *-gpt56-tN / gpt56-kN job
  python3 scripts/check_trajectory.py evidence-<task>/<job> ...  # explicit job directories

Per trial it prints reward, test counts, steps, tool calls, tokens, cost, and the
capture signals the kit requires: ``all_messages`` stored, ``api-calls.jsonl`` and
``recording.cast`` present, no truncated observation
(``[... output limited to N bytes; M interior bytes omitted ...]``), and every
logged API request carrying the expected reasoning effort, and no trial exception (an
``AuthenticationError`` from an expired key voids the trial). The last line reads
``SUMMARY <jobs>: x/n solved; fidelity PASS|FAIL``. Exit 1 on FAIL — that round
is void: rename it ``_void-<name>``, fix the cause, and run again.

Adapted from the STB full-fidelity kit (``docs/reference/stb-full-fidelity-kit/``).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

TRUNC = re.compile(r"\[\.\.\. output limited to \d+ bytes; \d+ interior bytes omitted \.\.\.\]")
_MODEL_JOB = re.compile(r"(?:^|-)gpt56-(?:t[1-9]|k[1-9][0-9]*)$")
DEFAULT_EFFORT = "xhigh"


def request_effort(request: dict) -> str | None:
    """Reasoning effort as LiteLLM sent it: chat ``reasoning_effort`` or Responses ``reasoning.effort``."""
    if isinstance(request.get("reasoning_effort"), str):
        return request["reasoning_effort"]
    reasoning = request.get("reasoning")
    if isinstance(reasoning, dict) and isinstance(reasoning.get("effort"), str):
        return reasoning["effort"]
    return None


def check_trial(td: str, effort: str) -> dict:
    out = {"trial": os.path.basename(td), "ok": True, "problems": []}
    rp = os.path.join(td, "verifier", "reward.txt")
    out["reward"] = open(rp).read().strip() if os.path.exists(rp) else "?"
    # A trial that died in the harness (typically an AuthenticationError from an expired
    # key) never reached the verifier; it is an infrastructure failure and voids the round.
    rj = os.path.join(td, "result.json")
    try:
        exc = (json.load(open(rj)) if os.path.exists(rj) else {}).get("exception_info") or {}
    except (OSError, ValueError, AttributeError):
        exc = {}
    if exc:
        out["ok"] = False
        out["problems"].append(f"trial exception: {exc.get('exception_type')}: {str(exc.get('exception_message', ''))[:160]}")
    elif out["reward"] == "?":
        out["ok"] = False
        out["problems"].append("no verifier/reward.txt (trial did not reach the verifier)")
    cp = os.path.join(td, "verifier", "ctrf.json")
    if os.path.exists(cp):
        try:
            s = json.load(open(cp))["results"]["summary"]
            out["tests"] = f"{s['passed']}/{s['tests']}"
        except (OSError, ValueError, KeyError, TypeError):
            out["tests"] = "?"
    tp = os.path.join(td, "agent", "trajectory.json")
    if not os.path.exists(tp):
        out["ok"] = False
        out["problems"].append("no trajectory.json")
        return out
    try:
        t = json.load(open(tp))
    except (OSError, ValueError) as exc:
        out["ok"] = False
        out["problems"].append(f"unreadable trajectory.json: {exc}")
        return out
    steps = t.get("steps", []) if isinstance(t, dict) else []
    out["steps"] = len(steps)
    out["tool_calls"] = sum(len(s.get("tool_calls") or []) for s in steps)
    out["reasoning_steps"] = sum(1 for s in steps if s.get("reasoning_content"))
    fm = t.get("final_metrics") or {}
    out["prompt_tokens"] = fm.get("total_prompt_tokens")
    out["completion_tokens"] = fm.get("total_completion_tokens")
    out["cost_usd"] = fm.get("total_cost_usd")
    meta = t.get("metadata") or {}
    out["summarizations"] = meta.get("summarization_count")
    am = meta.get("all_messages")
    if not isinstance(am, list):  # Terminus-2 stores them on the AgentContext -> result.json
        rj = os.path.join(td, "result.json")
        if os.path.exists(rj):
            try:
                am = ((json.load(open(rj)).get("agent_result") or {}).get("metadata") or {}).get("all_messages")
            except (OSError, ValueError, AttributeError):
                am = None
    out["all_messages"] = len(am) if isinstance(am, list) else 0
    if not out["all_messages"]:
        out["ok"] = False
        out["problems"].append("metadata.all_messages missing/empty (store_all_messages)")

    # Truncation: scan every string in every step's observation and message, plus continuations.
    blob = json.dumps(steps)
    for cont in sorted(glob.glob(os.path.join(td, "agent", "trajectory.cont-*.json"))):
        try:
            blob += json.dumps(json.load(open(cont)).get("steps", []))
        except (OSError, ValueError, AttributeError):
            out["problems"].append(f"unreadable {os.path.basename(cont)}")
            out["ok"] = False
    n_trunc = len(TRUNC.findall(blob))
    out["truncated_observations"] = n_trunc
    if n_trunc:
        out["ok"] = False
        out["problems"].append(f"{n_trunc} truncated observations")
    out["continuations"] = len(glob.glob(os.path.join(td, "agent", "trajectory.cont-*.json")))
    for f in ("recording.cast", "api-calls.jsonl"):
        if not os.path.exists(os.path.join(td, "agent", f)):
            out["ok"] = False
            out["problems"].append(f"no {f}")

    # Raw API log: count records and confirm every request carried the expected effort.
    ap = os.path.join(td, "agent", "api-calls.jsonl")
    out["api_calls"] = 0
    efforts: dict[str, int] = {}
    if os.path.exists(ap):
        with open(ap) as fh:
            for line in fh:
                if not line.strip():
                    continue
                out["api_calls"] += 1
                try:
                    request = json.loads(line).get("request") or {}
                except (ValueError, AttributeError):
                    efforts["<unparsable>"] = efforts.get("<unparsable>", 0) + 1
                    continue
                key = request_effort(request) or "<none>"
                efforts[key] = efforts.get(key, 0) + 1
        if out["api_calls"] == 0:
            out["ok"] = False
            out["problems"].append("api-calls.jsonl is empty")
    out["effort"] = ",".join(f"{k}:{v}" for k, v in sorted(efforts.items())) or "?"
    if efforts and set(efforts) != {effort}:
        out["ok"] = False
        out["problems"].append(f"reasoning effort in API requests is {out['effort']}, expected {effort} only")

    # The adapter's own record of how the trial was configured. archive_step3c.py and
    # audit_step3c.py refuse a round whose recording_config.json does not say uncapped +
    # the required effort, so check it here, at the end of the round, rather than letting
    # a paid round die at archive time. (Harbor 0.23 moved reasoning_effort from
    # Terminus2._reasoning_effort onto .options; scripts/recording.py reads both.)
    rcp = os.path.join(td, "agent", "recording_config.json")
    try:
        with open(rcp) as fh:
            recording = json.load(fh)
    except (OSError, ValueError):
        recording = None
    if not isinstance(recording, dict):
        out["ok"] = False
        out["problems"].append("no readable agent/recording_config.json")
    else:
        out["recorded_effort"] = recording.get("reasoning_effort")
        out["recorded_cap"] = recording.get("max_output_bytes")
        if recording.get("max_output_bytes") != 0:
            out["ok"] = False
            out["problems"].append(
                f"recording_config.json max_output_bytes={recording.get('max_output_bytes')!r}, expected 0 (uncapped)")
        if recording.get("reasoning_effort") != effort:
            out["ok"] = False
            out["problems"].append(
                f"recording_config.json reasoning_effort={recording.get('reasoning_effort')!r}, expected {effort!r}")
        if not recording.get("raw_api_log"):
            out["ok"] = False
            out["problems"].append(
                "recording_config.json records no raw_api_log — the stb-bundled harbor was not patched")
    out["largest_observation_bytes"] = max((len(json.dumps(s.get("observation") or "")) for s in steps), default=0)
    return out


def trial_dirs(job: str) -> list[str]:
    return sorted(d for d in glob.glob(os.path.join(job, "*"))
                  if os.path.isdir(d) and os.path.exists(os.path.join(d, "config.json")))


def discover_jobs(root: str) -> list[str]:
    """A Step 3c OUT directory yields its model jobs; a job directory yields itself.

    Harbor writes a config.json at both job and trial level, so the job-name
    pattern, not file presence, tells the two layouts apart.
    """
    if _MODEL_JOB.search(os.path.basename(os.path.abspath(root))):
        return [root]
    jobs = sorted(d for d in glob.glob(os.path.join(root, "*"))
                  if os.path.isdir(d) and _MODEL_JOB.search(os.path.basename(d)))
    return jobs or [root]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", help="Step 3c OUT directory, or one or more Harbor job directories")
    parser.add_argument("--effort", default=DEFAULT_EFFORT,
                        help=f"reasoning effort every API request must carry (default: {DEFAULT_EFFORT})")
    args = parser.parse_args(argv)

    jobs: list[str] = []
    for path in args.paths:
        jobs += discover_jobs(path)
    if not jobs:
        print(f"no model jobs under {', '.join(args.paths)}")
        return 1
    rc = 0
    rewards: list[str] = []
    for job in jobs:
        trials = trial_dirs(job)
        if not trials:
            print(f"BAD {os.path.basename(job)}: no trials")
            rc = 1
            continue
        for td in trials:
            r = check_trial(td, args.effort)
            rewards.append(r.get("reward", "?"))
            flag = "OK " if r["ok"] else "BAD"
            print(f"{flag} {os.path.basename(job)}/{r['trial']}: reward={r.get('reward')} tests={r.get('tests', '?')} "
                  f"steps={r.get('steps')} tool_calls={r.get('tool_calls')} reasoning_steps={r.get('reasoning_steps')} "
                  f"all_messages={r.get('all_messages')} truncated={r.get('truncated_observations')} "
                  f"api_calls={r.get('api_calls')} effort={r.get('effort')} cfg_effort={r.get('recorded_effort')} "
                  f"cfg_cap={r.get('recorded_cap')} largest_obs={r.get('largest_observation_bytes')}B "
                  f"summarizations={r.get('summarizations')} conts={r.get('continuations')} "
                  f"tokens={r.get('prompt_tokens')}/{r.get('completion_tokens')} cost=${r.get('cost_usd')}")
            for p in r["problems"]:
                print("     -", p)
            if not r["ok"]:
                rc = 1
    solved = sum(1 for x in rewards if x in ("1", "1.0"))
    label = (os.path.basename(os.path.abspath(args.paths[0])) if len(args.paths) == 1
             else ", ".join(os.path.basename(j) for j in jobs))
    print(f"SUMMARY {label}: {solved}/{len(rewards)} solved; fidelity {'PASS' if rc == 0 else 'FAIL'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
