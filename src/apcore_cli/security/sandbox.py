"""Subprocess-based execution sandboxing (FE-05)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apcore import Executor


class ModuleExecutionError(Exception):
    """Raised when a sandboxed module execution fails."""

    pass


# Non-secret APCORE_* vars forwarded into the sandbox subprocess.
# Excludes credential/token vars (APCORE_AUTH_*, APCORE_*_KEY, etc.) so that
# untrusted module code cannot read the remote-registry bearer token.
_SANDBOX_APCORE_ALLOWLIST = frozenset(
    {
        "APCORE_EXTENSIONS_ROOT",
        "APCORE_LOG_LEVEL",
        "APCORE_CLI_LOGGING_LEVEL",
        "APCORE_CLI_GROUP_DEPTH",
        "APCORE_CLI_STRATEGY",
        "APCORE_CLI_APPROVAL_TIMEOUT",
        "APCORE_CLI_APCLI",
        "APCORE_CLI_AUTO_APPROVE",
    }
)


class Sandbox:
    """Subprocess-isolated module execution.

    Audit D1-005 parity (v0.6.x): the `timeout_seconds` parameter mirrors
    the Rust `Sandbox::new(enabled, timeout_ms)` API. When `enabled=False`,
    `execute()` is a passthrough to the injected apcore Executor.
    """

    def __init__(
        self,
        enabled: bool = False,
        timeout_seconds: int = 300,
        extensions_root: str | None = None,
        max_output_bytes: int = 64 * 1024 * 1024,
    ) -> None:
        self._enabled = enabled
        self._timeout_seconds = timeout_seconds
        self._extensions_root = extensions_root
        self._max_output_bytes = max_output_bytes

    def execute(self, module_id: str, input_data: dict, executor: Executor) -> Any:
        if not self._enabled:
            return executor.call(module_id, input_data)
        return self._sandboxed_execute(module_id, input_data)

    def _sandboxed_execute(self, module_id: str, input_data: dict) -> Any:
        env: dict[str, str] = {}
        for key in ("PATH", "PYTHONPATH", "LANG", "LC_ALL"):
            if key in os.environ:
                env[key] = os.environ[key]
        # Forward only explicitly-allowlisted APCORE_* vars — excludes secrets
        # such as APCORE_AUTH_API_KEY that must not reach untrusted module code.
        for key in _SANDBOX_APCORE_ALLOWLIST:
            if key in os.environ:
                env[key] = os.environ[key]

        # Inject extensions root as an absolute path so the runner locates
        # modules correctly even when cwd is changed to the sandbox tempdir.
        if self._extensions_root is not None:
            env["APCORE_EXTENSIONS_ROOT"] = str(Path(self._extensions_root).resolve())
        elif "APCORE_EXTENSIONS_ROOT" in env:
            env["APCORE_EXTENSIONS_ROOT"] = str(Path(env["APCORE_EXTENSIONS_ROOT"]).resolve())

        with tempfile.TemporaryDirectory(prefix="apcore_sandbox_") as tmpdir:
            env["HOME"] = tmpdir
            env["TMPDIR"] = tmpdir

            try:
                result = subprocess.run(
                    [sys.executable, "-m", "apcore_cli._sandbox_runner", module_id],
                    input=json.dumps(input_data),
                    capture_output=True,
                    text=True,
                    env=env,
                    cwd=tmpdir,
                    timeout=self._timeout_seconds,
                )
            except subprocess.TimeoutExpired as err:
                raise ModuleExecutionError(f"Error: Module '{module_id}' timed out in sandbox.") from err

            # Enforce output size cap (post-capture soft limit; for a hard cap
            # that prevents memory accumulation, use Popen-based streaming).
            total_bytes = len(result.stdout.encode()) + len(result.stderr.encode())
            if total_bytes > self._max_output_bytes:
                limit_mb = self._max_output_bytes // (1024 * 1024)
                raise ModuleExecutionError(
                    f"Error: Module '{module_id}' output exceeded the {limit_mb}MB sandbox limit."
                )

            if result.returncode != 0:
                raise ModuleExecutionError(f"Error: Module '{module_id}' execution failed: {result.stderr}")

            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as err:
                preview = result.stdout[:200]
                raise ModuleExecutionError(f"Error: Module '{module_id}' returned non-JSON output: {preview}") from err
