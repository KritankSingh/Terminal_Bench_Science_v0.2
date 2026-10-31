#!/usr/bin/env python3
"""Apply (or verify) the full-fidelity capture patches to the Harbor copy bundled inside ``stb``.

``stb harbor run`` executes its OWN Harbor copy under
``~/.local/share/uv/tools/snorkelai-stb/``, not the standalone ``harbor`` used for
Oracle/NOP controls. Step 3c model trials therefore need these capture patches
there. The script is idempotent, keeps ``<file>.orig-<stb version>`` backups, and
must be re-run after every ``stb`` install, upgrade **or reinstall**
(``run_step3c_eval.sh`` re-checks before every single model attempt).

  python3 scripts/patch_stb_harbor.py                 # apply, then self-check
  python3 scripts/patch_stb_harbor.py --check         # verify only; exit 1 if not patched
  python3 scripts/patch_stb_harbor.py --check-agent   # verify the Step 3c --ak set validates

Patch 1   terminus_2.py  ``_limit_output_length`` honours ``TERMINUS_MAX_OUTPUT_BYTES``
                         (legacy upstream variable; default stays 10000).
Patch 2a  terminus_2.py  with ``TERMINUS_RAW_API_LOG=1`` the agent points its LLM at
                         ``<trial>/agent/api-calls.jsonl``.
Patch 2b  lite_llm.py    ``_raw_api_log()`` appends every request + raw response as
                         JSONL (chat-completions and Responses paths).

Both patched files also gain a module-level ``HARBOR_FULL_FIDELITY_PATCH`` marker so
the patch can be verified by grep, by import, and by content digest.

WHY ``--check`` IS PARANOID.  ``uv tool install snorkelai-stb ... --reinstall`` (the
command ``stb`` itself prints when it blocks on an outdated version) rewrites the whole
site-packages tree and silently reverts these patches. A round launched against a
reverted install spends real money and produces a 10 000-byte-capped trajectory that
``prompts/step3c.md`` voids. ``--check`` therefore fails unless ALL of the following
hold, and prints one line per item:

  1. exactly one stb-bundled Harbor tree exists;
  2. the bundled interpreter imports Harbor FROM that tree (not a PYTHONPATH shadow);
  3. the imported Harbor version is one this patch was built and anchored for;
  4. every patch marker is present in the on-disk sources;
  5. the imported modules carry the marker and actually behave (uncapped output,
     ``LiteLLM._raw_api_log``) — this is what catches a stale ``__pycache__``;
  6. the stamp file records this patch revision, this Harbor version, and SHA-256
     digests that still match both files byte for byte.

Source: STB full-fidelity kit (``docs/reference/stb-full-fidelity-kit/``).
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import time

STB_TOOL_ROOT = os.path.expanduser("~/.local/share/uv/tools/snorkelai-stb")

# Bump when the patch body changes; the stamp and the in-file markers carry it, so an
# older patch left behind by a partial upgrade fails --check instead of passing.
PATCH_REVISION = "r3"

# Harbor releases whose anchors this patch was verified against by hand.
# 0.22.0: stb 2.4.15.  0.23.0: stb 2.4.16 (strict agent-kwarg validation added; the
# terminus_2/lite_llm anchors below are unchanged between the two).
SUPPORTED_HARBOR = ("0.22.0", "0.23.0")

TERMINUS_REL = "agents/terminus_2/terminus_2.py"
LITELLM_REL = "llms/lite_llm.py"
STAMP_NAME = ".full-fidelity-patch.json"

MARKER_LINE = f'HARBOR_FULL_FIDELITY_PATCH = "{PATCH_REVISION}"'

# Plain substrings that must survive in the patched sources. `grep -c` on any of these
# is a valid hand check; see docs/reference/stb-full-fidelity-kit/README.md.
MARKERS = {
    TERMINUS_REL: (MARKER_LINE, "TERMINUS_MAX_OUTPUT_BYTES", "TERMINUS_RAW_API_LOG"),
    LITELLM_REL: (MARKER_LINE, "def _raw_api_log"),
}

# Probe run by the *bundled* interpreter in isolated mode (-I: no PYTHONPATH, no user
# site), so it can never import a different Harbor than the one stb will run.
PROBE = r'''
import json, os
out = {}
try:
    os.environ["TERMINUS_MAX_OUTPUT_BYTES"] = "100000000"
    import harbor
    from harbor.agents.terminus_2 import terminus_2 as t2
    from harbor.llms import lite_llm as ll
    out["harbor_version"] = getattr(harbor, "__version__", None)
    out["terminus_file"] = os.path.realpath(t2.__file__)
    out["lite_llm_file"] = os.path.realpath(ll.__file__)
    out["terminus_marker"] = getattr(t2, "HARBOR_FULL_FIDELITY_PATCH", None)
    out["lite_llm_marker"] = getattr(ll, "HARBOR_FULL_FIDELITY_PATCH", None)
    out["uncapped"] = "omitted" not in t2.Terminus2._limit_output_length(None, "x" * 50000)
    out["raw_api_log"] = hasattr(ll.LiteLLM, "_raw_api_log")
    try:
        import importlib.metadata as _md
        out["stb_version"] = _md.version("snorkelai-stb")
    except Exception:
        out["stb_version"] = None
except BaseException as exc:
    out["error"] = f"{type(exc).__name__}: {exc}"
print("FFPROBE " + json.dumps(out))
'''

# Validates the exact --ak set run_step3c_eval.sh passes, against the recording adapter,
# through Harbor's own options model. Needs PYTHONPATH=<workspace>, so it cannot use -I.
AGENT_PROBE = r'''
import json
out = {}
try:
    from scripts.harbor_recording import RecordingTerminus2 as A
    model = getattr(A, "options_model", None)
    out["options_model"] = getattr(model, "__name__", None)
    kwargs = {"max_output_bytes": 0, "reasoning_effort": "xhigh", "store_all_messages": True}
    if hasattr(A, "preflight"):
        A.preflight(kwargs=dict(kwargs))
        out["preflight"] = "ok"
    else:
        out["preflight"] = "n/a (harbor has no preflight; 0.22)"
    if model is not None:
        parsed = model.model_validate(dict(kwargs))
        out["parsed"] = {k: getattr(parsed, k, None) for k in kwargs}
except BaseException as exc:
    out["error"] = f"{type(exc).__name__}: {exc}"
print("FFAGENT " + json.dumps(out))
'''


# --------------------------------------------------------------------------- helpers


def bundled_harbor_trees() -> list[str]:
    return sorted(glob.glob(f"{STB_TOOL_ROOT}/lib/python3.*/site-packages/harbor"))


def bundled_harbor() -> str | None:
    found = bundled_harbor_trees()
    return found[0] if found else None


def bundled_python() -> str | None:
    found = glob.glob(f"{STB_TOOL_ROOT}/bin/python3")
    return found[0] if found else None


def sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run_probe(source: str, sentinel: str, isolated: bool, env: dict | None = None) -> tuple[dict | None, str]:
    """Run ``source`` with the stb-bundled interpreter and return its sentinel JSON."""
    python = bundled_python()
    if python is None:
        return None, "stb-bundled interpreter not found"
    cmd = [python, "-I", "-c", source] if isolated else [python, "-c", source]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180,
                                env=env if env is not None else os.environ.copy())
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"probe could not run: {exc}"
    for line in reversed((result.stdout or "").splitlines()):
        if line.startswith(sentinel + " "):
            try:
                return json.loads(line[len(sentinel) + 1:]), ""
            except ValueError as exc:
                return None, f"probe emitted unparsable JSON: {exc}"
    tail = ((result.stderr or "") + (result.stdout or "")).strip()[-600:]
    return None, f"probe printed no {sentinel} line (rc={result.returncode}): {tail}"


def stb_version(probe: dict | None = None) -> str:
    """stb version from the bundled interpreter's own metadata.

    ``stb --version`` is avoided on purpose: it runs the CLI's update check, which
    raises (and prints an upgrade command) when a newer release exists.
    """
    if probe and probe.get("stb_version"):
        return str(probe["stb_version"])
    got, _ = run_probe(
        'import json,importlib.metadata as m\n'
        'try: v=m.version("snorkelai-stb")\n'
        'except Exception: v=None\n'
        'print("FFVER "+json.dumps({"stb_version":v}))\n',
        "FFVER", isolated=True)
    if got and got.get("stb_version"):
        return str(got["stb_version"])
    return "unknown"


def stamp_path(hb: str) -> str:
    return os.path.join(hb, STAMP_NAME)


def write_stamp(hb: str, harbor_version: str, stb_ver: str) -> None:
    stamp = {
        "revision": PATCH_REVISION,
        "harbor_version": harbor_version,
        "stb_version": stb_ver,
        "applied_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "files": {rel: sha256(os.path.join(hb, rel)) for rel in MARKERS},
    }
    with open(stamp_path(hb), "w") as fh:
        fh.write(json.dumps(stamp, indent=2) + "\n")


# ----------------------------------------------------------------------------- check


def check_detail() -> tuple[bool, list[str]]:
    """Run every verification step. Returns (ok, one report line per step)."""
    lines: list[str] = []
    ok = True

    def step(name: str, good: bool, detail: str = "") -> bool:
        nonlocal ok
        lines.append(f"  [{'PASS' if good else 'FAIL'}] {name}{': ' + detail if detail else ''}")
        ok = ok and good
        return good

    trees = bundled_harbor_trees()
    if not step("stb-bundled harbor tree", len(trees) == 1,
                (trees[0] if len(trees) == 1 else f"{len(trees)} candidates: {trees or 'none'} "
                 f"(expected exactly one under {STB_TOOL_ROOT})")):
        return False, lines
    hb = trees[0]

    probe, error = run_probe(PROBE, "FFPROBE", isolated=True)
    if not step("bundled interpreter imports harbor", probe is not None and not probe.get("error"),
                error or (probe or {}).get("error", "")):
        return False, lines
    assert probe is not None

    real_hb = os.path.realpath(hb)
    from_tree = all(str(probe.get(key, "")).startswith(real_hb + os.sep)
                    for key in ("terminus_file", "lite_llm_file"))
    step("harbor imported from the stb tree (no PYTHONPATH shadow)", from_tree,
         f"terminus_2={probe.get('terminus_file')} lite_llm={probe.get('lite_llm_file')}")

    version = str(probe.get("harbor_version"))
    step("harbor version is one this patch was built for", version in SUPPORTED_HARBOR,
         f"found {version}, patch {PATCH_REVISION} supports {', '.join(SUPPORTED_HARBOR)}"
         + ("" if version in SUPPORTED_HARBOR else
            " — re-port the patch against the new sources before any paid round"))

    for rel, markers in MARKERS.items():
        path = os.path.join(hb, rel)
        try:
            with open(path) as fh:
                text = fh.read()
        except OSError as exc:
            step(f"markers in {rel}", False, str(exc))
            continue
        missing = [m for m in markers if m not in text]
        step(f"markers in {rel}", not missing,
             "all present" if not missing else f"missing {missing}")

    step("imported modules carry the marker (no stale __pycache__)",
         probe.get("terminus_marker") == PATCH_REVISION and probe.get("lite_llm_marker") == PATCH_REVISION,
         f"terminus_2={probe.get('terminus_marker')!r} lite_llm={probe.get('lite_llm_marker')!r}, "
         f"expected {PATCH_REVISION!r}")
    step("observation cap is lifted by TERMINUS_MAX_OUTPUT_BYTES", bool(probe.get("uncapped")),
         "50 000-byte observation survived" if probe.get("uncapped") else
         "output was still truncated — the 10 000-byte cap is live")
    step("LiteLLM._raw_api_log exists (api-calls.jsonl capture)", bool(probe.get("raw_api_log")))

    sp = stamp_path(hb)
    try:
        with open(sp) as fh:
            stamp = json.load(fh)
    except (OSError, ValueError) as exc:
        step("patch stamp", False, f"{sp}: {exc}")
        return ok and False, lines
    good_rev = stamp.get("revision") == PATCH_REVISION
    step("stamp revision", good_rev, f"{stamp.get('revision')!r}, expected {PATCH_REVISION!r}")
    good_ver = stamp.get("harbor_version") == version
    step("stamp harbor version matches the installed one", good_ver,
         f"stamped {stamp.get('harbor_version')!r}, installed {version!r}"
         + ("" if good_ver else " — harbor was reinstalled or upgraded after patching"))
    recorded = stamp.get("files") or {}
    drift = []
    for rel in MARKERS:
        try:
            live = sha256(os.path.join(hb, rel))
        except OSError as exc:
            drift.append(f"{rel}: {exc}")
            continue
        if recorded.get(rel) != live:
            drift.append(f"{rel}: stamped {str(recorded.get(rel))[:12]} live {live[:12]}")
    step("patched files unchanged since the patch was applied", not drift,
         "both digests match" if not drift else "; ".join(drift))
    return ok, lines


def check_patch() -> tuple[bool, str]:
    """Back-compatible entry point used by ``scripts/doctor.py``."""
    ok, lines = check_detail()
    if ok:
        return True, "all checks passed"
    return False, "; ".join(line.strip() for line in lines if line.strip().startswith("[FAIL]"))


def check_agent_options() -> tuple[bool, str]:
    """Validate the Step 3c ``--ak`` set against the recording adapter's options model."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = os.environ.copy()
    env["PYTHONPATH"] = root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    got, error = run_probe(AGENT_PROBE, "FFAGENT", isolated=False, env=env)
    if got is None:
        return False, error
    if got.get("error"):
        return False, str(got["error"])
    return True, json.dumps(got)


# ----------------------------------------------------------------------------- apply


def backup(path: str, ver: str) -> None:
    copy = f"{path}.orig-{ver}"
    if not os.path.exists(copy):
        with open(path) as src, open(copy, "w") as dst:
            dst.write(src.read())


def apply(force_version: bool = False) -> int:
    hb = bundled_harbor()
    if hb is None:
        print("stb-bundled harbor not found; install stb first (see AGENT SETUP MANIFEST.txt)", file=sys.stderr)
        return 2

    probe, error = run_probe(PROBE, "FFPROBE", isolated=True)
    if probe is None or probe.get("error"):
        print(f"cannot read the bundled harbor: {error or probe.get('error')}", file=sys.stderr)
        return 2
    version = str(probe.get("harbor_version"))
    if version not in SUPPORTED_HARBOR and not force_version:
        print(f"harbor {version} is not one of the versions this patch was built for "
              f"({', '.join(SUPPORTED_HARBOR)}).\nRe-port the patch against the new sources "
              f"(anchors are listed in the module docstring), then add the version to "
              f"SUPPORTED_HARBOR. --force-version patches anyway and is for porting work only, "
              f"never for a paid round.", file=sys.stderr)
        return 2
    ver = stb_version(probe)

    # ---- Patch 1 + 2a: terminus_2.py ----
    p = os.path.join(hb, TERMINUS_REL)
    s = open(p).read()
    before = s
    if "TERMINUS_MAX_OUTPUT_BYTES" not in s:
        backup(p, ver)
        old = "    def _limit_output_length(self, output: str, max_bytes: int = 10000) -> str:\n"
        new = ('    def _limit_output_length(self, output: str, max_bytes: int | None = None) -> str:\n'
               '        if max_bytes is None:\n'
               '            import os as _os\n'
               '            max_bytes = int(_os.environ.get("TERMINUS_MAX_OUTPUT_BYTES", "10000"))\n')
        assert s.count(old) == 1, "cap signature not found — harbor changed; patch by hand"
        s = s.replace(old, new)
        print("patch 1 applied (output cap)")
    else:
        print("patch 1 already present")
    if "TERMINUS_RAW_API_LOG" not in s:
        old = ("        self._parser = self._get_parser()\n"
               "        self._prompt_template = self._get_prompt_template_path().read_text()")
        new = ('        if _os_env_flag("TERMINUS_RAW_API_LOG"):\n'
               '            try:\n'
               '                self._llm._raw_log_path = str(self.logs_dir / "api-calls.jsonl")\n'
               '            except Exception:\n'
               '                pass\n' + old)
        assert s.count(old) == 1, "terminus init anchor not found — harbor changed; patch by hand"
        s = s.replace(old, new)
        i = s.index("class Terminus2")
        s = s[:i] + (f'{MARKER_LINE}  # full-fidelity capture kit\n\n\n'
                     'def _os_env_flag(name: str) -> bool:\n    import os as _os\n'
                     '    return _os.environ.get(name, "").lower() in ("1", "true", "yes")\n\n\n') + s[i:]
        print("patch 2a applied (terminus hook)")
    else:
        print("patch 2a already present")
    if MARKER_LINE not in s:  # patched by an older revision of this script
        i = s.index("class Terminus2")
        s = s[:i] + f'{MARKER_LINE}  # full-fidelity capture kit\n\n\n' + s[i:]
        print(f"marker {PATCH_REVISION} added to terminus_2.py")
    if s != before:
        open(p, "w").write(s)

    # ---- Patch 2b: raw API log in LiteLLM ----
    p = os.path.join(hb, LITELLM_REL)
    s = open(p).read()
    before = s
    if "_raw_api_log" not in s:
        backup(p, ver)
        old = '        choice = response["choices"][0]\n        message = choice["message"]\n'
        assert s.count(old) == 1, "chat-completions anchor not found — harbor changed; patch by hand"
        s = s.replace(old, '        self._raw_api_log(completion_kwargs, response)\n' + old)
        old2 = '        # Extract text content from response.output\n        content = ""\n        reasoning_content = None\n'
        assert s.count(old2) == 1, "responses anchor not found — harbor changed; patch by hand"
        s = s.replace(old2, '        self._raw_api_log(responses_kwargs, response)\n' + old2)
        old3 = "    def _extract_usage_info(self, response) -> UsageInfo | None:\n"
        assert s.count(old3) == 1, "usage-info anchor not found — harbor changed; patch by hand"
        helper = '''    def _raw_api_log(self, request_kwargs, response) -> None:
        """Full-fidelity capture: append {request, raw response} as JSONL when _raw_log_path is set."""
        path = getattr(self, "_raw_log_path", None)
        if not path:
            return
        import json as _json, time as _time
        def _plain(o):
            for attr in ("model_dump", "to_dict", "dict"):
                f = getattr(o, attr, None)
                if callable(f):
                    try:
                        return f()
                    except Exception:
                        pass
            try:
                return _json.loads(_json.dumps(o, default=str))
            except Exception:
                return str(o)
        req = {k: v for k, v in request_kwargs.items() if k not in ("api_key", "extra_headers")}
        rec = {"ts": _time.time(), "request": _plain(req), "response": _plain(response)}
        try:
            with open(path, "a") as fh:
                fh.write(_json.dumps(rec, default=str) + "\\n")
        except Exception:
            pass

'''
        s = s.replace(old3, helper + old3)
        print("patch 2b applied (raw API log)")
    else:
        print("patch 2b already present")
    if MARKER_LINE not in s:
        marker_anchor = "class LiteLLM"
        assert s.count(marker_anchor) >= 1, "LiteLLM class not found — harbor changed; patch by hand"
        i = s.index(marker_anchor)
        s = s[:i] + f'{MARKER_LINE}  # full-fidelity capture kit\n\n\n' + s[i:]
        print(f"marker {PATCH_REVISION} added to lite_llm.py")
    if s != before:
        open(p, "w").write(s)

    write_stamp(hb, version, ver)
    print(f"stamped {stamp_path(hb)} (revision {PATCH_REVISION}, harbor {version}, stb {ver})")

    ok, lines = check_detail()
    print(f"stb-bundled harbor patch: {'PASS' if ok else 'FAIL'}")
    print("\n".join(lines))
    return 0 if ok else 1


# ------------------------------------------------------------------------------ main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="verify only; exit 1 if not fully patched")
    parser.add_argument("--check-agent", action="store_true",
                        help="verify the Step 3c --ak set validates against the recording adapter")
    parser.add_argument("--quiet", action="store_true", help="print only the verdict line")
    parser.add_argument("--force-version", action="store_true",
                        help="patch a harbor version this script was not built for (porting only)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.check_agent:
        ok, detail = check_agent_options()
        print(f"stb-bundled harbor agent options: {'PASS' if ok else 'FAIL'} ({detail})")
        return 0 if ok else 1
    if args.check:
        ok, lines = check_detail()
        print(f"stb-bundled harbor patch: {'PASS' if ok else 'FAIL'}")
        if not args.quiet or not ok:
            print("\n".join(lines))
        if not ok:
            print("run: python3 scripts/patch_stb_harbor.py   (re-run after every stb install, "
                  "upgrade or reinstall)", file=sys.stderr)
        return 0 if ok else 1
    try:
        return apply(force_version=args.force_version)
    except AssertionError as exc:
        print(f"patch_stb_harbor.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
