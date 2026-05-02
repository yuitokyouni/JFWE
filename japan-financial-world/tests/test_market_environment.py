"""
Tests for v1.12.2 MarketEnvironmentStateRecord +
MarketEnvironmentBook + ``build_market_environment_state``.

Covers field validation (including bounded ``confidence`` with
explicit bool rejection), immutability, ``add_state``
deduplication, unknown lookup, every list / filter method,
deterministic snapshots, ledger emission with the new
``RecordType.MARKET_ENVIRONMENT_STATE_ADDED``, kernel wiring of
the new ``MarketEnvironmentBook``, the no-mutation guarantee
against every other v0/v1 source-of-truth book in the kernel,
the v1.12.2 scope discipline (no prices, no yields, no spreads,
no index levels, no forecasts, no expected returns, no
recommendations, no target prices, no target weights, no orders,
no trades, no allocations), the builder's deterministic
mapping rule set per regime, and an explicit anti-fields
assertion that no ``price`` / ``market_price`` / ``yield_value``
/ ``spread_bps`` / ``index_level`` / ``forecast_value`` /
``expected_return`` / ``target_price`` / ``recommendation`` /
``investment_advice`` / ``real_data_value`` / ``market_size`` /
``order`` / ``trade`` / ``allocation`` field exists on the
record or in the ledger payload.

Identifier and tag strings used in this test suite are
jurisdiction-neutral and synthetic; no Japan-specific institution
name, regulator, exchange, vendor benchmark, code, or threshold
appears anywhere in the test body.
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
from datetime import date

import pytest

from world.clock import Clock
from world.industry import IndustryDemandConditionRecord
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.market_conditions import MarketConditionRecord
from world.market_environment import (
    DuplicateMarketEnvironmentStateError,
    MarketEnvironmentBook,
    MarketEnvironmentStateRecord,
    MarketEnvironmentStateResult,
    UnknownMarketEnvironmentStateError,
    build_market_environment_state,
)
from world.market_surface_readout import build_capital_market_readout
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state(
    *,
    environment_state_id: str = "market_environment:2026-03-31",
    as_of_date: str = "2026-03-31",
    liquidity_regime: str = "normal",
    volatility_regime: str = "calm",
    credit_regime: str = "neutral",
    funding_regime: str = "normal",
    risk_appetite_regime: str = "neutral",
    rate_environment: str = "low",
    refinancing_window: str = "open",
    equity_valuation_regime: str = "neutral",
    overall_market_access_label: str = "open_or_constructive",
    status: str = "active",
    visibility: str = "internal_only",
    confidence: float = 0.5,
    source_market_condition_ids: tuple[str, ...] = (),
    source_market_readout_ids: tuple[str, ...] = (),
    source_industry_condition_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> MarketEnvironmentStateRecord:
    return MarketEnvironmentStateRecord(
        environment_state_id=environment_state_id,
        as_of_date=as_of_date,
        liquidity_regime=liquidity_regime,
        volatility_regime=volatility_regime,
        credit_regime=credit_regime,
        funding_regime=funding_regime,
        risk_appetite_regime=risk_appetite_regime,
        rate_environment=rate_environment,
        refinancing_window=refinancing_window,
        equity_valuation_regime=equity_valuation_regime,
        overall_market_access_label=overall_market_access_label,
        status=status,
        visibility=visibility,
        confidence=confidence,
        source_market_condition_ids=source_market_condition_ids,
        source_market_readout_ids=source_market_readout_ids,
        source_industry_condition_ids=source_industry_condition_ids,
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


def _seed_market_condition(
    kernel: WorldKernel,
    *,
    market_id: str,
    market_type: str,
    direction: str,
    as_of_date: str = "2026-03-31",
    condition_id: str | None = None,
    confidence: float = 0.5,
    strength: float = 0.5,
) -> str:
    cid = condition_id or f"market_condition:{market_id}:{as_of_date}"
    kernel.market_conditions.add_condition(
        MarketConditionRecord(
            condition_id=cid,
            market_id=market_id,
            market_type=market_type,
            as_of_date=as_of_date,
            condition_type=f"{market_type}_state",
            direction=direction,
            strength=strength,
            time_horizon="medium_term",
            confidence=confidence,
            status="active",
            visibility="internal_only",
        )
    )
    return cid


def _seed_default_5_market_surface(
    kernel: WorldKernel,
    *,
    as_of_date: str = "2026-03-31",
    rate_direction: str = "supportive",
    credit_direction: str = "stable",
    equity_direction: str = "supportive",
    funding_direction: str = "supportive",
    liquidity_direction: str = "stable",
    volatility_direction: str = "calm",
) -> tuple[str, tuple[str, ...]]:
    """Seed 5 (or 6 if volatility specified) market conditions +
    a capital-market readout. Returns
    (readout_id, market_condition_ids)."""
    cids: list[str] = []
    cids.append(
        _seed_market_condition(
            kernel,
            market_id="market:reference_rates_general",
            market_type="reference_rates",
            direction=rate_direction,
            as_of_date=as_of_date,
        )
    )
    cids.append(
        _seed_market_condition(
            kernel,
            market_id="market:reference_credit_spreads_general",
            market_type="credit_spreads",
            direction=credit_direction,
            as_of_date=as_of_date,
        )
    )
    cids.append(
        _seed_market_condition(
            kernel,
            market_id="market:reference_equity_general",
            market_type="equity_market",
            direction=equity_direction,
            as_of_date=as_of_date,
        )
    )
    cids.append(
        _seed_market_condition(
            kernel,
            market_id="market:reference_funding_general",
            market_type="funding_market",
            direction=funding_direction,
            as_of_date=as_of_date,
        )
    )
    cids.append(
        _seed_market_condition(
            kernel,
            market_id="market:reference_liquidity_general",
            market_type="liquidity_market",
            direction=liquidity_direction,
            as_of_date=as_of_date,
        )
    )
    if volatility_direction != "calm":
        cids.append(
            _seed_market_condition(
                kernel,
                market_id="market:reference_volatility_general",
                market_type="volatility_regime",
                direction=volatility_direction,
                as_of_date=as_of_date,
            )
        )
    readout = build_capital_market_readout(
        kernel,
        as_of_date=as_of_date,
        market_condition_ids=tuple(cids),
    )
    return readout.readout_id, tuple(cids)


# ---------------------------------------------------------------------------
# Field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"environment_state_id": ""},
        {"as_of_date": ""},
        {"liquidity_regime": ""},
        {"volatility_regime": ""},
        {"credit_regime": ""},
        {"funding_regime": ""},
        {"risk_appetite_regime": ""},
        {"rate_environment": ""},
        {"refinancing_window": ""},
        {"equity_valuation_regime": ""},
        {"overall_market_access_label": ""},
        {"status": ""},
        {"visibility": ""},
    ],
)
def test_state_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _state(**kwargs)


@pytest.mark.parametrize("value", [-0.01, 1.01, -1.0, 1.5, 100.0])
def test_state_confidence_rejects_out_of_range(value):
    with pytest.raises(ValueError):
        _state(confidence=value)


@pytest.mark.parametrize("value", [0.0, 0.5, 1.0])
def test_state_confidence_accepts_in_range(value):
    s = _state(confidence=value)
    assert s.confidence == float(value)


def test_state_confidence_rejects_bool_true():
    with pytest.raises(ValueError):
        _state(confidence=True)


def test_state_confidence_rejects_bool_false():
    with pytest.raises(ValueError):
        _state(confidence=False)


@pytest.mark.parametrize(
    "value",
    ["high", None, [], object()],
)
def test_state_confidence_rejects_non_numeric(value):
    with pytest.raises(ValueError):
        _state(confidence=value)


@pytest.mark.parametrize(
    "tuple_field",
    [
        "source_market_condition_ids",
        "source_market_readout_ids",
        "source_industry_condition_ids",
    ],
)
def test_state_rejects_empty_strings_in_tuple_fields(tuple_field):
    with pytest.raises(ValueError):
        _state(**{tuple_field: ("",)})


def test_state_coerces_as_of_date_to_iso_string():
    s = _state(as_of_date=date(2026, 3, 31))
    assert s.as_of_date == "2026-03-31"


def test_state_is_frozen():
    s = _state()
    with pytest.raises(Exception):
        s.liquidity_regime = "tight"  # type: ignore[misc]


def test_state_to_dict_round_trips_fields():
    s = _state(
        source_market_condition_ids=("market_condition:a",),
        source_market_readout_ids=("readout:a",),
        source_industry_condition_ids=("industry_condition:a",),
        metadata={"note": "synthetic"},
    )
    out = s.to_dict()
    assert out["environment_state_id"] == s.environment_state_id
    assert out["as_of_date"] == s.as_of_date
    assert out["liquidity_regime"] == s.liquidity_regime
    assert out["volatility_regime"] == s.volatility_regime
    assert out["credit_regime"] == s.credit_regime
    assert out["funding_regime"] == s.funding_regime
    assert out["risk_appetite_regime"] == s.risk_appetite_regime
    assert out["rate_environment"] == s.rate_environment
    assert out["refinancing_window"] == s.refinancing_window
    assert out["equity_valuation_regime"] == s.equity_valuation_regime
    assert out["overall_market_access_label"] == s.overall_market_access_label
    assert out["confidence"] == s.confidence
    assert out["source_market_condition_ids"] == ["market_condition:a"]
    assert out["source_market_readout_ids"] == ["readout:a"]
    assert out["source_industry_condition_ids"] == ["industry_condition:a"]
    assert out["metadata"] == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# Anti-fields — no price/yield/spread/forecast/order/trade/etc.
# ---------------------------------------------------------------------------


def test_state_record_has_no_price_or_forecast_field():
    """v1.12.2 market environment record must store labels only —
    never price / yield / spread / index level / forecast /
    expected return / target price / recommendation / target
    weight / order / trade / allocation."""
    field_names = {f.name for f in dataclass_fields(MarketEnvironmentStateRecord)}
    forbidden = {
        "price",
        "market_price",
        "yield_value",
        "spread_bps",
        "index_level",
        "forecast_value",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        "real_data_value",
        "market_size",
        "order",
        "trade",
        "allocation",
    }
    leaked = field_names & forbidden
    assert not leaked, (
        "MarketEnvironmentStateRecord must not declare anti-fields; "
        f"leaked: {sorted(leaked)}"
    )


# ---------------------------------------------------------------------------
# Book CRUD
# ---------------------------------------------------------------------------


def test_add_and_get_state():
    book = MarketEnvironmentBook()
    s = _state()
    book.add_state(s)
    assert book.get_state(s.environment_state_id) is s


def test_get_state_unknown_raises():
    book = MarketEnvironmentBook()
    with pytest.raises(UnknownMarketEnvironmentStateError):
        book.get_state("market_environment:missing")


def test_unknown_state_error_is_keyerror():
    book = MarketEnvironmentBook()
    with pytest.raises(KeyError):
        book.get_state("market_environment:missing")


def test_duplicate_state_id_rejected():
    book = MarketEnvironmentBook()
    book.add_state(_state())
    with pytest.raises(DuplicateMarketEnvironmentStateError):
        book.add_state(_state())


def test_add_state_returns_record():
    book = MarketEnvironmentBook()
    s = _state()
    out = book.add_state(s)
    assert out is s


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------


def test_list_states_in_insertion_order():
    book = MarketEnvironmentBook()
    a = _state(environment_state_id="market_environment:a")
    b = _state(environment_state_id="market_environment:b")
    book.add_state(a)
    book.add_state(b)
    assert book.list_states() == (a, b)


def test_list_states_empty_book():
    assert MarketEnvironmentBook().list_states() == ()


def test_list_by_date_filters_exactly():
    book = MarketEnvironmentBook()
    book.add_state(
        _state(
            environment_state_id="market_environment:2026-03-31",
            as_of_date="2026-03-31",
        )
    )
    book.add_state(
        _state(
            environment_state_id="market_environment:2026-06-30",
            as_of_date="2026-06-30",
        )
    )
    out = book.list_by_date("2026-03-31")
    assert len(out) == 1
    assert out[0].as_of_date == "2026-03-31"


def test_list_by_date_accepts_date_object():
    book = MarketEnvironmentBook()
    book.add_state(_state(as_of_date="2026-03-31"))
    out = book.list_by_date(date(2026, 3, 31))
    assert len(out) == 1


@pytest.mark.parametrize(
    "filter_method,filter_field,filter_value",
    [
        ("list_by_liquidity_regime", "liquidity_regime", "tight"),
        ("list_by_volatility_regime", "volatility_regime", "stressed"),
        ("list_by_credit_regime", "credit_regime", "tightening"),
        ("list_by_funding_regime", "funding_regime", "constrained"),
        ("list_by_risk_appetite_regime", "risk_appetite_regime", "risk_off"),
        ("list_by_rate_environment", "rate_environment", "rising"),
        ("list_by_refinancing_window", "refinancing_window", "closed"),
        (
            "list_by_overall_market_access_label",
            "overall_market_access_label",
            "selective_or_constrained",
        ),
    ],
)
def test_list_by_regime_filters(filter_method, filter_field, filter_value):
    book = MarketEnvironmentBook()
    book.add_state(_state(environment_state_id="market_environment:a"))
    book.add_state(
        _state(
            environment_state_id="market_environment:b",
            **{filter_field: filter_value},
        )
    )
    out = getattr(book, filter_method)(filter_value)
    assert len(out) == 1
    assert getattr(out[0], filter_field) == filter_value


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_is_deterministic_and_sorted():
    book = MarketEnvironmentBook()
    book.add_state(_state(environment_state_id="market_environment:b"))
    book.add_state(_state(environment_state_id="market_environment:a"))
    snap = book.snapshot()
    assert snap["state_count"] == 2
    assert [s["environment_state_id"] for s in snap["states"]] == [
        "market_environment:a",
        "market_environment:b",
    ]


def test_snapshot_empty_book():
    snap = MarketEnvironmentBook().snapshot()
    assert snap["state_count"] == 0
    assert snap["states"] == []


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_type_exists():
    assert (
        RecordType.MARKET_ENVIRONMENT_STATE_ADDED.value
        == "market_environment_state_added"
    )


def test_add_state_writes_exactly_one_ledger_record():
    ledger = Ledger()
    book = MarketEnvironmentBook(ledger=ledger)
    book.add_state(_state())
    assert len(ledger.records) == 1
    rec = ledger.records[0]
    assert rec.record_type is RecordType.MARKET_ENVIRONMENT_STATE_ADDED


def test_add_state_payload_carries_full_field_set():
    ledger = Ledger()
    book = MarketEnvironmentBook(ledger=ledger)
    book.add_state(
        _state(
            source_market_condition_ids=("market_condition:a",),
            source_market_readout_ids=("readout:a",),
            source_industry_condition_ids=("industry_condition:a",),
        )
    )
    payload = ledger.records[0].payload
    expected_keys = {
        "environment_state_id",
        "as_of_date",
        "liquidity_regime",
        "volatility_regime",
        "credit_regime",
        "funding_regime",
        "risk_appetite_regime",
        "rate_environment",
        "refinancing_window",
        "equity_valuation_regime",
        "overall_market_access_label",
        "status",
        "visibility",
        "confidence",
        "source_market_condition_ids",
        "source_market_readout_ids",
        "source_industry_condition_ids",
    }
    assert set(payload.keys()) >= expected_keys


def test_add_state_payload_carries_no_price_or_forecast_keys():
    """v1.12.2 ledger payload must not include any anti-field
    key; pin the absence so a future drift fails loudly."""
    ledger = Ledger()
    book = MarketEnvironmentBook(ledger=ledger)
    book.add_state(_state())
    payload = ledger.records[0].payload
    forbidden = {
        "price",
        "market_price",
        "yield_value",
        "spread_bps",
        "index_level",
        "forecast_value",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        "real_data_value",
        "market_size",
        "order",
        "trade",
        "allocation",
    }
    leaked = set(payload.keys()) & forbidden
    assert not leaked, (
        "ledger payload must not include anti-field keys; "
        f"leaked: {sorted(leaked)}"
    )


def test_add_state_without_ledger_does_not_raise():
    book = MarketEnvironmentBook()
    book.add_state(_state())


def test_duplicate_add_emits_no_extra_ledger_record():
    ledger = Ledger()
    book = MarketEnvironmentBook(ledger=ledger)
    book.add_state(_state())
    with pytest.raises(DuplicateMarketEnvironmentStateError):
        book.add_state(_state())
    assert len(ledger.records) == 1


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_market_environments_book():
    kernel = _kernel()
    assert isinstance(kernel.market_environments, MarketEnvironmentBook)
    assert kernel.market_environments.ledger is kernel.ledger
    assert kernel.market_environments.clock is kernel.clock


def test_kernel_add_state_emits_to_kernel_ledger():
    kernel = _kernel()
    kernel.market_environments.add_state(_state())
    records = kernel.ledger.filter(event_type="market_environment_state_added")
    assert len(records) == 1


def test_kernel_state_simulation_date_uses_clock():
    kernel = _kernel()
    kernel.market_environments.add_state(_state())
    records = kernel.ledger.filter(event_type="market_environment_state_added")
    assert records[-1].simulation_date == "2026-01-01"


# ---------------------------------------------------------------------------
# No-mutation guarantee against every other source-of-truth book
# ---------------------------------------------------------------------------


def test_market_environment_book_does_not_mutate_other_kernel_books():
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
        "industry_conditions": kernel.industry_conditions.snapshot(),
        "market_conditions": kernel.market_conditions.snapshot(),
        "capital_market_readouts": kernel.capital_market_readouts.snapshot(),
        "firm_financial_states": kernel.firm_financial_states.snapshot(),
        "investor_intents": kernel.investor_intents.snapshot(),
    }

    kernel.market_environments.add_state(_state(environment_state_id="env:k:a"))
    kernel.market_environments.add_state(
        _state(
            environment_state_id="env:k:b",
            as_of_date="2026-04-15",
            overall_market_access_label="selective_or_constrained",
        )
    )
    kernel.market_environments.list_states()
    kernel.market_environments.list_by_date("2026-03-31")
    kernel.market_environments.list_by_liquidity_regime("normal")
    kernel.market_environments.list_by_volatility_regime("calm")
    kernel.market_environments.list_by_credit_regime("neutral")
    kernel.market_environments.list_by_funding_regime("normal")
    kernel.market_environments.list_by_risk_appetite_regime("neutral")
    kernel.market_environments.list_by_rate_environment("low")
    kernel.market_environments.list_by_refinancing_window("open")
    kernel.market_environments.list_by_overall_market_access_label(
        "open_or_constructive"
    )
    kernel.market_environments.snapshot()

    for name, before in snaps_before.items():
        after = getattr(kernel, name).snapshot()
        assert after == before, f"book {name!r} was mutated"


# ---------------------------------------------------------------------------
# No-action invariant
# ---------------------------------------------------------------------------


def test_market_environments_emits_only_state_added_records():
    ledger = Ledger()
    book = MarketEnvironmentBook(ledger=ledger)
    book.add_state(_state())
    assert len(ledger.records) == 1
    record = ledger.records[0]
    assert record.record_type is RecordType.MARKET_ENVIRONMENT_STATE_ADDED


def test_market_environments_does_not_emit_action_or_pricing_records():
    """v1.12.2 add_state must not emit any action / pricing /
    contract / order / trade / allocation record."""
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
        "investor_intent_signal_added",
        "firm_latent_state_updated",
    }
    ledger = Ledger()
    book = MarketEnvironmentBook(ledger=ledger)
    book.add_state(_state())
    seen = {r.record_type.value for r in ledger.records}
    assert not (seen & forbidden_event_types), (
        f"emitted forbidden record types: {seen & forbidden_event_types}"
    )


# ---------------------------------------------------------------------------
# Builder — basic
# ---------------------------------------------------------------------------


def test_builder_returns_result_with_record_added_to_book():
    kernel = _kernel()
    r = build_market_environment_state(
        kernel, as_of_date="2026-03-31"
    )
    assert isinstance(r, MarketEnvironmentStateResult)
    assert r.record is kernel.market_environments.get_state(
        r.environment_state_id
    )


def test_builder_default_no_evidence_yields_unknown_labels():
    """No evidence → every regime label defaults to ``unknown``."""
    kernel = _kernel()
    r = build_market_environment_state(
        kernel, as_of_date="2026-03-31"
    )
    rec = r.record
    assert rec.liquidity_regime == "unknown"
    assert rec.volatility_regime == "unknown"
    assert rec.credit_regime == "unknown"
    assert rec.funding_regime == "unknown"
    assert rec.risk_appetite_regime == "unknown"
    assert rec.rate_environment == "unknown"
    assert rec.refinancing_window == "unknown"
    assert rec.equity_valuation_regime == "unknown"
    assert rec.overall_market_access_label == "unknown"
    assert rec.confidence == 0.5


def test_builder_is_idempotent_on_environment_state_id():
    kernel = _kernel()
    r1 = build_market_environment_state(
        kernel, as_of_date="2026-03-31"
    )
    r2 = build_market_environment_state(
        kernel, as_of_date="2026-03-31"
    )
    assert r1.environment_state_id == r2.environment_state_id
    assert r1.record is r2.record
    assert len(kernel.market_environments.list_states()) == 1


def test_builder_kernel_required():
    with pytest.raises(ValueError):
        build_market_environment_state(None, as_of_date="2026-03-31")


def test_builder_records_evidence_id_tuples():
    """The state record must carry the cited source id tuples
    so the v1.12.2 attention discipline is enforceable."""
    kernel = _kernel()
    readout_id, cids = _seed_default_5_market_surface(kernel)
    kernel.industry_conditions.add_condition(
        IndustryDemandConditionRecord(
            condition_id="industry_condition:a",
            industry_id="industry:reference_general",
            industry_label="Reference Industry",
            as_of_date="2026-03-31",
            condition_type="demand_state",
            demand_direction="stable",
            demand_strength=0.5,
            confidence=0.5,
            time_horizon="medium_term",
            status="active",
            visibility="internal_only",
        )
    )
    r = build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
        market_readout_ids=(readout_id,),
        industry_condition_ids=("industry_condition:a",),
    )
    assert r.record.source_market_condition_ids == cids
    assert r.record.source_market_readout_ids == (readout_id,)
    assert r.record.source_industry_condition_ids == ("industry_condition:a",)


def test_builder_does_not_mutate_evidence_books():
    kernel = _kernel()
    readout_id, cids = _seed_default_5_market_surface(kernel)
    snaps_before = {
        "market_conditions": kernel.market_conditions.snapshot(),
        "capital_market_readouts": (
            kernel.capital_market_readouts.snapshot()
        ),
        "industry_conditions": kernel.industry_conditions.snapshot(),
    }
    build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
        market_readout_ids=(readout_id,),
    )
    for name, before in snaps_before.items():
        assert getattr(kernel, name).snapshot() == before


def test_builder_deterministic_for_identical_inputs():
    """Two fresh kernels with identical wiring + identical
    builder calls must produce byte-identical state records."""
    k_a = _kernel()
    rid_a, cids_a = _seed_default_5_market_surface(k_a)
    r_a = build_market_environment_state(
        k_a,
        as_of_date="2026-03-31",
        market_condition_ids=cids_a,
        market_readout_ids=(rid_a,),
    )

    k_b = _kernel()
    rid_b, cids_b = _seed_default_5_market_surface(k_b)
    r_b = build_market_environment_state(
        k_b,
        as_of_date="2026-03-31",
        market_condition_ids=cids_b,
        market_readout_ids=(rid_b,),
    )

    a_dict = r_a.record.to_dict()
    b_dict = r_b.record.to_dict()
    assert a_dict == b_dict


# ---------------------------------------------------------------------------
# Builder — deterministic mapping rule set
# ---------------------------------------------------------------------------


def test_builder_constructive_directions_yield_constructive_labels():
    """All-supportive default 5-market surface yields:
    funding_regime=cheap, refinancing_window=open,
    overall_market_access_label=open_or_constructive,
    risk_appetite_regime=risk_on (since equity is supportive +
    liquidity at least normal)."""
    kernel = _kernel()
    rid, cids = _seed_default_5_market_surface(kernel)
    r = build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
        market_readout_ids=(rid,),
    )
    rec = r.record
    assert rec.funding_regime == "cheap"
    assert rec.refinancing_window == "open"
    assert rec.equity_valuation_regime == "supportive"
    assert rec.overall_market_access_label == "open_or_constructive"
    assert rec.risk_appetite_regime == "risk_on"


def test_builder_restrictive_credit_yields_tightening_credit_regime():
    kernel = _kernel()
    rid, cids = _seed_default_5_market_surface(
        kernel, credit_direction="tightening"
    )
    r = build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
        market_readout_ids=(rid,),
    )
    assert r.record.credit_regime == "tightening"


def test_builder_stressed_credit_yields_stressed_credit_regime():
    kernel = _kernel()
    rid, cids = _seed_default_5_market_surface(
        kernel, credit_direction="restrictive"
    )
    r = build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
        market_readout_ids=(rid,),
    )
    assert r.record.credit_regime == "stressed"


def test_builder_constrained_funding_yields_closed_refinancing_window():
    kernel = _kernel()
    rid, cids = _seed_default_5_market_surface(
        kernel,
        funding_direction="constrained",
        credit_direction="tightening",
        liquidity_direction="tightening",
    )
    r = build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
        market_readout_ids=(rid,),
    )
    rec = r.record
    assert rec.funding_regime == "constrained"
    assert rec.refinancing_window == "closed"
    assert rec.overall_market_access_label == "selective_or_constrained"
    # risk_off rule fires when overall constrained AND
    # (liquidity tight OR credit tightening).
    assert rec.risk_appetite_regime == "risk_off"


def test_builder_tight_liquidity_yields_tight_liquidity_regime():
    kernel = _kernel()
    rid, cids = _seed_default_5_market_surface(
        kernel, liquidity_direction="tightening"
    )
    r = build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
        market_readout_ids=(rid,),
    )
    assert r.record.liquidity_regime == "tight"


def test_builder_rising_rates_yields_rising_rate_environment():
    kernel = _kernel()
    rid, cids = _seed_default_5_market_surface(
        kernel, rate_direction="tightening"
    )
    r = build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
        market_readout_ids=(rid,),
    )
    assert r.record.rate_environment == "rising"


def test_builder_demanding_equity_yields_demanding_regime():
    kernel = _kernel()
    rid, cids = _seed_default_5_market_surface(
        kernel, equity_direction="tightening"
    )
    r = build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
        market_readout_ids=(rid,),
    )
    assert r.record.equity_valuation_regime == "demanding"


def test_builder_stressed_volatility_yields_stressed_volatility_regime():
    kernel = _kernel()
    rid, cids = _seed_default_5_market_surface(
        kernel, volatility_direction="stressed"
    )
    r = build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
        market_readout_ids=(rid,),
    )
    assert r.record.volatility_regime == "stressed"


def test_builder_overall_label_sourced_from_readout():
    kernel = _kernel()
    rid, cids = _seed_default_5_market_surface(kernel)
    r = build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
        market_readout_ids=(rid,),
    )
    readout = kernel.capital_market_readouts.get_readout(rid)
    assert (
        r.record.overall_market_access_label
        == readout.overall_market_access_label
    )


def test_builder_confidence_is_mean_of_evidence_confidences():
    kernel = _kernel()
    cid_a = _seed_market_condition(
        kernel,
        market_id="market:reference_rates_general",
        market_type="reference_rates",
        direction="supportive",
        confidence=0.4,
    )
    cid_b = _seed_market_condition(
        kernel,
        market_id="market:reference_credit_spreads_general",
        market_type="credit_spreads",
        direction="stable",
        confidence=0.6,
    )
    r = build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=(cid_a, cid_b),
    )
    # confidence is the mean of cited record confidences (here
    # both market conditions; no readout cited).
    assert abs(r.record.confidence - 0.5) < 1e-9


def test_builder_tolerates_unresolved_evidence_ids():
    """v1.12.2 attention discipline: unresolved cited ids are
    recorded as data on the state but do not block emission."""
    kernel = _kernel()
    r = build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=("market_condition:nonexistent",),
        market_readout_ids=("readout:nonexistent",),
        industry_condition_ids=("industry_condition:nonexistent",),
    )
    assert r.record.liquidity_regime == "unknown"
    assert r.record.source_market_condition_ids == (
        "market_condition:nonexistent",
    )
    assert r.record.source_market_readout_ids == ("readout:nonexistent",)
    assert r.record.source_industry_condition_ids == (
        "industry_condition:nonexistent",
    )


def test_builder_default_id_format():
    kernel = _kernel()
    r = build_market_environment_state(
        kernel, as_of_date="2026-03-31"
    )
    assert r.environment_state_id == "market_environment:2026-03-31"


def test_builder_explicit_id_overrides_default():
    kernel = _kernel()
    r = build_market_environment_state(
        kernel,
        as_of_date="2026-03-31",
        environment_state_id="env:custom",
    )
    assert r.environment_state_id == "env:custom"


# ---------------------------------------------------------------------------
# Jurisdiction-neutral identifier scan
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


def test_market_environment_module_contains_no_jurisdiction_specific_identifiers():
    import re
    from pathlib import Path

    module_path = (
        Path(__file__).resolve().parent.parent / "world" / "market_environment.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"jurisdiction-specific token {token!r} appeared in "
            f"world/market_environment.py"
        )
