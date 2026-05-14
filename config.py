"""
Centralized configuration module for Open-Source Ghostwriter.

Uses Pydantic BaseSettings to read all configuration from environment
variables (or a .env file), providing validation and type safety.
"""

from __future__ import annotations

import logging

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    # ── GitHub ──────────────────────────────────────────────────────────
    github_webhook_secret: str = Field(
        ...,
        description="Secret used to validate GitHub webhook HMAC-SHA256 signatures.",
    )
    github_token: str = Field(
        ...,
        description="Personal access token (PAT) for GitHub API & git push.",
    )

    # ── LLM ─────────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key. Provide this OR another LLM key.",
    )
    google_api_key: str = Field(
        default="",
        description="Google AI Studio API key for Gemini models.",
    )
    groq_api_key: str = Field(
        default="",
        description="Groq API key for fast LLM inference.",
    )
    analyzer_provider: str = Field(
        default="groq",
        description="LLM provider for the Analyzer node (e.g. groq, google, anthropic)."
    )
    analyzer_model: str = Field(
        default="llama-3.1-8b-instant",
        description="Fast, cheap model for analyzing diffs."
    )
    writer_provider: str = Field(
        default="groq",
        description="LLM provider for the Writer node."
    )
    writer_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Advanced reasoning model for writing documentation."
    )

    # ── Paths & Sandbox ─────────────────────────────────────────────────
    clone_dir: str = Field(
        default="/tmp/ghostwriter_repos",
        description="Local directory used for cloning repositories.",
    )
    docker_image: str = Field(
        default="python:3.11-slim",
        description="Docker image name for the code-execution sandbox.",
    )

    # ── Behaviour ───────────────────────────────────────────────────────
    max_retries: int = Field(
        default=3,
        description="Maximum number of writer ↔ tester retry cycles.",
    )
    max_diff_chars: int = Field(
        default=50_000,
        description="Maximum diff size (in characters) forwarded to the LLM.",
    )
    llm_request_timeout: int = Field(
        default=120,
        description="Timeout in seconds for a single LLM API request.",
    )

    # ── Validators ──────────────────────────────────────────────────────
    @model_validator(mode="after")
    def _require_at_least_one_llm_key(self) -> "Settings":
        """Ensure at least one LLM API key is configured."""
        if not self.anthropic_api_key and not self.google_api_key and not self.groq_api_key:
            raise ValueError(
                "At least one of ANTHROPIC_API_KEY, GOOGLE_API_KEY, or GROQ_API_KEY must be set."
            )
        return self

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


def _mask(value: str, visible: int = 4) -> str:
    """Return a masked version of a secret string for safe logging."""
    if len(value) <= visible:
        return "****"
    return value[:visible] + "****"


# Singleton instance – import this wherever settings are needed.
settings = Settings()


def configure_logging() -> None:
    """Set up structured logging for the application.

    Called once during startup from ``app/main.py``.
    """
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        ),
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("docker").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(
        "Configuration loaded  analyzer_provider=%s  analyzer_model=%s  "
        "writer_provider=%s  writer_model=%s  clone_dir=%s  max_retries=%d  "
        "anthropic_key=%s  google_key=%s  groq_key=%s",
        settings.analyzer_provider,
        settings.analyzer_model,
        settings.writer_provider,
        settings.writer_model,
        settings.clone_dir,
        settings.max_retries,
        _mask(settings.anthropic_api_key) if settings.anthropic_api_key else "(not set)",
        _mask(settings.google_api_key) if settings.google_api_key else "(not set)",
        _mask(settings.groq_api_key) if settings.groq_api_key else "(not set)",
    )
