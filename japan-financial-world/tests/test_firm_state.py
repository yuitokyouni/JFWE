"""
Tests for v1.12.0 FirmFinancialStateRecord +
FirmFinancialStateBook +
``run_reference_firm_financial_state_update``.

Covers field validation (including the seven bounded synthetic
numeric scalars in ``[0.0, 1.0]`` and explicit bool rejection
matching v1.11.0 / v1.11.1 idioms), immutability, ``add_state``
deduplication, unknown lookup, every list / filter method, the
``get_latest_for_firm`` and ``history_for_firm`` helpers,
deterministic snapshots, ledger emission with the new
``RecordType.FIRM_LATENT_STATE_UPDATED``, kernel wiring of the
new ``FirmFinancialStateBook``, the no-mutation guarantee against
every other v0/v1 source-of-truth book in the kernel (including
the v1.11.0 / v1.11.1 capital-market and readout books and the
v1.10.4 industry conditions book), the v1.12.0 scope discipline
(no pricing, no forecasting, no contract mutation, no covenant
enforcement, no investment advice), the helper's deterministic
rule set including chain-link to prior state, and an explicit
anti-fields assertion that no ``revenue`` / ``sales`` / ``EBITDA``
/ ``net_income`` / ``cash_balance`` / ``debt_amount`` /
``real_financial_statement`` / ``forecast_value`` /
``actual_value`` / ``accounting_value`` /
``investment_recommendation`` field exists on the record or in
the ledger payload.

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
from world.firm_state import (
    DuplicateFirmFinancialStateError,
    FirmFinancialStateBook,
    FirmFinancialStateRecord,
    FirmFinancialStateUpdateResult,
    UnknownFirmFinancialStateError,
    run_reference_firm_financial_state_update,
)
from world.industry import IndustryDemandConditionRecord
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.market_conditions import MarketConditionRecord
from world.market_surface_readout import build_capital_market_readout
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state(
    *,
    state_id: str = "firm_state:firm:reference_manufacturer_a:2026-03-31",
    firm_id: str = "firm:reference_manufacturer_a",
    as_of_date: str = "2026-03-31",
    status: str = "active",
    visibility: str = "internal_only",
    margin_pressure: float = 0.5,
    liquidity_pressure: float = 0.5,
    debt_service_pressure: float = 0.5,
    market_access_pressure: float = 0.5,
    funding_need_intensity: float = 0.5,
    response_readiness: float = 0.5,
    confidence: float = 0.5,
    previous_state_id: str | None = None,
    evidence_market_condition_ids: tuple[str, ...] = (),
    evidence_market_readout_ids: tuple[str, ...] = (),
    evidence_market_environment_state_ids: tuple[str, ...] = (),
    evidence_industry_condition_ids: tuple[str, ...] = (),
    evidence_pressure_signal_ids: tuple[str, ...] = (),
    evidence_valuation_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> FirmFinancialStateRecord:
    return FirmFinancialStateRecord(
        state_id=state_id,
        firm_id=firm_id,
        as_of_date=as_of_date,
        status=status,
        visibility=visibility,
        margin_pressure=margin_pressure,
        liquidity_pressure=liquidity_pressure,
        debt_service_pressure=debt_service_pressure,
        market_access_pressure=market_access_pressure,
        funding_need_intensity=funding_need_intensity,
        response_readiness=response_readiness,
        confidence=confidence,
        previous_state_id=previous_state_id,
        evidence_market_condition_ids=evidence_market_condition_ids,
        evidence_market_readout_ids=evidence_market_readout_ids,
        evidence_market_environment_state_ids=(
            evidence_market_environment_state_ids
        ),
        evidence_industry_condition_ids=evidence_industry_condition_ids,
        evidence_pressure_signal_ids=evidence_pressure_signal_ids,
        evidence_valuation_ids=evidence_valuation_ids,
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


def _seed_default_market_surface(
    kernel: WorldKernel, *, as_of_date: str, regime_overall: str
) -> tuple[str, tuple[str, ...]]:
    """Seed five v1.11.0 market conditions with directions chosen
    so the v1.11.1 readout's overall_market_access_label matches
    ``regime_overall``. Returns (readout_id, condition_ids)."""
    if regime_overall == "open_or_constructive":
        directions = {
            "reference_rates": "supportive",
            "credit_spreads": "stable",
            "equity_market": "supportive",
            "funding_market": "supportive",
            "liquidity_market": "stable",
        }
    elif regime_overall == "selective_or_constrained":
        directions = {
            "reference_rates": "tightening",
            "credit_spreads": "restrictive",
            "equity_market": "restrictive",
            "funding_market": "mixed",
            "liquidity_market": "tightening",
        }
    elif regime_overall == "mixed":
        directions = {
            "reference_rates": "stable",
            "credit_spreads": "stable",
            "equity_market": "mixed",
            "funding_market": "mixed",
            "liquidity_market": "stable",
        }
    else:
        raise ValueError(f"unknown overall {regime_overall!r}")
    spec_meta = (
        ("market:reference_rates_general", "reference_rates", "rate_level"),
        (
            "market:reference_credit_spreads_general",
            "credit_spreads",
            "spread_level",
        ),
        (
            "market:reference_equity_general",
            "equity_market",
            "valuation_environment",
        ),
        (
            "market:reference_funding_general",
            "funding_market",
            "funding_window",
        ),
        (
            "market:reference_liquidity_general",
            "liquidity_market",
            "liquidity_regime",
        ),
    )
    cids: list[str] = []
    for market_id, market_type, condition_type in spec_meta:
        cid = f"market_condition:{market_id}:{as_of_date}"
        kernel.market_conditions.add_condition(
            MarketConditionRecord(
                condition_id=cid,
                market_id=market_id,
                market_type=market_type,
                as_of_date=as_of_date,
                condition_type=condition_type,
                direction=directions[market_type],
                strength=0.5,
                time_horizon="medium_term",
                confidence=0.5,
                status="active",
                visibility="internal_only",
            )
        )
        cids.append(cid)
    readout = build_capital_market_readout(
        kernel,
        as_of_date=as_of_date,
        market_condition_ids=tuple(cids),
    )
    assert readout.overall_market_access_label == regime_overall
    return readout.readout_id, tuple(cids)


def _seed_industry(
    kernel: WorldKernel,
    *,
    industry_id: str = "industry:reference_manufacturing_general",
    as_of_date: str = "2026-03-31",
    direction: str = "stable",
) -> str:
    cid = f"industry_condition:{industry_id}:{as_of_date}"
    kernel.industry_conditions.add_condition(
        IndustryDemandConditionRecord(
            condition_id=cid,
            industry_id=industry_id,
            industry_label="reference industry (synthetic)",
            as_of_date=as_of_date,
            condition_type="demand_assessment",
            demand_direction=direction,
            demand_strength=0.5,
            time_horizon="medium_term",
            confidence=0.5,
            status="active",
            visibility="internal_only",
        )
    )
    return cid


# ---------------------------------------------------------------------------
# Record — field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"state_id": ""},
        {"firm_id": ""},
        {"as_of_date": ""},
        {"status": ""},
        {"visibility": ""},
    ],
)
def test_state_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _state(**kwargs)


@pytest.mark.parametrize(
    "field_name",
    [
        "margin_pressure",
        "liquidity_pressure",
        "debt_service_pressure",
        "market_access_pressure",
        "funding_need_intensity",
        "response_readiness",
        "confidence",
    ],
)
@pytest.mark.parametrize("value", [-0.01, 1.01, -1.0, 1.5, 100.0])
def test_state_bounded_numerics_reject_out_of_range(field_name, value):
    with pytest.raises(ValueError):
        _state(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "margin_pressure",
        "liquidity_pressure",
        "debt_service_pressure",
        "market_access_pressure",
        "funding_need_intensity",
        "response_readiness",
        "confidence",
    ],
)
def test_state_bounded_numerics_reject_bool_true(field_name):
    with pytest.raises(ValueError):
        _state(**{field_name: True})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field_name",
    [
        "margin_pressure",
        "liquidity_pressure",
        "debt_service_pressure",
        "market_access_pressure",
        "funding_need_intensity",
        "response_readiness",
        "confidence",
    ],
)
def test_state_bounded_numerics_reject_bool_false(field_name):
    with pytest.raises(ValueError):
        _state(**{field_name: False})  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["0.5", None, [0.5], {"x": 0.5}])
def test_state_margin_pressure_rejects_non_numeric(value):
    with pytest.raises((TypeError, ValueError)):
        _state(margin_pressure=value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "tuple_field",
    [
        "evidence_market_condition_ids",
        "evidence_market_readout_ids",
        "evidence_market_environment_state_ids",
        "evidence_industry_condition_ids",
        "evidence_pressure_signal_ids",
        "evidence_valuation_ids",
    ],
)
def test_state_rejects_empty_strings_in_tuple_fields(tuple_field):
    bad = {tuple_field: ("valid", "")}
    with pytest.raises(ValueError):
        _state(**bad)


def test_state_rejects_empty_previous_state_id():
    with pytest.raises(ValueError):
        _state(previous_state_id="")


def test_state_accepts_none_previous_state_id():
    s = _state(previous_state_id=None)
    assert s.previous_state_id is None


def test_state_coerces_as_of_date_to_iso_string():
    s = _state(as_of_date=date(2026, 3, 31))
    assert s.as_of_date == "2026-03-31"


# ---------------------------------------------------------------------------
# Immutability & round-trip
# ---------------------------------------------------------------------------


def test_state_is_frozen():
    s = _state()
    with pytest.raises(Exception):
        s.state_id = "tampered"  # type: ignore[misc]


def test_state_to_dict_round_trips_fields():
    s = _state(
        previous_state_id="firm_state:prev",
        evidence_market_readout_ids=("readout:a",),
        evidence_industry_condition_ids=("industry_condition:a",),
        evidence_pressure_signal_ids=("signal:a",),
        evidence_valuation_ids=("valuation:a",),
        metadata={"note": "synthetic"},
    )
    out = s.to_dict()
    assert out["state_id"] == s.state_id
    assert out["firm_id"] == s.firm_id
    assert out["as_of_date"] == s.as_of_date
    assert out["status"] == s.status
    assert out["visibility"] == s.visibility
    assert out["margin_pressure"] == s.margin_pressure
    assert out["liquidity_pressure"] == s.liquidity_pressure
    assert out["debt_service_pressure"] == s.debt_service_pressure
    assert out["market_access_pressure"] == s.market_access_pressure
    assert out["funding_need_intensity"] == s.funding_need_intensity
    assert out["response_readiness"] == s.response_readiness
    assert out["confidence"] == s.confidence
    assert out["previous_state_id"] == "firm_state:prev"
    assert out["evidence_market_readout_ids"] == ["readout:a"]
    assert out["evidence_industry_condition_ids"] == ["industry_condition:a"]
    assert out["evidence_pressure_signal_ids"] == ["signal:a"]
    assert out["evidence_valuation_ids"] == ["valuation:a"]
    assert out["metadata"] == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# Anti-fields — no revenue / EBITDA / cash / debt / forecast / accounting
# ---------------------------------------------------------------------------


def test_state_record_has_no_accounting_or_forecast_field():
    """v1.12.0 firm financial state record must store synthetic
    [0, 1] ordering scalars only — never revenue, sales, EBITDA,
    net income, cash balance, debt amount, real financial
    statement, forecast value, actual value, accounting value, or
    investment recommendation."""
    field_names = {
        f.name for f in dataclass_fields(FirmFinancialStateRecord)
    }
    forbidden = {
        "revenue",
        "sales",
        "EBITDA",
        "ebitda",
        "net_income",
        "cash_balance",
        "debt_amount",
        "real_financial_statement",
        "forecast_value",
        "actual_value",
        "accounting_value",
        "investment_recommendation",
    }
    leaked = field_names & forbidden
    assert not leaked, (
        f"v1.12.0 firm state must not carry accounting / forecast / "
        f"recommendation fields; found: {sorted(leaked)}"
    )


# ---------------------------------------------------------------------------
# Book — add / get / dedup / unknown
# ---------------------------------------------------------------------------


def test_add_and_get_state():
    book = FirmFinancialStateBook()
    s = _state()
    book.add_state(s)
    assert book.get_state(s.state_id) is s


def test_get_state_unknown_raises():
    book = FirmFinancialStateBook()
    with pytest.raises(UnknownFirmFinancialStateError):
        book.get_state("does-not-exist")


def test_unknown_state_error_is_keyerror():
    err = UnknownFirmFinancialStateError("missing")
    assert isinstance(err, KeyError)


def test_duplicate_state_id_rejected():
    book = FirmFinancialStateBook()
    book.add_state(_state(state_id="firm_state:dup"))
    with pytest.raises(DuplicateFirmFinancialStateError):
        book.add_state(_state(state_id="firm_state:dup"))


def test_add_state_returns_record():
    book = FirmFinancialStateBook()
    s = _state()
    returned = book.add_state(s)
    assert returned is s


# ---------------------------------------------------------------------------
# Listings & filters
# ---------------------------------------------------------------------------


def test_list_states_in_insertion_order():
    book = FirmFinancialStateBook()
    book.add_state(_state(state_id="firm_state:a"))
    book.add_state(_state(state_id="firm_state:b"))
    book.add_state(_state(state_id="firm_state:c"))
    listed = book.list_states()
    assert tuple(s.state_id for s in listed) == (
        "firm_state:a", "firm_state:b", "firm_state:c",
    )


def test_list_states_empty_book():
    assert FirmFinancialStateBook().list_states() == ()


def test_list_by_firm():
    book = FirmFinancialStateBook()
    book.add_state(
        _state(state_id="firm_state:a:1", firm_id="firm:reference_a")
    )
    book.add_state(
        _state(state_id="firm_state:b:1", firm_id="firm:reference_b")
    )
    book.add_state(
        _state(state_id="firm_state:a:2", firm_id="firm:reference_a")
    )
    matched = book.list_by_firm("firm:reference_a")
    assert tuple(s.state_id for s in matched) == (
        "firm_state:a:1", "firm_state:a:2",
    )


def test_list_by_date_filters_exactly():
    book = FirmFinancialStateBook()
    book.add_state(_state(state_id="firm_state:mar", as_of_date="2026-03-31"))
    book.add_state(_state(state_id="firm_state:jun", as_of_date="2026-06-30"))
    mar = book.list_by_date("2026-03-31")
    assert tuple(s.state_id for s in mar) == ("firm_state:mar",)
    assert book.list_by_date("2026-09-30") == ()


def test_list_by_date_accepts_date_object():
    book = FirmFinancialStateBook()
    book.add_state(_state(state_id="firm_state:mar", as_of_date="2026-03-31"))
    matched = book.list_by_date(date(2026, 3, 31))
    assert tuple(s.state_id for s in matched) == ("firm_state:mar",)


def test_get_latest_for_firm_returns_most_recently_added():
    book = FirmFinancialStateBook()
    s_old = _state(
        state_id="firm_state:old",
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
    )
    s_new = _state(
        state_id="firm_state:new",
        firm_id="firm:reference_a",
        as_of_date="2026-06-30",
    )
    book.add_state(s_old)
    book.add_state(s_new)
    assert book.get_latest_for_firm("firm:reference_a") is s_new


def test_get_latest_for_firm_returns_none_when_no_states():
    book = FirmFinancialStateBook()
    assert book.get_latest_for_firm("firm:reference_a") is None


def test_history_for_firm_returns_records_in_insertion_order():
    book = FirmFinancialStateBook()
    book.add_state(
        _state(
            state_id="firm_state:a:1",
            firm_id="firm:reference_a",
            as_of_date="2026-03-31",
        )
    )
    book.add_state(
        _state(
            state_id="firm_state:b:1",
            firm_id="firm:reference_b",
            as_of_date="2026-03-31",
        )
    )
    book.add_state(
        _state(
            state_id="firm_state:a:2",
            firm_id="firm:reference_a",
            as_of_date="2026-06-30",
        )
    )
    history = book.history_for_firm("firm:reference_a")
    assert tuple(s.state_id for s in history) == (
        "firm_state:a:1", "firm_state:a:2",
    )


# ---------------------------------------------------------------------------
# Snapshot determinism
# ---------------------------------------------------------------------------


def test_snapshot_is_deterministic_and_sorted():
    book = FirmFinancialStateBook()
    book.add_state(_state(state_id="firm_state:z"))
    book.add_state(_state(state_id="firm_state:a"))
    book.add_state(_state(state_id="firm_state:m"))

    snap1 = book.snapshot()
    snap2 = book.snapshot()
    assert snap1 == snap2
    assert snap1["state_count"] == 3
    assert [s["state_id"] for s in snap1["states"]] == [
        "firm_state:a", "firm_state:m", "firm_state:z",
    ]


def test_snapshot_empty_book():
    snap = FirmFinancialStateBook().snapshot()
    assert snap == {"state_count": 0, "states": []}


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_type_exists():
    assert (
        RecordType("firm_latent_state_updated")
        is RecordType.FIRM_LATENT_STATE_UPDATED
    )
    assert (
        RecordType.FIRM_LATENT_STATE_UPDATED.value
        == "firm_latent_state_updated"
    )


def test_add_state_writes_exactly_one_ledger_record():
    ledger = Ledger()
    book = FirmFinancialStateBook(ledger=ledger)
    book.add_state(_state(state_id="firm_state:emit"))
    records = ledger.filter(event_type="firm_latent_state_updated")
    assert len(records) == 1
    record = records[0]
    assert record.record_type is RecordType.FIRM_LATENT_STATE_UPDATED
    assert record.object_id == "firm_state:emit"
    assert record.source == "firm:reference_manufacturer_a"
    assert record.space_id == "firm_state"
    assert record.visibility == "internal_only"
    assert record.confidence == 0.5


def test_add_state_payload_carries_full_field_set():
    ledger = Ledger()
    book = FirmFinancialStateBook(ledger=ledger)
    book.add_state(
        _state(
            state_id="firm_state:payload",
            previous_state_id="firm_state:prev",
            evidence_market_readout_ids=("readout:a",),
            evidence_industry_condition_ids=("industry_condition:a",),
            evidence_pressure_signal_ids=("signal:a",),
        )
    )
    payload = ledger.filter(
        event_type="firm_latent_state_updated"
    )[-1].payload
    assert payload["state_id"] == "firm_state:payload"
    assert payload["firm_id"] == "firm:reference_manufacturer_a"
    assert payload["as_of_date"] == "2026-03-31"
    assert payload["status"] == "active"
    assert payload["visibility"] == "internal_only"
    assert payload["margin_pressure"] == 0.5
    assert payload["liquidity_pressure"] == 0.5
    assert payload["debt_service_pressure"] == 0.5
    assert payload["market_access_pressure"] == 0.5
    assert payload["funding_need_intensity"] == 0.5
    assert payload["response_readiness"] == 0.5
    assert payload["confidence"] == 0.5
    assert payload["previous_state_id"] == "firm_state:prev"
    assert tuple(payload["evidence_market_readout_ids"]) == ("readout:a",)
    assert tuple(payload["evidence_industry_condition_ids"]) == (
        "industry_condition:a",
    )
    assert tuple(payload["evidence_pressure_signal_ids"]) == ("signal:a",)


def test_add_state_payload_carries_no_accounting_or_forecast_keys():
    ledger = Ledger()
    book = FirmFinancialStateBook(ledger=ledger)
    book.add_state(_state(state_id="firm_state:audit"))
    payload_keys = set(
        ledger.filter(
            event_type="firm_latent_state_updated"
        )[-1].payload.keys()
    )
    forbidden = {
        "revenue",
        "sales",
        "EBITDA",
        "ebitda",
        "net_income",
        "cash_balance",
        "debt_amount",
        "real_financial_statement",
        "forecast_value",
        "actual_value",
        "accounting_value",
        "investment_recommendation",
    }
    leaked = payload_keys & forbidden
    assert not leaked, (
        f"v1.12.0 firm state payload must not carry accounting / "
        f"forecast / recommendation keys; found: {sorted(leaked)}"
    )


def test_add_state_without_ledger_does_not_raise():
    book = FirmFinancialStateBook()
    book.add_state(_state())


def test_duplicate_add_emits_no_extra_ledger_record():
    ledger = Ledger()
    book = FirmFinancialStateBook(ledger=ledger)
    book.add_state(_state(state_id="firm_state:once"))
    with pytest.raises(DuplicateFirmFinancialStateError):
        book.add_state(_state(state_id="firm_state:once"))
    assert len(ledger.filter(event_type="firm_latent_state_updated")) == 1


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_firm_financial_states_book():
    kernel = _kernel()
    assert isinstance(kernel.firm_financial_states, FirmFinancialStateBook)
    assert kernel.firm_financial_states.ledger is kernel.ledger
    assert kernel.firm_financial_states.clock is kernel.clock


def test_kernel_add_state_emits_to_kernel_ledger():
    kernel = _kernel()
    kernel.firm_financial_states.add_state(_state())
    records = kernel.ledger.filter(event_type="firm_latent_state_updated")
    assert len(records) == 1


def test_kernel_state_simulation_date_uses_clock():
    kernel = _kernel()
    kernel.firm_financial_states.add_state(_state(state_id="firm_state:wired"))
    records = kernel.ledger.filter(event_type="firm_latent_state_updated")
    assert records[-1].simulation_date == "2026-01-01"


# ---------------------------------------------------------------------------
# No-mutation guarantee against every other source-of-truth book
# ---------------------------------------------------------------------------


def test_firm_financial_states_book_does_not_mutate_other_kernel_books():
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
    }

    kernel.firm_financial_states.add_state(_state(state_id="firm_state:k:a"))
    kernel.firm_financial_states.add_state(
        _state(
            state_id="firm_state:k:b",
            firm_id="firm:reference_b",
            as_of_date="2026-04-15",
            margin_pressure=0.6,
            liquidity_pressure=0.7,
        )
    )
    kernel.firm_financial_states.list_states()
    kernel.firm_financial_states.list_by_firm("firm:reference_manufacturer_a")
    kernel.firm_financial_states.list_by_date("2026-03-31")
    kernel.firm_financial_states.get_latest_for_firm("firm:reference_b")
    kernel.firm_financial_states.history_for_firm(
        "firm:reference_manufacturer_a"
    )
    kernel.firm_financial_states.snapshot()

    for name, before in snaps_before.items():
        after = getattr(kernel, name).snapshot()
        assert after == before, f"book {name!r} was mutated"


# ---------------------------------------------------------------------------
# No-action invariant
# ---------------------------------------------------------------------------


def test_firm_financial_states_emits_only_firm_latent_state_updated_records():
    ledger = Ledger()
    book = FirmFinancialStateBook(ledger=ledger)
    book.add_state(_state(state_id="firm_state:audit"))
    assert len(ledger.records) == 1
    record = ledger.records[0]
    assert record.record_type is RecordType.FIRM_LATENT_STATE_UPDATED


def test_firm_financial_states_does_not_emit_action_or_pricing_records():
    """v1.12.0 add_state must not emit any action / pricing /
    contract-mutation / firm-state-added (v0/v1 registration)
    record. The forbidden set covers v1.x action-shaped records
    plus the legacy firm_state_added registration event so the
    new firm_latent_state_updated event is unambiguously
    distinguishable."""
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
    book = FirmFinancialStateBook(ledger=ledger)
    book.add_state(_state(state_id="firm_state:no_action"))
    seen = {r.event_type for r in ledger.records}
    assert seen.isdisjoint(forbidden_event_types), (
        f"v1.12.0 add_state must not emit any action / pricing / "
        f"contract-mutation / firm_state_added record; saw forbidden "
        f"event types: {sorted(seen & forbidden_event_types)}"
    )


# ---------------------------------------------------------------------------
# Helper — deterministic rule set
# ---------------------------------------------------------------------------


def test_helper_returns_result_with_record_added_to_book():
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="open_or_constructive"
    )
    icid = _seed_industry(kernel, direction="stable")
    result = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
        pressure_signal_ids=(),
    )
    assert isinstance(result, FirmFinancialStateUpdateResult)
    assert (
        kernel.firm_financial_states.get_state(result.state_id)
        is result.record
    )


def test_helper_is_idempotent_on_state_id():
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="open_or_constructive"
    )
    icid = _seed_industry(kernel, direction="stable")
    r1 = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
    )
    r2 = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
    )
    assert r1.record is r2.record
    assert (
        len(
            kernel.ledger.filter(
                event_type="firm_latent_state_updated"
            )
        )
        == 1
    )


def test_helper_chains_via_previous_state_id_explicit():
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="open_or_constructive"
    )
    icid = _seed_industry(kernel, direction="stable")
    r1 = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
    )
    readout_id2, cids2 = _seed_default_market_surface(
        kernel, as_of_date="2026-06-30", regime_overall="open_or_constructive"
    )
    icid2 = _seed_industry(kernel, as_of_date="2026-06-30", direction="stable")
    r2 = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-06-30",
        previous_state_id=r1.state_id,
        market_readout_ids=(readout_id2,),
        market_condition_ids=cids2,
        industry_condition_ids=(icid2,),
    )
    assert r2.previous_state_id == r1.state_id
    assert r2.record.previous_state_id == r1.state_id


def test_helper_chains_via_get_latest_for_firm_when_previous_state_id_omitted():
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="open_or_constructive"
    )
    icid = _seed_industry(kernel, direction="stable")
    r1 = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
    )
    readout_id2, cids2 = _seed_default_market_surface(
        kernel, as_of_date="2026-06-30", regime_overall="open_or_constructive"
    )
    icid2 = _seed_industry(kernel, as_of_date="2026-06-30", direction="stable")
    r2 = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-06-30",
        market_readout_ids=(readout_id2,),
        market_condition_ids=cids2,
        industry_condition_ids=(icid2,),
    )
    assert r2.previous_state_id == r1.state_id


def test_helper_starts_from_neutral_baseline_when_no_prior_state():
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="mixed"
    )
    icid = _seed_industry(kernel, direction="stable")
    r = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
    )
    # Mixed readout nudges market_access_pressure +0.02 from
    # baseline 0.5 → 0.52; everything else stays at 0.5 (no
    # restrictive credit, no contracting/expanding industry,
    # no pressure signals).
    assert r.record.previous_state_id is None
    assert r.record.margin_pressure == pytest.approx(0.5)
    assert r.record.liquidity_pressure == pytest.approx(0.5)
    assert r.record.debt_service_pressure == pytest.approx(0.5)
    assert r.record.market_access_pressure == pytest.approx(0.52)
    # funding_need = (0.5 + 0.5 + 0.52) / 3 = 0.5066...
    assert r.record.funding_need_intensity == pytest.approx(0.5066, abs=0.001)


def test_helper_constructive_regime_lets_pressures_decay_below_baseline():
    """Single period with constructive readout: market_access
    drops 0.05 from 0.5 → 0.45; debt_service drops 0.03 from 0.5
    → 0.47."""
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="open_or_constructive"
    )
    icid = _seed_industry(kernel, direction="stable")
    r = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
    )
    assert r.record.market_access_pressure == pytest.approx(0.45)
    assert r.record.debt_service_pressure == pytest.approx(0.47)


def test_helper_constrained_regime_raises_pressures_above_baseline():
    """Single period with constrained readout: market_access
    rises 0.10 from 0.5 → 0.60; debt_service rises 0.05 from 0.5
    → 0.55, and credit_tone restrictive adds another 0.05 →
    final 0.60."""
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="selective_or_constrained"
    )
    icid = _seed_industry(kernel, direction="stable")
    r = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
    )
    assert r.record.market_access_pressure == pytest.approx(0.60)
    # constrained readout +0.05 + restrictive credit_tone +0.05 = +0.10
    assert r.record.debt_service_pressure == pytest.approx(0.60)


def test_helper_constructive_lower_pressure_than_constrained_after_chained_periods():
    """The headline endogenous-dynamics test: starting from
    neutral, a chained sequence of constructive periods produces
    materially lower market_access_pressure than the same number
    of constrained periods."""
    def _run_chain(overall: str, periods: int) -> float:
        kernel = _kernel()
        prev_id: str | None = None
        for i, d in enumerate(
            ("2026-03-31", "2026-06-30", "2026-09-30", "2026-12-31")[:periods]
        ):
            readout_id, cids = _seed_default_market_surface(
                kernel, as_of_date=d, regime_overall=overall
            )
            icid = _seed_industry(kernel, as_of_date=d, direction="stable")
            r = run_reference_firm_financial_state_update(
                kernel,
                firm_id="firm:reference_manufacturer_a",
                as_of_date=d,
                previous_state_id=prev_id,
                market_readout_ids=(readout_id,),
                market_condition_ids=cids,
                industry_condition_ids=(icid,),
            )
            prev_id = r.state_id
        return r.record.market_access_pressure  # type: ignore[name-defined]

    constructive_final = _run_chain("open_or_constructive", periods=4)
    constrained_final = _run_chain("selective_or_constrained", periods=4)
    assert constructive_final < constrained_final
    # Constructive lets it decay materially; constrained pushes
    # it materially up.
    assert constructive_final < 0.4
    assert constrained_final > 0.7


def test_helper_contracting_industry_raises_margin_pressure():
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="mixed"
    )
    icid = _seed_industry(kernel, direction="contracting")
    r = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
    )
    assert r.record.margin_pressure == pytest.approx(0.55)


def test_helper_expanding_industry_lowers_margin_pressure():
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="mixed"
    )
    icid = _seed_industry(kernel, direction="expanding")
    r = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
    )
    assert r.record.margin_pressure == pytest.approx(0.47)


def test_helper_pressure_signals_raise_liquidity_pressure():
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="mixed"
    )
    icid = _seed_industry(kernel, direction="stable")
    r = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
        pressure_signal_ids=("signal:a", "signal:b", "signal:c"),
    )
    # 3 × +0.02 from baseline 0.5
    assert r.record.liquidity_pressure == pytest.approx(0.56)


def test_helper_funding_need_is_mean_of_three_pressures():
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="open_or_constructive"
    )
    icid = _seed_industry(kernel, direction="stable")
    r = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
    )
    # liquidity 0.5, debt_service 0.47, market_access 0.45.
    expected = (0.5 + 0.47 + 0.45) / 3.0
    assert r.record.funding_need_intensity == pytest.approx(expected, abs=0.001)


def test_helper_response_readiness_is_mean_of_funding_need_and_margin():
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="open_or_constructive"
    )
    icid = _seed_industry(kernel, direction="contracting")
    r = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
    )
    expected = (r.record.funding_need_intensity + r.record.margin_pressure) / 2.0
    assert r.record.response_readiness == pytest.approx(expected, abs=0.001)


def test_helper_clamps_pressures_to_unit_interval():
    """Ten chained constrained periods should saturate pressures
    at 1.0, not exceed it."""
    kernel = _kernel()
    prev_id: str | None = None
    for i in range(10):
        d = f"2026-{i + 1:02d}-15"
        readout_id, cids = _seed_default_market_surface(
            kernel, as_of_date=d, regime_overall="selective_or_constrained"
        )
        icid = _seed_industry(kernel, as_of_date=d, direction="contracting")
        r = run_reference_firm_financial_state_update(
            kernel,
            firm_id="firm:reference_manufacturer_a",
            as_of_date=d,
            previous_state_id=prev_id,
            market_readout_ids=(readout_id,),
            market_condition_ids=cids,
            industry_condition_ids=(icid,),
            pressure_signal_ids=("signal:a", "signal:b", "signal:c"),
        )
        prev_id = r.state_id
    final = r.record  # type: ignore[name-defined]
    for v in (
        final.margin_pressure,
        final.liquidity_pressure,
        final.debt_service_pressure,
        final.market_access_pressure,
        final.funding_need_intensity,
        final.response_readiness,
    ):
        assert 0.0 <= v <= 1.0


def test_helper_records_v1122_market_environment_evidence_id_tuple():
    """v1.12.2: the helper accepts a
    ``market_environment_state_ids`` kwarg and stores the tuple
    on the produced record's
    ``evidence_market_environment_state_ids`` slot. The slot is
    additive — pre-v1.12.2 callers (without the kwarg) still get
    an empty tuple."""
    kernel = _kernel()
    out = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_environment_state_ids=("market_environment:2026-03-31",),
    )
    assert out.record.evidence_market_environment_state_ids == (
        "market_environment:2026-03-31",
    )


def test_helper_default_records_empty_market_environment_evidence():
    kernel = _kernel()
    out = run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
    )
    assert out.record.evidence_market_environment_state_ids == ()


def test_helper_does_not_mutate_evidence_books():
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="open_or_constructive"
    )
    icid = _seed_industry(kernel, direction="stable")
    snaps_before = {
        "market_conditions": kernel.market_conditions.snapshot(),
        "capital_market_readouts": kernel.capital_market_readouts.snapshot(),
        "industry_conditions": kernel.industry_conditions.snapshot(),
    }
    run_reference_firm_financial_state_update(
        kernel,
        firm_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        industry_condition_ids=(icid,),
    )
    for name, before in snaps_before.items():
        after = getattr(kernel, name).snapshot()
        assert after == before, f"book {name!r} was mutated by helper"


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


def test_firm_state_module_contains_no_jurisdiction_specific_identifiers():
    import re
    from pathlib import Path

    module_path = (
        Path(__file__).resolve().parent.parent / "world" / "firm_state.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"jurisdiction-specific token {token!r} appeared in "
            f"world/firm_state.py"
        )
