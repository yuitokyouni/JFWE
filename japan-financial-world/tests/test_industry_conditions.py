"""
Tests for v1.10.4 IndustryDemandConditionRecord +
IndustryConditionBook.

Covers field validation (including bounded synthetic numeric fields
``demand_strength`` and ``confidence`` and explicit bool rejection
matching the v1 ``world/exposures.py`` style), immutability,
``add_condition`` deduplication, unknown lookup, every list / filter
method, deterministic snapshots, ledger emission with the new
``RecordType.INDUSTRY_DEMAND_CONDITION_ADDED``, kernel wiring of the
new ``IndustryConditionBook``, the no-mutation guarantee against
every other v0/v1 source-of-truth book in the kernel, the v1.10.4
scope discipline (no demand forecast, no revenue forecast, no
financial-statement update, no action-class ledger record on
``add_condition``), plain-id cross-reference acceptance with prior
v1.10.x books (themes / dialogues / valuations / pressure signals
referenced from a corporate strategic response candidate), an
explicit anti-fields assertion that no ``forecast_value`` /
``revenue_forecast`` / ``sales_forecast`` / ``market_size`` /
``demand_index_value`` / ``vendor_consensus`` field exists on the
record or in the ledger payload, and a jurisdiction-neutral
identifier scan over both the new module and the test file.

Identifier and tag strings used in this test suite are
jurisdiction-neutral and synthetic; no Japan-specific institution
name, regulator, code, or threshold appears anywhere in the test
body.
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
from datetime import date

import pytest

from world.clock import Clock
from world.industry import (
    DuplicateIndustryConditionError,
    IndustryConditionBook,
    IndustryDemandConditionRecord,
    UnknownIndustryConditionError,
)
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _condition(
    *,
    condition_id: str = (
        "industry_condition:reference_manufacturing_general:2026Q1:001"
    ),
    industry_id: str = "industry:reference_manufacturing_general",
    industry_label: str = "reference manufacturing (synthetic)",
    as_of_date: str = "2026-03-01",
    condition_type: str = "demand_assessment",
    demand_direction: str = "stable",
    demand_strength: float = 0.5,
    time_horizon: str = "medium_term",
    confidence: float = 0.5,
    status: str = "active",
    visibility: str = "internal_only",
    related_variable_ids: tuple[str, ...] = (),
    related_signal_ids: tuple[str, ...] = (),
    related_exposure_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> IndustryDemandConditionRecord:
    return IndustryDemandConditionRecord(
        condition_id=condition_id,
        industry_id=industry_id,
        industry_label=industry_label,
        as_of_date=as_of_date,
        condition_type=condition_type,
        demand_direction=demand_direction,
        demand_strength=demand_strength,
        time_horizon=time_horizon,
        confidence=confidence,
        status=status,
        visibility=visibility,
        related_variable_ids=related_variable_ids,
        related_signal_ids=related_signal_ids,
        related_exposure_ids=related_exposure_ids,
        metadata=metadata or {},
    )


def _kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 1, 1)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


# ---------------------------------------------------------------------------
# Record — field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"condition_id": ""},
        {"industry_id": ""},
        {"industry_label": ""},
        {"as_of_date": ""},
        {"condition_type": ""},
        {"demand_direction": ""},
        {"time_horizon": ""},
        {"status": ""},
        {"visibility": ""},
    ],
)
def test_condition_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _condition(**kwargs)


@pytest.mark.parametrize(
    "tuple_field",
    [
        "related_variable_ids",
        "related_signal_ids",
        "related_exposure_ids",
    ],
)
def test_condition_rejects_empty_strings_in_tuple_fields(tuple_field):
    bad = {tuple_field: ("valid", "")}
    with pytest.raises(ValueError):
        _condition(**bad)


def test_condition_coerces_as_of_date_to_iso_string():
    c = _condition(as_of_date=date(2026, 3, 1))
    assert c.as_of_date == "2026-03-01"


def test_condition_rejects_non_date_as_of_date():
    with pytest.raises((TypeError, ValueError)):
        _condition(as_of_date=12345)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Bounded numeric fields — demand_strength and confidence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [-0.01, 1.01, -1.0, 1.5, 100.0])
def test_demand_strength_rejects_out_of_range(value):
    with pytest.raises(ValueError):
        _condition(demand_strength=value)


@pytest.mark.parametrize("value", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_demand_strength_accepts_in_range(value):
    c = _condition(demand_strength=value)
    assert c.demand_strength == float(value)


def test_demand_strength_rejects_bool_true():
    """Booleans are a subtype of int in Python; reject explicitly."""
    with pytest.raises(ValueError):
        _condition(demand_strength=True)  # type: ignore[arg-type]


def test_demand_strength_rejects_bool_false():
    with pytest.raises(ValueError):
        _condition(demand_strength=False)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["0.5", None, [0.5], {"x": 0.5}])
def test_demand_strength_rejects_non_numeric(value):
    with pytest.raises((TypeError, ValueError)):
        _condition(demand_strength=value)  # type: ignore[arg-type]


def test_demand_strength_int_is_accepted_and_coerced_to_float():
    c = _condition(demand_strength=1)
    assert isinstance(c.demand_strength, float)
    assert c.demand_strength == 1.0


@pytest.mark.parametrize("value", [-0.01, 1.01, -1.0, 1.5, 100.0])
def test_confidence_rejects_out_of_range(value):
    with pytest.raises(ValueError):
        _condition(confidence=value)


@pytest.mark.parametrize("value", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_confidence_accepts_in_range(value):
    c = _condition(confidence=value)
    assert c.confidence == float(value)


def test_confidence_rejects_bool_true():
    with pytest.raises(ValueError):
        _condition(confidence=True)  # type: ignore[arg-type]


def test_confidence_rejects_bool_false():
    with pytest.raises(ValueError):
        _condition(confidence=False)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["0.5", None, [0.5], {"x": 0.5}])
def test_confidence_rejects_non_numeric(value):
    with pytest.raises((TypeError, ValueError)):
        _condition(confidence=value)  # type: ignore[arg-type]


def test_confidence_int_is_accepted_and_coerced_to_float():
    c = _condition(confidence=0)
    assert isinstance(c.confidence, float)
    assert c.confidence == 0.0


# ---------------------------------------------------------------------------
# Immutability & round-trip
# ---------------------------------------------------------------------------


def test_condition_is_frozen():
    c = _condition()
    with pytest.raises(Exception):
        c.condition_id = "tampered"  # type: ignore[misc]


def test_condition_to_dict_round_trips_fields():
    c = _condition(
        related_variable_ids=("variable:reference_var_a",),
        related_signal_ids=("signal:reference_signal_a",),
        related_exposure_ids=("exposure:reference_exposure_a",),
        metadata={"note": "synthetic"},
    )
    out = c.to_dict()
    assert out["condition_id"] == c.condition_id
    assert out["industry_id"] == c.industry_id
    assert out["industry_label"] == c.industry_label
    assert out["as_of_date"] == c.as_of_date
    assert out["condition_type"] == c.condition_type
    assert out["demand_direction"] == c.demand_direction
    assert out["demand_strength"] == c.demand_strength
    assert out["time_horizon"] == c.time_horizon
    assert out["confidence"] == c.confidence
    assert out["status"] == c.status
    assert out["visibility"] == c.visibility
    assert out["related_variable_ids"] == ["variable:reference_var_a"]
    assert out["related_signal_ids"] == ["signal:reference_signal_a"]
    assert out["related_exposure_ids"] == ["exposure:reference_exposure_a"]
    assert out["metadata"] == {"note": "synthetic"}


def test_condition_metadata_is_independent_copy():
    src = {"note": "synthetic"}
    c = _condition(metadata=src)
    src["note"] = "tampered"
    assert c.metadata["note"] == "synthetic"


# ---------------------------------------------------------------------------
# Anti-fields — no forecast / revenue / market-size fields
# ---------------------------------------------------------------------------


def test_condition_record_has_no_forecast_or_revenue_field():
    """
    v1.10.4 industry condition record must store synthetic
    direction / strength / confidence triple plus generic labels —
    never a forecast value, revenue/sales forecast, market size,
    or vendor consensus number that could be confused with a real
    measurement or forecast.
    """
    field_names = {
        f.name for f in dataclass_fields(IndustryDemandConditionRecord)
    }
    forbidden = {
        "forecast_value",
        "revenue_forecast",
        "sales_forecast",
        "market_size",
        "demand_index_value",
        "vendor_consensus",
        "consensus_forecast",
        "real_data_value",
    }
    leaked = field_names & forbidden
    assert not leaked, (
        f"v1.10.4 industry condition must not carry forecast / "
        f"revenue / market-size fields; found: {sorted(leaked)}"
    )


# ---------------------------------------------------------------------------
# Book — add / get / dedup / unknown
# ---------------------------------------------------------------------------


def test_add_and_get_condition():
    book = IndustryConditionBook()
    c = _condition()
    book.add_condition(c)
    assert book.get_condition(c.condition_id) is c


def test_get_condition_unknown_raises():
    book = IndustryConditionBook()
    with pytest.raises(UnknownIndustryConditionError):
        book.get_condition("does-not-exist")


def test_unknown_industry_condition_error_is_keyerror():
    err = UnknownIndustryConditionError("missing")
    assert isinstance(err, KeyError)


def test_duplicate_condition_id_rejected():
    book = IndustryConditionBook()
    book.add_condition(_condition(condition_id="cond:dup"))
    with pytest.raises(DuplicateIndustryConditionError):
        book.add_condition(_condition(condition_id="cond:dup"))


def test_add_condition_returns_record():
    book = IndustryConditionBook()
    c = _condition()
    returned = book.add_condition(c)
    assert returned is c


# ---------------------------------------------------------------------------
# Listings & filters
# ---------------------------------------------------------------------------


def test_list_conditions_in_insertion_order():
    book = IndustryConditionBook()
    book.add_condition(_condition(condition_id="cond:a"))
    book.add_condition(_condition(condition_id="cond:b"))
    book.add_condition(_condition(condition_id="cond:c"))
    listed = book.list_conditions()
    assert tuple(c.condition_id for c in listed) == (
        "cond:a",
        "cond:b",
        "cond:c",
    )


def test_list_conditions_empty_book():
    assert IndustryConditionBook().list_conditions() == ()


def test_list_by_industry():
    book = IndustryConditionBook()
    book.add_condition(
        _condition(
            condition_id="cond:m",
            industry_id="industry:reference_manufacturing_general",
        )
    )
    book.add_condition(
        _condition(
            condition_id="cond:r",
            industry_id="industry:reference_retail_general",
        )
    )
    book.add_condition(
        _condition(
            condition_id="cond:m2",
            industry_id="industry:reference_manufacturing_general",
        )
    )
    matched = book.list_by_industry(
        "industry:reference_manufacturing_general"
    )
    assert tuple(c.condition_id for c in matched) == ("cond:m", "cond:m2")


def test_list_by_industry_no_match():
    book = IndustryConditionBook()
    book.add_condition(
        _condition(industry_id="industry:reference_manufacturing_general")
    )
    assert (
        book.list_by_industry("industry:reference_other_general") == ()
    )


def test_list_by_condition_type():
    book = IndustryConditionBook()
    book.add_condition(
        _condition(
            condition_id="cond:assess",
            condition_type="demand_assessment",
        )
    )
    book.add_condition(
        _condition(
            condition_id="cond:struct",
            condition_type="structural_demand_state",
        )
    )
    book.add_condition(
        _condition(
            condition_id="cond:assess2",
            condition_type="demand_assessment",
        )
    )
    matched = book.list_by_condition_type("demand_assessment")
    assert tuple(c.condition_id for c in matched) == (
        "cond:assess",
        "cond:assess2",
    )


def test_list_by_demand_direction():
    book = IndustryConditionBook()
    book.add_condition(
        _condition(
            condition_id="cond:exp", demand_direction="expanding"
        )
    )
    book.add_condition(
        _condition(condition_id="cond:stb", demand_direction="stable")
    )
    book.add_condition(
        _condition(
            condition_id="cond:con", demand_direction="contracting"
        )
    )
    book.add_condition(
        _condition(condition_id="cond:mix", demand_direction="mixed")
    )
    book.add_condition(
        _condition(condition_id="cond:unk", demand_direction="unknown")
    )
    assert tuple(
        c.condition_id for c in book.list_by_demand_direction("expanding")
    ) == ("cond:exp",)
    assert tuple(
        c.condition_id for c in book.list_by_demand_direction("stable")
    ) == ("cond:stb",)
    assert tuple(
        c.condition_id
        for c in book.list_by_demand_direction("contracting")
    ) == ("cond:con",)
    assert tuple(
        c.condition_id for c in book.list_by_demand_direction("mixed")
    ) == ("cond:mix",)
    assert tuple(
        c.condition_id for c in book.list_by_demand_direction("unknown")
    ) == ("cond:unk",)


def test_list_by_status():
    book = IndustryConditionBook()
    book.add_condition(
        _condition(condition_id="cond:draft", status="draft")
    )
    book.add_condition(
        _condition(condition_id="cond:active", status="active")
    )
    book.add_condition(
        _condition(condition_id="cond:retired", status="retired")
    )
    assert tuple(
        c.condition_id for c in book.list_by_status("active")
    ) == ("cond:active",)


def test_list_by_date_filters_exactly():
    book = IndustryConditionBook()
    book.add_condition(
        _condition(condition_id="cond:mar", as_of_date="2026-03-01")
    )
    book.add_condition(
        _condition(condition_id="cond:apr", as_of_date="2026-04-01")
    )
    book.add_condition(
        _condition(condition_id="cond:mar2", as_of_date="2026-03-01")
    )
    mar = book.list_by_date("2026-03-01")
    apr = book.list_by_date("2026-04-01")
    miss = book.list_by_date("2026-05-01")
    assert tuple(c.condition_id for c in mar) == ("cond:mar", "cond:mar2")
    assert tuple(c.condition_id for c in apr) == ("cond:apr",)
    assert miss == ()


def test_list_by_date_accepts_date_object():
    book = IndustryConditionBook()
    book.add_condition(
        _condition(condition_id="cond:mar", as_of_date="2026-03-01")
    )
    matched = book.list_by_date(date(2026, 3, 1))
    assert tuple(c.condition_id for c in matched) == ("cond:mar",)


# ---------------------------------------------------------------------------
# Plain-id cross-references — no validation against any other book
# ---------------------------------------------------------------------------


def test_condition_can_reference_unresolved_variable_signal_exposure_ids():
    book = IndustryConditionBook()
    c = _condition(
        related_variable_ids=("variable:not-in-variable-book",),
        related_signal_ids=("signal:not-in-signal-book",),
        related_exposure_ids=("exposure:not-in-exposure-book",),
    )
    book.add_condition(c)
    assert book.get_condition(c.condition_id) is c


def test_condition_id_can_be_referenced_from_corporate_response_candidate():
    """
    A v1.10.3 ``CorporateStrategicResponseCandidate`` must be able to
    cite an industry condition record's id at its
    ``trigger_signal_ids`` slot as a plain id, without v1.10.4
    forcing cross-book validation.
    """
    from world.strategic_response import (
        CorporateStrategicResponseCandidate,
        StrategicResponseCandidateBook,
    )

    book = IndustryConditionBook()
    c = _condition(condition_id="cond:cited")
    book.add_condition(c)

    response_book = StrategicResponseCandidateBook()
    response_book.add_candidate(
        CorporateStrategicResponseCandidate(
            response_candidate_id="resp:cites_industry_cond",
            company_id="firm:reference_manufacturer_a",
            as_of_date="2026-04-01",
            response_type="capital_allocation_review",
            status="draft",
            priority="medium",
            horizon="medium_term",
            expected_effect_label=(
                "expected_efficiency_improvement_candidate"
            ),
            constraint_label="subject_to_board_review",
            visibility="internal_only",
            trigger_signal_ids=("cond:cited",),
        )
    )
    listed = response_book.list_candidates()
    assert listed[0].trigger_signal_ids == ("cond:cited",)


# ---------------------------------------------------------------------------
# Snapshot determinism
# ---------------------------------------------------------------------------


def test_snapshot_is_deterministic_and_sorted():
    book = IndustryConditionBook()
    book.add_condition(_condition(condition_id="cond:z"))
    book.add_condition(_condition(condition_id="cond:a"))
    book.add_condition(_condition(condition_id="cond:m"))

    snap1 = book.snapshot()
    snap2 = book.snapshot()
    assert snap1 == snap2
    assert snap1["condition_count"] == 3
    assert [c["condition_id"] for c in snap1["conditions"]] == [
        "cond:a",
        "cond:m",
        "cond:z",
    ]


def test_snapshot_empty_book():
    snap = IndustryConditionBook().snapshot()
    assert snap == {"condition_count": 0, "conditions": []}


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_type_exists():
    assert (
        RecordType("industry_demand_condition_added")
        is RecordType.INDUSTRY_DEMAND_CONDITION_ADDED
    )
    assert (
        RecordType.INDUSTRY_DEMAND_CONDITION_ADDED.value
        == "industry_demand_condition_added"
    )


def test_add_condition_writes_exactly_one_ledger_record():
    ledger = Ledger()
    book = IndustryConditionBook(ledger=ledger)
    book.add_condition(_condition(condition_id="cond:emit"))
    records = ledger.filter(event_type="industry_demand_condition_added")
    assert len(records) == 1
    record = records[0]
    assert (
        record.record_type
        is RecordType.INDUSTRY_DEMAND_CONDITION_ADDED
    )
    assert record.object_id == "cond:emit"
    assert record.source == "industry:reference_manufacturing_general"
    assert record.space_id == "industry"
    assert record.visibility == "internal_only"
    assert record.confidence == 0.5


def test_add_condition_payload_carries_full_field_set():
    ledger = Ledger()
    book = IndustryConditionBook(ledger=ledger)
    book.add_condition(
        _condition(
            condition_id="cond:payload",
            related_variable_ids=("variable:reference_var_a",),
            related_signal_ids=("signal:reference_signal_a",),
            related_exposure_ids=("exposure:reference_exposure_a",),
        )
    )
    payload = ledger.filter(
        event_type="industry_demand_condition_added"
    )[-1].payload
    assert payload["condition_id"] == "cond:payload"
    assert (
        payload["industry_id"]
        == "industry:reference_manufacturing_general"
    )
    assert payload["industry_label"] == "reference manufacturing (synthetic)"
    assert payload["as_of_date"] == "2026-03-01"
    assert payload["condition_type"] == "demand_assessment"
    assert payload["demand_direction"] == "stable"
    assert payload["demand_strength"] == 0.5
    assert payload["time_horizon"] == "medium_term"
    assert payload["confidence"] == 0.5
    assert payload["status"] == "active"
    assert payload["visibility"] == "internal_only"
    assert tuple(payload["related_variable_ids"]) == (
        "variable:reference_var_a",
    )
    assert tuple(payload["related_signal_ids"]) == (
        "signal:reference_signal_a",
    )
    assert tuple(payload["related_exposure_ids"]) == (
        "exposure:reference_exposure_a",
    )


def test_add_condition_payload_carries_no_forecast_or_revenue_keys():
    ledger = Ledger()
    book = IndustryConditionBook(ledger=ledger)
    book.add_condition(_condition(condition_id="cond:audit"))
    payload_keys = set(
        ledger.filter(
            event_type="industry_demand_condition_added"
        )[-1].payload.keys()
    )
    forbidden = {
        "forecast_value",
        "revenue_forecast",
        "sales_forecast",
        "market_size",
        "demand_index_value",
        "vendor_consensus",
        "consensus_forecast",
        "real_data_value",
    }
    leaked = payload_keys & forbidden
    assert not leaked, (
        f"v1.10.4 industry condition payload must not carry forecast / "
        f"revenue / market-size keys; found: {sorted(leaked)}"
    )


def test_add_condition_without_ledger_does_not_raise():
    book = IndustryConditionBook()
    book.add_condition(_condition())


def test_duplicate_add_emits_no_extra_ledger_record():
    ledger = Ledger()
    book = IndustryConditionBook(ledger=ledger)
    book.add_condition(_condition(condition_id="cond:once"))
    with pytest.raises(DuplicateIndustryConditionError):
        book.add_condition(_condition(condition_id="cond:once"))
    assert (
        len(
            ledger.filter(event_type="industry_demand_condition_added")
        )
        == 1
    )


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_industry_conditions_book():
    kernel = _kernel()
    assert isinstance(kernel.industry_conditions, IndustryConditionBook)
    assert kernel.industry_conditions.ledger is kernel.ledger
    assert kernel.industry_conditions.clock is kernel.clock


def test_kernel_add_condition_emits_to_kernel_ledger():
    kernel = _kernel()
    kernel.industry_conditions.add_condition(_condition())
    records = kernel.ledger.filter(
        event_type="industry_demand_condition_added"
    )
    assert len(records) == 1


def test_kernel_industry_simulation_date_uses_clock():
    kernel = _kernel()
    kernel.industry_conditions.add_condition(
        _condition(condition_id="cond:wired")
    )
    records = kernel.ledger.filter(
        event_type="industry_demand_condition_added"
    )
    assert records[-1].simulation_date == "2026-01-01"


# ---------------------------------------------------------------------------
# No-mutation guarantee against every other source-of-truth book
# ---------------------------------------------------------------------------


def test_industry_conditions_book_does_not_mutate_other_kernel_books():
    kernel = _kernel()
    kernel.ownership.add_position("agent:alice", "asset:cash", 100)
    kernel.prices.set_price("asset:cash", 1.0, "2026-01-01", "exchange")

    snaps_before = {
        "ownership": kernel.ownership.snapshot(),
        "contracts": kernel.contracts.snapshot(),
        "prices": kernel.prices.snapshot(),
        "constraints": kernel.constraints.snapshot(),
        "signals": kernel.signals.snapshot(),
        "valuations": kernel.valuations.snapshot(),
        "institutions": kernel.institutions.snapshot(),
        "external_processes": kernel.external_processes.snapshot(),
        "relationships": kernel.relationships.snapshot(),
        "interactions": kernel.interactions.snapshot(),
        "routines": kernel.routines.snapshot(),
        "attention": kernel.attention.snapshot(),
        "variables": kernel.variables.snapshot(),
        "exposures": kernel.exposures.snapshot(),
        "stewardship": kernel.stewardship.snapshot(),
        "engagement": kernel.engagement.snapshot(),
        "escalations": kernel.escalations.snapshot(),
        "strategic_responses": kernel.strategic_responses.snapshot(),
    }

    kernel.industry_conditions.add_condition(
        _condition(
            condition_id="cond:k:a",
            related_variable_ids=("variable:reference_var_a",),
            related_signal_ids=("signal:reference_signal_a",),
            related_exposure_ids=("exposure:reference_exposure_a",),
        )
    )
    kernel.industry_conditions.add_condition(
        _condition(
            condition_id="cond:k:b",
            industry_id="industry:reference_retail_general",
            industry_label="reference retail (synthetic)",
            condition_type="structural_demand_state",
            demand_direction="contracting",
            demand_strength=0.7,
            confidence=0.8,
            status="under_review",
            visibility="public",
            as_of_date="2026-04-15",
        )
    )
    kernel.industry_conditions.list_conditions()
    kernel.industry_conditions.list_by_industry(
        "industry:reference_manufacturing_general"
    )
    kernel.industry_conditions.list_by_condition_type("demand_assessment")
    kernel.industry_conditions.list_by_demand_direction("stable")
    kernel.industry_conditions.list_by_status("active")
    kernel.industry_conditions.list_by_date("2026-03-01")
    kernel.industry_conditions.snapshot()

    assert kernel.ownership.snapshot() == snaps_before["ownership"]
    assert kernel.contracts.snapshot() == snaps_before["contracts"]
    assert kernel.prices.snapshot() == snaps_before["prices"]
    assert kernel.constraints.snapshot() == snaps_before["constraints"]
    assert kernel.signals.snapshot() == snaps_before["signals"]
    assert kernel.valuations.snapshot() == snaps_before["valuations"]
    assert kernel.institutions.snapshot() == snaps_before["institutions"]
    assert (
        kernel.external_processes.snapshot()
        == snaps_before["external_processes"]
    )
    assert kernel.relationships.snapshot() == snaps_before["relationships"]
    assert kernel.interactions.snapshot() == snaps_before["interactions"]
    assert kernel.routines.snapshot() == snaps_before["routines"]
    assert kernel.attention.snapshot() == snaps_before["attention"]
    assert kernel.variables.snapshot() == snaps_before["variables"]
    assert kernel.exposures.snapshot() == snaps_before["exposures"]
    assert kernel.stewardship.snapshot() == snaps_before["stewardship"]
    assert kernel.engagement.snapshot() == snaps_before["engagement"]
    assert kernel.escalations.snapshot() == snaps_before["escalations"]
    assert (
        kernel.strategic_responses.snapshot()
        == snaps_before["strategic_responses"]
    )


# ---------------------------------------------------------------------------
# No-action invariant
# ---------------------------------------------------------------------------


def test_industry_emits_only_industry_demand_condition_added_records():
    ledger = Ledger()
    book = IndustryConditionBook(ledger=ledger)
    book.add_condition(_condition(condition_id="cond:audit"))
    assert len(ledger.records) == 1
    record = ledger.records[0]
    assert (
        record.record_type
        is RecordType.INDUSTRY_DEMAND_CONDITION_ADDED
    )


def test_industry_does_not_emit_action_or_forecast_records():
    """
    v1.10.4 add_condition must not emit any action-class or
    forecast-class record. The forbidden record-type set covers
    every v1.x action-shaped record plus any record we would
    associate with execution behavior.
    """
    forbidden_event_types = {
        "order_submitted",
        "price_updated",
        "contract_created",
        "contract_status_updated",
        "contract_covenant_breached",
        "ownership_position_added",
        "ownership_transferred",
        "institution_action_recorded",
        "valuation_added",
        "valuation_compared",
        "firm_state_added",
    }
    ledger = Ledger()
    book = IndustryConditionBook(ledger=ledger)
    book.add_condition(_condition(condition_id="cond:no_action"))
    seen = {r.event_type for r in ledger.records}
    assert seen.isdisjoint(forbidden_event_types), (
        f"v1.10.4 add_condition must not emit any action / forecast / "
        f"firm-state record; saw forbidden event types: "
        f"{sorted(seen & forbidden_event_types)}"
    )


# ---------------------------------------------------------------------------
# Jurisdiction-neutral identifier scan
#
# This test reads its own source file and confirms that every test
# string is jurisdiction-neutral. The forbidden token list mirrors
# ``world/experiment.py::_FORBIDDEN_TOKENS``; this duplication is
# intentional so that the test fails locally even when the
# experiment-config scan does not run.
# ---------------------------------------------------------------------------


_FORBIDDEN_TOKENS = (
    "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
    "gpif", "tse", "nikkei", "topix", "sony", "jgb", "nyse",
)


def test_test_file_contains_no_jurisdiction_specific_identifiers():
    import re
    from pathlib import Path

    text = Path(__file__).read_text(encoding="utf-8").lower()
    table_start = text.find("_forbidden_tokens = (")
    table_end = text.find(")", table_start) + 1
    if table_start != -1 and table_end > 0:
        text = text[:table_start] + text[table_end:]

    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"jurisdiction-specific token {token!r} appeared in test file"
        )


def test_industry_module_contains_no_jurisdiction_specific_identifiers():
    import re
    from pathlib import Path

    module_path = (
        Path(__file__).resolve().parent.parent / "world" / "industry.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"jurisdiction-specific token {token!r} appeared in "
            f"world/industry.py"
        )
