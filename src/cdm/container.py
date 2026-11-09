"""Start and stop the Oracle container with Docker Compose (docker-compose.yml, ADR 0009).

Plain `docker compose` commands run through subprocess, so the same `uv run cdm oracle up`
works on Linux, macOS and Windows. Docker must be installed and running: Docker Engine on
Linux (docs/qa/m4-oracle-source.md), Docker Desktop on Windows and macOS.
"""

from __future__ import annotations

import shutil
import subprocess

from cdm import settings

DOCKER_MISSING = (
    "Docker is not installed or not on PATH. On Ubuntu: "
    "`sudo apt install -y docker.io docker-compose-v2` (see docs/qa/m4-oracle-source.md). "
    "On Windows or macOS: install Docker Desktop "
    "(https://docs.docker.com/desktop/), start it and open a new terminal. "
    "Then run the command again."
)
DOCKER_NOT_RUNNING = (
    "Docker is installed but not running. On Ubuntu: `sudo systemctl start docker`. "
    'On Windows or macOS: start Docker Desktop and wait until it says "Engine running". '
    "Then run the command again."
)
DOCKER_NO_PERMISSION = (
    "Your user cannot use Docker yet (permission denied on the Docker socket). On Ubuntu: "
    "`sudo usermod -aG docker $USER`, then log out and log in again, then run the command again."
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
        if "permission denied" in (probe.stderr or "").lower():
            raise DockerError(DOCKER_NO_PERMISSION)
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
