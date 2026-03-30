"""
Unit tests for ``agent.workflow``.

Tests the ``run_ghostwriter_workflow`` entry point with all external
dependencies mocked (git, Docker, LLM).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestRunGhostwriterWorkflow:
    """Integration-level tests for the workflow entry point."""

    @patch("agent.workflow.commit_and_push")
    @patch("agent.workflow.write_file")
    @patch("agent.workflow.read_file", return_value="# Old README")
    @patch("agent.workflow.get_diff", return_value="")
    @patch("agent.workflow.clone_repo", return_value="/tmp/repo")
    def test_empty_diff_returns_no_changes(
        self,
        mock_clone: MagicMock,
        mock_diff: MagicMock,
        mock_read: MagicMock,
        mock_write: MagicMock,
        mock_push: MagicMock,
    ) -> None:
        from agent.workflow import run_ghostwriter_workflow

        result = run_ghostwriter_workflow(
            clone_url="https://github.com/user/repo.git",
            branch="main",
            base_sha="aaa111",
            head_sha="bbb222",
        )
        assert result["status"] == "no_changes"
        mock_push.assert_not_called()

    @patch("agent.workflow._compiled_workflow")
    @patch("agent.workflow.scan_repo", return_value="PROJECT STRUCTURE:\n├── main.py")
    @patch("agent.workflow.commit_and_push")
    @patch("agent.workflow.write_file")
    @patch("agent.workflow.read_file", side_effect=FileNotFoundError)
    @patch("agent.workflow.get_diff", return_value="some diff")
    @patch("agent.workflow.clone_repo", return_value="/tmp/repo")
    def test_missing_readme_triggers_initial_generation(
        self,
        mock_clone: MagicMock,
        mock_diff: MagicMock,
        mock_read: MagicMock,
        mock_write: MagicMock,
        mock_push: MagicMock,
        mock_scan: MagicMock,
        mock_workflow: MagicMock,
    ) -> None:
        """When README is missing, workflow should run (not skip) and scan repo."""
        mock_workflow.invoke.return_value = {
            "updated_readme": "# Generated README",
            "original_readme": "",
            "error_message": "",
        }

        from agent.workflow import run_ghostwriter_workflow

        result = run_ghostwriter_workflow(
            clone_url="https://github.com/user/repo.git",
            branch="main",
            base_sha="aaa111",
            head_sha="bbb222",
        )
        # Workflow should NOT return "no_readme" — it should invoke the graph
        assert result.get("status") != "no_readme"
        mock_scan.assert_called_once()

    @patch("agent.workflow._compiled_workflow")
    @patch("agent.workflow.scan_repo", return_value="PROJECT STRUCTURE:\n├── main.py")
    @patch("agent.workflow.commit_and_push")
    @patch("agent.workflow.write_file")
    @patch("agent.workflow.read_file", return_value="")
    @patch("agent.workflow.get_diff", return_value="some diff")
    @patch("agent.workflow.clone_repo", return_value="/tmp/repo")
    def test_empty_readme_triggers_repo_scan(
        self,
        mock_clone: MagicMock,
        mock_diff: MagicMock,
        mock_read: MagicMock,
        mock_write: MagicMock,
        mock_push: MagicMock,
        mock_scan: MagicMock,
        mock_workflow: MagicMock,
    ) -> None:
        """When README is empty string, workflow should scan repo for context."""
        mock_workflow.invoke.return_value = {
            "updated_readme": "# Generated README",
            "original_readme": "",
            "error_message": "",
        }

        from agent.workflow import run_ghostwriter_workflow

        result = run_ghostwriter_workflow(
            clone_url="https://github.com/user/repo.git",
            branch="main",
            base_sha="aaa111",
            head_sha="bbb222",
        )
        mock_scan.assert_called_once()

    @patch("agent.workflow.clone_repo", side_effect=Exception("network error"))
    def test_clone_failure_returns_error(self, mock_clone: MagicMock) -> None:
        from agent.workflow import run_ghostwriter_workflow

        result = run_ghostwriter_workflow(
            clone_url="https://github.com/user/repo.git",
            branch="main",
            base_sha="aaa111",
            head_sha="bbb222",
        )
        assert result["status"] == "error"


class TestShouldRetry:
    """Tests for the conditional edge logic."""

    def test_retry_when_errors_and_retries_remain(self) -> None:
        from agent.workflow import _should_retry

        state = {
            "error_message": "Block 1 failed",
            "retry_count": 1,
        }
        assert _should_retry(state) == "writer"

    def test_end_when_no_errors(self) -> None:
        from agent.workflow import _should_retry

        state = {"error_message": "", "retry_count": 1}
        assert _should_retry(state) == "end"

    @patch("agent.workflow.settings")
    def test_end_when_retries_exhausted(self, mock_settings: MagicMock) -> None:
        mock_settings.max_retries = 3

        from agent.workflow import _should_retry

        state = {"error_message": "still failing", "retry_count": 3}
        assert _should_retry(state) == "end"
