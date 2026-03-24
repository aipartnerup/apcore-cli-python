# Implementation Plan: Grouped CLI Commands

**Priority**: P0
**Source Spec**: `../apcore-cli/docs/features/grouped-commands.md`
**Module Paths**: `apcore_cli/cli.py`, `apcore_cli/__main__.py`, `apcore_cli/discovery.py`, `apcore_cli/output.py`, `apcore_cli/shell.py`
**Dependencies**: Core Dispatcher (FE-01), Display Overlay (§5.13)

---

## Tasks

### Task 1: `_resolve_group()` — group resolution logic
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_cli.py` (class `TestResolveGroup`):
- `test_resolve_group_explicit_group`: descriptor with `display.cli.group = "admin"`, `display.cli.alias = "create"` → returns `("admin", "create")`
- `test_resolve_group_explicit_group_no_alias`: descriptor with `display.cli.group = "admin"` but no alias → returns `("admin", module_id)`
- `test_resolve_group_opt_out_empty_string`: descriptor with `display.cli.group = ""`, `display.cli.alias = "healthcheck"` → returns `(None, "healthcheck")`
- `test_resolve_group_auto_from_alias_dot`: descriptor with `display.cli.alias = "user.list"`, no group → returns `("user", "list")`
- `test_resolve_group_auto_from_module_id_dot`: module_id `"user.create"`, no display overlay → returns `("user", "create")`
- `test_resolve_group_no_dot_top_level`: module_id `"standalone"`, no display overlay → returns `(None, "standalone")`
- `test_resolve_group_multi_dot_first_only`: module_id `"a.b.c"`, no display overlay → returns `("a", "b.c")`
- `test_resolve_group_empty_module_id_warns`: module_id `""` → returns `(None, "")`, WARNING logged

**GREEN** — Implement `_resolve_group(module_id, descriptor)` as a static method on `GroupedModuleGroup`:
1. Read `display = _get_display(descriptor)`, `cli_display = display.get("cli") or {}`.
2. `explicit_group = cli_display.get("group")`.
3. If `explicit_group` is non-empty string: return `(explicit_group, cli_display.get("alias") or module_id)`.
4. If `explicit_group == ""`: return `(None, cli_display.get("alias") or module_id)`.
5. `cli_name = cli_display.get("alias") or module_id`.
6. If `"." in cli_name`: `group, _, cmd = cli_name.partition(".")` → return `(group, cmd)`.
7. Else: return `(None, cli_name)`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py::TestResolveGroup -v`

---

### Task 2: `_build_group_map()` and `GroupedModuleGroup.__init__`
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_cli.py` (class `TestBuildGroupMap`):
- `test_build_group_map_three_groups`: Registry has `product.list`, `product.get`, `user.create`, `user.list`, `standalone` → `_group_map = {"product": 2 entries, "user": 2 entries}`, `_top_level_modules = {"standalone": 1 entry}`
- `test_build_group_map_idempotent`: Call twice → second call is a no-op (check registry.list call count = 1)
- `test_build_group_map_builtin_collision_warns`: Module `list.something` exists → WARNING logged about collision with built-in command `list`
- `test_build_group_map_failure_allows_retry`: Registry raises on first call → `_group_map_built` stays False, second call retries
- `test_build_group_map_with_display_overlay_group`: descriptor with `display.cli.group = "admin"`, `display.cli.alias = "create"` → grouped under "admin" with command name "create"

**GREEN** — Implement:
- `GroupedModuleGroup(LazyModuleGroup)` with `__init__` adding `_group_map`, `_top_level_modules`, `_group_cache`, `_group_map_built`.
- `_build_group_map()`:
  1. Guard: if `_group_map_built`, return.
  2. Call `self._build_alias_map()` (parent method populates descriptor cache).
  3. Iterate `self._registry.list()`, get descriptors from cache, call `_resolve_group`.
  4. Partition into `_group_map` and `_top_level_modules`.
  5. Check group name collisions with `BUILTIN_COMMANDS`, log warnings.
  6. Set `_group_map_built = True` inside try block.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py::TestBuildGroupMap -v`

---

### Task 3: `list_commands()` and `get_command()` overrides
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_cli.py` (class `TestGroupedModuleGroupRouting`):
- `test_list_commands_shows_groups_and_top_level`: With product (2 modules) + user (2 modules) + standalone → returns sorted `[completion, describe, exec, list, man, product, standalone, user]`
- `test_get_command_returns_lazy_group`: `get_command(ctx, "product")` → returns a `click.Group` instance (the `_LazyGroup`)
- `test_get_command_returns_top_level_command`: `get_command(ctx, "standalone")` → returns a `click.Command` (not a group)
- `test_get_command_returns_builtin`: `get_command(ctx, "list")` → returns built-in list command (not a group named "list")
- `test_get_command_unknown_returns_none`: `get_command(ctx, "nonexistent")` → returns `None`
- `test_get_command_caches_lazy_group`: Two calls to `get_command(ctx, "product")` → same object

**GREEN** — Override `list_commands()` and `get_command()` on `GroupedModuleGroup`:
- `list_commands`: build group map, return sorted(builtins + group names (excluding collisions) + top-level module names).
- `get_command`: check builtins → check group cache → check group map (create `_LazyGroup`) → check top-level modules → None.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py::TestGroupedModuleGroupRouting -v`

---

### Task 4: `_LazyGroup` — nested group commands
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_cli.py` (class `TestLazyGroup`):
- `test_lazy_group_list_commands`: `_LazyGroup` with members `{"list": ..., "get": ..., "create": ...}` → `list_commands` returns `["create", "get", "list"]`
- `test_lazy_group_get_command`: `get_command(ctx, "list")` → returns a `click.Command` built from the descriptor
- `test_lazy_group_get_command_not_found`: `get_command(ctx, "nonexistent")` → returns `None`
- `test_lazy_group_caches_commands`: Two calls to `get_command(ctx, "list")` → same object
- `test_lazy_group_command_execution`: Via `CliRunner`, invoke `apcore-cli product list --category food` → executor called with correct module_id and args

**GREEN** — Implement `_LazyGroup(click.Group)`:
- `__init__`: store `members`, `executor`, `help_text_max_length`, init `_cmd_cache`.
- `list_commands`: return `sorted(self._members.keys())`.
- `get_command`: check cache → lookup in members → `build_module_command` → cache → return.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py::TestLazyGroup -v`

---

### Task 5: `format_help()` — collapsed root help display
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_cli.py` (class `TestGroupedHelpDisplay`):
- `test_root_help_shows_groups_section`: Via `CliRunner --help`, output contains "Groups:" section header
- `test_root_help_shows_group_with_count`: Output contains `product` with "(3 commands)" or similar count
- `test_root_help_shows_top_level_modules`: Output contains "Modules:" section with standalone command
- `test_root_help_shows_builtin_commands`: Output contains "Commands:" with exec, list, describe, etc.
- `test_group_help_shows_commands`: Via `CliRunner`, `apcore-cli product --help` shows individual commands (list, get, create)

**GREEN** — Override `format_help()` on `GroupedModuleGroup`:
1. Build group map.
2. Use Click's `HelpFormatter` to write sections: Options, Commands (builtins), Modules (top-level), Groups (with counts).
3. `_LazyGroup` uses default Click help formatting (shows its commands normally).

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py::TestGroupedHelpDisplay -v`

---

### Task 6: Wire `GroupedModuleGroup` into `create_cli()`
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_cli.py` (class `TestCreateCliGrouped`):
- `test_create_cli_uses_grouped_module_group`: Call `create_cli(extensions_dir=...)` → returned group is instance of `GroupedModuleGroup`

**GREEN** — Change `__main__.py`:
- Import `GroupedModuleGroup` instead of (or in addition to) `LazyModuleGroup`.
- Change `cls=LazyModuleGroup` → `cls=GroupedModuleGroup` in the `@click.group()` decorator.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py::TestCreateCliGrouped -v`

---

### Task 7: Discovery `list --flat` and `describe group.command`
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_discovery.py` (class `TestGroupedDiscovery`):
- `test_list_flat_flag`: `apcore-cli list --flat` → output matches flat table (all modules, no grouping)
- `test_list_default_grouped_display`: `apcore-cli list` with grouped modules → output shows group headers with commands underneath
- `test_describe_group_dot_command`: `apcore-cli describe product.list` → resolves to the correct module, shows metadata
- `test_describe_full_module_id`: `apcore-cli describe product.list_products.get` → works with canonical module_id

**GREEN** — Modify `discovery.py`:
- `list_cmd`: add `--flat` flag. When not flat, group modules by their display group and render grouped output.
- `describe_cmd`: before `validate_module_id`, try to resolve `group.command` notation → scan registry for matching module_id.

Modify `output.py`:
- Add `format_grouped_module_list()` that renders modules grouped under section headers.

**REFACTOR** — Ensure `format_module_list()` still works for `--flat` path.

**Verification**: `pytest tests/test_discovery.py::TestGroupedDiscovery -v`

---

### Task 8: Shell completion for nested groups
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_shell.py` (class `TestGroupedCompletion`):
- `test_bash_completion_includes_groups`: Generated bash completion for position 1 includes group names
- `test_bash_completion_nested_commands`: At position 2 after a group name, completes with group's commands
- `test_zsh_completion_includes_groups`: Generated zsh completion includes group names
- `test_fish_completion_includes_groups`: Generated fish completion includes group names and nested subcommands

**GREEN** — Modify `shell.py`:
- Update `_generate_bash_completion`: position 1 completes with builtins + group names + top-level modules; position 2 after a group name completes with that group's commands.
- Update `_generate_zsh_completion` and `_generate_fish_completion` similarly.
- Accept `registry` parameter (or group instance) to get group/command lists dynamically.

**REFACTOR** — Extract common group/command list generation.

**Verification**: `pytest tests/test_shell.py::TestGroupedCompletion -v`

---

### Task 9: Integration tests — end-to-end grouped invocation
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests in `tests/test_cli.py` (class `TestGroupedE2E`):
- `test_grouped_invocation_product_get`: Via `CliRunner`, `apcore-cli product get --id 123` → executor called with correct module_id
- `test_single_command_group_works`: `apcore-cli health check` → executor called with `health.check` module_id
- `test_top_level_module_works`: `apcore-cli standalone --key val` → executor called with `standalone` module_id
- `test_unknown_group_exits_2`: `apcore-cli nonexistent` → exit code 2
- `test_unknown_command_in_group_exits_2`: `apcore-cli product nonexistent` → exit code 2

**GREEN** — No new production code (this validates the full stack from tasks 1–8).

**REFACTOR** — Fix any issues found during integration.

**Verification**: `pytest tests/test_cli.py::TestGroupedE2E -v`

---

## Implementation Order

Execute tasks sequentially: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9

Tasks 1–4 are the core grouped commands engine (cli.py only).
Task 5 is the help display.
Task 6 wires it in.
Tasks 7–8 update downstream features.
Task 9 is the integration test sweep.

## Files Modified

| File | Tasks | Changes |
|------|-------|---------|
| `src/apcore_cli/cli.py` | 1–5 | Add `GroupedModuleGroup`, `_LazyGroup`, `_resolve_group`, `_build_group_map`, `format_help` |
| `src/apcore_cli/__main__.py` | 6 | Change `cls=LazyModuleGroup` → `cls=GroupedModuleGroup` |
| `src/apcore_cli/discovery.py` | 7 | Add `--flat` flag, `group.command` resolution in `describe` |
| `src/apcore_cli/output.py` | 7 | Add `format_grouped_module_list()` |
| `src/apcore_cli/shell.py` | 8 | Update completion generators for two-level groups |
| `tests/test_cli.py` | 1–6, 9 | ~30 new tests across 7 test classes |
| `tests/test_discovery.py` | 7 | ~4 new tests |
| `tests/test_shell.py` | 8 | ~4 new tests |
