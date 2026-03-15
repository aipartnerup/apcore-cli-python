# Implementation Plan: Shell Integration

**Priority**: P2
**Source Spec**: `../apcore-cli/docs/features/shell-integration.md`
**Module Path**: `apcore_cli/shell.py`
**Dependencies**: Core Dispatcher, Schema Parser

---

## Tasks

### Task 1: Bash completion script generation
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_shell.py`:
  - `test_bash_completion_contains_subcommands`: Script includes `exec`, `list`, `describe`, `completion`, `man`.
  - `test_bash_completion_has_complete_directive`: Script contains `complete -F _apcore_cli_completion apcore-cli`.
  - `test_bash_completion_valid_syntax`: Script passes `bash -n` syntax check.

**GREEN** — Implement `_generate_bash_completion()` with static subcommand completion and dynamic module ID completion.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_shell.py -v`

---

### Task 2: Zsh and Fish completion script generation
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_shell.py`:
  - `test_zsh_completion_contains_compdef`: Script contains `compdef`.
  - `test_zsh_completion_contains_subcommands`: Script includes CLI subcommands.
  - `test_fish_completion_contains_complete`: Script contains `complete -c apcore-cli`.
  - `test_fish_completion_contains_subcommands`: Script includes CLI subcommands.

**GREEN** — Implement `_generate_zsh_completion()` and `_generate_fish_completion()`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_shell.py -v`

---

### Task 3: completion command and CLI wiring
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_shell.py`:
  - `test_completion_bash`: `apcore-cli completion bash` → outputs Bash script. Exit 0.
  - `test_completion_zsh`: `apcore-cli completion zsh` → outputs Zsh script. Exit 0.
  - `test_completion_fish`: `apcore-cli completion fish` → outputs Fish script. Exit 0.
  - `test_completion_invalid_shell`: `apcore-cli completion invalid` → Click rejects. Exit 2.

**GREEN** — Implement `completion` Click command. Register as built-in.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_shell.py -v`

---

### Task 4: Man page generation
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_shell.py`:
  - `test_man_exec`: `apcore-cli man exec` → roff output with `.TH`, `.SH NAME`, `.SH SYNOPSIS`.
  - `test_man_list`: `apcore-cli man list` → roff output for list command.
  - `test_man_unknown_command`: `apcore-cli man nonexistent` → exit 2, stderr "Unknown command".
  - `test_man_contains_options`: Man page for `exec` includes option descriptions.
  - `test_man_contains_exit_codes`: Man page includes EXIT CODES section.

**GREEN** — Implement `man_cmd` Click command with roff document generation. Register as built-in.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_shell.py -v`

---

## Exit Criteria
- All 4 tasks complete with passing tests.
- `apcore-cli completion bash|zsh|fish` outputs valid shell completion scripts.
- `apcore-cli man <command>` outputs valid roff-formatted man pages.
- Both commands registered as built-in subcommands.
