"""Discovery commands — list, describe, validate (FE-04, FE-11)."""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import click

from apcore_cli.cli import format_preflight_result, validate_module_id
from apcore_cli.display_helpers import get_cli_display_fields
from apcore_cli.output import (
    format_grouped_module_list,
    format_module_detail,
    format_module_list,
    resolve_format,
)

logger = logging.getLogger("apcore_cli.discovery")

_TAG_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


def _validate_tag(tag: str) -> None:
    """Validate tag format."""
    if not _TAG_PATTERN.match(tag):
        click.echo(
            f"Error: Invalid tag format: '{tag}'. Tags must match [a-z][a-z0-9_-]*.",
            err=True,
        )
        sys.exit(2)


def _resolve_group_for_display(descriptor: Any) -> tuple[str | None, str]:
    """Resolve group name and command name for display — delegates to GroupedModuleGroup."""
    from apcore_cli.cli import GroupedModuleGroup

    module_id = getattr(descriptor, "module_id", "") or ""
    return GroupedModuleGroup._resolve_group(module_id, descriptor)


def register_discovery_commands(cli: click.Group, registry: Any, exposure_filter: Any | None = None) -> None:
    """Register list and describe commands on the CLI group."""
    # Import here to avoid circular imports at module level.
    from apcore_cli.exposure import ExposureFilter

    if exposure_filter is None:
        exposure_filter = ExposureFilter()

    @cli.command("list")
    @click.option("--tag", multiple=True, help="Filter modules by tag (AND logic). Repeatable.")
    @click.option("--flat", is_flag=True, default=False, help="Show flat list (no grouping).")
    @click.option(
        "--format",
        "output_format",
        type=click.Choice(["table", "json", "csv", "yaml", "jsonl"]),
        default=None,
        help="Output format. Default: table (TTY) or json (non-TTY).",
    )
    @click.option("--search", "-s", default=None, help="Filter by substring match on ID and description.")
    @click.option(
        "--status",
        type=click.Choice(["enabled", "disabled", "all"]),
        default="enabled",
        help="Filter by module status. Default: enabled.",
    )
    @click.option(
        "--annotation",
        "-a",
        multiple=True,
        type=click.Choice(
            [
                "destructive",
                "requires-approval",
                "readonly",
                "streaming",
                "cacheable",
                "idempotent",
            ]
        ),
        help="Filter by annotation flag (AND logic). Repeatable.",
    )
    @click.option(
        "--sort",
        type=click.Choice(["id", "calls", "errors", "latency"]),
        default="id",
        help="Sort order. Default: id.",
    )
    @click.option("--reverse", is_flag=True, default=False, help="Reverse sort order.")
    @click.option("--deprecated", is_flag=True, default=False, help="Include deprecated modules.")
    @click.option("--deps", is_flag=True, default=False, help="Show dependency count column.")
    @click.option(
        "--exposure",
        type=click.Choice(["exposed", "hidden", "all"]),
        default="exposed",
        help="Filter by exposure status. Default: exposed.",
    )
    def list_cmd(  # pyright: ignore[reportUnusedVariable]
        tag: tuple[str, ...],
        flat: bool,
        output_format: str | None,
        search: str | None,
        status: str,
        annotation: tuple[str, ...],
        sort: str,
        reverse: bool,
        deprecated: bool,
        deps: bool,
        exposure: str,
    ) -> None:
        """List available modules in the registry."""
        # Validate tag format
        for t in tag:
            _validate_tag(t)

        modules = []
        for mid in registry.list():
            mdef = registry.get_definition(mid)
            if mdef is not None:
                modules.append(mdef)

        # Tag filter
        if tag:
            filter_tags = set(tag)
            modules = [m for m in modules if filter_tags.issubset(set(getattr(m, "tags", [])))]

        # Search filter (case-insensitive substring on id + description)
        if search:
            query = search.lower()
            modules = [
                m
                for m in modules
                if query in (getattr(m, "module_id", "") or "").lower()
                or query in (getattr(m, "description", "") or "").lower()
            ]

        # Status filter
        if status == "enabled":
            modules = [m for m in modules if getattr(m, "enabled", None) is not False]
        elif status == "disabled":
            modules = [m for m in modules if getattr(m, "enabled", None) is False]
        # "all": no filter

        # Deprecated filter (excluded by default)
        if not deprecated:
            modules = [m for m in modules if getattr(m, "deprecated", False) is not True]

        # Annotation filter (AND logic)
        if annotation:
            _ann_map = {
                "destructive": "destructive",
                "requires-approval": "requires_approval",
                "readonly": "readonly",
                "streaming": "streaming",
                "cacheable": "cacheable",
                "idempotent": "idempotent",
            }
            for ann_flag in annotation:
                attr = _ann_map.get(ann_flag, ann_flag)
                modules = [m for m in modules if getattr(getattr(m, "annotations", None), attr, False) is True]

        # Exposure filter (FE-12)
        if exposure == "exposed":
            modules = [m for m in modules if exposure_filter.is_exposed(getattr(m, "module_id", ""))]
        elif exposure == "hidden":
            modules = [m for m in modules if not exposure_filter.is_exposed(getattr(m, "module_id", ""))]
        # "all": no filter — show all regardless of exposure status

        # Sort
        if sort in ("calls", "errors", "latency"):
            logger.warning(
                "Usage data not available; sorting by id. Sort by %s requires system.usage modules.",
                sort,
            )
        modules.sort(key=lambda m: getattr(m, "module_id", ""), reverse=reverse)

        fmt = resolve_format(output_format)

        show_exposure_col = exposure == "all"  # pyright: ignore[reportUnusedVariable]

        if flat or fmt in ("json", "csv", "yaml", "jsonl"):
            format_module_list(
                modules,
                fmt,
                filter_tags=tag,
                show_deps=deps,
                exposure_filter=exposure_filter if show_exposure_col else None,
            )
        else:
            # Build grouped dict for table display
            grouped: dict[str | None, list[tuple[str, str, list[str]]]] = {}
            for m in modules:
                group_name, cmd_name = _resolve_group_for_display(m)
                _, desc, tags_val = get_cli_display_fields(m)
                grouped.setdefault(group_name, []).append((cmd_name, desc, tags_val))
            format_grouped_module_list(grouped, filter_tags=tag)

    @cli.command("describe")
    @click.argument("module_id")
    @click.option(
        "--format",
        "output_format",
        type=click.Choice(["table", "json"]),
        default=None,
        help="Output format. Default: table (TTY) or json (non-TTY).",
    )
    def describe_cmd(module_id: str, output_format: str | None) -> None:  # pyright: ignore[reportUnusedVariable]
        """Show metadata, schema, and annotations for a module."""
        validate_module_id(module_id)

        module_def = registry.get_definition(module_id)
        if module_def is None:
            click.echo(f"Error: Module '{module_id}' not found.", err=True)
            sys.exit(44)

        fmt = resolve_format(output_format)
        format_module_detail(module_def, fmt)


def register_validate_command(cli: click.Group, registry: Any, executor: Any) -> None:
    """Register the standalone validate command."""
    from apcore_cli.cli import _first_failed_exit_code, collect_input

    @cli.command("validate")
    @click.argument("module_id")
    @click.option("--input", "stdin_input", default=None, help="JSON input file or '-' for stdin.")
    @click.option(
        "--format",
        "output_format",
        type=click.Choice(["table", "json"]),
        default=None,
        help="Output format.",
    )
    def validate_cmd(module_id: str, stdin_input: str | None, output_format: str | None) -> None:  # pyright: ignore[reportUnusedVariable]
        """Run preflight checks without executing a module."""
        validate_module_id(module_id)

        module_def = registry.get_definition(module_id)
        if module_def is None:
            click.echo(f"Error: Module '{module_id}' not found.", err=True)
            sys.exit(44)

        merged = collect_input(stdin_input, {}, False) if stdin_input else {}
        preflight = executor.validate(module_id, merged)
        format_preflight_result(preflight, output_format)
        sys.exit(0 if preflight.valid else _first_failed_exit_code(preflight))
