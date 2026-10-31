# Threat model — <task-name>

Source of truth: `MASTER_CHECKLIST_TBSCI.md` (Master #20, #24, #44, #45,
#54–#56, #58, #60, #64, #93, #99, #100, #102). For each class, name the countermeasure and verifier
location, or write `n/a` with a contract-based reason. Every class Master #60
names must be rejected by its own named assertion.

| Class | Applicable? | Countermeasure/location | Named assertion | Control/evidence |
|---|---:|---|---|---|
| Reward/test/CTRF modification (incl. detached writer) (#60) | | | | NC-06/NC-06b |
| Format-only/default output (#59, #60) | | | | NC-02 |
| Public/example hard-code (#46, #60) | | | | NC-03/NC-14 |
| Self-reported metric (#44, #60) | | | | NC-04 |
| Missing artifact (#60) | | | | NC-05 |
| Single-axis partial | | | | NC-08 |
| Unpersisted state | | | | NC-09 |
| Boundary/order/scale shortcut | | | | NC-10/NC-13 |
| Protected-input tampering (#45) | | | | NC-11 |
| Wrapper/module/PATH/preload (#54) | | | | NC-12 |
| Agent code executed by the verifier reads `/tests` or writes `/logs/verifier` (#54, Appendix A: `setpriv --reuid=12000 --regid=12000 --clear-groups --no-new-privs env -i … timeout -k 5 <PER_RUN_LIMIT>`, `chmod -R go-rwx /tests`, root-owned `/work` and `/logs/verifier`) | | | | static (auditor) + Appendix A SELF-TEST |
| Agent-planted symlink in an artifact path to a `/tests` file, or expected value read from an artifact/`/app` (#55) | | | | static (auditor `T3-SYMLINK`) + live plant |
| Detached process rewrites `reward.txt` after grading (#56: kill-to-exhaustion, `rm -f` reward, then write) | | | | static (auditor `T3-REWARD-LAST`) + live background writer |
| Background reward access | | | | NC-06b/NC-12 |
| Verifier-time fetch poisoning (#38) | | | | static |
| Submission phones out or reaches a hosted answer key from the verifier (#64: `[verifier.environment].network_mode = "no-network"`) | | | | static (auditor) |
| Answer reachable online — published result, posted solution, dataset with known labels — with the agent on open internet (#99) | | | | review (searches tried) |
| Answer recalled from memory: a well-known published value or benchmark dataset (#99) | | | | review |
| Science-free null reaches a graded instance — constant, range mean/median, domain centre, majority class, copy-through (#102) | | | | null runs in traceability.md |
| Build-time data fetch drifts or is swapped (#100: literal immutable revision + checksum in the build) | | | | static + review |
| Cache/precomputation manipulation | | | | NC-13 |
| Answer leakage: byte-identical env/tests file, comments, lore/notes files, layers (#13–#15, #19, #20) | | | | review |
| `/solution`/hidden-test access (#24) | | | | review |
| Empty/disabled alternate state | | | | NC-10/NC-11 |
| Oracle/agent identity branching (#58) | | | | static + review |

## Public-solution risk

## Refusal risk

## Residual risk
