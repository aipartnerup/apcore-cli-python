# Implementation Plan: Core Dispatcher

**Priority**: P0
**Source Spec**: `../apcore-cli/docs/features/core-dispatcher.md`
**Module Paths**: `apcore_cli/cli.py`, `apcore_cli/__main__.py`
**Dependencies**: Config Resolver

---

## Tasks

### Task 1: LazyModuleGroup skeleton and list_commands
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_cli.py`:
  - `test_lazy_module_group_init`: Create with mock Registry and Executor, assert attributes stored.
  - `test_list_commands_returns_builtins`: With empty registry, `list_commands` returns sorted built-in commands.
  - `test_list_commands_includes_modules`: Registry has `math.add`, `text.summarize` → returned alongside built-ins.
  - `test_list_commands_registry_error`: Registry raises exception → only built-in commands returned, no crash.

**GREEN** — Implement:
- `LazyModuleGroup(click.Group)` with `__init__`, `list_commands`, `_module_cache`.
- Mock `Registry` and `Executor` for tests.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py -v`

---

### Task 2: get_command and build_module_command
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_cli.py`:
  - `test_get_command_builtin`: `get_command(ctx, "list")` returns built-in command.
  - `test_get_command_module`: `get_command(ctx, "math.add")` returns dynamically built command.
  - `test_get_command_not_found`: `get_command(ctx, "nonexistent")` returns `None`.
  - `test_get_command_caches_module`: Two calls for same module ID → same object returned.
  - `test_build_module_command_creates_command`: Built command has correct name, help text.

**GREEN** — Implement:
- `get_command()` with built-in check → cache check → registry lookup → `build_module_command`.
- Basic `build_module_command()` that creates a Click command with name/help.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py -v`

---

### Task 3: collect_input — STDIN JSON handling
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_cli.py`:
  - `test_collect_input_no_stdin`: `stdin_flag=None` → returns cli_kwargs with None values removed.
  - `test_collect_input_stdin_valid_json`: Reads from stdin, returns parsed dict.
  - `test_collect_input_stdin_cli_overrides`: CLI flag overrides STDIN key.
  - `test_collect_input_stdin_exceeds_limit`: 15MB input without `--large-input` → exit 2.
  - `test_collect_input_stdin_large_input_allowed`: 15MB with `large_input=True` → accepted.
  - `test_collect_input_stdin_invalid_json`: Non-JSON → exit 2 with message.
  - `test_collect_input_stdin_not_object`: JSON array → exit 2 with message.
  - `test_collect_input_stdin_empty`: Empty stdin → returns `{}`.

**GREEN** — Implement `collect_input(stdin_flag, cli_kwargs, large_input)`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py -v`

---

### Task 4: validate_module_id
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_cli.py`:
  - `test_validate_module_id_valid`: `math.add`, `text.summarize`, `a` → no error.
  - `test_validate_module_id_too_long`: 129-char ID → exit 2.
  - `test_validate_module_id_invalid_format`: `"INVALID!ID"`, `"123abc"`, `".leading.dot"` → exit 2.
  - `test_validate_module_id_max_length`: Exactly 128 chars → valid.

**GREEN** — Implement `validate_module_id(module_id)` with regex and length check.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py -v`

---

### Task 5: main() entry point and CLI integration
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_cli.py`:
  - `test_main_help_flag`: Invoke with `--help` → exit 0, output contains "apcore-cli".
  - `test_main_version_flag`: Invoke with `--version` → exit 0, output matches `apcore-cli, version X.Y.Z`.
  - `test_main_extensions_dir_not_found`: Non-existent path → exit 47.
  - `test_main_extensions_dir_not_readable`: Unreadable dir → exit 47.

**GREEN** — Implement:
- `apcore_cli/__main__.py` with `main()` function.
- Wire up `ConfigResolver`, `Registry`, `Executor`, `LazyModuleGroup`.
- Register `--version` and `--help` on root group.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py -v`

---

### Task 6: Module execution callback (exec flow)
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_cli.py`:
  - `test_exec_module_success`: Mock executor returns result → exit 0, result printed to stdout.
  - `test_exec_module_not_found`: Non-existent module → exit 44.
  - `test_exec_module_validation_error`: Invalid input → exit 45.
  - `test_exec_module_execution_error`: Executor raises → exit 1.
  - `test_exec_keyboard_interrupt`: Simulated Ctrl+C → exit 130.
  - `test_exec_module_disabled`: Disabled module → exit 44.
  - `test_exec_acl_denied`: ACL rejection → exit 77.

**GREEN** — Implement the command callback in `build_module_command`:
- Input collection → validation → approval check → executor call → output formatting.
- Error code mapping.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_cli.py -v`

---

## Exit Criteria
- All 6 tasks complete with passing tests.
- `apcore-cli --help`, `--version` work.
- `apcore-cli exec <module_id>` loads, validates, executes, and outputs results.
- STDIN piping with `--input -` works with size limits and JSON validation.
- All error codes match the error taxonomy.
