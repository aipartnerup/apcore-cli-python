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


class TestNamespaceAwareConfigResolution:
    """Config Bus namespace ↔ legacy key fallback (apcore >= 0.15.0)."""

    def test_defaults_contain_namespace_keys(self):
        resolver = ConfigResolver()
        for key in [
            "apcore-cli.stdin_buffer_limit",
            "apcore-cli.auto_approve",
            "apcore-cli.help_text_max_length",
            "apcore-cli.logging_level",
        ]:
            assert key in resolver.DEFAULTS, f"Missing namespace default: {key}"

    def test_resolve_namespace_key_from_legacy_config_file(self, tmp_path, clean_env):
        """Querying 'apcore-cli.stdin_buffer_limit' finds 'cli.stdin_buffer_limit' in file."""
        config_file = tmp_path / "apcore.yaml"
        config_file.write_text("cli:\n  stdin_buffer_limit: 5242880\n")
        resolver = ConfigResolver(config_path=str(config_file))
        result = resolver.resolve("apcore-cli.stdin_buffer_limit")
        assert result == 5242880

    def test_resolve_legacy_key_from_namespace_config_file(self, tmp_path, clean_env):
        """Querying 'cli.auto_approve' finds 'apcore-cli.auto_approve' in file."""
        config_file = tmp_path / "apcore.yaml"
        config_file.write_text("apcore-cli:\n  auto_approve: true\n")
        resolver = ConfigResolver(config_path=str(config_file))
        result = resolver.resolve("cli.auto_approve")
        assert result is True

    def test_direct_key_takes_precedence_over_alternate(self, tmp_path, clean_env):
        """When both keys exist in file, the directly-queried key wins."""
        config_file = tmp_path / "apcore.yaml"
        config_file.write_text("cli:\n  help_text_max_length: 500\n" "apcore-cli:\n  help_text_max_length: 2000\n")
        resolver = ConfigResolver(config_path=str(config_file))
        assert resolver.resolve("cli.help_text_max_length") == 500
        assert resolver.resolve("apcore-cli.help_text_max_length") == 2000

    def test_namespace_mapping_is_bidirectional(self):
        resolver = ConfigResolver()
        assert len(resolver._NAMESPACE_TO_LEGACY) == len(resolver._LEGACY_TO_NAMESPACE)
        for ns_key, legacy_key in resolver._NAMESPACE_TO_LEGACY.items():
            assert resolver._LEGACY_TO_NAMESPACE[legacy_key] == ns_key
