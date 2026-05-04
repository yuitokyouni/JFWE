"""
Tests for v1.18.1 ``ScenarioDriverTemplate`` storage —
``world.scenario_drivers`` module.

Pinned invariants:

- closed-set vocabularies (``SCENARIO_FAMILY_LABELS``,
  ``DRIVER_GROUP_LABELS``, ``EVENT_DATE_POLICY_LABELS``,
  ``SEVERITY_LABELS``, ``AFFECTED_ACTOR_SCOPE_LABELS``,
  ``EXPECTED_ANNOTATION_TYPE_LABELS``, ``REASONING_MODE_LABELS``,
  ``REASONING_SLOT_LABELS``, ``STATUS_LABELS``,
  ``VISIBILITY_LABELS``);
- v1.18.0 hard naming boundary (``FORBIDDEN_SCENARIO_FIELD_NAMES``)
  disjoint from every closed-set vocabulary; dataclass field
  names disjoint; payload keys disjoint;
- frozen dataclass with strict construction-time validation;
- duplicate template id rejected; duplicate emits no extra
  ledger record;
- unknown template id raises ``UnknownScenarioDriverTemplateError``;
- every list / filter method;
- snapshot determinism;
- ledger emits exactly one record per ``add_template`` call;
- kernel wiring (``WorldKernel.scenario_drivers``);
- adding a template does not mutate ``PriceBook`` or any other
  source-of-truth book;
- adding a template does not move the default-fixture
  ``living_world_digest``;
- no forbidden ledger event types or payload keys;
- reasoning_mode default is ``rule_based_fallback``;
- jurisdiction-neutral identifier scan over module + test text.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.registry import Registry
from world.scenario_drivers import (
    AFFECTED_ACTOR_SCOPE_LABELS,
    DEFAULT_REASONING_MODE,
    DEFAULT_REASONING_SLOT,
    DRIVER_GROUP_LABELS,
    DuplicateScenarioDriverTemplateError,
    EVENT_DATE_POLICY_LABELS,
    EXPECTED_ANNOTATION_TYPE_LABELS,
    FORBIDDEN_SCENARIO_FIELD_NAMES,
    REASONING_MODE_LABELS,
    REASONING_SLOT_LABELS,
    SCENARIO_FAMILY_LABELS,
    SEVERITY_LABELS,
    STATUS_LABELS,
    ScenarioDriverTemplate,
    ScenarioDriverTemplateBook,
    UnknownScenarioDriverTemplateError,
    VISIBILITY_LABELS,
)
from world.scheduler import Scheduler
from world.state import State


_MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "world"
    / "scenario_drivers.py"
)


# ---------------------------------------------------------------------------
# Closed-set vocabularies
# ---------------------------------------------------------------------------


def test_scenario_family_labels_closed_set():
    assert SCENARIO_FAMILY_LABELS == frozenset(
        {
            "rate_repricing_driver",
            "credit_tightening_driver",
            "funding_window_closure_driver",
            "liquidity_stress_driver",
            "risk_off_driver",
            "sector_demand_deterioration_driver",
            "market_access_reopening_driver",
            "refinancing_wall_driver",
            "input_cost_pressure_driver",
            "information_gap_driver",
            "regulatory_risk_driver",
            "litigation_risk_driver",
            "supply_constraint_driver",
            "customer_churn_driver",
            "technology_substitution_driver",
            "policy_subsidy_driver",
            "thematic_attention_driver",
            "short_squeeze_attention_driver",
            "index_inclusion_exclusion_driver",
            "capital_policy_uncertainty_driver",
            "unknown",
        }
    )


def test_driver_group_labels_closed_set():
    assert DRIVER_GROUP_LABELS == frozenset(
        {
            "macro_rates",
            "credit_liquidity",
            "demand_earnings",
            "cost_supply",
            "regulation_legal",
            "ownership_market_structure",
            "technology_competition",
            "capital_structure_refinancing",
            "information_attention",
            "unknown",
        }
    )


def test_event_date_policy_labels_closed_set():
    assert EVENT_DATE_POLICY_LABELS == frozenset(
        {
            "quarter_start",
            "quarter_end",
            "nearest_reporting_date",
            "explicit_date",
            "display_only_date",
            "unknown",
        }
    )


def test_severity_labels_closed_set():
    assert SEVERITY_LABELS == frozenset(
        {"low", "medium", "high", "stress", "unknown"}
    )


def test_affected_actor_scope_labels_closed_set():
    assert AFFECTED_ACTOR_SCOPE_LABELS == frozenset(
        {
            "market_wide",
            "all_actors",
            "firms_only",
            "investors_only",
            "banks_only",
            "selected_firms",
            "selected_investors",
            "selected_banks",
            "selected_securities",
            "unknown",
        }
    )


def test_expected_annotation_type_labels_closed_set():
    assert EXPECTED_ANNOTATION_TYPE_LABELS == frozenset(
        {
            "market_environment_change",
            "attention_shift",
            "market_pressure_change",
            "financing_constraint",
            "causal_checkpoint",
            "synthetic_event",
            "unknown",
        }
    )


def test_reasoning_mode_labels_closed_set():
    assert REASONING_MODE_LABELS == frozenset(
        {
            "rule_based_fallback",
            "future_llm_compatible",
            "external_policy_slot",
            "unknown",
        }
    )


def test_reasoning_slot_labels_closed_set():
    assert REASONING_SLOT_LABELS == frozenset(
        {
            "future_llm_compatible",
            "rule_based_only",
            "not_applicable",
            "unknown",
        }
    )


def test_status_labels_closed_set():
    assert STATUS_LABELS == frozenset(
        {"draft", "active", "stale", "superseded", "archived", "unknown"}
    )


def test_visibility_labels_closed_set():
    assert VISIBILITY_LABELS == frozenset(
        {"internal_only", "shared_internal", "external_audit"}
    )


# ---------------------------------------------------------------------------
# Forbidden field-name boundary (v1.18.0 binding)
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
    assert pinned <= FORBIDDEN_SCENARIO_FIELD_NAMES


def test_forbidden_field_names_disjoint_from_every_closed_set():
    """The hard naming boundary must not collide with any
    closed-set value the dataclass legitimately uses."""
    for vocab in (
        SCENARIO_FAMILY_LABELS,
        DRIVER_GROUP_LABELS,
        EVENT_DATE_POLICY_LABELS,
        SEVERITY_LABELS,
        AFFECTED_ACTOR_SCOPE_LABELS,
        EXPECTED_ANNOTATION_TYPE_LABELS,
        REASONING_MODE_LABELS,
        REASONING_SLOT_LABELS,
        STATUS_LABELS,
        VISIBILITY_LABELS,
    ):
        assert not (FORBIDDEN_SCENARIO_FIELD_NAMES & vocab)


def test_dataclass_field_names_disjoint_from_forbidden():
    fields = set(ScenarioDriverTemplate.__dataclass_fields__.keys())
    assert not (fields & FORBIDDEN_SCENARIO_FIELD_NAMES)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _template(
    *,
    scenario_driver_template_id: str = "scenario_driver:rate_repricing:reference:standard",
    scenario_family_label: str = "rate_repricing_driver",
    driver_group_label: str = "macro_rates",
    driver_label: str = "Synthetic rising-rate context shift",
    event_date_policy_label: str = "quarter_start",
    severity_label: str = "medium",
    affected_actor_scope_label: str = "market_wide",
    expected_annotation_type_label: str = "market_environment_change",
    affected_context_surface_labels: tuple[str, ...] = (
        "market_environment_state",
    ),
    affected_evidence_bucket_labels: tuple[str, ...] = (
        "market_environment_state",
    ),
    reasoning_mode: str | None = None,
    reasoning_slot: str | None = None,
    status: str = "active",
    visibility: str = "internal_only",
    metadata: dict | None = None,
) -> ScenarioDriverTemplate:
    kwargs = dict(
        scenario_driver_template_id=scenario_driver_template_id,
        scenario_family_label=scenario_family_label,
        driver_group_label=driver_group_label,
        driver_label=driver_label,
        event_date_policy_label=event_date_policy_label,
        severity_label=severity_label,
        affected_actor_scope_label=affected_actor_scope_label,
        expected_annotation_type_label=expected_annotation_type_label,
        affected_context_surface_labels=affected_context_surface_labels,
        affected_evidence_bucket_labels=affected_evidence_bucket_labels,
        status=status,
        visibility=visibility,
        metadata=metadata or {},
    )
    if reasoning_mode is not None:
        kwargs["reasoning_mode"] = reasoning_mode
    if reasoning_slot is not None:
        kwargs["reasoning_slot"] = reasoning_slot
    return ScenarioDriverTemplate(**kwargs)


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 3, 31)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


# ---------------------------------------------------------------------------
# Field validation
# ---------------------------------------------------------------------------


def test_template_accepts_minimal_required_fields():
    t = _template()
    assert t.scenario_driver_template_id == "scenario_driver:rate_repricing:reference:standard"
    assert t.reasoning_mode == "rule_based_fallback"
    assert t.reasoning_slot == "future_llm_compatible"
    assert t.status == "active"
    assert t.visibility == "internal_only"


def test_template_rejects_empty_scenario_driver_template_id():
    with pytest.raises(ValueError):
        _template(scenario_driver_template_id="")


def test_template_rejects_unknown_scenario_family_label():
    with pytest.raises(ValueError):
        _template(scenario_family_label="rogue_driver")


def test_template_rejects_unknown_driver_group_label():
    with pytest.raises(ValueError):
        _template(driver_group_label="custom_group")


def test_template_rejects_unknown_event_date_policy_label():
    with pytest.raises(ValueError):
        _template(event_date_policy_label="random_date")


def test_template_rejects_unknown_severity_label():
    with pytest.raises(ValueError):
        _template(severity_label="catastrophic")


def test_template_rejects_unknown_actor_scope_label():
    with pytest.raises(ValueError):
        _template(affected_actor_scope_label="every_actor")


def test_template_rejects_unknown_expected_annotation_type_label():
    with pytest.raises(ValueError):
        _template(expected_annotation_type_label="custom_event")


def test_template_rejects_unknown_reasoning_mode():
    with pytest.raises(ValueError):
        _template(reasoning_mode="learned_model_v3")


def test_template_rejects_unknown_reasoning_slot():
    with pytest.raises(ValueError):
        _template(reasoning_slot="custom_slot")


def test_template_rejects_unknown_status():
    with pytest.raises(ValueError):
        _template(status="committed")


def test_template_rejects_unknown_visibility():
    with pytest.raises(ValueError):
        _template(visibility="public_marketing")


def test_template_rejects_empty_string_in_context_surface_labels():
    with pytest.raises(ValueError):
        _template(affected_context_surface_labels=("market_environment_state", ""))


def test_template_rejects_metadata_with_forbidden_key():
    with pytest.raises(ValueError):
        _template(metadata={"buy": "this firm"})


def test_template_rejects_metadata_with_forbidden_target_price_key():
    with pytest.raises(ValueError):
        _template(metadata={"target_price": 1.0})


def test_template_rejects_metadata_with_forbidden_llm_prose_key():
    with pytest.raises(ValueError):
        _template(metadata={"llm_prose": "the bank should approve"})


# ---------------------------------------------------------------------------
# Default reasoning_mode
# ---------------------------------------------------------------------------


def test_default_reasoning_mode_is_rule_based_fallback():
    """v1.18.0 binding default; documented in the design note
    and the module-level constant."""
    assert DEFAULT_REASONING_MODE == "rule_based_fallback"
    assert DEFAULT_REASONING_SLOT == "future_llm_compatible"
    t = _template()
    assert t.reasoning_mode == "rule_based_fallback"
    assert t.reasoning_slot == "future_llm_compatible"


# ---------------------------------------------------------------------------
# Immutability + to_dict
# ---------------------------------------------------------------------------


def test_template_record_is_immutable():
    t = _template()
    with pytest.raises(Exception):
        t.scenario_driver_template_id = "other"  # type: ignore[misc]


def test_template_to_dict_round_trip_byte_identical():
    a = _template()
    b = _template()
    assert a.to_dict() == b.to_dict()


def test_template_to_dict_keys_disjoint_from_forbidden():
    payload = _template().to_dict()
    assert not (set(payload.keys()) & FORBIDDEN_SCENARIO_FIELD_NAMES)
    metadata_keys = set(payload["metadata"].keys())
    assert not (metadata_keys & FORBIDDEN_SCENARIO_FIELD_NAMES)


# ---------------------------------------------------------------------------
# ScenarioDriverTemplateBook — add / get / list / duplicate / unknown
# ---------------------------------------------------------------------------


def test_book_add_get_list_template():
    book = ScenarioDriverTemplateBook()
    t = _template()
    book.add_template(t)
    assert book.get_template(t.scenario_driver_template_id) is t
    assert book.list_templates() == (t,)


def test_book_duplicate_template_id_raises():
    book = ScenarioDriverTemplateBook()
    t = _template()
    book.add_template(t)
    with pytest.raises(DuplicateScenarioDriverTemplateError):
        book.add_template(t)


def test_book_unknown_template_id_raises():
    book = ScenarioDriverTemplateBook()
    with pytest.raises(UnknownScenarioDriverTemplateError):
        book.get_template("missing")


def test_book_list_by_family():
    book = ScenarioDriverTemplateBook()
    a = _template(
        scenario_driver_template_id="scenario_driver:rate:1",
        scenario_family_label="rate_repricing_driver",
        driver_group_label="macro_rates",
    )
    b = _template(
        scenario_driver_template_id="scenario_driver:credit:1",
        scenario_family_label="credit_tightening_driver",
        driver_group_label="credit_liquidity",
    )
    book.add_template(a)
    book.add_template(b)
    assert book.list_by_family("rate_repricing_driver") == (a,)
    assert book.list_by_family("credit_tightening_driver") == (b,)
    assert book.list_by_family("liquidity_stress_driver") == ()


def test_book_list_by_group():
    book = ScenarioDriverTemplateBook()
    a = _template(
        scenario_driver_template_id="scenario_driver:macro:1",
        scenario_family_label="rate_repricing_driver",
        driver_group_label="macro_rates",
    )
    b = _template(
        scenario_driver_template_id="scenario_driver:liquidity:1",
        scenario_family_label="liquidity_stress_driver",
        driver_group_label="credit_liquidity",
    )
    book.add_template(a)
    book.add_template(b)
    assert book.list_by_group("macro_rates") == (a,)
    assert book.list_by_group("credit_liquidity") == (b,)


def test_book_list_by_severity():
    book = ScenarioDriverTemplateBook()
    a = _template(
        scenario_driver_template_id="scenario_driver:medium:1",
        severity_label="medium",
    )
    b = _template(
        scenario_driver_template_id="scenario_driver:stress:1",
        severity_label="stress",
    )
    book.add_template(a)
    book.add_template(b)
    assert book.list_by_severity("medium") == (a,)
    assert book.list_by_severity("stress") == (b,)


def test_book_list_by_actor_scope():
    book = ScenarioDriverTemplateBook()
    a = _template(
        scenario_driver_template_id="scenario_driver:wide:1",
        affected_actor_scope_label="market_wide",
    )
    b = _template(
        scenario_driver_template_id="scenario_driver:firm:1",
        affected_actor_scope_label="selected_firms",
    )
    book.add_template(a)
    book.add_template(b)
    assert book.list_by_actor_scope("market_wide") == (a,)
    assert book.list_by_actor_scope("selected_firms") == (b,)


def test_book_list_by_status():
    book = ScenarioDriverTemplateBook()
    a = _template(
        scenario_driver_template_id="scenario_driver:active:1",
        status="active",
    )
    b = _template(
        scenario_driver_template_id="scenario_driver:draft:1",
        status="draft",
    )
    book.add_template(a)
    book.add_template(b)
    assert book.list_by_status("active") == (a,)
    assert book.list_by_status("draft") == (b,)


def test_book_list_by_expected_annotation_type():
    book = ScenarioDriverTemplateBook()
    a = _template(
        scenario_driver_template_id="scenario_driver:env:1",
        expected_annotation_type_label="market_environment_change",
    )
    b = _template(
        scenario_driver_template_id="scenario_driver:attn:1",
        expected_annotation_type_label="attention_shift",
    )
    book.add_template(a)
    book.add_template(b)
    assert book.list_by_expected_annotation_type(
        "market_environment_change"
    ) == (a,)
    assert book.list_by_expected_annotation_type("attention_shift") == (b,)


def test_book_snapshot_deterministic():
    book = ScenarioDriverTemplateBook()
    book.add_template(_template())
    snap_a = book.snapshot()
    snap_b = book.snapshot()
    assert snap_a == snap_b
    assert "scenario_driver_templates" in snap_a
    assert len(snap_a["scenario_driver_templates"]) == 1


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_ledger_emits_exactly_one_record_per_add_template():
    kernel = _bare_kernel()
    before = len(kernel.ledger.records)
    kernel.scenario_drivers.add_template(_template())
    after = len(kernel.ledger.records)
    assert after - before == 1
    record = kernel.ledger.records[-1]
    assert record.record_type == RecordType.SCENARIO_DRIVER_TEMPLATE_RECORDED
    assert record.payload["scenario_driver_template_id"] == (
        "scenario_driver:rate_repricing:reference:standard"
    )
    assert record.payload["reasoning_mode"] == "rule_based_fallback"


def test_duplicate_template_emits_no_extra_ledger_record():
    kernel = _bare_kernel()
    kernel.scenario_drivers.add_template(_template())
    count_after_first = len(kernel.ledger.records)
    with pytest.raises(DuplicateScenarioDriverTemplateError):
        kernel.scenario_drivers.add_template(_template())
    assert len(kernel.ledger.records) == count_after_first


def test_ledger_payload_keys_disjoint_from_forbidden():
    kernel = _bare_kernel()
    kernel.scenario_drivers.add_template(_template())
    record = kernel.ledger.records[-1]
    assert not (set(record.payload.keys()) & FORBIDDEN_SCENARIO_FIELD_NAMES)


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_wires_scenario_drivers_book():
    kernel = _bare_kernel()
    assert isinstance(
        kernel.scenario_drivers, ScenarioDriverTemplateBook
    )
    assert kernel.scenario_drivers.ledger is kernel.ledger
    assert kernel.scenario_drivers.list_templates() == ()


# ---------------------------------------------------------------------------
# No-mutation invariants
# ---------------------------------------------------------------------------


def test_add_template_does_not_mutate_pricebook():
    kernel = _bare_kernel()
    snap_before = kernel.prices.snapshot()
    kernel.scenario_drivers.add_template(_template())
    snap_after = kernel.prices.snapshot()
    assert snap_before == snap_after


def test_empty_scenario_drivers_does_not_move_default_living_world_digest():
    """Wiring an empty ScenarioDriverTemplateBook into WorldKernel
    must leave the default-fixture ``living_world_digest``
    byte-identical to v1.17.last."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import _run_default, _seed_kernel

    k = _seed_kernel()
    r = _run_default(k)
    assert (
        living_world_digest(k, r)
        == "f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c"
    )


def test_add_template_does_not_create_actor_decision_event():
    kernel = _bare_kernel()
    kernel.scenario_drivers.add_template(_template())
    forbidden_event_names = {
        "order_submitted",
        "trade_executed",
        "price_updated",
        "quote_disseminated",
        "clearing_completed",
        "settlement_completed",
        "ownership_transferred",
        "loan_approved",
        "security_issued",
        "underwriting_executed",
    }
    seen = {rec.record_type.value for rec in kernel.ledger.records}
    assert not (seen & forbidden_event_names)


# ---------------------------------------------------------------------------
# Future-LLM-compatibility metadata accepted
# ---------------------------------------------------------------------------


def test_template_accepts_future_llm_compatible_reasoning_slot():
    t = _template(reasoning_slot="future_llm_compatible")
    assert t.reasoning_slot == "future_llm_compatible"


def test_template_accepts_external_policy_slot_reasoning_mode():
    t = _template(reasoning_mode="external_policy_slot")
    assert t.reasoning_mode == "external_policy_slot"


def test_template_accepts_reasoning_policy_id():
    t = _template()  # default policy id is set in dataclass
    assert t.reasoning_policy_id.startswith("v1.18.")


# ---------------------------------------------------------------------------
# Forbidden-name + jurisdiction-neutral scans
# ---------------------------------------------------------------------------


def test_module_text_does_not_carry_actor_decision_phrases():
    """Module text must not assert actor decisions. The
    forbidden field names are allowed inside the
    ``FORBIDDEN_SCENARIO_FIELD_NAMES`` literal at module scope
    (the closed-set definition itself); strip that literal then
    scan."""
    text = _MODULE_PATH.read_text(encoding="utf-8")
    open_idx = text.find(
        "FORBIDDEN_SCENARIO_FIELD_NAMES: frozenset[str] = frozenset("
    )
    close_idx = text.find(")", open_idx) if open_idx >= 0 else -1
    if open_idx >= 0 and close_idx > open_idx:
        text = text[:open_idx] + text[close_idx:]
    forbidden_phrases = (
        "firm_decision",
        "investor_action",
        "bank_approval",
        "trading_decision",
        "optimal_capital_structure",
        "predicted_index",
        "forecast_path",
        "expected_return",
        "target_price",
        "real_data_value",
        "japan_calibration",
        "llm_output",
        "llm_prose",
        "prompt_text",
    )
    for phrase in forbidden_phrases:
        assert phrase not in text, (
            f"forbidden phrase {phrase!r} appears in scenario_drivers.py "
            "outside the closed-set literal"
        )


_FORBIDDEN_TOKENS = (
    "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
    "gpif", "tse", "nikkei", "topix", "sony", "jgb", "nyse",
    "nasdaq",
)


def test_module_jurisdiction_neutral_scan():
    text = _MODULE_PATH.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in scenario_drivers.py"
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
            "test_scenario_drivers.py"
        )
