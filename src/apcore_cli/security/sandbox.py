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


# Env forwarding strategy (mirrors Rust spec §4.4 and apcore-cli/docs/features/security.md):
# Allow: PATH, PYTHONPATH, LANG, LC_ALL + all APCORE_* vars.
# Deny prefix: APCORE_AUTH_ — credentials must not cross the sandbox trust boundary.
_SANDBOX_ALLOW_KEYS = ("PATH", "PYTHONPATH", "LANG", "LC_ALL")
_SANDBOX_ALLOW_PREFIX = "APCORE_"
_SANDBOX_DENY_PREFIX = "APCORE_AUTH_"


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
        for key in _SANDBOX_ALLOW_KEYS:
            if key in os.environ:
                env[key] = os.environ[key]
        # Forward all APCORE_* vars except the APCORE_AUTH_* deny prefix.
        # Using prefix-allow + deny avoids silently missing newly-added APCORE_* vars.
        for key, val in os.environ.items():
            if key.startswith(_SANDBOX_ALLOW_PREFIX) and not key.startswith(_SANDBOX_DENY_PREFIX):
                env[key] = val

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
