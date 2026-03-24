"""Display overlay helpers — shared resolution logic for CLI surfaces."""

from __future__ import annotations

from typing import Any


def get_display(descriptor: Any) -> dict[str, Any]:
    """Extract resolved display overlay from a ModuleDescriptor's metadata."""
    metadata = getattr(descriptor, "metadata", None) or {}
    if isinstance(metadata, dict):
        return metadata.get("display") or {}
    return {}


def get_cli_display_fields(descriptor: Any) -> tuple[str, str, list[str]]:
    """Return (display_name, description, tags) resolved from the display overlay.

    Falls back to scanner-provided values when no overlay is present.
    """
    display = get_display(descriptor)
    cli = display.get("cli") or {}
    name = (
        cli.get("alias")
        or display.get("alias")
        or (descriptor.canonical_id if hasattr(descriptor, "canonical_id") else descriptor.module_id)
    )
    desc = cli.get("description") or descriptor.description
    tags = display.get("tags") or (descriptor.tags if hasattr(descriptor, "tags") else [])
    return name, desc, tags
