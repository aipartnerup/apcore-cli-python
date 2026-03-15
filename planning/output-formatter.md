# Implementation Plan: Output Formatter

**Priority**: P1
**Source Spec**: `../apcore-cli/docs/features/output-formatter.md`
**Module Path**: `apcore_cli/output.py`
**Dependencies**: Core Dispatcher

---

## Tasks

### Task 1: resolve_format and _truncate helper
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_output.py`:
  - `test_resolve_format_explicit_json`: `resolve_format("json")` → `"json"`.
  - `test_resolve_format_explicit_table`: `resolve_format("table")` → `"table"`.
  - `test_resolve_format_none_tty`: Mock `isatty()` True → `"table"`.
  - `test_resolve_format_none_non_tty`: Mock `isatty()` False → `"json"`.
  - `test_truncate_short`: 50-char text → unchanged.
  - `test_truncate_exact`: 80-char text → unchanged.
  - `test_truncate_long`: 100-char text → 77 chars + "...".

**GREEN** — Implement `resolve_format()` and `_truncate()`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_output.py -v`

---

### Task 2: format_module_list
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_output.py`:
  - `test_format_list_table_with_modules`: 2 modules → table output contains IDs.
  - `test_format_list_table_empty`: No modules → "No modules found." message.
  - `test_format_list_table_empty_with_tags`: No matches with tags → "No modules found matching tags: ..." message.
  - `test_format_list_json_with_modules`: 2 modules → valid JSON array with id, description, tags.
  - `test_format_list_json_empty`: No modules → `[]`.
  - `test_format_list_description_truncated`: Module with 120-char description → truncated in table.

**GREEN** — Implement `format_module_list()`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_output.py -v`

---

### Task 3: format_module_detail
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_output.py`:
  - `test_format_detail_table_full`: Module with all metadata → Panel, schemas, annotations, tags rendered.
  - `test_format_detail_table_minimal`: Module with only id/description → no schema/annotation sections.
  - `test_format_detail_json_full`: Full metadata → valid JSON with all fields.
  - `test_format_detail_json_no_none`: Fields with `None` value → omitted from JSON.

**GREEN** — Implement `format_module_detail()`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_output.py -v`

---

### Task 4: format_exec_result
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_output.py`:
  - `test_format_exec_dict`: Dict result → JSON-formatted output.
  - `test_format_exec_list`: List result → JSON-formatted output.
  - `test_format_exec_string`: String result → printed directly.
  - `test_format_exec_none`: None result → empty stdout.
  - `test_format_exec_other`: Integer result → `str(result)`.
  - `test_format_exec_non_serializable`: Object with `default=str` fallback.

**GREEN** — Implement `format_exec_result()`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_output.py -v`

---

## Exit Criteria
- All 4 tasks complete with passing tests.
- TTY-adaptive format detection works correctly.
- Table and JSON output formats produce correct output.
- Description truncation at 80 chars works.
- Exec result formatting handles all types.
