"""Smoke tests for apcore_cli.strategy module.

TODO (T-001): expand with full FE-11 strategy / describe-pipeline / --strategy
flag coverage. Real behavior verification requires a live apcore Executor with
strategy support — see code-forge:build for the dedicated test-writing pass.
"""

from __future__ import annotations


def test_strategy_module_importable():
    from apcore_cli import strategy

    assert strategy is not None


def test_strategy_has_register_pipeline_command():
    from apcore_cli.strategy import register_pipeline_command

    assert callable(register_pipeline_command)
