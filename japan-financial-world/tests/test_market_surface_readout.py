"""
Tests for v1.11.1 CapitalMarketReadoutRecord +
CapitalMarketReadoutBook + ``build_capital_market_readout``.

Covers field validation (including the bounded synthetic
``confidence`` and explicit bool rejection matching v1.11.0
``world/market_conditions.py``), immutability, ``add_readout``
deduplication, unknown lookup, every list / filter method,
deterministic snapshots, ledger emission with the new
``RecordType.CAPITAL_MARKET_READOUT_ADDED``, kernel wiring of the
new ``CapitalMarketReadoutBook``, the no-mutation guarantee
against every other v0/v1 source-of-truth book in the kernel
(including v1.11.0 ``MarketConditionBook``), the v1.11.1 scope
discipline (no pricing, no forecasting, no DCM / ECM execution,
no investment recommendation, no action-class ledger record on
``add_readout``), the builder's deterministic rule set, and an
explicit anti-fields assertion that no ``price`` /
``target_price`` / ``yield_value`` / ``spread_bps`` /
``forecast_value`` / ``expected_return`` / ``recommendation`` /
``deal_advice`` / ``market_size`` / ``real_data_value`` field
exists on the record or in the ledger payload.

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
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.market_conditions import MarketConditionRecord
from world.market_surface_readout import (
    CapitalMarketReadoutBook,
    CapitalMarketReadoutRecord,
    DuplicateCapitalMarketReadoutError,
    UnknownCapitalMarketReadoutError,
    build_capital_market_readout,
)
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _readout(
    *,
    readout_id: str = "readout:capital_market:2026-03-31",
    as_of_date: str = "2026-03-31",
    rates_tone: str = "supportive",
    credit_tone: str = "stable",
    equity_tone: str = "supportive",
    funding_window_tone: str = "supportive",
    liquidity_tone: str = "stable",
    volatility_tone: str = "stable",
    overall_market_access_label: str = "open_or_constructive",
    banker_summary_label: str = "constructive_market_access_synthetic",
    status: str = "active",
    confidence: float = 0.5,
    visibility: str = "internal_only",
    market_condition_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> CapitalMarketReadoutRecord:
    return CapitalMarketReadoutRecord(
        readout_id=readout_id,
        as_of_date=as_of_date,
        rates_tone=rates_tone,
        credit_tone=credit_tone,
        equity_tone=equity_tone,
        funding_window_tone=funding_window_tone,
        liquidity_tone=liquidity_tone,
        volatility_tone=volatility_tone,
        overall_market_access_label=overall_market_access_label,
        banker_summary_label=banker_summary_label,
        status=status,
        confidence=confidence,
        visibility=visibility,
        market_condition_ids=market_condition_ids,
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


def _seed_default_market_conditions(
    kernel: WorldKernel, as_of_date: str = "2026-03-31"
) -> tuple[str, ...]:
    """Seed the kernel with the v1.11.0 default 5-market set so
    the v1.11.1 builder has something to read."""
    specs = (
        (
            "market:reference_rates_general",
            "reference_rates",
            "rate_level",
            "supportive",
        ),
        (
            "market:reference_credit_spreads_general",
            "credit_spreads",
            "spread_level",
            "stable",
        ),
        (
            "market:reference_equity_general",
            "equity_market",
            "valuation_environment",
            "supportive",
        ),
        (
            "market:reference_funding_general",
            "funding_market",
            "funding_window",
            "supportive",
        ),
        (
            "market:reference_liquidity_general",
            "liquidity_market",
            "liquidity_regime",
            "stable",
        ),
    )
    out: list[str] = []
    for market_id, market_type, condition_type, direction in specs:
        cid = f"market_condition:{market_id}:{as_of_date}"
        kernel.market_conditions.add_condition(
            MarketConditionRecord(
                condition_id=cid,
                market_id=market_id,
                market_type=market_type,
                as_of_date=as_of_date,
                condition_type=condition_type,
                direction=direction,
                strength=0.5,
                time_horizon="medium_term",
                confidence=0.5,
                status="active",
                visibility="internal_only",
            )
        )
        out.append(cid)
    return tuple(out)


# ---------------------------------------------------------------------------
# Record — field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"readout_id": ""},
        {"as_of_date": ""},
        {"rates_tone": ""},
        {"credit_tone": ""},
        {"equity_tone": ""},
        {"funding_window_tone": ""},
        {"liquidity_tone": ""},
        {"volatility_tone": ""},
        {"overall_market_access_label": ""},
        {"banker_summary_label": ""},
        {"status": ""},
        {"visibility": ""},
    ],
)
def test_readout_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _readout(**kwargs)


def test_readout_rejects_empty_strings_in_market_condition_ids():
    with pytest.raises(ValueError):
        _readout(market_condition_ids=("valid", ""))


def test_readout_coerces_as_of_date_to_iso_string():
    r = _readout(as_of_date=date(2026, 3, 31))
    assert r.as_of_date == "2026-03-31"


def test_readout_rejects_non_date_as_of_date():
    with pytest.raises((TypeError, ValueError)):
        _readout(as_of_date=12345)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Bounded numeric — confidence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [-0.01, 1.01, -1.0, 1.5, 100.0])
def test_confidence_rejects_out_of_range(value):
    with pytest.raises(ValueError):
        _readout(confidence=value)


@pytest.mark.parametrize("value", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_confidence_accepts_in_range(value):
    r = _readout(confidence=value)
    assert r.confidence == float(value)


def test_confidence_rejects_bool_true():
    with pytest.raises(ValueError):
        _readout(confidence=True)  # type: ignore[arg-type]


def test_confidence_rejects_bool_false():
    with pytest.raises(ValueError):
        _readout(confidence=False)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["0.5", None, [0.5], {"x": 0.5}])
def test_confidence_rejects_non_numeric(value):
    with pytest.raises((TypeError, ValueError)):
        _readout(confidence=value)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Immutability & round-trip
# ---------------------------------------------------------------------------


def test_readout_is_frozen():
    r = _readout()
    with pytest.raises(Exception):
        r.readout_id = "tampered"  # type: ignore[misc]


def test_readout_to_dict_round_trips_fields():
    r = _readout(
        market_condition_ids=("market_condition:reference_rates:2026-03-31",),
        metadata={"note": "synthetic"},
    )
    out = r.to_dict()
    assert out["readout_id"] == r.readout_id
    assert out["as_of_date"] == r.as_of_date
    assert out["rates_tone"] == r.rates_tone
    assert out["credit_tone"] == r.credit_tone
    assert out["equity_tone"] == r.equity_tone
    assert out["funding_window_tone"] == r.funding_window_tone
    assert out["liquidity_tone"] == r.liquidity_tone
    assert out["volatility_tone"] == r.volatility_tone
    assert (
        out["overall_market_access_label"]
        == r.overall_market_access_label
    )
    assert out["banker_summary_label"] == r.banker_summary_label
    assert out["status"] == r.status
    assert out["confidence"] == r.confidence
    assert out["visibility"] == r.visibility
    assert out["market_condition_ids"] == [
        "market_condition:reference_rates:2026-03-31"
    ]
    assert out["metadata"] == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# Anti-fields — no price / target_price / yield_value / forecast / etc.
# ---------------------------------------------------------------------------


def test_readout_record_has_no_price_or_advice_field():
    """v1.11.1 readout record must store deterministic labels —
    never a price, target price, yield, spread, forecast, expected
    return, recommendation, deal advice, market size, or
    real-data value. The v1.11.1 anti-fields list is the binding
    contract this test pins."""
    field_names = {
        f.name for f in dataclass_fields(CapitalMarketReadoutRecord)
    }
    forbidden = {
        "price",
        "target_price",
        "yield_value",
        "spread_bps",
        "forecast_value",
        "expected_return",
        "recommendation",
        "deal_advice",
        "market_size",
        "real_data_value",
    }
    leaked = field_names & forbidden
    assert not leaked, (
        f"v1.11.1 readout record must not carry price / forecast / "
        f"recommendation / deal-advice fields; found: {sorted(leaked)}"
    )


# ---------------------------------------------------------------------------
# Book — add / get / dedup / unknown
# ---------------------------------------------------------------------------


def test_add_and_get_readout():
    book = CapitalMarketReadoutBook()
    r = _readout()
    book.add_readout(r)
    assert book.get_readout(r.readout_id) is r


def test_get_readout_unknown_raises():
    book = CapitalMarketReadoutBook()
    with pytest.raises(UnknownCapitalMarketReadoutError):
        book.get_readout("does-not-exist")


def test_unknown_readout_error_is_keyerror():
    err = UnknownCapitalMarketReadoutError("missing")
    assert isinstance(err, KeyError)


def test_duplicate_readout_id_rejected():
    book = CapitalMarketReadoutBook()
    book.add_readout(_readout(readout_id="readout:dup"))
    with pytest.raises(DuplicateCapitalMarketReadoutError):
        book.add_readout(_readout(readout_id="readout:dup"))


def test_add_readout_returns_record():
    book = CapitalMarketReadoutBook()
    r = _readout()
    returned = book.add_readout(r)
    assert returned is r


# ---------------------------------------------------------------------------
# Listings & filters
# ---------------------------------------------------------------------------


def test_list_readouts_in_insertion_order():
    book = CapitalMarketReadoutBook()
    book.add_readout(_readout(readout_id="readout:a"))
    book.add_readout(_readout(readout_id="readout:b"))
    book.add_readout(_readout(readout_id="readout:c"))
    listed = book.list_readouts()
    assert tuple(r.readout_id for r in listed) == (
        "readout:a", "readout:b", "readout:c",
    )


def test_list_readouts_empty_book():
    assert CapitalMarketReadoutBook().list_readouts() == ()


def test_list_by_date_filters_exactly():
    book = CapitalMarketReadoutBook()
    book.add_readout(_readout(readout_id="r:mar", as_of_date="2026-03-31"))
    book.add_readout(_readout(readout_id="r:jun", as_of_date="2026-06-30"))
    book.add_readout(_readout(readout_id="r:mar2", as_of_date="2026-03-31"))
    mar = book.list_by_date("2026-03-31")
    jun = book.list_by_date("2026-06-30")
    miss = book.list_by_date("2026-09-30")
    assert tuple(r.readout_id for r in mar) == ("r:mar", "r:mar2")
    assert tuple(r.readout_id for r in jun) == ("r:jun",)
    assert miss == ()


def test_list_by_date_accepts_date_object():
    book = CapitalMarketReadoutBook()
    book.add_readout(_readout(readout_id="r:mar", as_of_date="2026-03-31"))
    matched = book.list_by_date(date(2026, 3, 31))
    assert tuple(r.readout_id for r in matched) == ("r:mar",)


def test_list_by_status():
    book = CapitalMarketReadoutBook()
    book.add_readout(_readout(readout_id="r:draft", status="draft"))
    book.add_readout(_readout(readout_id="r:active", status="active"))
    book.add_readout(_readout(readout_id="r:retired", status="retired"))
    assert tuple(
        r.readout_id for r in book.list_by_status("active")
    ) == ("r:active",)


def test_list_by_overall_market_access_label():
    book = CapitalMarketReadoutBook()
    book.add_readout(
        _readout(
            readout_id="r:open",
            overall_market_access_label="open_or_constructive",
        )
    )
    book.add_readout(
        _readout(
            readout_id="r:select",
            overall_market_access_label="selective_or_constrained",
        )
    )
    book.add_readout(
        _readout(readout_id="r:mixed", overall_market_access_label="mixed")
    )
    open_rs = book.list_by_overall_market_access_label("open_or_constructive")
    select_rs = book.list_by_overall_market_access_label(
        "selective_or_constrained"
    )
    mixed_rs = book.list_by_overall_market_access_label("mixed")
    assert tuple(r.readout_id for r in open_rs) == ("r:open",)
    assert tuple(r.readout_id for r in select_rs) == ("r:select",)
    assert tuple(r.readout_id for r in mixed_rs) == ("r:mixed",)


# ---------------------------------------------------------------------------
# Snapshot determinism
# ---------------------------------------------------------------------------


def test_snapshot_is_deterministic_and_sorted():
    book = CapitalMarketReadoutBook()
    book.add_readout(_readout(readout_id="readout:z"))
    book.add_readout(_readout(readout_id="readout:a"))
    book.add_readout(_readout(readout_id="readout:m"))

    snap1 = book.snapshot()
    snap2 = book.snapshot()
    assert snap1 == snap2
    assert snap1["readout_count"] == 3
    assert [r["readout_id"] for r in snap1["readouts"]] == [
        "readout:a", "readout:m", "readout:z",
    ]


def test_snapshot_empty_book():
    snap = CapitalMarketReadoutBook().snapshot()
    assert snap == {"readout_count": 0, "readouts": []}


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_type_exists():
    assert (
        RecordType("capital_market_readout_added")
        is RecordType.CAPITAL_MARKET_READOUT_ADDED
    )
    assert (
        RecordType.CAPITAL_MARKET_READOUT_ADDED.value
        == "capital_market_readout_added"
    )


def test_add_readout_writes_exactly_one_ledger_record():
    ledger = Ledger()
    book = CapitalMarketReadoutBook(ledger=ledger)
    book.add_readout(_readout(readout_id="r:emit"))
    records = ledger.filter(event_type="capital_market_readout_added")
    assert len(records) == 1
    record = records[0]
    assert (
        record.record_type is RecordType.CAPITAL_MARKET_READOUT_ADDED
    )
    assert record.object_id == "r:emit"
    assert record.space_id == "capital_markets"
    assert record.visibility == "internal_only"
    assert record.confidence == 0.5


def test_add_readout_payload_carries_full_field_set():
    ledger = Ledger()
    book = CapitalMarketReadoutBook(ledger=ledger)
    book.add_readout(
        _readout(
            readout_id="r:payload",
            market_condition_ids=(
                "market_condition:reference_rates:2026-03-31",
            ),
        )
    )
    payload = ledger.filter(
        event_type="capital_market_readout_added"
    )[-1].payload
    assert payload["readout_id"] == "r:payload"
    assert payload["as_of_date"] == "2026-03-31"
    assert payload["rates_tone"] == "supportive"
    assert payload["credit_tone"] == "stable"
    assert payload["equity_tone"] == "supportive"
    assert payload["funding_window_tone"] == "supportive"
    assert payload["liquidity_tone"] == "stable"
    assert payload["volatility_tone"] == "stable"
    assert (
        payload["overall_market_access_label"]
        == "open_or_constructive"
    )
    assert (
        payload["banker_summary_label"]
        == "constructive_market_access_synthetic"
    )
    assert payload["status"] == "active"
    assert payload["confidence"] == 0.5
    assert payload["visibility"] == "internal_only"
    assert tuple(payload["market_condition_ids"]) == (
        "market_condition:reference_rates:2026-03-31",
    )


def test_add_readout_payload_carries_no_price_or_advice_keys():
    ledger = Ledger()
    book = CapitalMarketReadoutBook(ledger=ledger)
    book.add_readout(_readout(readout_id="r:audit"))
    payload_keys = set(
        ledger.filter(
            event_type="capital_market_readout_added"
        )[-1].payload.keys()
    )
    forbidden = {
        "price",
        "target_price",
        "yield_value",
        "spread_bps",
        "forecast_value",
        "expected_return",
        "recommendation",
        "deal_advice",
        "market_size",
        "real_data_value",
    }
    leaked = payload_keys & forbidden
    assert not leaked, (
        f"v1.11.1 readout payload must not carry price / forecast / "
        f"recommendation / deal-advice keys; found: {sorted(leaked)}"
    )


def test_add_readout_without_ledger_does_not_raise():
    book = CapitalMarketReadoutBook()
    book.add_readout(_readout())


def test_duplicate_add_emits_no_extra_ledger_record():
    ledger = Ledger()
    book = CapitalMarketReadoutBook(ledger=ledger)
    book.add_readout(_readout(readout_id="r:once"))
    with pytest.raises(DuplicateCapitalMarketReadoutError):
        book.add_readout(_readout(readout_id="r:once"))
    assert (
        len(ledger.filter(event_type="capital_market_readout_added"))
        == 1
    )


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_capital_market_readouts_book():
    kernel = _kernel()
    assert isinstance(
        kernel.capital_market_readouts, CapitalMarketReadoutBook
    )
    assert kernel.capital_market_readouts.ledger is kernel.ledger
    assert kernel.capital_market_readouts.clock is kernel.clock


def test_kernel_add_readout_emits_to_kernel_ledger():
    kernel = _kernel()
    kernel.capital_market_readouts.add_readout(_readout())
    records = kernel.ledger.filter(
        event_type="capital_market_readout_added"
    )
    assert len(records) == 1


def test_kernel_readout_simulation_date_uses_clock():
    kernel = _kernel()
    kernel.capital_market_readouts.add_readout(_readout(readout_id="r:wired"))
    records = kernel.ledger.filter(
        event_type="capital_market_readout_added"
    )
    assert records[-1].simulation_date == "2026-01-01"


# ---------------------------------------------------------------------------
# No-mutation guarantee against every other source-of-truth book
# ---------------------------------------------------------------------------


def test_capital_market_readouts_book_does_not_mutate_other_kernel_books():
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
    }

    kernel.capital_market_readouts.add_readout(_readout(readout_id="r:k:a"))
    kernel.capital_market_readouts.add_readout(
        _readout(
            readout_id="r:k:b",
            overall_market_access_label="mixed",
            banker_summary_label="mixed_market_access_synthetic",
        )
    )
    kernel.capital_market_readouts.list_readouts()
    kernel.capital_market_readouts.list_by_date("2026-03-31")
    kernel.capital_market_readouts.list_by_status("active")
    kernel.capital_market_readouts.list_by_overall_market_access_label("mixed")
    kernel.capital_market_readouts.snapshot()

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
    assert (
        kernel.industry_conditions.snapshot()
        == snaps_before["industry_conditions"]
    )
    assert (
        kernel.market_conditions.snapshot()
        == snaps_before["market_conditions"]
    )


# ---------------------------------------------------------------------------
# No-action invariant
# ---------------------------------------------------------------------------


def test_capital_market_readouts_emits_only_readout_added_records():
    ledger = Ledger()
    book = CapitalMarketReadoutBook(ledger=ledger)
    book.add_readout(_readout(readout_id="r:audit"))
    assert len(ledger.records) == 1
    record = ledger.records[0]
    assert record.record_type is RecordType.CAPITAL_MARKET_READOUT_ADDED


def test_capital_market_readouts_does_not_emit_action_or_pricing_records():
    """v1.11.1 add_readout must not emit any action / pricing /
    issuance / deal-execution record. The forbidden record-type
    set covers v1.x action-shaped records plus every record we
    would associate with DCM / ECM execution, security issuance,
    pricing, or order matching."""
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
    book = CapitalMarketReadoutBook(ledger=ledger)
    book.add_readout(_readout(readout_id="r:no_action"))
    seen = {r.event_type for r in ledger.records}
    assert seen.isdisjoint(forbidden_event_types), (
        f"v1.11.1 add_readout must not emit any action / pricing / "
        f"issuance / firm-state record; saw forbidden event types: "
        f"{sorted(seen & forbidden_event_types)}"
    )


# ---------------------------------------------------------------------------
# Builder — deterministic rule set
# ---------------------------------------------------------------------------


def test_builder_returns_record_added_to_book():
    kernel = _kernel()
    cids = _seed_default_market_conditions(kernel)
    rec = build_capital_market_readout(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
    )
    assert isinstance(rec, CapitalMarketReadoutRecord)
    assert kernel.capital_market_readouts.get_readout(rec.readout_id) is rec


def test_builder_is_idempotent_on_readout_id():
    kernel = _kernel()
    cids = _seed_default_market_conditions(kernel)
    rec1 = build_capital_market_readout(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
    )
    rec2 = build_capital_market_readout(
        kernel,
        as_of_date="2026-03-31",
        market_condition_ids=cids,
    )
    assert rec1 is rec2
    assert (
        len(
            kernel.ledger.filter(event_type="capital_market_readout_added")
        )
        == 1
    )


def test_builder_deterministic_for_identical_market_conditions():
    """Two fresh kernels with identical market conditions must
    produce byte-identical readout to_dict() output."""
    k1 = _kernel()
    cids1 = _seed_default_market_conditions(k1)
    rec1 = build_capital_market_readout(
        k1, as_of_date="2026-03-31", market_condition_ids=cids1
    )
    k2 = _kernel()
    cids2 = _seed_default_market_conditions(k2)
    rec2 = build_capital_market_readout(
        k2, as_of_date="2026-03-31", market_condition_ids=cids2
    )
    assert rec1.to_dict() == rec2.to_dict()


def test_builder_maps_market_types_to_tone_slots():
    """Each v1.11.0 market_type must map to its corresponding
    tone slot per the v1.11.1 rule set; unmapped market types
    leave the slot at ``"unknown"``."""
    kernel = _kernel()
    cids = _seed_default_market_conditions(kernel)
    rec = build_capital_market_readout(
        kernel, as_of_date="2026-03-31", market_condition_ids=cids
    )
    # Default fixture: rates / credit / equity / funding / liquidity
    # all set; volatility absent.
    assert rec.rates_tone == "supportive"
    assert rec.credit_tone == "stable"
    assert rec.equity_tone == "supportive"
    assert rec.funding_window_tone == "supportive"
    assert rec.liquidity_tone == "stable"
    assert rec.volatility_tone == "unknown"


def test_builder_open_or_constructive_when_funding_supportive_and_credit_not_restrictive():
    kernel = _kernel()
    cids = _seed_default_market_conditions(kernel)
    rec = build_capital_market_readout(
        kernel, as_of_date="2026-03-31", market_condition_ids=cids
    )
    assert rec.overall_market_access_label == "open_or_constructive"
    assert rec.banker_summary_label == "constructive_market_access_synthetic"


def test_builder_selective_or_constrained_when_credit_and_liquidity_restrictive():
    kernel = _kernel()
    # Override the default fixture to simulate restrictive credit
    # and tightening liquidity. Funding window is held neutral
    # ("mixed") so the open_or_constructive branch does not fire.
    specs = (
        ("market:reference_rates_general", "reference_rates", "rate_level", "tightening"),
        ("market:reference_credit_spreads_general", "credit_spreads", "spread_level", "widening"),
        ("market:reference_equity_general", "equity_market", "valuation_environment", "mixed"),
        ("market:reference_funding_general", "funding_market", "funding_window", "mixed"),
        ("market:reference_liquidity_general", "liquidity_market", "liquidity_regime", "tightening"),
    )
    cids: list[str] = []
    for market_id, market_type, condition_type, direction in specs:
        cid = f"market_condition:{market_id}:2026-03-31"
        kernel.market_conditions.add_condition(
            MarketConditionRecord(
                condition_id=cid,
                market_id=market_id,
                market_type=market_type,
                as_of_date="2026-03-31",
                condition_type=condition_type,
                direction=direction,
                strength=0.5,
                time_horizon="medium_term",
                confidence=0.5,
                status="active",
                visibility="internal_only",
            )
        )
        cids.append(cid)
    rec = build_capital_market_readout(
        kernel, as_of_date="2026-03-31", market_condition_ids=tuple(cids)
    )
    assert rec.overall_market_access_label == "selective_or_constrained"
    assert rec.banker_summary_label == "selective_market_access_synthetic"


def test_builder_mixed_when_neither_branch_fires():
    kernel = _kernel()
    specs = (
        ("market:reference_rates_general", "reference_rates", "rate_level", "tightening"),
        ("market:reference_credit_spreads_general", "credit_spreads", "spread_level", "widening"),
        ("market:reference_equity_general", "equity_market", "valuation_environment", "mixed"),
        ("market:reference_funding_general", "funding_market", "funding_window", "mixed"),
        ("market:reference_liquidity_general", "liquidity_market", "liquidity_regime", "stable"),
    )
    cids: list[str] = []
    for market_id, market_type, condition_type, direction in specs:
        cid = f"market_condition:{market_id}:2026-03-31"
        kernel.market_conditions.add_condition(
            MarketConditionRecord(
                condition_id=cid,
                market_id=market_id,
                market_type=market_type,
                as_of_date="2026-03-31",
                condition_type=condition_type,
                direction=direction,
                strength=0.5,
                time_horizon="medium_term",
                confidence=0.5,
                status="active",
                visibility="internal_only",
            )
        )
        cids.append(cid)
    rec = build_capital_market_readout(
        kernel, as_of_date="2026-03-31", market_condition_ids=tuple(cids)
    )
    assert rec.overall_market_access_label == "mixed"
    assert rec.banker_summary_label == "mixed_market_access_synthetic"


def test_builder_confidence_is_average_of_cited_conditions():
    kernel = _kernel()
    cid_specs = (
        ("market:reference_rates_general", "reference_rates", "rate_level", 0.4),
        ("market:reference_credit_spreads_general", "credit_spreads", "spread_level", 0.6),
    )
    cids: list[str] = []
    for market_id, market_type, condition_type, conf in cid_specs:
        cid = f"market_condition:{market_id}:2026-03-31"
        kernel.market_conditions.add_condition(
            MarketConditionRecord(
                condition_id=cid,
                market_id=market_id,
                market_type=market_type,
                as_of_date="2026-03-31",
                condition_type=condition_type,
                direction="stable",
                strength=0.5,
                time_horizon="medium_term",
                confidence=conf,
                status="active",
                visibility="internal_only",
            )
        )
        cids.append(cid)
    rec = build_capital_market_readout(
        kernel, as_of_date="2026-03-31", market_condition_ids=tuple(cids)
    )
    assert rec.confidence == pytest.approx(0.5)


def test_builder_volatility_tone_uses_volatility_market_when_present():
    kernel = _kernel()
    cid = "market_condition:market:reference_volatility_general:2026-03-31"
    kernel.market_conditions.add_condition(
        MarketConditionRecord(
            condition_id=cid,
            market_id="market:reference_volatility_general",
            market_type="volatility_regime",
            as_of_date="2026-03-31",
            condition_type="volatility_regime",
            direction="restrictive",
            strength=0.7,
            time_horizon="short_term",
            confidence=0.5,
            status="active",
            visibility="internal_only",
        )
    )
    rec = build_capital_market_readout(
        kernel, as_of_date="2026-03-31", market_condition_ids=(cid,)
    )
    assert rec.volatility_tone == "restrictive"


def test_builder_returns_unknown_for_missing_market_types():
    kernel = _kernel()
    # Only seed one market — every other tone slot must default
    # to "unknown".
    cid = "market_condition:market:reference_rates_general:2026-03-31"
    kernel.market_conditions.add_condition(
        MarketConditionRecord(
            condition_id=cid,
            market_id="market:reference_rates_general",
            market_type="reference_rates",
            as_of_date="2026-03-31",
            condition_type="rate_level",
            direction="easing",
            strength=0.5,
            time_horizon="medium_term",
            confidence=0.5,
            status="active",
            visibility="internal_only",
        )
    )
    rec = build_capital_market_readout(
        kernel, as_of_date="2026-03-31", market_condition_ids=(cid,)
    )
    assert rec.rates_tone == "easing"
    assert rec.credit_tone == "unknown"
    assert rec.equity_tone == "unknown"
    assert rec.funding_window_tone == "unknown"
    assert rec.liquidity_tone == "unknown"
    assert rec.volatility_tone == "unknown"


def test_builder_does_not_mutate_market_conditions_book():
    """The builder must read MarketConditionBook without touching
    it. We snapshot before / after and compare."""
    kernel = _kernel()
    cids = _seed_default_market_conditions(kernel)
    snap_before = kernel.market_conditions.snapshot()
    build_capital_market_readout(
        kernel, as_of_date="2026-03-31", market_condition_ids=cids
    )
    assert kernel.market_conditions.snapshot() == snap_before


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


def test_market_surface_readout_module_contains_no_jurisdiction_specific_identifiers():
    import re
    from pathlib import Path

    module_path = (
        Path(__file__).resolve().parent.parent
        / "world"
        / "market_surface_readout.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"jurisdiction-specific token {token!r} appeared in "
            f"world/market_surface_readout.py"
        )
