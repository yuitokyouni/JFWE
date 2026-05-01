"""
Regression test for the FWE Reference Demo catalog shape.

The CI environment that ships v1.7-public-rc1 + the experiment
harness exposed a shape mismatch: ``world.loader.load_yaml_file_raw``
falls back to a small custom YAML parser when PyYAML is not
installed, and that fallback cannot represent a top-level mapping
value. ``examples/reference_world/entities.yaml`` has a
``loop:`` block whose value is a mapping of run parameters; the
fallback parser silently misreads it as a list of empty dicts,
which causes the demo to crash with
``TypeError: list indices must be integers or slices, not str``
at ``run_reference_loop.py:261``.

The fix is to declare PyYAML as a runtime dependency in
``pyproject.toml``. This test is the regression guardrail: it
asserts that the catalog the demo loads is a Mapping with all the
keys the runner reads. If a future environment again falls back to
the custom parser (or breaks the YAML for any reason), this test
fails loudly with a precise error rather than the demo crashing
mid-loop.

The intended public schema is **a single canonical shape: a
top-level mapping**. The codebase deliberately does not support
both a list and a mapping form; the runner reads ``catalog["loop"]``
as a mapping and there is no compatibility code path for a list.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Mapping


_DEMO_DIR = (
    Path(__file__).resolve().parents[1] / "examples" / "reference_world"
)
_ENTITIES_PATH = _DEMO_DIR / "entities.yaml"


def _load_demo_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "fwe_reference_demo_run_for_catalog_shape",
        _DEMO_DIR / "run_reference_loop.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# Keys ``run_reference_loop.run()`` reads from ``catalog["loop"]``.
# Keep this list in sync with the actual reads in that file; the
# test fails loudly if any key is missing from the catalog.
_REQUIRED_LOOP_KEYS: tuple[str, ...] = (
    "as_of_date",
    "observation_phase_id",
    "signal_id_observation",
    "observed_factor",
    "valuation_id",
    "valuation_subject_id",
    "valuer_id",
    "valuation_method",
    "valuation_estimated_value",
    "valuation_currency",
    "action_id",
    "action_institution_id",
    "action_type",
    "action_phase_id",
    "signal_id_followup",
    "event_id",
    "event_source_space",
    "event_target_spaces",
)


def _load_catalog() -> dict:
    from world.loader import load_yaml_file_raw

    catalog = load_yaml_file_raw(_ENTITIES_PATH)
    assert isinstance(catalog, Mapping), (
        f"entities.yaml root must be a mapping; got {type(catalog).__name__}. "
        "If this fails, the YAML parser is misreading the file — most "
        "likely PyYAML is not installed and the loader fell back to its "
        "limited custom parser. PyYAML is declared as a runtime "
        "dependency in pyproject.toml; install it via "
        "`pip install -e .[dev]` from the repo root."
    )
    return dict(catalog)


# ---------------------------------------------------------------------------
# Top-level catalog shape
# ---------------------------------------------------------------------------


def test_catalog_root_is_a_mapping():
    catalog = _load_catalog()
    assert isinstance(catalog, Mapping)


def test_catalog_has_required_top_level_keys():
    catalog = _load_catalog()
    required_top_level = (
        "firms",
        "banks",
        "investors",
        "exchanges",
        "real_estate_markets",
        "information_sources",
        "policy_authorities",
        "institutions",
        "external_factors",
        "seed_prices",
        "seed_ownership",
        "loop",
    )
    missing = [k for k in required_top_level if k not in catalog]
    assert missing == [], (
        f"entities.yaml is missing top-level keys: {missing}"
    )


# ---------------------------------------------------------------------------
# loop section: must be a mapping with all required keys
# ---------------------------------------------------------------------------


def test_catalog_loop_is_a_mapping():
    """
    The intended schema for ``loop:`` is a single mapping. If this
    test fails with ``loop`` typed as a list, the YAML parser has
    misread the file — see this module's docstring.
    """
    catalog = _load_catalog()
    loop_cfg = catalog["loop"]
    assert isinstance(loop_cfg, Mapping), (
        f"catalog['loop'] must be a Mapping; got {type(loop_cfg).__name__}. "
        f"This is the v1.7-public-rc1+ CI failure mode. PyYAML must be "
        f"installed for the demo to run."
    )


def test_catalog_loop_has_all_required_keys():
    catalog = _load_catalog()
    loop_cfg = catalog["loop"]
    assert isinstance(loop_cfg, Mapping)
    missing = [k for k in _REQUIRED_LOOP_KEYS if k not in loop_cfg]
    assert missing == [], (
        f"catalog['loop'] is missing required keys: {missing}"
    )


def test_catalog_loop_event_target_spaces_is_a_list_of_strings():
    catalog = _load_catalog()
    targets = catalog["loop"]["event_target_spaces"]
    assert isinstance(targets, list)
    assert targets, "event_target_spaces must not be empty"
    for t in targets:
        assert isinstance(t, str), (
            f"event_target_spaces entries must be strings; got {t!r}"
        )


def test_catalog_loop_scalar_values_are_strings_or_numbers():
    """
    Spot-check: every loop key the runner reads as a plain scalar
    must round-trip as a string (or number for valuation_estimated_value).
    Catches the case where a parser inserts ``{}`` placeholders.
    """
    catalog = _load_catalog()
    loop_cfg = catalog["loop"]
    string_fields = (
        "as_of_date",
        "observation_phase_id",
        "signal_id_observation",
        "observed_factor",
        "valuation_id",
        "valuation_subject_id",
        "valuer_id",
        "valuation_method",
        "valuation_currency",
        "action_id",
        "action_institution_id",
        "action_type",
        "action_phase_id",
        "signal_id_followup",
        "event_id",
        "event_source_space",
    )
    for field in string_fields:
        value = loop_cfg[field]
        assert isinstance(value, str) and value, (
            f"loop[{field!r}] must be a non-empty string; got {value!r}"
        )

    estimated = loop_cfg["valuation_estimated_value"]
    assert isinstance(estimated, (int, float)) and not isinstance(estimated, bool), (
        f"loop['valuation_estimated_value'] must be numeric; got "
        f"{type(estimated).__name__}"
    )


# ---------------------------------------------------------------------------
# external_factors[0] shape (also read directly by the runner)
# ---------------------------------------------------------------------------


def test_catalog_external_factors_is_nonempty_list_of_mappings():
    catalog = _load_catalog()
    factors = catalog["external_factors"]
    assert isinstance(factors, list)
    assert factors, "external_factors must not be empty"
    for entry in factors:
        assert isinstance(entry, Mapping)
        # The runner reads catalog["external_factors"][0]["process_id"].
        assert "process_id" in entry
        assert isinstance(entry["process_id"], str)


# ---------------------------------------------------------------------------
# End-to-end: the demo's run() must succeed once the catalog loads
# correctly. This test is what would have caught the CI failure.
# ---------------------------------------------------------------------------


def test_demo_run_succeeds_with_current_catalog():
    """
    Exercise the full demo from a fresh module load. Any catalog-
    shape regression that causes ``run()`` to raise will be reported
    here with the original traceback, matching the CI failure mode.
    """
    demo = _load_demo_module()
    kernel, summary = demo.run()
    assert kernel is not None
    assert summary is not None
    assert summary.setup_record_count > 0
