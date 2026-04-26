"""Preflight validation helpers (FE-11 — D9-005).

Extracted from cli.py during the cross-SDK leanness pass to mirror the
apcore-cli-rust split (apcore-cli-rust/src/validate.rs). The helpers are
pure formatting / exit-code decision functions consumed by:

* the standalone ``apcli validate`` subcommand (cli.py),
* the ``--dry-run`` branch of ``dispatch_module`` (cli.py),
* the ``apcli describe`` command path that emits preflight JSON (discovery.py).

Keeping them in a dedicated module makes the pure logic testable in
isolation and reduces cli.py's surface area. Cli.py and discovery.py
re-import from here; both legacy import paths
(``from apcore_cli.cli import format_preflight_result``) are preserved
via re-export at cli.py for backward compatibility.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import click


def first_failed_exit_code(result: Any) -> int:
    """Return the exit code for the first failed check in a PreflightResult.

    Mirrors ``apcore-cli-rust/src/validate.rs::first_failed_exit_code``. The
    map is the canonical check-name → exit-code mapping documented in
    apcore-cli/docs/features/core-dispatcher.md.
    """
    _check_to_exit = {
        "module_id": 2,
        "module_lookup": 44,
        "call_chain": 1,
        "acl": 77,
        "schema": 45,
        "approval": 46,
        "module_preflight": 1,
    }
    for check in getattr(result, "checks", []):
        if not check.passed:
            return _check_to_exit.get(check.check, 1)
    return 1


def format_preflight_result(result: Any, fmt: str | None = None) -> None:
    """Format and print a PreflightResult to stdout.

    Renders JSON when ``fmt == 'json'`` or stdout is non-TTY (so pipelines
    always get machine-readable output). For interactive TTY callers,
    renders a compact symbol-prefixed table mirroring the format the Rust
    SDK uses.
    """
    from apcore_cli.output import resolve_format

    resolved = resolve_format(fmt)
    if resolved == "json" or not sys.stdout.isatty():
        payload: dict[str, Any] = {
            "valid": result.valid,
            "requires_approval": result.requires_approval,
            "checks": [],
        }
        for c in result.checks:
            entry: dict[str, Any] = {"check": c.check, "passed": c.passed}
            if c.error is not None:
                entry["error"] = c.error
            if c.warnings:
                entry["warnings"] = c.warnings
            payload["checks"].append(entry)
        click.echo(json.dumps(payload, indent=2, default=str))
    else:
        # TTY table format
        for c in result.checks:
            has_warnings = bool(getattr(c, "warnings", []))
            if c.passed and has_warnings:
                sym = "⚠"  # ⚠ passed with warnings
            elif c.passed:
                sym = "✓"  # ✓ passed
            elif c.passed is False:
                sym = "✗"  # ✗ failed
            else:
                sym = "○"  # ○ skipped
            status = f"  {sym} {c.check:<20}"
            if c.error:
                detail = json.dumps(c.error, default=str) if isinstance(c.error, dict) else str(c.error)
                status += f" {detail}"
            elif c.passed and not has_warnings:
                status += " OK"
            elif not c.passed:
                status += " Skipped"
            click.echo(status)
            for w in getattr(c, "warnings", []):
                click.echo(f"    Warning: {w}")
        errors = sum(1 for c in result.checks if not c.passed)
        warnings = sum(len(getattr(c, "warnings", [])) for c in result.checks)
        tag = "PASS" if result.valid else "FAIL"
        click.echo(f"\nResult: {tag} ({errors} error(s), {warnings} warning(s))")
