"""
Unit tests for ``tools.git_manager``.

External dependencies (GitPython, filesystem) are mocked so these tests
run quickly and without side-effects.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools import git_manager
from tools.git_manager import _safe_resolve, _sanitize_repo_name


# ── Path-safety helpers ─────────────────────────────────────────────────────

class TestSanitizeRepoName:
    """Tests for ``_sanitize_repo_name``."""

    def test_normal_url(self) -> None:
        assert _sanitize_repo_name("https://github.com/user/my-repo.git") == "my-repo"

    def test_url_without_dotgit(self) -> None:
        assert _sanitize_repo_name("https://github.com/user/repo") == "repo"

    def test_suspicious_name_raises(self) -> None:
        with pytest.raises(ValueError, match="Suspicious"):
            _sanitize_repo_name("https://github.com/user/repo%2F..%2Fetc.git")


class TestSafeResolve:
    """Tests for ``_safe_resolve``."""

    def test_normal_path(self, tmp_path: Path) -> None:
        result = _safe_resolve(str(tmp_path), "README.md")
        assert str(result).startswith(str(tmp_path))

    def test_traversal_blocked(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Path traversal"):
            _safe_resolve(str(tmp_path), "../../etc/passwd")

    def test_nested_path(self, tmp_path: Path) -> None:
        result = _safe_resolve(str(tmp_path), "docs/guide.md")
        assert str(result).startswith(str(tmp_path))


# ── Git operations ──────────────────────────────────────────────────────────

class TestCloneRepo:
    """Tests for ``clone_repo``."""

    @patch("tools.git_manager._git_env", return_value={})
    @patch("tools.git_manager.Repo")
    @patch("tools.git_manager.os.path.isdir", return_value=False)
    def test_clones_when_dir_missing(
        self, mock_isdir: MagicMock, mock_repo_cls: MagicMock, mock_env: MagicMock
    ) -> None:
        result = git_manager.clone_repo("https://github.com/user/repo.git", "main")

        mock_repo_cls.clone_from.assert_called_once()
        assert result.endswith("repo")

    @patch("tools.git_manager._git_env", return_value={})
    @patch("tools.git_manager.Repo")
    @patch("tools.git_manager.os.path.isdir", return_value=True)
    def test_pulls_when_dir_exists(
        self, mock_isdir: MagicMock, mock_repo_cls: MagicMock, mock_env: MagicMock
    ) -> None:
        mock_repo_instance = MagicMock()
        mock_repo_cls.return_value = mock_repo_instance

        git_manager.clone_repo("https://github.com/user/repo.git", "main")

        mock_repo_instance.remotes.origin.fetch.assert_called_once()


class TestGetDiff:
    """Tests for ``get_diff``."""

    @patch("tools.git_manager.Repo")
    def test_returns_diff_string(self, mock_repo_cls: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_repo.git.diff.return_value = "diff --git a/foo.py b/foo.py\n+bar"
        mock_repo_cls.return_value = mock_repo

        result = git_manager.get_diff("/fake/path", "abc123", "def456")

        mock_repo.git.diff.assert_called_once_with("abc123", "def456")
        assert "diff --git" in result

    @patch("tools.git_manager.settings")
    @patch("tools.git_manager.Repo")
    def test_truncates_large_diff(
        self, mock_repo_cls: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.max_diff_chars = 100
        mock_repo = MagicMock()
        mock_repo.git.diff.return_value = "x" * 500
        mock_repo_cls.return_value = mock_repo

        result = git_manager.get_diff("/fake/path", "abc", "def")
        assert len(result) < 500
        assert "[...diff truncated...]" in result


class TestReadFile:
    """Tests for ``read_file``."""

    def test_reads_file_content(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Hello\n", encoding="utf-8")
        content = git_manager.read_file(str(tmp_path), "README.md")
        assert content == "# Hello\n"

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Path traversal"):
            git_manager.read_file(str(tmp_path), "../../etc/passwd")


class TestWriteFile:
    """Tests for ``write_file``."""

    def test_writes_file_content(self, tmp_path: Path) -> None:
        git_manager.write_file(str(tmp_path), "docs/guide.md", "content")
        assert (tmp_path / "docs" / "guide.md").read_text() == "content"

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Path traversal"):
            git_manager.write_file(str(tmp_path), "../../evil.txt", "data")


class TestCommitAndPush:
    """Tests for ``commit_and_push``."""

    @patch("tools.git_manager._git_env", return_value={})
    @patch("tools.git_manager.Repo")
    def test_commits_and_pushes(
        self, mock_repo_cls: MagicMock, mock_env: MagicMock
    ) -> None:
        mock_repo = MagicMock()
        mock_repo.active_branch.name = "main"
        mock_repo_cls.return_value = mock_repo

        git_manager.commit_and_push("/repo", "README.md", "update docs")

        mock_repo.index.add.assert_called_once_with(["README.md"])
        mock_repo.index.commit.assert_called_once_with("update docs")

    @patch("tools.git_manager._git_env", return_value={})
    @patch("tools.git_manager.Repo")
    def test_pushes_to_specified_branch(
        self, mock_repo_cls: MagicMock, mock_env: MagicMock
    ) -> None:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        git_manager.commit_and_push("/repo", "README.md", "update", branch="develop")
