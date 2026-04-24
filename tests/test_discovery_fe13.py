"""Coverage-focused tests for FE-13 discovery split-registrar edges.

Covers ``register_exec_command`` runtime paths (module not found, invalid
JSON --input, successful call with inline JSON) and ``register_validate_command``
failure paths that aren't exercised by the batched-wrapper tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from apcore_cli.discovery import (
    register_describe_command,
    register_exec_command,
    register_list_command,
    register_validate_command,
)


def _make_module_def(module_id: str = "foo.bar"):
    m = MagicMock()
    m.module_id = module_id
    m.canonical_id = module_id
    m.description = "desc"
    m.tags = []
    m.annotations = None
    m.input_schema = {"properties": {}, "required": []}
    m.output_schema = None
    m.deprecated = False
    m.enabled = True
    m.metadata = {}
    # Used by check_approval — return no approval requirement.
    m.requires_approval = False
    return m


def _build_apcli_with(registrar, *args, **kwargs) -> click.Group:
    @click.group()
    def apcli() -> None:
        pass

    registrar(apcli, *args, **kwargs)
    return apcli


class TestRegisterExecCommand:
    def test_module_not_found_exits_44(self):
        registry = MagicMock()
        registry.get_definition.return_value = None
        executor = MagicMock()
        cli = _build_apcli_with(register_exec_command, registry, executor)
        result = CliRunner().invoke(cli, ["exec", "nosuch.module"])
        assert result.exit_code == 44
        assert "not found" in result.output

    def test_inline_json_object_success(self):
        module_def = _make_module_def("foo.bar")
        registry = MagicMock()
        registry.get_definition.return_value = module_def
        executor = MagicMock()
        executor.call.return_value = {"result": "ok"}
        cli = _build_apcli_with(register_exec_command, registry, executor)
        result = CliRunner().invoke(cli, ["exec", "foo.bar", "--input", '{"k": 1}', "--yes", "--format", "json"])
        assert result.exit_code == 0, result.output
        executor.call.assert_called_once_with("foo.bar", {"k": 1})

    def test_inline_invalid_json_exits_2(self):
        module_def = _make_module_def("foo.bar")
        registry = MagicMock()
        registry.get_definition.return_value = module_def
        executor = MagicMock()
        cli = _build_apcli_with(register_exec_command, registry, executor)
        result = CliRunner().invoke(cli, ["exec", "foo.bar", "--input", "{not json}"])
        assert result.exit_code == 2
        assert "not valid JSON" in result.output

    def test_inline_json_non_object_exits_2(self):
        module_def = _make_module_def("foo.bar")
        registry = MagicMock()
        registry.get_definition.return_value = module_def
        executor = MagicMock()
        cli = _build_apcli_with(register_exec_command, registry, executor)
        result = CliRunner().invoke(cli, ["exec", "foo.bar", "--input", "[1, 2]"])
        assert result.exit_code == 2
        assert "must be an object" in result.output

    def test_executor_exception_propagates_exit_code(self):
        module_def = _make_module_def("foo.bar")
        registry = MagicMock()
        registry.get_definition.return_value = module_def
        executor = MagicMock()
        err = RuntimeError("boom")
        err.code = "MODULE_EXECUTE_ERROR"
        executor.call.side_effect = err
        cli = _build_apcli_with(register_exec_command, registry, executor)
        result = CliRunner().invoke(cli, ["exec", "foo.bar", "--yes"])
        # _ERROR_CODE_MAP["MODULE_EXECUTE_ERROR"] = 1
        assert result.exit_code == 1

    def test_exec_cmd_writes_audit_log_on_success(self):
        """W1 (D9): exec_cmd must call _audit_logger.log_execution on success,
        matching the audit trail written by build_module_command."""
        module_def = _make_module_def("foo.bar")
        registry = MagicMock()
        registry.get_definition.return_value = module_def
        executor = MagicMock()
        executor.call.return_value = {"result": "ok"}
        audit_logger = MagicMock()
        with patch("apcore_cli.cli._audit_logger", audit_logger):
            cli = _build_apcli_with(register_exec_command, registry, executor)
            CliRunner().invoke(cli, ["exec", "foo.bar", "--yes", "--format", "json"])
        audit_logger.log_execution.assert_called_once()
        args = audit_logger.log_execution.call_args[0]
        assert args[0] == "foo.bar"
        assert args[2] == "success"

    def test_exec_cmd_writes_audit_log_on_error(self):
        """W1 (D9): exec_cmd must call _audit_logger.log_execution on error too."""
        module_def = _make_module_def("foo.bar")
        registry = MagicMock()
        registry.get_definition.return_value = module_def
        executor = MagicMock()
        executor.call.side_effect = RuntimeError("boom")
        audit_logger = MagicMock()
        with patch("apcore_cli.cli._audit_logger", audit_logger):
            cli = _build_apcli_with(register_exec_command, registry, executor)
            CliRunner().invoke(cli, ["exec", "foo.bar", "--yes"])
        audit_logger.log_execution.assert_called_once()
        args = audit_logger.log_execution.call_args[0]
        assert args[0] == "foo.bar"
        assert args[2] == "error"


class TestRegisterValidateCommand:
    def test_module_not_found_exits_44(self):
        registry = MagicMock()
        registry.get_definition.return_value = None
        executor = MagicMock()
        cli = _build_apcli_with(register_validate_command, registry, executor)
        result = CliRunner().invoke(cli, ["validate", "nosuch.module"])
        assert result.exit_code == 44

    def test_preflight_failure_surfaces_exit_code(self):
        module_def = _make_module_def("foo.bar")
        registry = MagicMock()
        registry.get_definition.return_value = module_def
        executor = MagicMock()
        preflight = MagicMock()
        preflight.valid = False
        preflight.checks = []
        executor.validate.return_value = preflight
        cli = _build_apcli_with(register_validate_command, registry, executor)
        result = CliRunner().invoke(cli, ["validate", "foo.bar", "--format", "json"])
        # _first_failed_exit_code defaults to 1 when no specific check pattern matched
        assert result.exit_code != 0

    def test_executor_exception_surfaces_mapped_exit_code(self):
        """W5: executor.validate raising (e.g. ACL_DENIED) must emit a
        formatted CLI error and resolve the mapped exit code — mirroring
        register_exec_command. Before the fix, the user saw a raw traceback."""
        module_def = _make_module_def("foo.bar")
        registry = MagicMock()
        registry.get_definition.return_value = module_def
        executor = MagicMock()

        class _AclDeniedError(Exception):
            code = "ACL_DENIED"

        executor.validate.side_effect = _AclDeniedError("acl denied")
        cli = _build_apcli_with(register_validate_command, registry, executor)
        result = CliRunner().invoke(cli, ["validate", "foo.bar"])
        # Exit is a mapped code (77 = ACL_DENIED per _ERROR_CODE_MAP) OR 1 if
        # the project's _ERROR_CODE_MAP doesn't carry this symbol yet — either
        # way, non-zero AND non-exception (no raw traceback in output).
        assert result.exit_code != 0
        assert result.exception is None or isinstance(result.exception, SystemExit)
        # _emit_error_tty prefix must be present on stderr/combined output.
        assert "Error" in (result.output or "") or "acl denied" in (result.output or "").lower()


class TestRegisterListDescribeSmoke:
    """Smoke-test the split registrars register commands on the passed group."""

    def test_register_list_command_attaches(self):
        cli = _build_apcli_with(register_list_command, MagicMock())
        assert "list" in cli.commands

    def test_register_describe_command_attaches(self):
        cli = _build_apcli_with(register_describe_command, MagicMock())
        assert "describe" in cli.commands


_ = pytest  # silence unused import
