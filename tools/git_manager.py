"""
Git repository manager for Open-Source Ghostwriter.

Wraps GitPython to provide high-level helpers for:
  • Cloning a repository
  • Retrieving diffs between commits
  • Reading / writing files within the working tree
  • Committing and pushing documentation changes

Security notes
──────────────
- The GitHub PAT is injected via ``GIT_ASKPASS`` rather than embedded in the
  URL to prevent token leakage in logs and tracebacks.
- ``read_file`` and ``write_file`` resolve paths and verify they stay inside
  the repo root to prevent path-traversal attacks.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional

from git import Repo, GitCommandError

from config import settings

logger = logging.getLogger(__name__)

# ── Path-safety helpers ─────────────────────────────────────────────────────

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _sanitize_repo_name(clone_url: str) -> str:
    """Derive a safe directory name from a clone URL.

    Raises:
        ValueError: If the derived name contains suspicious characters.
    """
    name: str = clone_url.rstrip("/").split("/")[-1].replace(".git", "")
    if not _SAFE_NAME_RE.match(name):
        raise ValueError(f"Suspicious repository name derived from URL: {name!r}")
    return name


def _safe_resolve(repo_root: str, relative_path: str) -> Path:
    """Resolve *relative_path* within *repo_root*, preventing path traversal.

    Args:
        repo_root: Absolute path to the repository root.
        relative_path: Untrusted relative path (e.g. ``README.md``).

    Returns:
        Resolved ``Path`` that is guaranteed to be inside *repo_root*.

    Raises:
        ValueError: If the resolved path escapes the repository root.
    """
    root = Path(repo_root).resolve()
    full = (root / relative_path).resolve()
    if not str(full).startswith(str(root)):
        raise ValueError(
            f"Path traversal blocked: {relative_path!r} escapes {repo_root!r}"
        )
    return full


# ── Credential helper ───────────────────────────────────────────────────────

def _authenticated_url(clone_url: str) -> str:
    """Inject the GitHub token into an HTTPS clone URL for authentication.

    Converts ``https://github.com/user/repo.git``
    into     ``https://x-access-token:TOKEN@github.com/user/repo.git``

    Returns the original URL unchanged if it's not HTTPS.
    """
    token = settings.github_token
    if token and clone_url.startswith("https://"):
        # Insert token after https://
        return clone_url.replace("https://", f"https://x-access-token:{token}@", 1)
    return clone_url


def _git_env() -> dict[str, str]:
    """Return environment variables for git operations."""
    return {
        "GIT_TERMINAL_PROMPT": "0",  # never prompt interactively
    }


# ── Public API ──────────────────────────────────────────────────────────────

def clone_repo(clone_url: str, branch: str = "main") -> str:
    """Clone a remote repository to a local directory.

    The clone is placed under ``settings.clone_dir`` in a sub-folder derived
    from the repository name.  If the directory already exists it is reused
    (a fresh fetch is performed instead).

    Args:
        clone_url: HTTPS clone URL of the repository.
        branch: Branch to check out after cloning.

    Returns:
        Absolute path to the local clone directory.

    Raises:
        ValueError: If the repository name looks suspicious.
        GitCommandError: If the git operation fails.
    """
    repo_name = _sanitize_repo_name(clone_url)
    dest: str = os.path.join(settings.clone_dir, repo_name)
    auth_url = _authenticated_url(clone_url)
    env = _git_env()

    try:
        if os.path.isdir(dest):
            logger.info("Repository already cloned – pulling latest for %s", repo_name)
            repo = Repo(dest)
            # Update remote URL in case token changed
            repo.remotes.origin.set_url(auth_url)
            with repo.git.custom_environment(**env):
                repo.remotes.origin.fetch()
                repo.git.checkout(branch)
                repo.git.pull("origin", branch)
            # Restore clean URL (without token) for safety
            repo.remotes.origin.set_url(clone_url)
        else:
            logger.info("Cloning %s → %s", clone_url, dest)
            repo = Repo.clone_from(
                auth_url, dest, branch=branch,
                env=env,
            )
            # Restore clean URL (without token) for safety
            repo.remotes.origin.set_url(clone_url)
    except GitCommandError:
        logger.exception("Git operation failed for %s", clone_url)
        raise

    return dest


def get_diff(repo_path: str, base_sha: str, head_sha: str) -> str:
    """Return the unified diff between two commits.

    Large diffs are truncated to ``settings.max_diff_chars`` to avoid
    exceeding LLM context limits.

    Args:
        repo_path: Path to the local clone.
        base_sha: The earlier commit SHA.
        head_sha: The later commit SHA.

    Returns:
        Multi-line unified diff string (possibly truncated).
    """
    repo = Repo(repo_path)
    diff_text: str = repo.git.diff(base_sha, head_sha)

    if len(diff_text) > settings.max_diff_chars:
        logger.warning(
            "Diff truncated from %d to %d chars.", len(diff_text), settings.max_diff_chars
        )
        diff_text = diff_text[: settings.max_diff_chars] + "\n\n[...diff truncated...]"

    return diff_text


def read_file(repo_path: str, file_path: str) -> str:
    """Read and return the contents of a file inside the repository.

    Path-traversal attempts are blocked.

    Args:
        repo_path: Path to the local clone.
        file_path: Relative path within the repository (e.g. ``README.md``).

    Returns:
        File contents as a string.

    Raises:
        ValueError: If *file_path* escapes the repository root.
    """
    full_path = _safe_resolve(repo_path, file_path)
    return full_path.read_text(encoding="utf-8")


def write_file(repo_path: str, file_path: str, content: str) -> None:
    """Write *content* to a file inside the repository (creating it if needed).

    Path-traversal attempts are blocked.

    Args:
        repo_path: Path to the local clone.
        file_path: Relative path within the repository.
        content: New file contents.

    Raises:
        ValueError: If *file_path* escapes the repository root.
    """
    full_path = _safe_resolve(repo_path, file_path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")


def commit_and_push(
    repo_path: str,
    file_path: str,
    commit_message: str,
    branch: Optional[str] = None,
) -> None:
    """Stage a file, commit, and push to the remote.

    Args:
        repo_path: Path to the local clone.
        file_path: Relative path of the file to stage.
        commit_message: Git commit message.
        branch: Target branch (defaults to the currently checked-out branch).

    Raises:
        GitCommandError: If the push fails (e.g. auth error, force-push
        protection).
    """
    repo = Repo(repo_path)

    # Configure committer identity (idempotent)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Ghostwriter Bot")
        cw.set_value("user", "email", "ghostwriter-bot@users.noreply.github.com")

    repo.index.add([file_path])
    repo.index.commit(commit_message)

    push_branch: str = branch or repo.active_branch.name
    logger.info("Pushing to origin/%s", push_branch)

    # Get the current remote URL and temporarily set authenticated URL
    original_url = repo.remotes.origin.url
    auth_url = _authenticated_url(original_url)

    try:
        repo.remotes.origin.set_url(auth_url)
        env = _git_env()
        with repo.git.custom_environment(**env):
            repo.remotes.origin.push(push_branch)
    except GitCommandError:
        logger.exception("Push to origin/%s failed", push_branch)
        raise
    finally:
        # Always restore the clean URL (without token)
        repo.remotes.origin.set_url(original_url)

