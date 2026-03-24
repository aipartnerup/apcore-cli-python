"""Tests for init command (Phase 1)."""

import click
import pytest
from click.testing import CliRunner

from apcore_cli.init_cmd import register_init_command


@pytest.fixture
def cli():
    @click.group()
    def root():
        pass

    register_init_command(root)
    return root


class TestInitModule:
    def test_init_convention_creates_file(self, cli, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "module", "ops.deploy", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Created" in result.output
        # Check file exists
        files = list(tmp_path.rglob("*.py"))
        assert len(files) >= 1

    def test_init_decorator_creates_file(self, cli, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "module", "ops.deploy", "--style", "decorator", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        files = list(tmp_path.rglob("*.py"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "@module" in content
        assert 'id="ops.deploy"' in content

    def test_init_binding_creates_yaml(self, cli, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "module", "ops.deploy", "--style", "binding", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        yaml_files = list(tmp_path.rglob("*.yaml"))
        assert len(yaml_files) == 1
        content = yaml_files[0].read_text()
        assert "ops.deploy" in content

    def test_init_convention_has_cli_group(self, cli, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "module", "ops.deploy", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        files = list(tmp_path.rglob("*.py"))
        content = files[0].read_text()
        assert "CLI_GROUP" in content

    def test_init_with_description(self, cli, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "init",
                "module",
                "ops.deploy",
                "--dir",
                str(tmp_path),
                "-d",
                "Deploy to production",
            ],
        )
        assert result.exit_code == 0
        files = list(tmp_path.rglob("*.py"))
        content = files[0].read_text()
        assert "Deploy to production" in content

    def test_init_module_help(self, cli):
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "module", "--help"])
        assert result.exit_code == 0
        assert "decorator" in result.output
        assert "convention" in result.output
        assert "binding" in result.output
