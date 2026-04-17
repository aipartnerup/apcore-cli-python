<<<<<<< ours
"""Module exposure filtering (FE-12).

Controls which discovered modules are exposed as CLI commands.
Filtering is applied at command-registration time, after discovery but before
Click Command building. The Registry retains all modules — exposure is a UX
filter, not a security boundary.
=======
"""Module Exposure Filtering (FE-12).

Provides declarative control over which discovered modules are exposed
as CLI commands. Supports three modes: all, include (whitelist), and
exclude (blacklist) with glob-pattern matching on module IDs.
>>>>>>> theirs
"""

from __future__ import annotations

import logging
import re

<<<<<<< ours
logger = logging.getLogger("apcore_cli.exposure")


def _compile_pattern(pattern: str) -> re.Pattern[str] | None:
    """Compile a glob pattern to a regex. Returns None if pattern is invalid."""
    try:
        # Replace ** before * so the sentinel replacement is unambiguous.
        sentinel = "\x00GLOBSTAR\x00"
        p = pattern.replace("**", sentinel)
        # * matches within a single dotted segment (no dots)
        p = p.replace("*", "[^.]*")
        # ** (sentinel) matches across segment boundaries
        p = p.replace(sentinel, ".*")
        # Escape all regex metacharacters except the ones we substituted above.
        # We already replaced the globs, so escape the literal parts.
        # Re-build by escaping non-substituted chars via re.escape on the literal pieces.
        return re.compile(f"^{p}$")
    except re.error:
        return None
=======
import click

logger = logging.getLogger("apcore_cli.exposure")


def _compile_pattern(pattern: str) -> re.Pattern[str]:
    """Compile a glob pattern to a regex.

    - ``*`` matches a single dotted segment (no dots).
    - ``**`` matches across segments (any characters including dots).
    - Literal text is matched exactly.
    """
    # Replace ** first with a sentinel to avoid confusion with single *
    sentinel = "\x00GLOB\x00"
    escaped = pattern.replace("**", sentinel)
    # Escape regex-special chars except our sentinel and remaining *
    parts = escaped.split("*")
    parts = [p.replace(sentinel, "**") for p in parts]
    # Now rebuild: join single-star positions with [^.]* and handle **
    regex = "[^.]*".join(re.escape(p) for p in parts)
    # Restore ** → .+ (must match at least one char across segments)
    regex = regex.replace(re.escape("**"), ".+")
    return re.compile(f"^{regex}$")


def _glob_match(module_id: str, pattern: str) -> bool:
    """Test whether a module_id matches a glob pattern."""
    compiled = _compile_pattern(pattern)
    return compiled.match(module_id) is not None
>>>>>>> theirs


class ExposureFilter:
    """Determines which modules are exposed as CLI commands.

    Filtering modes:
<<<<<<< ours
    - all: every discovered module becomes a CLI command (default)
    - include: only modules matching at least one include pattern are exposed
    - exclude: all modules are exposed except those matching any exclude pattern
=======
    - ``all``: every discovered module becomes a CLI command (default).
    - ``include``: only modules matching at least one include pattern are exposed.
    - ``exclude``: all modules are exposed except those matching any exclude pattern.
>>>>>>> theirs
    """

    def __init__(
        self,
        mode: str = "all",
        include: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> None:
<<<<<<< ours
        if mode not in ("all", "include", "exclude"):
            raise ValueError(f"Invalid expose mode: '{mode}'. Must be one of: all, include, exclude.")
        self._mode = mode
        self._include_patterns: list[re.Pattern[str]] = []
        self._exclude_patterns: list[re.Pattern[str]] = []

        for pat in set(include or []):
            if not pat:
                logger.warning("Empty pattern in expose.include, skipping.")
                continue
            compiled = _compile_pattern(pat)
            if compiled is None:
                logger.warning("Invalid pattern '%s' in expose.include, skipping.", pat)
            else:
                self._include_patterns.append(compiled)

        for pat in set(exclude or []):
            if not pat:
                logger.warning("Empty pattern in expose.exclude, skipping.")
                continue
            compiled = _compile_pattern(pat)
            if compiled is None:
                logger.warning("Invalid pattern '%s' in expose.exclude, skipping.", pat)
            else:
                self._exclude_patterns.append(compiled)

    @classmethod
    def from_config(cls, config: dict) -> ExposureFilter:
        """Create from a parsed apcore.yaml config dict.

        Reads the ``expose`` section. Returns mode=all if the section is absent
        or malformed.
=======
        self._mode = mode
        self._include_patterns = list(dict.fromkeys(include or []))
        self._exclude_patterns = list(dict.fromkeys(exclude or []))
        # Pre-compile regexes
        self._compiled_include = [_compile_pattern(p) for p in self._include_patterns]
        self._compiled_exclude = [_compile_pattern(p) for p in self._exclude_patterns]

    def is_exposed(self, module_id: str) -> bool:
        """Return True if the module should be exposed as a CLI command."""
        if self._mode == "all":
            return True
        if self._mode == "include":
            return any(rx.match(module_id) for rx in self._compiled_include)
        if self._mode == "exclude":
            return not any(rx.match(module_id) for rx in self._compiled_exclude)
        return True

    def filter_modules(self, module_ids: list[str]) -> tuple[list[str], list[str]]:
        """Partition module_ids into (exposed, hidden) lists."""
        exposed: list[str] = []
        hidden: list[str] = []
        for mid in module_ids:
            if self.is_exposed(mid):
                exposed.append(mid)
            else:
                hidden.append(mid)
        return exposed, hidden

    @classmethod
    def from_config(cls, config: dict) -> ExposureFilter:
        """Create an ExposureFilter from a parsed config dict.

        Expected structure::

            {"expose": {"mode": "include", "include": ["admin.*"]}}
>>>>>>> theirs
        """
        expose = config.get("expose", {})
        if not isinstance(expose, dict):
            logger.warning("Invalid 'expose' config (expected dict), using mode: all.")
            return cls()

        mode = expose.get("mode", "all")
        if mode not in ("all", "include", "exclude"):
<<<<<<< ours
            import click

            raise click.BadParameter(f"Invalid expose mode: '{mode}'. Must be one of: all, include, exclude.")

        include_raw = expose.get("include", [])
        if not isinstance(include_raw, list):
            logger.warning("Invalid 'expose.include' (expected list), ignoring.")
            include_raw = []

        exclude_raw = expose.get("exclude", [])
        if not isinstance(exclude_raw, list):
            logger.warning("Invalid 'expose.exclude' (expected list), ignoring.")
            exclude_raw = []

        # Filter empty strings with a warning (handled inside __init__)
        return cls(mode=mode, include=list(include_raw), exclude=list(exclude_raw))

    def is_exposed(self, module_id: str) -> bool:
        """Return True if the module should be exposed as a CLI command."""
        if self._mode == "all":
            return True
        if self._mode == "include":
            return any(p.match(module_id) for p in self._include_patterns)
        # mode == "exclude"
        return not any(p.match(module_id) for p in self._exclude_patterns)

    def filter_modules(self, module_ids: list[str]) -> tuple[list[str], list[str]]:
        """Partition module_ids into (exposed, hidden) lists."""
        exposed: list[str] = []
        hidden: list[str] = []
        for mid in module_ids:
            if self.is_exposed(mid):
                exposed.append(mid)
            else:
                hidden.append(mid)
        return exposed, hidden
=======
            msg = f"Invalid expose mode: '{mode}'. Must be one of: all, include, exclude."
            raise click.BadParameter(msg)

        include = expose.get("include", [])
        if not isinstance(include, list):
            logger.warning("Invalid 'expose.include' (expected list), ignoring.")
            include = []

        exclude = expose.get("exclude", [])
        if not isinstance(exclude, list):
            logger.warning("Invalid 'expose.exclude' (expected list), ignoring.")
            exclude = []

        # Filter empty strings
        filtered_include: list[str] = []
        for p in include:
            if not p:
                logger.warning("Empty pattern in expose.include, skipping.")
            else:
                filtered_include.append(str(p))

        filtered_exclude: list[str] = []
        for p in exclude:
            if not p:
                logger.warning("Empty pattern in expose.exclude, skipping.")
            else:
                filtered_exclude.append(str(p))

        return cls(mode=mode, include=filtered_include, exclude=filtered_exclude)
>>>>>>> theirs
