"""FE-13 cross-language conformance fixture tests (T-APCLI-31).

All fixtures (``create_cli.json`` / ``env.json`` / ``input.yaml`` /
``expected_help.txt``) live in the spec repo at
``../apcore-cli/conformance/fixtures/apcli-visibility/<scenario>/`` and are
shared across every SDK (TypeScript, Python, Rust). Each SDK is responsible
for making its underlying help renderer (Commander.js / Click / clap) emit
the canonical clap-style format — see the spec repo's
``conformance/fixtures/apcli-visibility/README.md`` for the format rules.

Shared files use ``snake_case`` keys; the Python loader maps them to
``create_cli`` kwargs at the test boundary.

Behavioral assertions (apcli group visibility, registered subcommands)
run today — they verify that the Python SDK resolves the FE-13 4-tier
decision chain identically to the TypeScript reference implementation.
Byte-matching against ``expected_help.txt`` is marked ``xfail`` until
the canonical help formatter (tracked alongside
``src/canonical-help.ts`` in the TypeScript SDK) is ported to Click.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import click
import pytest
from click.testing import CliRunner

from apcore_cli.factory import create_cli

# ---------------------------------------------------------------------------
# Fixture location — matches the TS test's APCORE_CLI_SPEC_REPO convention.
# ---------------------------------------------------------------------------

_DEFAULT_SPEC_REPO = Path(__file__).resolve().parents[3] / "apcore-cli"
SPEC_REPO_ROOT = Path(os.environ.get("APCORE_CLI_SPEC_REPO", str(_DEFAULT_SPEC_REPO)))
FIXTURE_ROOT = SPEC_REPO_ROOT / "conformance" / "fixtures" / "apcli-visibility"


def _discover_scenarios() -> list[str]:
    if not FIXTURE_ROOT.is_dir():
        return []
    return sorted(p.name for p in FIXTURE_ROOT.iterdir() if p.is_dir() and (p / "create_cli.json").is_file())


SCENARIOS = _discover_scenarios()


# ---------------------------------------------------------------------------
# Registry / executor stubs for embedded scenarios.
#
# The help path never executes modules, so these stubs only need to satisfy
# create_cli's construction-time checks. `list()` returns an empty set so the
# apcli group has no module-derived subcommands to render.
# ---------------------------------------------------------------------------


def _mock_registry() -> Any:
    registry = MagicMock()
    registry.list.return_value = []
    registry.get_definition.return_value = None
    return registry


def _mock_executor() -> Any:
    executor = MagicMock()
    # Force the system-cmd probe to return False (matches an integrator who
    # hasn't registered system.* modules).
    executor.validate.side_effect = RuntimeError("system modules not available")
    return executor


# ---------------------------------------------------------------------------
# Per-scenario harness
# ---------------------------------------------------------------------------


def _load_scenario(scenario: str) -> dict[str, Any]:
    """Read the four fixture files for ``scenario``."""
    d = FIXTURE_ROOT / scenario
    shared = json.loads((d / "create_cli.json").read_text(encoding="utf-8"))
    env = json.loads((d / "env.json").read_text(encoding="utf-8"))
    yaml_path = d / "input.yaml"
    expected_help = (d / "expected_help.txt").read_text(encoding="utf-8")
    return {
        "shared": shared,
        "env": env,
        "yaml_text": yaml_path.read_text(encoding="utf-8") if yaml_path.is_file() else None,
        "expected_help": expected_help,
    }


def _build_cli(shared: dict[str, Any], ext_dir: Path) -> click.Group:
    """Build a Click Group mirroring the TS ``createCli(opts)`` shape.

    Standalone scenarios (``registry_injected=False``) run filesystem
    discovery; point it at an empty directory so construction succeeds
    without registering any modules.
    """
    kwargs: dict[str, Any] = {"prog_name": shared["prog_name"]}
    if shared.get("registry_injected"):
        kwargs["registry"] = _mock_registry()
        kwargs["executor"] = _mock_executor()
    else:
        kwargs["extensions_dir"] = str(ext_dir)
    if "apcli" in shared:
        kwargs["apcli"] = shared["apcli"]
    return create_cli(**kwargs)


def _scenario_context(
    scenario: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> dict[str, Any]:
    """Materialize a scenario: chdir, env overlay, yaml, and the built CLI.

    Click writes no state outside what ``create_cli`` captures at build
    time, so the env/cwd overlay can be torn down by ``monkeypatch`` /
    ``tmp_path`` once the scenario object is constructed.
    """
    data = _load_scenario(scenario)

    # Always clear APCORE_CLI_APCLI for deterministic isolation, mirroring
    # the TS loader's behavior.
    monkeypatch.delenv("APCORE_CLI_APCLI", raising=False)

    for k, v in data["env"].items():
        monkeypatch.setenv(k, v)

    if data["yaml_text"] is not None:
        (tmp_path / "apcore.yaml").write_text(data["yaml_text"], encoding="utf-8")
    ext_dir = tmp_path / "extensions"
    ext_dir.mkdir(exist_ok=True)
    monkeypatch.chdir(tmp_path)

    cli = _build_cli(data["shared"], ext_dir)
    return {"data": data, "cli": cli, "shared": data["shared"]}


def _capture_help(cli: click.Group, prog_name: str) -> str:
    """Render ``<prog> --help`` through Click, stripped of trailing blanks."""
    result = CliRunner().invoke(cli, ["--help"], prog_name=prog_name)
    assert result.exit_code == 0, f"--help exited {result.exit_code}: {result.output}"
    return result.output


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not SCENARIOS,
    reason=(
        f"conformance fixtures not found at {FIXTURE_ROOT}. "
        "Checkout the spec repo (aipartnerup/apcore-cli) as a sibling "
        "directory or set APCORE_CLI_SPEC_REPO."
    ),
)


@pytest.mark.parametrize("scenario", SCENARIOS)
class TestApcliVisibilityConformance:
    """Cross-language conformance for the FE-13 decision chain."""

    def test_group_visibility_matches_expected_help(
        self,
        scenario: str,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """apcli group visibility must match whether ``apcli`` appears in the
        expected help's Commands section — this is the behavioral contract
        that drives the golden output and can be asserted independently of
        the help renderer's formatting."""
        ctx = _scenario_context(scenario, monkeypatch, tmp_path)
        cli: click.Group = ctx["cli"]
        apcli_cmd = cli.commands.get("apcli")
        assert apcli_cmd is not None, "apcli group must always be registered"

        expected_help: str = ctx["data"]["expected_help"]
        # Extract the Commands section — use the canonical-format header,
        # which every fixture uses regardless of SDK.
        commands_section = expected_help.split("Commands:", 1)[-1]
        # Stop at the Options section so we don't pick up options named
        # after subcommands.
        commands_section = commands_section.split("Options:", 1)[0]
        expected_apcli_visible = any(
            line.lstrip().startswith("apcli ") or line.lstrip() == "apcli" or line.lstrip().startswith("apcli\t")
            for line in commands_section.splitlines()
        )
        assert apcli_cmd.hidden is (not expected_apcli_visible), (
            f"[{scenario}] apcli group visibility mismatch: "
            f"hidden={apcli_cmd.hidden}, expected visible={expected_apcli_visible}"
        )

    def test_apcli_subcommand_registration_matches_fixture(
        self,
        scenario: str,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Include/exclude fixtures must produce the right subcommand set.

        The canonical ``exec`` subcommand is always registered (spec §4.9),
        so we spot-check that include-filtered subcommands are honored.
        """
        ctx = _scenario_context(scenario, monkeypatch, tmp_path)
        cli: click.Group = ctx["cli"]
        apcli_cmd = cli.commands["apcli"]
        assert isinstance(apcli_cmd, click.Group)
        registered = set(apcli_cmd.commands.keys())
        # exec is always registered per spec §4.9.
        assert "exec" in registered, f"[{scenario}] 'exec' must always be registered; got {sorted(registered)}"

        shared: dict[str, Any] = ctx["shared"]
        yaml_text: str | None = ctx["data"]["yaml_text"]
        apcli_opt = shared.get("apcli")
        yaml_include_list: list[str] | None = None
        if isinstance(apcli_opt, dict) and apcli_opt.get("mode") == "include":
            yaml_include_list = list(apcli_opt.get("include", []))
        elif yaml_text and "mode: include" in yaml_text:
            # Parse the include list out of the yaml fixture.
            import yaml as _yaml  # type: ignore[import-untyped]

            parsed = _yaml.safe_load(yaml_text) or {}
            apcli_block = parsed.get("apcli") if isinstance(parsed, dict) else None
            if isinstance(apcli_block, dict) and apcli_block.get("mode") == "include":
                yaml_include_list = list(apcli_block.get("include", []))

        if yaml_include_list is not None:
            for name in yaml_include_list:
                assert name in registered, f"[{scenario}] include list requires '{name}'; got {sorted(registered)}"
            # Subcommands outside the include list (other than exec) must be
            # absent.
            allowed = set(yaml_include_list) | {"exec"}
            stray = registered - allowed
            assert not stray, f"[{scenario}] include-mode leaked subcommands: {sorted(stray)}"

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "Canonical clap-style help format not yet implemented in the "
            "Python SDK. Tracked for parity with "
            "apcore-cli-typescript/src/canonical-help.ts. Fixture loader, "
            "env/yaml overlay, and scenario discovery are in place — the "
            "byte-match will flip to green once Click's HelpFormatter is "
            "replaced with a canonical-format emitter."
        ),
    )
    def test_help_matches_golden(
        self,
        scenario: str,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Byte-match ``<prog> --help`` against the canonical fixture."""
        ctx = _scenario_context(scenario, monkeypatch, tmp_path)
        cli: click.Group = ctx["cli"]
        shared: dict[str, Any] = ctx["shared"]
        actual = _capture_help(cli, shared["prog_name"])
        assert actual == ctx["data"]["expected_help"]


# ---------------------------------------------------------------------------
# Golden regeneration — disabled by default.
#
# The golden is a cross-language contract, not a local snapshot. Setting
# ``APCLI_FIXTURE_UPDATE=1`` regenerates the goldens in the spec repo from
# the Python renderer's current output — intended only for iterating on
# the canonical format during development. Flip this off before CI runs.
# ---------------------------------------------------------------------------


def _maybe_regenerate_goldens() -> None:  # pragma: no cover — developer-only
    if os.environ.get("APCLI_FIXTURE_UPDATE") != "1":
        return
    if not shutil.which("python"):
        return
    for scenario in SCENARIOS:
        # Regeneration mirrors the test path but writes the renderer's
        # actual output back into the spec repo's golden file.
        # Kept intentionally minimal — golden curation is a human task.
        data = _load_scenario(scenario)
        shared = data["shared"]
        import tempfile as _tempfile

        with _tempfile.TemporaryDirectory() as _ext:
            cli = _build_cli(shared, Path(_ext))
            actual = _capture_help(cli, shared["prog_name"])
        (FIXTURE_ROOT / scenario / "expected_help.txt").write_text(actual, encoding="utf-8")


_maybe_regenerate_goldens()
