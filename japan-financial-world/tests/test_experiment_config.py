"""
Tests for the v1.8 experiment harness (``world/experiment.py``).

The harness loads + validates a config, calls the existing
reference demo, and writes a manifest + ledger digest. These tests
verify the schema contract (required fields, types, defaults,
synthetic-only guard) and the end-to-end equivalence with the
bundled demo's known digest.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from world.experiment import (
    CONFIG_SCHEMA_VERSION,
    ExperimentConfig,
    ExperimentConfigError,
    _config_from_mapping,
    load_experiment_config,
    run_reference_experiment,
    validate_experiment_config,
)


_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEMO_DIR = _REPO_ROOT / "examples" / "reference_world"
_BASE_CONFIG_PATH = _DEMO_DIR / "configs" / "base.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_valid_raw(tmp_path: Path) -> dict:
    """Smallest legal config dict with all required fields filled."""
    return {
        "run_id": "fwe_reference_demo_test_run",
        "run_label": "FWE Reference Demo — test run",
        "start_date": "2026-01-01",
        "days": 2,
        "execution_mode": "date_tick",
        "input_entities_path": "examples/reference_world/entities.yaml",
        "output_dir": str(tmp_path),
        "manifest_enabled": True,
        "replay_digest_enabled": True,
    }


# ---------------------------------------------------------------------------
# load: base config
# ---------------------------------------------------------------------------


def test_load_base_config_succeeds():
    config = load_experiment_config(_BASE_CONFIG_PATH)
    assert isinstance(config, ExperimentConfig)
    assert config.run_id == "fwe_reference_demo_base_2026_01_01"
    assert config.start_date == "2026-01-01"
    assert config.days == 2
    assert config.execution_mode == "date_tick"
    assert config.manifest_enabled is True
    assert config.replay_digest_enabled is True


def test_load_base_config_returns_immutable_dataclass():
    config = load_experiment_config(_BASE_CONFIG_PATH)
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.run_id = "tampered"  # type: ignore[misc]


def test_load_missing_file_raises_config_error(tmp_path: Path):
    missing = tmp_path / "does_not_exist.yaml"
    with pytest.raises(ExperimentConfigError) as exc:
        load_experiment_config(missing)
    assert "not found" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing_field",
    [
        "run_id",
        "run_label",
        "start_date",
        "days",
        "execution_mode",
        "input_entities_path",
        "output_dir",
        "manifest_enabled",
        "replay_digest_enabled",
    ],
)
def test_missing_required_field_raises_config_error(
    tmp_path: Path, missing_field: str
):
    raw = _minimal_valid_raw(tmp_path)
    del raw[missing_field]
    with pytest.raises(ExperimentConfigError) as exc:
        _config_from_mapping(raw)
    assert "missing required field" in str(exc.value).lower()
    assert missing_field in str(exc.value)


# ---------------------------------------------------------------------------
# Type / value validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name, bad_value",
    [
        ("run_id", ""),
        ("run_id", 42),
        ("run_label", ""),
        ("start_date", "2026/01/01"),  # wrong format
        ("start_date", "not-a-date"),
        ("days", 0),
        ("days", -1),
        ("days", "2"),  # string not int
        ("days", True),  # bool is rejected even though it's an int
        ("execution_mode", "foobar"),
        ("execution_mode", ""),
        ("manifest_enabled", "yes"),  # not a bool
        ("replay_digest_enabled", 1),  # not a bool
    ],
)
def test_invalid_field_value_raises_config_error(
    tmp_path: Path, field_name: str, bad_value
):
    raw = _minimal_valid_raw(tmp_path)
    raw[field_name] = bad_value
    with pytest.raises(ExperimentConfigError):
        _config_from_mapping(raw)


# ---------------------------------------------------------------------------
# Defaults applied for optional sections
# ---------------------------------------------------------------------------


def test_optional_sections_default_to_empty_tuples(tmp_path: Path):
    raw = _minimal_valid_raw(tmp_path)
    # No optional sections at all in `raw`.
    config = _config_from_mapping(raw)
    assert config.external_observations == ()
    assert config.signal_templates == ()
    assert config.valuation_templates == ()
    assert config.institutional_actions == ()
    assert config.event_delivery_targets == ()


def test_optional_section_explicit_null_treated_as_empty(tmp_path: Path):
    raw = _minimal_valid_raw(tmp_path)
    raw["external_observations"] = None
    raw["signal_templates"] = None
    config = _config_from_mapping(raw)
    assert config.external_observations == ()
    assert config.signal_templates == ()


def test_optional_section_must_be_list_of_mappings(tmp_path: Path):
    raw = _minimal_valid_raw(tmp_path)
    raw["external_observations"] = ["not-a-mapping"]
    with pytest.raises(ExperimentConfigError) as exc:
        _config_from_mapping(raw)
    assert "external_observations" in str(exc.value)


# ---------------------------------------------------------------------------
# Synthetic-only guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name, value_with_token",
    [
        ("run_id", "fwe_demo_with_toyota_in_id"),
        ("run_label", "Demo using BoJ data"),
        ("input_entities_path", "examples/jpx_listings.yaml"),
        ("output_dir", "build/mufg_stress_run"),
    ],
)
def test_synthetic_only_guard_rejects_forbidden_tokens(
    tmp_path: Path, field_name: str, value_with_token: str
):
    raw = _minimal_valid_raw(tmp_path)
    raw[field_name] = value_with_token
    with pytest.raises(ExperimentConfigError) as exc:
        _config_from_mapping(raw)
    assert "forbidden token" in str(exc.value).lower()


def test_synthetic_only_guard_walks_optional_sections(tmp_path: Path):
    raw = _minimal_valid_raw(tmp_path)
    raw["external_observations"] = [
        {"process_id": "process:reference_macro_index"},
        # Hidden inside an optional section:
        {"process_id": "process:gpif_alloc"},
    ]
    with pytest.raises(ExperimentConfigError) as exc:
        _config_from_mapping(raw)
    assert "forbidden token" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# validate_experiment_config: same checks for code-built configs
# ---------------------------------------------------------------------------


def test_validate_runs_synthetic_check_on_code_built_config(tmp_path: Path):
    cfg = ExperimentConfig(
        run_id="fwe_demo_with_smbc_in_label",
        run_label="ok",
        start_date="2026-01-01",
        days=2,
        execution_mode="date_tick",
        input_entities_path="examples/reference_world/entities.yaml",
        output_dir=str(tmp_path),
        manifest_enabled=True,
        replay_digest_enabled=True,
    )
    with pytest.raises(ExperimentConfigError):
        validate_experiment_config(cfg)


def test_validate_rejects_non_config_arg():
    with pytest.raises(ExperimentConfigError):
        validate_experiment_config({"not": "a config"})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# run_reference_experiment: digest equivalence with the demo
# ---------------------------------------------------------------------------


def _load_replay_module():
    sibling = _DEMO_DIR / "replay_utils.py"
    spec = importlib.util.spec_from_file_location(
        "fwe_reference_replay_utils_for_exp", sibling
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_demo_module():
    sibling = _DEMO_DIR / "run_reference_loop.py"
    spec = importlib.util.spec_from_file_location(
        "fwe_reference_demo_run_for_exp", sibling
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_run_with_base_config_produces_same_digest_as_demo(tmp_path: Path):
    """
    Running the base config through the harness must produce the
    same canonical SHA-256 ledger digest as calling the bundled
    demo directly. This is the v1.8 equivalence guarantee.
    """
    config = load_experiment_config(_BASE_CONFIG_PATH)
    config = dataclasses.replace(config, output_dir=str(tmp_path))

    result = run_reference_experiment(config)

    demo = _load_demo_module()
    replay = _load_replay_module()
    direct_kernel, _ = demo.run()
    direct_digest = replay.ledger_digest(direct_kernel)

    assert result.ledger_digest == direct_digest


def test_run_writes_manifest_and_digest_when_enabled(tmp_path: Path):
    config = load_experiment_config(_BASE_CONFIG_PATH)
    config = dataclasses.replace(config, output_dir=str(tmp_path))

    result = run_reference_experiment(config)

    assert result.manifest_path is not None
    assert result.manifest_path.is_file()
    assert result.digest_path is not None
    assert result.digest_path.is_file()

    # Manifest carries the experiment-level metadata (run_id /
    # run_label / config_used) on top of the demo manifest fields.
    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["run_type"] == "fwe_reference_demo"
    assert manifest["experiment"]["run_id"] == config.run_id
    assert manifest["experiment"]["run_label"] == config.run_label
    assert (
        manifest["experiment"]["config_schema_version"]
        == CONFIG_SCHEMA_VERSION
    )
    assert manifest["ledger_digest"] == result.ledger_digest

    # Digest file is just the hex digest + a trailing newline.
    digest_text = result.digest_path.read_text()
    assert digest_text.strip() == result.ledger_digest
    assert digest_text.endswith("\n")


def test_run_skips_manifest_and_digest_when_disabled(tmp_path: Path):
    config = load_experiment_config(_BASE_CONFIG_PATH)
    config = dataclasses.replace(
        config,
        output_dir=str(tmp_path),
        manifest_enabled=False,
        replay_digest_enabled=False,
    )
    result = run_reference_experiment(config)

    assert result.manifest_path is None
    assert result.digest_path is None
    assert result.ledger_digest is None
    # Output dir should not contain a manifest.json from this run.
    assert not (tmp_path / "manifest.json").exists()
    assert not (tmp_path / "ledger_digest.txt").exists()


# ---------------------------------------------------------------------------
# Unimplemented-override boundaries
# ---------------------------------------------------------------------------


def test_run_with_custom_entities_path_raises_not_implemented(
    tmp_path: Path,
):
    custom = tmp_path / "custom_entities.yaml"
    custom.write_text("# placeholder\n", encoding="utf-8")
    raw = _minimal_valid_raw(tmp_path)
    raw["input_entities_path"] = str(custom)
    config = _config_from_mapping(raw)

    with pytest.raises(NotImplementedError) as exc:
        run_reference_experiment(config)
    assert "v1.8.x" in str(exc.value)


def test_run_with_custom_days_raises_not_implemented(tmp_path: Path):
    raw = _minimal_valid_raw(tmp_path)
    raw["days"] = 5
    config = _config_from_mapping(raw)
    with pytest.raises(NotImplementedError):
        run_reference_experiment(config)


def test_run_with_intraday_phase_mode_raises_not_implemented(
    tmp_path: Path,
):
    raw = _minimal_valid_raw(tmp_path)
    raw["execution_mode"] = "intraday_phase"
    config = _config_from_mapping(raw)
    with pytest.raises(NotImplementedError) as exc:
        run_reference_experiment(config)
    assert "intraday_phase" in str(exc.value)


def test_run_with_nonempty_optional_section_raises_not_implemented(
    tmp_path: Path,
):
    raw = _minimal_valid_raw(tmp_path)
    raw["external_observations"] = [
        {"process_id": "process:reference_macro_index"},
    ]
    config = _config_from_mapping(raw)
    with pytest.raises(NotImplementedError) as exc:
        run_reference_experiment(config)
    assert "external_observations" in str(exc.value)


# ---------------------------------------------------------------------------
# No simulation behavior change
# ---------------------------------------------------------------------------


def test_running_harness_does_not_change_demo_behavior(tmp_path: Path):
    """
    The harness reads from the kernel and writes only to output_dir.
    Two demo runs (one direct, one through the harness) must produce
    the same ledger digest — the v1.8 equivalence guarantee, asserted
    here as a regression check that the harness has zero side effects
    on the simulation itself.
    """
    config = load_experiment_config(_BASE_CONFIG_PATH)
    config = dataclasses.replace(config, output_dir=str(tmp_path))

    demo = _load_demo_module()
    replay = _load_replay_module()

    # Direct run BEFORE the harness.
    direct_kernel_a, _ = demo.run()
    digest_before = replay.ledger_digest(direct_kernel_a)

    # Harness run.
    result = run_reference_experiment(config)
    assert result.ledger_digest == digest_before

    # Direct run AFTER the harness.
    direct_kernel_b, _ = demo.run()
    digest_after = replay.ledger_digest(direct_kernel_b)
    assert digest_after == digest_before, (
        "harness must not perturb subsequent demo runs"
    )
