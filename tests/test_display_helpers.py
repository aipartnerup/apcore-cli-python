"""Smoke tests for apcore_cli.display_helpers module (FE-09).

TODO (T-001): expand with full display overlay / get_display / get_cli_display_fields
coverage including binding metadata edge cases.
"""

from __future__ import annotations


def test_display_helpers_module_importable():
    from apcore_cli import display_helpers

    assert display_helpers is not None


def test_get_display_returns_dict_for_empty_descriptor():
    from apcore_cli.display_helpers import get_display

    descriptor = {"module_id": "test.empty"}
    result = get_display(descriptor)
    assert isinstance(result, dict)
