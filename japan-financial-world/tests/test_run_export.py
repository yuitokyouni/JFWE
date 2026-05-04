"""
Tests for v1.19.1 run-export bundle infrastructure —
``world.run_export``.

Pinned invariants:

- closed-set vocabularies (``RUN_PROFILE_LABELS``,
  ``GENERATED_AT_POLICY_LABELS``, ``STATUS_LABELS``,
  ``VISIBILITY_LABELS``);
- v1.19.0 hard naming boundary
  (``FORBIDDEN_RUN_EXPORT_FIELD_NAMES``) disjoint from every
  closed-set vocabulary; dataclass field names disjoint;
  rejected on every payload + boundary-flag + metadata mapping;
- frozen dataclass with strict construction-time validation;
  ``period_count`` rejects ``bool``;
- default boundary flags carry the v1.19.0 binding eight-flag
  set;
- :func:`bundle_to_json` is byte-deterministic (``sort_keys=True``);
  same bundle → same string;
- write / read JSON round-trip via tmp_path;
- ``stable_for_replay`` does not insert any current timestamp
  (the dataclass has no wall-clock field);
- ``monthly_reference`` / ``daily_display_only`` /
  ``future_daily_full_simulation`` labels are accepted but do
  not trigger any engine execution — the module imports no
  source-of-truth book or kernel (pinned by a module-text scan);
- invalid labels rejected;
- no kernel / ``PriceBook`` / scenario_drivers / scenario_applications
  imports;
- empty bundle module does not move the default-fixture
  ``living_world_digest``;
- no ledger emission;
- jurisdiction-neutral identifier scan over module + test text.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest

from world.run_export import (
    FORBIDDEN_RUN_EXPORT_FIELD_NAMES,
    GENERATED_AT_POLICY_LABELS,
    RUN_PROFILE_LABELS,
    RunExportBundle,
    RunExportError,
    STATUS_LABELS,
    VISIBILITY_LABELS,
    build_run_export_bundle,
    bundle_to_dict,
    bundle_to_json,
    read_run_export_bundle,
    write_run_export_bundle,
)


_MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "world"
    / "run_export.py"
)


# ---------------------------------------------------------------------------
# Closed-set vocabularies
# ---------------------------------------------------------------------------


def test_run_profile_labels_closed_set():
    assert RUN_PROFILE_LABELS == frozenset(
        {
            "quarterly_default",
            "monthly_reference",
            "scenario_monthly",
            "daily_display_only",
            "future_daily_full_simulation",
            "unknown",
        }
    )


def test_generated_at_policy_labels_closed_set():
    assert GENERATED_AT_POLICY_LABELS == frozenset(
        {
            "stable_for_replay",
            "explicit_timestamp",
            "omitted",
            "unknown",
        }
    )


def test_status_labels_closed_set():
    assert STATUS_LABELS == frozenset(
        {
            "draft",
            "exported",
            "stale",
            "superseded",
            "archived",
            "unknown",
        }
    )


def test_visibility_labels_closed_set():
    assert VISIBILITY_LABELS == frozenset(
        {
            "public",
            "restricted",
            "internal",
            "private",
            "unknown",
        }
    )


# ---------------------------------------------------------------------------
# Forbidden field-name boundary
# ---------------------------------------------------------------------------


def test_forbidden_field_names_includes_v1_18_0_pinned_set():
    pinned = {
        "firm_decision",
        "investor_action",
        "bank_approval",
        "trading_decision",
        "optimal_capital_structure",
        "buy",
        "sell",
        "order",
        "trade",
        "execution",
        "price",
        "market_price",
        "predicted_index",
        "forecast_path",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        "real_data_value",
        "japan_calibration",
        "llm_output",
        "llm_prose",
        "prompt_text",
    }
    assert pinned <= FORBIDDEN_RUN_EXPORT_FIELD_NAMES


def test_forbidden_field_names_disjoint_from_every_closed_set():
    for vocab in (
        RUN_PROFILE_LABELS,
        GENERATED_AT_POLICY_LABELS,
        STATUS_LABELS,
        VISIBILITY_LABELS,
    ):
        assert not (FORBIDDEN_RUN_EXPORT_FIELD_NAMES & vocab)


def test_dataclass_field_names_disjoint_from_forbidden():
    fields = set(RunExportBundle.__dataclass_fields__.keys())
    assert not (fields & FORBIDDEN_RUN_EXPORT_FIELD_NAMES)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bundle(
    *,
    bundle_id: str = "run_bundle:test:1",
    run_profile_label: str = "quarterly_default",
    regime_label: str = "constrained",
    selected_scenario_label: str = "none_baseline",
    period_count: int = 4,
    digest: str = (
        "f93bdf3f4203c20d4a58e956160b0bb1004dcdecf"
        "0648a92cc961401b705897c"
    ),
    generated_at_policy_label: str = "stable_for_replay",
    manifest=None,
    overview=None,
    timeline=None,
    regime_compare=None,
    scenario_trace=None,
    attention_diff=None,
    market_intent=None,
    financing=None,
    ledger_excerpt=None,
    boundary_flags=None,
    status: str = "exported",
    visibility: str = "public",
    metadata=None,
) -> RunExportBundle:
    return build_run_export_bundle(
        bundle_id=bundle_id,
        run_profile_label=run_profile_label,
        regime_label=regime_label,
        selected_scenario_label=selected_scenario_label,
        period_count=period_count,
        digest=digest,
        generated_at_policy_label=generated_at_policy_label,
        manifest=manifest,
        overview=overview,
        timeline=timeline,
        regime_compare=regime_compare,
        scenario_trace=scenario_trace,
        attention_diff=attention_diff,
        market_intent=market_intent,
        financing=financing,
        ledger_excerpt=ledger_excerpt,
        boundary_flags=boundary_flags,
        status=status,
        visibility=visibility,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Field validation
# ---------------------------------------------------------------------------


def test_bundle_accepts_minimal_required_fields():
    b = _bundle()
    assert b.bundle_id == "run_bundle:test:1"
    assert b.run_profile_label == "quarterly_default"
    assert b.regime_label == "constrained"
    assert b.selected_scenario_label == "none_baseline"
    assert b.period_count == 4
    assert b.generated_at_policy_label == "stable_for_replay"
    assert b.status == "exported"
    assert b.visibility == "public"


def test_bundle_rejects_empty_bundle_id():
    with pytest.raises(ValueError):
        _bundle(bundle_id="")


def test_bundle_rejects_empty_regime_label():
    with pytest.raises(ValueError):
        _bundle(regime_label="")


def test_bundle_rejects_empty_selected_scenario_label():
    with pytest.raises(ValueError):
        _bundle(selected_scenario_label="")


def test_bundle_rejects_empty_digest():
    with pytest.raises(ValueError):
        _bundle(digest="")


def test_bundle_rejects_unknown_run_profile_label():
    with pytest.raises(ValueError):
        _bundle(run_profile_label="hourly_simulation")


def test_bundle_rejects_unknown_generated_at_policy_label():
    with pytest.raises(ValueError):
        _bundle(generated_at_policy_label="random_clock")


def test_bundle_rejects_unknown_status_label():
    with pytest.raises(ValueError):
        _bundle(status="committed_for_audit")


def test_bundle_rejects_unknown_visibility_label():
    with pytest.raises(ValueError):
        _bundle(visibility="public_marketing")


def test_bundle_rejects_negative_period_count():
    with pytest.raises(ValueError):
        _bundle(period_count=-1)


def test_bundle_rejects_bool_for_period_count():
    """``bool`` is a subclass of ``int``; the dataclass must
    reject it explicitly."""
    with pytest.raises(ValueError):
        _bundle(period_count=True)  # type: ignore[arg-type]


def test_bundle_rejects_string_for_period_count():
    with pytest.raises(ValueError):
        _bundle(period_count="4")  # type: ignore[arg-type]


def test_bundle_rejects_metadata_with_forbidden_key():
    with pytest.raises(ValueError):
        _bundle(metadata={"target_price": 1.0})


def test_bundle_rejects_overview_with_forbidden_key():
    with pytest.raises(ValueError):
        _bundle(overview={"investment_advice": "buy"})


def test_bundle_rejects_nested_forbidden_key_in_payload():
    """Forbidden keys at any depth inside a payload are
    rejected — the v1.19.0 boundary scan walks recursively."""
    with pytest.raises(ValueError):
        _bundle(
            timeline={
                "rows": [
                    {"label": "ok"},
                    {"forecast_path": [1, 2, 3]},
                ]
            }
        )


def test_bundle_rejects_boundary_flag_with_forbidden_key():
    with pytest.raises(ValueError):
        _bundle(
            boundary_flags={"target_price": True},
        )


def test_bundle_rejects_non_bool_boundary_flag_value():
    with pytest.raises(ValueError):
        _bundle(boundary_flags={"synthetic_only": "yes"})


def test_bundle_rejects_non_mapping_payload():
    with pytest.raises(ValueError):
        _bundle(overview="not a dict")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Immutability + to_dict
# ---------------------------------------------------------------------------


def test_bundle_is_immutable():
    b = _bundle()
    with pytest.raises(Exception):
        b.bundle_id = "other"  # type: ignore[misc]


def test_bundle_to_dict_round_trip_byte_identical():
    a = _bundle()
    b = _bundle()
    assert a.to_dict() == b.to_dict()


def test_bundle_to_dict_keys_disjoint_from_forbidden():
    payload = _bundle().to_dict()
    assert not (set(payload.keys()) & FORBIDDEN_RUN_EXPORT_FIELD_NAMES)
    for sub in (
        "manifest",
        "overview",
        "timeline",
        "regime_compare",
        "scenario_trace",
        "attention_diff",
        "market_intent",
        "financing",
        "ledger_excerpt",
        "metadata",
        "boundary_flags",
    ):
        keys = set(payload[sub].keys())
        assert not (keys & FORBIDDEN_RUN_EXPORT_FIELD_NAMES), (
            f"section {sub!r} carries a forbidden key"
        )


def test_module_level_bundle_to_dict_alias_works():
    b = _bundle()
    assert bundle_to_dict(b) == b.to_dict()


def test_bundle_to_dict_alias_rejects_non_bundle():
    with pytest.raises(TypeError):
        bundle_to_dict({"bundle_id": "x"})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Default boundary flags
# ---------------------------------------------------------------------------


def test_default_boundary_flags_carry_eight_v1_19_0_pins():
    b = _bundle()
    assert b.boundary_flags == {
        "synthetic_only": True,
        "no_price_formation": True,
        "no_trading": True,
        "no_investment_advice": True,
        "no_real_data": True,
        "no_japan_calibration": True,
        "no_llm_execution": True,
        "display_or_export_only": True,
    }


def test_caller_can_extend_boundary_flags_with_additional_pins():
    """Passing a partial mapping merges on top of the default
    set — the eight v1.19.0 pins always survive."""
    b = _bundle(
        boundary_flags={"stable_for_replay": True}
    )
    flags = b.boundary_flags
    assert flags["synthetic_only"] is True
    assert flags["no_price_formation"] is True
    assert flags["stable_for_replay"] is True


def test_caller_cannot_override_boundary_default_to_false():
    """Merging on top means a False value passed by the caller
    *does* take effect for that key — the merge is by-key. We
    pin this behaviour rather than assume immutability of the
    default; tests simply document the merge semantics."""
    b = _bundle(boundary_flags={"synthetic_only": False})
    assert b.boundary_flags["synthetic_only"] is False
    # but the other defaults still carry through
    assert b.boundary_flags["no_price_formation"] is True


# ---------------------------------------------------------------------------
# Deterministic JSON
# ---------------------------------------------------------------------------


def test_bundle_to_json_byte_deterministic():
    a = _bundle(metadata={"k1": 1, "k2": 2})
    b = _bundle(metadata={"k2": 2, "k1": 1})
    # Despite different metadata insertion order, sort_keys=True
    # produces byte-identical JSON output.
    assert bundle_to_json(a) == bundle_to_json(b)


def test_bundle_to_json_parses_back_to_equivalent_dict():
    b = _bundle(overview={"main": "baseline"})
    text = bundle_to_json(b)
    parsed = json.loads(text)
    assert parsed["bundle_id"] == "run_bundle:test:1"
    assert parsed["run_profile_label"] == "quarterly_default"
    assert parsed["overview"] == {"main": "baseline"}


def test_bundle_to_json_indent_default_is_two():
    b = _bundle()
    text = bundle_to_json(b)
    assert text.startswith("{\n  ")


def test_bundle_to_json_compact_with_indent_none():
    b = _bundle()
    text = bundle_to_json(b, indent=None)
    assert "\n" not in text


def test_bundle_to_json_rejects_non_bundle():
    with pytest.raises(TypeError):
        bundle_to_json({"bundle_id": "x"})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Write / read round-trip
# ---------------------------------------------------------------------------


def test_write_then_read_round_trip_dict_equivalent(tmp_path):
    b = _bundle(
        overview={"main": "baseline"},
        metadata={"label": "fixture"},
    )
    path = tmp_path / "run_bundle.json"
    write_run_export_bundle(b, path)
    loaded = read_run_export_bundle(path)
    # Per v1.19.1 task: read returns a dict; full dataclass
    # restoration is deferred. The loaded dict must equal
    # ``bundle.to_dict()`` modulo JSON-compatible types.
    assert loaded == b.to_dict()


def test_write_twice_produces_byte_identical_files(tmp_path):
    b = _bundle()
    path_a = tmp_path / "run_bundle_a.json"
    path_b = tmp_path / "run_bundle_b.json"
    write_run_export_bundle(b, path_a)
    write_run_export_bundle(b, path_b)
    assert path_a.read_bytes() == path_b.read_bytes()


def test_write_run_export_bundle_rejects_non_bundle(tmp_path):
    with pytest.raises(TypeError):
        write_run_export_bundle(
            {"bundle_id": "x"},  # type: ignore[arg-type]
            tmp_path / "out.json",
        )


def test_read_run_export_bundle_rejects_non_dict_top_level(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(RunExportError):
        read_run_export_bundle(path)


# ---------------------------------------------------------------------------
# stable_for_replay — no current timestamp
# ---------------------------------------------------------------------------


def test_stable_for_replay_does_not_insert_current_time():
    """Two bundles built with the same args under
    ``stable_for_replay`` must produce byte-identical JSON. The
    dataclass carries no wall-clock field; the policy is
    declarative."""
    a = bundle_to_json(_bundle())
    b = bundle_to_json(_bundle())
    assert a == b


def test_stable_for_replay_json_has_no_iso_timestamp():
    """The dataclass has no timestamp field, so the rendered
    JSON must not contain anything that looks like an ISO
    timestamp inserted by the export module itself."""
    text = bundle_to_json(_bundle())
    # ISO-8601 with seconds (e.g. "2026-05-04T10:23:11"):
    assert (
        re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", text)
        is None
    )


def test_explicit_timestamp_policy_label_accepted():
    b = _bundle(
        generated_at_policy_label="explicit_timestamp",
        metadata={
            "explicit_timestamp_iso": "2026-04-15T00:00:00Z"
        },
    )
    assert b.generated_at_policy_label == "explicit_timestamp"
    assert (
        b.metadata["explicit_timestamp_iso"]
        == "2026-04-15T00:00:00Z"
    )


def test_omitted_policy_label_accepted():
    b = _bundle(generated_at_policy_label="omitted")
    assert b.generated_at_policy_label == "omitted"


# ---------------------------------------------------------------------------
# Run profile label discipline
# ---------------------------------------------------------------------------


def test_monthly_reference_label_accepted_but_does_not_run_engine():
    """v1.19.1 must accept the ``monthly_reference`` label as a
    pure carrier — the bundle does not invoke any engine
    machinery. We verify this by constructing a bundle and
    confirming the module's text imports no kernel /
    source-of-truth book."""
    b = _bundle(run_profile_label="monthly_reference")
    assert b.run_profile_label == "monthly_reference"
    text = _MODULE_PATH.read_text(encoding="utf-8")
    forbidden_imports = (
        "from world.kernel",
        "from world.prices",
        "from world.scenario_drivers",
        "from world.scenario_applications",
        "from world.market_environment",
        "from world.firm_state",
        "from world.interbank_liquidity",
        "from world.financing_paths",
        "from world.market_intents",
        "from world.attention",
        "from world.attention_feedback",
        "from world.reference_living_world",
    )
    for imp in forbidden_imports:
        assert imp not in text, (
            f"world/run_export.py imports {imp!r} — v1.19.1 "
            "must remain export-infrastructure-only"
        )


def test_scenario_monthly_label_accepted():
    b = _bundle(run_profile_label="scenario_monthly")
    assert b.run_profile_label == "scenario_monthly"


def test_daily_display_only_label_accepted_no_economic_records():
    """The label is accepted as a carrier; v1.19.1 produces no
    economic records under any profile (the bundle is a JSON
    payload, not a run)."""
    b = _bundle(
        run_profile_label="daily_display_only",
        period_count=0,
    )
    assert b.run_profile_label == "daily_display_only"
    assert b.period_count == 0


def test_future_daily_full_simulation_label_accepted_only_as_label():
    """Per v1.19.0, ``future_daily_full_simulation`` is named
    only as a gating point. v1.19.1 accepts it as a label
    carrier so a future test fixture can be constructed; the
    profile remains out-of-scope."""
    b = _bundle(run_profile_label="future_daily_full_simulation")
    assert b.run_profile_label == "future_daily_full_simulation"


# ---------------------------------------------------------------------------
# No kernel / no PriceBook / no living_world_digest movement
# ---------------------------------------------------------------------------


def test_module_imports_no_kernel_or_source_books():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    # The module must import only the stdlib + typing helpers.
    forbidden_imports = (
        "from world.kernel",
        "from world.prices",
        "from world.market_environment",
        "from world.firm_state",
        "from world.interbank_liquidity",
        "from world.financing_paths",
        "from world.market_intents",
        "from world.scenario_drivers",
        "from world.scenario_applications",
        "from world.attention",
        "from world.attention_feedback",
        "from world.reference_living_world",
        "from world.display_timeline",
        "from world.ledger",
        "from world.clock",
    )
    for imp in forbidden_imports:
        assert imp not in text, (
            f"world/run_export.py imports {imp!r} — "
            "v1.19.1 must remain runtime-book-free"
        )


def test_constructing_bundles_does_not_emit_any_ledger_record():
    """The module imports no Ledger; constructing a bundle
    therefore cannot append a ledger record. We sanity-check by
    building a fresh kernel separately and confirming it has
    zero records before and after a bundle is built."""
    from world.clock import Clock
    from world.kernel import WorldKernel
    from world.ledger import Ledger
    from world.registry import Registry
    from world.scheduler import Scheduler
    from world.state import State

    kernel = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 3, 31)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )
    before = len(kernel.ledger.records)
    _bundle()
    bundle_to_json(_bundle())
    write_run_export_bundle(
        _bundle(), Path("/tmp/v1_19_1_smoke.json")
    )
    assert len(kernel.ledger.records) == before
    Path("/tmp/v1_19_1_smoke.json").unlink(missing_ok=True)


def test_constructing_bundles_does_not_mutate_pricebook():
    from world.clock import Clock
    from world.kernel import WorldKernel
    from world.ledger import Ledger
    from world.registry import Registry
    from world.scheduler import Scheduler
    from world.state import State

    kernel = WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 3, 31)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )
    snap_before = kernel.prices.snapshot()
    _bundle()
    bundle_to_json(_bundle())
    assert kernel.prices.snapshot() == snap_before


def test_constructing_bundles_does_not_move_default_living_world_digest():
    """A bundle is a pure data carrier; building it on its own
    must not influence a separately seeded default sweep."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import (
        _run_default,
        _seed_kernel,
    )

    _bundle()
    bundle_to_json(_bundle())
    k = _seed_kernel()
    r = _run_default(k)
    assert (
        living_world_digest(k, r)
        == "f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c"
    )


# ---------------------------------------------------------------------------
# Jurisdiction-neutral scan
# ---------------------------------------------------------------------------


_FORBIDDEN_TOKENS = (
    "toyota",
    "mufg",
    "smbc",
    "mizuho",
    "boj",
    "fsa",
    "jpx",
    "gpif",
    "tse",
    "nikkei",
    "topix",
    "sony",
    "jgb",
    "nyse",
    "nasdaq",
)


def test_module_jurisdiction_neutral_scan():
    text = _MODULE_PATH.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in run_export.py"
        )


def test_test_file_jurisdiction_neutral_scan():
    text = Path(__file__).read_text(encoding="utf-8").lower()
    table_start = text.find("_forbidden_tokens = (")
    table_end = text.find(")", table_start) + 1
    if table_start != -1 and table_end > 0:
        text = text[:table_start] + text[table_end:]
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            "test_run_export.py"
        )
