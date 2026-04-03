"""apcore-cli: CLI adapter for the apcore module ecosystem."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _get_version

try:
    __version__ = _get_version("apcore-cli")
except PackageNotFoundError:
    __version__ = "unknown"

# Config Bus namespace registration (apcore >= 0.15.0)
try:
    from apcore import Config

    Config.register_namespace(
        name="apcore-cli",
        schema=None,
        env_prefix="APCORE_CLI",
        defaults={
            "stdin_buffer_limit": 10_485_760,
            "auto_approve": False,
            "help_text_max_length": 1000,
            "logging_level": "WARNING",
        },
    )
except (ImportError, AttributeError):
    pass  # apcore < 0.15.0 or not installed

# Public API re-exports
from apcore_cli.__main__ import create_cli

__all__ = ["__version__", "create_cli"]
