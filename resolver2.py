import re

def resolve_changelog():
    with open("CHANGELOG.md", "r") as f:
        src = f.read()
    
    new_block = """## [0.7.0] - 2026-04-15

### Changed

- **Dependency bump**: requires `apcore >= 0.18.0` (was `>= 0.17.1`). Aligns with upstream `apcore 0.18.0` and `apcore-toolkit 0.4.2` breaking changes.
- **`MAX_MODULE_ID_LENGTH` 128 → 192**: `validate_module_id()` and all references updated to the new 192-character limit introduced in `apcore 0.18.0` (`apcore.registry.registry.MAX_MODULE_ID_LENGTH`).
- **`describe-pipeline` renders `StrategyInfo`**: `executor.describe_pipeline(strategy)` now returns a `StrategyInfo` dataclass (`name`, `step_count`, `step_names`, `description`). `strategy.py` updated to use `StrategyInfo` fields; header line is `Pipeline: {info.name} ({info.step_count} steps)`. Falls back gracefully to the legacy `_resolve_strategy_name` path when `describe_pipeline` is unavailable.

### Added

- **`create_cli(app=...)` parameter**: `create_cli()` accepts an optional `app: APCore` unified client (introduced in `apcore 0.18.0`). `app` is mutually exclusive with `registry`/`executor` (raises `ValueError`). When `app` is provided, `registry` and `executor` are extracted from `app.registry` and `app.executor`. Filesystem discovery is skipped if `app.registry` already contains registered modules; otherwise normal discovery proceeds into `app.registry`.
- **FE-12: Module Exposure Filtering** — Declarative control over which discovered modules are exposed as CLI commands.
  - `ExposureFilter` class in `exposure.py` with `is_exposed(module_id)` and `filter_modules(ids)` methods.
  - Three modes: `all` (default), `include` (whitelist), `exclude` (blacklist) with glob-pattern matching.
  - `ExposureFilter.from_config(dict)` classmethod for loading from `apcore.yaml` `expose` section.
  - `create_cli(expose=...)` parameter accepting `dict` or `ExposureFilter` instance.
  - `list --exposure {exposed,hidden,all}` filter flag in discovery commands.
  - `GroupedModuleGroup._build_group_map()` integration: calls `ExposureFilter.is_exposed()` to filter command registration.
  - `ConfigResolver` gains `expose.*` config keys.
  - 4-tier config precedence: `CliConfig.expose` > `--expose-mode` CLI flag > env var > `apcore.yaml`.
  - Hidden modules remain invocable via `exec <module_id>`.
- New file: `exposure.py`."""

    src = re.sub(r'<<<<<<< HEAD\n.*?\n=======\n.*?\n>>>>>>> 53ee[\w]+', new_block, src, flags=re.DOTALL)
    with open("CHANGELOG.md", "w") as f:
        f.write(src)

resolve_changelog()
