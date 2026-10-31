# Running a task the way it will be judged: GPT-5.6 at `xhigh`, nothing truncated

Every k-run you submit as evidence must be produced this way. A run with the defaults of `stb`
(no reasoning effort set, terminal output cut at 10 000 bytes) is not evidence of difficulty:
the model is reasoning at default effort and never sees the file it just opened. Those runs are
void.

## One-time setup (5 minutes)

```bash
uv tool install snorkelai-stb --upgrade      # need 2.4.15 or newer; check: stb --version
stb login --env prod                          # interactive; do this in a real terminal
python3 patch_stb_harbor.py                   # from this kit; prints "ok True True" when done
```

`patch_stb_harbor.py` edits the harbor copy **bundled inside stb** (`~/.local/share/uv/tools/snorkelai-stb/...`)
so that (1) the 10 000-byte observation cap can be lifted and (2) every raw API request/response
is written to disk. It is idempotent and keeps backups. **Re-run it after every `stb` upgrade**
(`run_k.sh` refuses to start if the patch is missing).

## Every run

```bash
python3 stb_key_guard.py status               # never run `stb keys refresh` by hand: run_k.sh probes the key and refreshes only when its $10 budget is used up
bash run_k.sh /path/to/<task-dir> 5           # k=5 attempts, sequential-safe; OUT=/some/dir to choose where jobs land
```

What `run_k.sh` does, and what you must never change:

| setting | value | why |
|---|---|---|
| model | `@openai/gpt-5.6` | the reference solver |
| `--ak reasoning_effort=xhigh` | xhigh | default effort understates the model |
| `TERMINUS_MAX_OUTPUT_BYTES=100000000` | 100 MB | no observation is ever truncated |
| `--ak store_all_messages=true` | on | every prompt and reply lands in `result.json` |
| `TERMINUS_RAW_API_LOG=1` | on | `agent/api-calls.jsonl`: every request + raw response |
| asciinema recording | on (default) | `agent/recording.cast` |
| console log + `SOURCE.txt` | written | binds the run to the bundle sha, model, effort, k |

Do not run `stb harbor run` by hand with other flags, do not run through a wrapper's defaults,
do not "clean up" a trajectory before submitting.

## What a valid run looks like

`run_k.sh` ends by running `check_trajectory.py` on the job; the last line must read
`SUMMARY <job>: x/k solved; fidelity PASS`. It checks, per trial: reward and test counts,
`result.json` carries `all_messages`, `api-calls.jsonl` and `recording.cast` exist, and no
observation contains a truncation marker (`[... output limited to N bytes; M interior bytes omitted ...]`).
If it prints `fidelity FAIL`, the run is void: rename the job dir `_void-<name>`, fix the cause
(usually a missing patch or an expired key mid-run — the trial's `result.json` then holds an
`AuthenticationError`), and run again. Never quote numbers from a void run.

## What to submit

The whole job directory, untouched: `<slug>-k5-<stamp>/` with `SOURCE.txt`, every `<trial>/`
(`agent/trajectory.json`, `agent/api-calls.jsonl`, `agent/recording.cast`, `result.json`,
`verifier/`) plus the `.console.log` beside it. The bundle sha in `SOURCE.txt` must equal the sha
of the bundle you submit — if you edit anything in `instruction.md`, `tests/`, `environment/`,
`solution/` or `task.toml` after the run, the run no longer describes your bundle: run again.

## Reading the result honestly

- 5/5 at xhigh means the model already does this task; that is the band, whatever a default-effort
  run said before.
- A failure counts only if the trajectory shows the model saw everything it needed and still
  failed on a rule the instruction or docs state. A failure caused by a truncated observation, a
  key expiring mid-run, or a harness crash is not a failure of the task.
