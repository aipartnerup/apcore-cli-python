# Implementation Plans: apcore-cli-python

CLI adapter for the apcore module ecosystem — Python implementation.

---

## Features & Implementation Order

Features are listed in dependency-resolved implementation order. All features are **completed**.

| # | Feature | Priority | Plan | Status | Dependencies |
|---|---------|----------|------|--------|-------------|
| 1 | **Config Resolver** | P0 | [config-resolver.md](config-resolver.md) | Done | None (foundation) |
| 2 | **Core Dispatcher** | P0 | [core-dispatcher.md](core-dispatcher.md) | Done | Config Resolver |
| 3 | **Schema Parser** | P0 | [schema-parser.md](schema-parser.md) | Done | Core Dispatcher |
| 4 | **Output Formatter** | P1 | [output-formatter.md](output-formatter.md) | Done | Core Dispatcher |
| 5 | **Discovery** | P1 | [discovery.md](discovery.md) | Done | Core Dispatcher, Output Formatter |
| 6 | **Approval Gate** | P1 | [approval-gate.md](approval-gate.md) | Done | Schema Parser |
| 7 | **Security Manager** | P1 | [security-manager.md](security-manager.md) | Done | Config Resolver |
| 8 | **Shell Integration** | P2 | [shell-integration.md](shell-integration.md) | Done | Core Dispatcher, Schema Parser |

---

## Dependency Graph

```
Config Resolver (foundation)
  └── Core Dispatcher
        ├── Schema Parser
        │     └── Approval Gate
        ├── Output Formatter
        │     └── Discovery
        ├── Security Manager
        └── Shell Integration
```

---

## Architecture

```
src/apcore_cli/
├── __init__.py              # Package version
├── __main__.py              # CLI entry point, wiring
├── cli.py                   # LazyModuleGroup, build_module_command, collect_input
├── config.py                # ConfigResolver (4-tier precedence)
├── schema_parser.py         # JSON Schema → Click options
├── ref_resolver.py          # $ref / allOf / anyOf / oneOf resolution
├── output.py                # TTY-adaptive output formatting (rich)
├── discovery.py             # list / describe commands
├── approval.py              # HITL approval gate with timeout
├── shell.py                 # bash/zsh/fish completion + man pages
├── _sandbox_runner.py       # Subprocess entry point for sandboxed execution
└── security/
    ├── __init__.py           # Exports
    ├── auth.py               # API key authentication
    ├── config_encryptor.py   # Keyring + AES-256-GCM fallback
    ├── audit.py              # JSON Lines audit logging
    └── sandbox.py            # Subprocess-based execution isolation
```

---

## Source Specifications

All feature specs originate from `../apcore-cli/docs/`:

| Document | Path |
|----------|------|
| Tech Design | `../apcore-cli/docs/apcore-cli/tech-design.md` |
| SRS | `../apcore-cli/docs/apcore-cli/srs.md` |
| Project Manifest | `../apcore-cli/docs/project-apcore-cli.md` |
| Feature Specs | `../apcore-cli/docs/features/*.md` |

---

## Test Coverage

| Layer | Tests | What it covers |
|-------|-------|----------------|
| Unit | 180 | Individual functions, classes, edge cases |
| Integration | 16 | Feature wiring, mock registry + real CLI pipeline |
| End-to-end | 37 | Real apcore modules, STDIN piping, subprocess invocation |
| Bugfix regression | 11 | `--extensions-dir` flag, Pydantic schema, audit cleanup |
| **Total** | **244** | |
