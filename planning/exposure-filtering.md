# Implementation Plan: Module Exposure Filtering

**Priority**: P1
**Source Spec**: `../apcore-cli/docs/features/exposure-filtering.md`
**Module Paths**: `apcore_cli/exposure.py` (new), `apcore_cli/cli.py`, `apcore_cli/__main__.py`, `apcore_cli/config.py`, `apcore_cli/discovery.py`, `apcore_cli/output.py`
**Dependencies**: Core Dispatcher (FE-01), Grouped Commands (FE-09), Config Resolver (FE-07), Discovery (FE-04)

---

## Tasks

### Task 1: `_glob_match()` — pattern-to-regex compiler
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_exposure.py` (class `TestGlobMatch`):
- `test_exact_match`: pattern `"system.health"`, module_id `"system.health"` → True
- `test_exact_no_partial`: pattern `"system.health"`, module_id `"system.health.check"` → False
- `test_single_star_matches_one_segment`: pattern `"admin.*"`, module_id `"admin.users"` → True
- `test_single_star_not_across_dots`: pattern `"admin.*"`, module_id `"admin.users.list"` → False
- `test_single_star_not_prefix_only`: pattern `"admin.*"`, module_id `"admin"` → False
- `test_star_prefix`: pattern `"*.get"`, module_id `"product.get"` → True; `"product.get.all"` → False
- `test_double_star_matches_across_segments`: pattern `"admin.**"`, module_id `"admin.users"` → True; `"admin.users.list"` → True
- `test_double_star_not_bare_prefix`: pattern `"admin.**"`, module_id `"admin"` → False
- `test_bare_star`: pattern `"*"` matches any single-segment id like `"standalone"` → True; multi-segment `"a.b"` → False
- `test_bare_double_star`: pattern `"**"` matches any module_id → True
- `test_literal_no_glob`: pattern `"admin.users"` matches only `"admin.users"` → True; `"admin.config"` → False

**GREEN** — Create `src/apcore_cli/exposure.py`. Implement `_glob_match(module_id: str, pattern: str) -> bool`:
1. Replace `**` with sentinel `\x00GLOB\x00`.
2. Escape regex special chars in remaining text (except `*`).
3. Replace remaining `*` with `[^.]*` (single segment).
4. Replace sentinel with `.*` (any segments).
5. Anchor with `^...$` and match via `re.fullmatch`.

Also implement `_compile_patterns(patterns: list[str]) -> list[re.Pattern]` to pre-compile at init time.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_exposure.py::TestGlobMatch -v`

---

### Task 2: `ExposureFilter` — core class with `is_exposed` and `filter_modules`
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_exposure.py` (class `TestExposureFilter`):
- `test_mode_all_exposes_everything`: `ExposureFilter(mode="all")` → `is_exposed("anything")` returns True
- `test_mode_include_matches`: `ExposureFilter(mode="include", include=["admin.*", "jobs.*"])` → `is_exposed("admin.users")` True, `is_exposed("webhooks.stripe")` False
- `test_mode_include_empty_list_exposes_nothing`: `ExposureFilter(mode="include", include=[])` → `is_exposed("anything")` returns False
- `test_mode_exclude_matches`: `ExposureFilter(mode="exclude", exclude=["webhooks.*", "internal.*"])` → `is_exposed("admin.users")` True, `is_exposed("webhooks.stripe")` False
- `test_mode_exclude_empty_list_exposes_all`: `ExposureFilter(mode="exclude", exclude=[])` → `is_exposed("anything")` True
- `test_filter_modules_partitions`: `ExposureFilter(mode="include", include=["admin.*"])` → `filter_modules(["admin.users", "admin.config", "webhooks.stripe"])` returns `(["admin.users", "admin.config"], ["webhooks.stripe"])`
- `test_duplicate_patterns_deduplicated`: `ExposureFilter(mode="include", include=["admin.*", "admin.*"])` → works without error
- `test_default_is_mode_all`: `ExposureFilter()` → `is_exposed("anything")` True

**GREEN** — Implement `ExposureFilter` class in `exposure.py`:
- `__init__(mode="all", include=None, exclude=None)`: validate mode, dedup patterns, pre-compile regexes.
- `is_exposed(module_id)`: mode dispatch → all/include/exclude logic per spec §4.3.
- `filter_modules(module_ids)`: partition into (exposed, hidden) per spec §4.6.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_exposure.py::TestExposureFilter -v`

---

### Task 3: `ExposureFilter.from_config()` — config parsing with validation
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_exposure.py` (class `TestExposureFilterFromConfig`):
- `test_from_config_include_mode`: `{"expose": {"mode": "include", "include": ["admin.*"]}}` → ExposureFilter with mode="include"
- `test_from_config_exclude_mode`: `{"expose": {"mode": "exclude", "exclude": ["webhooks.*"]}}` → ExposureFilter with mode="exclude"
- `test_from_config_missing_expose_key`: `{}` → ExposureFilter with mode="all" (default)
- `test_from_config_invalid_mode_raises`: `{"expose": {"mode": "whitelist"}}` → raises `click.BadParameter`
- `test_from_config_expose_not_dict_warns`: `{"expose": "invalid"}` → WARNING logged, returns mode="all"
- `test_from_config_include_not_list_warns`: `{"expose": {"mode": "include", "include": "admin.*"}}` → WARNING, include=[]
- `test_from_config_empty_string_in_list_warns`: `{"expose": {"mode": "include", "include": ["admin.*", ""]}}` → WARNING, empty string skipped
- `test_from_config_mode_all_ignores_lists`: `{"expose": {"mode": "all", "include": ["admin.*"]}}` → mode="all", include list is ignored

**GREEN** — Implement `from_config(cls, config: dict) -> ExposureFilter`:
1. Read `expose = config.get("expose", {})`.
2. Type-check expose is dict, mode is valid, include/exclude are lists.
3. Filter empty strings, log warnings.
4. Return constructed `ExposureFilter`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_exposure.py::TestExposureFilterFromConfig -v`

---

### Task 4: Wire `ExposureFilter` into `GroupedModuleGroup`
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_cli.py` (class `TestExposureInGroupedModuleGroup`):
- `test_build_group_map_with_include_filter`: Registry has `admin.users`, `admin.config`, `webhooks.stripe`, `user.create`. ExposureFilter(mode="include", include=["admin.*"]) → `_group_map` contains only `admin` group, `_top_level_modules` is empty, `webhooks.stripe` and `user.create` not present.
- `test_build_group_map_with_exclude_filter`: ExposureFilter(mode="exclude", exclude=["webhooks.*"]) → all modules except `webhooks.stripe` in group map.
- `test_build_group_map_default_filter_exposes_all`: No exposure_filter passed (default) → all modules present (backward compatible).
- `test_list_commands_respects_filter`: With include filter on `admin.*` → `list_commands()` returns builtins + `admin` group only, no `user` or `webhooks`.
- `test_get_command_hidden_group_returns_none`: With include filter excluding `user` → `get_command(ctx, "user")` returns None.

**GREEN** — Modify `GroupedModuleGroup.__init__()` to accept `exposure_filter: ExposureFilter | None = None` kwarg. Default to `ExposureFilter()` (mode=all). Store as `self._exposure_filter`.

Modify `_build_group_map()`: after getting descriptor, add `if not self._exposure_filter.is_exposed(module_id): continue` before `_resolve_group()`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py::TestExposureInGroupedModuleGroup -v`

---

### Task 5: Wire `expose` parameter into `create_cli()`
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_cli.py` (class `TestCreateCliExposure`):
- `test_create_cli_with_exposure_filter_instance`: `create_cli(registry=..., executor=..., expose=ExposureFilter(mode="include", include=["admin.*"]))` → returned CLI group has exposure filter applied.
- `test_create_cli_with_exposure_dict`: `create_cli(registry=..., executor=..., expose={"mode": "include", "include": ["admin.*"]})` → ExposureFilter constructed from dict.
- `test_create_cli_default_no_exposure`: `create_cli(registry=..., executor=...)` → mode="all" (backward compatible).
- `test_create_cli_env_var_overrides_config`: Set `APCORE_CLI_EXPOSE_MODE=all`, config file has `mode: include` → mode becomes "all".

**GREEN** — Modify `create_cli()` in `__main__.py`:
1. Add `expose: dict | ExposureFilter | None = None` parameter.
2. Build ExposureFilter:
   - If `isinstance(expose, ExposureFilter)`: use directly.
   - If `isinstance(expose, dict)`: call `ExposureFilter.from_config({"expose": expose})`.
   - Else: check env var `APCORE_CLI_EXPOSE_MODE` for mode override, then fall through to `ConfigResolver._config_file` for full config.
3. Pass `exposure_filter=exposure_filter` to `GroupedModuleGroup` via the `@click.group()` kwargs.

Update `__init__.py` to export `ExposureFilter` in `__all__`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py::TestCreateCliExposure -v`

---

### Task 6: `ConfigResolver` — add `expose.*` config keys
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_config.py` (class `TestConfigExpose`):
- `test_resolve_expose_mode_from_file`: `apcore.yaml` with `expose.mode: include` → `config.resolve("expose.mode")` returns `"include"`.
- `test_resolve_expose_include_from_file`: `apcore.yaml` with `expose.include: [admin.*]` → resolved correctly.
- `test_expose_defaults`: Without config file → `config.resolve("expose.mode")` returns `"all"`.

**GREEN** — Add to `ConfigResolver.DEFAULTS`:
```python
"expose.mode": "all",
"expose.include": [],
"expose.exclude": [],
```

Note: The `_flatten_dict` method already handles nested YAML → dot-notation, so `expose.mode` from a YAML `expose: { mode: include }` works automatically. However, lists (`expose.include`) won't flatten correctly — they'll be stored as the key `expose.include` with a list value, which is the correct behavior (we want the full list, not flattened).

**REFACTOR** — Verify `_flatten_dict` preserves list values (it does — the `isinstance(value, dict)` check only recurses into dicts, not lists).

**Verification**: `pytest tests/test_config.py::TestConfigExpose -v`

---

### Task 7: `list --exposure` option — discovery enhancement
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_discovery.py` (class `TestExposureListFilter`):
- `test_list_exposure_exposed_default`: `apcore-cli list` with ExposureFilter(include=["admin.*"]) → only admin modules shown.
- `test_list_exposure_hidden`: `apcore-cli list --exposure hidden` → only hidden (non-admin) modules shown.
- `test_list_exposure_all_shows_column`: `apcore-cli list --exposure all` → output contains "Exposure" column with ✓ and — markers.
- `test_list_exposure_all_json_format`: `apcore-cli list --exposure all --format json` → JSON output includes `"exposed": true/false` field.

**GREEN** — Modify `discovery.py`:
1. Add `--exposure` option to `list_cmd` with `click.Choice(["exposed", "hidden", "all"])`, default `"exposed"`.
2. After existing filters, apply exposure filter:
   - Get `exposure_filter` from click context (stored during `create_cli()`).
   - Filter modules based on `--exposure` choice.
3. When `--exposure all`, add "Exposure" column to table output.

Modify `output.py`:
- Update `format_module_list()` and `format_grouped_module_list()` to accept optional `exposure_filter` parameter and `show_exposure_column` flag.

**REFACTOR** — Ensure existing `list` tests still pass (no regression on tag/status/annotation filters).

**Verification**: `pytest tests/test_discovery.py::TestExposureListFilter -v`

---

### Task 8: Integration tests — end-to-end exposure filtering
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_cli.py` (class `TestExposureE2E`):
- `test_help_only_shows_exposed_groups`: Via `CliRunner`, create CLI with include=["admin.*"], registry has admin + user + webhooks modules → `--help` shows only "admin" group, not "user" or "webhooks".
- `test_exec_bypasses_exposure_filter`: Same setup → `apcore-cli exec user.create --name test` succeeds (exit 0).
- `test_hidden_command_not_in_help`: `apcore-cli user --help` → exit 2 ("No such command").
- `test_describe_works_for_hidden_module`: `apcore-cli describe webhooks.stripe` → shows metadata (exit 0).
- `test_include_with_glob_pattern_e2e`: include=["*.get"] → `apcore-cli product get` works, `apcore-cli product create` hidden.

**GREEN** — No new production code (validates the full stack from tasks 1–7).

**REFACTOR** — Fix any issues found during integration testing.

**Verification**: `pytest tests/test_cli.py::TestExposureE2E -v`

---

## Implementation Order

Execute tasks sequentially: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

Tasks 1–3 build the standalone `ExposureFilter` module (no changes to existing code).
Task 4 integrates into `GroupedModuleGroup` (cli.py change).
Task 5 wires into `create_cli()` (entry point change).
Task 6 adds config support.
Task 7 enhances the `list` command.
Task 8 is the integration test sweep.

## Files Modified

| File | Tasks | Changes |
|------|-------|---------|
| `src/apcore_cli/exposure.py` | 1–3 | **New file**: `ExposureFilter`, `_glob_match`, `_compile_patterns`, `from_config` |
| `src/apcore_cli/cli.py` | 4 | `GroupedModuleGroup.__init__` gains `exposure_filter`; `_build_group_map` applies filter |
| `src/apcore_cli/__main__.py` | 5 | `create_cli()` gains `expose` parameter, builds `ExposureFilter` |
| `src/apcore_cli/__init__.py` | 5 | Export `ExposureFilter` in `__all__` |
| `src/apcore_cli/config.py` | 6 | Add `expose.*` keys to `DEFAULTS` |
| `src/apcore_cli/discovery.py` | 7 | Add `--exposure` option to `list` command |
| `src/apcore_cli/output.py` | 7 | Add optional "Exposure" column support |
| `tests/test_exposure.py` | 1–3 | **New file**: ~20 tests across 3 test classes |
| `tests/test_cli.py` | 4–5, 8 | ~14 new tests across 3 test classes |
| `tests/test_config.py` | 6 | ~3 new tests |
| `tests/test_discovery.py` | 7 | ~4 new tests |
