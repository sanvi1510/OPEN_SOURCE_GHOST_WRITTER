"""
Shared data models for Open-Source Ghostwriter.

Provides Pydantic models and dataclasses used across modules so that
types are explicit and validated rather than raw dicts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


# ── Sandbox result ──────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class SandboxResult:
    """Immutable result of a Docker sandbox execution."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1

    @property
    def success(self) -> bool:
        """Return ``True`` when the code block exited cleanly."""
        return self.exit_code == 0


# ── Webhook payload ─────────────────────────────────────────────────────────

class _PRRef(BaseModel):
    ref: str = ""
    sha: str = ""


class _PRInfo(BaseModel):
    merged: bool = False
    base: _PRRef = Field(default_factory=_PRRef)
    head: _PRRef = Field(default_factory=_PRRef)


class _RepoInfo(BaseModel):
    clone_url: str = ""


class WebhookPayload(BaseModel):
    """Typed representation of a GitHub ``pull_request`` webhook payload.

    Only the fields required by the workflow are modelled.  Unknown fields
    are silently ignored (Pydantic default behaviour).
    """

    action: str = ""
    pull_request: _PRInfo = Field(default_factory=_PRInfo)
    repository: _RepoInfo = Field(default_factory=_RepoInfo)

    @property
    def is_merged_pr(self) -> bool:
        """Return ``True`` if this event represents a merged pull request."""
        return self.action == "closed" and self.pull_request.merged

    @property
    def clone_url(self) -> str:
        return self.repository.clone_url

    @property
    def branch(self) -> str:
        return self.pull_request.base.ref

    @property
    def base_sha(self) -> str:
        return self.pull_request.base.sha

    @property
    def head_sha(self) -> str:
        return self.pull_request.head.sha
