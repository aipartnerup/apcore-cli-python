"""Tests for Shell Integration (FE-06)."""

import click
from click.testing import CliRunner

from apcore_cli.shell import (
    _generate_bash_completion,
    _generate_fish_completion,
    _generate_zsh_completion,
    register_shell_commands,
)


def _make_cli():
    @click.group()
    def cli():
        pass

    @cli.command("list")
    @click.option("--tag", multiple=True)
    def list_cmd(tag):
        """List available modules."""
        pass

    @cli.command("exec")
    @click.argument("module_id", required=False)
    def exec_cmd(module_id):
        """Execute an apcore module."""
        pass

    register_shell_commands(cli)
    return cli


class TestBashCompletion:
    def test_bash_completion_contains_subcommands(self):
        script = _generate_bash_completion()
        for cmd in ["exec", "list", "describe", "completion", "man"]:
            assert cmd in script

    def test_bash_completion_has_complete_directive(self):
        script = _generate_bash_completion()
        assert "complete -F _apcore_cli_completion apcore-cli" in script

    def test_bash_completion_valid_syntax(self):
        # Just check it's a non-empty string
        script = _generate_bash_completion()
        assert len(script) > 100


class TestZshFishCompletion:
    def test_zsh_completion_contains_compdef(self):
        script = _generate_zsh_completion()
        assert "compdef" in script

    def test_zsh_completion_contains_subcommands(self):
        script = _generate_zsh_completion()
        for cmd in ["exec", "list", "describe"]:
            assert cmd in script

    def test_fish_completion_contains_complete(self):
        script = _generate_fish_completion()
        assert "complete -c apcore-cli" in script

    def test_fish_completion_contains_subcommands(self):
        script = _generate_fish_completion()
        for cmd in ["exec", "list", "describe"]:
            assert cmd in script


class TestCompletionCommand:
    def test_completion_bash(self):
        cli = _make_cli()
        runner = CliRunner()
        result = runner.invoke(cli, ["completion", "bash"])
        assert result.exit_code == 0
        assert "complete" in result.output

    def test_completion_zsh(self):
        cli = _make_cli()
        runner = CliRunner()
        result = runner.invoke(cli, ["completion", "zsh"])
        assert result.exit_code == 0
        assert "compdef" in result.output

    def test_completion_fish(self):
        cli = _make_cli()
        runner = CliRunner()
        result = runner.invoke(cli, ["completion", "fish"])
        assert result.exit_code == 0
        assert "complete -c apcore-cli" in result.output

    def test_completion_invalid_shell(self):
        cli = _make_cli()
        runner = CliRunner()
        result = runner.invoke(cli, ["completion", "invalid"])
        assert result.exit_code == 2


class TestManCommand:
    def test_man_list(self):
        cli = _make_cli()
        runner = CliRunner()
        result = runner.invoke(cli, ["man", "list"])
        assert result.exit_code == 0
        assert ".TH" in result.output
        assert "APCORE-CLI-LIST" in result.output

    def test_man_exec(self):
        cli = _make_cli()
        runner = CliRunner()
        result = runner.invoke(cli, ["man", "exec"])
        assert result.exit_code == 0
        assert ".TH" in result.output

    def test_man_unknown_command(self):
        cli = _make_cli()
        runner = CliRunner()
        result = runner.invoke(cli, ["man", "nonexistent"])
        assert result.exit_code == 2

    def test_man_contains_exit_codes(self):
        cli = _make_cli()
        runner = CliRunner()
        result = runner.invoke(cli, ["man", "list"])
        assert "EXIT CODES" in result.output
