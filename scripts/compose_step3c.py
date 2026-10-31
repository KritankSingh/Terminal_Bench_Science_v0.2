#!/usr/bin/env python3
"""Compose one Step 3c round from the first five fidelity-complete trials across rounds.

  python3 scripts/compose_step3c.py tasks/<task> \\
      --source evidence-<task>-r1 --source evidence-<task>-r2 \\
      --controls evidence-<task>-controls \\
      --out evidence-<task>-composed \\
      [--reason <trial-id>=<outcome-independent reason> ...]

MASTER_CHECKLIST_TBSCI.md #94 item (1): the five packaged runs are the first five
fidelity-complete trials at the current digest and run config, in launch order across
rounds, with no valid attempt skipped; the order is checkable from each run's own
result.json timestamps and trial IDs. This tool is the only way such a round is
assembled. It never edits a captured file -- it copies.

What it enforces (it refuses, exit 2, on any violation):

* Same digest. Every source round and the controls round record the same
  ``task-digest.txt`` (and agent/grader digests where recorded). Pooling never crosses
  digests. The composed round must also bind to the task on disk (full digest, or the
  descriptive-only agent+grader match that archive_step3c.py accepts).
* Same run config. Model rounds agree on model, reasoning_effort, agent adapter and
  launcher, capture settings (TERMINUS_MAX_OUTPUT_BYTES, max_output_bytes=0,
  store_all_messages, raw API log), stb and Harbor versions, arch, the full-fidelity
  patch revision in ``patch-guard.log``, and the run-affecting source hashes in
  ``recording-source.sha256`` (harbor_recording.py, recording.py,
  patch_stb_harbor.py). Every model trial agrees on its config.json agent block,
  recording_config.json, result.json task_checksum and agent_info, and its job's
  lock.json Harbor version. The controls round agrees on digest, local Harbor version,
  arch and the adapter hashes (harbor_recording.py, recording.py).
* Fidelity-complete = every per-trial ``check_trajectory.py`` criterion, verifier CTRF
  with test records, ``exception_info`` null, and the files archive_step3c.py requires.
* Selection. Every model trial across the sources is sorted by its own result.json
  ``started_at`` (UTC); the first five fidelity-complete trials are taken. Never
  best-of: a fidelity-complete trial launched before the fifth selected one can never be
  left out, because the sort decides, not the operator.
* Exclusions are outcome-independent. A trial launched before the fifth selected one
  may be excluded only because it is not fidelity-complete. The reason is recorded. An
  operator stop (CancelledError / KeyboardInterrupt) or a trial with no finished record
  inside the first five also needs an explicit ``--reason`` -- a stop that happened
  while the trial was one of the five would otherwise be a way to discard a result.
* No hidden rounds. Every other round directory beside the sources (and at the repo
  root) that carries this task's model jobs at the same digest is inspected; one with
  the same run config and a trial launched before the fifth selected trial is a refusal
  until it is passed as a ``--source``.

Output: ``<slug>-gpt56-t1..t5`` in launch order (whole job directories copied; the job
folder is renamed, nothing inside it is -- the job-level config.json still names the
job it was captured as, and composition.json maps both), oracle-1..3 / nop-1..2 from
the controls round, their console/exit-code logs, ``task-digest.txt`` (+ agent/grader),
``recording-source.sha256``, a merged ``SOURCE.txt``, ``provenance/<round>/`` (each
source round's own records, credentials log excluded), ``composition.json`` (every
candidate trial, its start time, validity, selected/excluded and why) and
``fidelity-check.log``. The result works unchanged with check_trajectory.py,
archive_step3c.py, audit_step3c.py, package_task.py, verify_package.py and the bundled
auditor.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
from contextlib import redirect_stdout

from check_trajectory import check_trial, main as check_trajectory_main
from common import (REPO_ROOT, WorkflowError, evidence_inventory, portable_path, split_digests, task_digest,
                    write_json)


EFFORT = "xhigh"
MODEL_AGENT = "scripts.harbor_recording:RecordingTerminus2"
CONTROL_JOBS = ("oracle-1", "oracle-2", "oracle-3", "nop-1", "nop-2")
# Files whose bytes change what a trial does. archive_step3c.py and check_trajectory.py
# are also listed in recording-source.sha256 but only read a round after it ran.
RUN_SOURCES = ("scripts/harbor_recording.py", "scripts/recording.py", "scripts/patch_stb_harbor.py")
CONTROL_SOURCES = ("scripts/harbor_recording.py", "scripts/recording.py")
PROVENANCE_FILES = ("SOURCE.txt", "task-digest.txt", "agent-digest.txt", "grader-digest.txt",
                    "recording-source.sha256", "patch-guard.log", "fidelity-check.log")
OPERATOR_STOP = {"CancelledError", "KeyboardInterrupt"}
CREDENTIAL = re.compile(r"Authentication|RateLimit|Quota|Budget|PermissionDenied|ApiUsageLimit", re.I)


def model_job_re(slug: str) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(slug)}-gpt56-t([1-9][0-9]*)$")


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return {}
    return value if isinstance(value, dict) else {}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return ""


def parse_utc(value: object) -> datetime | None:
    """A Harbor trial timestamp. Trial-level result.json carries UTC with a trailing Z."""
    if not isinstance(value, str) or not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo is not None else None  # naive stamps are local time: unusable


def iso(stamp: datetime | None) -> str | None:
    return stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if stamp else None


def inventory(root: Path, trial_depth: int = 2, links: dict[str, str] | None = None) -> dict[str, str]:
    """Per-file sha256 of a round (trial_depth 2) or of one job dir (trial_depth 1).

    Master #55: a symlink inside a trial's artifacts/ is hashed from its link text and
    copied as a link (copytree symlinks=True); any other symlink is refused.
    """
    return evidence_inventory(root, "round contains a symlink outside a trial's artifacts/; inspect it by hand",
                              trial_depth, links)


# ---------------------------------------------------------------------------
# Round-level run config
# ---------------------------------------------------------------------------
def parse_source_txt(text: str) -> dict:
    """The run-config fields run_step3c_eval.sh writes into SOURCE.txt."""
    fields: dict[str, object] = {}
    lines = text.splitlines()
    for line in lines:
        if m := re.match(r"^task (\S+), task digest (\S+)$", line):
            fields["task"], fields["task_digest"] = m.group(1), m.group(2)
        elif m := re.match(r"^model (\S+), reasoning_effort (\S+), k=(\d+) .*agent (\S+) via (.+)$", line):
            fields.update(model=m.group(1), reasoning_effort=m.group(2), k=int(m.group(3)),
                          agent=m.group(4), launcher=m.group(5).strip())
        elif m := re.match(r"^model none, k=0", line):
            fields.update(model=None, k=0)
        elif line.startswith("TERMINUS_MAX_OUTPUT_BYTES="):
            fields["capture"] = line.strip()
        elif m := re.match(r"^controls .* via local harbor (\S+) \((.+)\)$", line):
            fields["local_harbor"], fields["control_adapters"] = m.group(1), m.group(2)
        elif line.startswith("credential policy:"):
            fields["credential_policy"] = line.split(":", 1)[1].strip()
        elif m := re.match(r"^arch (\S+), started (\S+), stb (\S+) \(bundled harbor patched: (\w+)\)", line):
            fields.update(arch=m.group(1), started=m.group(2), stb=m.group(3), bundled_patched=m.group(4))
    fields["notes"] = [line for line in lines if line.startswith(("ABORT", "stb-bundled harbor lost", "finished"))]
    return fields


def parse_hash_file(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            out[parts[1]] = parts[0]
    return out


def patch_guard_entries(text: str) -> dict[str, dict]:
    """Last patch-guard entry per label: rc, stamp revision and stamped harbor version."""
    entries: dict[str, dict] = {}
    current: dict | None = None
    for line in text.splitlines():
        if m := re.match(r"^(\S+) patch guard \((.+)\): rc=(\d+)$", line):
            current = {"at": m.group(1), "rc": int(m.group(3))}
            entries[m.group(2)] = current
        elif current is not None:
            if m := re.search(r"stamp revision: '([^']+)'", line):
                current["revision"] = m.group(1)
            elif m := re.search(r"stamped '([^']+)', installed '([^']+)'", line):
                current["stb_harbor"] = m.group(2)
    return entries


def load_round(path: Path, role: str) -> dict:
    path = path.resolve()
    if not path.is_dir():
        raise WorkflowError(f"{role} round not found: {path}")
    if (path / "composition.json").exists():
        raise WorkflowError(f"{path.name} is itself a composed round; pass the rounds it was composed from")
    digest = read_text(path / "task-digest.txt")
    if not digest:
        raise WorkflowError(f"{path.name} has no readable task-digest.txt")
    source = parse_source_txt(read_text(path / "SOURCE.txt"))
    if source.get("task_digest") not in (None, digest):
        raise WorkflowError(f"{path.name}: SOURCE.txt digest {source.get('task_digest')} != task-digest.txt {digest}")
    return {
        "path": path, "name": path.name, "role": role, "digest": digest,
        "agent_digest": read_text(path / "agent-digest.txt"),
        "grader_digest": read_text(path / "grader-digest.txt"),
        "source": source,
        "hashes": parse_hash_file(read_text(path / "recording-source.sha256")),
        "guards": patch_guard_entries(read_text(path / "patch-guard.log")),
    }


def model_round_config(rnd: dict) -> dict:
    src = rnd["source"]
    missing = [k for k in ("model", "reasoning_effort", "agent", "launcher", "capture", "local_harbor",
                           "arch", "stb", "bundled_patched") if not src.get(k)]
    if missing:
        raise WorkflowError(f"{rnd['name']}: SOURCE.txt lacks {', '.join(missing)}; not a run_step3c_eval.sh model round")
    absent = [name for name in RUN_SOURCES if name not in rnd["hashes"]]
    if absent:
        raise WorkflowError(f"{rnd['name']}: recording-source.sha256 lacks {', '.join(absent)}")
    return {
        "task_digest": rnd["digest"], "agent_digest": rnd["agent_digest"] or None,
        "grader_digest": rnd["grader_digest"] or None,
        "model": src["model"], "reasoning_effort": src["reasoning_effort"], "agent": src["agent"],
        "launcher": src["launcher"], "capture": src["capture"], "local_harbor": src["local_harbor"],
        "arch": src["arch"], "stb": src["stb"], "bundled_harbor_patched": src["bundled_patched"],
        "run_source_sha256": {name: rnd["hashes"][name] for name in RUN_SOURCES},
    }


def control_round_config(rnd: dict) -> dict:
    src = rnd["source"]
    if not src.get("local_harbor") or not src.get("arch"):
        raise WorkflowError(f"{rnd['name']}: SOURCE.txt lacks the local harbor version or arch")
    absent = [name for name in CONTROL_SOURCES if name not in rnd["hashes"]]
    if absent:
        raise WorkflowError(f"{rnd['name']}: recording-source.sha256 lacks {', '.join(absent)}")
    return {"task_digest": rnd["digest"], "agent_digest": rnd["agent_digest"] or None,
            "grader_digest": rnd["grader_digest"] or None,
            "local_harbor": src["local_harbor"], "arch": src["arch"],
            "control_source_sha256": {name: rnd["hashes"][name] for name in CONTROL_SOURCES}}


def diff(a: dict, b: dict) -> list[str]:
    return [f"{k}: {a.get(k)!r} vs {b.get(k)!r}" for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]


# ---------------------------------------------------------------------------
# Trials
# ---------------------------------------------------------------------------
def trial_record(rnd: dict, job: Path, slot: int) -> list[dict]:
    trials = sorted(d for d in job.iterdir() if d.is_dir() and (d / "config.json").is_file())
    lock = read_json(job / "lock.json")
    records = []
    if not trials:
        return [{"round": rnd["name"], "job": job.name, "attempt": slot, "trial": None, "trial_id": None,
                 "started": parse_utc(lock.get("created_at")), "finished": None, "path": None,
                 "exception": None, "reward": None, "tests": None, "valid": False,
                 "problems": ["job directory holds no trial"], "category": "incomplete",
                 "lock_harbor": (lock.get("harbor") or {}).get("version")}]
    for td in trials:
        result = read_json(td / "result.json")
        exc = result.get("exception_info") if isinstance(result.get("exception_info"), dict) else None
        started = parse_utc(result.get("started_at")) or parse_utc(lock.get("created_at"))
        rec = {"round": rnd["name"], "job": job.name, "attempt": slot, "trial": td.name,
               "trial_id": result.get("id"), "started": started, "finished": parse_utc(result.get("finished_at")),
               "path": td, "exception": exc, "lock_harbor": (lock.get("harbor") or {}).get("version")}
        check = check_trial(str(td), EFFORT)
        problems = list(check["problems"])
        rec["reward"] = check.get("reward")
        rec["tests"] = check.get("tests")
        ctrf = read_json(td / "verifier" / "ctrf.json")
        cases = (ctrf.get("results") or {}).get("tests") if isinstance(ctrf.get("results"), dict) else None
        if not isinstance(cases, list) or not cases:
            problems.append("verifier CTRF missing or without test records")
        for rel in ("trial.log", "verifier/reward.txt", "agent/recording.cast"):
            if not (td / rel).is_file():
                problems.append(f"missing {rel}")
        if not list((td / "agent" / "terminal-output").glob("*.txt")):
            problems.append("raw terminal observations missing (agent/terminal-output/)")
        steps = read_json(td / "agent" / "trajectory.json").get("steps")
        if not isinstance(steps, list) or not steps:
            problems.append("ATIF steps missing")
        if not result:
            problems.append("no readable result.json")
        elif result.get("finished_at") is None and exc is None:
            problems.append("result.json has no finished_at (still running, or died without a record)")
        rec["problems"] = sorted(set(problems))
        rec["valid"] = not rec["problems"] and exc is None
        if exc is not None:
            etype = str(exc.get("exception_type") or "")
            rec["category"] = ("operator-stop" if etype in OPERATOR_STOP
                               else "credential/quota" if CREDENTIAL.search(etype + " " + str(exc.get("exception_message", "")))
                               else "exception_info")
        elif not rec["valid"]:
            rec["category"] = "incomplete" if any("finished_at" in p or "result.json" in p for p in rec["problems"]) \
                else "fidelity"
        else:
            rec["category"] = None
        # The trial's own record of how it was configured (compared across every candidate).
        cfg = read_json(td / "config.json")
        agent = cfg.get("agent") if isinstance(cfg.get("agent"), dict) else {}
        rec["config"] = {"agent_name": agent.get("name"), "model_name": agent.get("model_name"),
                         "kwargs": agent.get("kwargs"),
                         "recording_config": read_json(td / "agent" / "recording_config.json") or None,
                         "task_checksum": result.get("task_checksum"),
                         "agent_info": result.get("agent_info")}
        records.append(rec)
    return records


def model_trials(rnd: dict, slug: str) -> list[dict]:
    pattern = model_job_re(slug)
    out = []
    other = [d.name for d in rnd["path"].iterdir() if d.is_dir() and re.search(r"gpt56-k\d+$", d.name)]
    if other:
        raise WorkflowError(f"{rnd['name']}: batch-layout jobs {other} are not supported; one Harbor job per attempt")
    for job in sorted(rnd["path"].iterdir()):
        m = pattern.fullmatch(job.name)
        if job.is_dir() and m:
            out += trial_record(rnd, job, int(m.group(1)))
    return out


def reason_for(rec: dict) -> str:
    exc = rec.get("exception")
    if exc:
        return (f"{rec['category']}: exception_info {exc.get('exception_type')}: "
                f"{str(exc.get('exception_message') or '')[:140]}").strip()
    return f"{rec['category']}: " + "; ".join(rec["problems"])


def other_rounds(slug: str, digest: str, listed: set[Path], out: Path, roots: set[Path]) -> list[Path]:
    pattern = model_job_re(slug)
    found = []
    for root in sorted(roots):
        try:
            children = sorted(root.iterdir())
        except OSError:
            continue
        for d in children:
            d = d.resolve()
            if not d.is_dir() or d in listed or d == out or (d / "composition.json").exists():
                continue
            if read_text(d / "task-digest.txt") != digest:
                continue
            try:
                if any(pattern.fullmatch(c.name) for c in d.iterdir() if c.is_dir()):
                    found.append(d)
            except OSError:
                continue
    return found


# ---------------------------------------------------------------------------
# Compose
# ---------------------------------------------------------------------------
def compose(task: Path, sources: list[Path], controls: Path, out: Path, reasons: dict[str, str],
            workspace: Path | None = None) -> dict:
    task, out = task.resolve(), out.resolve()
    slug = task.name
    if out.exists():
        raise WorkflowError(f"choose a fresh OUT directory: {out} already exists")
    if not task.is_dir():
        raise WorkflowError(f"task directory not found: {task}")
    if out.is_relative_to(task):
        raise WorkflowError("OUT must be outside the task tree")
    if not sources:
        raise WorkflowError("at least one --source round is required")

    rounds = [load_round(p, "model") for p in sources]
    if len({r["path"] for r in rounds}) != len(rounds):
        raise WorkflowError("a source round is listed twice")
    ctl_round = next((r for r in rounds if r["path"] == controls.resolve()), None) or load_round(controls, "controls")

    # 1. One digest, one run config.
    digests = {r["name"]: (r["digest"], r["agent_digest"], r["grader_digest"]) for r in rounds + [ctl_round]}
    if len({d[0] for d in digests.values()}) != 1:
        raise WorkflowError("source rounds are at different task digests; pooling never crosses digests: "
                            + "; ".join(f"{k}={v[0]}" for k, v in digests.items()))
    split = {(a, g) for _, a, g in digests.values() if a and g}
    if len(split) > 1:
        raise WorkflowError(f"source rounds disagree on agent/grader digests: {sorted(split)}")
    digest = rounds[0]["digest"]
    agent_d, grader_d = next(iter(split)) if split else ("", "")
    for r in rounds + [ctl_round]:
        if r["source"].get("task") not in (None, slug):
            raise WorkflowError(f"{r['name']}: SOURCE.txt names task {r['source'].get('task')!r}, not {slug!r}")
    current = task_digest(task)
    digest_note = None
    if current != digest:
        now_split = split_digests(task)
        if not (agent_d and grader_d) or (agent_d, grader_d) != (now_split["agent"], now_split["grader"]):
            raise WorkflowError(f"source rounds bind to {digest}; the task is now {current} and the agent/grader "
                                "surfaces are not both unchanged")
        digest_note = f"captured at {digest}; task now {current}; agent and grader digests unchanged (descriptive-only edit)"

    config = model_round_config(rounds[0])
    for r in rounds[1:]:
        delta = diff(config, model_round_config(r))
        if delta:
            raise WorkflowError(f"{r['name']} was not run with the same config as {rounds[0]['name']}: " + "; ".join(delta))
    ctl_config = control_round_config(ctl_round)
    expected_ctl = {"task_digest": digest, "agent_digest": config["agent_digest"],
                    "grader_digest": config["grader_digest"], "local_harbor": config["local_harbor"],
                    "arch": config["arch"],
                    "control_source_sha256": {k: config["run_source_sha256"][k] for k in CONTROL_SOURCES}}
    delta = diff(expected_ctl, ctl_config)
    if delta:
        raise WorkflowError(f"controls round {ctl_round['name']} differs from the model rounds: " + "; ".join(delta))

    # 2. Every candidate trial, in launch order.
    candidates: list[dict] = []
    for r in rounds:
        candidates += model_trials(r, slug)
    if not candidates:
        raise WorkflowError("no model trials in the source rounds")
    undated = [f"{c['round']}/{c['job']}" for c in candidates if c["started"] is None]
    if undated:
        raise WorkflowError(f"cannot place in launch order (no UTC start time in result.json or lock.json): {undated}")
    ids = [c["trial_id"] for c in candidates if c["trial_id"]]
    if len(ids) != len(set(ids)):
        raise WorkflowError("the same trial ID appears twice across the sources (a round copied into another?)")
    candidates.sort(key=lambda c: (c["started"], c["trial_id"] or ""))

    reference = next((c["config"] for c in candidates if c["valid"]), None)
    for c in candidates:
        if not c.get("config") or c["path"] is None:
            continue
        cfg = c["config"]
        if cfg["agent_name"] and cfg["agent_name"] != MODEL_AGENT:
            raise WorkflowError(f"{c['round']}/{c['job']}: agent {cfg['agent_name']!r}, expected {MODEL_AGENT}")
        if reference and c["valid"]:
            delta = diff(reference, cfg)
            if delta:
                raise WorkflowError(f"{c['round']}/{c['job']}/{c['trial']} was not run with the same config: "
                                    + "; ".join(delta))
        if c["valid"]:
            guard = next((g for label, g in rounds_by_name(rounds)[c["round"]]["guards"].items()
                          if label == c["job"]), None)
            if guard is None or guard.get("rc") != 0 or not guard.get("revision"):
                raise WorkflowError(f"{c['round']}/{c['job']}: no passing patch-guard.log entry records the "
                                    "full-fidelity patch revision before this attempt")
            c["patch_revision"] = guard["revision"]
            c["stb_harbor"] = guard.get("stb_harbor")
    lock_versions = {c["lock_harbor"] for c in candidates if c["valid"]}
    if len(lock_versions) > 1:
        raise WorkflowError(f"model jobs ran on different Harbor versions: {sorted(map(str, lock_versions))}")
    revisions = {(c.get("patch_revision"), c.get("stb_harbor")) for c in candidates if c["valid"]}
    if len(revisions) > 1:
        raise WorkflowError(f"model trials ran under different full-fidelity patch revisions: {sorted(revisions)}")

    valid = [c for c in candidates if c["valid"]]
    if len(valid) < 5:
        raise WorkflowError(f"only {len(valid)} fidelity-complete trial(s) across the sources; five are required\n"
                            + table(candidates))
    selected = valid[:5]
    fifth = selected[-1]["started"]
    for c in candidates:
        key_ids = {x for x in (c["trial_id"], c["trial"], f"{c['round']}/{c['job']}") if x}
        given = next((reasons[k] for k in key_ids if k in reasons), None)
        c["operator_reason"] = given
        if c in selected:
            c["status"], c["slot"] = "selected", selected.index(c) + 1
            c["reason"] = f"fidelity-complete; launch position {candidates.index(c) + 1}"
            if given:
                raise WorkflowError(f"--reason given for {c['trial_id']}, a selected trial; nothing to exclude")
        elif c["started"] > fifth:
            c["status"] = "not_selected"
            c["reason"] = ("launched after the fifth selected trial" +
                           ("" if c["valid"] else f" (also not fidelity-complete — {reason_for(c)})"))
        else:
            c["status"] = "excluded"
            c["reason"] = reason_for(c)
            if c["category"] in ("operator-stop", "incomplete") and not given:
                raise WorkflowError(
                    f"{c['round']}/{c['job']}/{c['trial']} ({c['trial_id']}) was launched before the fifth selected "
                    f"trial and ended as {c['category']}. Excluding it needs an explicit outcome-independent reason: "
                    f"--reason {c['trial_id'] or c['round'] + '/' + c['job']}='<why>' — or wait for it to finish")
        if given:
            c["reason"] += f"; operator: {given}"
    used = {k for c in candidates for k in (c["trial_id"], c["trial"], f"{c['round']}/{c['job']}") if k}
    unknown = sorted(set(reasons) - used)
    if unknown:
        raise WorkflowError(f"--reason names no candidate trial: {unknown}")

    # 3. No same-digest, same-config round left out.
    roots = {r["path"].parent for r in rounds} | {workspace.resolve() if workspace else REPO_ROOT}
    listed = {r["path"] for r in rounds} | {ctl_round["path"]}
    known_ids = set(ids)
    others = []
    for path in other_rounds(slug, digest, listed, out, roots):
        rnd = load_round(path, "model")
        entry = {"path": portable_path(path)}
        try:
            delta = diff(config, model_round_config(rnd))
        except WorkflowError as exc:
            delta = [str(exc)]
        trials = model_trials(rnd, slug)
        fresh = [t for t in trials if t["trial_id"] not in known_ids]
        early = [t for t in fresh if t["started"] is not None and t["started"] <= fifth]
        if not fresh:
            entry["disposition"] = "every trial is already a candidate (a copy of a source)"
        elif delta:
            entry["disposition"] = "different run config: " + "; ".join(delta)
        elif early:
            raise WorkflowError(
                f"{path.name} is a round at this digest and run config with trial(s) launched before the fifth "
                f"selected trial ({', '.join(t['job'] for t in early)}); pass it as --source — no attempt may be skipped")
        else:
            entry["disposition"] = "every trial launched after the fifth selected trial"
        others.append(entry)

    # 4. Controls: five jobs, one finished trial each, of this task, with CTRF and no exception.
    for job in CONTROL_JOBS:
        if not (ctl_round["path"] / job).is_dir():
            raise WorkflowError(f"controls round {ctl_round['name']} has no {job}/")
        trials = [d for d in (ctl_round["path"] / job).iterdir() if d.is_dir() and (d / "config.json").is_file()]
        if len(trials) != 1:
            raise WorkflowError(f"{ctl_round['name']}/{job}: expected one trial, found {len(trials)}")
        result = read_json(trials[0] / "result.json")
        ctrf = read_json(trials[0] / "verifier" / "ctrf.json")
        cases = (ctrf.get("results") or {}).get("tests") if isinstance(ctrf.get("results"), dict) else None
        problems = []
        if not task_matches(result.get("task_name"), slug) or not task_matches(
                ((read_json(trials[0] / "config.json").get("task") or {}).get("path")), slug):
            problems.append(f"is not a trial of {slug}")
        if result.get("exception_info"):
            problems.append(f"exception_info {result['exception_info'].get('exception_type')}")
        if not isinstance(cases, list) or not cases or not (trials[0] / "verifier" / "reward.txt").is_file():
            problems.append("no verifier CTRF/reward")
        if problems:
            raise WorkflowError(f"{ctl_round['name']}/{job}/{trials[0].name}: " + "; ".join(problems))
    for c in candidates:
        if c["path"] is not None:
            result = read_json(c["path"] / "result.json")
            if result and not task_matches(result.get("task_name"), slug):
                raise WorkflowError(f"{c['round']}/{c['job']}/{c['trial']} is a trial of {result.get('task_name')!r}")

    # 5. Copy, never move.
    before = {r["name"]: inventory(r["path"]) for r in rounds}
    if ctl_round["name"] not in before:
        before[ctl_round["name"]] = inventory(ctl_round["path"])
    out.mkdir(parents=True)
    try:
        mapping = []
        for c in selected:
            new = f"{slug}-gpt56-t{c['slot']}"
            src_round = rounds_by_name(rounds)[c["round"]]["path"]
            shutil.copytree(src_round / c["job"], out / new, symlinks=True)
            for suffix in (".console.log", ".exit-codes.txt"):
                src = src_round / f"{c['job']}{suffix}"
                if src.is_file():
                    shutil.copy2(src, out / f"{new}{suffix}")
            mapping.append((c, new))
        control_rows = []
        for job in CONTROL_JOBS:
            shutil.copytree(ctl_round["path"] / job, out / job, symlinks=True)
            for suffix in (".console.log", ".exit-codes.txt"):
                src = ctl_round["path"] / f"{job}{suffix}"
                if src.is_file():
                    shutil.copy2(src, out / f"{job}{suffix}")
            for td in sorted(d for d in (out / job).iterdir() if d.is_dir() and (d / "config.json").is_file()):
                result = read_json(td / "result.json")
                ctrf = read_json(td / "verifier" / "ctrf.json")
                summary = (ctrf.get("results") or {}).get("summary") if isinstance(ctrf.get("results"), dict) else {}
                control_rows.append({"job": job, "trial": td.name, "trial_id": result.get("id"),
                                     "started_at": result.get("started_at"),
                                     "reward": read_text(td / "verifier" / "reward.txt") or None,
                                     "tests_passed": f"{summary.get('passed')}/{summary.get('tests')}" if summary else None,
                                     "exception": (result.get("exception_info") or {}).get("exception_type")})
        for r in {x["name"]: x for x in rounds + [ctl_round]}.values():
            dest = out / "provenance" / r["name"]
            dest.mkdir(parents=True)
            for name in PROVENANCE_FILES:
                if (r["path"] / name).is_file():
                    shutil.copy2(r["path"] / name, dest / name)

        (out / "task-digest.txt").write_text(digest + "\n", encoding="utf-8")
        if agent_d and grader_d:
            (out / "agent-digest.txt").write_text(agent_d + "\n", encoding="utf-8")
            (out / "grader-digest.txt").write_text(grader_d + "\n", encoding="utf-8")
        shutil.copy2(rounds[0]["path"] / "recording-source.sha256", out / "recording-source.sha256")

        src_lines = read_text(rounds[0]["path"] / "SOURCE.txt").splitlines()
        ctl_lines = read_text(ctl_round["path"] / "SOURCE.txt").splitlines()
        head = [line for line in src_lines if line.startswith(("task ", "model ", "TERMINUS_MAX_OUTPUT_BYTES="))]
        ctl = [line for line in ctl_lines if line.startswith("controls ")]
        composed_at = iso(datetime.now(timezone.utc))
        lines = head + ctl + [
            "credential policy: " + "; ".join(f"{r['name']}: {r['source'].get('credential_policy', '?')}" for r in rounds),
            f"arch {config['arch']}, stb {config['stb']} (bundled harbor patched: {config['bundled_harbor_patched']}), "
            f"full-fidelity patch {selected[0].get('patch_revision')}, local harbor {config['local_harbor']}",
            f"composed {composed_at} by scripts/compose_step3c.py (MASTER_CHECKLIST_TBSCI.md #94 item 1): first five "
            "fidelity-complete trials in launch order across " + ", ".join(r["name"] for r in rounds)
            + f"; controls from {ctl_round['name']}; every candidate and exclusion in composition.json",
        ] + [f"source {r['name']}: started {r['source'].get('started', '?')}"
             + "".join(f"; {n}" for n in r["source"].get("notes", [])) for r in rounds]
        (out / "SOURCE.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

        report = {
            "schema_version": "1.0",
            "tool": "scripts/compose_step3c.py",
            "rule": ("MASTER_CHECKLIST_TBSCI.md #94 item 1: the five packaged runs are the first five "
                     "fidelity-complete trials at the current digest and run config, in launch order across "
                     "rounds, with no valid attempt skipped"),
            "task": slug, "task_digest": digest, "agent_digest": agent_d or None, "grader_digest": grader_d or None,
            "digest_note": digest_note, "composed_at": composed_at, "out": portable_path(out),
            "run_config": {**config, "patch_revision": selected[0].get("patch_revision"),
                           "stb_bundled_harbor": selected[0].get("stb_harbor"),
                           "harbor_lock_version": selected[0].get("lock_harbor"),
                           "trial_config": selected[0]["config"]},
            "sources": [{"round": r["name"], "path": portable_path(r["path"]),
                         "started": r["source"].get("started"),
                         "credential_policy": r["source"].get("credential_policy"),
                         "notes": r["source"].get("notes", [])} for r in rounds],
            "controls_source": {"round": ctl_round["name"], "path": portable_path(ctl_round["path"]),
                                "config": ctl_config},
            "selection": "sort every model trial across the sources by result.json started_at (UTC); "
                         "take the first five fidelity-complete trials",
            "candidates": [{
                "launch_position": i, "round": c["round"], "job": c["job"], "trial": c["trial"],
                "trial_id": c["trial_id"], "started_at": iso(c["started"]), "finished_at": iso(c["finished"]),
                "reward": c.get("reward"), "tests_passed": c.get("tests"),
                "exception_type": (c["exception"] or {}).get("exception_type"),
                "fidelity_complete": c["valid"], "problems": c.get("problems", []),
                "status": c["status"], "reason": c["reason"],
                "composed_job": f"{slug}-gpt56-t{c['slot']}" if c["status"] == "selected" else None,
            } for i, c in enumerate(candidates, 1)],
            "selected": [{"composed_job": new, "original_round": c["round"], "original_job": c["job"],
                          "trial": c["trial"], "trial_id": c["trial_id"], "started_at": iso(c["started"]),
                          "reward": c.get("reward"), "tests_passed": c.get("tests")} for c, new in mapping],
            "controls": control_rows,
            "other_rounds_at_digest": others,
            "job_level_note": ("each composed job directory is a byte copy of the captured job; its job-level "
                               "config.json / lock.json / job.log still name original_job. Trial folders, trial IDs "
                               "and timestamps are untouched."),
        }
        write_json(out / "composition.json", report)

        links: dict[str, str] = {}
        for c, new in mapping:
            src_round = rounds_by_name(rounds)[c["round"]]["path"]
            job_links: dict[str, str] = {}
            if inventory(src_round / c["job"], 1) != inventory(out / new, 1, job_links):
                raise WorkflowError(f"copy of {c['round']}/{c['job']} differs from its source")
            links.update({f"{new}/{relative}": text for relative, text in job_links.items()})
        for job in CONTROL_JOBS:
            job_links = {}
            inventory(out / job, 1, job_links)
            links.update({f"{job}/{relative}": text for relative, text in job_links.items()})
        if links:
            # In-artifacts symlinks (Master #55) copied as links, with their exact link text.
            report["artifact_symlinks"] = dict(sorted(links.items()))
        for r in rounds + [ctl_round]:
            if inventory(r["path"]) != before[r["name"]]:
                raise WorkflowError(f"source round {r['name']} changed while composing; wait for it to finish")

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = check_trajectory_main([str(out), "--effort", EFFORT])
        (out / "fidelity-check.log").write_text(buffer.getvalue(), encoding="utf-8")
        report["fidelity_check"] = buffer.getvalue().strip().splitlines()[-1] if buffer.getvalue().strip() else ""
        report["fidelity_rc"] = rc
        write_json(out / "composition.json", report)
    except BaseException:
        # Everything under OUT is a copy; leave nothing that looks like a round behind.
        shutil.rmtree(out, ignore_errors=True)
        raise
    return report


def task_matches(value: object, slug: str) -> bool:
    """Harbor records the task as a path or as org/slug; the last component is the slug."""
    return isinstance(value, str) and Path(value).name == slug


def rounds_by_name(rounds: list[dict]) -> dict[str, dict]:
    return {r["name"]: r for r in rounds}


def table(candidates: list[dict]) -> str:
    rows = []
    for i, c in enumerate(candidates, 1):
        rows.append(f"  {i:>2}. {iso(c['started'])}  {c['round']}/{c['job']}  {c['trial_id']}  "
                    f"reward={c.get('reward')}  {'VALID' if c['valid'] else 'INVALID'}"
                    f"  {c.get('status', '')}  {c.get('reason', '' if c['valid'] else reason_for(c))}")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--source", type=Path, action="append", required=True,
                        help="a Step 3c round holding <slug>-gpt56-tN jobs (repeat for each round)")
    parser.add_argument("--controls", type=Path, required=True,
                        help="the round holding oracle-1..3 and nop-1..2 (a source round or a CONTROLS_ONLY=1 round)")
    parser.add_argument("--out", type=Path, required=True, help="fresh output directory")
    parser.add_argument("--reason", action="append", default=[], metavar="TRIAL=TEXT",
                        help="outcome-independent reason for excluding a non-fidelity-complete trial "
                             "(trial ID, trial name or <round>/<job>); required for an operator stop or an "
                             "unfinished trial inside the first five")
    parser.add_argument("--workspace", type=Path, default=None,
                        help="directory scanned for other rounds at this digest (default: the repo root)")
    args = parser.parse_args(argv)
    reasons = {}
    for item in args.reason:
        key, sep, text = item.partition("=")
        if not sep or not key.strip() or not text.strip():
            parser.error(f"--reason must be TRIAL=TEXT: {item!r}")
        reasons[key.strip()] = text.strip()
    try:
        report = compose(args.task_dir, args.source, args.controls, args.out, reasons, args.workspace)
    except (OSError, WorkflowError) as exc:
        print(f"compose_step3c.py: REFUSED: {exc}", file=sys.stderr)
        return 2
    print(f"composed {report['out']}  task {report['task']}  digest {report['task_digest']}")
    for c in report["candidates"]:
        print(f"  {c['launch_position']:>2}. {c['started_at']}  {c['round']}/{c['job']}  {c['trial_id']}  "
              f"reward={c['reward']}  {c['status'].upper():<12} {c['composed_job'] or ''}  {c['reason']}")
    for row in report["controls"]:
        print(f"  control {row['job']}: reward={row['reward']} tests={row['tests_passed']} exception={row['exception']}")
    for entry in report["other_rounds_at_digest"]:
        print(f"  other round {entry['path']}: {entry['disposition']}")
    print(report["fidelity_check"])
    return 0 if report["fidelity_rc"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
