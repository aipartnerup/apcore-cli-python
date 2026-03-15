# Implementation Plan: Discovery

**Priority**: P1
**Source Spec**: `../apcore-cli/docs/features/discovery.md`
**Module Path**: `apcore_cli/discovery.py`
**Dependencies**: Core Dispatcher, Output Formatter

---

## Tasks

### Task 1: list_cmd — basic listing and tag filtering
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_discovery.py`:
  - `test_list_cmd_shows_modules`: 2 modules registered → both appear in output.
  - `test_list_cmd_empty_registry`: No modules → "No modules found." Exit 0.
  - `test_list_cmd_tag_filter_single`: `--tag math` → only math-tagged modules.
  - `test_list_cmd_tag_filter_and`: `--tag math --tag core` → only modules with BOTH tags.
  - `test_list_cmd_tag_no_match`: `--tag nonexistent` → "No modules found matching tags: nonexistent." Exit 0.
  - `test_list_cmd_format_json`: `--format json` → valid JSON array output.
  - `test_list_cmd_format_table`: `--format table` → table output with columns.
  - `test_list_cmd_non_tty_default_json`: Non-TTY context → JSON output by default.

**GREEN** — Implement `list_cmd` Click command in `discovery.py`.

**REFACTOR** — Extract format resolution to use `output.resolve_format()`.

**Verification**: `pytest tests/test_discovery.py -v`

---

### Task 2: describe_cmd — full module metadata display
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_discovery.py`:
  - `test_describe_valid_module`: Known module → full metadata displayed. Exit 0.
  - `test_describe_not_found`: Unknown module → exit 44, stderr "not found".
  - `test_describe_invalid_id`: `"INVALID!"` → exit 2.
  - `test_describe_json_format`: `--format json` → JSON object with all metadata fields.
  - `test_describe_no_output_schema`: Module without output_schema → section omitted.
  - `test_describe_no_annotations`: Module without annotations → section omitted.
  - `test_describe_with_x_fields`: Module with `x-custom` metadata → shown under Extension Metadata.

**GREEN** — Implement `describe_cmd` Click command in `discovery.py`.

**REFACTOR** — Use `output.format_module_detail()` for rendering.

**Verification**: `pytest tests/test_discovery.py -v`

---

### Task 3: Integration with CLI group
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_discovery.py`:
  - `test_list_registered_as_command`: `apcore-cli list` is a recognized command.
  - `test_describe_registered_as_command`: `apcore-cli describe` is a recognized command.
  - `test_list_help`: `apcore-cli list --help` shows tag and format options.
  - `test_describe_help`: `apcore-cli describe --help` shows module_id argument and format option.
  - `test_list_invalid_format`: `--format yaml` → Click rejects. Exit 2.

**GREEN** — Wire `list_cmd` and `describe_cmd` as built-in commands in `LazyModuleGroup`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_discovery.py -v`

---

## Exit Criteria
- All 3 tasks complete with passing tests.
- `apcore-cli list` shows modules with tag filtering and format selection.
- `apcore-cli describe <module_id>` shows full metadata with syntax highlighting.
- TTY-adaptive default format works correctly.
