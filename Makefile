.PHONY: test test-cov lint fmt fmt-check check clean

# Run all tests (no coverage; same as `pytest`).
test:
	pytest --tb=short -q

# Run tests with coverage report (D5-002 cross-SDK coverage wiring).
# Mirrors apcore-cli-rust `make coverage` and apcore-cli-typescript
# `pnpm run test:cov`. Configuration lives in pyproject.toml under
# [tool.coverage.*] (source, fail_under, show_missing).
test-cov:
	pytest --cov=apcore_cli --cov-report=term-missing --cov-report=html

# Lint with ruff.
lint:
	ruff check src tests

# Format code with ruff. Run after every code change (CLAUDE.md).
fmt:
	ruff format src tests

# Check formatting without writing.
fmt-check:
	ruff format --check src tests

# Pre-commit / pre-merge gate.
check: fmt-check lint test

clean:
	rm -rf .coverage htmlcov build dist *.egg-info .pytest_cache .ruff_cache
