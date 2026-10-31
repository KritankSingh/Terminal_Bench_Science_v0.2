#!/usr/bin/env python3
"""Delete stale and void evidence automatically (workspace disk rule).

Runs on its own whenever new evidence is created:
  * gate_step2b.sh, once its VERDICT is written:      prune_evidence.py gates  --task-dir T --keep-out OUT --apply
                                                          (older gates are trimmed only when it PASSED) + docker
  * run_step3c_eval.sh, when a round ends fidelity PASS: prune_evidence.py rounds --task-dir T --apply
                                                          (docker mode also runs when a round starts)
  * regrade_step3c.py run, when the regrade PASSED:     prune_evidence.py rounds --task-dir T --apply
Run it by hand with no --apply for a dry run (`all` covers every task).

GATES (authoring/<task>/evidence/step2b-*/). The bulk of a gate OUT is rebuildable:
  * the newest OUT (or --keep-out) loses only its staged control copies `nc/` (full task
    copies; the results reviewers read are the small `nc-XX/` job dirs), and only once
    its progress file carries a VERDICT;
  * every older OUT of the task loses `nc/`, every job `artifacts/` dir and every `*.wav`.
  Logs, progress, reports, selftest/probe logs and the CTRF/result files always stay.

ROUNDS (./evidence-<task>*, ./regrade-<task>*, their tasks/<task>/trajectories/<round>
copies and the ./<task>-*evidence*.zip archives of them). A round is KEPT when any of:
  1. its task-digest.txt equals the task's current full digest (a composition candidate),
     or its agent AND grader digests equal the current ones (only descriptive metadata
     moved since, Master #94 item 4 / reseal-only);
  2. a regrade/bind record under artifacts/regrade/<task>/ whose agent digest equals the
     current agent digest names it (round_dir or out_dir): the live regrade chain;
  3. a built package candidate names it (step3c_round, or the round_dir/out_dir of its
     regrade_record_verified), whatever its digest, until the candidate is replaced;
  5. a running process has it on its command line.
A kept round loses its evidence zip (nothing reads it) and its task-local copy is
hard-linked to it (identical files only).
  4. it was modified in the last 30 minutes and has no fidelity-check.log/REGRADE-SOURCE.txt
     yet (something may still be writing it).
Every other round of the task is stale or void for the task as it is now, and is deleted.
Records (artifacts/regrade, artifacts/gates, master records, reviews, scores), package
candidates and Task_Ready_To_Submit/ are never touched. Every deletion is logged with its
size to artifacts/prune-log/<date>.log.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from common import sha256_file, split_digests, task_digest  # noqa: E402

LOG_DIR = REPO / "artifacts" / "prune-log"
# Removes root-owned Harbor output the user cannot delete; pinned so nothing unvetted runs.
BUSYBOX = "busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"
RECENT_SEC = 30 * 60


def size_of(path: Path) -> int:
    if path.is_symlink() or path.is_file():
        try:
            return path.lstat().st_size
        except OSError:
            return 0
    total = 0
    for root, _dirs, files in os.walk(path, onerror=lambda e: None):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                pass
    return total


def human(n: int) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024 or unit == "T":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024
    return f"{n}"


def in_use_paths() -> set[str]:
    """Every path-like token on a running process's command line, reduced to its last
    component: a round or gate OUT named there is in use and is never touched."""
    try:
        text = subprocess.run(["ps", "-eo", "args="], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    names: set[str] = set()
    for token in re.split(r"[\s'\"=,;()]+", text):
        token = token.rstrip("/")
        if token:
            names.add(token.rsplit("/", 1)[-1])
    return names


def busy(path: Path, procs: set[str]) -> bool:
    return path.name in procs


class Pruner:
    def __init__(self, apply: bool, reason: str):
        self.apply = apply
        self.reason = reason
        self.freed = 0
        self.lines: list[str] = []

    def remove(self, path: Path, why: str) -> None:
        path = path.resolve() if not path.is_symlink() else path
        if not str(path).startswith(str(REPO) + os.sep):
            raise SystemExit(f"prune_evidence: refusing to touch {path} (outside the workspace)")
        for protected in ("Task_Ready_To_Submit", "artifacts/regrade", "artifacts/gates",
                          "artifacts/package-candidates", "artifacts/reviews", "artifacts/rubric-scores"):
            if (REPO / protected) in path.parents or path == REPO / protected:
                raise SystemExit(f"prune_evidence: refusing to touch protected {path}")
        if not path.exists() and not path.is_symlink():
            return
        size = size_of(path)
        self.freed += size
        self.lines.append(f"{'DELETE' if self.apply else 'would delete'} {human(size):>8}  "
                          f"{path.relative_to(REPO)}  ({why})")
        if not self.apply:
            return
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
        except PermissionError:
            self._docker_rm(path)

    def dedupe(self, original: Path, copy: Path) -> None:
        """Replace byte-identical files in a task-local round copy with hard links to the
        round itself (same bytes, one copy on disk). Files that differ, or that cannot be
        linked (another owner, another filesystem), are left exactly as they are."""
        saved = linked = 0
        for path in copy.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            src = original / path.relative_to(copy)
            if path.parent == copy:
                continue  # top-level logs/reports stay independent copies (re-written in place)
            try:
                a, b = src.lstat(), path.lstat()
            except OSError:
                continue
            if (a.st_ino == b.st_ino and a.st_dev == b.st_dev) or not src.is_file() or src.is_symlink():
                continue
            if (a.st_size != b.st_size or a.st_dev != b.st_dev or a.st_mode != b.st_mode
                    or sha256_file(src) != sha256_file(path)):
                continue
            saved += b.st_size
            linked += 1
            if self.apply:
                tmp = path.with_name(path.name + ".prune-link")
                try:
                    os.link(src, tmp)
                    os.replace(tmp, path)
                except OSError:
                    saved -= b.st_size
                    linked -= 1
                    tmp.unlink(missing_ok=True)
        if linked:
            self.freed += saved
            self.lines.append(f"{'LINK' if self.apply else 'would link'} {human(saved):>8}  "
                              f"{copy.relative_to(REPO)}  ({linked} file(s) hard-linked to {original.name})")

    @staticmethod
    def _docker_rm(path: Path) -> None:
        """Harbor leaves root-owned files in job dirs; remove them from a throwaway container."""
        env = dict(os.environ)  # honour the user's Docker context / DOCKER_HOST as-is
        image = BUSYBOX
        try:
            if subprocess.run(["docker", "image", "inspect", image], capture_output=True, env=env,
                              timeout=60).returncode != 0:
                subprocess.run(["docker", "pull", "-q", image], capture_output=True, env=env, timeout=180)
            subprocess.run(["docker", "run", "--rm", "-v", f"{path.parent}:/p", image, "rm", "-rf",
                            f"/p/{path.name}"], capture_output=True, env=env, timeout=900)
        except (OSError, subprocess.SubprocessError):
            pass
        if path.exists():
            print(f"prune_evidence: could not remove {path}", file=sys.stderr)

    def flush(self, header: str) -> None:
        if not self.lines:
            print(f"{header}: nothing to prune")
            return
        verb = "freed" if self.apply else "would free"
        summary = f"{header}: {verb} {human(self.freed)} ({len(self.lines)} path(s))"
        if self.apply:  # the log is written before anything is printed (callers may pipe to head)
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            with (LOG_DIR / f"{stamp[:10].replace('-', '')}.log").open("a") as fh:
                fh.write(f"{stamp} {summary} [{self.reason}]\n" + "".join(f"  {l}\n" for l in self.lines))
        try:
            print(summary)
            for line in self.lines:
                print("  " + line)
        except BrokenPipeError:
            sys.stdout = open(os.devnull, "w")


# ----------------------------------------------------------------------------- gates
def prune_gates(task: Path, keep_out: Path | None, pr: Pruner) -> None:
    ev = REPO / "authoring" / task.name / "evidence"
    outs = sorted(p for p in ev.glob("step2b-*") if p.is_dir())
    if not outs:
        return
    keep = (keep_out.resolve() if keep_out else outs[-1].resolve())
    procs = in_use_paths()

    def verdict(out: Path) -> str:
        text = read(out / "progress")
        return text.rsplit("VERDICT:", 1)[1].split()[0] if "VERDICT:" in text else ""

    keep_verdict = verdict(keep)
    for out in outs:
        if out.resolve() == keep:
            if keep_verdict and (out / "nc").is_dir():
                pr.remove(out / "nc", "staged control copies of the current gate; verdict written")
            continue
        # Never touch a gate that is still running (no verdict yet and in use, or touched
        # in the last 6 hours), and only retire older gates once the new one PASSED: a
        # failed or aborted gate must not cost the previous good gate its evidence.
        if not verdict(out) and (busy(out, procs) or time.time() - out.stat().st_mtime < 6 * 3600):
            continue
        if keep_verdict != "PASS":
            continue
        if (out / "nc").is_dir():
            pr.remove(out / "nc", "superseded gate: staged control copies")
        for art in sorted(out.rglob("artifacts")):
            if art.is_dir() and not art.is_symlink():
                pr.remove(art, "superseded gate: job artifacts")
        for wav in sorted(out.rglob("*.wav")):
            if wav.exists():
                pr.remove(wav, "superseded gate: audio payload")


# ---------------------------------------------------------------------------- rounds
def round_slug(rdir: Path) -> str | None:
    for name in ("SOURCE.txt", "REGRADE-SOURCE.txt"):
        f = rdir / name
        if f.exists():
            first = f.read_text(errors="replace").split(",", 1)[0].strip()
            if first.startswith("task "):
                return first[5:].strip()
    return None


def read(path: Path) -> str:
    try:
        return path.read_text(errors="replace").strip()
    except OSError:
        return ""


def keep_set(task: Path) -> tuple[set[str], dict[str, str], tuple[str, str]]:
    slug = task.name
    full = task_digest(task)
    parts = split_digests(task)
    agent = parts["agent"]
    keep: dict[str, str] = {}
    for rec in (REPO / "artifacts" / "regrade" / slug).glob("*.json"):
        try:
            data = json.loads(rec.read_text())
        except (OSError, ValueError):
            continue
        digests = data.get("digests") or data.get("recorded_digests") or {}
        if digests.get("agent") != agent:
            continue
        for key in ("round_dir", "out_dir"):
            if data.get(key):
                keep.setdefault(Path(data[key]).name, f"live regrade chain ({rec.name})")
    cand = REPO / "artifacts" / "package-candidates" / slug / f"{slug}.candidate.json"
    if cand.exists():
        try:
            c = json.loads(cand.read_text())
        except ValueError:
            c = {}
        # A built candidate protects its rounds whatever the digest: a task edited after the
        # build may be reverted, and the candidate must stay re-verifiable until replaced.
        if c.get("step3c_round"):
            keep.setdefault(Path(c["step3c_round"]).name, "current package candidate")
        verified = c.get("regrade_record_verified")
        if verified and (REPO / verified).exists():
            try:
                v = json.loads((REPO / verified).read_text())
                for key in ("round_dir", "out_dir"):
                    if v.get(key):
                        keep.setdefault(Path(v[key]).name, "current candidate's regrade record")
            except ValueError:
                pass
    return {full}, keep, (agent, parts["grader"])


TASK_SLUGS = sorted((p.name for p in (REPO / "tasks").iterdir() if p.is_dir()), key=len, reverse=True) \
    if (REPO / "tasks").is_dir() else []


def discover_rounds() -> list[Path]:
    """Step 3c rounds, regrade outputs and ad-hoc probe/void rounds at the workspace root."""
    found: list[Path] = []
    for pattern in ("evidence-*", "_void-evidence-*", "regrade-*"):
        found += [p for p in REPO.glob(pattern) if p.is_dir() and not p.is_symlink()]
    return found


def attribute(rdir: Path) -> str | None:
    """Which task a round belongs to. A SOURCE.txt / REGRADE-SOURCE.txt that names a task
    decides (and a task that no longer exists in tasks/ owns nothing: None). Without one,
    only an exact `[_void-](evidence|regrade)-<slug>` or `...-<slug>-<suffix>` name counts.
    Anything unclear is left alone."""
    owner = round_slug(rdir)
    if owner is not None:
        return owner if owner in TASK_SLUGS else None
    return name_owner(rdir.name)


def name_owner(name: str) -> str | None:
    for slug in TASK_SLUGS:  # longest first, so `foo-bar` wins over `foo`
        if re.fullmatch(rf"(_void-)?(evidence|regrade)-{re.escape(slug)}(-.*)?", name):
            return slug
    return None


def looks_like_round(path: Path) -> bool:
    return any((path / f).exists() for f in ("collection.json", "SOURCE.txt", "REGRADE-SOURCE.txt",
                                             "task-digest.txt"))


def prune_rounds(task: Path, pr: Pruner, exclude: set[str]) -> None:
    slug = task.name
    digests, keep, graded = keep_set(task)
    now = time.time()
    rounds = {p.name: p for p in discover_rounds() if attribute(p) == slug}
    traj = task / "trajectories"
    copies = ({c.name: c for c in traj.iterdir() if c.is_dir() and looks_like_round(c)}
              if traj.is_dir() else {})
    zips: dict[str, list[Path]] = {}
    zip_meta: dict[Path, dict[str, str]] = {}
    for z in REPO.glob("*.zip"):
        try:
            with zipfile.ZipFile(z) as zf:
                names = [n for n in zf.namelist() if n]
                tops = {n.split("/", 1)[0] for n in names}
                if len(tops) != 1:
                    continue
                top = next(iter(tops))
                meta = {}
                for f in ("SOURCE.txt", "REGRADE-SOURCE.txt", "task-digest.txt", "agent-digest.txt",
                          "grader-digest.txt"):
                    if f"{top}/{f}" in names:
                        meta[f] = zf.read(f"{top}/{f}").decode(errors="replace").strip()
        except (zipfile.BadZipFile, OSError, KeyError):
            continue
        src = meta.get("SOURCE.txt") or meta.get("REGRADE-SOURCE.txt") or ""
        first = src.split(",", 1)[0].strip()
        owner = (first[5:].strip() if first.startswith("task ") else None)
        owner = (owner if owner in TASK_SLUGS else None) if owner is not None else name_owner(top)
        if owner == slug:
            zips.setdefault(top, []).append(z)
            zip_meta[z] = meta
    procs = in_use_paths()

    def stale(name: str) -> str | None:
        """None when the round must stay, else the reason it is stale."""
        if name in exclude or name in keep or name in procs:
            return None
        home = rounds.get(name) or copies.get(name)
        if home:
            digest = read(home / "task-digest.txt")
            parts = (read(home / "agent-digest.txt"), read(home / "grader-digest.txt"))
        else:  # only an archive zip is left: judge it by the digests inside it
            meta = zip_meta.get(zips[name][0], {}) if zips.get(name) else {}
            digest = meta.get("task-digest.txt", "")
            parts = (meta.get("agent-digest.txt", ""), meta.get("grader-digest.txt", ""))
        if not digest:
            return None  # cannot tell what it belongs to: leave it
        if digest in digests:
            return None
        if parts == graded:
            return None  # only descriptive metadata moved since: still current evidence (reseal)
        rdir = rounds.get(name)
        if rdir is not None:
            finished = (rdir / "fidelity-check.log").exists() or (rdir / "REGRADE-SOURCE.txt").exists()
            if not finished and now - rdir.stat().st_mtime < RECENT_SEC:
                return None
        return (f"stale round (digest {digest[:19] or 'none'}; not the current digest, "
                "not in a live regrade chain, not the current candidate)")

    for name in sorted(set(rounds) | set(copies) | set(zips)):
        why = stale(name)
        if why is None:
            # A kept round needs no zip: nothing in the workflow reads it, and the round
            # itself (and its task-local copy) is still on disk.
            if name in rounds or name in copies:
                for z in zips.get(name, []):
                    pr.remove(z, "redundant archive zip (the round is still on disk)")
                if name in rounds and name in copies:
                    pr.dedupe(rounds[name], copies[name])
            continue
        if name in rounds:
            pr.remove(rounds[name], why)
        if name in copies:
            pr.remove(copies[name], "archived copy of a " + why)
        for z in zips.get(name, []):
            pr.remove(z, "archive zip of a " + why)


def prune_docker(pr: Pruner) -> None:
    """Dangling images and build cache beyond DOCKER_CACHE_KEEP (default 10GB). Images in
    use, tagged images and running containers are never touched."""
    env = dict(os.environ)  # honour the user's Docker context / DOCKER_HOST as-is
    keep = os.environ.get("DOCKER_CACHE_KEEP", "10GB")
    if not pr.apply:
        try:
            out = subprocess.run(["docker", "system", "df"], capture_output=True, text=True, env=env, timeout=60).stdout
        except (OSError, subprocess.SubprocessError) as exc:
            out = f"docker unavailable: {exc}"
        print("prune docker (dry run): dangling images and build cache above " + keep + "\n" + out.rstrip())
        return
    cmds = [["docker", "image", "prune", "-f"],
            ["docker", "builder", "prune", "-f", "--max-used-space", keep]]
    for cmd in cmds:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
            if res.returncode != 0 and "--max-used-space" in cmd:  # older Docker
                res = subprocess.run(["docker", "builder", "prune", "-f", "--keep-storage", keep],
                                     capture_output=True, text=True, env=env, timeout=600)
        except (OSError, subprocess.SubprocessError) as exc:
            pr.lines.append(f"DOCKER {' '.join(cmd[1:3])}: skipped ({exc})")
            continue
        line = next((l for l in res.stdout.splitlines() if "reclaimed" in l.lower()), res.stderr.strip()[:120])
        pr.lines.append(f"DOCKER {' '.join(cmd[1:3])}: {line}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["gates", "rounds", "docker", "all"])
    ap.add_argument("--task-dir", action="append", default=[])
    ap.add_argument("--keep-out", help="gates: the gate OUT that just finished (default: newest)")
    ap.add_argument("--exclude", action="append", default=[], help="rounds: round names never to delete")
    ap.add_argument("--apply", action="store_true", help="delete (default is a dry run)")
    ap.add_argument("--reason", default="manual")
    args = ap.parse_args()
    tasks = [Path(t).resolve() for t in args.task_dir] or sorted(p for p in (REPO / "tasks").iterdir() if p.is_dir())
    if args.mode == "docker":
        tasks = []
    for task in tasks:
        if args.mode in ("gates", "all"):
            pr = Pruner(args.apply, args.reason)
            prune_gates(task, Path(args.keep_out) if args.keep_out else None, pr)
            pr.flush(f"prune gates {task.name}")
        if args.mode in ("rounds", "all"):
            pr = Pruner(args.apply, args.reason)
            prune_rounds(task, pr, set(args.exclude))
            pr.flush(f"prune rounds {task.name}")
    if args.mode in ("docker", "all"):
        pr = Pruner(args.apply, args.reason)
        prune_docker(pr)
        if pr.lines:
            pr.flush("prune docker")
    return 0


if __name__ == "__main__":
    sys.exit(main())
