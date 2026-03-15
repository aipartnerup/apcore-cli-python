# Implementation Plan: Schema Parser

**Priority**: P0
**Source Spec**: `../apcore-cli/docs/features/schema-parser.md`
**Module Paths**: `apcore_cli/schema_parser.py`, `apcore_cli/ref_resolver.py`
**Dependencies**: Core Dispatcher

---

## Tasks

### Task 1: Basic type mapping (_map_type)
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_schema_parser.py`:
  - `test_map_type_string`: `{"type": "string"}` → `click.STRING`.
  - `test_map_type_integer`: `{"type": "integer"}` → `click.INT`.
  - `test_map_type_number`: `{"type": "number"}` → `click.FLOAT`.
  - `test_map_type_boolean`: `{"type": "boolean"}` → boolean flag marker.
  - `test_map_type_object`: `{"type": "object"}` → `click.STRING`.
  - `test_map_type_array`: `{"type": "array"}` → `click.STRING`.
  - `test_map_type_unknown`: `{"type": "foobar"}` → `click.STRING` + WARNING logged.
  - `test_map_type_missing`: `{}` → `click.STRING` + WARNING logged.
  - `test_map_type_file_convention`: Property name `input_file` → `click.Path(exists=True)`.
  - `test_map_type_x_cli_file`: `{"type": "string", "x-cli-file": true}` → `click.Path(exists=True)`.

**GREEN** — Implement `_map_type(prop_name, prop_schema)` in `schema_parser.py`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_schema_parser.py -v`

---

### Task 2: schema_to_click_options — basic property mapping
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_schema_parser.py`:
  - `test_schema_to_options_simple`: Schema with `name` (string) and `count` (integer) → 2 Click options with correct types.
  - `test_schema_to_options_underscore_to_hyphen`: Property `input_file` → flag `--input-file`.
  - `test_schema_to_options_required`: Required property → `required=True` on option.
  - `test_schema_to_options_default`: Property with `default: 42` → option default is 42.
  - `test_schema_to_options_empty_schema`: No properties → empty list.

**GREEN** — Implement `schema_to_click_options(schema)`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_schema_parser.py -v`

---

### Task 3: Boolean flag pairs and enum choices
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_schema_parser.py`:
  - `test_boolean_flag_pair`: `verbose` boolean → `--verbose/--no-verbose` flag pair.
  - `test_boolean_default_true`: `default: true` → flag default is `True`.
  - `test_enum_choice`: `format` with `enum: ["json", "csv"]` → `click.Choice(["json", "csv"])`.
  - `test_enum_integer_reconversion`: `enum: [1, 2, 3]` → Choice accepts "1", reconverts to int.
  - `test_enum_empty_warning`: Empty enum array → WARNING logged, standard string option.
  - `test_boolean_with_enum_true`: Boolean with `enum: [true]` → treated as standard boolean flag.

**GREEN** — Implement boolean flag pair creation and enum-to-Choice mapping with post-parse reconversion.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_schema_parser.py -v`

---

### Task 4: Help text extraction and flag collision detection
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_schema_parser.py`:
  - `test_help_from_x_llm_description`: `x-llm-description` present → used over `description`.
  - `test_help_from_description`: Only `description` → used.
  - `test_help_truncation`: Description > 200 chars → truncated to 197 + "...".
  - `test_help_none`: No description fields → `None`.
  - `test_flag_collision_detection`: Properties `foo_bar` and `foo-bar` both map to `--foo-bar` → exit 48.

**GREEN** — Implement `_extract_help(prop_schema)` and collision detection in `schema_to_click_options`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_schema_parser.py -v`

---

### Task 5: $ref resolution (resolve_refs)
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_ref_resolver.py`:
  - `test_resolve_simple_ref`: `$ref: "#/$defs/Address"` → Address properties inlined.
  - `test_resolve_nested_ref`: Ref that references another ref → both resolved.
  - `test_resolve_circular_ref`: A → B → A → exit 48.
  - `test_resolve_depth_exceeded`: Chain of 33 refs → exit 48.
  - `test_resolve_unresolvable_ref`: `$ref: "#/$defs/Missing"` → exit 45.
  - `test_resolve_no_refs`: Schema without refs → returned unchanged.
  - `test_resolve_removes_defs`: `$defs` key removed from result.

**GREEN** — Implement `resolve_refs()` and `_resolve_node()` in `ref_resolver.py`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_ref_resolver.py -v`

---

### Task 6: allOf, anyOf, oneOf flattening
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_ref_resolver.py`:
  - `test_allof_merge_properties`: Two sub-schemas → properties merged, required extended.
  - `test_allof_later_overrides`: Conflicting property in later sub-schema → later wins.
  - `test_anyof_union_properties`: Properties unioned.
  - `test_anyof_required_intersection`: Only fields required in ALL branches are required.
  - `test_oneof_same_as_anyof`: Same behavior as anyOf.
  - `test_nested_composition`: allOf containing a $ref → resolved correctly.

**GREEN** — Implement allOf/anyOf/oneOf handling in `_resolve_node()`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_ref_resolver.py -v`

---

### Task 7: STDIN deferred required enforcement
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_schema_parser.py`:
  - `test_required_deferred_with_stdin`: When `--input -` used, required fields not enforced at Click level.
  - `test_required_satisfied_via_stdin`: STDIN provides required field → validation passes.
  - `test_required_missing_after_merge`: Required field missing from both STDIN and CLI → exit 45.

**GREEN** — Implement deferred required logic: set `required=False` at Click level when STDIN is active, validate after merge via `jsonschema.validate()`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_schema_parser.py -v`

---

## Exit Criteria
- All 7 tasks complete with passing tests.
- JSON Schema properties correctly map to Click options with types, defaults, help text.
- Boolean flag pairs and enum choices work correctly.
- `$ref` resolution handles circular refs, depth limits, and composition keywords.
- STDIN + CLI required field interaction is correct.
