"""
Unit tests for ``tools.docker_executor``.

Docker operations are fully mocked so tests run without a Docker daemon.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from models import SandboxResult


class TestRunCodeInSandbox:
    """Tests for ``run_code_in_sandbox``."""

    @patch("tools.docker_executor._get_docker_client")
    def test_successful_execution(self, mock_get_client: MagicMock) -> None:
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.side_effect = [b"hello\n", b""]
        mock_container.id = "abc123"

        mock_client = MagicMock()
        mock_client.containers.run.return_value = mock_container
        mock_get_client.return_value = mock_client

        from tools.docker_executor import run_code_in_sandbox

        result = run_code_in_sandbox("print('hello')")

        assert isinstance(result, SandboxResult)
        assert result.success
        assert result.exit_code == 0
        assert "hello" in result.stdout
        mock_container.remove.assert_called_once_with(force=True)

    @patch("tools.docker_executor._get_docker_client")
    def test_failed_execution(self, mock_get_client: MagicMock) -> None:
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 1}
        mock_container.logs.side_effect = [b"", b"NameError: name 'x'\n"]
        mock_container.id = "abc123"

        mock_client = MagicMock()
        mock_client.containers.run.return_value = mock_container
        mock_get_client.return_value = mock_client

        from tools.docker_executor import run_code_in_sandbox

        result = run_code_in_sandbox("print(x)")

        assert not result.success
        assert result.exit_code == 1
        assert "NameError" in result.stderr
        mock_container.remove.assert_called_once_with(force=True)

    @patch("tools.docker_executor._get_docker_client")
    def test_image_not_found(self, mock_get_client: MagicMock) -> None:
        from docker.errors import ImageNotFound

        mock_client = MagicMock()
        mock_client.containers.run.side_effect = ImageNotFound("not found")
        mock_get_client.return_value = mock_client

        from tools.docker_executor import run_code_in_sandbox

        result = run_code_in_sandbox("print('hello')")

        assert not result.success
        assert "not found" in result.stderr

    @patch("tools.docker_executor._get_docker_client")
    def test_container_removed_on_timeout(self, mock_get_client: MagicMock) -> None:
        """Container should be removed even when wait() raises."""
        mock_container = MagicMock()
        mock_container.wait.side_effect = Exception("timeout")
        mock_container.id = "abc123"

        mock_client = MagicMock()
        mock_client.containers.run.return_value = mock_container
        mock_get_client.return_value = mock_client

        from tools.docker_executor import run_code_in_sandbox

        result = run_code_in_sandbox("while True: pass")

        assert not result.success
        # Verify the container was cleaned up despite the error
        mock_container.remove.assert_called_once_with(force=True)

    def test_sandbox_result_model(self) -> None:
        """Verify the SandboxResult dataclass behaves correctly."""
        ok = SandboxResult(stdout="hello", stderr="", exit_code=0)
        assert ok.success

        fail = SandboxResult(stdout="", stderr="err", exit_code=1)
        assert not fail.success
