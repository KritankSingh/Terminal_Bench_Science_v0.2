#!/usr/bin/env python3
"""Check that the hardened Terminal-Bench Science workspace and local Harbor tooling are usable."""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from common import REPO_ROOT
from patch_stb_harbor import check_patch


REQUIRED_PATHS = (
    Path("MASTER_CHECKLIST_TBSCI.md"),
    Path("FROZEN.md5"),
    Path("config/round.toml"),
    Path("config/client_rules.toml"),
    Path("docs/WORKFLOW.md"),
    Path("docs/V02_RULES.md"),
    Path("scripts/tbsci.py"),
    Path("scripts/v02_checks.py"),
    Path("scripts/trial_labels.py"),
    Path("AGENTS.md"),
    Path("commands.md"),
    Path("docs/TBSCI_HARDENING_RULES.md"),
    Path("docs/TESTING_POLICY.md"),
    Path("docs/TASK_TAXONOMY.md"),
    Path("docs/TASK_COMPONENTS.md"),
    Path("prompts/step1.md"),
    Path("prompts/step2a.md"),
    Path("prompts/step2b.md"),
    Path("prompts/step3a.md"),
    Path("prompts/step3b.md"),
    Path("prompts/step3c.md"),
    Path("prompts/step4.md"),
    Path("authoring/_templates/controls.md"),
    Path("scripts/hardening_check.py"),
    Path("scripts/per_test_gate.py"),
    Path("scripts/evidence.py"),
    Path("scripts/package_task.py"),
    Path("scripts/master_checklist.py"),
    Path("scripts/verify_package.py"),
    Path("scripts/bundle_sha.py"),
    Path("scripts/audit_task.py"),
    Path("tools/final-tbsci-audit-master/scripts/tbsci_static_screen.py"),
    Path("tools/final-tbsci-audit-master/scripts/trial_evidence.py"),
    Path("tools/final-tbsci-audit-master/scripts/verdict_lint.py"),
    Path("tools/final-tbsci-audit-master/scripts/review.sh"),
    Path("tools/final-tbsci-audit-master/reference/MASTER_CHECKLIST_TBSCI.md"),
    Path("scripts/harbor_recording.py"),
    Path("scripts/run_step3c_eval.sh"),
    Path("scripts/patch_stb_harbor.py"),
    Path("scripts/check_trajectory.py"),
    Path("scripts/stb_key_guard.py"),
    Path("scripts/prune_evidence.py"),
    Path("docs/reference/stb-full-fidelity-kit/README.md"),
    Path("docs/reference/stb-full-fidelity-kit/stb_key_guard.py"),
)


def run(command: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


# TB-Science tasks declare [verifier.environment].network_mode = "no-network" (Master #64).
# Harbor's Docker backend enforces it with an egress-control sidecar, and enables
# that only when a short kernel probe container succeeds (30 s limit). A probe that is
# slow -- its image not yet pulled, or Docker busy building -- silently disables egress
# control and the trial then fails with "network_mode='no-network' is not supported by
# EnvironmentType.DOCKER environment". This pre-pulls the probe image and runs Harbor's
# own probe through Harbor's interpreter.
EGRESS_PROBE = """
import subprocess, sys
try:
    from harbor.environments.docker.docker import DockerEnvironment as D
    image = D._EGRESS_CONTROL_KERNEL_PROBE_IMAGE
    support = D._egress_control_kernel_support
except Exception as exc:  # Harbor internals moved: report, do not guess
    print(f"UNKNOWN cannot locate Harbor's egress-control probe: {exc}"); sys.exit(2)
subprocess.run(["docker", "pull", "-q", image], capture_output=True, timeout=300)
print("OK" if support() else f"FAIL probe {image} did not pass"); sys.exit(0 if support() else 1)
"""


def check_egress_control(harbor: str) -> tuple[int, str]:
    """(0 ok | 1 unsupported | 2 unknown, detail) for Harbor's Docker no-network support."""
    path = shutil.which(harbor)
    if not path:
        return 2, f"{harbor} not found"
    try:
        first = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        return 2, f"cannot read {path}"
    interpreter = first[2:].strip() if first.startswith("#!") else ""
    if not interpreter or not Path(interpreter.split()[0]).exists():
        return 2, f"cannot find Harbor's Python interpreter from {path}"
    code, output = run([*interpreter.split(), "-c", EGRESS_PROBE], timeout=360)
    return (code if code in (0, 1) else 2), output.strip()[-300:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict-tools", action="store_true",
                        help="treat missing or unusable Docker/Harbor/stb as a failure")
    parser.add_argument("--harbor-bin", default="harbor",
                        help="local Harbor executable used for Oracle/NOP (default: 'harbor')")
    args = parser.parse_args(argv)
    errors: list[str] = []
    warnings: list[str] = []
    if sys.version_info < (3, 11):
        errors.append(f"Python 3.11+ required; found {sys.version.split()[0]}. Run 'source .venv/bin/activate' after the README setup.")
    for relative in REQUIRED_PATHS:
        if not (REPO_ROOT / relative).exists():
            errors.append(f"missing repository file: {relative}")

    launcher = shlex.split(args.harbor_bin)
    tools = {"docker": ["docker", "info", "--format", "{{.ServerVersion}}"],
             launcher[0]: [*launcher, "run", "--help"]}
    # stb is only needed for Step 3c model trials; Oracle/NOP run on local Harbor.
    stb_patch = "n/a"
    if not shutil.which("stb"):
        warnings.append("stb not found; Step 3c GPT-5.6 trials are unavailable (Oracle/NOP gates still work)")
    else:
        # Full-fidelity capture (raw API log, lifted observation cap) lives in the Harbor
        # copy bundled inside stb; run_step3c_eval.sh refuses to start without it.
        patched, detail = check_patch()
        stb_patch = "patched" if patched else f"UNPATCHED ({detail})"
        if not patched:
            warnings.append("stb-bundled harbor lacks the full-fidelity patch; Step 3c model trials will be refused "
                            "until you run: python3 scripts/patch_stb_harbor.py (re-run after every stb upgrade)")
        # The key guard (refresh only on budget exhaustion) runs under stb's own interpreter.
        # No network here: this only proves it can load stb's credential helpers.
        code, output = run([sys.executable, str(REPO_ROOT / "scripts" / "stb_key_guard.py"), "--help"])
        if code:
            warnings.append(
                "scripts/stb_key_guard.py cannot load stb's credential helpers; Step 3c rounds will stop before "
                f"the first attempt: {output[-300:].strip()}")
        if (REPO_ROOT / "docs/reference/stb-full-fidelity-kit/stb_key_guard.py").read_bytes() != \
                (REPO_ROOT / "scripts/stb_key_guard.py").read_bytes():
            errors.append("docs/reference/stb-full-fidelity-kit/stb_key_guard.py differs from scripts/stb_key_guard.py")
    for tool, command in tools.items():
        if not shutil.which(tool):
            message = f"{tool} not found; dynamic task gates are unavailable"
            (errors if args.strict_tools else warnings).append(message)
            continue
        if not args.strict_tools:
            continue
        code, output = run(command)
        if code:
            errors.append(f"{tool} is installed but unusable: {output[-500:].strip()}")
        elif command[-1] == "--help" and "--verifier-env" not in output:
            errors.append(f"{' '.join(launcher)} lacks --verifier-env; per-test selection is unavailable")
    egress = "not checked (use --strict-tools)"
    if args.strict_tools and shutil.which("docker") and shutil.which(launcher[0]):
        code, detail = check_egress_control(launcher[0])
        egress = {0: "supported", 1: "UNSUPPORTED", 2: "unknown"}[code]
        if code == 1:
            errors.append("Harbor's Docker backend cannot enforce network_mode = \"no-network\" on this host "
                          "(egress-control kernel probe failed: the kernel needs nftables fib inet support, "
                          "CONFIG_NFT_FIB_INET). Every TB-Science task declares a no-network verifier "
                          f"(Master #64), so Oracle/NOP trials will fail here. {detail}")
        elif code == 2:
            warnings.append(f"could not verify Harbor's Docker no-network support: {detail}")
    if args.strict_tools and shutil.which("docker"):
        code, context = run(["docker", "context", "show"])
        if code == 0 and context.strip() != "default":
            errors.append(f"docker context is {context.strip()!r}; WSL hosts must use 'default' (native socket)")

    status = "FAIL" if errors else "PASS"
    print(f"Authoring doctor: {status}")
    print(f"Repository: {REPO_ROOT}")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"Docker: {shutil.which('docker') or 'MISSING'}")
    print(f"Harbor (Oracle/NOP): {' '.join(launcher)} -> {shutil.which(launcher[0]) or 'MISSING'}")
    print(f"Harbor Docker no-network verifier (Master #64): {egress}")
    print(f"stb (Step 3c model trials only): {shutil.which('stb') or 'MISSING'}; bundled harbor full-fidelity patch: {stb_patch}")
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"FAIL: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
