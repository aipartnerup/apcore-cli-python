# Implementation Plan: Security Manager

**Priority**: P1 (Auth, Encryption, Audit) / P2 (Sandbox)
**Source Spec**: `../apcore-cli/docs/features/security.md`
**Module Paths**: `apcore_cli/security/__init__.py`, `auth.py`, `config_encryptor.py`, `audit.py`, `sandbox.py`
**Dependencies**: Config Resolver

---

## Tasks

### Task 1: AuthProvider — API key resolution and request authentication
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_security/test_auth.py`:
  - `test_get_api_key_from_env`: `APCORE_AUTH_API_KEY=abc123` → returns `"abc123"`.
  - `test_get_api_key_none`: No key configured → returns `None`.
  - `test_get_api_key_keyring_ref`: Config value `keyring:auth.api_key` → decrypted via encryptor.
  - `test_authenticate_request_adds_header`: Key available → `Authorization: Bearer abc123` added.
  - `test_authenticate_request_no_key_raises`: No key → `AuthenticationError`.
  - `test_handle_response_401`: Status 401 → `AuthenticationError`.
  - `test_handle_response_403`: Status 403 → `AuthenticationError`.
  - `test_handle_response_200`: Status 200 → no error.

**GREEN** — Implement `AuthProvider` class in `security/auth.py`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_security/test_auth.py -v`

---

### Task 2: ConfigEncryptor — keyring and AES-256-GCM
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_security/test_config_encryptor.py`:
  - `test_store_with_keyring`: Keyring available → returns `keyring:key` reference.
  - `test_store_without_keyring`: Keyring unavailable → returns `enc:base64...` value.
  - `test_retrieve_keyring_ref`: `keyring:auth.api_key` → value from keyring.
  - `test_retrieve_enc_ref`: `enc:base64...` → decrypted value.
  - `test_retrieve_plaintext`: Plain string → returned as-is.
  - `test_retrieve_keyring_not_found`: Key missing from keyring → `ConfigDecryptionError`.
  - `test_retrieve_corrupted_ciphertext`: Invalid ciphertext → `ConfigDecryptionError`.
  - `test_aes_roundtrip`: Encrypt then decrypt → same plaintext.
  - `test_keyring_available_fail_backend`: Fail keyring backend → returns `False`.

**GREEN** — Implement `ConfigEncryptor` class with `store()`, `retrieve()`, `_keyring_available()`, `_derive_key()`, `_aes_encrypt()`, `_aes_decrypt()`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_security/test_config_encryptor.py -v`

---

### Task 3: AuditLogger — JSON Lines logging
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_security/test_audit.py`:
  - `test_log_execution_success`: Log success entry → JSONL file contains entry with correct fields.
  - `test_log_execution_error`: Log error entry → `status: "error"`, correct exit code.
  - `test_log_creates_directory`: Parent dir doesn't exist → created automatically.
  - `test_log_input_hash`: Same input → same SHA-256 hash. Different input → different hash.
  - `test_log_write_failure_warns`: Unwritable path → WARNING logged, no exception raised.
  - `test_get_user_fallback`: `os.getlogin()` fails → falls back to `USER` env var.
  - `test_log_entry_format`: Entry has timestamp, user, module_id, input_hash, status, exit_code, duration_ms.

**GREEN** — Implement `AuditLogger` class with `log_execution()`, `_get_user()`, `_ensure_directory()`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_security/test_audit.py -v`

---

### Task 4: Sandbox — subprocess isolation
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_security/test_sandbox.py`:
  - `test_sandbox_disabled_direct_execution`: `enabled=False` → calls `executor.call()` directly.
  - `test_sandbox_enabled_subprocess`: `enabled=True` → runs in subprocess with restricted env.
  - `test_sandbox_restricted_env`: Only allowed env vars present (`PATH`, `PYTHONPATH`, `LANG`, `APCORE_*`).
  - `test_sandbox_home_is_tempdir`: `HOME` env var is temp directory.
  - `test_sandbox_subprocess_failure`: Subprocess returns non-zero → `ModuleExecutionError`.
  - `test_sandbox_timeout`: Subprocess exceeds 300s → timeout error.
  - `test_sandbox_result_parsing`: Subprocess stdout is valid JSON → parsed and returned.

**GREEN** — Implement `Sandbox` class with `execute()` and `_sandboxed_execute()`. Create `apcore_cli/_sandbox_runner.py`.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_security/test_sandbox.py -v`

---

### Task 5: Security package integration
**Status**: pending
**Type**: RED-GREEN-REFACTOR

**RED** — Write failing tests:
- `tests/test_security/test_init.py`:
  - `test_exports`: `from apcore_cli.security import AuthProvider, ConfigEncryptor, AuditLogger, Sandbox` → all importable.
  - `test_integration_exec_with_audit`: Module execution → audit log entry written.
  - `test_integration_sandbox_flag`: `--sandbox` flag → Sandbox enabled.

**GREEN** — Implement `security/__init__.py` with exports. Wire audit logging into exec callback. Wire sandbox into exec flow.

**REFACTOR** — None expected.

**Verification**: `pytest tests/test_security/ -v`

---

## Exit Criteria
- All 5 tasks complete with passing tests.
- API key auth works with keyring and AES-256-GCM fallback.
- Audit logging writes JSONL entries with input hashing.
- Sandbox runs modules in isolated subprocess with restricted environment.
- All security components integrated into the CLI exec flow.
