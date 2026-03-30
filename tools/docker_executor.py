"""
Docker sandbox executor for Open-Source Ghostwriter.

Runs Python code snippets inside an ephemeral, network-disabled Docker
container to safely validate documentation examples.

Security hardening
──────────────────
- Networking disabled (``network_mode="none"``).
- Memory capped at 128 MB.
- CPU limited to 50 % of one core.
- PID limit of 50 (prevents fork-bombs).
- Read-only root filesystem with a small tmpfs at ``/tmp``.
- Non-root user inside the container (set in the Dockerfile).
- Container is always removed, even if a timeout or error occurs.
"""

from __future__ import annotations

import logging
from typing import Any

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

from config import settings
from models import SandboxResult

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────────────
_MEMORY_LIMIT: str = "128m"
_TIMEOUT_SECONDS: int = 30
_NETWORK_MODE: str = "none"
_CPU_QUOTA: int = 50_000          # 50 % of one CPU core (period = 100 000)
_PIDS_LIMIT: int = 50
_TMPFS_CONFIG: dict[str, str] = {"/tmp": "size=10m,noexec"}

# Module-level Docker client (reused across calls).
_client: docker.DockerClient | None = None


def _get_docker_client() -> docker.DockerClient:
    """Return (and cache) a Docker client connected to the local daemon."""
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def run_code_in_sandbox(code: str, repo_path: str = "") -> SandboxResult:
    """Execute a Python code snippet inside an isolated Docker container.

    The container is:
      • Memory-limited to 128 MB
      • CPU-limited to 50 % of one core
      • PID-limited to 50
      • Network-disabled
      • Read-only root filesystem (tmpfs at /tmp)
      • Automatically removed after execution (even on error)
      • Subject to a 30-second timeout
      • Optionally mounts the repo (read-only) so project imports work

    Args:
        code: Python source code to execute.
        repo_path: Optional path to the cloned repo. When provided,
                   the repo is bind-mounted read-only at ``/sandbox/repo``
                   and added to ``PYTHONPATH``.

    Returns:
        A ``SandboxResult`` with ``stdout``, ``stderr``, and ``exit_code``.
    """
    client = _get_docker_client()
    container = None

    # Build optional volumes and environment for repo access.
    volumes: dict[str, dict[str, str]] = {}
    environment: dict[str, str] = {}
    if repo_path:
        volumes[repo_path] = {"bind": "/sandbox/repo", "mode": "ro"}
        environment["PYTHONPATH"] = "/sandbox/repo"

    try:
        container = client.containers.run(
            image=settings.docker_image,
            command=["python", "-c", code],
            mem_limit=_MEMORY_LIMIT,
            network_mode=_NETWORK_MODE,
            cpu_quota=_CPU_QUOTA,
            pids_limit=_PIDS_LIMIT,
            read_only=True,
            tmpfs=_TMPFS_CONFIG,
            volumes=volumes or None,
            environment=environment or None,
            stderr=True,
            stdout=True,
            detach=True,
        )

        # Wait for the container to finish (with timeout).
        result = container.wait(timeout=_TIMEOUT_SECONDS)
        exit_code: int = result.get("StatusCode", -1)

        stdout_bytes: bytes = container.logs(stdout=True, stderr=False)
        stderr_bytes: bytes = container.logs(stdout=False, stderr=True)

        return SandboxResult(
            stdout=stdout_bytes.decode("utf-8", errors="replace"),
            stderr=stderr_bytes.decode("utf-8", errors="replace"),
            exit_code=exit_code,
        )

    except ImageNotFound:
        error_msg = (
            f"Docker image '{settings.docker_image}' not found. "
            "Build it with: docker build -t ghostwriter-sandbox sandbox/"
        )
        logger.error(error_msg)
        return SandboxResult(stderr=error_msg, exit_code=1)

    except ContainerError as exc:
        logger.error("Container execution error: %s", exc)
        return SandboxResult(
            stderr=str(exc),
            exit_code=getattr(exc, "exit_status", 1),
        )

    except APIError as exc:
        logger.error("Docker API error: %s", exc)
        return SandboxResult(stderr=str(exc), exit_code=1)

    except Exception as exc:
        # Catch-all: timeout exceptions, connection errors, etc.
        logger.exception("Unexpected sandbox error")
        return SandboxResult(stderr=str(exc), exit_code=1)

    finally:
        # Always clean up the container to prevent orphans.
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                logger.warning("Failed to remove container %s", container.id)
