# Implementation Plan: Approval Gate

**Priority**: P1
**Source Spec**: `../apcore-cli/docs/features/approval-gate.md`
**Module Path**: `apcore_cli/approval.py`
**Dependencies**: Schema Parser

---

## Tasks

### Task 1: check_approval — bypass and skip logic
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_approval.py`:
  - `test_no_annotations_skips`: Module with no annotations → returns immediately.
  - `test_annotations_not_dict_skips`: Annotations is not a dict → returns immediately.
  - `test_requires_approval_false_skips`: `requires_approval: false` → returns immediately.
  - `test_requires_approval_string_true_skips`: `requires_approval: "true"` (string, not bool) → returns immediately.
  - `test_bypass_yes_flag`: `auto_approve=True` → returns immediately, INFO logged.
  - `test_bypass_env_var`: `APCORE_CLI_AUTO_APPROVE=1` → returns immediately, INFO logged.
  - `test_env_var_not_one_warns`: `APCORE_CLI_AUTO_APPROVE=true` → WARNING logged, NOT bypassed.
  - `test_yes_flag_priority_over_env`: Both `--yes` and env var set → `--yes` logged as bypass source.

**GREEN** — Implement `check_approval(module_def, auto_approve, ctx)` with bypass logic.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_approval.py -v`

---

### Task 2: Non-TTY rejection
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_approval.py`:
  - `test_non_tty_no_bypass_exits_46`: Non-TTY, no bypass → exit 46 with help message.
  - `test_non_tty_with_yes_flag_proceeds`: Non-TTY, `--yes` flag → proceeds (bypass takes priority).

**GREEN** — Implement non-TTY detection (`sys.stdin.isatty()`) and exit logic.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_approval.py -v`

---

### Task 3: TTY prompt with timeout
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_approval.py`:
  - `test_tty_user_approves`: Mock `click.confirm` returns True → proceeds, INFO logged.
  - `test_tty_user_denies`: Mock `click.confirm` returns False → exit 46, "Approval denied."
  - `test_tty_timeout`: Mock timeout → exit 46, "timed out after 60 seconds."
  - `test_custom_approval_message`: Module with `approval_message` annotation → custom message displayed.
  - `test_default_approval_message`: No `approval_message` → default message displayed.

**GREEN** — Implement `_prompt_with_timeout(module_def, timeout=60)` with SIGALRM (Unix).

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_approval.py -v`

---

### Task 4: ApprovalTimeoutError and integration
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_approval.py`:
  - `test_approval_timeout_error_is_exception`: `ApprovalTimeoutError` inherits from `Exception`.
  - `test_integration_exec_with_approval`: Full exec flow with approval-required module, user approves → execution proceeds.
  - `test_integration_exec_with_denial`: Full exec flow, user denies → exit 46.

**GREEN** — Implement `ApprovalTimeoutError` custom exception. Wire `check_approval` into the exec callback in `build_module_command`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_approval.py -v`

---

## Exit Criteria
- All 4 tasks complete with passing tests.
- Approval gate correctly checks `annotations.requires_approval` (strict boolean).
- Bypass via `--yes` and `APCORE_CLI_AUTO_APPROVE=1` works with correct priority.
- Non-TTY environments get proper error message with bypass instructions.
- TTY prompts have 60s timeout with SIGALRM.
