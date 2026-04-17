"""Smoke tests for apcore_cli.system_cmd module.

TODO (T-001): expand with full FE-11 system management coverage —
health, usage, enable, disable, reload, config get/set. Real verification
requires a live apcore Executor with system modules registered.
"""

from __future__ import annotations


def test_system_cmd_module_importable():
    from apcore_cli import system_cmd

    assert system_cmd is not None


def test_system_cmd_has_register_system_commands():
    from apcore_cli.system_cmd import register_system_commands

    assert callable(register_system_commands)
