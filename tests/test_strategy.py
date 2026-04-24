"""Tests for pipeline strategy command (FE-11)."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import MagicMock, patch

from apcore_cli.strategy import _PRESET_STEPS, _render_pipeline_table, register_pipeline_command
from click.testing import CliRunner


def _make_step(name: str, pure: bool = False, removable: bool = True, timeout_ms: int | None = None) -> MagicMock:
    """Create a mock pipeline step."""
    step = MagicMock()
    step.name = name
    step.pure = pure
    step.removable = removable
    step.timeout_ms = timeout_ms
    return step


def _make_strategy_obj(steps: list[MagicMock]) -> MagicMock:
    """Create a mock strategy object with a steps list."""
    obj = MagicMock()
    obj.steps = steps
    return obj


def _make_strategy_info(name: str, steps: list[str]) -> MagicMock:
    """Create a mock StrategyInfo dataclass."""
    info = MagicMock()
    info.name = name
    info.step_count = len(steps)
    info.step_names = steps
    return info


def _build_cli_with_executor(executor: MagicMock) -> MagicMock:
    """Build a minimal Click group with the pipeline command registered."""
    import click

    @click.group()
    def cli() -> None:
        pass

    register_pipeline_command(cli, executor)
    return cli


class TestPresetStrategies:
    """All 5 preset strategies must exist in _PRESET_STEPS."""

    def test_all_five_presets_exist(self) -> None:
        assert set(_PRESET_STEPS.keys()) == {"standard", "internal", "testing", "performance", "minimal"}

    def test_standard_preset_has_expected_steps(self) -> None:
        assert "execute" in _PRESET_STEPS["standard"]
        assert "context_creation" in _PRESET_STEPS["standard"]
        assert "return_result" in _PRESET_STEPS["standard"]

    def test_minimal_preset_has_four_steps(self) -> None:
        assert len(_PRESET_STEPS["minimal"]) == 4

    def test_all_presets_non_empty(self) -> None:
        for name, steps in _PRESET_STEPS.items():
            assert steps, f"Preset '{name}' must have at least one step"


class TestStrategyInfoPath:
    """executor.describe_pipeline() returns StrategyInfo — verify table output."""

    def _make_executor_with_strategy_info(
        self, strategy: str = "standard", with_step_objects: bool = False
    ) -> MagicMock:
        executor = MagicMock()
        step_names = _PRESET_STEPS[strategy]
        strategy_info = _make_strategy_info(strategy, step_names)
        executor.describe_pipeline.return_value = strategy_info

        if with_step_objects:
            steps = [_make_step(n) for n in step_names]
            strategy_obj = _make_strategy_obj(steps)
            # Expose via _resolve_strategy_name
            del executor._strategy  # remove auto-created attr
            executor._resolve_strategy_name.return_value = strategy_obj
        else:
            # No _strategy or _resolve_strategy_name — falls back to step_names list
            del executor._strategy
            del executor._resolve_strategy_name

        return executor

    def test_strategy_info_renders_table(self) -> None:
        executor = self._make_executor_with_strategy_info()
        cli = _build_cli_with_executor(executor)
        runner = CliRunner()
        # CliRunner stdout is not a TTY; --format json is the default output mode.
        # Verify that the JSON output contains the expected strategy name.
        result = runner.invoke(cli, ["describe-pipeline", "--strategy", "standard", "--format", "json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["strategy"] == "standard"
        assert data["step_count"] == len(_PRESET_STEPS["standard"])

    def test_strategy_info_json_format(self) -> None:
        executor = self._make_executor_with_strategy_info()
        cli = _build_cli_with_executor(executor)
        runner = CliRunner()
        result = runner.invoke(cli, ["describe-pipeline", "--strategy", "standard", "--format", "json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["strategy"] == "standard"
        assert data["step_count"] == len(_PRESET_STEPS["standard"])
        assert len(data["steps"]) == data["step_count"]
        # Each step must have an index and a name
        for step in data["steps"]:
            assert "index" in step
            assert "name" in step

    def test_strategy_info_with_step_objects(self) -> None:
        executor = self._make_executor_with_strategy_info(with_step_objects=True)
        cli = _build_cli_with_executor(executor)
        runner = CliRunner()
        result = runner.invoke(cli, ["describe-pipeline", "--strategy", "standard", "--format", "json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["strategy"] == "standard"


class TestLegacyResolvePath:
    """executor has _resolve_strategy_name but no describe_pipeline."""

    def _make_legacy_executor(self, strategy: str = "standard") -> MagicMock:
        executor = MagicMock(spec=[])  # no attributes by default
        step_names = _PRESET_STEPS[strategy]
        steps = [_make_step(n) for n in step_names]
        strategy_obj = _make_strategy_obj(steps)

        # Manually add _resolve_strategy_name; it always returns the same strategy_obj
        # regardless of the strategy argument (enough for testing the code path).
        executor._resolve_strategy_name = MagicMock(return_value=strategy_obj)
        return executor

    def test_legacy_path_renders_table(self) -> None:
        executor = self._make_legacy_executor(strategy="standard")
        cli = _build_cli_with_executor(executor)
        runner = CliRunner()
        # CliRunner stdout is not a TTY — output will be JSON regardless of --format table.
        result = runner.invoke(cli, ["describe-pipeline", "--strategy", "standard", "--format", "json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["strategy"] == "standard"
        assert data["step_count"] == len(_PRESET_STEPS["standard"])

    def test_legacy_path_json_format(self) -> None:
        executor = self._make_legacy_executor(strategy="internal")
        cli = _build_cli_with_executor(executor)
        runner = CliRunner()
        result = runner.invoke(cli, ["describe-pipeline", "--strategy", "internal", "--format", "json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["strategy"] == "internal"
        assert data["step_count"] == len(_PRESET_STEPS["internal"])


class TestPresetFallbackPath:
    """executor has neither describe_pipeline nor _resolve_strategy_name."""

    def _make_bare_executor(self) -> MagicMock:
        return MagicMock(spec=[])  # no relevant attrs

    def test_preset_fallback_renders_steps(self) -> None:
        executor = self._make_bare_executor()
        cli = _build_cli_with_executor(executor)
        runner = CliRunner()
        # CliRunner stdout is not a TTY — use JSON format to inspect output reliably.
        result = runner.invoke(cli, ["describe-pipeline", "--strategy", "minimal", "--format", "json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["strategy"] == "minimal"
        step_names = [s["name"] for s in data["steps"]]
        for step in _PRESET_STEPS["minimal"]:
            assert step in step_names

    def test_preset_fallback_json_format(self) -> None:
        executor = self._make_bare_executor()
        cli = _build_cli_with_executor(executor)
        runner = CliRunner()
        result = runner.invoke(cli, ["describe-pipeline", "--strategy", "performance", "--format", "json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["strategy"] == "performance"
        assert data["step_count"] == len(_PRESET_STEPS["performance"])
        # Preset fallback only has index + name (no pure/removable/timeout)
        for step in data["steps"]:
            assert "index" in step
            assert "name" in step


class TestRenderPipelineTableHelper:
    """Unit tests for the _render_pipeline_table helper."""

    def test_json_format_emits_json(self) -> None:
        steps = [{"name": "execute", "pure": False, "removable": True, "timeout_ms": None}]
        output = StringIO()
        with (
            patch("click.echo", side_effect=lambda s, **kw: output.write(str(s) + "\n")),
            patch("apcore_cli.strategy.sys.stdout") as mock_stdout,
        ):
            # Fake isatty to return True so TTY branch would be taken if format were "table"
            mock_stdout.isatty.return_value = True
            _render_pipeline_table(steps, "json", "test", 1)
        data = json.loads(output.getvalue())
        assert data["strategy"] == "test"
        assert data["step_count"] == 1

    def test_table_name_only_when_all_defaults(self) -> None:
        """When all steps have default metadata, render name-only table (no Pure/Removable/Timeout cols)."""
        steps = [
            {"name": "context_creation", "pure": False, "removable": True, "timeout_ms": None},
            {"name": "execute", "pure": False, "removable": True, "timeout_ms": None},
        ]
        output_lines: list[str] = []
        with (
            patch("click.echo", side_effect=lambda s, **kw: output_lines.append(str(s))),
            patch("apcore_cli.strategy.sys.stdout") as mock_stdout,
        ):
            mock_stdout.isatty.return_value = True
            _render_pipeline_table(steps, "table", "standard", 2)
        combined = "\n".join(output_lines)
        # Name-only mode: should NOT have Pure/Removable columns
        assert "Pure" not in combined
        assert "Removable" not in combined
        assert "context_creation" in combined

    def test_table_full_metadata_when_non_defaults(self) -> None:
        """When any step has non-default metadata, render full-metadata table."""
        steps = [
            {"name": "execute", "pure": True, "removable": True, "timeout_ms": None},
        ]
        output_lines: list[str] = []
        with (
            patch("click.echo", side_effect=lambda s, **kw: output_lines.append(str(s))),
            patch("apcore_cli.strategy.sys.stdout") as mock_stdout,
        ):
            mock_stdout.isatty.return_value = True
            _render_pipeline_table(steps, "table", "custom", 1)
        combined = "\n".join(output_lines)
        assert "Pure" in combined
        assert "Removable" in combined
