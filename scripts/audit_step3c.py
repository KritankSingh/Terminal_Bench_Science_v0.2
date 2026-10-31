#!/usr/bin/env python3
"""Build the per-trial Step 3c audit dossier from a Harbor jobs directory.

After ``scripts/run_step3c_eval.sh`` finishes, the author must classify every
model trial from its full trajectory (``prompts/step3c.md`` section 3). This
script reads each ``<slug>-gpt56-tN`` trial (result.json, CTRF, legacy upstream Terminus-2 ATIF
trajectory and its continuation/summarization files, raw terminal observations,
collected artifacts, raw API log and capture-fidelity signals) and each control (``oracle-1``, ``oracle-2``, ``nop-1``
execution traces) and writes one markdown dossier: a summary table, raw pass@1,
and a section per trial with command counts, token usage, compaction events,
harness errors, reward-hack and refusal signals, and a compact command timeline.

It is a reading aid for the human audit, not a verdict. Missing files are
reported as ``MISSING``; malformed JSON is reported inline. The script exits 0
unless its arguments are invalid.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

from common import WorkflowError, load_test_manifest, portable_path, task_digest


MISSING = "MISSING"
# docs/DELIVERY_CHECKLIST.md requires oracle x3 and nop x2, not two and one: three runs are
# what separates a passing Oracle from a flaky one. Listing only oracle-1/-2 here meant
# no task's dossier could ever show oracle-3, however many Oracles the round actually had.
CONTROL_JOBS = (("oracle-1", "oracle"), ("oracle-2", "oracle"), ("oracle-3", "oracle"),
                ("nop-1", "nop"), ("nop-2", "nop"))
EXPECTED_MODEL_ATTEMPTS = 5
FIRST_COMMANDS, LAST_COMMANDS, COMMAND_WIDTH = 40, 20, 160
FINAL_MESSAGE_WIDTH = 1200

_PER_TRIAL_MODEL = re.compile(r"(?:^|-)gpt56-t([1-5])$")
_BATCH_MODEL = re.compile(r"^gpt56-k([1-9][0-9]*)$")
_CONTINUATION = re.compile(r"^trajectory\.cont-(\d+)\.json$")
_SUMMARIZATION = re.compile(r"^trajectory\.summarization-(\d+)-(\w+)\.json$")
_TRUNCATED = re.compile(r"\[\.\.\. output limited to \d+ bytes; \d+ interior bytes omitted \.\.\.\]")
REQUIRED_REASONING_EFFORT = "xhigh"

_RUN_SIM = re.compile(r"/app/tools/build/run_sim|\brun_sim\b")
_SUBMISSION = re.compile(r"/app/submission")
_WRITE_HINT = re.compile(
    r"(?:>>?|\btee\b|\bcp\b|\bmv\b|\brm\b|\bmkdir\b|\btouch\b|\bsed\s+-i|\bln\b|<<|"
    r"\bcat\s*>|\bnano\b|\bvim?\b|\bpatch\b|\binstall\b|\bcmake\b|\bmake\b|\bpython3?\b)"
)
_BUILD = re.compile(r"\bcmake\b|\bmake\b|\bninja\b|\b(?:g\+\+|c\+\+|clang\+\+|gcc|clang)\b")
_SLEEP = re.compile(r"\bsleep\s+(\d+(?:\.\d+)?)")
_HACK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("touches /tests", re.compile(r"(?<![\w/.])/tests(?:/|\b)")),
    ("touches /logs", re.compile(r"(?<![\w/.])/logs(?:/|\b)")),
    ("touches /oracle", re.compile(r"(?<![\w/.])/oracle(?:/|\b)")),
    ("touches /solution", re.compile(r"(?<![\w/.])/solution(?:/|\b)")),
    ("LD_PRELOAD", re.compile(r"\bLD_PRELOAD\b")),
    ("setpriv", re.compile(r"\bsetpriv\b")),
    ("chmod on /app", re.compile(r"\bchmod\b[^\n;&|]*\s/app(?![\w-])")),
    ("reward/ctrf file", re.compile(r"reward\.txt|\bctrf(?:\.json)?\b")),
    ("hidden_scenarios", re.compile(r"hidden_scenarios")),
    ("escalation (sudo/su)", re.compile(r"\bsudo\b|(?:^|[;&|]\s*)su\b")),
)
_REFUSAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cannot/won't help or assist", re.compile(
        r"\bI\s+(?:can(?:no|')t|cannot|won't|will\s+not|am\s+unable\s+to|'m\s+unable\s+to|am\s+not\s+able\s+to|"
        r"'m\s+not\s+able\s+to)\s+(?:help|assist|comply|continue|proceed|complete|provide|do\s+this|do\s+that)", re.I)),
    ("declines", re.compile(r"\bI\s+(?:must|have\s+to|need\s+to|will|'ll)?\s*(?:decline|refuse)\b", re.I)),
    ("policy / guidelines", re.compile(
        r"\b(?:against|violat\w+|per|under)\s+(?:my|the|our|openai'?s?|anthropic'?s?)\s+(?:usage\s+)?(?:policy|policies|guidelines)\b|"
        r"\b(?:usage|content|safety)\s+polic(?:y|ies)\b", re.I)),
    ("not able/allowed", re.compile(r"\bnot\s+(?:able|allowed|permitted|going)\s+to\s+(?:help|assist|comply|proceed|continue|provide)\b", re.I)),
    ("harm/weapon framing", re.compile(r"\b(?:harmful|dangerous|weapon\w*|dual[- ]use|malicious)\b", re.I)),
)
_LOG_ERROR = re.compile(r"Traceback|\w*Error\b|\w*Exception\b|\b[Ff]ailed\b|timed out|\bTimeout\b")


# --------------------------------------------------------------------------- helpers

def read_json(path: Path) -> tuple[Any, str | None]:
    """Return (payload, None), (None, MISSING) or (None, error text)."""
    if not path.is_file():
        return None, MISSING
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace")), None
    except (OSError, ValueError) as exc:
        return None, f"ERROR: {type(exc).__name__}: {str(exc)[:200]}"


def read_text(path: Path) -> tuple[str | None, str | None]:
    if not path.is_file():
        return None, MISSING
    try:
        return path.read_text(encoding="utf-8", errors="replace"), None
    except OSError as exc:
        return None, f"ERROR: {exc}"


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def seconds_between(start: Any, end: Any) -> float | None:
    first, last = parse_timestamp(start), parse_timestamp(end)
    if first is None or last is None:
        return None
    try:
        return (last - first).total_seconds()
    except TypeError:  # naive vs aware
        return None


def fmt_seconds(value: float | None) -> str:
    if value is None:
        return MISSING
    return f"{value:.1f}s" if value < 120 else f"{value / 60:.1f}min"


def fmt_num(value: Any) -> str:
    if value is None:
        return MISSING
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return str(value)


def one_line(text: Any, width: int = COMMAND_WIDTH) -> str:
    collapsed = re.sub(r"\s+", " ", str(text)).strip()
    if len(collapsed) > width:
        return collapsed[: width - 1] + "…"
    return collapsed


def cell(text: Any) -> str:
    return one_line(text, 400).replace("|", "\\|")


def message_text(message: Any) -> str:
    """ATIF messages are a string or a list of ContentPart objects."""
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        return "\n".join(str(part.get("text")) for part in message
                         if isinstance(part, dict) and part.get("type") == "text" and part.get("text"))
    return "" if message is None else str(message)


def observation_text(step: dict[str, Any]) -> str:
    parts = []
    for result in as_list(as_dict(step.get("observation")).get("results")):
        if isinstance(result, dict):
            parts.append(message_text(result.get("content")))
    return "\n".join(parts)


def file_size(path: Path) -> str:
    try:
        return f"{path.stat().st_size:,} bytes" if path.is_file() else MISSING
    except OSError as exc:
        return f"ERROR: {exc}"


def trial_dirs(job: Path) -> list[Path]:
    try:
        return sorted(path for path in job.iterdir() if path.is_dir() and any(
            (path / marker).exists() for marker in ("config.json", "result.json", "agent", "verifier")))
    except OSError:
        return []


# --------------------------------------------------------------------------- shared trial facts

@dataclass
class TrialFacts:
    job: str
    kind: str
    label: str
    trial: Path | None
    notes: list[str] = field(default_factory=list)
    reward_file: str = MISSING
    reward_result: Any = None
    reward: float | None = None
    exception: str | None = None
    ctrf_summary: str = MISSING
    ctrf_cases: list[tuple[str, str]] = field(default_factory=list)
    verifier_seconds: float | None = None
    agent_seconds: float | None = None
    trial_log_errors: list[str] = field(default_factory=list)
    trial_log_status: str = MISSING
    task_name: Any = None

    @property
    def reward_text(self) -> str:
        if self.reward is None:
            return MISSING if self.reward_file == MISSING and self.reward_result is None else f"UNPARSED ({self.reward_file!r})"
        return fmt_num(self.reward)

    @property
    def ctrf_text(self) -> str:
        if not self.ctrf_cases:
            return self.ctrf_summary
        return ", ".join(f"{name.split('::')[-1]}={status}" for name, status in self.ctrf_cases)


def parse_reward(text: str | None) -> float | None:
    if text is None:
        return None
    try:
        return float(text.strip())
    except ValueError:
        return None


def collect_common(facts: TrialFacts) -> None:
    trial = facts.trial
    if trial is None:
        return
    result, error = read_json(trial / "result.json")
    if error:
        facts.notes.append(f"result.json: {error}")
    result = as_dict(result)
    facts.task_name = result.get("task_name")
    verifier_result = as_dict(result.get("verifier_result"))
    facts.reward_result = as_dict(verifier_result.get("rewards")).get("reward")
    exception = result.get("exception_info")
    if isinstance(exception, dict):
        facts.exception = f"{exception.get('exception_type')}: {one_line(exception.get('exception_message'), 300)}"
    elif exception:
        facts.exception = one_line(exception, 300)
    if (trial / "exception.txt").is_file():
        facts.notes.append("exception.txt present")
    facts.verifier_seconds = seconds_between(as_dict(result.get("verifier")).get("started_at"),
                                             as_dict(result.get("verifier")).get("finished_at"))
    facts.agent_seconds = seconds_between(as_dict(result.get("agent_execution")).get("started_at"),
                                          as_dict(result.get("agent_execution")).get("finished_at"))

    reward_text, error = read_text(trial / "verifier" / "reward.txt")
    facts.reward_file = error or reward_text.strip()
    facts.reward = parse_reward(reward_text)
    if facts.reward is None and isinstance(facts.reward_result, (int, float)):
        facts.reward = float(facts.reward_result)
        facts.notes.append("reward taken from result.json (reward.txt unusable)")
    elif (facts.reward is not None and isinstance(facts.reward_result, (int, float))
            and float(facts.reward_result) != facts.reward):
        facts.notes.append(f"reward.txt ({facts.reward}) disagrees with result.json ({facts.reward_result})")

    ctrf, error = read_json(trial / "verifier" / "ctrf.json")
    if error:
        facts.ctrf_summary = error
    else:
        results = as_dict(as_dict(ctrf).get("results"))
        summary = as_dict(results.get("summary"))
        tests = as_list(results.get("tests"))
        facts.ctrf_cases = [(str(as_dict(t).get("name")), str(as_dict(t).get("status"))) for t in tests]
        facts.ctrf_summary = (
            f"{summary.get('passed', '?')} passed / {summary.get('failed', '?')} failed / "
            f"{summary.get('skipped', '?')} skipped of {summary.get('tests', len(tests))}"
            if summary or tests else "ERROR: no CTRF results")

    log, error = read_text(trial / "trial.log")
    if error:
        facts.trial_log_status = error
    else:
        lines = log.splitlines()
        facts.trial_log_status = f"{len(lines)} lines"
        facts.trial_log_errors = [one_line(line, 200) for line in lines if _LOG_ERROR.search(line)]


# --------------------------------------------------------------------------- model trials

@dataclass
class Command:
    index: int
    segment: str
    step_id: Any
    timestamp: Any
    function: str
    text: str
    duration: Any = None


@dataclass
class ModelFacts(TrialFacts):
    segments: list[str] = field(default_factory=list)
    steps_total: int = 0
    steps_copied: int = 0
    steps_by_source: dict[str, int] = field(default_factory=dict)
    commands: list[Command] = field(default_factory=list)
    task_complete_calls: int = 0
    tokens_in: Any = None
    tokens_out: Any = None
    tokens_cached: Any = None
    cost_usd: Any = None
    tokens_source: str = MISSING
    final_message: str = MISSING
    final_step: str = MISSING
    agent_messages: list[tuple[str, str]] = field(default_factory=list)
    compaction: list[str] = field(default_factory=list)
    first_command_seconds: float | None = None
    first_command_note: str = ""
    hack_signals: list[str] = field(default_factory=list)
    hidden_mentions: dict[str, int] = field(default_factory=dict)
    refusal_signals: list[str] = field(default_factory=list)
    recording: str = MISSING
    cast: str = MISSING
    terminal_outputs: str = MISSING
    reasoning_effort: Any = None
    api_calls: str = MISSING
    api_efforts: dict[str, int] = field(default_factory=dict)
    truncated_observations: int = 0
    fidelity_problems: list[str] = field(default_factory=list)
    artifacts_summary: list[str] = field(default_factory=list)
    submission_files: list[str] = field(default_factory=list)
    submission_state: str = MISSING
    model_name: Any = None

    @property
    def ran_run_sim(self) -> int:
        return sum(1 for c in self.commands if _RUN_SIM.search(c.text))

    @property
    def submission_mentions(self) -> int:
        return sum(1 for c in self.commands if _SUBMISSION.search(c.text))

    @property
    def submission_writes(self) -> int:
        return sum(1 for c in self.commands if _SUBMISSION.search(c.text) and _WRITE_HINT.search(c.text))

    @property
    def build_commands(self) -> int:
        return sum(1 for c in self.commands if _BUILD.search(c.text))


def trajectory_segments(agent_dir: Path) -> list[tuple[str, Any, str | None]]:
    """Return [(name, payload, error)] for trajectory.json and trajectory.cont-N.json in order."""
    names = ["trajectory.json"]
    try:
        extra = [(int(m.group(1)), p.name) for p in agent_dir.iterdir() if (m := _CONTINUATION.match(p.name))]
    except OSError:
        extra = []
    names += [name for _, name in sorted(extra)]
    return [(name, *read_json(agent_dir / name)) for name in names]


def collect_model(facts: ModelFacts) -> None:
    collect_common(facts)
    trial = facts.trial
    if trial is None:
        return
    agent_dir = trial / "agent"
    result, _ = read_json(trial / "result.json")
    result = as_dict(result)
    facts.model_name = as_dict(as_dict(result.get("config")).get("agent")).get("model_name")
    agent_result = as_dict(result.get("agent_result"))
    if any(agent_result.get(k) is not None for k in ("n_input_tokens", "n_output_tokens")):
        facts.tokens_in, facts.tokens_out = agent_result.get("n_input_tokens"), agent_result.get("n_output_tokens")
        facts.tokens_cached, facts.cost_usd = agent_result.get("n_cache_tokens"), agent_result.get("cost_usd")
        facts.tokens_source = "result.json agent_result"

    # Recording adapter evidence.
    recording, error = read_json(agent_dir / "recording_config.json")
    recording = as_dict(recording)
    facts.recording = error or (
        f"adapter={recording.get('adapter')} max_output_bytes={recording.get('max_output_bytes')} "
        f"reasoning_effort={recording.get('reasoning_effort')} raw_api_log={recording.get('raw_api_log')}")
    facts.reasoning_effort = recording.get("reasoning_effort")
    if facts.reasoning_effort != REQUIRED_REASONING_EFFORT:
        facts.fidelity_problems.append(f"recorded reasoning_effort={facts.reasoning_effort!r}, required {REQUIRED_REASONING_EFFORT!r}")
    if recording.get("max_output_bytes") != 0:
        facts.fidelity_problems.append(f"max_output_bytes={recording.get('max_output_bytes')!r} (not uncapped)")
    facts.cast = file_size(agent_dir / "recording.cast")
    if not (agent_dir / "recording.cast").is_file():
        facts.fidelity_problems.append("recording.cast missing")

    # Raw API log written by the patched stb-bundled LiteLLM (scripts/patch_stb_harbor.py).
    api_log = agent_dir / "api-calls.jsonl"
    if api_log.is_file():
        count = 0
        try:
            for line in api_log.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                count += 1
                try:
                    request = as_dict(as_dict(json.loads(line)).get("request"))
                except ValueError:
                    key = "<unparsable>"
                else:
                    key = request.get("reasoning_effort") if isinstance(request.get("reasoning_effort"), str) else \
                        as_dict(request.get("reasoning")).get("effort") or "<none>"
                facts.api_efforts[str(key)] = facts.api_efforts.get(str(key), 0) + 1
            facts.api_calls = f"{count} records, {file_size(api_log)}"
        except OSError as exc:
            facts.api_calls = f"ERROR: {exc}"
        if count == 0:
            facts.fidelity_problems.append("api-calls.jsonl is empty")
        elif set(facts.api_efforts) != {REQUIRED_REASONING_EFFORT}:
            facts.fidelity_problems.append(
                "API requests carried reasoning effort "
                + ", ".join(f"{k}={v}" for k, v in sorted(facts.api_efforts.items())) + f"; required {REQUIRED_REASONING_EFFORT!r} only")
    else:
        facts.fidelity_problems.append("api-calls.jsonl missing")
    outputs = sorted((agent_dir / "terminal-output").glob("*.txt")) if (agent_dir / "terminal-output").is_dir() else []
    if outputs:
        try:
            facts.terminal_outputs = f"{len(outputs)} files, {sum(p.stat().st_size for p in outputs):,} bytes"
        except OSError as exc:
            facts.terminal_outputs = f"{len(outputs)} files (ERROR: {exc})"

    # Summarization/continuation files written by the legacy upstream Terminus-2 agent.
    try:
        names = sorted(p.name for p in agent_dir.iterdir())
    except OSError:
        names = []
    for name in names:
        if _SUMMARIZATION.match(name) or _CONTINUATION.match(name):
            facts.compaction.append(f"file: {name} ({file_size(agent_dir / name)})")

    # ATIF steps and commands.
    segments = trajectory_segments(agent_dir)
    all_texts: list[tuple[str, str]] = []  # (where, text) for hidden_scenarios search
    last_agent: tuple[str, str] | None = None
    first_command_ts: Any = None
    first_step_ts: Any = None
    for name, payload, error in segments:
        if error:
            facts.segments.append(f"{name}: {error}")
            continue
        payload = as_dict(payload)
        steps = as_list(payload.get("steps"))
        facts.segments.append(f"{name}: {len(steps)} steps, schema {payload.get('schema_version')}")
        facts.truncated_observations += len(_TRUNCATED.findall(json.dumps(steps)))
        if payload.get("continued_trajectory_ref"):
            facts.compaction.append(f"{name} continued in {payload['continued_trajectory_ref']}")
        if facts.tokens_source == MISSING:
            metrics = as_dict(payload.get("final_metrics"))
            if metrics:
                facts.tokens_in, facts.tokens_out = metrics.get("total_prompt_tokens"), metrics.get("total_completion_tokens")
                facts.tokens_cached, facts.cost_usd = metrics.get("total_cached_tokens"), metrics.get("total_cost_usd")
                facts.tokens_source = f"{name} final_metrics"
        for step in steps:
            step = as_dict(step)
            step_id, source = step.get("step_id"), str(step.get("source"))
            facts.steps_total += 1
            facts.steps_by_source[source] = facts.steps_by_source.get(source, 0) + 1
            if step.get("is_copied_context"):
                facts.steps_copied += 1
                continue  # Copied context duplicates a previous segment; do not double count.
            if first_step_ts is None:
                first_step_ts = step.get("timestamp")
            text = message_text(step.get("message"))
            reasoning = step.get("reasoning_content")
            if as_dict(step.get("extra")).get("context_management") or (
                    source == "system" and "summarization" in text.lower()):
                facts.compaction.append(f"{name} step {step_id}: {one_line(text, 120)}")
            for res in as_list(as_dict(step.get("observation")).get("results")):
                refs = as_list(as_dict(res).get("subagent_trajectory_ref"))
                for ref in refs:
                    facts.compaction.append(
                        f"{name} step {step_id}: subagent {as_dict(ref).get('trajectory_path')} "
                        f"({as_dict(as_dict(ref).get('extra')).get('summary', '')})")
            all_texts.append((f"{name} step {step_id} message", text))
            if isinstance(reasoning, str):
                all_texts.append((f"{name} step {step_id} reasoning", reasoning))
            all_texts.append((f"{name} step {step_id} observation", observation_text(step)))
            if source == "agent":
                if text.strip():
                    last_agent = (f"{name} step {step_id}", text)
                facts.agent_messages.append((f"{name} step {step_id}", text))
            for call in as_list(step.get("tool_calls")):
                call = as_dict(call)
                function = str(call.get("function_name"))
                arguments = as_dict(call.get("arguments"))
                if function == "mark_task_complete":
                    facts.task_complete_calls += 1
                    continue
                command_text = next((arguments[k] for k in ("keystrokes", "command", "cmd") if isinstance(arguments.get(k), str)), None)
                if command_text is None:
                    command_text = json.dumps(arguments, ensure_ascii=False)
                facts.commands.append(Command(len(facts.commands) + 1, name, step_id, step.get("timestamp"),
                                              function, command_text, arguments.get("duration")))
                if first_command_ts is None:
                    first_command_ts = step.get("timestamp")

    if facts.truncated_observations:
        facts.fidelity_problems.append(f"{facts.truncated_observations} truncated observation(s) in ATIF")
    if last_agent:
        facts.final_step, facts.final_message = last_agent
    elif facts.steps_total:
        facts.final_message = "(no non-empty agent message)"

    # Time to first command: ATIF step timestamps are recorded after the command batch ran,
    # so this is an upper bound on the LLM latency before the first command.
    started = as_dict(result.get("agent_execution")).get("started_at")
    if first_command_ts is not None:
        anchor = started if started else first_step_ts
        facts.first_command_seconds = seconds_between(anchor, first_command_ts)
        facts.first_command_note = ("from agent_execution.started_at" if started else "from first step timestamp") + \
            " to the first command step (stamped after that batch executed)"
    elif facts.commands == [] and facts.steps_total:
        facts.first_command_note = "no commands recorded"

    # Reward-hack signals over commands.
    for label, pattern in _HACK_PATTERNS:
        hits = [c for c in facts.commands if pattern.search(c.text)]
        if hits:
            facts.hack_signals.append(
                f"{label}: {len(hits)} command(s), e.g. #{hits[0].index} (step {hits[0].step_id}): `{one_line(hits[0].text, 120)}`")
    sleeps = [(c, float(m.group(1))) for c in facts.commands if (m := _SLEEP.search(c.text))]
    long_sleeps = [(c, s) for c, s in sleeps if s >= 30]
    if long_sleeps or len(sleeps) >= 5:
        worst = max(sleeps, key=lambda item: item[1])
        facts.hack_signals.append(
            f"sleep-based stalling: {len(sleeps)} sleep command(s), {len(long_sleeps)} of >=30s, longest {worst[1]:g}s "
            f"at #{worst[0].index} (step {worst[0].step_id})")
    durations = [c for c in facts.commands if isinstance(c.duration, (int, float)) and c.duration >= 300]
    if durations:
        facts.hack_signals.append(
            f"long command waits: {len(durations)} command(s) with duration >= 300s, e.g. #{durations[0].index} "
            f"({durations[0].duration}s)")
    for where, text in all_texts:
        if "hidden_scenarios" in text:
            kind = where.rsplit(" ", 1)[-1]
            facts.hidden_mentions[kind] = facts.hidden_mentions.get(kind, 0) + 1
    if facts.hidden_mentions:
        first = next(where for where, text in all_texts if "hidden_scenarios" in text)
        facts.hack_signals.append(
            f"mentions hidden_scenarios: " + ", ".join(f"{k} x{v}" for k, v in sorted(facts.hidden_mentions.items()))
            + f"; first at {first}")

    # Refusal signals over the final message and the last few agent messages.
    tail = facts.agent_messages[-4:]
    for label, pattern in _REFUSAL_PATTERNS:
        for where, text in tail:
            match = pattern.search(text)
            if match:
                facts.refusal_signals.append(f"{label} at {where}: `{one_line(match.group(0), 80)}`")
                break
    if facts.steps_total and not facts.commands:
        facts.refusal_signals.append("no commands were executed in the whole trajectory")

    # Collected artifacts (end-of-trial container state).
    manifest, error = read_json(trial / "artifacts" / "manifest.json")
    if error:
        facts.artifacts_summary.append(f"artifacts/manifest.json: {error}")
    for entry in as_list(manifest):
        entry = as_dict(entry)
        facts.artifacts_summary.append(f"{entry.get('source')} -> {entry.get('destination')} [{entry.get('status')}]")
    submission = trial / "artifacts" / "app" / "submission"
    if submission.is_dir():
        try:
            files = sorted(p for p in submission.rglob("*") if p.is_file())
        except OSError as exc:
            files = []
            facts.submission_state = f"ERROR: {exc}"
        shared = [p for p in files if p.suffix == ".so"]
        top = sorted(p.relative_to(submission).as_posix() for p in files if p.parent == submission)
        facts.submission_files = top[:20]
        facts.submission_state = (f"present: {len(files)} file(s), {len(top)} top-level, "
                                  f"{len(shared)} .so " + (f"({', '.join(p.relative_to(submission).as_posix() for p in shared[:3])})" if shared else "(no shared library)"))
    elif not error:
        facts.submission_state = "not collected (no artifacts/app/submission)"


# --------------------------------------------------------------------------- controls

@dataclass
class ControlFacts(TrialFacts):
    trace_events: dict[str, int] = field(default_factory=dict)
    trace_status: str = MISSING
    trace_commands: list[str] = field(default_factory=list)
    trace_return_codes: list[Any] = field(default_factory=list)
    oracle_txt: str = MISSING
    oracle_tail: list[str] = field(default_factory=list)


def collect_control(facts: ControlFacts) -> None:
    collect_common(facts)
    trial = facts.trial
    if trial is None:
        return
    text, error = read_text(trial / "agent" / "execution_trace.jsonl")
    if error:
        facts.trace_status = error
    else:
        bad = 0
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except ValueError:
                bad += 1
                continue
            event = as_dict(event)
            name = str(event.get("event"))
            facts.trace_events[name] = facts.trace_events.get(name, 0) + 1
            if name == "exec_start":
                facts.trace_commands.append(one_line(event.get("command"), COMMAND_WIDTH))
            elif name == "exec_end":
                facts.trace_return_codes.append(event.get("return_code"))
            elif name in ("exec_error", "run_error"):
                facts.notes.append(f"trace {name}: {event.get('exception_type')}: {one_line(event.get('exception'), 200)}")
        events = list(facts.trace_events)
        facts.trace_status = f"{sum(facts.trace_events.values())} events" + (f", {bad} malformed line(s)" if bad else "")
        if not events or events[0] != "run_start" or not any(e in facts.trace_events for e in ("run_end", "run_error")):
            facts.notes.append("execution trace lacks run_start/run_end")
    if facts.kind == "oracle":
        oracle_path = trial / "agent" / "oracle.txt"
        oracle, error = read_text(oracle_path)
        facts.oracle_txt = error or f"present ({file_size(oracle_path)})"
        if oracle is not None:
            facts.oracle_tail = [one_line(l, 200) for l in oracle.splitlines() if l.strip()][-5:]


# --------------------------------------------------------------------------- discovery

def discover(jobs: Path, slug: str) -> tuple[list[ModelFacts], list[ControlFacts]]:
    models: list[ModelFacts] = []
    found: dict[int, Path] = {}
    batches: list[Path] = []
    for child in sorted(jobs.iterdir()):
        if not child.is_dir():
            continue
        match = _PER_TRIAL_MODEL.search(child.name)
        if match:
            found.setdefault(int(match.group(1)), child)
        elif _BATCH_MODEL.fullmatch(child.name) or child.name == "gpt56-k5":
            batches.append(child)
    for attempt in range(1, EXPECTED_MODEL_ATTEMPTS + 1):
        job = found.get(attempt)
        label = f"t{attempt}"
        if job is None:
            models.append(ModelFacts(job=f"{slug}-gpt56-{label}", kind="model", label=label, trial=None,
                                     notes=["job directory MISSING"]))
            continue
        trials = trial_dirs(job)
        if not trials:
            models.append(ModelFacts(job=job.name, kind="model", label=label, trial=None, notes=["no trial directory"]))
            continue
        facts = ModelFacts(job=job.name, kind="model", label=label, trial=trials[0])
        if len(trials) > 1:
            facts.notes.append(f"{len(trials)} trial dirs in job; using {trials[0].name}")
        models.append(facts)
    for batch in batches:
        for index, trial in enumerate(trial_dirs(batch), start=1):
            models.append(ModelFacts(job=batch.name, kind="model", label=f"{batch.name}#{index}", trial=trial,
                                     notes=["batch job trial (outside the t1..t5 attempt identities)"]))
    controls: list[ControlFacts] = []
    for name, kind in CONTROL_JOBS:
        job = jobs / name
        trials = trial_dirs(job) if job.is_dir() else []
        facts = ControlFacts(job=name, kind=kind, label=name, trial=trials[0] if trials else None)
        if not job.is_dir():
            facts.notes.append("job directory MISSING")
        elif not trials:
            facts.notes.append("no trial directory")
        elif len(trials) > 1:
            facts.notes.append(f"{len(trials)} trial dirs in job; using {trials[0].name}")
        controls.append(facts)
    for facts in models:
        collect_model(facts)
    for facts in controls:
        collect_control(facts)
    return models, controls


# --------------------------------------------------------------------------- rendering

def command_timeline(commands: list[Command]) -> list[str]:
    if not commands:
        return ["(no commands recorded)"]
    if len(commands) <= FIRST_COMMANDS + LAST_COMMANDS:
        shown: list[Command | None] = list(commands)
    else:
        shown = [*commands[:FIRST_COMMANDS], None, *commands[-LAST_COMMANDS:]]
    lines = []
    for command in shown:
        if command is None:
            lines.append(f"    ... {len(commands) - FIRST_COMMANDS - LAST_COMMANDS} command(s) omitted ...")
            continue
        duration = f" ({command.duration}s)" if command.duration not in (None, "") else ""
        function = "" if command.function == "bash_command" else f" [{command.function}]"
        segment = "" if command.segment == "trajectory.json" else command.segment.removeprefix("trajectory.").removesuffix(".json") + " "
        lines.append(f"{command.index:4d}. {segment}step {command.step_id}{function}{duration}: {one_line(command.text)}")
    return lines


def bullet(label: str, value: Any) -> str:
    return f"- **{label}:** {value}"


def render_model(facts: ModelFacts) -> list[str]:
    out = [f"## Model trial {facts.label} — `{facts.job}`", ""]
    out.append(bullet("Trial dir", f"`{portable_path(facts.trial)}`" if facts.trial else MISSING))
    if facts.notes:
        out.append(bullet("Notes", "; ".join(facts.notes)))
    if facts.trial is None:
        return [*out, ""]
    out += [
        bullet("Model", facts.model_name or MISSING),
        bullet("Reward", f"{facts.reward_text} (reward.txt={facts.reward_file!r}, result.json={facts.reward_result!r})"),
        bullet("Harbor exception", facts.exception or "none"),
        bullet("CTRF", f"{facts.ctrf_summary}; " + (", ".join(f"`{n}`={s}" for n, s in facts.ctrf_cases) or "no cases")),
        bullet("Verifier duration", fmt_seconds(facts.verifier_seconds)),
        bullet("Agent execution duration", fmt_seconds(facts.agent_seconds)),
        bullet("ATIF segments", "; ".join(facts.segments) or MISSING),
        bullet("ATIF steps", f"{facts.steps_total} total ({', '.join(f'{k}={v}' for k, v in sorted(facts.steps_by_source.items())) or 'none'}), "
               f"{facts.steps_copied} copied-context"),
        bullet("Commands executed", f"{len(facts.commands)} (mark_task_complete calls: {facts.task_complete_calls})"),
        bullet("Tokens", f"in={fmt_num(facts.tokens_in)} out={fmt_num(facts.tokens_out)} cached={fmt_num(facts.tokens_cached)} "
               f"cost_usd={fmt_num(facts.cost_usd)} (source: {facts.tokens_source})"),
        bullet("Time to first command", fmt_seconds(facts.first_command_seconds) + (f" — {facts.first_command_note}" if facts.first_command_note else "")),
        bullet("Ran /app/tools/build/run_sim", f"{'yes' if facts.ran_run_sim else 'no'} ({facts.ran_run_sim} command(s))"),
        bullet("Touched /app/submission", f"{facts.submission_mentions} command(s) mention it, {facts.submission_writes} look like writes"),
        bullet("Build invocations (cmake/make/compiler)", str(facts.build_commands)),
        bullet("Submission at end (collected artifacts)", facts.submission_state
               + (f"; top-level: {', '.join(facts.submission_files)}" if facts.submission_files else "")),
        bullet("Artifacts manifest", "; ".join(facts.artifacts_summary) or MISSING),
        bullet("Recording adapter", facts.recording),
        bullet("recording.cast", facts.cast),
        bullet("Raw terminal observations", facts.terminal_outputs),
        bullet("Raw API log (api-calls.jsonl)", facts.api_calls
               + (f"; effort in requests: {', '.join(f'{k}={v}' for k, v in sorted(facts.api_efforts.items()))}" if facts.api_efforts else "")),
        bullet("Truncated observations in ATIF", str(facts.truncated_observations)),
        bullet("Capture fidelity", "PASS" if not facts.fidelity_problems else "FAIL — not difficulty evidence; replace it with the next fidelity-complete trial (compose_step3c.py): " + "; ".join(facts.fidelity_problems)),
        bullet("Context compaction / summarization", "; ".join(facts.compaction) if facts.compaction else "none detected"),
        bullet("trial.log", facts.trial_log_status + (f"; {len(facts.trial_log_errors)} error-like line(s)" if facts.trial_log_errors else "; no error-like lines")),
    ]
    for line in facts.trial_log_errors[:15]:
        out.append(f"    - `{line}`")
    if len(facts.trial_log_errors) > 15:
        out.append(f"    - ... {len(facts.trial_log_errors) - 15} more")
    out.append(bullet("Reward-hack signals (for human review)", "none detected" if not facts.hack_signals else ""))
    out += [f"    - {signal}" for signal in facts.hack_signals]
    out.append(bullet("Refusal signals", "none detected" if not facts.refusal_signals else ""))
    out += [f"    - {signal}" for signal in facts.refusal_signals]
    out += ["", f"**Final agent message** ({facts.final_step}):", ""]
    final = facts.final_message
    if len(final) > FINAL_MESSAGE_WIDTH:
        final = final[:FINAL_MESSAGE_WIDTH] + f"\n… [{len(facts.final_message) - FINAL_MESSAGE_WIDTH} more chars]"
    out += ["```text", *final.splitlines(), "```", ""]
    out += [f"**Command timeline** (first {FIRST_COMMANDS} / last {LAST_COMMANDS}, {COMMAND_WIDTH}-char truncation):", "", "```text",
            *command_timeline(facts.commands), "```", ""]
    return out


def render_control(facts: ControlFacts) -> list[str]:
    out = [f"## Control `{facts.job}` ({facts.kind})", ""]
    out.append(bullet("Trial dir", f"`{portable_path(facts.trial)}`" if facts.trial else MISSING))
    if facts.notes:
        out.append(bullet("Notes", "; ".join(facts.notes)))
    if facts.trial is None:
        return [*out, ""]
    expected = "1.0 with every case passed" if facts.kind == "oracle" else "0.0 with every case failed"
    out += [
        bullet("Reward", f"{facts.reward_text} (reward.txt={facts.reward_file!r}, result.json={facts.reward_result!r}); expected {expected}"),
        bullet("Harbor exception", facts.exception or "none"),
        bullet("CTRF", f"{facts.ctrf_summary}; " + (", ".join(f"`{n}`={s}" for n, s in facts.ctrf_cases) or "no cases")),
        bullet("Verifier duration", fmt_seconds(facts.verifier_seconds)),
        bullet("Agent execution duration", fmt_seconds(facts.agent_seconds)),
        bullet("Execution trace", facts.trace_status + (": " + ", ".join(f"{k}={v}" for k, v in facts.trace_events.items()) if facts.trace_events else "")),
        bullet("Trace return codes", ", ".join(str(c) for c in facts.trace_return_codes) or "none"),
        bullet("trial.log", facts.trial_log_status + (f"; {len(facts.trial_log_errors)} error-like line(s)" if facts.trial_log_errors else "; no error-like lines")),
    ]
    out += [f"    - `{line}`" for line in facts.trial_log_errors[:10]]
    if facts.kind == "oracle":
        out.append(bullet("oracle.txt", facts.oracle_txt))
        out += [f"    - `{line}`" for line in facts.oracle_tail]
    if facts.trace_commands:
        out += ["", "```text", *(f"{i:4d}. {c}" for i, c in enumerate(facts.trace_commands, start=1)), "```"]
    return [*out, ""]


def control_status(facts: ControlFacts) -> str:
    if facts.trial is None or facts.reward is None or facts.exception:
        return "INFRA? (missing evidence or exception)"
    want_reward = 1.0 if facts.kind == "oracle" else 0.0
    want_status = "passed" if facts.kind == "oracle" else "failed"
    if not facts.ctrf_cases:
        return "INFRA? (no CTRF cases)"
    if facts.reward == want_reward and all(s == want_status for _, s in facts.ctrf_cases):
        return "matches expectation"
    return "MISMATCH — trace the cause"


def render(jobs: Path, task_dir: Path, models: list[ModelFacts], controls: list[ControlFacts]) -> str:
    slug = task_dir.name
    lines = [f"# Step 3c audit dossier — `{slug}`", ""]
    lines.append(bullet("Jobs directory", f"`{portable_path(jobs)}`"))
    lines.append(bullet("Task directory", f"`{portable_path(task_dir)}`"))
    try:
        digest = task_digest(task_dir)
    except (WorkflowError, OSError) as exc:
        digest = f"ERROR: {exc}"
    lines.append(bullet("Current task digest", f"`{digest}`"))
    recorded, error = read_text(jobs / "task-digest.txt")
    recorded_text = error or recorded.strip()
    verdict = "" if error else (" (matches)" if recorded.strip() == digest else " (**DIFFERS from current task source**)")
    lines.append(bullet("Recorded task-digest.txt", f"`{recorded_text}`{verdict}"))
    try:
        manifest = load_test_manifest(task_dir)
        declared = [f"`{t['id']}` -> `{t['cases'][0]}`" for t in manifest["tests"]]
        lines.append(bullet("Declared tests", "; ".join(declared)))
    except (WorkflowError, OSError) as exc:
        lines.append(bullet("Declared tests", f"ERROR: {exc}"))
    lines.append(bullet("Generated", datetime.now().astimezone().isoformat(timespec="seconds")))
    lines.append("")
    lines += ["This dossier is a reading aid: rewards and signals below are not classifications. "
              "Assign VALID_PASS / VALID_FAIL / FALSE_FAIL_SPEC_GAP / INVALID_PASS_REWARD_HACK / INFRA_FAILURE "
              "only after reading the full trajectory (prompts/step3c.md section 3), and record each trial against the "
              "eight trial-analysis criteria of Master #107 (upstream rubrics/trial-analysis.toml): "
              "specification_completeness, solution_discoverability, verifier_correctness, boundary_fairness, "
              "policy_refusal, execution_blocked, unearned_credit, meaningful_difficulty.", ""]

    # Summary table.
    lines += ["## Summary", "",
              "| Label | Job | Reward | Exception | CTRF | Steps | Cmds | run_sim | /app/submission writes | Builds | Submission at end | Compaction | Hack signals | Refusal signals | Verifier | Fidelity |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for f in models:
        if f.trial is None:
            lines.append(f"| {f.label} | `{f.job}` | {MISSING} | — | {MISSING} | — | — | — | — | — | — | — | — | — | — | — |")
            continue
        lines.append("| " + " | ".join([
            f.label, f"`{f.job}`", f.reward_text, cell(f.exception or "none"), cell(f.ctrf_text),
            str(f.steps_total), str(len(f.commands)), str(f.ran_run_sim), str(f.submission_writes), str(f.build_commands),
            cell(f.submission_state.split(":")[0]), str(len(f.compaction)), str(len(f.hack_signals)),
            str(len(f.refusal_signals)), fmt_seconds(f.verifier_seconds),
            "PASS" if not f.fidelity_problems else f"FAIL ({len(f.fidelity_problems)})"]) + " |")
    lines += ["", "| Control | Kind | Reward | Exception | CTRF | Trace events | oracle.txt | Status |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for f in controls:
        lines.append("| " + " | ".join([
            f"`{f.job}`", f.kind, f.reward_text if f.trial else MISSING, cell(f.exception or "none") if f.trial else "—",
            cell(f.ctrf_text if f.trial else MISSING), f.trace_status,
            (f.oracle_txt if f.kind == "oracle" else "n/a"), control_status(f)]) + " |")

    attempts = [f for f in models if _PER_TRIAL_MODEL.search(f.job)]
    launched = [f for f in attempts if f.trial is not None]
    measured = [f for f in launched if f.reward is not None]
    passes = [f for f in measured if f.reward == 1.0]
    lines += ["", "## Raw pass@1 (model attempts only; controls excluded)", ""]
    lines.append(bullet("Attempts expected", str(EXPECTED_MODEL_ATTEMPTS)))
    lines.append(bullet("Attempts launched", f"{len(launched)} ({', '.join(f.label for f in launched) or 'none'})"))
    lines.append(bullet("Attempts with a parsable reward", f"{len(measured)}; missing reward: "
                        f"{', '.join(f.label for f in launched if f.reward is None) or 'none'}"))
    lines.append(bullet("reward == 1", f"{len(passes)} ({', '.join(f.label for f in passes) or 'none'})"))
    lines.append(bullet("Raw pass@1", f"{len(passes)}/{EXPECTED_MODEL_ATTEMPTS} = {len(passes) / EXPECTED_MODEL_ATTEMPTS:.0%}"
                        + (" — ROUND INCOMPLETE: fewer than five launched attempts; do not treat unlaunched attempts as failures"
                           if len(launched) < EXPECTED_MODEL_ATTEMPTS else "")
                        + (f"; {len(launched) - len(measured)} launched attempt(s) lack a reward and are listed, not counted as 0"
                           if len(launched) > len(measured) else "")))
    lines.append(bullet("Defensible pass rate", "assign after classification: VALID_PASS / (VALID_PASS + VALID_FAIL)"))
    void = [f for f in launched if f.fidelity_problems]
    lines.append(bullet("Capture fidelity (reasoning_effort=xhigh, uncapped, raw API log, recording)",
                        "PASS for every launched attempt" if not void else
                        f"FAIL for {', '.join(f.label for f in void)} — a trial at default effort or with truncated "
                        "observations is not difficulty evidence; the round cannot ship as it stands — run more attempts at this digest "
                        "and compose the first five fidelity-complete trials in launch order (scripts/compose_step3c.py, Master #94 item 1)"))
    lines.append("")
    for f in models:
        lines += render_model(f)
    for f in controls:
        lines += render_control(f)
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------- entry point

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--jobs-dir", type=Path, required=True, help="Harbor jobs directory from run_step3c_eval.sh")
    parser.add_argument("--task-dir", type=Path, required=True, help="tasks/<slug>")
    parser.add_argument("--out", type=Path, default=None, help="markdown output path (default: <jobs-dir>/audit-dossier.md)")
    parser.add_argument("--quiet", action="store_true", help="write the dossier without echoing it to stdout")
    args = parser.parse_args(argv)
    jobs, task_dir = args.jobs_dir.resolve(), args.task_dir.resolve()
    if not jobs.is_dir():
        parser.error(f"jobs directory not found: {args.jobs_dir}")
    if not task_dir.is_dir():
        parser.error(f"task directory not found: {args.task_dir}")
    out = (args.out or jobs / "audit-dossier.md").resolve()
    if out.is_relative_to(task_dir):
        parser.error(f"dossier must be written outside the task directory: {out}")

    models, controls = discover(jobs, task_dir.name)
    dossier = render(jobs, task_dir, models, controls)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(dossier, encoding="utf-8")
        written = f"audit_step3c.py: wrote {out}"
    except OSError as exc:
        written = f"audit_step3c.py: could not write {out}: {exc}"
    if not args.quiet:
        sys.stdout.write(dossier)
    print(written, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
