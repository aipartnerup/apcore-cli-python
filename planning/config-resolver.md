# Implementation Plan: Config Resolver

**Priority**: P0 (Foundation)
**Source Spec**: `../apcore-cli/docs/features/config-resolver.md`
**Module Path**: `apcore_cli/config.py`
**Dependencies**: None (foundation layer)

---

## Tasks

### Task 1: Project scaffolding and ConfigResolver class skeleton
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_config.py`:
  - `test_config_resolver_instantiation`: Create `ConfigResolver()` with no args, assert it exists and has `DEFAULTS` dict.
  - `test_config_resolver_with_cli_flags`: Create `ConfigResolver(cli_flags={"--extensions-dir": "/cli"})`, assert flags stored.
  - `test_defaults_contains_expected_keys`: Assert `DEFAULTS` has keys `extensions.root`, `logging.level`, `sandbox.enabled`, `cli.stdin_buffer_limit`.

**GREEN** — Implement minimally:
- Create `pyproject.toml` with project metadata, dependencies (`click`, `jsonschema`, `rich`, `pyyaml`), dev dependencies (`pytest`), and `[project.scripts]` entry point.
- Create `apcore_cli/__init__.py` (empty).
- Create `apcore_cli/config.py` with `ConfigResolver` class, `DEFAULTS` dict, `__init__` method.
- Create `tests/__init__.py` (empty).
- Create `tests/conftest.py` with basic fixtures.

**REFACTOR** — None needed for skeleton.

**Verification**: `pytest tests/test_config.py -v` — all 3 tests pass.

---

### Task 2: ConfigResolver.resolve() — 4-tier precedence
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_config.py`:
  - `test_resolve_tier1_cli_flag_wins`: CLI flag set, env var set, config file set → CLI flag returned.
  - `test_resolve_tier2_env_var_wins`: No CLI flag, env var set, config file set → env var returned.
  - `test_resolve_tier3_config_file_wins`: No CLI flag, no env var, config file set → config value returned.
  - `test_resolve_tier4_default_wins`: No CLI flag, no env var, no config file → default returned.
  - `test_resolve_cli_flag_none_skips`: CLI flag explicitly `None` → falls through to env var.
  - `test_resolve_env_var_empty_string_skips`: Env var is `""` → falls through to config file.
  - `test_resolve_unknown_key_returns_none`: Unknown key with no sources → returns `None`.

**GREEN** — Implement `resolve(key, cli_flag=None, env_var=None)`:
- Check tiers in order: CLI flag → env var → config file → defaults.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_config.py -v` — all tests pass.

---

### Task 3: Config file loading and flattening
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_config.py`:
  - `test_load_config_file_valid_yaml`: Create temp `apcore.yaml` with nested keys, assert flattened correctly.
  - `test_load_config_file_not_found`: Non-existent path → `_config_file` is `None`, no error.
  - `test_load_config_file_malformed_yaml`: Invalid YAML → `_config_file` is `None`, WARNING logged.
  - `test_load_config_file_not_dict`: YAML that parses to list → `_config_file` is `None`, WARNING logged.
  - `test_flatten_dict_nested`: `{"extensions": {"root": "/path"}}` → `{"extensions.root": "/path"}`.
  - `test_flatten_dict_deeply_nested`: 3 levels deep → correct dot-notation.

**GREEN** — Implement `_load_config_file()` and `_flatten_dict()`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_config.py -v` — all tests pass.

---

## Boundary Values

| Parameter | Min | Max | Default |
|-----------|-----|-----|---------|
| Config file size | 0 bytes | No limit | — |
| Nesting depth (flatten) | 0 | No limit | — |
| Key length | 1 char | No limit | — |

## Exit Criteria
- All 3 tasks complete with passing tests.
- `ConfigResolver` correctly implements 4-tier precedence.
- Config file loading is resilient to missing/malformed files.
