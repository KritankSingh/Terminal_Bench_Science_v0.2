#!/usr/bin/env python3
"""Spend each stb AI key down to its budget before refreshing it.

Workspace credential policy: a key from `stb keys refresh` carries a $10 budget and
lasts 30 days, and the account allows only 20 refreshes. Refreshing before every
attempt burned that quota on keys that were barely used, and every refresh revokes
the previous key, which killed the trials of any other round running on it. So:

* Before each model attempt the launcher runs `ensure`. It sends a tiny completion
  (about 20 tokens) with the stored key. A working key is kept, whatever it has spent.
* Only a key the gateway rejects for its usage limit (Portkey "Usage Limit Exceeded",
  error code 04) is refreshed, once, under a machine-wide lock. Rounds that run in
  parallel share the key, and none of them refreshes a key another has just replaced.
* An invalid or expired key (401/403, Portkey code 03) is never refreshed
  automatically. `refresh --expired` does it after an operator has checked why.
* Every probe verdict that leads to a refresh, and every refresh, is appended to a
  machine-wide ledger (~/.cache/tb4-workflow/stb-key-ledger.jsonl) with key
  fingerprints only (sha256 prefix), never the key itself.

Never run `stb keys refresh` by hand; use `status`, `ensure` or `refresh`.

  python3 scripts/stb_key_guard.py status
  python3 scripts/stb_key_guard.py ensure --label <job> [--log FILE] [--no-refresh]
  python3 scripts/stb_key_guard.py refresh [--expired] [--label why]

Exit codes: 0 key usable; 2 key invalid/expired (operator action); 3 budget exhausted
and refresh not allowed or refused by stb (quota); 4 gateway unreachable.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

STATE_DIR = Path(os.environ.get("TB4_STATE_DIR", Path.home() / ".cache" / "tb4-workflow"))
LOCK_FILE = STATE_DIR / "stb-keys.lock"
LEDGER = STATE_DIR / "stb-key-ledger.jsonl"
PROBE_MODEL = os.environ.get("STB_KEY_PROBE_MODEL", "@openai/gpt-5.6")
EXHAUSTED_MARKERS = ("usage limit exceeded", "error code: 04", "budget exceeded", "budget limit")
INVALID_MARKERS = ("invalid api key", "error code: 03")


def _stb_python() -> list[str] | None:
    """The interpreter argv of the installed stb tool (it carries snorkelai_stb). Handles
    `#!/path/python` (uv/pipx) and `#!/usr/bin/env python3` (pip --user) shebangs."""
    stb = shutil.which("stb")
    if not stb:
        return None
    try:
        with open(Path(stb).resolve(), "rb") as fh:
            first = fh.readline(512).decode(errors="replace").strip()
    except OSError:
        return None
    return first[2:].split() if first.startswith("#!") and first[2:].split() else None


try:  # stb's own helpers give the gateway the headers and TLS context it expects
    from snorkelai_stb import portkey_utils as pu  # type: ignore
except ImportError:
    argv = _stb_python()
    if argv and not os.environ.get("_STB_GUARD_REEXEC"):
        os.environ["_STB_GUARD_REEXEC"] = "1"
        try:
            os.execvp(argv[0], [*argv, os.path.abspath(__file__), *sys.argv[1:]])
        except OSError:
            pass
    sys.exit("stb_key_guard: cannot load stb's credential helpers (snorkelai_stb). Install stb as the "
             "workspace docs describe (`uv tool install snorkelai-stb`), then `stb login`.")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fingerprint(key: str) -> str:
    return "sha256:" + hashlib.sha256(key.encode()).hexdigest()[:12]


class NoKey(Exception):
    pass


def stored_key() -> tuple[str, str]:
    """The key stb has stored NOW. stb caches config.ini per process, and `stb keys refresh`
    writes the new key from another process, so the cache is dropped before every read."""
    try:
        from snorkelai_stb.config import GlobalConfig  # type: ignore
        GlobalConfig._instance = None
    except (ImportError, AttributeError):
        pass
    try:
        cfg = pu.get_portkey_config()
    except ValueError as exc:
        raise NoKey(str(exc)) from exc
    return cfg["api_key"], cfg.get("gateway_url") or "https://api.portkey.ai/v1"


NO_KEY_HELP = ("no stb AI key is stored. Run `stb login` (it fetches your first key); if it reports "
               "'Could not fetch AI credentials', run `python3 scripts/stb_key_guard.py refresh`. Never run "
               "`stb keys refresh` by hand.")


def probe(key: str, gateway: str) -> tuple[str, str]:
    """Return (OK|EXHAUSTED|INVALID|UNREACHABLE, detail) for one tiny completion."""
    headers = {"x-portkey-api-key": key, "Content-Type": "application/json", "User-Agent": pu.get_user_agent()}
    headers.update(pu.get_portkey_headers("harbor"))
    body = json.dumps({"model": PROBE_MODEL, "messages": [{"role": "user", "content": "ok"}],
                       "max_completion_tokens": 16}).encode()
    last = ""
    for attempt in range(6):
        req = urllib.request.Request(gateway.rstrip("/") + "/chat/completions", data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60, context=pu.get_ssl_context()) as resp:
                return "OK", f"HTTP {resp.status}"
        except urllib.error.HTTPError as exc:
            text = exc.read().decode(errors="replace")[:400]
            low = text.lower()
            if any(m in low for m in EXHAUSTED_MARKERS):
                return "EXHAUSTED", f"HTTP {exc.code}: {text.strip()}"
            if exc.code in (401, 403) or any(m in low for m in INVALID_MARKERS):
                return "INVALID", f"HTTP {exc.code}: {text.strip()}"
            if 400 <= exc.code < 500 and exc.code != 429:
                return "REJECTED", f"HTTP {exc.code}: {text.strip()}"
            last = f"HTTP {exc.code}: {text.strip()}"  # 429/5xx: transient, retry with backoff
        except OSError as exc:
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(10 * (attempt + 1))  # up to ~3.5 minutes in total
    return "UNREACHABLE", last


def ledger(event: dict, log: Path | None) -> None:
    event = {"time": now(), "host": os.uname().nodename, **event}
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(event) + "\n")
    if log:
        with log.open("a") as fh:
            fh.write(f"{event['time']} {event['event']} ({event.get('label', '')}): "
                     + ", ".join(f"{k}={v}" for k, v in event.items() if k not in ("time", "event", "label")) + "\n")


def refreshes_last_24h() -> int:
    if not LEDGER.exists():
        return 0
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)
    count = 0
    for line in LEDGER.read_text().splitlines():
        try:
            rec = json.loads(line)
            when = dt.datetime.strptime(rec["time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        except (ValueError, KeyError):
            continue
        if rec.get("event") == "refresh" and rec.get("result") == "ok" and when >= cutoff:
            count += 1
    return count


def do_refresh(reason: str, label: str, log: Path | None, old_fp: str) -> int:
    out = subprocess.run(["stb", "keys", "refresh"], capture_output=True, text=True)
    text = (out.stdout + out.stderr).strip()
    if out.returncode != 0 or "error" in text.lower() or "❌" in text or "maximum refresh limit" in text.lower():
        tail = text.splitlines()[-1] if text else f"exit {out.returncode}"
        ledger({"event": "refresh", "label": label, "reason": reason, "result": "failed",
                "fingerprint_before": old_fp, "stb": tail}, log)
        low = text.lower()
        if "maximum refresh limit" in low or "limit" in low and "refresh" in low:
            action = ("your account's refresh quota is used up. Ask a workspace admin to reset it, or install a "
                      "key you were given with `stb keys set`; then relaunch the round in a fresh OUT.")
        elif any(w in low for w in ("login", "log in", "unauthor", "401", "403", "expired", "token")):
            action = ("your stb session is not valid. Run `stb login`, then "
                      "`python3 scripts/stb_key_guard.py refresh`, then relaunch the round in a fresh OUT.")
        else:
            action = "check `stb --version` / your network, then `python3 scripts/stb_key_guard.py status`."
        print(f"stb_key_guard: STOP — the key's budget is used up and `stb keys refresh` failed ({tail}). "
              f"What to do: {action} Completed trials stay candidates for scripts/compose_step3c.py.",
              file=sys.stderr)
        return 3
    key, gateway = stored_key()
    status, detail = probe(key, gateway)
    for _ in range(5):  # a brand-new key can take a moment to activate at the gateway
        if status != "INVALID" or fingerprint(key) == old_fp:
            break
        time.sleep(5)
        status, detail = probe(key, gateway)
    if fingerprint(key) == old_fp:
        status, detail = "UNCHANGED", "stb reported success but the stored key did not change"
    ledger({"event": "refresh", "label": label, "reason": reason, "result": "ok" if status == "OK" else status,
            "fingerprint_before": old_fp, "fingerprint_after": fingerprint(key), "probe": detail,
            "refreshes_24h": refreshes_last_24h() + (1 if status == "OK" else 0)}, log)
    if status != "OK":
        print(f"stb_key_guard: STOP — refreshed, but the new key does not work ({status}: {detail}). "
              "Run `python3 scripts/stb_key_guard.py status`; if it persists run `stb login` and retry.",
              file=sys.stderr)
        return 2 if status in ("INVALID", "UNCHANGED") else 4
    print(f"stb_key_guard: refreshed ({reason}); new key {fingerprint(key)}; "
          f"{refreshes_last_24h()} refresh(es) in the last 24 h on this machine")
    return 0


class Lock:
    def __enter__(self):
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.fh = LOCK_FILE.open("w")
        fcntl.flock(self.fh, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.fh, fcntl.LOCK_UN)
        self.fh.close()


def cmd_status(args) -> int:
    try:
        key, gateway = stored_key()
    except NoKey:
        print(f"stb_key_guard: {NO_KEY_HELP}", file=sys.stderr)
        return 2
    status, detail = probe(key, gateway)
    print(f"key {fingerprint(key)}: {status} ({detail}); {refreshes_last_24h()} refresh(es) in the last 24 h")
    return {"OK": 0, "INVALID": 2, "EXHAUSTED": 3}.get(status, 4)


def cmd_ensure(args) -> int:
    log = Path(args.log) if args.log else None
    with Lock():
        try:
            key, gateway = stored_key()
        except NoKey:
            print(f"stb_key_guard: STOP before {args.label} — {NO_KEY_HELP}", file=sys.stderr)
            return 2
        fp = fingerprint(key)
        status, detail = probe(key, gateway)
        if status == "OK":
            if log:
                with log.open("a") as fh:
                    fh.write(f"{now()} key ok ({args.label}): {fp}, no refresh\n")
            return 0
        if status == "REJECTED":
            ledger({"event": "probe", "label": args.label, "status": status, "fingerprint": fp, "detail": detail}, log)
            print(f"stb_key_guard: STOP before {args.label} — the gateway rejected the probe request "
                  f"({detail}). This is not a key-budget problem; report it to the workspace maintainers "
                  "(the probe model can be overridden with STB_KEY_PROBE_MODEL).", file=sys.stderr)
            return 4
        if status == "UNREACHABLE":
            ledger({"event": "probe", "label": args.label, "status": status, "fingerprint": fp, "detail": detail}, log)
            print(f"stb_key_guard: STOP before {args.label} — the AI gateway could not be reached ({detail}). "
                  "Check your network/VPN, then relaunch the round in a fresh OUT.", file=sys.stderr)
            return 4
        if status == "INVALID":
            ledger({"event": "probe", "label": args.label, "status": status, "fingerprint": fp, "detail": detail}, log)
            print(f"stb_key_guard: STOP before {args.label} — the stored key {fp} is invalid or expired "
                  f"({detail}). Keys are not refreshed automatically for this. What to do: if `stb keys show` "
                  "is empty or your session expired, run `stb login`; then run "
                  "`python3 scripts/stb_key_guard.py refresh --expired` (or `stb keys set` with a key you were "
                  "given) and relaunch the round in a fresh OUT. Completed trials stay candidates for "
                  "scripts/compose_step3c.py.", file=sys.stderr)
            return 2
        # EXHAUSTED: the only automatic refresh.
        ledger({"event": "probe", "label": args.label, "status": status, "fingerprint": fp, "detail": detail}, log)
        if args.no_refresh:
            print(f"stb_key_guard: STOP before {args.label} — key {fp} has used its $10 budget and "
                  "STB_KEYS_NO_REFRESH=1 forbids a refresh. Run `python3 scripts/stb_key_guard.py refresh`, "
                  "then relaunch in a fresh OUT.", file=sys.stderr)
            return 3
        return do_refresh("budget exhausted", args.label, log, fp)


def cmd_refresh(args) -> int:
    with Lock():
        try:
            key, gateway = stored_key()
        except NoKey:  # no key at all: fetching the first one wastes no budget
            return do_refresh("no key stored", args.label, None, "none")
        fp = fingerprint(key)
        status, detail = probe(key, gateway)
        if status == "EXHAUSTED" or (status == "INVALID" and args.expired):
            return do_refresh("budget exhausted" if status == "EXHAUSTED" else "invalid/expired (operator)",
                              args.label, None, fp)
        print(f"stb_key_guard: refusing to refresh: key {fp} is {status} ({detail}). Keys are refreshed only "
              "after their $10 budget is used up" + ("" if status != "INVALID" else "; pass --expired after checking why it is invalid") + ".",
              file=sys.stderr)
        return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    e = sub.add_parser("ensure")
    e.add_argument("--label", default="manual")
    e.add_argument("--log")
    e.add_argument("--no-refresh", action="store_true")
    r = sub.add_parser("refresh")
    r.add_argument("--expired", action="store_true")
    r.add_argument("--label", default="manual")
    args = ap.parse_args()
    return {"status": cmd_status, "ensure": cmd_ensure, "refresh": cmd_refresh}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
