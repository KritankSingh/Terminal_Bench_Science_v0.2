"""Dependency-free recording helpers for the local Harbor adapters."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class OutputRecordingMixin:
    """Retain full terminal observations and explicitly control the model-facing cap."""

    def __init__(self, *args, max_output_bytes=None, **kwargs):
        # Legacy upstream compatibility variable; do not rename without a migration.
        limit = int(os.environ.get("TERMINUS_MAX_OUTPUT_BYTES", "0")) if max_output_bytes is None else max_output_bytes
        if type(limit) is not int or limit < 0:
            raise ValueError("max_output_bytes must be a nonnegative integer; 0 means uncapped")
        self._recording_output_limit = limit
        self._recording_output_index = 0
        kwargs["store_all_messages"] = True
        kwargs["record_terminal_session"] = True
        super().__init__(*args, **kwargs)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        # Raw request/response capture needs the patched stb-bundled LiteLLM
        # (scripts/patch_stb_harbor.py). Point it at the trial when available so the
        # log does not depend on the TERMINUS_RAW_API_LOG hook alone; record None
        # otherwise so archive_step3c.py can flag the trial instead of guessing.
        llm = getattr(self, "_llm", None)
        raw_api_log = None
        if llm is not None and hasattr(type(llm), "_raw_api_log"):
            if not getattr(llm, "_raw_log_path", None):
                llm._raw_log_path = str(self.logs_dir / "api-calls.jsonl")
            raw_api_log = "api-calls.jsonl"
        (self.logs_dir / "recording_config.json").write_text(json.dumps({
            "adapter": type(self).__name__, "max_output_bytes": limit,
            "raw_terminal_output": "terminal-output/", "store_all_messages": True,
            "record_terminal_session": True,
            "reasoning_effort": self._recorded_reasoning_effort(),
            "raw_api_log": raw_api_log,
        }, indent=2) + "\n")

    def _recorded_reasoning_effort(self):
        # Harbor 0.23 parses agent kwargs onto self.options; 0.22 kept
        # self._reasoning_effort. Reading only the retired attribute records null, and
        # archive_step3c.py voids a round whose recording_config.json is not xhigh.
        options = getattr(self, "options", None)
        for value in (getattr(options, "reasoning_effort", None),
                      getattr(self, "_reasoning_effort", None),
                      getattr(getattr(self, "_llm", None), "_reasoning_effort", None)):
            if value is not None:
                return value
        return None

    def _limit_output_length(self, output: str, max_bytes: int = 10000) -> str:
        # Ignore the native helper's default. The explicit adapter setting wins.
        directory = self.logs_dir / "terminal-output"
        directory.mkdir(parents=True, exist_ok=True)
        self._recording_output_index += 1
        path = directory / f"{self._recording_output_index:06d}.txt"
        with path.open("x", encoding="utf-8", newline="") as handle:
            handle.write(output)
        if self._recording_output_limit == 0:
            return output
        return super()._limit_output_length(output, max_bytes=self._recording_output_limit)


class RecordingEnvironment:
    """Delegate real environment operations while recording executed commands."""

    def __init__(self, environment, emit):
        self._environment = environment
        self._emit = emit

    def __getattr__(self, name):
        return getattr(self._environment, name)

    async def exec(self, *args, **kwargs):
        self._emit("exec_start", command=kwargs.get("command", args[0] if args else None),
                   timeout_sec=kwargs.get("timeout_sec"), user=kwargs.get("user"),
                   cwd=kwargs.get("cwd"))
        try:
            result = await self._environment.exec(*args, **kwargs)
        except BaseException as exc:
            self._emit("exec_error", exception_type=type(exc).__name__, exception=str(exc))
            raise
        self._emit("exec_end", return_code=result.return_code,
                   stdout=result.stdout, stderr=result.stderr)
        return result


class ExecutionRecordingMixin:
    """Record actual Oracle/NOP execution; these events are not model ATIF."""

    async def run(self, instruction, environment, context):
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        trace = self.logs_dir / "execution_trace.jsonl"

        def emit(event, **values):
            with trace.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"schema_version": "1.0", "kind": "execution-trace",
                                         "agent": self.name(), "timestamp": timestamp(),
                                         "event": event, **values}, ensure_ascii=False) + "\n")

        emit("run_start", instruction=instruction,
             note="No model reasoning is generated by this baseline agent.")
        try:
            result = await super().run(instruction, RecordingEnvironment(environment, emit), context)
        except BaseException as exc:
            emit("run_error", exception_type=type(exc).__name__, exception=str(exc))
            raise
        emit("run_end", note="Read trial result and verifier CTRF for reward and test outcomes.")
        return result
