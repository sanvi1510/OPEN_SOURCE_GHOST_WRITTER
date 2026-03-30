"""
Unit tests for ``agent.nodes``.

LLM calls and Docker execution are fully mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent.state import GhostwriterState
from models import SandboxResult


def _base_state(**overrides: object) -> GhostwriterState:
    """Return a minimal valid workflow state, with optional overrides."""
    state: GhostwriterState = {
        "repo_path": "/tmp/repo",
        "diff": "diff --git a/foo.py\n+bar",
        "analysis": '{"changes":[],"affected_docs_likely":false,"summary":"none"}',
        "original_readme": "# Old README",
        "updated_readme": "",
        "code_blocks": [],
        "test_results": [],
        "error_message": "",
        "retry_count": 0,
    }
    state.update(overrides)  # type: ignore[arg-type]
    return state


class TestAnalyzerNode:
    """Tests for ``analyzer_node``."""

    @patch("agent.nodes._invoke_llm_with_retry")
    @patch("agent.nodes._get_llm")
    def test_returns_analysis(
        self, mock_llm: MagicMock, mock_invoke: MagicMock
    ) -> None:
        mock_invoke.return_value = '{"changes": [], "summary": "no changes"}'

        from agent.nodes import analyzer_node

        result = analyzer_node(_base_state())
        assert "analysis" in result
        assert result["analysis"] == '{"changes": [], "summary": "no changes"}'

    @patch("agent.nodes._invoke_llm_with_retry")
    @patch("agent.nodes._get_llm")
    def test_llm_failure_surfaces_error(
        self, mock_llm: MagicMock, mock_invoke: MagicMock
    ) -> None:
        mock_invoke.side_effect = RuntimeError("API down")

        from agent.nodes import analyzer_node

        result = analyzer_node(_base_state())
        assert result["analysis"] == ""
        assert "API down" in result["error_message"]


class TestWriterNode:
    """Tests for ``writer_node``."""

    @patch("agent.nodes._invoke_llm_with_retry")
    @patch("agent.nodes._get_llm")
    def test_first_pass_uses_original_readme(
        self, mock_llm: MagicMock, mock_invoke: MagicMock
    ) -> None:
        mock_invoke.return_value = "# Updated README"

        from agent.nodes import writer_node

        result = writer_node(_base_state())
        assert result["updated_readme"] == "# Updated README"
        assert result["retry_count"] == 1
        assert result["error_message"] == ""

    @patch("agent.nodes._invoke_llm_with_retry")
    @patch("agent.nodes._get_llm")
    def test_retry_pass_uses_updated_readme(
        self, mock_llm: MagicMock, mock_invoke: MagicMock
    ) -> None:
        mock_invoke.return_value = "# Fixed README"

        from agent.nodes import writer_node

        state = _base_state(
            updated_readme="# Draft with errors",
            retry_count=1,
            error_message="Block 1 failed",
        )
        result = writer_node(state)
        assert result["updated_readme"] == "# Fixed README"
        assert result["retry_count"] == 2

    @patch("agent.nodes._invoke_llm_with_retry")
    @patch("agent.nodes._get_llm")
    def test_llm_failure_surfaces_error(
        self, mock_llm: MagicMock, mock_invoke: MagicMock
    ) -> None:
        mock_invoke.side_effect = RuntimeError("Rate limited")

        from agent.nodes import writer_node

        result = writer_node(_base_state())
        assert "Rate limited" in result["error_message"]


class TestTesterNode:
    """Tests for ``tester_node``."""

    @patch("agent.nodes.run_code_in_sandbox")
    def test_all_blocks_pass(self, mock_sandbox: MagicMock) -> None:
        mock_sandbox.return_value = SandboxResult(
            stdout="ok", stderr="", exit_code=0
        )

        from agent.nodes import tester_node

        state = _base_state(
            updated_readme="```python\nprint('hello')\n```\n"
        )
        result = tester_node(state)
        assert result["error_message"] == ""
        assert len(result["code_blocks"]) == 1

    @patch("agent.nodes.run_code_in_sandbox")
    def test_block_failure_recorded(self, mock_sandbox: MagicMock) -> None:
        mock_sandbox.return_value = SandboxResult(
            stdout="", stderr="NameError", exit_code=1
        )

        from agent.nodes import tester_node

        state = _base_state(
            updated_readme="```python\nprint(x)\n```\n"
        )
        result = tester_node(state)
        assert "NameError" in result["error_message"]

    def test_no_updated_readme(self) -> None:
        from agent.nodes import tester_node

        result = tester_node(_base_state(updated_readme=""))
        assert "error_message" in result

    def test_no_python_blocks(self) -> None:
        from agent.nodes import tester_node

        state = _base_state(updated_readme="# Just text, no code")
        result = tester_node(state)
        assert result["error_message"] == ""
        assert result["code_blocks"] == []
