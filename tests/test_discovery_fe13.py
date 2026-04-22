"""Coverage-focused tests for FE-13 discovery split-registrar edges.

Covers ``register_exec_command`` runtime paths (module not found, invalid
JSON --input, successful call with inline JSON) and ``register_validate_command``
failure paths that aren't exercised by the batched-wrapper tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock

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


class TestRegisterListDescribeSmoke:
    """Smoke-test the split registrars register commands on the passed group."""

    def test_register_list_command_attaches(self):
        cli = _build_apcli_with(register_list_command, MagicMock())
        assert "list" in cli.commands

    def test_register_describe_command_attaches(self):
        cli = _build_apcli_with(register_describe_command, MagicMock())
        assert "describe" in cli.commands


_ = pytest  # silence unused import
