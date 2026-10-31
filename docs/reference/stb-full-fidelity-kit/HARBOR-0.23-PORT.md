# Full-fidelity capture kit — Harbor 0.23 port (patch revision `r3`)

**Targets Harbor 0.22.0 (stb 2.4.15) and Harbor 0.23.0 (stb 2.4.16).** Ported 2026-09-24.
`README.md` in this directory is the kit as received and describes the 0.22-era setup; where
the two disagree, this file wins, and the workspace scripts — not the kit copies — are what
actually run:

| what runs | kit reference copy |
|---|---|
| `scripts/patch_stb_harbor.py` | `patch_stb_harbor.py` |
| `scripts/check_trajectory.py` | `check_trajectory.py` |
| `scripts/run_step3c_eval.sh`, `scripts/resume_step3c_eval.sh` | `run_k.sh` |
| `scripts/harbor_recording.py`, `scripts/recording.py` | (no kit equivalent) |

## What the patch does (unchanged in substance from 0.22)

| # | file | edit |
|---|---|---|
| 1 | `harbor/agents/terminus_2/terminus_2.py` | `_limit_output_length` takes `max_bytes: int \| None = None` and falls back to `TERMINUS_MAX_OUTPUT_BYTES` (default still 10000), so `TERMINUS_MAX_OUTPUT_BYTES=100000000` lifts the model-facing observation cap |
| 2a | `harbor/agents/terminus_2/terminus_2.py` | with `TERMINUS_RAW_API_LOG=1`, the agent sets `self._llm._raw_log_path = <trial>/agent/api-calls.jsonl` right after the LLM is built |
| 2b | `harbor/llms/lite_llm.py` | `LiteLLM._raw_api_log()` appends `{ts, request, response}` as JSONL on both the chat-completions and the Responses path; `api_key` and `extra_headers` are stripped |
| — | both files | `HARBOR_FULL_FIDELITY_PATCH = "r3"` marker at module level |

All five source anchors are byte-identical in 0.22.0 and 0.23.0, so one patch body covers both.

## Harbor 0.22 → 0.23 deltas that matter to this kit

1. **Strict agent-kwarg validation (breaking).** `harbor/agents/base.py` now validates `--ak`
   options against a per-agent Pydantic `options_model` with `extra="forbid"`, at
   `AgentFactory.run_preflight()` — *before* the task is even resolved, let alone a container
   started. `Terminus2Options` does not know `max_output_bytes` (our own option, consumed by
   `OutputRecordingMixin` and never forwarded to Harbor), so a 0.22-era adapter dies with:

   ```
   Invalid kwargs for agent 'terminus-2':
     Unknown option 'max_output_bytes'.
   ```

   `scripts/harbor_recording.py` now declares `RecordingTerminus2.options_model =
   RecordingTerminus2Options`, a `Terminus2Options` subclass that adds
   `max_output_bytes: int = 0` (`ge=0`). `reasoning_effort`, `store_all_messages` and
   `record_terminal_session` are **already** Harbor 0.23 options and are inherited, not
   redeclared — the kwarg set we pass needs exactly one addition. The extension is applied
   only when `Terminus2Options` imports, so the module still loads on 0.22, where the
   Oracle/NOP controls run (standalone `harbor` is still 0.22.0 in this workspace).

2. **`reasoning_effort` moved off the agent instance.** 0.22 kept `self._reasoning_effort`;
   0.23 parses every user kwarg onto `self.options`. `scripts/recording.py` wrote
   `recording_config.json` from the retired attribute, so under 0.23 it recorded
   `"reasoning_effort": null` — and `archive_step3c.py` / `audit_step3c.py` reject a round
   whose recording config does not say `xhigh`. That would have voided a fully paid round
   *after* capture. It now reads `self.options.reasoning_effort`, falling back to
   `self._reasoning_effort` (0.22) and then to the LLM's own copy.

3. **Trial output layout: unchanged.** `verifier/reward.txt`, `verifier/ctrf.json`,
   `agent/trajectory.json`, `agent/trajectory.cont-N.json`, `agent/recording.cast`,
   `agent/api-calls.jsonl`, `result.json → agent_result.metadata.all_messages` are all where
   0.22 put them. `check_trajectory.py` needed no path changes; it gained
   `recording_config.json` checks (see below).

4. **`stb` blocks on an outdated version** and prints
   `uv tool install snorkelai-stb --find-links … --reinstall --no-cache`. That command rewrites
   the whole site-packages tree and **silently reverts this patch** — see "How the patch gets
   lost" below.

## Verifying the patch — `--check` is the guard, not a formality

```bash
python3 scripts/patch_stb_harbor.py            # apply (idempotent), then self-check
python3 scripts/patch_stb_harbor.py --check    # verify only; exit 1 if anything is off
python3 scripts/patch_stb_harbor.py --check-agent   # the Step 3c --ak set, through Harbor's own preflight
```

`--check` prints one line per item and passes only if **all** hold:

1. exactly one stb-bundled Harbor tree exists;
2. the bundled interpreter imports Harbor **from that tree** (a `PYTHONPATH` entry pointing at
   another, patched, Harbor cannot fake a pass);
3. the imported Harbor version is one this patch revision was anchored against;
4. every marker is present in the **on-disk sources**;
5. the **imported modules** carry the marker and behave (50 000-byte observation survives,
   `LiteLLM._raw_api_log` exists) — this is the stale-`__pycache__` check;
6. the stamp file `<harbor>/.full-fidelity-patch.json` records this revision and this Harbor
   version, and its SHA-256 digests still match both files byte for byte.

Why so many: a behaviour-only probe (what the 0.22 kit used, and what `run_k.sh` still inlines)
**can print PASS on an unpatched source**. Restore an unpatched `terminus_2.py` padded to the
patched file's exact size and mtime and Python serves the stale patched `.pyc`; the old probe
prints `ok True True` while `grep -c TERMINUS_MAX_OUTPUT_BYTES` on the source returns 0. That is
reproduced in the port notes. Conversely, a grep-only check would miss a patched source that the
interpreter is not actually loading. Both directions are now required, plus the digest.

Hand check, when you want to see it yourself:

```bash
H=~/.local/share/uv/tools/snorkelai-stb/lib/python3.*/site-packages/harbor
grep -c TERMINUS_MAX_OUTPUT_BYTES $H/agents/terminus_2/terminus_2.py   # 1
grep -c TERMINUS_RAW_API_LOG      $H/agents/terminus_2/terminus_2.py   # 1
grep -c '_raw_api_log'            $H/llms/lite_llm.py                  # 3
grep -h HARBOR_FULL_FIDELITY_PATCH $H/agents/terminus_2/terminus_2.py $H/llms/lite_llm.py
```

Note `grep api-calls` on `lite_llm.py` returns 0 **even when patched** — the path is set by patch
2a in `terminus_2.py`, not in the LiteLLM helper. Use the markers above, not that string.

## How the patch gets lost (and why the guard is now per-trial)

The patch is a set of edits to files under `~/.local/share/uv/tools/snorkelai-stb/`. Anything that
reinstalls the tool — including the upgrade command `stb` itself prints when it blocks — replaces
those files with the pristine wheel contents. Nothing warns you. On 2026-09-24 the tree was
patched at 02:44 and reinstalled at 12:05 (`uv-receipt.toml` and every file in site-packages
restamped; `terminus_2.py` byte-identical to its own `.orig-2.4.16` backup), so a round started
after 12:05 on a preflight-only check would have burned five paid GPT-5.6 trials at a 10 000-byte
observation cap with no `api-calls.jsonl` — void under `prompts/step3c.md`.

`scripts/run_step3c_eval.sh` and `scripts/resume_step3c_eval.sh` therefore call `patch_guard`
**before every model attempt** and once after the last one, appending to `<OUT>/patch-guard.log`
(part of the round's records). A failure aborts the round rather than producing unusable trials.

## What `check_trajectory.py` now also checks

On top of reward/tests/steps/`all_messages`/truncation markers/`recording.cast`/`api-calls.jsonl`
and `reasoning_effort` in every logged request, it reads `agent/recording_config.json` and fails
the round when `max_output_bytes != 0`, `reasoning_effort != xhigh`, or `raw_api_log` is empty.
These are the same conditions `archive_step3c.py` enforces later; checking them at the end of the
round turns a post-hoc archive rejection into an immediate `fidelity FAIL`.

## After any stb change

```bash
python3 scripts/patch_stb_harbor.py          # re-apply; safe to run repeatedly
python3 scripts/patch_stb_harbor.py --check
python3 scripts/patch_stb_harbor.py --check-agent
```

If Harbor moves to a version not in `SUPPORTED_HARBOR`, both `--check` and `apply` fail loudly and
name the version. Re-port against the new sources (the five anchors are in the module docstring),
verify, then add the version — `--force-version` exists for porting work only, never for a paid
round.
