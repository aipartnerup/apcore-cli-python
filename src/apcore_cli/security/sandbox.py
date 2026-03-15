"""Subprocess-based execution sandboxing (FE-05)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apcore import Executor


class ModuleExecutionError(Exception):
    """Raised when a sandboxed module execution fails."""

    pass


class Sandbox:
    def __init__(self, enabled: bool = False) -> None:
        self._enabled = enabled

    def execute(self, module_id: str, input_data: dict, executor: Executor) -> Any:
        if not self._enabled:
            return executor.call(module_id, input_data)
        return self._sandboxed_execute(module_id, input_data)

    def _sandboxed_execute(self, module_id: str, input_data: dict) -> Any:
        env = {}
        for key in ("PATH", "PYTHONPATH", "LANG", "LC_ALL"):
            if key in os.environ:
                env[key] = os.environ[key]
        for key, value in os.environ.items():
            if key.startswith("APCORE_"):
                env[key] = value

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
                    timeout=300,
                )
            except subprocess.TimeoutExpired as err:
                raise ModuleExecutionError(f"Error: Module '{module_id}' timed out in sandbox.") from err

            if result.returncode != 0:
                raise ModuleExecutionError(f"Error: Module '{module_id}' execution failed: {result.stderr}")

            return json.loads(result.stdout)
