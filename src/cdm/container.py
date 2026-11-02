"""Start and stop the Oracle container with Docker Compose (docker-compose.yml, ADR 0009).

Plain `docker compose` commands run through subprocess, so the same `uv run cdm oracle up`
works in PowerShell, macOS and Linux. Docker Desktop must be installed and running.
"""

from __future__ import annotations

import shutil
import subprocess

from cdm import settings

DOCKER_MISSING = (
    "Docker is not installed or not on PATH. Install Docker Desktop "
    "(https://docs.docker.com/desktop/setup/install/windows-install/), start it, open a new "
    "PowerShell window and run the command again."
)
DOCKER_NOT_RUNNING = (
    "Docker is installed but not running. Start Docker Desktop, wait until it says "
    '"Engine running", then run the command again.'
)


class DockerError(RuntimeError):
    """Docker is missing or not running; the message says what to do."""


def _compose(*args: str) -> list[str]:
    compose_file = settings.project_root() / "docker-compose.yml"
    return ["docker", "compose", "--file", str(compose_file), *args]


def check_docker() -> None:
    if shutil.which("docker") is None:
        raise DockerError(DOCKER_MISSING)
    probe = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if probe.returncode != 0:
        raise DockerError(DOCKER_NOT_RUNNING)


def up() -> int:
    """Start the container and wait until its health check passes."""
    check_docker()
    return subprocess.run(
        _compose("up", "--detach", "--wait"), cwd=settings.project_root()
    ).returncode


def down(delete_data: bool = False) -> int:
    check_docker()
    args = ["down", "--volumes"] if delete_data else ["down"]
    return subprocess.run(_compose(*args), cwd=settings.project_root()).returncode
