"""Harbor 0.22 / 0.23 recording adapters; import with Harbor's own Python environment.

Use -a scripts.harbor_recording:RecordingTerminus2 (or RecordingOracle / RecordingNop).
``RecordingTerminus2`` and ``harbor.agents.terminus_2`` are legacy upstream
Harbor compatibility identifiers; keep their spelling unchanged.
Native agent behavior is inherited; no installed Harbor files are modified.
"""

from __future__ import annotations

import json
from pathlib import Path

from harbor.agents.nop import NopAgent
from harbor.agents.oracle import OracleAgent
from harbor.agents.terminus_2 import Terminus2
from harbor.models.trial.paths import TrialPaths

from scripts.recording import ExecutionRecordingMixin, OutputRecordingMixin


class RecordingTerminus2(OutputRecordingMixin, Terminus2):
    """Legacy upstream Harbor agent with recording and an output byte cap."""


# Harbor 0.23 (stb 2.4.16) validates --ak against the agent's options_model with
# extra="forbid" before the task is resolved, so our own max_output_bytes option must
# be declared or the run dies with "Unknown option 'max_output_bytes'". reasoning_effort,
# store_all_messages and record_terminal_session are already Terminus2Options fields.
try:
    from harbor.agents.terminus_2.terminus_2 import Terminus2Options
    from pydantic import Field
except ImportError:  # older Harbor without an options model
    Terminus2Options = None

if Terminus2Options is not None:
    class RecordingTerminus2Options(Terminus2Options):
        max_output_bytes: int = Field(default=0, ge=0)

    RecordingTerminus2.options_model = RecordingTerminus2Options


def _recover_oracle_paths(logs_dir: Path) -> tuple[Path, TrialPaths]:
    """Harbor only injects task_dir/trial_paths when agent.name == 'oracle'.

    Custom import-path agents still receive logs_dir=<trial>/agent, so recover
    the missing Oracle kwargs from the trial layout and lock/config.
    """
    trial_dir = Path(logs_dir).resolve().parent
    trial_paths = TrialPaths(trial_dir=trial_dir)
    task_dir = None
    for name in ("config.json", "lock.json"):
        path = trial_dir / name
        if not path.is_file():
            continue
        data = json.loads(path.read_text())
        task = data.get("task") or {}
        candidate = task.get("path")
        if candidate:
            task_dir = Path(candidate)
            break
    if task_dir is None:
        raise TypeError(
            "RecordingOracle requires task_dir/trial_paths; Harbor did not inject "
            f"them and they could not be recovered from {trial_dir}"
        )
    return task_dir, trial_paths


class RecordingOracle(ExecutionRecordingMixin, OracleAgent):
    """Native Oracle with a command/observation execution trace."""

    def __init__(self, logs_dir, task_dir=None, trial_paths=None, **kwargs):
        if task_dir is None or trial_paths is None:
            recovered_task_dir, recovered_trial_paths = _recover_oracle_paths(logs_dir)
            task_dir = task_dir or recovered_task_dir
            trial_paths = trial_paths or recovered_trial_paths
        super().__init__(
            logs_dir=logs_dir, task_dir=task_dir, trial_paths=trial_paths, **kwargs
        )


class RecordingNop(ExecutionRecordingMixin, NopAgent):
    """Native NOP with an explicit start/end trace and no invented actions."""
