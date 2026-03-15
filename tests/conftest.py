"""Shared test fixtures for apcore-cli tests."""

import os

import pytest


@pytest.fixture
def tmp_config_dir(tmp_path):
    """Provide a temporary directory for config file tests."""
    return tmp_path


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all APCORE_ env vars to ensure test isolation."""
    for key in list(os.environ.keys()):
        if key.startswith("APCORE_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def _clean_audit_logger():
    """Ensure global _audit_logger is reset after every test (LOW-2 fix)."""
    from apcore_cli.cli import set_audit_logger

    yield
    set_audit_logger(None)
