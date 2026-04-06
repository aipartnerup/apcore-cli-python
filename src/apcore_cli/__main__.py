"""Entry point for apcore-cli (FE-01)."""

from __future__ import annotations

import logging
import os
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _get_version
from typing import Any

import click

from apcore_cli.cli import GroupedModuleGroup, set_audit_logger, set_verbose_help
from apcore_cli.config import ConfigResolver
from apcore_cli.discovery import register_discovery_commands
from apcore_cli.security.audit import AuditLogger
from apcore_cli.shell import configure_man_help, register_shell_commands

try:
    __version__ = _get_version("apcore-cli")
except PackageNotFoundError:
    __version__ = "unknown"

logger = logging.getLogger("apcore_cli")

EXIT_CONFIG_NOT_FOUND = 47


def _extract_argv_option(argv: list[str] | None, flag: str) -> str | None:
    """Extract an option value from argv before Click parses it.

    This is needed because certain options must be resolved before Click runs.
    Returns None if the flag is not present.
    """
    args = argv if argv is not None else sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == flag and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith(f"{flag}="):
            return arg.split("=", 1)[1]
    return None


def _extract_extensions_dir(argv: list[str] | None = None) -> str | None:
    """Extract --extensions-dir value from argv before Click parses it."""
    return _extract_argv_option(argv, "--extensions-dir")


def _extract_commands_dir(argv: list[str] | None = None) -> str | None:
    """Extract --commands-dir value from argv before Click parses it."""
    return _extract_argv_option(argv, "--commands-dir")


def _extract_binding_path(argv: list[str] | None = None) -> str | None:
    """Extract --binding value from argv before Click parses it."""
    return _extract_argv_option(argv, "--binding")


def _has_verbose_flag(argv: list[str] | None = None) -> bool:
    """Check if --verbose is present in argv (pre-parse, before Click)."""
    args = argv if argv is not None else sys.argv[1:]
    return "--verbose" in args


def create_cli(
    extensions_dir: str | None = None,
    prog_name: str | None = None,
    commands_dir: str | None = None,
    binding_path: str | None = None,
    registry: Any | None = None,
    executor: Any | None = None,
    extra_commands: list[Any] | None = None,
) -> click.Group:
    """Create the CLI application.

    Args:
        extensions_dir: Override for extensions directory.
                        When None, resolves via ConfigResolver (env/file/default).
        prog_name: Name shown in help text and version output.
                   Defaults to the basename of sys.argv[0], so downstream projects
                   that install their own entry-point script get the correct name
                   automatically (e.g. ``mycli`` instead of ``apcore-cli``).
        commands_dir: Directory containing convention-based modules.
                      When set, scans for plain-function modules and registers
                      them via ConventionScanner (requires apcore-toolkit).
        binding_path: Path to binding.yaml file or directory for display resolution.
                      When set, applies DisplayResolver to convention-scanned modules
                      (requires apcore-toolkit).
        registry: Pre-populated apcore Registry instance. When provided, skips
                  filesystem discovery entirely. Useful for frameworks that register
                  modules at runtime (e.g. apflow's bridge).
        executor: Pre-built apcore Executor instance. When provided alongside
                  registry, skips Executor construction. If omitted but registry
                  is provided, an Executor is built from the given registry.
    """
    if prog_name is None:
        prog_name = os.path.basename(sys.argv[0]) or "apcore-cli"

    # Pre-parse --verbose before Click runs so build_module_command knows
    # whether to hide built-in options.
    verbose = _has_verbose_flag()
    set_verbose_help(verbose)

    # Resolve CLI log level (3-tier precedence, evaluated before Click runs):
    #   APCORE_CLI_LOGGING_LEVEL (CLI-specific) > APCORE_LOGGING_LEVEL (global) > WARNING
    # The --log-level flag (parsed later) can further override at runtime.
    _cli_level_str = os.environ.get("APCORE_CLI_LOGGING_LEVEL", "").upper()
    _global_level_str = os.environ.get("APCORE_LOGGING_LEVEL", "").upper()
    _active_level_str = _cli_level_str or _global_level_str
    _default_level = getattr(logging, _active_level_str, logging.WARNING) if _active_level_str else logging.WARNING
    logging.basicConfig(level=_default_level, format="%(levelname)s: %(message)s")
    # basicConfig is a no-op if handlers already exist; always set the root level explicitly.
    logging.getLogger().setLevel(_default_level)
    # Silence noisy upstream apcore loggers unless the user requests verbose output.
    # Always set explicitly so the level is deterministic regardless of prior state.
    apcore_level = _default_level if _default_level <= logging.INFO else logging.ERROR
    logging.getLogger("apcore").setLevel(apcore_level)

    config = ConfigResolver()

    if extensions_dir is not None:
        ext_dir = extensions_dir
    else:
        ext_dir = config.resolve(
            "extensions.root",
            cli_flag="--extensions-dir",
            env_var="APCORE_EXTENSIONS_ROOT",
        )

    help_text_max_length = config.resolve(
        "cli.help_text_max_length",
        env_var="APCORE_CLI_HELP_TEXT_MAX_LENGTH",
    )
    try:
        help_text_max_length = int(help_text_max_length)
    except (TypeError, ValueError):
        help_text_max_length = 1000

    if executor is not None and registry is None:
        raise ValueError("executor requires registry — pass both or neither")

    if registry is not None:
        # Pre-populated registry provided — skip filesystem discovery.
        try:
            from apcore import Executor as _Executor

            if executor is None:
                executor = _Executor(registry)
            logger.info("Using pre-populated registry (%d modules).", len(list(registry.list())))
        except Exception as e:
            click.echo(
                f"Error: Failed to initialize executor from provided registry: {e}",
                err=True,
            )
            sys.exit(EXIT_CONFIG_NOT_FOUND)
    else:
        # Standard path: discover modules from filesystem.
        ext_dir_missing = not os.path.exists(ext_dir)
        ext_dir_unreadable = not ext_dir_missing and not os.access(ext_dir, os.R_OK)

        if ext_dir_missing:
            click.echo(
                f"Error: Extensions directory not found: '{ext_dir}'. Set APCORE_EXTENSIONS_ROOT or verify the path.",
                err=True,
            )
            sys.exit(EXIT_CONFIG_NOT_FOUND)

        if ext_dir_unreadable:
            click.echo(
                f"Error: Cannot read extensions directory: '{ext_dir}'. Check permissions.",
                err=True,
            )
            sys.exit(EXIT_CONFIG_NOT_FOUND)

        try:
            from apcore import Executor as _Executor
            from apcore import Registry as _Registry

            registry = _Registry(extensions_dir=ext_dir)
            try:
                logger.debug("Loading extensions from %s", ext_dir)
                count = registry.discover()
                logger.info("Initialized apcore-cli with %d modules.", count)
            except Exception as e:
                logger.warning("Discovery failed: %s", e)

            # Convention module discovery
            if commands_dir is not None:
                try:
                    from apcore_toolkit import RegistryWriter
                    from apcore_toolkit.convention_scanner import ConventionScanner

                    conv_scanner = ConventionScanner()
                    conv_modules = conv_scanner.scan(commands_dir)
                    if conv_modules:
                        if binding_path is not None:
                            try:
                                from apcore_toolkit import DisplayResolver

                                display_resolver = DisplayResolver()
                                conv_modules = display_resolver.resolve(conv_modules, binding_path=binding_path)
                                logger.info(
                                    "DisplayResolver: applied binding from %s",
                                    binding_path,
                                )
                            except ImportError:
                                logger.warning("DisplayResolver not available in apcore-toolkit")
                        writer = RegistryWriter()
                        writer.write(conv_modules, registry)
                        logger.info(
                            "Convention scanner: registered %d modules from %s",
                            len(conv_modules),
                            commands_dir,
                        )
                except ImportError:
                    logger.warning("apcore-toolkit not installed — convention module scanning unavailable")
                except Exception as e:
                    logger.warning("Convention module scanning failed: %s", e)

            executor = _Executor(registry)
        except Exception as e:
            click.echo(f"Error: Failed to initialize registry: {e}", err=True)
            sys.exit(EXIT_CONFIG_NOT_FOUND)

    # Initialize audit logger
    try:
        audit_logger = AuditLogger()
        set_audit_logger(audit_logger)
    except Exception as e:
        logger.warning("Failed to initialize audit logger: %s", e)

    # Wire CliApprovalHandler to Executor (FE-11 §3.5)
    try:
        import contextlib

        from apcore_cli.approval import CliApprovalHandler

        approval_timeout = 60
        with contextlib.suppress(TypeError, ValueError):
            approval_timeout = int(config.resolve("cli.approval_timeout", env_var="APCORE_CLI_APPROVAL_TIMEOUT") or 60)
        handler = CliApprovalHandler(auto_approve=False, timeout=approval_timeout)
        if hasattr(executor, "set_approval_handler"):
            executor.set_approval_handler(handler)
            logger.debug("CliApprovalHandler wired to Executor (timeout=%ds).", approval_timeout)
    except Exception as e:
        logger.debug("Could not wire CliApprovalHandler: %s", e)

    @click.group(
        cls=GroupedModuleGroup,
        registry=registry,
        executor=executor,
        help_text_max_length=help_text_max_length,
        name=prog_name,
        help="CLI adapter for the apcore module ecosystem.",
    )
    @click.version_option(
        version=__version__,
        prog_name=prog_name,
    )
    @click.option(
        "--extensions-dir",
        "extensions_dir_opt",
        default=None,
        help="Path to apcore extensions directory.",
    )
    @click.option(
        "--commands-dir",
        "commands_dir_opt",
        default=None,
        help="Path to convention-based commands directory.",
    )
    @click.option(
        "--binding",
        "binding_opt",
        default=None,
        help="Path to binding.yaml file or directory for display resolution.",
    )
    @click.option(
        "--log-level",
        default=None,
        type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
        help="Log verbosity. Overrides APCORE_CLI_LOGGING_LEVEL and APCORE_LOGGING_LEVEL env vars.",
    )
    @click.option(
        "--verbose",
        "verbose_help",
        is_flag=True,
        default=False,
        help="Show all options in help output (including built-in apcore options).",
    )
    @click.pass_context
    def cli(
        ctx: click.Context,
        extensions_dir_opt: str | None = None,
        commands_dir_opt: str | None = None,
        binding_opt: str | None = None,
        log_level: str | None = None,
        verbose_help: bool = False,
    ) -> None:
        if log_level is not None:
            # basicConfig() is a no-op once handlers exist; set level on the root logger directly.
            level = getattr(logging, log_level.upper(), logging.WARNING)
            logging.getLogger().setLevel(level)
            # Keep apcore logger in sync: verbose when user asks for it, quiet otherwise.
            apcore_level = level if level <= logging.INFO else logging.ERROR
            logging.getLogger("apcore").setLevel(apcore_level)
        ctx.ensure_object(dict)
        ctx.obj["extensions_dir"] = ext_dir
        ctx.obj["verbose_help"] = verbose_help

    # Register discovery commands (list, describe)
    register_discovery_commands(cli, registry)

    # Register validate command (FE-11 §3.1)
    from apcore_cli.discovery import register_validate_command

    register_validate_command(cli, registry, executor)

    # Register system management commands (FE-11 §3.2) — no-op if system modules unavailable
    from apcore_cli.system_cmd import register_system_commands

    register_system_commands(cli, executor)

    # Register pipeline introspection command (FE-11 §3.8)
    from apcore_cli.strategy import register_pipeline_command

    register_pipeline_command(cli, executor)

    # Register shell integration commands
    register_shell_commands(cli, prog_name=prog_name)

    # Register --help --man support
    configure_man_help(cli, prog_name, __version__)

    # Register init scaffolding command
    from apcore_cli.init_cmd import register_init_command

    register_init_command(cli)

    # Register extra commands from downstream projects (FE-11 §3.11)
    if extra_commands:
        from apcore_cli.cli import BUILTIN_COMMANDS

        for cmd in extra_commands:
            cmd_name = getattr(cmd, "name", None)
            if cmd_name and cmd_name in BUILTIN_COMMANDS:
                msg = f"Extra command '{cmd_name}' conflicts with built-in command."
                raise ValueError(msg)
            cli.add_command(cmd)

    return cli


def main(prog_name: str | None = None) -> None:
    """Main entry point for apcore-cli.

    Args:
        prog_name: Override the program name shown in help/version output.
                   When None, inferred from sys.argv[0] automatically.
    """
    ext_dir = _extract_extensions_dir()
    cmd_dir = _extract_commands_dir()
    bind_path = _extract_binding_path()
    cli = create_cli(
        extensions_dir=ext_dir,
        prog_name=prog_name,
        commands_dir=cmd_dir,
        binding_path=bind_path,
    )
    cli(standalone_mode=True)


if __name__ == "__main__":
    main()
