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

    def test_sandbox_env_does_not_leak_auth_api_key(self):
        """C1: APCORE_AUTH_API_KEY must not reach the sandboxed subprocess."""
        sandbox = Sandbox(enabled=True)
        parent_env = {"APCORE_AUTH_API_KEY": "secret-token", "PATH": "/usr/bin"}
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
            with patch.dict("os.environ", parent_env, clear=True):
                sandbox._sandboxed_execute("mod", {})
            call_env = mock_run.call_args.kwargs.get("env") or mock_run.call_args[1].get("env")
            assert "APCORE_AUTH_API_KEY" not in call_env

    def test_sandbox_env_forwards_allowed_apcore_vars(self):
        """Non-secret APCORE_* vars in the allowlist must still be forwarded."""
        sandbox = Sandbox(enabled=True)
        parent_env = {
            "APCORE_EXTENSIONS_ROOT": "/some/path",
            "APCORE_LOG_LEVEL": "DEBUG",
            "APCORE_AUTH_API_KEY": "secret",
            "PATH": "/usr/bin",
        }
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
            with patch.dict("os.environ", parent_env, clear=True):
                sandbox._sandboxed_execute("mod", {})
            call_env = mock_run.call_args.kwargs.get("env") or mock_run.call_args[1].get("env")
            assert "APCORE_LOG_LEVEL" in call_env
            assert "APCORE_AUTH_API_KEY" not in call_env

    def test_sandbox_extensions_root_injected_as_absolute(self):
        """C2: extensions_root kwarg must be injected as APCORE_EXTENSIONS_ROOT
        with an absolute path so module discovery works under cwd=tmpdir."""
        sandbox = Sandbox(enabled=True, extensions_root="/abs/extensions")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
            with patch.dict("os.environ", {}, clear=True):
                sandbox._sandboxed_execute("mod", {})
            call_env = mock_run.call_args.kwargs.get("env") or mock_run.call_args[1].get("env")
            assert call_env.get("APCORE_EXTENSIONS_ROOT") == "/abs/extensions"

    def test_sandbox_extensions_root_env_var_resolved_to_absolute(self):
        """C2: a relative APCORE_EXTENSIONS_ROOT env var must be resolved to
        an absolute path before injecting it into the subprocess env."""
        sandbox = Sandbox(enabled=True)
        parent_env = {"APCORE_EXTENSIONS_ROOT": "./extensions", "PATH": "/usr/bin"}
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
            with patch.dict("os.environ", parent_env, clear=True):
                sandbox._sandboxed_execute("mod", {})
            call_env = mock_run.call_args.kwargs.get("env") or mock_run.call_args[1].get("env")
            assert call_env.get("APCORE_EXTENSIONS_ROOT", "").startswith("/")

    def test_sandbox_output_size_limit_raises(self):
        """W6 (D3): oversized subprocess output must raise ModuleExecutionError."""
        sandbox = Sandbox(enabled=True, max_output_bytes=100)
        big_stdout = "x" * 200
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=big_stdout, stderr="")
            with pytest.raises(ModuleExecutionError, match="exceeded"):
                sandbox._sandboxed_execute("mod", {})

    def test_sandbox_does_not_forward_pythonpath(self):
        """D10-010: PYTHONPATH must not appear in the sandboxed subprocess environment."""
        sandbox = Sandbox(enabled=True)
        parent_env = {"PYTHONPATH": "/some/path", "PATH": "/usr/bin"}
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
            with patch.dict("os.environ", parent_env, clear=True):
                sandbox._sandboxed_execute("mod", {})
            call_env = mock_run.call_args.kwargs.get("env") or mock_run.call_args[1].get("env")
            assert "PYTHONPATH" not in call_env, "PYTHONPATH must not be forwarded to the sandbox"

    def test_sandbox_deny_keys_constant_exists(self):
        """D11-007: _SANDBOX_DENY_KEYS constant must be defined and contain APCORE_AUTH_API_KEY."""
        from apcore_cli.security import sandbox as sandbox_module

        assert hasattr(sandbox_module, "_SANDBOX_DENY_KEYS"), "_SANDBOX_DENY_KEYS must be defined in sandbox.py"
        assert "APCORE_AUTH_API_KEY" in sandbox_module._SANDBOX_DENY_KEYS
