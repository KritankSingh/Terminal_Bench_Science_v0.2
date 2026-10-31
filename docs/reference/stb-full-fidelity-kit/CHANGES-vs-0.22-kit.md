# What changed from the original kit

The original kit targets Harbor 0.22.0. `stb` force-upgrades past it: 2.4.15
refuses to run at all ("Version 2.4.15 is outdated ... Please upgrade before
continuing"), and 2.4.16 bundles Harbor **0.23.0**. This kit supports both.

## 1. `patch_stb_harbor.py` — same patches, a much stronger guard

The three patches are unchanged in substance, and their anchors still match:
`llms/lite_llm.py` is byte-identical between 0.22.0 and 0.23.0. What changed is
the verification.

The old `--check` tested **behaviour only**. That is a false-PASS waiting to
happen: with stale `__pycache__` over an unpatched source, or a `PYTHONPATH`
shadowing the bundled tree, it prints `ok True True` while the 10,000-byte
observation cap is live and no raw API log is written. This was reproduced
deliberately, not theorised.

`--check` now runs six independent checks and prints PASS/FAIL for each:

1. exactly one harbor tree;
2. harbor imported *from that tree* (kills PYTHONPATH shadowing);
3. harbor version in the supported set;
4. patch markers present in the **on-disk sources**;
5. markers *and* behaviour in the **imported modules** (kills stale bytecode);
6. a `.full-fidelity-patch.json` stamp whose revision, version and SHA-256
   digests still match the live files.

`apply` refuses an unsupported Harbor version rather than patching blindly
(`--force-version` exists for porting). `--check-agent` validates a full
`--ak` set through Harbor's own `preflight()`.

## 2. `run_k.sh` — the guard runs before every attempt, not once

The inline probe was the old behaviour-only test. It now calls
`patch_stb_harbor.py --check`. Run it before **every** attempt: any
`uv tool install snorkelai-stb ... --reinstall` silently reverts the patch,
including the one `stb` itself prints when it blocks on an outdated version.
A reinstall during a round otherwise yields capped, unusable trials that only
surface at archive time -- after the money is spent.

## 3. `check_trajectory.py` — capture defects fail the round immediately

Trial layout is unchanged in 0.23. Added: `agent/recording_config.json` is
checked for `max_output_bytes == 0`, `reasoning_effort == "xhigh"` and a raw
API log path, reported as new `cfg_effort=` / `cfg_cap=` columns. Previously a
capture defect surfaced only at archive time.

## 4. If you use a custom recording adapter, read this

Harbor 0.23 added strict agent-kwarg validation (`harbor/agents/base.py`): each
agent class carries a Pydantic `options_model` with `extra="forbid"`, and
unknown `--ak` options are rejected *before* the agent is constructed. A
subclass that merely accepts `**kwargs` is not enough.

`Terminus2Options` in 0.23 already declares `reasoning_effort`,
`store_all_messages` and `record_terminal_session`. If your adapter adds an
option of its own, declare it:

```python
class MyAdapterOptions(Terminus2Options):
    max_output_bytes: int = Field(default=0, ge=0)

class MyAdapter(OutputRecordingMixin, Terminus2):
    options_model = MyAdapterOptions
```

Also note 0.23 moved agent kwargs onto `self.options`. Code reading
`self._reasoning_effort` now gets `None`, which silently writes
`"reasoning_effort": null` into `recording_config.json` -- and a round that
does not record `xhigh` is void. Read `self.options.reasoning_effort` with a
fallback for 0.22.
