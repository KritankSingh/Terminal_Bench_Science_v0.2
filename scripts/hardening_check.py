#!/usr/bin/env python3
"""Conservative static checks for the hardened Terminal-Bench Science workflow.

This tool catches mechanical hazards named by MASTER_CHECKLIST_TBSCI.md (the source of
truth; check numbers are cited as ``Master #N``). It does not replace Harbor checks,
negative-control execution, paper review, trajectory analysis, or the per-task
``authoring/<task>/master-checklist.md`` record.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


DELIVERY_TIMEOUT_SEC = 28800
# Master #13: literal hint-comment grep across environment/ and solution/. The upper-case
# markers are matched case-sensitively so a "todo" product domain is not flagged.
HINT_PATTERNS = (
    re.compile(r"\bTODO\b"),
    re.compile(r"\bFIXME\b"),
    re.compile(r"\bBUG:"),
    re.compile(r"\bplanted\b", re.I),
    re.compile(r"\bdeliberate(?:ly)?\b", re.I),
    re.compile(r"\bfor the grader\b", re.I),
    re.compile(r"\bfor the tests?\b", re.I),
)
# Master #16: opaque letter+digit codes (k7, t2, w0, qp7) naming code that does real work.
OPAQUE_NAME_RE = re.compile(r"^[A-Za-z]{1,2}\d{1,2}$")
OPAQUE_NAME_ALLOWED = re.compile(r"^(?:v\d+|s3|mp[34]|py[23]|q[1-4]|x64)$", re.I)
CODE_SUFFIXES = {
    ".py", ".c", ".h", ".cc", ".cpp", ".hpp", ".go", ".rs", ".js", ".mjs", ".ts", ".java",
    ".cs", ".rb", ".sh", ".php", ".kt", ".scala", ".swift", ".lua", ".pl", ".r", ".jl",
}
TEXT_SCAN_LIMIT = 4 * 1024 * 1024
ENV_TOTAL_LIMIT = 100 * 1024 * 1024
ENV_FILE_LIMIT = 50 * 1024 * 1024
# Master #26: apt packages are installed WITHOUT version pins; language packages WITH
# exact pins. Tokens after these installers are package specs.
PIP_INSTALL_RE = re.compile(r"\b(?:pip3?|python3?\s+-m\s+pip|uv\s+pip)\s+install\b(?P<args>[^;&|]*)")
NPM_GLOBAL_RE = re.compile(r"\b(?:npm\s+(?:install|i)|pnpm\s+add|yarn\s+(?:global\s+)?add)\b(?P<args>[^;&|]*)")
CARGO_INSTALL_RE = re.compile(r"\bcargo\s+install\b(?P<args>[^;&|]*)")
GEM_INSTALL_RE = re.compile(r"\bgem\s+install\b(?P<args>[^;&|]*)")
APT_INSTALL_RE = re.compile(r"\bapt(?:-get)?\s+install\b(?P<args>[^;&|]*)")
# Master #106 (upstream check-nproc.sh): bare `nproc` returns the HOST cpu count inside a
# container; `nproc --all` / `nproc --help` are intentional and allowed.
NPROC_RE = re.compile(r"(?<![\w-])nproc\b(?!\s+--(?:all|help)\b)")
# Master #38 (absorbs former #105; upstream check-trial-network-fetch.sh): trial-time fetches in tests/test.sh.
TRIAL_FETCH_RE = re.compile(
    r"\bbash\s+<\(\s*(?:curl|wget)|\b(?:curl|wget)\b[^\n|]*\|\s*(?:ba|z)?sh\b|"
    r"\b(?:curl|wget)\b[^\n]*https?://[A-Za-z0-9-]+\.[A-Za-z0-9.-]+|\bgit\s+clone\s+(?:https?://|git@)")
# Master #24/#106 (upstream check-dockerfile-references.sh).
ENV_DOCKERFILE_FORBIDDEN_REFS = ("solution/solve.sh", "solve.sh", "tests/test.sh", "test.sh", "test_")
VERIFIER_NETWORK_MODES = ("no-network", "allowlist")


@dataclass
class Finding:
    severity: str
    path: str
    message: str


class Check:
    def __init__(self, root: Path, require_workflow: bool) -> None:
        self.root = root
        self.repo = Path(__file__).resolve().parents[1]
        self.require_workflow = require_workflow
        self.findings: list[Finding] = []

    def add(self, severity: str, path: Path | str, message: str) -> None:
        try:
            display = str(Path(path).relative_to(self.repo))
        except (TypeError, ValueError):
            display = str(path)
        self.findings.append(Finding(severity, display, message))

    def text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            self.add("ERROR", path, f"cannot read text: {exc}")
            return ""

    def required_files(self) -> None:
        required = [
            "task.toml",
            "instruction.md",
            "environment/Dockerfile",
            "solution/solve.sh",
            "tests/Dockerfile",
            "tests/test.sh",
            "tests/test_outputs.py",
        ]
        for rel in required:
            if not (self.root / rel).is_file():
                self.add("ERROR", self.root / rel, "required file is missing")

    def toml(self) -> None:
        path = self.root / "task.toml"
        if not path.is_file():
            return
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            self.add("ERROR", path, f"invalid TOML: {exc}")
            return

        artifacts = data.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            self.add("ERROR", path, "top-level artifacts must be a non-empty list")
        else:
            for artifact in artifacts:
                if not isinstance(artifact, str) or not artifact.startswith("/app/"):
                    self.add("ERROR", path, f"artifact must be an absolute /app path: {artifact!r}")

        verifier = data.get("verifier", {})
        if verifier.get("environment_mode") != "separate":
            self.add("ERROR", path, '[verifier].environment_mode must be "separate" (Master #37, #63)')
        if "artifacts" in verifier:
            self.add("ERROR", path, "artifacts is nested under [verifier], where it is silently dropped; "
                                    "make it a top-level key (Master #37, #61)")

        # Master #63: 28800 on every task, deliberately -- from creation, not raised at
        # packaging -- so a shipped failure is a rule violation, never the clock.
        for section, key in (("agent", "timeout_sec"), ("verifier", "timeout_sec"),
                             ("environment", "build_timeout_sec")):
            table = data.get(section, {})
            value = table.get(key) if isinstance(table, dict) else None
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value != DELIVERY_TIMEOUT_SEC:
                self.add("ERROR", path, f"[{section}].{key} must be {DELIVERY_TIMEOUT_SEC} (Master #63); got {value!r}")

        metadata = data.get("metadata", {})
        tags = metadata.get("tags")
        if not isinstance(tags, list) or not 3 <= len(tags) <= 6:
            self.add("ERROR", path, "[metadata].tags must contain 3–6 entries")
        if "number_of_milestones" in data or "number_of_milestones" in metadata:
            self.add("ERROR", path, "milestone fields are not supported")
        if "is_multi_container" in metadata and metadata["is_multi_container"] is not True:
            self.add("ERROR", path, "is_multi_container must be true when present; omit it otherwise")

        # Master #64 (absorbs former #105; upstream check-allow-internet.sh): the network policy is DECLARED
        # on both phases -- Harbor defaults an omitted one to "public".
        environment = data.get("environment", {})
        if not isinstance(environment, dict):
            environment = {}
        if environment.get("network_mode") != "public":
            self.add("ERROR", path, '[environment].network_mode must be declared "public": the agent phase runs '
                                    "with open internet; difficulty never comes from cutting the network "
                                    f"(Master #64); got {environment.get('network_mode')!r}")
        if "allow_internet" in environment:
            self.add("ERROR", path, "[environment].allow_internet is deprecated; declare network_mode instead (Master #64)")
        verifier_env = verifier.get("environment", {}) if isinstance(verifier, dict) else {}
        if not isinstance(verifier_env, dict):
            verifier_env = {}
        vmode = verifier_env.get("network_mode")
        if vmode not in VERIFIER_NETWORK_MODES:
            self.add("ERROR", path, '[verifier.environment].network_mode must be declared "no-network" (or a '
                                    "justified \"allowlist\" with allowed_hosts): the verifier grades agent code "
                                    f"and must not reach the network (Master #64); got {vmode!r}")
        elif vmode == "allowlist":
            hosts = verifier_env.get("allowed_hosts")
            if not isinstance(hosts, list) or not hosts:
                self.add("ERROR", path, '[verifier.environment].network_mode = "allowlist" needs a non-empty '
                                        "allowed_hosts list (Master #64)")
            else:
                self.add("WARN", path, "verifier network allowlist in use; record the justification in "
                                       "authoring/<task>/resource-plan.md (Master #64)")
        if "allow_internet" in verifier_env:
            self.add("ERROR", path, "[verifier.environment].allow_internet is deprecated; declare network_mode (Master #64)")

    def dockerfiles(self) -> None:
        paths = list(self.root.glob("**/Dockerfile"))
        for path in paths:
            content = self.text(path)
            for number, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if re.match(r"^FROM\s+--platform=", stripped, re.I):
                    self.add("ERROR", path, f"line {number}: FROM --platform pin is not portable")
                if re.match(r"^FROM\s+", stripped, re.I) and "@sha256:" not in stripped:
                    self.add("ERROR", path, f"line {number}: base image is not digest pinned")
                if re.search(r"(?:^|[:/@])latest(?:\s|$)", stripped, re.I):
                    self.add("ERROR", path, f"line {number}: mutable latest reference")
            if "-march=native" in content:
                self.add("ERROR", path, "-march=native creates host-specific behavior")
            if "/var/run/docker.sock" in content or re.search(r"\bprivileged\b", content, re.I):
                self.add("ERROR", path, "privileged/Docker-socket dependency is forbidden")

        env_dockerfile = self.root / "environment/Dockerfile"
        if env_dockerfile.is_file():
            content = self.text(env_dockerfile)
            for forbidden in ("COPY tests", "COPY solution", "ADD tests", "ADD solution"):
                if re.search(rf"(?im)^\s*{re.escape(forbidden)}(?:/|\s)", content):
                    self.add("ERROR", env_dockerfile, f"agent image leaks reserved content: {forbidden}")
            for number, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if re.search(r"(?<![A-Za-z0-9_])/(?:tests|solution|oracle|logs/verifier|logs/artifacts)(?:/|\s|$)", stripped):
                    self.add(
                        "ERROR",
                        env_dockerfile,
                        f"line {number}: agent Dockerfile touches a Harbor-reserved path "
                        "(/tests, /solution, /oracle, /logs/verifier, /logs/artifacts; Master #24)",
                    )
            for tool in ("tmux", "asciinema"):
                if not re.search(rf"\b(?:install|add)\b[^\n]*\b{tool}\b", self._joined_runs(content)):
                    self.add("ERROR", env_dockerfile, f"required tool is not installed explicitly: {tool} (Master #26)")
            for command in self._run_commands(content):
                for match in APT_INSTALL_RE.finditer(command):
                    pinned = [token for token in match.group("args").split()
                              if not token.startswith("-") and re.match(r"^[A-Za-z0-9][\w.+-]*=\S+$", token)]
                    if pinned:
                        self.add("ERROR", env_dockerfile,
                                 f"apt packages must be installed WITHOUT version pins (Master #26): {', '.join(pinned)}")
            uncommented = "\n".join(line for line in content.splitlines() if not line.strip().startswith("#"))
            for forbidden in ENV_DOCKERFILE_FORBIDDEN_REFS:
                pattern = (r"(?<![\w/.-])test_[\w-]*\.py\b" if forbidden == "test_"
                           else rf"(?<![\w.-]){re.escape(forbidden)}\b")
                if re.search(pattern, uncommented):
                    self.add("ERROR", env_dockerfile, f"agent Dockerfile references {forbidden!r}: it must never COPY "
                                                      "or name solution/test files (upstream "
                                                      "check-dockerfile-references.sh, Master #24, #106)")
                    break
        for path in paths:
            commands = self._run_commands(self.text(path))
            joined = " && ".join(commands)
            if APT_INSTALL_RE.search(joined):
                if not re.search(r"\bapt(?:-get)?\s+update\b", joined):
                    self.add("ERROR", path, "apt install without apt-get update (upstream check-dockerfile-sanity.sh, "
                                            "Master #106)")
                if "rm -rf /var/lib/apt/lists" not in joined:
                    self.add("ERROR", path, "apt install without 'rm -rf /var/lib/apt/lists/*' cleanup (upstream "
                                            "check-dockerfile-sanity.sh, Master #106)")
        for path in paths:
            for command in self._run_commands(self.text(path)):
                for problem in self._unpinned_language_packages(path, command):
                    self.add("ERROR", path, f"{problem} (Master #26, #38)")
        self.environment_size()

    @staticmethod
    def _run_commands(content: str) -> list[str]:
        """RUN instructions with backslash continuations joined, comments dropped."""
        commands: list[str] = []
        current: list[str] | None = None
        for raw in content.splitlines():
            line = raw.strip()
            if current is None:
                if not re.match(r"^RUN\b", line, re.I):
                    continue
                current = []
                line = line[3:].strip()
            if line.startswith("#"):
                continue
            continued = line.endswith("\\")
            current.append(line[:-1] if continued else line)
            if not continued:
                commands.append(" ".join(current))
                current = None
        if current:
            commands.append(" ".join(current))
        return commands

    def _joined_runs(self, content: str) -> str:
        return "\n".join(self._run_commands(content))

    def _unpinned_language_packages(self, dockerfile: Path, command: str) -> list[str]:
        problems: list[str] = []

        def specs(args: str, value_options: set[str]) -> list[str]:
            out, skip = [], False
            for token in args.split():
                if skip:
                    skip = False
                    continue
                if token in value_options:
                    skip = True
                    continue
                if token.startswith(("-", "$")):
                    continue
                out.append(token.strip("'\""))
            return out

        def local(token: str) -> bool:
            return (token.startswith((".", "/", "~")) or "://" in token
                    or token.endswith((".whl", ".tar.gz", ".zip", ".tgz", ".gem", ".crate")))

        pip_values = {"-r", "--requirement", "-c", "--constraint", "-e", "--editable", "-i",
                      "--index-url", "--extra-index-url", "-f", "--find-links", "-t", "--target",
                      "--prefix", "--root", "--platform", "--python-version", "--only-binary",
                      "--no-binary", "--progress-bar", "--cache-dir", "--src"}
        npm_values = {"--registry", "--prefix", "--cache", "--tag", "-w", "--workspace"}
        for match in PIP_INSTALL_RE.finditer(command):
            args = match.group("args")
            for requirement in re.findall(r"(?:-r|--requirement)\s+(\S+)", args):
                problems += self._unpinned_requirements(dockerfile, requirement.strip("'\""))
            for token in specs(args, pip_values):
                if not local(token) and "==" not in token:
                    problems.append(f"pip package is not pinned to an exact version (use ==): {token}")
        for match in NPM_GLOBAL_RE.finditer(command):
            for token in specs(match.group("args"), npm_values):
                if local(token):
                    continue
                body = token[1:] if token.startswith("@") else token
                version = body.rpartition("@")[2] if "@" in body else ""
                if not re.match(r"^\d+\.\d+\.\d+", version):
                    problems.append(f"npm/yarn/pnpm package is not pinned to an exact version (use name@x.y.z): {token}")
        for match in CARGO_INSTALL_RE.finditer(command):
            if not re.search(r"--version\s+=?\d|--locked|@\d", match.group("args")):
                problems.append("cargo install without an exact --version pin")
        for match in GEM_INSTALL_RE.finditer(command):
            if not re.search(r"(?:-v|--version)\s+['\"]?\d", match.group("args")):
                problems.append("gem install without an exact -v pin")
        return problems

    def _unpinned_requirements(self, dockerfile: Path, requirement: str) -> list[str]:
        context = dockerfile.parent
        candidates = []
        # Follow the Dockerfile's own COPY/ADD lines: `COPY deps/req.txt /tmp/r.txt`.
        for match in re.finditer(r"(?im)^\s*(?:COPY|ADD)\s+(?!--from)(?:--\S+\s+)*(.+)$", self.text(dockerfile)):
            tokens = match.group(1).split()
            if len(tokens) < 2:
                continue
            *sources, dest = tokens
            for source in sources:
                if requirement == dest or (dest.endswith("/") and requirement == dest + Path(source).name):
                    candidates.append(context / source)
                elif dest.endswith("/") and requirement.startswith(dest) and (context / source).is_dir():
                    candidates.append(context / source / requirement[len(dest):])
        candidates += [context / requirement.lstrip("/"), context / Path(requirement).name]
        candidates += sorted(context.rglob(Path(requirement).name))
        source = next((c for c in candidates if c.is_file()), None)
        if source is None:
            return [f"cannot verify pins: requirements file {requirement} is not in the build context"]
        problems = []
        for raw in self.text(source).splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            if "==" not in line and "@" not in line:
                problems.append(f"{source.name}: requirement is not pinned with ==: {line}")
        return problems

    def environment_size(self) -> None:
        root = self.root / "environment"
        if not root.is_dir():
            return
        total = 0
        for path in root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                size = path.stat().st_size
                total += size
                if size > ENV_FILE_LIMIT:
                    self.add("ERROR", path, f"file is {size / 1048576:.1f} MiB; no file under environment/ may exceed 50 MiB (Master #26)")
        if total > ENV_TOTAL_LIMIT:
            self.add("ERROR", root, f"environment/ is {total / 1048576:.1f} MiB; the limit is 100 MiB (Master #26)")

    def compose(self) -> None:
        for path in list(self.root.glob("**/docker-compose.y*ml")) + list(self.root.glob("**/compose.y*ml")):
            content = self.text(path)
            if "/var/run/docker.sock" in content or re.search(r"(?m)^\s*privileged\s*:\s*true", content):
                self.add("ERROR", path, "privileged/Docker-socket compose configuration")
            for number, line in enumerate(content.splitlines(), 1):
                if re.search(r"^\s*-\s*['\"]?(?:\.|/|~|[A-Za-z]:[\\/]).*:\s*/", line) or re.search(
                        r"^\s*(?:-\s*)?type\s*:\s*['\"]?bind\b", line):
                    self.add("ERROR", path, f"line {number}: host bind mount; use a named volume (upstream "
                                            "check-compose-host-binds.sh, Master #106)")
                if re.search(r"^\s*image\s*:", line) and "@sha256:" not in line:
                    self.add("ERROR", path, f"line {number}: compose image is not digest pinned")

            services = self._compose_services(content)
            if len(services) >= 2:
                task_toml = self.root / "task.toml"
                try:
                    task_data = tomllib.loads(task_toml.read_text(encoding="utf-8"))
                    tagged = task_data.get("metadata", {}).get("is_multi_container") is True
                except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
                    tagged = False
                if not tagged:
                    self.add(
                        "ERROR",
                        task_toml,
                        f"compose defines {len(services)} services but is_multi_container=true is missing",
                    )

    @staticmethod
    def _compose_services(content: str) -> list[str]:
        lines = content.splitlines()
        for index, line in enumerate(lines):
            match = re.match(r"^(\s*)services\s*:\s*(?:#.*)?$", line)
            if not match:
                continue
            base = len(match.group(1))
            services: list[str] = []
            for candidate in lines[index + 1 :]:
                if not candidate.strip() or candidate.lstrip().startswith("#"):
                    continue
                indent = len(candidate) - len(candidate.lstrip())
                if indent <= base:
                    break
                service = re.match(r"^\s{%d}([A-Za-z0-9_.-]+)\s*:\s*(?:#.*)?$" % (base + 2), candidate)
                if service:
                    services.append(service.group(1))
            return services
        return []

    def verifier(self) -> None:
        script = self.root / "tests/test.sh"
        if script.is_file():
            content = self.text(script)
            if "/logs/verifier/reward.txt" not in content:
                self.add("ERROR", script, "reward.txt is never written")
            if "ctrf" not in content.lower():
                self.add("ERROR", script, "CTRF output is not evident")
            if re.search(r"(?im)^\s*(?:pip|pip3|uvx|uv\s+pip|apt-get|curl|wget)\b", content):
                self.add("ERROR", script, "trial-time install/fetch detected; bake verifier dependencies")
            fetch = TRIAL_FETCH_RE.search("\n".join(l for l in content.splitlines() if not l.strip().startswith("#")))
            if fetch:
                self.add("ERROR", script, f"trial-time network fetch {fetch.group(0)[:60]!r}; bake it into "
                                          "tests/Dockerfile (upstream check-trial-network-fetch.sh, Master #38)")
            if re.search(r"(?m)^\s*set\s+(?:-[a-df-zA-Z]*e|-[a-zA-Z]*\s+-[a-df-zA-Z]*e)|^\s*set\s+-o\s+errexit", content):
                self.add("ERROR", script, "set -e/errexit is banned in tests/test.sh: a failing run must still reach "
                                          "the reward write (Master #39)")
            commands = [line.strip() for line in content.splitlines()
                        if line.strip() and not line.strip().startswith("#")]
            if not commands or commands[-1] != "exit 0":
                self.add("ERROR", script, "tests/test.sh must end with `exit 0`: the reward file, not the exit "
                                          "status, decides pass/fail (Master #39)")
            writes = re.findall(r"echo\s+([^\n]+?)\s*>\s*/logs/verifier/reward\.txt", content)
            if writes and any(not re.search(r"(?:^|\s)[01](?:\s|$)", value) for value in writes):
                self.add("ERROR", script, "non-binary reward write may be present")
            first_reward = content.find("/logs/verifier/reward.txt")
            for number, line in enumerate(content.splitlines(), 1):
                if re.match(r"^\s*exit\b", line) and content.find(line) < first_reward:
                    self.add("ERROR", script, f"line {number}: exits before any reward write")
            self._check_shell_defaults(script, content)

        dockerfile = self.root / "tests/Dockerfile"
        if dockerfile.is_file():
            content = self.text(dockerfile)
            if not re.search(r"(?im)^\s*COPY\s+\.\s+/tests/?\s*$", content):
                self.add("ERROR", dockerfile, "verifier tests are not visibly baked at /tests")
            if not any(re.search(r"\bmkdir\s+-p\s+[^;&|]*?/app\b", command) for command in self._run_commands(content)):
                self.add("ERROR", dockerfile, "artifact parent /app is not pre-created")

        actor_patterns = (
            r"/oracle(?:/|\s|['\"]|$)",
            r"\bEVAL_IS_ORACLE\b",
            r"\bIS_ORACLE\b",
            r"\bORACLE_MODE\b",
            r"\bAGENT_MODE\b",
        )
        latency_patterns = (
            r"\btest_[A-Za-z0-9_]*(?:latency|throughput|performance|timing)",
            r"\b(?:p50|p95|p99|latency|throughput|requests_per_second|wall_time)\b",
            r"\btime\.(?:perf_counter|monotonic|time)\s*\(",
            r"\bpytest\.mark\.benchmark\b",
        )
        for path in self._source_files(self.root / "tests"):
            content = self.text(path)
            # Upstream check-verifier-output.py / check-binary-reward.py: Harbor reads
            # reward.json IN PREFERENCE to reward.txt, so a task writing it is scored on that
            # file; this workflow writes exactly 0/1 to reward.txt only (Master #58).
            if re.search(r"/logs/verifier/reward\.json|['\"]reward\.json['\"]", content):
                self.add("ERROR", path, "writes or names /logs/verifier/reward.json; write only reward.txt "
                                        "(Harbor prefers reward.json over reward.txt; Master #58)")
            for pattern in actor_patterns:
                if re.search(pattern, content, re.I):
                    self.add("ERROR", path, "Oracle/agent-specific verifier logic or /oracle access detected")
                    break
            for pattern in latency_patterns:
                if re.search(pattern, content, re.I):
                    self.add("ERROR", path, "latency/throughput or wall-clock test signal detected")
                    break
            if re.search(r"(?i)oracle[^\n]{0,100}(?:0\.9[5-9]|95\s*%)", content):
                self.add("WARN", path, "possible near-Oracle threshold; require explicit reviewer justification")
            for number, line in enumerate(content.splitlines(), 1):
                if re.search(r"(['\"])[^'\"\n]*\1\s*\+\s*(['\"])[^'\"\n]*\2", line):
                    self.add("WARN", path, f"line {number}: adjacent string literals concatenated with + "
                                           "(grep/similarity obfuscation adds no grading value; Master #49)")
                    break

    def portability(self) -> None:
        """Master #106: no bare `nproc` (upstream check-nproc.sh) in any Dockerfile, test.sh or
        solve.sh; every pip/uv install in solve.sh is pinned (upstream check-pip-pinning.sh --
        Dockerfiles are covered by dockerfiles(), and test.sh may not install at all)."""
        targets = list(self.root.glob("**/Dockerfile")) + [self.root / "tests/test.sh", self.root / "solution/solve.sh"]
        for path in targets:
            if not path.is_file():
                continue
            for number, line in enumerate(self.text(path).splitlines(), 1):
                code = line.split("#", 1)[0] if not line.strip().startswith("#") else ""
                if NPROC_RE.search(code):
                    self.add("ERROR", path, f"line {number}: bare `nproc` returns the HOST cpu count inside a container; "
                                            "use a fixed value sized to [environment].cpus (upstream check-nproc.sh, "
                                            "Master #106)")
        solve = self.root / "solution/solve.sh"
        if solve.is_file():
            lines, current = [], ""
            for raw in self.text(solve).splitlines():
                line = raw.split("#", 1)[0] if not raw.strip().startswith("#") else ""
                if line.rstrip().endswith("\\"):
                    current += line.rstrip()[:-1] + " "
                    continue
                lines.append(current + line)
                current = ""
            for command in lines:
                for problem in self._unpinned_language_packages(solve, command):
                    self.add("ERROR", solve, f"{problem} (upstream check-pip-pinning.sh, Master #106)")

    def _check_shell_defaults(self, path: Path, content: str) -> None:
        refs: set[str] = set()
        for match in re.finditer(r"\$(?:\{([A-Z_][A-Z0-9_]*)[^}]*\}|([A-Z_][A-Z0-9_]*))", content):
            refs.add(match.group(1) or match.group(2))
        exempt = {
            "HOME", "PWD", "OLDPWD", "PATH", "SHELL", "USER", "LOGNAME",
            "UID", "EUID", "GID", "TMPDIR", "LANG", "LC_ALL", "TERM",
            "SHLVL", "RANDOM", "SECONDS", "PIPESTATUS",
        }
        for variable in sorted(refs - exempt):
            if re.search(rf"\$\{{{variable}(?::?-)[^}}]*\}}", content):
                continue
            assignment = re.search(rf"(?m)^\s*(?:export\s+)?{variable}\s*=\s*(.+)$", content)
            if assignment and not re.search(rf"\$(?:{variable}|\{{{variable}(?:\}}|[^}}]*\}}))", assignment.group(1)):
                continue
            self.add(
                "ERROR",
                path,
                f"environment variable {variable} is used without a compatible default",
            )

    @staticmethod
    def _source_files(root: Path) -> list[Path]:
        if not root.is_dir():
            return []
        suffixes = {".sh", ".py", ".js", ".ts", ".go", ".rs", ".java", ".cs", ".rb", ".php"}
        return [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes]

    def runtime_fetches(self) -> None:
        direct_patterns = (
            r"(?m)^\s*(?:curl|wget)\b",
            r"\burllib\.request\.(?:urlopen|urlretrieve)\b",
            r"\brequests\.(?:get|post|request|head)\s*\(",
            r"\bfetch\s*\(",
        )
        generic_client_patterns = (
            r"\bhttp\.(?:Get|Post|Head|NewRequest)\s*\(",
            r"\bclient\.(?:Get|Post|Head|Do)\s*\(",
            r"\bHttpClient\b",
            r"\bopenConnection\s*\(",
        )
        nonlocal_url = r"https?://(?!127\.0\.0\.1(?::|/)|localhost(?::|/)|\[::1\](?::|/))"
        paths = self._source_files(self.root / "solution")
        paths += [path for path in self._source_files(self.root / "environment") if path.name != "Dockerfile"]
        paths += self._source_files(self.root / "tests")
        for path in sorted(set(paths)):
            content = self.text(path)
            direct = any(re.search(pattern, content, re.I) for pattern in direct_patterns)
            generic = any(re.search(pattern, content) for pattern in generic_client_patterns)
            has_nonlocal_url = bool(re.search(nonlocal_url, content, re.I))
            if has_nonlocal_url and (direct or generic):
                self.add("ERROR", path, "runtime web/API fetch signal detected; bundle required data locally")
            elif direct or generic:
                self.add("WARN", path, "network client call detected; verify it is only a local task service")

    def instruction(self) -> None:
        path = self.root / "instruction.md"
        if not path.is_file():
            return
        content = self.text(path)
        if re.search(r"(?m)^#{1,6}\s+", content):
            self.add("WARN", path, "Markdown headings increase prompt ceremony; verify they are necessary")
        if "/app/" not in content:
            self.add("ERROR", path, "no absolute /app path found")
        # Master #104 (upstream check-instruction-suffix.sh) -- the exact match is in task_check.py.
        if not re.search(r"(?m)^You have \d+ seconds to complete this task\. Do not cheat by using online "
                         r"solutions or hints specific to this task\.\s*\Z", content):
            self.add("ERROR", path, "instruction.md does not end with the 'You have N seconds to complete this task. "
                                    "Do not cheat by using online solutions or hints specific to this task.' "
                                    "paragraph (Master #104)")
        if re.search(r"(?i)\b(?:step[- ]by[- ]step|here is how|detection guidance)\b", content):
            self.add("WARN", path, "possible solution-guidance language")

    def _text_files(self, root: Path) -> list[Path]:
        if not root.is_dir():
            return []
        found = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink() or path.stat().st_size > TEXT_SCAN_LIMIT:
                continue
            try:
                head = path.read_bytes()[:8192]
            except OSError:
                continue
            if b"\0" in head:
                continue
            found.append(path)
        return found

    def hint_comments(self) -> None:
        """Master #13: zero hint/intent markers across environment/ and solution/."""
        for root in (self.root / "environment", self.root / "solution"):
            for path in self._text_files(root):
                try:
                    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                except OSError:
                    continue
                for number, line in enumerate(lines, 1):
                    for pattern in HINT_PATTERNS:
                        match = pattern.search(line)
                        if match:
                            self.add("ERROR", path, f"line {number}: hint/intent marker {match.group(0)!r} "
                                                    "(TODO/FIXME/BUG:/planted/deliberate/for the grader/for the test "
                                                    "must not appear; Master #13)")
                            break

    def opaque_names(self) -> None:
        """Master #16: no opaque letter+digit names (k7, t2, w0, qp7) for code under environment/."""
        root = self.root / "environment"
        if not root.is_dir():
            return
        for path in sorted(root.rglob("*")):
            stem = path.name if path.is_dir() else path.stem
            if path.is_file() and path.suffix.lower() not in CODE_SUFFIXES:
                continue
            if OPAQUE_NAME_RE.fullmatch(stem) and not OPAQUE_NAME_ALLOWED.fullmatch(stem):
                self.add("ERROR", path, f"opaque name {stem!r} hides what the code does; name it for its "
                                        "job (Master #16)")

    def repository_hygiene(self) -> None:
        forbidden_names = {"AGENTS.md", "CLAUDE.md", "skills.md", "SOURCE.txt", ".DS_Store"}
        for path in self.root.rglob("*"):
            # Archived Step 3c rounds under trajectories/ are workspace evidence (excluded from
            # the task digest and from task_check's scan); archive_step3c.py records SOURCE.txt
            # there by design, and package_task.py/verify_package.py ban it from the ZIP itself.
            if path.relative_to(self.root).parts[:1] == ("trajectories",):
                continue
            if path.is_file() and path.name in forbidden_names:
                self.add("ERROR", path, "AI/authoring scaffold must not ship in a task")
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                self.add("ERROR", path, "generated cache must not ship")

    def workflow_evidence(self) -> None:
        authoring = self.repo / "authoring" / self.root.name
        required = [
            "seed-review.md",
            "contract.md",
            "traceability.md",
            "threat-model.md",
            "resource-plan.md",
            "controls.md",
        ]
        if not authoring.is_dir():
            severity = "ERROR" if self.require_workflow else "WARN"
            self.add(severity, authoring, "authoring evidence directory is missing")
            return
        for rel in required:
            if not (authoring / rel).is_file():
                severity = "ERROR" if self.require_workflow else "WARN"
                self.add(severity, authoring / rel, "workflow evidence file is missing")

    def collect(self) -> list[Finding]:
        """Run every check and return sorted findings without printing (used by task_check.py)."""
        self.required_files()
        self.toml()
        self.dockerfiles()
        self.compose()
        self.verifier()
        self.portability()
        self.runtime_fetches()
        self.instruction()
        self.hint_comments()
        self.opaque_names()
        self.repository_hygiene()
        self.workflow_evidence()

        order = {"ERROR": 0, "WARN": 1}
        self.findings.sort(key=lambda item: (order.get(item.severity, 9), item.path, item.message))
        return self.findings

    def run(self) -> int:
        self.collect()
        for item in self.findings:
            print(f"[{item.severity}] {item.path}: {item.message}")

        errors = sum(item.severity == "ERROR" for item in self.findings)
        warnings = sum(item.severity == "WARN" for item in self.findings)
        print(f"summary: errors={errors} warnings={warnings}")
        return 1 if errors else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", type=Path, help="path to tasks/<task-name>")
    parser.add_argument(
        "--workflow",
        action="store_true",
        help="require Step 1/2a authoring evidence files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task = args.task.resolve()
    if not task.is_dir():
        print(f"error: task directory does not exist: {task}", file=sys.stderr)
        return 2
    return Check(task, args.workflow).run()


if __name__ == "__main__":
    raise SystemExit(main())
