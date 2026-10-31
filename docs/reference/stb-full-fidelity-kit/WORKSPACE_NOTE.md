# STB full-fidelity kit — reference copy

`README.md`, `patch_stb_harbor.py`, `check_trajectory.py`, `run_k.sh`,
`CHANGES-vs-0.22-kit.md` and `HARBOR-0.23-PORT.md` are the 0.23 kit as received
(`STB_FULL_FIDELITY_KIT_0.23.zip`, installed 2026-09-24), kept unchanged for
provenance. `README.md` is the original 0.22-era text; where it disagrees with
`HARBOR-0.23-PORT.md`, the port notes win. The earlier kit
(`STB_FULL_FIDELITY_KIT.zip`) is in git history.

| Kit file | Workspace equivalent | What changed |
|---|---|---|
| `patch_stb_harbor.py` | `scripts/patch_stb_harbor.py` | identical (patch revision `r3`, Harbor 0.22.0 / 0.23.0, six-part `--check`, `--check-agent`) |
| `check_trajectory.py` | `scripts/check_trajectory.py` | identical (Step 3c `OUT` dir, per-request effort, `recording_config.json` checks) |
| `run_k.sh` | `scripts/run_step3c_eval.sh` | same settings folded into the launcher: one Harbor job per attempt through `scripts.harbor_recording:RecordingTerminus2`, `patch_guard` + key refresh before each attempt (`<OUT>/patch-guard.log`), `--check-agent` at preflight, Oracle x3 / NOP x2 controls, digest binding via `task_digest.py` |
| `README.md` | `prompts/step3c.md`, `commands.md` | policy text incorporated |
| — | `scripts/harbor_recording.py`, `scripts/recording.py` | `RecordingTerminus2Options` declares `max_output_bytes` for Harbor 0.23's strict `--ak` validation; `recording_config.json` reads `self.options.reasoning_effort` with 0.22 fallbacks |

Workspace deviations from `HARBOR-0.23-PORT.md`:

- There is no `scripts/resume_step3c_eval.sh`; the launcher refuses an existing
  `OUT`, so a dead round is never resumed.
- The kit README's "`fidelity FAIL` → the run is void" is narrowed here to the
  trial (MASTER_CHECKLIST_TBSCI.md #94 item 1): a round's `BAD` trials are never
  evidence, its `OK` trials still are. The five shipped runs are the first five
  fidelity-complete trials at the digest and run config in launch order across
  rounds, assembled by `scripts/compose_step3c.py` (controls from any same-config
  round or `CONTROLS_ONLY=1 scripts/run_step3c_eval.sh`). `check_trajectory.py`
  itself is unchanged and still decides fidelity per trial.
- The stb 2.4.15 install here bundled Harbor **0.21.0**, not 0.22.0, which r3
  refuses. Step 3c needs stb 2.4.16 (Harbor 0.23.0).
- `HARBOR-0.23-PORT.md` says standalone `harbor` stays 0.22.0. Here it was
  upgraded to 0.23.0 on 2026-09-24 (`uv tool install harbor==0.23.0`), so Oracle/NOP
  controls, the per-test matrix and `regrade_step3c.py` run on the same Harbor as
  Step 3c. Rounds sealed under 0.22.0 stay valid: Harbor's version is recorded
  as provenance, never compared, and 0.23 regrades a 0.22 job to the same reward.

`scripts/archive_step3c.py` and `scripts/audit_step3c.py` enforce and report the
kit's fidelity requirements on every archived model trial.
