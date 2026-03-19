"""Tests for ConfigResolver (FE-07)."""

import logging

from apcore_cli.config import ConfigResolver


class TestConfigResolverSkeleton:
    """Task 1: Instantiation and DEFAULTS."""

    def test_config_resolver_instantiation(self):
        resolver = ConfigResolver()
        assert resolver is not None
        assert hasattr(resolver, "DEFAULTS")
        assert isinstance(resolver.DEFAULTS, dict)

    def test_config_resolver_with_cli_flags(self):
        flags = {"--extensions-dir": "/cli"}
        resolver = ConfigResolver(cli_flags=flags)
        assert resolver._cli_flags == flags

    def test_defaults_contains_expected_keys(self):
        resolver = ConfigResolver()
        expected_keys = [
            "extensions.root",
            "logging.level",
            "sandbox.enabled",
            "cli.stdin_buffer_limit",
            "cli.help_text_max_length",
        ]
        for key in expected_keys:
            assert key in resolver.DEFAULTS, f"Missing default key: {key}"


class TestConfigResolverResolve:
    """Task 2: 4-tier precedence."""

    def test_resolve_tier1_cli_flag_wins(self, monkeypatch, tmp_path):
        config_file = tmp_path / "apcore.yaml"
        config_file.write_text("extensions:\n  root: /config-path\n")
        monkeypatch.setenv("APCORE_EXTENSIONS_ROOT", "/env-path")
        resolver = ConfigResolver(
            cli_flags={"--extensions-dir": "/cli-path"},
            config_path=str(config_file),
        )
        result = resolver.resolve(
            "extensions.root",
            cli_flag="--extensions-dir",
            env_var="APCORE_EXTENSIONS_ROOT",
        )
        assert result == "/cli-path"

    def test_resolve_tier2_env_var_wins(self, monkeypatch, tmp_path):
        config_file = tmp_path / "apcore.yaml"
        config_file.write_text("extensions:\n  root: /config-path\n")
        monkeypatch.setenv("APCORE_EXTENSIONS_ROOT", "/env-path")
        resolver = ConfigResolver(config_path=str(config_file))
        result = resolver.resolve(
            "extensions.root",
            env_var="APCORE_EXTENSIONS_ROOT",
        )
        assert result == "/env-path"

    def test_resolve_tier3_config_file_wins(self, tmp_path, clean_env):
        config_file = tmp_path / "apcore.yaml"
        config_file.write_text("extensions:\n  root: /config-path\n")
        resolver = ConfigResolver(config_path=str(config_file))
        result = resolver.resolve("extensions.root")
        assert result == "/config-path"

    def test_resolve_tier4_default_wins(self, clean_env):
        resolver = ConfigResolver(config_path="/nonexistent/apcore.yaml")
        result = resolver.resolve("extensions.root")
        assert result == "./extensions"

    def test_resolve_cli_flag_none_skips(self, monkeypatch):
        monkeypatch.setenv("APCORE_EXTENSIONS_ROOT", "/env-path")
        resolver = ConfigResolver(cli_flags={"--extensions-dir": None})
        result = resolver.resolve(
            "extensions.root",
            cli_flag="--extensions-dir",
            env_var="APCORE_EXTENSIONS_ROOT",
        )
        assert result == "/env-path"

    def test_resolve_env_var_empty_string_skips(self, monkeypatch, tmp_path):
        config_file = tmp_path / "apcore.yaml"
        config_file.write_text("extensions:\n  root: /config-path\n")
        monkeypatch.setenv("APCORE_EXTENSIONS_ROOT", "")
        resolver = ConfigResolver(config_path=str(config_file))
        result = resolver.resolve(
            "extensions.root",
            env_var="APCORE_EXTENSIONS_ROOT",
        )
        assert result == "/config-path"

    def test_resolve_unknown_key_returns_none(self, clean_env):
        resolver = ConfigResolver(config_path="/nonexistent/apcore.yaml")
        result = resolver.resolve("nonexistent.key")
        assert result is None


class TestConfigFileLoading:
    """Task 3: Config file loading and flattening."""

    def test_load_config_file_valid_yaml(self, tmp_path):
        config_file = tmp_path / "apcore.yaml"
        config_file.write_text("extensions:\n  root: /custom/path\nlogging:\n  level: DEBUG\n")
        resolver = ConfigResolver(config_path=str(config_file))
        assert resolver._config_file is not None
        assert resolver._config_file["extensions.root"] == "/custom/path"
        assert resolver._config_file["logging.level"] == "DEBUG"

    def test_load_config_file_not_found(self):
        resolver = ConfigResolver(config_path="/nonexistent/apcore.yaml")
        assert resolver._config_file is None

    def test_load_config_file_malformed_yaml(self, tmp_path, caplog):
        config_file = tmp_path / "apcore.yaml"
        config_file.write_text(":\n  :\n    - [invalid{yaml")
        with caplog.at_level(logging.WARNING, logger="apcore_cli.config"):
            resolver = ConfigResolver(config_path=str(config_file))
        assert resolver._config_file is None
        assert "malformed" in caplog.text

    def test_load_config_file_not_dict(self, tmp_path, caplog):
        config_file = tmp_path / "apcore.yaml"
        config_file.write_text("- item1\n- item2\n")
        with caplog.at_level(logging.WARNING, logger="apcore_cli.config"):
            resolver = ConfigResolver(config_path=str(config_file))
        assert resolver._config_file is None
        assert "malformed" in caplog.text

    def test_flatten_dict_nested(self):
        resolver = ConfigResolver(config_path="/nonexistent/apcore.yaml")
        result = resolver._flatten_dict({"extensions": {"root": "/path"}})
        assert result == {"extensions.root": "/path"}

    def test_flatten_dict_deeply_nested(self):
        resolver = ConfigResolver(config_path="/nonexistent/apcore.yaml")
        result = resolver._flatten_dict({"a": {"b": {"c": "deep_value"}}})
        assert result == {"a.b.c": "deep_value"}
