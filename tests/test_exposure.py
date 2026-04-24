"""Tests for ExposureFilter (FE-12)."""

from __future__ import annotations

import logging

import click
import pytest
from apcore_cli.exposure import ExposureFilter, _glob_match

# --- Task 1: _glob_match tests ---


class TestGlobMatch:
    def test_exact_match(self):
        assert _glob_match("system.health", "system.health") is True

    def test_exact_no_partial(self):
        assert _glob_match("system.health.check", "system.health") is False

    def test_single_star_matches_one_segment(self):
        assert _glob_match("admin.users", "admin.*") is True

    def test_single_star_not_across_dots(self):
        assert _glob_match("admin.users.list", "admin.*") is False

    def test_single_star_not_prefix_only(self):
        assert _glob_match("admin", "admin.*") is False

    def test_star_prefix_match(self):
        assert _glob_match("product.get", "*.get") is True

    def test_star_prefix_no_deep(self):
        assert _glob_match("product.get.all", "*.get") is False

    def test_double_star_matches_across_segments(self):
        assert _glob_match("admin.users", "admin.**") is True
        assert _glob_match("admin.users.list", "admin.**") is True

    def test_double_star_not_bare_prefix(self):
        assert _glob_match("admin", "admin.**") is False

    def test_bare_star(self):
        assert _glob_match("standalone", "*") is True
        assert _glob_match("a.b", "*") is False

    def test_bare_double_star(self):
        assert _glob_match("anything", "**") is True
        assert _glob_match("a.b.c.d", "**") is True

    def test_literal_no_glob(self):
        assert _glob_match("admin.users", "admin.users") is True
        assert _glob_match("admin.config", "admin.users") is False


# --- Task 2: ExposureFilter tests ---


class TestExposureFilter:
    def test_mode_all_exposes_everything(self):
        f = ExposureFilter(mode="all")
        assert f.is_exposed("anything") is True

    def test_mode_include_matches(self):
        f = ExposureFilter(mode="include", include=["admin.*", "jobs.*"])
        assert f.is_exposed("admin.users") is True
        assert f.is_exposed("webhooks.stripe") is False

    def test_mode_include_empty_list_exposes_nothing(self):
        f = ExposureFilter(mode="include", include=[])
        assert f.is_exposed("anything") is False

    def test_mode_exclude_matches(self):
        f = ExposureFilter(mode="exclude", exclude=["webhooks.*", "internal.*"])
        assert f.is_exposed("admin.users") is True
        assert f.is_exposed("webhooks.stripe") is False

    def test_mode_exclude_empty_list_exposes_all(self):
        f = ExposureFilter(mode="exclude", exclude=[])
        assert f.is_exposed("anything") is True

    def test_filter_modules_partitions(self):
        f = ExposureFilter(mode="include", include=["admin.*"])
        exposed, hidden = f.filter_modules(["admin.users", "admin.config", "webhooks.stripe"])
        assert exposed == ["admin.users", "admin.config"]
        assert hidden == ["webhooks.stripe"]

    def test_duplicate_patterns_deduplicated(self):
        f = ExposureFilter(mode="include", include=["admin.*", "admin.*"])
        assert f.is_exposed("admin.users") is True

    def test_default_is_mode_all(self):
        f = ExposureFilter()
        assert f.is_exposed("anything") is True


# --- Task 3: from_config tests ---


class TestExposureFilterFromConfig:
    def test_from_config_include_mode(self):
        f = ExposureFilter.from_config({"expose": {"mode": "include", "include": ["admin.*"]}})
        assert f._mode == "include"
        assert f.is_exposed("admin.users") is True
        assert f.is_exposed("webhooks.stripe") is False

    def test_from_config_exclude_mode(self):
        f = ExposureFilter.from_config({"expose": {"mode": "exclude", "exclude": ["webhooks.*"]}})
        assert f._mode == "exclude"
        assert f.is_exposed("webhooks.stripe") is False

    def test_from_config_missing_expose_key(self):
        f = ExposureFilter.from_config({})
        assert f._mode == "all"

    def test_from_config_invalid_mode_raises(self):
        with pytest.raises(click.BadParameter, match="Invalid expose mode"):
            ExposureFilter.from_config({"expose": {"mode": "whitelist"}})

    def test_from_config_expose_not_dict_warns(self, caplog):
        with caplog.at_level(logging.WARNING, logger="apcore_cli.exposure"):
            f = ExposureFilter.from_config({"expose": "invalid"})
        assert f._mode == "all"
        assert "expected dict" in caplog.text

    def test_from_config_include_not_list_warns(self, caplog):
        with caplog.at_level(logging.WARNING, logger="apcore_cli.exposure"):
            f = ExposureFilter.from_config({"expose": {"mode": "include", "include": "admin.*"}})
        assert f._mode == "include"
        assert "expected list" in caplog.text

    def test_from_config_empty_string_in_list_warns(self, caplog):
        with caplog.at_level(logging.WARNING, logger="apcore_cli.exposure"):
            f = ExposureFilter.from_config({"expose": {"mode": "include", "include": ["admin.*", ""]}})
        assert f.is_exposed("admin.users") is True
        assert "Empty pattern" in caplog.text

    def test_from_config_mode_all_ignores_lists(self):
        f = ExposureFilter.from_config({"expose": {"mode": "all", "include": ["admin.*"]}})
        assert f._mode == "all"
        assert f.is_exposed("webhooks.stripe") is True
