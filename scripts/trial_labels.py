#!/usr/bin/env python3
"""Label the five Step 3c trials and judge the band on legitimate outcomes only.

  python3 scripts/trial_labels.py authoring/<slug>/trials.md tasks/<slug>

Reads the first table (run | reward | label | evidence) of authoring/<slug>/trials.md.
Usually called through `python3 scripts/tbsci.py labels <slug>`.
Labels: legit-pass, hack-pass, legit-fail, false-fail.

  - a hack-pass (reward 1 without the science) or a false-fail (reward 0 for correct work, a
    spec gap, a verifier bug or an environment fault) is a TASK DEFECT: fix the task, re-run
    `tbsci.py check` and `tbsci.py review`; the round is void;
  - otherwise the band (config/round.toml [band]) is judged on the number of legit-passes.

Five trials are noisy: a 0/5 is consistent with a true pass rate up to ~43% (95% interval),
so the band verdict is a gate, not a measurement.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

LABELS = ("legit-pass", "hack-pass", "legit-fail", "false-fail")


def check_rows(rows: list[dict], task_dir: Path, round_cfg: dict) -> tuple[list[str], dict]:
    errors: list[str] = []
    counts = {label: 0 for label in LABELS}
    for row in rows:
        run = row.get("run", "").strip()
        label = row.get("label", "").strip().lower()
        reward = row.get("reward", "").strip()
        if label not in LABELS:
            errors.append(f"table:trials: {run} label {label!r} not in {LABELS}")
            continue
        counts[label] += 1
        if reward not in {"0", "1"}:
            errors.append(f"table:trials: {run} reward must be 0 or 1, got {reward!r}")
        elif label.endswith("pass") != (reward == "1"):
            errors.append(f"table:trials: {run} label {label} does not match reward {reward}")
        on_disk = task_dir / "trajectories" / run / "verifier" / "reward.txt"
        if on_disk.is_file():
            value = on_disk.read_text(encoding="utf-8").strip()
            try:
                value = str(int(float(value)))
            except ValueError:
                pass
            if value != reward:
                errors.append(f"table:trials: {run} reward {reward} disagrees with {on_disk.name} ({value})")
        if not row.get("evidence", "").strip():
            errors.append(f"table:trials: {run} has no evidence (trajectory step, failing test, instruction line)")
        if label == "hack-pass":
            errors.append(f"table:trials: {run} is a hack-pass -> TASK DEFECT (reward hacking); fix the task, the round is void")
        if label == "false-fail":
            errors.append(f"table:trials: {run} is a false-fail -> TASK DEFECT (correct work rejected); fix the task, the round is void")
    band = round_cfg.get("band", {})
    lo, hi = int(band.get("band_min", 0)), int(band.get("band_max", 3))
    k = counts["legit-pass"]
    summary = {"counts": counts, "legit_passes": k, "n": len(rows), "band": [lo, hi]}
    if not any(e for e in errors if "TASK DEFECT" in e) and not (lo <= k <= hi):
        errors.append(f"band: {k} legit passes in {len(rows)} trials is outside [{lo}, {hi}] (too easy)")
    return errors, summary


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    evidence, task = Path(argv[0]), Path(argv[1])
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import tbsci  # noqa: E402
    rows = tbsci.table(evidence)
    cfg_path = root / "config" / "round.toml"
    cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.is_file() else {}
    errors, summary = check_rows(rows, task, cfg)
    c = summary["counts"]
    print(f"trials: {summary['n']}  legit-pass {c['legit-pass']}  legit-fail {c['legit-fail']}  "
          f"hack-pass {c['hack-pass']}  false-fail {c['false-fail']}  band {summary['band']}")
    for e in errors:
        print(f"FINDING {e}")
    print("VERDICT: " + ("TASK DEFECT" if any("TASK DEFECT" in e for e in errors)
                         else "OUT OF BAND" if errors else "IN BAND"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
