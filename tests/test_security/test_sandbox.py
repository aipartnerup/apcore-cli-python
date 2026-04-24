"""Tests for Sandbox (FE-05)."""

from unittest.mock import MagicMock, patch

import pytest
from apcore_cli.security.sandbox import ModuleExecutionError, Sandbox


class TestSandbox:
    def test_sandbox_disabled_direct_execution(self):
        executor = MagicMock()
        executor.call.return_value = {"result": 42}
        sandbox = Sandbox(enabled=False)
        result = sandbox.execute("math.add", {"a": 5}, executor)
        assert result == {"result": 42}
        executor.call.assert_called_once_with("math.add", {"a": 5})

    def test_sandbox_enabled_subprocess(self):
        sandbox = Sandbox(enabled=True)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"result": 42}', stderr="")
            result = sandbox._sandboxed_execute("math.add", {"a": 5})
        assert result == {"result": 42}

    def test_sandbox_restricted_env(self):
        sandbox = Sandbox(enabled=True)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
            sandbox._sandboxed_execute("mod", {})
            call_kwargs = mock_run.call_args
            env = call_kwargs.kwargs.get("env") or call_kwargs[1].get("env")
            # HOME should be a temp dir, not the real home
            assert env.get("HOME", "").startswith("/")
            # Should not have random env vars
            assert "EDITOR" not in env

    def test_sandbox_subprocess_failure(self):
        sandbox = Sandbox(enabled=True)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="module error")
            with pytest.raises(ModuleExecutionError, match="execution failed"):
                sandbox._sandboxed_execute("mod", {})

    def test_sandbox_result_parsing(self):
        sandbox = Sandbox(enabled=True)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"key": "value", "num": 123}', stderr="")
            result = sandbox._sandboxed_execute("mod", {})
        assert result == {"key": "value", "num": 123}

    def test_sandbox_non_json_stdout_on_success_raises_module_execution_error(self):
        """W9: a subprocess that exits 0 but emits non-JSON stdout must surface
        as the documented ModuleExecutionError contract, not raw JSONDecodeError."""
        sandbox = Sandbox(enabled=True)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="DeprecationWarning: blah\n{not-json-at-all",
                stderr="",
            )
            with pytest.raises(ModuleExecutionError, match="non-JSON output"):
                sandbox._sandboxed_execute("mod", {})
