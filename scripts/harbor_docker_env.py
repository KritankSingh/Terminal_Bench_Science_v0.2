"""Docker environment for Harbor subprocesses on WSL/Linux hosts."""

from __future__ import annotations

import os

NATIVE_DOCKER_HOST = "unix:///var/run/docker.sock"

# Docker Desktop WSL2 socket paths (in order of preference)
DOCKER_DESKTOP_SOCKETS = [
    # Primary: Ubuntu-22.04 bind mount (most reliable)
    "unix:///mnt/wsl/docker-desktop-bind-mounts/Ubuntu-22.04/docker.sock",
    # Fallback: shared sockets
    "unix:///mnt/wsl/docker-desktop/shared-sockets/guest-services/docker.proxy.sock",
    "unix:///mnt/wsl/docker-desktop/shared-sockets/guest-services/Ubuntu-22.04.docker.container-proxy.sock",
]


def _find_working_socket() -> str | None:
    """Prefer native Linux engine; fall back to Docker Desktop WSL bind mounts."""
    if os.path.exists("/var/run/docker.sock"):
        return NATIVE_DOCKER_HOST
    for sock_path in DOCKER_DESKTOP_SOCKETS:
        if os.path.exists(sock_path.removeprefix("unix://")):
            return sock_path
    return None


def harbor_env() -> dict[str, str]:
    """Return env for `harbor run` that avoids broken Docker Desktop WSL bridges."""
    env = os.environ.copy()

    if "DOCKER_HOST" in env:
        return env

    if env.get("DOCKER_CONTEXT") == "desktop-linux":
        env.pop("DOCKER_CONTEXT", None)
    elif "DOCKER_CONTEXT" in env:
        return env

    working_socket = _find_working_socket()
    if working_socket:
        env["DOCKER_HOST"] = working_socket

    return env
