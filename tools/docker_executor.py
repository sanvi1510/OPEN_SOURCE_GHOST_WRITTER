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

_LANGUAGE_IMAGE_MAP: dict[str, str] = {
    "javascript": "node:20-slim",
    "bash": "python:3.11-slim",
    "makefile": "buildpack-deps:bookworm-scm",
    "ruby": "ruby:3.2-slim",
    "go": "golang:1.22-bullseye",
    "php": "php:8.2-cli",
    "java": "openjdk:21-slim",
    "c": "gcc:13.2",
    "cpp": "gcc:13.2",
    "rust": "rust:1.82-slim",
    "kotlin": "openjdk:21-slim",
    "scala": "hseeberger/scala-sbt:11.0.19_2.13.12_1.9.20",
    "csharp": "mcr.microsoft.com/dotnet/sdk:8.0",
}


def _get_docker_client() -> docker.DockerClient:
    """Return (and cache) a Docker client connected to the local daemon."""
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def _get_image(language: str) -> str:
    if language == "python":
        return settings.docker_image
    return _LANGUAGE_IMAGE_MAP.get(language, settings.docker_image)


def _build_command(code: str, language: str) -> list[str]:
    if language == "python":
        return ["python", "-c", code]
    if language == "javascript":
        return ["node", "-e", code]
    if language == "bash":
        return ["bash", "-lc", code]
    if language == "ruby":
        return ["ruby", "-e", code]
    if language == "go":
        return [
            "bash",
            "-lc",
            "cat > /tmp/main.go <<'EOF'\n" + code + "\nEOF\ngo run /tmp/main.go",
        ]
    if language == "php":
        return ["php", "-r", code]
    if language == "java":
        return [
            "bash",
            "-lc",
            "cat > /tmp/Main.java <<'EOF'\n" + code + "\nEOF\njavac /tmp/Main.java && java -cp /tmp Main",
        ]
    if language == "makefile":
        return [
            "bash",
            "-lc",
            "cat > /tmp/Makefile <<'EOF'\n" + code + "\nEOF\nmake -f /tmp/Makefile",
        ]
    if language == "c":
        return [
            "bash",
            "-lc",
            "cat > /tmp/main.c <<'EOF'\n" + code + "\nEOF\ngcc /tmp/main.c -o /tmp/main && /tmp/main",
        ]
    if language == "cpp":
        return [
            "bash",
            "-lc",
            "cat > /tmp/main.cpp <<'EOF'\n" + code + "\nEOF\ng++ /tmp/main.cpp -o /tmp/main && /tmp/main",
        ]
    if language == "rust":
        return [
            "bash",
            "-lc",
            "cat > /tmp/main.rs <<'EOF'\n" + code + "\nEOF\nrustc /tmp/main.rs -o /tmp/main && /tmp/main",
        ]
    if language == "kotlin":
        return [
            "bash",
            "-lc",
            "cat > /tmp/Main.kt <<'EOF'\n" + code + "\nEOF\nkotlinc /tmp/Main.kt -include-runtime -d /tmp/Main.jar && java -jar /tmp/Main.jar",
        ]
    if language == "scala":
        return [
            "bash",
            "-lc",
            "cat > /tmp/Main.scala <<'EOF'\n" + code + "\nEOF\nscala /tmp/Main.scala",
        ]
    if language == "csharp":
        return [
            "bash",
            "-lc",
            "cat > /tmp/Main.cs <<'EOF'\n" + code + "\nEOF\ndotnet script /tmp/Main.cs",
        ]
    raise ValueError(f"Unsupported language: {language}")


def run_code_in_sandbox(code: str, language: str = "python", repo_path: str = "") -> SandboxResult:
    """Execute a code snippet inside an isolated Docker container."""
    client = _get_docker_client()
    container = None

    image = _get_image(language)
    command = _build_command(code, language)

    # Build optional volumes and environment for repo access.
    volumes: dict[str, dict[str, str]] = {}
    environment: dict[str, str] = {}
    if repo_path:
        volumes[repo_path] = {"bind": "/sandbox/repo", "mode": "ro"}
        environment["PYTHONPATH"] = "/sandbox/repo"

    try:
        container = client.containers.run(
            image=image,
            command=command,
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
            f"Docker image '{image}' not found. "
            "Pull or build the required runtime image before retrying."
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

    except ValueError as exc:
        logger.error("Unsupported language: %s", exc)
        return SandboxResult(stderr=str(exc), exit_code=1)

    except Exception as exc:
        logger.exception("Unexpected sandbox error")
        return SandboxResult(stderr=str(exc), exit_code=1)

    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                logger.warning("Failed to remove container %s", container.id)
