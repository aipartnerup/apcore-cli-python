# CLAUDE.md — apcore-cli-python

## Build & Test

- `pytest` — run all tests. **Must pass before considering any task complete.**
- `pytest --cov` — run with coverage report.
- `ruff check .` — lint check.
- `ruff format .` — format all code. **Run after every code change.**

## Code Style

- Python 3.11+ with `from __future__ import annotations`.
- All code must pass `ruff check` and `ruff format --check`.
- Type annotations on all public function signatures.
- Use `click.echo()` for user-facing output, `logger.*` for debug/diagnostic output.
- Prefer `sys.exit(code)` with exit code constants over raising exceptions for CLI errors.

## Project Conventions

- Spec repo (single source of truth): `../apcore-cli/docs/`
- Package structure: `src/apcore_cli/` with `__init__.py` exporting `__version__` only.
- Entry point: `apcore_cli.__main__:main`.
- Security modules live in `src/apcore_cli/security/` sub-package.
- ConfigResolver.DEFAULTS values are Python-typed (str, int, bool).
- Tests organized by module: `tests/test_<module>.py`, security tests in `tests/test_security/`.

## Environment

- Python >= 3.11
- Key dependencies: click >= 8.0, rich >= 13.0, jsonschema >= 4.0, pyyaml >= 6.0
