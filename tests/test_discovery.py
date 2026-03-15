"""Tests for Discovery commands (FE-04)."""

import json
from unittest.mock import MagicMock

import click
from click.testing import CliRunner

from apcore_cli.discovery import register_discovery_commands


def _make_mock_module(module_id, description="A module.", tags=None):
    m = MagicMock()
    m.module_id = module_id
    m.canonical_id = module_id
    m.description = description
    m.tags = tags or []
    m.input_schema = None
    m.output_schema = None
    m.annotations = None
    m.metadata = {}
    return m


def _make_cli_with_modules(modules):
    """Create a CLI group with discovery commands and mock registry."""
    registry = MagicMock()
    registry.list.return_value = [m.module_id for m in modules]
    defs = {m.module_id: m for m in modules}
    registry.get_definition.side_effect = lambda mid, **kw: defs.get(mid)

    @click.group()
    def cli():
        pass

    register_discovery_commands(cli, registry)
    return cli


class TestListCommand:
    def test_list_cmd_shows_modules(self):
        modules = [
            _make_mock_module("math.add", "Add.", ["math"]),
            _make_mock_module("text.summarize", "Summarize.", ["text"]),
        ]
        cli = _make_cli_with_modules(modules)
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        ids = [m["id"] for m in data]
        assert "math.add" in ids
        assert "text.summarize" in ids

    def test_list_cmd_empty_registry(self):
        cli = _make_cli_with_modules([])
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--format", "table"])
        assert result.exit_code == 0
        assert "No modules found." in result.output

    def test_list_cmd_tag_filter_single(self):
        modules = [
            _make_mock_module("math.add", "Add.", ["math"]),
            _make_mock_module("text.summarize", "Summarize.", ["text"]),
        ]
        cli = _make_cli_with_modules(modules)
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--tag", "math", "--format", "json"])
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["id"] == "math.add"

    def test_list_cmd_tag_filter_and(self):
        modules = [
            _make_mock_module("math.add", "Add.", ["math", "core"]),
            _make_mock_module("math.sub", "Sub.", ["math"]),
        ]
        cli = _make_cli_with_modules(modules)
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--tag", "math", "--tag", "core", "--format", "json"])
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["id"] == "math.add"

    def test_list_cmd_tag_no_match(self):
        modules = [_make_mock_module("math.add", "Add.", ["math"])]
        cli = _make_cli_with_modules(modules)
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--tag", "nonexistent", "--format", "table"])
        assert result.exit_code == 0
        assert "No modules found matching tags: nonexistent" in result.output

    def test_list_cmd_format_json(self):
        modules = [_make_mock_module("x", "X.")]
        cli = _make_cli_with_modules(modules)
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--format", "json"])
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_list_cmd_invalid_format(self):
        cli = _make_cli_with_modules([])
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--format", "yaml"])
        assert result.exit_code == 2


class TestDescribeCommand:
    def test_describe_valid_module(self):
        modules = [_make_mock_module("math.add", "Add two numbers.", ["math"])]
        cli = _make_cli_with_modules(modules)
        runner = CliRunner()
        result = runner.invoke(cli, ["describe", "math.add", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "math.add"

    def test_describe_not_found(self):
        cli = _make_cli_with_modules([])
        runner = CliRunner()
        result = runner.invoke(cli, ["describe", "nonexistent"])
        assert result.exit_code == 44

    def test_describe_invalid_id(self):
        cli = _make_cli_with_modules([])
        runner = CliRunner()
        result = runner.invoke(cli, ["describe", "INVALID!"])
        assert result.exit_code == 2

    def test_describe_json_format(self):
        m = _make_mock_module("math.add", "Add.", ["math"])
        m.input_schema = {"type": "object"}
        cli = _make_cli_with_modules([m])
        runner = CliRunner()
        result = runner.invoke(cli, ["describe", "math.add", "--format", "json"])
        data = json.loads(result.output)
        assert "input_schema" in data

    def test_describe_no_annotations(self):
        m = _make_mock_module("simple", "Simple.")
        m.annotations = None
        cli = _make_cli_with_modules([m])
        runner = CliRunner()
        result = runner.invoke(cli, ["describe", "simple", "--format", "json"])
        data = json.loads(result.output)
        assert "annotations" not in data
