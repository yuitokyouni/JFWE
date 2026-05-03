"""
Tests for v1.15.4 IndicativeMarketPressureRecord +
IndicativeMarketPressureBook + ``build_indicative_market_pressure``.
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
from datetime import date

import pytest

from world.capital_structure import MARKET_ACCESS_LABELS as V1143_MARKET_ACCESS
from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.market_interest import AggregatedMarketInterestRecord
from world.market_pressure import (
    DEMAND_PRESSURE_LABELS,
    DuplicateIndicativeMarketPressureError,
    FINANCING_RELEVANCE_LABELS,
    IndicativeMarketPressureBook,
    IndicativeMarketPressureRecord,
    LIQUIDITY_PRESSURE_LABELS,
    MARKET_ACCESS_LABELS_V1154,
    STATUS_LABELS,
    UnknownIndicativeMarketPressureError,
    VOLATILITY_PRESSURE_LABELS,
    build_indicative_market_pressure,
)
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 3, 31)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _record(
    *,
    market_pressure_id: str = (
        "indicative_market_pressure:security:reference_a:equity:line_1:"
        "2026-03-31"
    ),
    security_id: str = "security:reference_a:equity:line_1",
    as_of_date: str = "2026-03-31",
    demand_pressure_label: str = "insufficient_observations",
    liquidity_pressure_label: str = "unknown",
    volatility_pressure_label: str = "unknown",
    market_access_label: str = "unknown",
    financing_relevance_label: str = "insufficient_observations",
    status: str = "active",
    visibility: str = "internal_only",
    confidence: float = 0.5,
    source_aggregated_interest_ids: tuple[str, ...] = (),
    source_market_environment_state_ids: tuple[str, ...] = (),
    source_security_ids: tuple[str, ...] = (),
    source_venue_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> IndicativeMarketPressureRecord:
    return IndicativeMarketPressureRecord(
        market_pressure_id=market_pressure_id,
        security_id=security_id,
        as_of_date=as_of_date,
        demand_pressure_label=demand_pressure_label,
        liquidity_pressure_label=liquidity_pressure_label,
        volatility_pressure_label=volatility_pressure_label,
        market_access_label=market_access_label,
        financing_relevance_label=financing_relevance_label,
        status=status,
        visibility=visibility,
        confidence=confidence,
        source_aggregated_interest_ids=source_aggregated_interest_ids,
        source_market_environment_state_ids=source_market_environment_state_ids,
        source_security_ids=source_security_ids,
        source_venue_ids=source_venue_ids,
        metadata=metadata or {},
    )


def _aggregated(
    *,
    aggregated_interest_id: str,
    venue_id: str = "venue:reference_exchange_a",
    security_id: str = "security:reference_a:equity:line_1",
    as_of_date: str = "2026-03-31",
    increased_interest_count: int = 0,
    reduced_interest_count: int = 0,
    neutral_or_hold_review_count: int = 0,
    liquidity_watch_count: int = 0,
    risk_reduction_review_count: int = 0,
    engagement_linked_review_count: int = 0,
    total_intent_count: int | None = None,
    net_interest_label: str = "balanced",
    liquidity_interest_label: str = "liquidity_attention_low",
    concentration_label: str = "moderately_concentrated",
) -> AggregatedMarketInterestRecord:
    if total_intent_count is None:
        total_intent_count = (
            increased_interest_count
            + reduced_interest_count
            + neutral_or_hold_review_count
            + liquidity_watch_count
            + risk_reduction_review_count
            + engagement_linked_review_count
        )
    return AggregatedMarketInterestRecord(
        aggregated_interest_id=aggregated_interest_id,
        venue_id=venue_id,
        security_id=security_id,
        as_of_date=as_of_date,
        increased_interest_count=increased_interest_count,
        reduced_interest_count=reduced_interest_count,
        neutral_or_hold_review_count=neutral_or_hold_review_count,
        liquidity_watch_count=liquidity_watch_count,
        risk_reduction_review_count=risk_reduction_review_count,
        engagement_linked_review_count=engagement_linked_review_count,
        total_intent_count=total_intent_count,
        net_interest_label=net_interest_label,
        liquidity_interest_label=liquidity_interest_label,
        concentration_label=concentration_label,
        status="active",
        visibility="internal_only",
        confidence=0.5,
    )


# ---------------------------------------------------------------------------
# Required-string validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"market_pressure_id": ""},
        {"security_id": ""},
        {"as_of_date": ""},
        {"visibility": ""},
    ],
)
def test_record_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _record(**kwargs)


def test_record_coerces_date_to_iso_string():
    r = _record(as_of_date=date(2026, 3, 31))
    assert r.as_of_date == "2026-03-31"


def test_record_is_frozen():
    r = _record()
    with pytest.raises(Exception):
        r.market_pressure_id = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Confidence (bounded, bool-rejecting)
# ---------------------------------------------------------------------------


def test_record_rejects_bool_confidence():
    with pytest.raises(ValueError):
        _record(confidence=True)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [-0.01, 1.01, -1.0, 2.0])
def test_record_rejects_out_of_range_confidence(bad):
    with pytest.raises(ValueError):
        _record(confidence=bad)


@pytest.mark.parametrize("good", [0.0, 0.5, 1.0])
def test_record_accepts_in_range_confidence(good):
    r = _record(confidence=good)
    assert r.confidence == float(good)


def test_record_rejects_non_numeric_confidence():
    with pytest.raises(ValueError):
        _record(confidence="0.5")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Source-id tuple validation
# ---------------------------------------------------------------------------


def test_record_rejects_empty_strings_in_source_tuples():
    for kwarg in (
        "source_aggregated_interest_ids",
        "source_market_environment_state_ids",
        "source_security_ids",
        "source_venue_ids",
    ):
        with pytest.raises(ValueError):
            _record(**{kwarg: ("",)})


def test_record_to_dict_round_trips():
    r = _record(
        source_aggregated_interest_ids=(
            "aggregated_market_interest:venue_a:security_a:2026-03-31",
        ),
        source_market_environment_state_ids=(
            "market_environment_state:2026Q3",
        ),
        source_security_ids=("security:reference_a:equity:line_1",),
        source_venue_ids=("venue:reference_exchange_a",),
        metadata={"note": "synthetic"},
    )
    out = r.to_dict()
    assert out["source_aggregated_interest_ids"] == [
        "aggregated_market_interest:venue_a:security_a:2026-03-31"
    ]
    assert out["source_market_environment_state_ids"] == [
        "market_environment_state:2026Q3"
    ]
    assert out["source_security_ids"] == [
        "security:reference_a:equity:line_1"
    ]
    assert out["source_venue_ids"] == ["venue:reference_exchange_a"]
    assert out["metadata"] == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# Closed-set acceptance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label", sorted(DEMAND_PRESSURE_LABELS))
def test_demand_pressure_labels_accepted(label):
    r = _record(demand_pressure_label=label)
    assert r.demand_pressure_label == label


@pytest.mark.parametrize("label", sorted(LIQUIDITY_PRESSURE_LABELS))
def test_liquidity_pressure_labels_accepted(label):
    r = _record(liquidity_pressure_label=label)
    assert r.liquidity_pressure_label == label


@pytest.mark.parametrize("label", sorted(VOLATILITY_PRESSURE_LABELS))
def test_volatility_pressure_labels_accepted(label):
    r = _record(volatility_pressure_label=label)
    assert r.volatility_pressure_label == label


@pytest.mark.parametrize("label", sorted(MARKET_ACCESS_LABELS_V1154))
def test_market_access_labels_accepted(label):
    r = _record(market_access_label=label)
    assert r.market_access_label == label


@pytest.mark.parametrize("label", sorted(FINANCING_RELEVANCE_LABELS))
def test_financing_relevance_labels_accepted(label):
    r = _record(financing_relevance_label=label)
    assert r.financing_relevance_label == label


@pytest.mark.parametrize("label", sorted(STATUS_LABELS))
def test_status_labels_accepted(label):
    r = _record(status=label)
    assert r.status == label


# ---------------------------------------------------------------------------
# Closed-set rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name",
    [
        "demand_pressure_label",
        "liquidity_pressure_label",
        "volatility_pressure_label",
        "market_access_label",
        "financing_relevance_label",
        "status",
    ],
)
def test_label_field_rejects_out_of_set_value(field_name):
    with pytest.raises(ValueError):
        _record(**{field_name: "not_a_real_label"})


# ---------------------------------------------------------------------------
# Closed-set pinning
# ---------------------------------------------------------------------------


def test_pinned_demand_pressure_label_set_is_exact():
    assert DEMAND_PRESSURE_LABELS == frozenset(
        {
            "supportive",
            "balanced",
            "cautious",
            "adverse",
            "mixed",
            "insufficient_observations",
            "unknown",
        }
    )


def test_pinned_liquidity_pressure_label_set_is_exact():
    assert LIQUIDITY_PRESSURE_LABELS == frozenset(
        {"ample", "normal", "thin", "tight", "stressed", "unknown"}
    )


def test_pinned_volatility_pressure_label_set_is_exact():
    assert VOLATILITY_PRESSURE_LABELS == frozenset(
        {"calm", "elevated", "stressed", "unknown"}
    )


def test_pinned_financing_relevance_label_set_is_exact():
    assert FINANCING_RELEVANCE_LABELS == frozenset(
        {
            "supportive_for_equity_access",
            "neutral_for_financing",
            "caution_for_dilution",
            "adverse_for_market_access",
            "insufficient_observations",
            "unknown",
        }
    )


def test_pinned_status_label_set_is_exact():
    assert STATUS_LABELS == frozenset(
        {"draft", "active", "stale", "superseded", "archived", "unknown"}
    )


def test_market_access_label_set_aligns_with_v1_14_3():
    """The v1.15.4 ``market_access_label`` vocabulary IS the
    v1.14.3 ``MARKET_ACCESS_LABELS`` vocabulary by construction
    (same frozenset object). This pin makes the alignment a
    structural invariant — if someone adds a label to one side
    only, this test fails."""
    assert MARKET_ACCESS_LABELS_V1154 is V1143_MARKET_ACCESS


# ---------------------------------------------------------------------------
# Anti-fields — must NOT appear on dataclass or ledger payload
# ---------------------------------------------------------------------------


_FORBIDDEN_FIELDS = {
    "price",
    "market_price",
    "indicative_price",
    "target_price",
    "expected_return",
    "bid",
    "ask",
    "quote",
    "order",
    "order_id",
    "order_imbalance",
    "trade",
    "trade_id",
    "execution",
    "executed",
    "clearing",
    "settlement",
    "recommendation",
    "investment_advice",
    "real_data_value",
    # plus the v1.14.x family standard set
    "amount",
    "loan_amount",
    "interest_rate",
    "coupon",
    "coupon_rate",
    "spread",
    "fee",
    "yield",
    "policy_rate",
    "interest",
    "tenor_years",
    "default_probability",
    "behavior_probability",
    "rating",
    "internal_rating",
    "pd",
    "lgd",
    "ead",
    "decision_outcome",
    "forecast_value",
    "actual_value",
    "underwriting",
    "syndication",
    "commitment",
    "allocation",
    "offering_price",
    "take_up_probability",
    "selected_option",
    "optimal_option",
    "approved",
    "buy",
    "sell",
    "target_weight",
    "overweight",
    "underweight",
}


def test_record_has_no_anti_fields():
    field_names = {
        f.name for f in dataclass_fields(IndicativeMarketPressureRecord)
    }
    leaked = field_names & _FORBIDDEN_FIELDS
    assert not leaked


# ---------------------------------------------------------------------------
# Book — CRUD
# ---------------------------------------------------------------------------


def test_book_add_and_get_record():
    book = IndicativeMarketPressureBook()
    r = _record()
    book.add_record(r)
    assert book.get_record(r.market_pressure_id) is r


def test_book_get_unknown_record_raises():
    book = IndicativeMarketPressureBook()
    with pytest.raises(UnknownIndicativeMarketPressureError):
        book.get_record("indicative_market_pressure:missing")
    with pytest.raises(KeyError):
        book.get_record("indicative_market_pressure:missing")


def test_book_duplicate_id_rejected():
    book = IndicativeMarketPressureBook()
    book.add_record(_record())
    with pytest.raises(DuplicateIndicativeMarketPressureError):
        book.add_record(_record())


def test_book_list_records_returns_all():
    book = IndicativeMarketPressureBook()
    book.add_record(_record(market_pressure_id="indicative_market_pressure:a"))
    book.add_record(_record(market_pressure_id="indicative_market_pressure:b"))
    assert len(book.list_records()) == 2


def test_book_list_by_security():
    book = IndicativeMarketPressureBook()
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:a",
            security_id="security:p1",
        )
    )
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:b",
            security_id="security:p2",
        )
    )
    assert len(book.list_by_security("security:p2")) == 1


def test_book_list_by_date():
    book = IndicativeMarketPressureBook()
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:a",
            as_of_date="2026-03-31",
        )
    )
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:b",
            as_of_date="2026-04-30",
        )
    )
    assert len(book.list_by_date("2026-04-30")) == 1


def test_book_list_by_demand_pressure():
    book = IndicativeMarketPressureBook()
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:a",
            demand_pressure_label="supportive",
        )
    )
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:b",
            demand_pressure_label="adverse",
        )
    )
    assert len(book.list_by_demand_pressure("adverse")) == 1


def test_book_list_by_liquidity_pressure():
    book = IndicativeMarketPressureBook()
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:a",
            liquidity_pressure_label="normal",
        )
    )
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:b",
            liquidity_pressure_label="stressed",
        )
    )
    assert len(book.list_by_liquidity_pressure("stressed")) == 1


def test_book_list_by_volatility_pressure():
    book = IndicativeMarketPressureBook()
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:a",
            volatility_pressure_label="calm",
        )
    )
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:b",
            volatility_pressure_label="stressed",
        )
    )
    assert len(book.list_by_volatility_pressure("stressed")) == 1


def test_book_list_by_market_access():
    book = IndicativeMarketPressureBook()
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:a",
            market_access_label="open",
        )
    )
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:b",
            market_access_label="constrained",
        )
    )
    assert len(book.list_by_market_access("constrained")) == 1


def test_book_list_by_status():
    book = IndicativeMarketPressureBook()
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:a", status="active"
        )
    )
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:b",
            status="superseded",
        )
    )
    assert len(book.list_by_status("superseded")) == 1


def test_book_list_by_source_aggregated_interest():
    book = IndicativeMarketPressureBook()
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:a",
            source_aggregated_interest_ids=("aggregated_market_interest:n1",),
        )
    )
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:b",
            source_aggregated_interest_ids=(
                "aggregated_market_interest:n1",
                "aggregated_market_interest:n2",
            ),
        )
    )
    book.add_record(
        _record(
            market_pressure_id="indicative_market_pressure:c",
            source_aggregated_interest_ids=("aggregated_market_interest:n3",),
        )
    )
    out = book.list_by_source_aggregated_interest(
        "aggregated_market_interest:n1"
    )
    assert {r.market_pressure_id for r in out} == {
        "indicative_market_pressure:a",
        "indicative_market_pressure:b",
    }


def test_book_snapshot_is_deterministic_and_sorted():
    book = IndicativeMarketPressureBook()
    book.add_record(_record(market_pressure_id="indicative_market_pressure:b"))
    book.add_record(_record(market_pressure_id="indicative_market_pressure:a"))
    snap = book.snapshot()
    assert snap["record_count"] == 2
    assert [r["market_pressure_id"] for r in snap["records"]] == [
        "indicative_market_pressure:a",
        "indicative_market_pressure:b",
    ]
    assert book.snapshot() == snap


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_type_exists():
    assert (
        RecordType.INDICATIVE_MARKET_PRESSURE_RECORDED.value
        == "indicative_market_pressure_recorded"
    )


def test_add_record_writes_exactly_one_ledger_record():
    ledger = Ledger()
    book = IndicativeMarketPressureBook(ledger=ledger)
    book.add_record(_record())
    assert len(ledger.records) == 1
    rec = ledger.records[0]
    assert rec.record_type is RecordType.INDICATIVE_MARKET_PRESSURE_RECORDED
    assert rec.space_id == "indicative_market_pressure"


def test_duplicate_add_emits_no_extra_ledger_record():
    ledger = Ledger()
    book = IndicativeMarketPressureBook(ledger=ledger)
    book.add_record(_record())
    with pytest.raises(DuplicateIndicativeMarketPressureError):
        book.add_record(_record())
    assert len(ledger.records) == 1


def test_ledger_record_routes_security_as_source():
    """``source = security_id`` so the ledger graph reads as
    'security S has indicative market pressure P'."""
    ledger = Ledger()
    book = IndicativeMarketPressureBook(ledger=ledger)
    book.add_record(_record())
    rec = ledger.records[0]
    assert rec.source == "security:reference_a:equity:line_1"


def test_ledger_payload_carries_no_anti_field_keys():
    ledger = Ledger()
    book = IndicativeMarketPressureBook(ledger=ledger)
    book.add_record(_record())
    rec = ledger.records[0]
    leaked = set(rec.payload.keys()) & _FORBIDDEN_FIELDS
    assert not leaked


def test_ledger_emits_no_forbidden_event_types():
    ledger = Ledger()
    book = IndicativeMarketPressureBook(ledger=ledger)
    book.add_record(_record())
    types = {rec.record_type for rec in ledger.records}
    assert types == {RecordType.INDICATIVE_MARKET_PRESSURE_RECORDED}


def test_book_without_ledger_does_not_raise():
    book = IndicativeMarketPressureBook()
    book.add_record(_record())


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_indicative_market_pressure_book():
    k = _kernel()
    assert isinstance(k.indicative_market_pressure, IndicativeMarketPressureBook)
    assert k.indicative_market_pressure.ledger is k.ledger
    assert k.indicative_market_pressure.clock is k.clock


def test_kernel_simulation_date_uses_clock_for_record():
    k = _kernel()
    k.indicative_market_pressure.add_record(_record())
    rec = k.ledger.records[-1]
    assert rec.simulation_date == "2026-03-31"


# ---------------------------------------------------------------------------
# No-mutation invariant — including PriceBook
# ---------------------------------------------------------------------------


def test_book_does_not_mutate_other_kernel_books_including_pricebook():
    k = _kernel()
    snaps_before = {
        "ownership": k.ownership.snapshot(),
        "contracts": k.contracts.snapshot(),
        "prices": k.prices.snapshot(),  # explicit PriceBook check
        "constraints": k.constraints.snapshot(),
        "signals": k.signals.snapshot(),
        "valuations": k.valuations.snapshot(),
        "settlement_accounts": k.settlement_accounts.snapshot(),
        "settlement_payments": k.settlement_payments.snapshot(),
        "interbank_liquidity": k.interbank_liquidity.snapshot(),
        "central_bank_signals": k.central_bank_signals.snapshot(),
        "attention_feedback": k.attention_feedback.snapshot(),
        "investor_intents": k.investor_intents.snapshot(),
        "market_environments": k.market_environments.snapshot(),
        "firm_financial_states": k.firm_financial_states.snapshot(),
        "corporate_financing_needs": k.corporate_financing_needs.snapshot(),
        "funding_options": k.funding_options.snapshot(),
        "capital_structure_reviews": k.capital_structure_reviews.snapshot(),
        "financing_paths": k.financing_paths.snapshot(),
        "security_market": k.security_market.snapshot(),
        "investor_market_intents": k.investor_market_intents.snapshot(),
        "aggregated_market_interest": k.aggregated_market_interest.snapshot(),
    }
    k.indicative_market_pressure.add_record(_record())
    for name, before in snaps_before.items():
        assert getattr(k, name).snapshot() == before, name


def test_helper_does_not_mutate_pricebook():
    """v1.15.4 explicitly does NOT mutate the PriceBook even
    when the helper synthesises a pressure record from real
    aggregated-interest data."""
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            increased_interest_count=3,
            security_id="security:target",
        )
    )
    prices_before = k.prices.snapshot()
    build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert k.prices.snapshot() == prices_before


# ---------------------------------------------------------------------------
# Builder — empty / no-data case
# ---------------------------------------------------------------------------


def test_builder_no_records_yields_insufficient_observations():
    k = _kernel()
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=(),
    )
    assert r.demand_pressure_label == "insufficient_observations"
    assert r.liquidity_pressure_label == "unknown"
    assert r.volatility_pressure_label == "unknown"
    assert r.market_access_label == "unknown"
    assert r.financing_relevance_label == "insufficient_observations"
    assert r.metadata["matched_aggregated_record_count"] == 0


# ---------------------------------------------------------------------------
# Builder — demand_pressure_label rules
# ---------------------------------------------------------------------------


def test_builder_supportive_demand_when_increased_dominates():
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            increased_interest_count=3,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.demand_pressure_label == "supportive"


def test_builder_cautious_demand_when_reduced_dominates_with_normal_liquidity():
    """Reduced > increased + neutral, no liquidity_watch
    → ``cautious`` (not yet ``adverse``)."""
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            reduced_interest_count=3,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.demand_pressure_label == "cautious"
    assert r.liquidity_pressure_label == "normal"


def test_builder_adverse_demand_when_reduced_with_tight_liquidity():
    """Reduced > increased + neutral, liquidity_watch dominates
    (high) but ``total < 4`` → liquidity_pressure ``tight`` →
    demand ``adverse``."""
    k = _kernel()
    # 1 reduced + 2 liquidity_watch = 3 total; lw*2 (= 4) >= total (3)
    # → liquidity_attention_high → tight (total < 4 branch)
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            reduced_interest_count=1,
            liquidity_watch_count=2,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.liquidity_pressure_label == "tight"
    assert r.demand_pressure_label == "adverse"


def test_builder_mixed_demand_when_increased_and_reduced_close():
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            increased_interest_count=1,
            reduced_interest_count=1,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.demand_pressure_label == "mixed"


def test_builder_balanced_demand_when_neutral_dominates():
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            neutral_or_hold_review_count=3,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.demand_pressure_label == "balanced"


# ---------------------------------------------------------------------------
# Builder — liquidity_pressure_label rules
# ---------------------------------------------------------------------------


def test_builder_liquidity_normal_when_no_liquidity_watch():
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            increased_interest_count=2,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.liquidity_pressure_label == "normal"


def test_builder_liquidity_thin_when_moderate_attention():
    """1 liquidity_watch out of 4 total → moderate → thin."""
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            increased_interest_count=3,
            liquidity_watch_count=1,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.liquidity_pressure_label == "thin"


def test_builder_liquidity_stressed_when_high_attention_and_total_ge_4():
    """4 liquidity_watch out of 4 total → high; total >= 4 →
    stressed (vs tight)."""
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            liquidity_watch_count=4,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.liquidity_pressure_label == "stressed"


# ---------------------------------------------------------------------------
# Builder — volatility_pressure_label rules
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lw,total,expected",
    [
        (0, 3, "calm"),         # liquidity normal → calm
        (1, 4, "elevated"),      # liquidity thin → elevated
        (4, 4, "stressed"),      # liquidity stressed → stressed
    ],
)
def test_builder_volatility_pressure_derived_from_liquidity(lw, total, expected):
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            liquidity_watch_count=lw,
            increased_interest_count=total - lw,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.volatility_pressure_label == expected


# ---------------------------------------------------------------------------
# Builder — market_access_label rules (sharing v1.14.3 vocabulary)
# ---------------------------------------------------------------------------


def test_builder_market_access_open_when_supportive_and_normal():
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            increased_interest_count=3,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.demand_pressure_label == "supportive"
    assert r.liquidity_pressure_label == "normal"
    assert r.market_access_label == "open"


def test_builder_market_access_constrained_when_adverse():
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            reduced_interest_count=1,
            liquidity_watch_count=2,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.demand_pressure_label == "adverse"
    assert r.market_access_label == "constrained"


def test_builder_market_access_selective_when_mixed():
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            increased_interest_count=1,
            reduced_interest_count=1,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.demand_pressure_label == "mixed"
    assert r.market_access_label == "selective"


def test_builder_market_access_unknown_when_no_observations():
    k = _kernel()
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=(),
    )
    assert r.market_access_label == "unknown"


# ---------------------------------------------------------------------------
# Builder — financing_relevance_label rules
# ---------------------------------------------------------------------------


def test_builder_financing_supportive_when_market_access_open():
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            increased_interest_count=3,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.market_access_label == "open"
    assert r.financing_relevance_label == "supportive_for_equity_access"


def test_builder_financing_caution_for_dilution_when_selective_and_cautious():
    """Reduced demand (1 reduced, 0 liquidity_watch) →
    demand=cautious, liquidity=normal → market_access=selective →
    financing_relevance=caution_for_dilution (cautious branch)."""
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            reduced_interest_count=3,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.demand_pressure_label == "cautious"
    assert r.market_access_label == "selective"
    assert r.financing_relevance_label == "caution_for_dilution"


def test_builder_financing_neutral_when_selective_and_mixed():
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            increased_interest_count=1,
            reduced_interest_count=1,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.market_access_label == "selective"
    assert r.financing_relevance_label == "neutral_for_financing"


def test_builder_financing_adverse_when_constrained():
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            reduced_interest_count=1,
            liquidity_watch_count=2,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=("aggregated_market_interest:a",),
    )
    assert r.market_access_label == "constrained"
    assert r.financing_relevance_label == "adverse_for_market_access"


def test_builder_financing_insufficient_when_unknown_market_access():
    k = _kernel()
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=(),
    )
    assert r.market_access_label == "unknown"
    assert r.financing_relevance_label == "insufficient_observations"


# ---------------------------------------------------------------------------
# Builder — sums counts across multiple matched records
# ---------------------------------------------------------------------------


def test_builder_sums_counts_across_multiple_matched_records():
    """Two aggregated records on the same security: their counts
    are summed before label derivation."""
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:a",
            increased_interest_count=2,
            security_id="security:target",
        )
    )
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:b",
            increased_interest_count=1,
            reduced_interest_count=1,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=(
            "aggregated_market_interest:a",
            "aggregated_market_interest:b",
        ),
    )
    # Summed: increased=3, reduced=1, total=4 →
    # increased > reduced and increased >= neutral → supportive.
    assert r.demand_pressure_label == "supportive"
    assert r.metadata["matched_aggregated_record_count"] == 2


# ---------------------------------------------------------------------------
# Builder — mismatched / unresolved / no-global-scan
# ---------------------------------------------------------------------------


def test_builder_ignores_mismatched_security_id_and_records_count_in_metadata():
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:on_target",
            increased_interest_count=3,
            security_id="security:target",
        )
    )
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:on_other",
            increased_interest_count=5,
            security_id="security:other",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=(
            "aggregated_market_interest:on_target",
            "aggregated_market_interest:on_other",
        ),
    )
    assert r.metadata["mismatched_security_id_count"] == 1
    assert r.metadata["unresolved_aggregated_interest_count"] == 0
    assert r.metadata["matched_aggregated_record_count"] == 1
    # Only the matching record counted toward labels.
    assert r.demand_pressure_label == "supportive"


def test_builder_ignores_unresolved_ids_and_records_count_in_metadata():
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:resolved",
            increased_interest_count=2,
            security_id="security:target",
        )
    )
    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=(
            "aggregated_market_interest:resolved",
            "aggregated_market_interest:does_not_exist",
        ),
    )
    assert r.metadata["mismatched_security_id_count"] == 0
    assert r.metadata["unresolved_aggregated_interest_count"] == 1
    assert r.metadata["matched_aggregated_record_count"] == 1


def test_builder_does_not_scan_aggregated_records_globally():
    """The helper must read only the cited ids — never iterate
    the full aggregated-interest book. We monkey-patch every
    list_* and snapshot on the cited book to raise; if the
    helper calls any of them, the test fails."""
    k = _kernel()
    k.aggregated_market_interest.add_record(
        _aggregated(
            aggregated_interest_id="aggregated_market_interest:cited",
            increased_interest_count=2,
            security_id="security:target",
        )
    )

    def _boom(*_a, **_kw):  # pragma: no cover - must not fire
        raise AssertionError(
            "helper performed a global scan via list_* / snapshot — forbidden"
        )

    book = k.aggregated_market_interest
    for method_name in dir(book):
        if method_name.startswith("list_") or method_name == "snapshot":
            setattr(book, method_name, _boom)

    r = build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=(
            "aggregated_market_interest:cited",
        ),
    )
    assert r.demand_pressure_label == "supportive"


def test_builder_default_id_is_deterministic():
    k = _kernel()
    r = build_indicative_market_pressure(
        k,
        security_id="security:reference_a:equity:line_1",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=(),
    )
    assert r.market_pressure_id == (
        "indicative_market_pressure:security:reference_a:equity:line_1:"
        "2026-03-31"
    )


def test_builder_writes_one_ledger_record():
    k = _kernel()
    build_indicative_market_pressure(
        k,
        security_id="security:target",
        as_of_date="2026-03-31",
        source_aggregated_interest_ids=(),
    )
    matched = [
        rec
        for rec in k.ledger.records
        if rec.record_type
        is RecordType.INDICATIVE_MARKET_PRESSURE_RECORDED
    ]
    assert len(matched) == 1


def test_builder_is_deterministic_across_fresh_kernels():
    """Same cited-record content + same args → same labels and
    metadata across two fresh kernels."""

    def build(kernel: WorldKernel) -> IndicativeMarketPressureRecord:
        kernel.aggregated_market_interest.add_record(
            _aggregated(
                aggregated_interest_id="aggregated_market_interest:a",
                increased_interest_count=3,
                security_id="security:target",
            )
        )
        return build_indicative_market_pressure(
            kernel,
            security_id="security:target",
            as_of_date="2026-03-31",
            source_aggregated_interest_ids=(
                "aggregated_market_interest:a",
            ),
        )

    k1 = _kernel()
    k2 = _kernel()
    r1 = build(k1)
    r2 = build(k2)
    assert r1.to_dict() == r2.to_dict()


# ---------------------------------------------------------------------------
# Jurisdiction-neutral identifier scan
# ---------------------------------------------------------------------------


_FORBIDDEN_TOKENS = (
    "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
    "gpif", "tse", "nikkei", "topix", "sony", "jgb", "nyse",
    "target2", "fedwire", "chaps", "bojnet",
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
        assert re.search(pattern, text) is None, token


def test_module_contains_no_jurisdiction_specific_identifiers():
    import re
    from pathlib import Path

    module_path = (
        Path(__file__).resolve().parent.parent
        / "world"
        / "market_pressure.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, token
