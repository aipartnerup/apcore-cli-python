"""Tests for _sandbox_runner subprocess entry point (FE-05)."""

from __future__ import annotations

import io
import json
import sys
from unittest.mock import MagicMock, patch


def _invoke_main(module_id: str, stdin_json: str, extra_env: dict | None = None) -> str:
    """Run _sandbox_runner.main() in-process with faked stdin/argv/env."""
    from apcore_cli._sandbox_runner import main

    mock_registry = MagicMock()
    mock_executor = MagicMock()
    mock_executor.call.return_value = json.loads(stdin_json) if stdin_json != "{}" else {"ok": True}

    captured = io.StringIO()
    env_override = extra_env or {}

    with (
        patch.object(sys, "argv", ["runner", module_id]),
        patch("sys.stdin", io.StringIO(stdin_json)),
        patch("sys.stdout", captured),
        patch.dict("os.environ", env_override, clear=False),
        patch("apcore.Registry", return_value=mock_registry),
        patch("apcore.Executor", return_value=mock_executor),
    ):
        main()
    return captured.getvalue()


class TestSandboxRunnerMain:
    def test_calls_executor_with_parsed_input(self):
        """main() must pass module_id and parsed JSON input to executor.call."""
        mock_registry = MagicMock()
        mock_executor = MagicMock()
        mock_executor.call.return_value = {"answer": 42}
        captured = io.StringIO()

        with (
            patch.object(sys, "argv", ["runner", "math.add"]),
            patch("sys.stdin", io.StringIO('{"a": 1}')),
            patch("sys.stdout", captured),
            patch("apcore.Registry", return_value=mock_registry),
            patch("apcore.Executor", return_value=mock_executor),
        ):
            from apcore_cli._sandbox_runner import main

            main()

        mock_registry.discover.assert_called_once()
        mock_executor.call.assert_called_once_with("math.add", {"a": 1})
        assert json.loads(captured.getvalue()) == {"answer": 42}

    def test_extensions_root_from_env_used_for_registry(self):
        """main() must pass APCORE_EXTENSIONS_ROOT to Registry(extensions_dir=...)."""
        mock_registry = MagicMock()
        mock_executor = MagicMock()
        mock_executor.call.return_value = {}
        registry_cls = MagicMock(return_value=mock_registry)

        with (
            patch.object(sys, "argv", ["runner", "mod.id"]),
            patch("sys.stdin", io.StringIO("{}")),
            patch("sys.stdout", io.StringIO()),
            patch.dict("os.environ", {"APCORE_EXTENSIONS_ROOT": "/abs/ext"}, clear=False),
            patch("apcore.Registry", registry_cls),
            patch("apcore.Executor", return_value=mock_executor),
        ):
            from apcore_cli._sandbox_runner import main

            main()

        registry_cls.assert_called_once_with(extensions_dir="/abs/ext")

    def test_empty_input_object_accepted(self):
        """main() must accept an empty JSON object '{}' as input without error."""
        mock_registry = MagicMock()
        mock_executor = MagicMock()
        mock_executor.call.return_value = {"status": "ok"}
        captured = io.StringIO()

        with (
            patch.object(sys, "argv", ["runner", "mod.id"]),
            patch("sys.stdin", io.StringIO("{}")),
            patch("sys.stdout", captured),
            patch("apcore.Registry", return_value=mock_registry),
            patch("apcore.Executor", return_value=mock_executor),
        ):
            from apcore_cli._sandbox_runner import main

            main()

        assert json.loads(captured.getvalue()) == {"status": "ok"}
        mock_executor.call.assert_called_once_with("mod.id", {})
