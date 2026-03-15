"""Shell Integration — completion scripts and man pages (FE-06)."""

from __future__ import annotations

import sys
from datetime import date

import click

from apcore_cli import __version__

# Shell snippet for dynamic module ID completion (shared across shells)
_MODULE_LIST_CMD = (
    "apcore-cli list --format json 2>/dev/null"
    ' | python3 -c "import sys,json;'
    "[print(m['id']) for m in json.load(sys.stdin)]\" 2>/dev/null"
)


def _generate_bash_completion() -> str:
    return (
        "_apcore_cli_completion() {\n"
        "    local cur prev opts\n"
        "    COMPREPLY=()\n"
        '    cur="${COMP_WORDS[COMP_CWORD]}"\n'
        '    prev="${COMP_WORDS[COMP_CWORD-1]}"\n'
        "\n"
        "    if [[ ${COMP_CWORD} -eq 1 ]]; then\n"
        '        opts="exec list describe completion man"\n'
        '        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )\n'
        "        return 0\n"
        "    fi\n"
        "\n"
        '    if [[ "${COMP_WORDS[1]}" == "exec" && ${COMP_CWORD} -eq 2 ]]; then\n'
        f"        local modules=$({_MODULE_LIST_CMD})\n"
        '        COMPREPLY=( $(compgen -W "${modules}" -- ${cur}) )\n'
        "        return 0\n"
        "    fi\n"
        "}\n"
        "complete -F _apcore_cli_completion apcore-cli\n"
    )


def _generate_zsh_completion() -> str:
    return (
        "#compdef apcore-cli\n"
        "\n"
        "_apcore_cli() {\n"
        "    local -a commands\n"
        "    commands=(\n"
        "        'exec:Execute an apcore module'\n"
        "        'list:List available modules'\n"
        "        'describe:Show module details'\n"
        "        'completion:Generate shell completion script'\n"
        "        'man:Generate man page'\n"
        "    )\n"
        "\n"
        "    _arguments -C \\\n"
        "        '1:command:->command' \\\n"
        "        '*::arg:->args'\n"
        "\n"
        '    case "$state" in\n'
        "        command)\n"
        "            _describe -t commands 'apcore-cli commands' commands\n"
        "            ;;\n"
        "        args)\n"
        '            case "${words[1]}" in\n'
        "                exec)\n"
        "                    local modules\n"
        f"                    modules=($({_MODULE_LIST_CMD}))\n"
        "                    compadd -a modules\n"
        "                    ;;\n"
        "            esac\n"
        "            ;;\n"
        "    esac\n"
        "}\n"
        "\n"
        "compdef _apcore_cli apcore-cli\n"
    )


def _generate_fish_completion() -> str:
    # Build the dynamic completion command for fish (needs escaped quotes)
    fish_dyn = _MODULE_LIST_CMD.replace('"', '\\"').replace("'", "\\'")
    return (
        "# Fish completions for apcore-cli\n"
        'complete -c apcore-cli -n "__fish_use_subcommand"'
        ' -a exec -d "Execute an apcore module"\n'
        'complete -c apcore-cli -n "__fish_use_subcommand"'
        ' -a list -d "List available modules"\n'
        'complete -c apcore-cli -n "__fish_use_subcommand"'
        ' -a describe -d "Show module details"\n'
        'complete -c apcore-cli -n "__fish_use_subcommand"'
        ' -a completion -d "Generate shell completion script"\n'
        'complete -c apcore-cli -n "__fish_use_subcommand"'
        ' -a man -d "Generate man page"\n'
        "\n"
        'complete -c apcore-cli -n "__fish_seen_subcommand_from exec"'
        f' -a "({fish_dyn})"\n'
    )


def _generate_man_page(command_name: str, command: click.Command | None, cli: click.Group) -> str:
    """Generate a roff-formatted man page for a command."""
    today = date.today().strftime("%Y-%m-%d")
    cmd_upper = command_name.upper()

    sections = []
    sections.append(f'.TH "APCORE-CLI-{cmd_upper}" "1" "{today}" "apcore-cli {__version__}" "apcore-cli Manual"')
    sections.append(".SH NAME")
    if command:
        desc = command.help or command_name
        sections.append(f"apcore-cli-{command_name} \\- {desc}")
    else:
        sections.append(f"apcore-cli-{command_name}")

    sections.append(".SH SYNOPSIS")
    sections.append(f"\\fBapcore-cli {command_name}\\fR [OPTIONS] [ARGUMENTS]")

    if command and command.help:
        sections.append(".SH DESCRIPTION")
        sections.append(command.help)

    if command and command.params:
        sections.append(".SH OPTIONS")
        for param in command.params:
            if isinstance(param, click.Option):
                flag = ", ".join(param.opts + getattr(param, "secondary_opts", []))
                type_name = param.type.name if hasattr(param.type, "name") else "VALUE"
                sections.append(".TP")
                sections.append(f"\\fB{flag}\\fR \\fI{type_name}\\fR")
                if param.help:
                    sections.append(param.help)

    sections.append(".SH EXIT CODES")
    sections.append(".TP\n\\fB0\\fR\nSuccess.")
    sections.append(".TP\n\\fB1\\fR\nModule execution error.")
    sections.append(".TP\n\\fB2\\fR\nInvalid CLI input.")
    sections.append(".TP\n\\fB44\\fR\nModule not found, disabled, or load error.")
    sections.append(".TP\n\\fB45\\fR\nSchema validation error.")
    sections.append(".TP\n\\fB46\\fR\nApproval denied or timed out.")
    sections.append(".TP\n\\fB47\\fR\nConfiguration error.")
    sections.append(".TP\n\\fB48\\fR\nSchema circular reference.")
    sections.append(".TP\n\\fB77\\fR\nACL denied.")
    sections.append(".TP\n\\fB130\\fR\nExecution cancelled (SIGINT).")

    sections.append(".SH SEE ALSO")
    sections.append("\\fBapcore-cli\\fR(1), \\fBapcore-cli-list\\fR(1), \\fBapcore-cli-describe\\fR(1)")

    return "\n".join(sections)


def register_shell_commands(cli: click.Group) -> None:
    """Register completion and man commands."""

    @cli.command("completion")
    @click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
    def completion_cmd(shell: str) -> None:
        """Generate shell completion script."""
        generators = {
            "bash": _generate_bash_completion,
            "zsh": _generate_zsh_completion,
            "fish": _generate_fish_completion,
        }
        click.echo(generators[shell]())

    @cli.command("man")
    @click.argument("command")
    @click.pass_context
    def man_cmd(ctx: click.Context, command: str) -> None:
        """Generate man page for a command."""
        parent = ctx.parent
        if parent is None:
            click.echo(f"Error: Unknown command '{command}'.", err=True)
            sys.exit(2)

        parent_group = parent.command
        cmd = parent_group.commands.get(command) if isinstance(parent_group, click.Group) else None

        if cmd is None and command not in ("exec", "list", "describe", "completion", "man"):
            click.echo(f"Error: Unknown command '{command}'.", err=True)
            sys.exit(2)

        roff = _generate_man_page(command, cmd, cli)
        click.echo(roff)
