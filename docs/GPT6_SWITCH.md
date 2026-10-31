# Switching the trial model to GPT-6 (do this only when the client confirms)

The engine scripts were written for GPT-5.6 at `reasoning_effort = xhigh` and hard-code that
in several places (launcher defaults, job names `<slug>-gpt56-tN`, archive and compose checks,
the auditor's trial-evidence screen). They were left unchanged on purpose: the exact GPT-6 model
id, its reasoning setting and the harness are not known yet, and guessing them would break the
evidence checks (#89, #91).

When the client confirms:

1. Fill `config/round.toml` `[trials]` with the exact model id, reasoning setting and harness.
2. Change every line listed below to the confirmed values (model string, effort, and the
   `gpt56` job tag). Keep the edit mechanical: one value, everywhere.
3. Run `python3 scripts/tbsci.py selftest`, `python3 scripts/doctor.py --strict-tools` and one
   `CONTROLS_ONLY=1 scripts/run_step3c_eval.sh` on a parked task to prove the chain still works.
4. Set `status = "CONFIRMED"` in `config/round.toml`.

Inventory generated on 2026-10-30 with
`grep -nE 'gpt-?5\.6|gpt56|xhigh' scripts/* tools/final-tbsci-audit-master/scripts/*`:

```
scripts/archive_step3c.py:29:REQUIRED_REASONING_EFFORT = "xhigh"
scripts/archive_step3c.py:36:_PER_TRIAL_MODEL = re.compile(r"(?:^|-)gpt56-t([1-5])$")
scripts/archive_step3c.py:37:_BATCH_MODEL = re.compile(r"^gpt56-k([1-9][0-9]*)$")
scripts/archive_step3c.py:57:    """Discover model jobs: ``gpt56-kN``, legacy ``gpt56-k5``, or per-attempt ``*-gpt56-tN``."""
scripts/archive_step3c.py:66:        elif name == "gpt56-k5":
scripts/archive_step3c.py:73:            found[f"gpt56-t{i}"] = (1, "model")
scripts/archive_step3c.py:159:    if "gpt56-k5" not in job_plan and not any(_BATCH_MODEL.fullmatch(n) for n in job_plan):
scripts/audit_step3c.py:6:script reads each ``<slug>-gpt56-tN`` trial (result.json, CTRF, legacy upstream Terminus-2 ATIF
scripts/audit_step3c.py:42:_PER_TRIAL_MODEL = re.compile(r"(?:^|-)gpt56-t([1-5])$")
scripts/audit_step3c.py:43:_BATCH_MODEL = re.compile(r"^gpt56-k([1-9][0-9]*)$")
scripts/audit_step3c.py:47:REQUIRED_REASONING_EFFORT = "xhigh"
scripts/audit_step3c.py:650:        elif _BATCH_MODEL.fullmatch(child.name) or child.name == "gpt56-k5":
scripts/audit_step3c.py:656:            models.append(ModelFacts(job=f"{slug}-gpt56-{label}", kind="model", label=label, trial=None,
scripts/audit_step3c.py:876:    lines.append(bullet("Capture fidelity (reasoning_effort=xhigh, uncapped, raw API log, recording)",
scripts/check_trajectory.py:4:  python3 scripts/check_trajectory.py evidence-<task>            # every *-gpt56-tN / gpt56-kN job
scripts/check_trajectory.py:29:_MODEL_JOB = re.compile(r"(?:^|-)gpt56-(?:t[1-9]|k[1-9][0-9]*)$")
scripts/check_trajectory.py:30:DEFAULT_EFFORT = "xhigh"
scripts/compose_step3c.py:47:Output: ``<slug>-gpt56-t1..t5`` in launch order (whole job directories copied; the job
scripts/compose_step3c.py:77:EFFORT = "xhigh"
scripts/compose_step3c.py:91:    return re.compile(rf"^{re.escape(slug)}-gpt56-t([1-9][0-9]*)$")
scripts/compose_step3c.py:311:    other = [d.name for d in rnd["path"].iterdir() if d.is_dir() and re.search(r"gpt56-k\d+$", d.name)]
scripts/compose_step3c.py:544:            new = f"{slug}-gpt56-t{c['slot']}"
scripts/compose_step3c.py:624:                "composed_job": f"{slug}-gpt56-t{c['slot']}" if c["status"] == "selected" else None,
scripts/compose_step3c.py:691:                        help="a Step 3c round holding <slug>-gpt56-tN jobs (repeat for each round)")
scripts/package_task.py:80:# docs/DELIVERY_CHECKLIST.md: five GPT-5.6 xhigh trials, three Oracle and two NOP
scripts/package_task.py:444:    # Harbor records the provider-qualified form `openai/@openai/gpt-5.6`. Master #77
scripts/package_task.py:445:    # strips through the last "/" and a leading "@", so SUMMARY names `gpt-5.6`.
scripts/package_task.py:458:            f"{trial}: config.json has no reasoning_effort key; xhigh capture metadata "
scripts/package_task.py:460:    bad = [item for item in efforts if item != "xhigh"]
scripts/package_task.py:462:        raise WorkflowError(f"{trial}: config.json reasoning_effort is {bad!r}, must be 'xhigh'")
scripts/package_task.py:510:# workspace round and trial tags (``evidence-<task>-b/<task>-gpt56-t1``), which are process
scripts/package_task.py:834:    """Order model jobs by their trailing trial number: `<slug>-gpt56-t1` first.
scripts/patch_stb_harbor.py:117:    kwargs = {"max_output_bytes": 0, "reasoning_effort": "xhigh", "store_all_messages": True}
scripts/recording.py:49:        # archive_step3c.py voids a round whose recording_config.json is not xhigh.
scripts/stb_key_guard.py:48:PROBE_MODEL = os.environ.get("STB_KEY_PROBE_MODEL", "@openai/gpt-5.6")
scripts/verify_package.py:56:MODEL = "@openai/gpt-5.6"
scripts/verify_package.py:57:EFFORT = "xhigh"
scripts/verify_package.py:229:    ``@openai/gpt-5.6`` and ``openai/@openai/gpt-5.6`` both become ``gpt-5.6``.
scripts/run_step3c_eval.sh:2:# Step 3c launcher: five GPT-5.6 attempts at reasoning_effort=xhigh with full-fidelity
scripts/run_step3c_eval.sh:7:#   model @openai/gpt-5.6, reasoning_effort xhigh, no truncated observation, every
scripts/run_step3c_eval.sh:12:# whose recorded effort is not xhigh.
scripts/run_step3c_eval.sh:50:MODEL="${MODEL:-@openai/gpt-5.6}"
scripts/run_step3c_eval.sh:51:EFFORT="${EFFORT:-xhigh}"
scripts/run_step3c_eval.sh:138:model $MODEL, reasoning_effort $EFFORT, k=5 (one Harbor job per attempt: ${SLUG}-gpt56-t1..t5), agent scripts.harbor_re
scripts/run_step3c_eval.sh:166:  refresh_keys "${SLUG}-gpt56-t${i}" || {
scripts/run_step3c_eval.sh:167:    echo "ABORT: no usable stb key before ${SLUG}-gpt56-t${i} (invalid/expired, budget exhausted with no refresh allowe
scripts/run_step3c_eval.sh:170:  patch_guard "${SLUG}-gpt56-t${i}" || {
scripts/run_step3c_eval.sh:171:    echo "ABORT: stb-bundled harbor lost its full-fidelity patch before ${SLUG}-gpt56-t${i}; the attempt would run capp
scripts/run_step3c_eval.sh:174:  run_logged "stb harbor" "${SLUG}-gpt56-t${i}" -p "$TASK" -a scripts.harbor_recording:RecordingTerminus2 \
scripts/run_step3c_eval.sh:179:  patch_guard "after ${SLUG}-gpt56-t5" || {
tools/final-tbsci-audit-master/scripts/audit_run.py:224:            "round": {"model": "gpt-5.6", "effort": "xhigh" if efforts else None, "attempts": 
tools/final-tbsci-audit-master/scripts/tbsci_static_screen.py:206:T3_EFFORT_VALUE = "xhigh"
tools/final-tbsci-audit-master/scripts/tbsci_static_screen.py:1039:                  "Remove the key entirely. Difficulty is measured (k=5, GPT-5.6 @ 
tools/final-tbsci-audit-master/scripts/tbsci_static_screen.py:1788:              'Two lines: `<task-slug> sha=<hash> model=gpt-5.6 (reasoning_effort=x
tools/final-tbsci-audit-master/scripts/tbsci_static_screen.py:1800:    m = re.match(r'^(\S+)\s+sha=([0-9a-fA-F]{8,})\s+model=gpt-5\.6\s+\(reasoning_ef
tools/final-tbsci-audit-master/scripts/tbsci_static_screen.py:1804:              "Line 1 is `<task-slug> sha=<hash> model=gpt-5.6 (reasoning_effort=xh
tools/final-tbsci-audit-master/scripts/tbsci_static_screen.py:1853:              f"Package a complete {T3_AGENT_ROUND}-attempt GPT-5.6 xhigh round as 
tools/final-tbsci-audit-master/scripts/tbsci_static_screen.py:1945:    """`reasoning_effort` and its value `xhigh` are REQUIRED capture metadata in
tools/final-tbsci-audit-master/scripts/tbsci_static_screen.py:3587:                           "package evidence (rubric.txt, a complete five-attempt G
tools/final-tbsci-audit-master/scripts/trial_evidence.py:26:    xhigh (confirmed on EVERY run, Master #91), five complete attempts, failures
tools/final-tbsci-audit-master/scripts/trial_evidence.py:338:                    help="terminus (default, MASTER_CHECKLIST_TBSCI.md): required round =
tools/final-tbsci-audit-master/scripts/trial_evidence.py:461:            # the required round: GPT-5.6 at xhigh, five complete attempts
tools/final-tbsci-audit-master/scripts/trial_evidence.py:464:            report["required_round"] = {"model": "gpt-5.6", "effort": "xhigh", "need": T3
tools/final-tbsci-audit-master/scripts/trial_evidence.py:471:            # Master #91: reasoning_effort=xhigh confirmed on EVERY run individually
tools/final-tbsci-audit-master/scripts/trial_evidence.py:472:            no_xhigh = [t["trial"] for v in round_arms.values() for t in v["trials"] if n
tools/final-tbsci-audit-master/scripts/trial_evidence.py:473:            if round_arms and no_xhigh:
tools/final-tbsci-audit-master/scripts/trial_evidence.py:474:                report["flags"].append(f"{len(no_xhigh)} GPT-5.6 run(s) record no xhigh r
tools/final-tbsci-audit-master/scripts/trial_evidence.py:475:                                       "— confirm reasoning_effort=xhigh on every run i
tools/final-tbsci-audit-master/scripts/trial_evidence.py:478:                                       f"{T3_AGENT_ROUND}-attempt GPT-5.6 xhigh round")
tools/final-tbsci-audit-master/scripts/trial_evidence.py:483:                report["flags"].append("GPT-5.6 round present but no xhigh reasoning effo
tools/final-tbsci-audit-master/scripts/trial_evidence.py:486:            report["flags"].append(f"only {len(agent_arms)} agent arm(s) — the maintain
tools/final-tbsci-audit-master/scripts/trial_evidence.py:496:                               + (f" (the required evidence is a complete {T3_AGENT_ROUND
tools/final-tbsci-audit-master/scripts/trial_evidence.py:498:                                  " (run `harbor run -p <task> -a claude-code -m anthropi
```
