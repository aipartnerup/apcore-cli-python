"""Tests for Output Formatter (FE-08)."""

import json
from unittest.mock import MagicMock

from apcore_cli.output import (
    _truncate,
    format_exec_result,
    format_module_detail,
    format_module_list,
    resolve_format,
)


def _make_mock_module(
    module_id="math.add",
    description="Add two numbers.",
    tags=None,
    input_schema=None,
    output_schema=None,
    annotations=None,
    metadata=None,
):
    m = MagicMock()
    m.module_id = module_id
    m.canonical_id = module_id
    m.description = description
    m.tags = tags or []
    m.input_schema = input_schema
    m.output_schema = output_schema
    m.annotations = annotations
    m.metadata = metadata or {}
    return m


class TestResolveFormat:
    def test_resolve_format_explicit_json(self):
        assert resolve_format("json") == "json"

    def test_resolve_format_explicit_table(self):
        assert resolve_format("table") == "table"

    def test_resolve_format_none_tty(self, monkeypatch):
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)
        assert resolve_format(None) == "table"

    def test_resolve_format_none_non_tty(self, monkeypatch):
        monkeypatch.setattr("sys.stdout.isatty", lambda: False)
        assert resolve_format(None) == "json"


class TestTruncate:
    def test_truncate_short(self):
        assert _truncate("hello", 80) == "hello"

    def test_truncate_exact(self):
        text = "x" * 80
        assert _truncate(text, 80) == text

    def test_truncate_long(self):
        text = "x" * 100
        result = _truncate(text, 80)
        assert len(result) == 80
        assert result.endswith("...")


class TestFormatModuleList:
    def test_format_list_table_with_modules(self, capsys):
        modules = [
            _make_mock_module("math.add", "Add two numbers.", ["math"]),
            _make_mock_module("text.summarize", "Summarize text.", ["text"]),
        ]
        format_module_list(modules, "table")
        out = capsys.readouterr().out
        assert "math.add" in out
        assert "text.summarize" in out

    def test_format_list_table_empty(self, capsys):
        format_module_list([], "table")
        out = capsys.readouterr().out
        assert "No modules found." in out

    def test_format_list_table_empty_with_tags(self, capsys):
        format_module_list([], "table", filter_tags=("math",))
        out = capsys.readouterr().out
        assert "No modules found matching tags: math" in out

    def test_format_list_json_with_modules(self, capsys):
        modules = [
            _make_mock_module("math.add", "Add.", ["math"]),
        ]
        format_module_list(modules, "json")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert len(data) == 1
        assert data[0]["id"] == "math.add"

    def test_format_list_json_uses_display_overlay(self, capsys):
        """JSON output must use display overlay alias, description, and tags — not raw scanner values."""
        m = _make_mock_module(
            "payment.get_status_payment__payment_id_.get",
            "Raw scanner description",
            tags=["raw"],
            metadata={
                "display": {
                    "alias": "pay-status",
                    "tags": ["payment", "v2"],
                    "cli": {
                        "alias": "pay-status",
                        "description": "Check payment status",
                    },
                }
            },
        )
        format_module_list([m], "json")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data[0]["id"] == "pay-status"
        assert data[0]["description"] == "Check payment status"
        assert data[0]["tags"] == ["payment", "v2"]

    def test_format_list_json_falls_back_to_scanner_when_no_overlay(self, capsys):
        """JSON output falls back to scanner values when no display overlay is present."""
        m = _make_mock_module("math.add", "Add two numbers.", ["math"])
        format_module_list([m], "json")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data[0]["id"] == "math.add"
        assert data[0]["description"] == "Add two numbers."
        assert data[0]["tags"] == ["math"]

    def test_format_list_json_empty(self, capsys):
        format_module_list([], "json")
        out = capsys.readouterr().out
        assert json.loads(out) == []

    def test_format_list_description_truncated(self, capsys):
        modules = [_make_mock_module("x", "a" * 120)]
        format_module_list(modules, "table")
        out = capsys.readouterr().out
        # Description should be truncated (either "..." or unicode "…")
        assert "..." in out or "\u2026" in out


class TestFormatModuleDetail:
    def test_format_detail_table_full(self, capsys):
        m = _make_mock_module(
            "math.add",
            "Add two numbers.",
            tags=["math", "core"],
            input_schema={"properties": {"a": {"type": "integer"}}},
            output_schema={"properties": {"sum": {"type": "integer"}}},
            annotations={"readonly": True},
        )
        format_module_detail(m, "table")
        out = capsys.readouterr().out
        assert "math.add" in out
        assert "Description:" in out
        assert "math, core" in out

    def test_format_detail_table_minimal(self, capsys):
        m = _make_mock_module("simple", "Simple module.")
        m.input_schema = None
        m.output_schema = None
        m.annotations = None
        format_module_detail(m, "table")
        out = capsys.readouterr().out
        assert "simple" in out
        assert "Output Schema" not in out

    def test_format_detail_json_full(self, capsys):
        m = _make_mock_module(
            "math.add",
            "Add.",
            tags=["math"],
            input_schema={"type": "object"},
            annotations={"readonly": True},
        )
        format_module_detail(m, "json")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["id"] == "math.add"
        assert "input_schema" in data
        assert "annotations" in data

    def test_format_detail_json_no_none(self, capsys):
        m = _make_mock_module("simple", "Simple.")
        m.input_schema = None
        m.output_schema = None
        m.annotations = None
        format_module_detail(m, "json")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "output_schema" not in data


class TestFormatExecResult:
    def test_format_exec_dict(self, capsys):
        format_exec_result({"sum": 15})
        out = capsys.readouterr().out
        assert json.loads(out) == {"sum": 15}

    def test_format_exec_list(self, capsys):
        format_exec_result([1, 2, 3])
        out = capsys.readouterr().out
        assert json.loads(out) == [1, 2, 3]

    def test_format_exec_string(self, capsys):
        format_exec_result("hello world")
        out = capsys.readouterr().out
        assert "hello world" in out

    def test_format_exec_none(self, capsys):
        format_exec_result(None)
        out = capsys.readouterr().out
        assert out == ""

    def test_format_exec_other(self, capsys):
        format_exec_result(42)
        out = capsys.readouterr().out
        assert "42" in out

    def test_format_exec_non_serializable(self, capsys):
        from datetime import datetime

        format_exec_result({"ts": datetime(2026, 1, 1)})
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "ts" in data
