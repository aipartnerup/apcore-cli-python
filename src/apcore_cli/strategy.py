"""Pipeline strategy commands — describe-pipeline (FE-11)."""

from __future__ import annotations

import contextlib
import json
import sys
from typing import Any

import click

from apcore_cli.output import resolve_format

_PRESET_STEPS = {
    "standard": [
        "context_creation",
        "call_chain_guard",
        "module_lookup",
        "acl_check",
        "approval_gate",
        "middleware_before",
        "input_validation",
        "execute",
        "output_validation",
        "middleware_after",
        "return_result",
    ],
    "internal": [
        "context_creation",
        "call_chain_guard",
        "module_lookup",
        "middleware_before",
        "input_validation",
        "execute",
        "output_validation",
        "middleware_after",
        "return_result",
    ],
    "testing": [
        "context_creation",
        "module_lookup",
        "middleware_before",
        "input_validation",
        "execute",
        "output_validation",
        "middleware_after",
        "return_result",
    ],
    "performance": [
        "context_creation",
        "call_chain_guard",
        "module_lookup",
        "acl_check",
        "approval_gate",
        "input_validation",
        "execute",
        "output_validation",
        "return_result",
    ],
    "minimal": [
        "context_creation",
        "module_lookup",
        "execute",
        "return_result",
    ],
}


def register_pipeline_command(cli: click.Group, executor: Any) -> None:
    """Register the describe-pipeline command."""

    @cli.command("describe-pipeline")
    @click.option(
        "--strategy",
        type=click.Choice(["standard", "internal", "testing", "performance", "minimal"]),
        default="standard",
        help="Strategy to describe (default: standard).",
    )
    @click.option("--format", "output_format", type=click.Choice(["table", "json"]), default=None)
    def describe_pipeline_cmd(strategy: str, output_format: str | None) -> None:
        """Show the execution pipeline steps for a strategy."""
        fmt = resolve_format(output_format)

        # Try to get strategy info from executor
        strategy_obj = None
        if hasattr(executor, "_resolve_strategy_name"):
            with contextlib.suppress(Exception):
                strategy_obj = executor._resolve_strategy_name(strategy)

        if strategy_obj is None:
            # Provide static info for known strategies
            steps = _PRESET_STEPS.get(strategy, [])

            if fmt == "json" or not sys.stdout.isatty():
                payload = {
                    "strategy": strategy,
                    "step_count": len(steps),
                    "steps": [{"index": i + 1, "name": s} for i, s in enumerate(steps)],
                }
                click.echo(json.dumps(payload, indent=2))
            else:
                click.echo(f"Pipeline: {strategy} ({len(steps)} steps)\n")
                click.echo(f"  {'#':<4} {'Step':<28}")
                click.echo(f"  {'-' * 4} {'-' * 28}")
                for i, s in enumerate(steps, 1):
                    click.echo(f"  {i:<4} {s:<28}")
            return

        # Use actual strategy object for detailed info
        steps_info = []
        for step in strategy_obj.steps:
            info: dict[str, Any] = {
                "name": step.name,
                "pure": getattr(step, "pure", False),
                "removable": getattr(step, "removable", True),
                "timeout_ms": getattr(step, "timeout_ms", None),
            }
            steps_info.append(info)

        if fmt == "json" or not sys.stdout.isatty():
            payload = {
                "strategy": strategy,
                "step_count": len(steps_info),
                "steps": [{"index": i + 1, **s} for i, s in enumerate(steps_info)],
            }
            click.echo(json.dumps(payload, indent=2))
        else:
            click.echo(f"Pipeline: {strategy} ({len(steps_info)} steps)\n")
            click.echo(f"  {'#':<4} {'Step':<28} {'Pure':<6} {'Removable':<11} Timeout")
            click.echo(f"  {'-' * 4} {'-' * 28} {'-' * 6} {'-' * 11} {'-' * 8}")
            for i, s in enumerate(steps_info, 1):
                pure = "yes" if s["pure"] else "no"
                removable = "yes" if s["removable"] else "no"
                timeout = f"{s['timeout_ms']}ms" if s["timeout_ms"] else "\u2014"
                click.echo(f"  {i:<4} {s['name']:<28} {pure:<6} {removable:<11} {timeout}")
