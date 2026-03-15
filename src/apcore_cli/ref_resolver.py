"""$ref resolution and schema composition (FE-02)."""

from __future__ import annotations

import copy
import sys
from typing import Any

import click


def resolve_refs(schema: dict, max_depth: int = 32, module_id: str = "") -> dict:
    """Resolve all $ref references in a JSON Schema.

    Returns a fully inlined schema with $defs/definitions removed.
    """
    schema = copy.deepcopy(schema)
    defs = schema.get("$defs", schema.get("definitions", {}))
    result = _resolve_node(schema, defs, visited=set(), depth=0, max_depth=max_depth, module_id=module_id)

    # Remove definition keys
    result.pop("$defs", None)
    result.pop("definitions", None)
    return result


def _resolve_node(
    node: Any,
    defs: dict,
    visited: set,
    depth: int,
    max_depth: int,
    module_id: str = "",
) -> Any:
    """Recursively resolve $ref, allOf, anyOf, oneOf in a schema node."""
    if not isinstance(node, dict):
        return node

    # Handle $ref
    if "$ref" in node:
        ref_path = node["$ref"]

        if depth >= max_depth:
            click.echo(
                f"Error: $ref resolution depth exceeded maximum of {max_depth} for module '{module_id}'.",
                err=True,
            )
            sys.exit(48)

        if ref_path in visited:
            click.echo(
                f"Error: Circular $ref detected in schema for module '{module_id}' at path '{ref_path}'.",
                err=True,
            )
            sys.exit(48)

        # Parse ref target: extract key from "#/$defs/Address" → "Address"
        parts = ref_path.split("/")
        key = parts[-1]

        if key not in defs:
            click.echo(
                f"Error: Unresolvable $ref '{ref_path}' in schema for module '{module_id}'.",
                err=True,
            )
            sys.exit(45)

        visited = visited | {ref_path}
        return _resolve_node(defs[key], defs, visited, depth + 1, max_depth, module_id)

    # Handle allOf
    if "allOf" in node:
        merged: dict[str, Any] = {"properties": {}, "required": []}
        for sub_schema in node["allOf"]:
            resolved = _resolve_node(sub_schema, defs, visited, depth + 1, max_depth, module_id)
            if "properties" in resolved:
                merged["properties"].update(resolved["properties"])
            if "required" in resolved:
                merged["required"].extend(resolved["required"])
        # Copy non-composition keys
        for k, v in node.items():
            if k != "allOf" and k not in merged:
                merged[k] = v
        return merged

    # Handle anyOf / oneOf
    for keyword in ("anyOf", "oneOf"):
        if keyword in node:
            merged = {"properties": {}, "required": []}
            all_required_sets: list[set[str]] = []
            for sub_schema in node[keyword]:
                resolved = _resolve_node(sub_schema, defs, visited, depth + 1, max_depth, module_id)
                if "properties" in resolved:
                    merged["properties"].update(resolved["properties"])
                if "required" in resolved:
                    all_required_sets.append(set(resolved["required"]))
            # Required = intersection of all branches
            if all_required_sets:
                merged["required"] = list(set.intersection(*all_required_sets))
            else:
                merged["required"] = []
            # Copy non-composition keys
            for k, v in node.items():
                if k != keyword and k not in merged:
                    merged[k] = v
            return merged

    # Recursively process nested properties
    if "properties" in node:
        for prop_name, prop_schema in node["properties"].items():
            node["properties"][prop_name] = _resolve_node(prop_schema, defs, visited, depth + 1, max_depth, module_id)

    return node
