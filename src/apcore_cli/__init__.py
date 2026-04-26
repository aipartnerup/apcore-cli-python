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
            "help_text_max_length": 1000,
            "approval_timeout": 60,
            "group_depth": 1,
        },
    )
except (ImportError, AttributeError):
    pass  # apcore < 0.15.0 or not installed

# Public API re-exports
from apcore_cli.approval import (
    ApprovalDeniedError,
    ApprovalTimeoutError,
    CliApprovalHandler,
    check_approval,
)
from apcore_cli.builtin_group import (
    RESERVED_GROUP_NAMES,
    ApcliGroup,
    ApcliMode,
)
from apcore_cli.config import ConfigResolver
from apcore_cli.exposure import ExposureFilter
from apcore_cli.factory import create_cli
from apcore_cli.output import format_exec_result
from apcore_cli.ref_resolver import resolve_refs
from apcore_cli.schema_parser import schema_to_click_options
from apcore_cli.security.audit import AuditLogger
from apcore_cli.security.auth import AuthenticationError, AuthProvider
from apcore_cli.security.config_encryptor import ConfigDecryptionError, ConfigEncryptor
from apcore_cli.security.sandbox import (
    CliModuleNotFoundError,
    ModuleExecutionError,
    Sandbox,
    SchemaValidationError,
)

__all__ = [
    "__version__",
    # Factory
    "create_cli",
    # FE-13 builtin-group surface
    "ApcliGroup",
    "ApcliMode",
    "RESERVED_GROUP_NAMES",
    # FE-11 approval
    "CliApprovalHandler",
    "check_approval",
    # FE-12 exposure
    "ExposureFilter",
    # Schema / output / ref resolution
    "resolve_refs",
    "schema_to_click_options",
    "format_exec_result",
    # Config / security
    "ConfigResolver",
    "AuditLogger",
    "AuthProvider",
    "ConfigEncryptor",
    "Sandbox",
    # Error classes
    "ApprovalDeniedError",
    "ApprovalTimeoutError",
    "AuthenticationError",
    "ConfigDecryptionError",
    "ModuleExecutionError",
    "CliModuleNotFoundError",
    "SchemaValidationError",
]
