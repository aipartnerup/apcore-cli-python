"""Output Formatter — TTY-adaptive output rendering (FE-08)."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from apcore_cli.display_helpers import get_cli_display_fields as _get_cli_fields

if TYPE_CHECKING:
    from apcore.registry.types import ModuleDescriptor


def resolve_format(explicit_format: str | None) -> str:
    """Resolve output format with TTY-adaptive default."""
    if explicit_format is not None:
        return explicit_format
    if sys.stdout.isatty():
        return "table"
    return "json"


def _truncate(text: str, max_length: int = 80) -> str:
    """Truncate text to max_length, appending '...' if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def format_module_list(
    modules: list[ModuleDescriptor],
    format: str,
    filter_tags: tuple[str, ...] = (),
) -> None:
    """Format and print a list of modules."""
    if format == "table":
        if not modules and filter_tags:
            click.echo(f"No modules found matching tags: {', '.join(filter_tags)}.")
            return
        if not modules:
            click.echo("No modules found.")
            return

        table = Table(title="Modules")
        table.add_column("ID")
        table.add_column("Description")
        table.add_column("Tags")

        for m in modules:
            display_name, desc, tags_val = _get_cli_fields(m)
            tags = ", ".join(tags_val) if tags_val else ""
            table.add_row(display_name, _truncate(desc, 80), tags)

        Console().print(table)
    elif format == "json":
        result = []
        for m in modules:
            mid, desc, tags_val = _get_cli_fields(m)
            result.append(
                {
                    "id": mid,
                    "description": desc,
                    "tags": tags_val,
                }
            )
        click.echo(json.dumps(result, indent=2))


def _annotations_to_dict(annotations: Any) -> dict | None:
    """Convert annotations (dict or dataclass) to a plain dict, or None."""
    if annotations is None:
        return None
    if isinstance(annotations, dict):
        return annotations if annotations else None
    # Dataclass-like object (e.g. ModuleAnnotations) — convert non-default fields
    try:
        import dataclasses

        if dataclasses.is_dataclass(annotations):
            return {
                k: v
                for k, v in dataclasses.asdict(annotations).items()
                if v is not None and v is not False and v != 0 and v != []
            }
    except Exception:
        pass
    # Fallback: try vars()
    try:
        d = {
            k: v
            for k, v in vars(annotations).items()
            if not k.startswith("_") and v is not None and v is not False and v != 0
        }
        return d if d else None
    except Exception:
        return None


def format_module_detail(module_def: ModuleDescriptor, format: str) -> None:
    """Format and print full module metadata."""
    from apcore_cli.display_helpers import get_display

    mid = module_def.canonical_id if hasattr(module_def, "canonical_id") else module_def.module_id

    # Resolve display overlay fields (§5.13)
    display = get_display(module_def)
    cli_display = display.get("cli") or {}
    display_description: str = cli_display.get("description") or module_def.description
    display_guidance: str | None = cli_display.get("guidance") or display.get("guidance")

    if format == "table":
        console = Console()
        console.print(Panel(f"Module: {mid}"))
        click.echo(f"\nDescription:\n  {display_description}\n")
        if display_guidance:
            click.echo(f"Guidance:\n{display_guidance}\n")

        if hasattr(module_def, "input_schema") and module_def.input_schema:
            click.echo("\nInput Schema:")
            console.print(Syntax(json.dumps(module_def.input_schema, indent=2), "json", theme="monokai"))

        if hasattr(module_def, "output_schema") and module_def.output_schema:
            click.echo("\nOutput Schema:")
            console.print(Syntax(json.dumps(module_def.output_schema, indent=2), "json", theme="monokai"))

        ann_dict = _annotations_to_dict(getattr(module_def, "annotations", None))
        if ann_dict:
            click.echo("\nAnnotations:")
            for k, v in ann_dict.items():
                click.echo(f"  {k}: {v}")

        # Extension metadata (x- prefixed)
        x_fields = {}
        if hasattr(module_def, "metadata") and isinstance(module_def.metadata, dict):
            x_fields = {k: v for k, v in module_def.metadata.items() if k.startswith("x-") or k.startswith("x_")}
        # Also check vars() for x_ prefixed attributes
        try:
            for k, v in vars(module_def).items():
                if (k.startswith("x_") or k.startswith("x-")) and k not in x_fields:
                    x_fields[k] = v
        except TypeError:
            pass
        if x_fields:
            click.echo("\nExtension Metadata:")
            for k, v in x_fields.items():
                click.echo(f"  {k}: {v}")

        tags = getattr(module_def, "tags", [])
        if tags:
            click.echo(f"\nTags: {', '.join(tags)}")

    elif format == "json":
        result: dict[str, Any] = {
            "id": mid,
            "description": display_description,
        }
        if display_guidance:
            result["guidance"] = display_guidance
        if hasattr(module_def, "input_schema") and module_def.input_schema:
            result["input_schema"] = module_def.input_schema
        if hasattr(module_def, "output_schema") and module_def.output_schema:
            result["output_schema"] = module_def.output_schema

        ann_dict = _annotations_to_dict(getattr(module_def, "annotations", None))
        if ann_dict:
            result["annotations"] = ann_dict

        tags = getattr(module_def, "tags", [])
        if tags:
            result["tags"] = tags

        # Extension metadata
        if hasattr(module_def, "metadata") and isinstance(module_def.metadata, dict):
            for k, v in module_def.metadata.items():
                if k.startswith("x-") or k.startswith("x_"):
                    result[k] = v
        try:
            for k, v in vars(module_def).items():
                if (k.startswith("x_") or k.startswith("x-")) and k not in result:
                    result[k] = v
        except TypeError:
            pass

        click.echo(json.dumps(result, indent=2))


def format_grouped_module_list(
    grouped: dict[str | None, list[tuple[str, str, list[str]]]],
    filter_tags: tuple[str, ...] = (),
) -> None:
    """Format and print modules grouped by namespace.

    Parameters
    ----------
    grouped:
        Mapping of group name (or ``None`` for ungrouped) to a list of
        ``(command_name, description, tags)`` tuples.
    filter_tags:
        Tags used for filtering (shown in the empty-state message).
    """
    console = Console()

    # Separate top-level (ungrouped) modules
    top = grouped.pop(None, [])

    all_empty = not top and not grouped
    if all_empty and filter_tags:
        click.echo(f"No modules found matching tags: {', '.join(filter_tags)}.")
        return
    if all_empty:
        click.echo("No modules found.")
        return

    # Named groups
    for group_name in sorted(grouped.keys()):
        members = grouped[group_name]
        table = Table(title=f"{group_name}")
        table.add_column("Command")
        table.add_column("Description")
        table.add_column("Tags")
        for cmd, desc, tags in sorted(members, key=lambda x: x[0]):
            table.add_row(cmd, _truncate(desc, 80), ", ".join(tags) if tags else "")
        console.print(table)

    # Top-level / ungrouped
    if top:
        table = Table(title="Other")
        table.add_column("Command")
        table.add_column("Description")
        table.add_column("Tags")
        for cmd, desc, tags in sorted(top, key=lambda x: x[0]):
            table.add_row(cmd, _truncate(desc, 80), ", ".join(tags) if tags else "")
        console.print(table)


def format_exec_result(result: Any, format: str | None = None) -> None:
    """Format and print module execution result.

    Uses ``resolve_format(format)`` for TTY-adaptive defaulting:
    - json (or non-TTY default): JSON-pretty-printed output.
    - table: Rich table for dict results; falls back to JSON for lists,
      plain string for scalars.
    """
    if result is None:
        return
    effective = resolve_format(format)
    if effective == "table" and isinstance(result, dict):
        table = Table()
        table.add_column("Key")
        table.add_column("Value")
        for k, v in result.items():
            table.add_row(str(k), str(v))
        Console().print(table)
    elif isinstance(result, dict | list):
        click.echo(json.dumps(result, indent=2, default=str))
    elif isinstance(result, str):
        click.echo(result)
    else:
        click.echo(str(result))
