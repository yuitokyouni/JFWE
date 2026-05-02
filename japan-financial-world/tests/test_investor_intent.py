"""
Tests for v1.12.1 InvestorIntentRecord + InvestorIntentBook +
``run_reference_investor_intent_signal``.

Covers field validation (including bounded ``confidence`` with
explicit bool rejection), immutability, ``add_intent``
deduplication, unknown lookup, every list / filter method,
deterministic snapshots, ledger emission with the new
``RecordType.INVESTOR_INTENT_SIGNAL_ADDED``, kernel wiring of the
new ``InvestorIntentBook``, the no-mutation guarantee against
every other v0/v1 source-of-truth book in the kernel, the v1.12.1
scope discipline (no orders, no trades, no rebalancing, no
target weights, no expected return, no recommendations), the
helper's deterministic rule set including the priority-order
classifier, and an explicit anti-fields assertion that no
``order`` / ``order_id`` / ``trade`` / ``buy`` / ``sell`` /
``rebalance`` / ``target_weight`` / ``overweight`` /
``underweight`` / ``expected_return`` / ``target_price`` /
``recommendation`` / ``investment_advice`` /
``portfolio_allocation`` / ``execution`` field exists on the
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
from world.firm_state import (
    FirmFinancialStateRecord,
)
from world.investor_intent import (
    DuplicateInvestorIntentError,
    InvestorIntentBook,
    InvestorIntentRecord,
    InvestorIntentSignalResult,
    UnknownInvestorIntentError,
    run_reference_investor_intent_signal,
)
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


def _intent(
    *,
    intent_id: str = (
        "intent:investor:reference_pension_a:firm:reference_manufacturer_a:2026-03-31"
    ),
    investor_id: str = "investor:reference_pension_a",
    target_company_id: str = "firm:reference_manufacturer_a",
    as_of_date: str = "2026-03-31",
    intent_type: str = "watch_adjustment",
    intent_direction: str = "hold_review",
    priority: str = "medium",
    horizon: str = "medium_term",
    status: str = "active",
    visibility: str = "internal_only",
    confidence: float = 0.5,
    evidence_selected_observation_set_ids: tuple[str, ...] = (),
    evidence_market_readout_ids: tuple[str, ...] = (),
    evidence_market_condition_ids: tuple[str, ...] = (),
    evidence_market_environment_state_ids: tuple[str, ...] = (),
    evidence_firm_state_ids: tuple[str, ...] = (),
    evidence_valuation_ids: tuple[str, ...] = (),
    evidence_dialogue_ids: tuple[str, ...] = (),
    evidence_escalation_candidate_ids: tuple[str, ...] = (),
    evidence_stewardship_theme_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> InvestorIntentRecord:
    return InvestorIntentRecord(
        intent_id=intent_id,
        investor_id=investor_id,
        target_company_id=target_company_id,
        as_of_date=as_of_date,
        intent_type=intent_type,
        intent_direction=intent_direction,
        priority=priority,
        horizon=horizon,
        status=status,
        visibility=visibility,
        confidence=confidence,
        evidence_selected_observation_set_ids=evidence_selected_observation_set_ids,
        evidence_market_readout_ids=evidence_market_readout_ids,
        evidence_market_condition_ids=evidence_market_condition_ids,
        evidence_market_environment_state_ids=(
            evidence_market_environment_state_ids
        ),
        evidence_firm_state_ids=evidence_firm_state_ids,
        evidence_valuation_ids=evidence_valuation_ids,
        evidence_dialogue_ids=evidence_dialogue_ids,
        evidence_escalation_candidate_ids=evidence_escalation_candidate_ids,
        evidence_stewardship_theme_ids=evidence_stewardship_theme_ids,
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
    return readout.readout_id, tuple(cids)


def _seed_firm_state(
    kernel: WorldKernel,
    *,
    state_id: str,
    firm_id: str = "firm:reference_manufacturer_a",
    as_of_date: str = "2026-03-31",
    margin_pressure: float = 0.5,
    liquidity_pressure: float = 0.5,
    debt_service_pressure: float = 0.5,
    market_access_pressure: float = 0.5,
    funding_need_intensity: float = 0.5,
    response_readiness: float = 0.5,
) -> str:
    kernel.firm_financial_states.add_state(
        FirmFinancialStateRecord(
            state_id=state_id,
            firm_id=firm_id,
            as_of_date=as_of_date,
            status="active",
            visibility="internal_only",
            margin_pressure=margin_pressure,
            liquidity_pressure=liquidity_pressure,
            debt_service_pressure=debt_service_pressure,
            market_access_pressure=market_access_pressure,
            funding_need_intensity=funding_need_intensity,
            response_readiness=response_readiness,
            confidence=0.5,
        )
    )
    return state_id


# ---------------------------------------------------------------------------
# Record — field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"intent_id": ""},
        {"investor_id": ""},
        {"target_company_id": ""},
        {"as_of_date": ""},
        {"intent_type": ""},
        {"intent_direction": ""},
        {"priority": ""},
        {"horizon": ""},
        {"status": ""},
        {"visibility": ""},
    ],
)
def test_intent_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _intent(**kwargs)


@pytest.mark.parametrize("value", [-0.01, 1.01, -1.0, 1.5, 100.0])
def test_intent_confidence_rejects_out_of_range(value):
    with pytest.raises(ValueError):
        _intent(confidence=value)


@pytest.mark.parametrize("value", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_intent_confidence_accepts_in_range(value):
    i = _intent(confidence=value)
    assert i.confidence == float(value)


def test_intent_confidence_rejects_bool_true():
    with pytest.raises(ValueError):
        _intent(confidence=True)  # type: ignore[arg-type]


def test_intent_confidence_rejects_bool_false():
    with pytest.raises(ValueError):
        _intent(confidence=False)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["0.5", None, [0.5], {"x": 0.5}])
def test_intent_confidence_rejects_non_numeric(value):
    with pytest.raises((TypeError, ValueError)):
        _intent(confidence=value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "tuple_field",
    [
        "evidence_selected_observation_set_ids",
        "evidence_market_readout_ids",
        "evidence_market_condition_ids",
        "evidence_market_environment_state_ids",
        "evidence_firm_state_ids",
        "evidence_valuation_ids",
        "evidence_dialogue_ids",
        "evidence_escalation_candidate_ids",
        "evidence_stewardship_theme_ids",
    ],
)
def test_intent_rejects_empty_strings_in_tuple_fields(tuple_field):
    bad = {tuple_field: ("valid", "")}
    with pytest.raises(ValueError):
        _intent(**bad)


def test_intent_coerces_as_of_date_to_iso_string():
    i = _intent(as_of_date=date(2026, 3, 31))
    assert i.as_of_date == "2026-03-31"


# ---------------------------------------------------------------------------
# Immutability & round-trip
# ---------------------------------------------------------------------------


def test_intent_is_frozen():
    i = _intent()
    with pytest.raises(Exception):
        i.intent_id = "tampered"  # type: ignore[misc]


def test_intent_to_dict_round_trips_fields():
    i = _intent(
        evidence_selected_observation_set_ids=("selection:a",),
        evidence_market_readout_ids=("readout:a",),
        evidence_firm_state_ids=("firm_state:a",),
        evidence_valuation_ids=("valuation:a",),
        evidence_dialogue_ids=("dialogue:a",),
        evidence_escalation_candidate_ids=("escalation:a",),
        evidence_stewardship_theme_ids=("theme:a",),
        metadata={"note": "synthetic"},
    )
    out = i.to_dict()
    assert out["intent_id"] == i.intent_id
    assert out["investor_id"] == i.investor_id
    assert out["target_company_id"] == i.target_company_id
    assert out["as_of_date"] == i.as_of_date
    assert out["intent_type"] == i.intent_type
    assert out["intent_direction"] == i.intent_direction
    assert out["confidence"] == i.confidence
    assert out["evidence_selected_observation_set_ids"] == ["selection:a"]
    assert out["evidence_market_readout_ids"] == ["readout:a"]
    assert out["evidence_firm_state_ids"] == ["firm_state:a"]
    assert out["evidence_valuation_ids"] == ["valuation:a"]
    assert out["evidence_dialogue_ids"] == ["dialogue:a"]
    assert out["evidence_escalation_candidate_ids"] == ["escalation:a"]
    assert out["evidence_stewardship_theme_ids"] == ["theme:a"]
    assert out["metadata"] == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# Anti-fields — no order/trade/rebalance/recommendation/etc.
# ---------------------------------------------------------------------------


def test_intent_record_has_no_order_or_recommendation_field():
    """v1.12.1 investor intent record must store labels only —
    never order / trade / rebalance / target weight / expected
    return / target price / recommendation / investment advice /
    portfolio allocation / execution. The v1.12.1 anti-fields
    list is the binding contract this test pins."""
    field_names = {f.name for f in dataclass_fields(InvestorIntentRecord)}
    forbidden = {
        "order",
        "order_id",
        "trade",
        "buy",
        "sell",
        "rebalance",
        "target_weight",
        "overweight",
        "underweight",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        "portfolio_allocation",
        "execution",
    }
    leaked = field_names & forbidden
    assert not leaked, (
        f"v1.12.1 investor intent record must not carry order / trade / "
        f"rebalance / recommendation / execution fields; "
        f"found: {sorted(leaked)}"
    )


# ---------------------------------------------------------------------------
# Book — add / get / dedup / unknown
# ---------------------------------------------------------------------------


def test_add_and_get_intent():
    book = InvestorIntentBook()
    i = _intent()
    book.add_intent(i)
    assert book.get_intent(i.intent_id) is i


def test_get_intent_unknown_raises():
    book = InvestorIntentBook()
    with pytest.raises(UnknownInvestorIntentError):
        book.get_intent("does-not-exist")


def test_unknown_intent_error_is_keyerror():
    err = UnknownInvestorIntentError("missing")
    assert isinstance(err, KeyError)


def test_duplicate_intent_id_rejected():
    book = InvestorIntentBook()
    book.add_intent(_intent(intent_id="intent:dup"))
    with pytest.raises(DuplicateInvestorIntentError):
        book.add_intent(_intent(intent_id="intent:dup"))


def test_add_intent_returns_record():
    book = InvestorIntentBook()
    i = _intent()
    returned = book.add_intent(i)
    assert returned is i


# ---------------------------------------------------------------------------
# Listings & filters
# ---------------------------------------------------------------------------


def test_list_intents_in_insertion_order():
    book = InvestorIntentBook()
    book.add_intent(_intent(intent_id="intent:a"))
    book.add_intent(_intent(intent_id="intent:b"))
    book.add_intent(_intent(intent_id="intent:c"))
    listed = book.list_intents()
    assert tuple(i.intent_id for i in listed) == (
        "intent:a", "intent:b", "intent:c",
    )


def test_list_intents_empty_book():
    assert InvestorIntentBook().list_intents() == ()


def test_list_by_investor():
    book = InvestorIntentBook()
    book.add_intent(
        _intent(intent_id="intent:1", investor_id="investor:a")
    )
    book.add_intent(
        _intent(intent_id="intent:2", investor_id="investor:b")
    )
    book.add_intent(
        _intent(intent_id="intent:3", investor_id="investor:a")
    )
    matched = book.list_by_investor("investor:a")
    assert tuple(i.intent_id for i in matched) == ("intent:1", "intent:3")


def test_list_by_target_company():
    book = InvestorIntentBook()
    book.add_intent(
        _intent(intent_id="intent:m", target_company_id="firm:m")
    )
    book.add_intent(
        _intent(intent_id="intent:r", target_company_id="firm:r")
    )
    matched = book.list_by_target_company("firm:m")
    assert tuple(i.intent_id for i in matched) == ("intent:m",)


def test_list_by_intent_type():
    book = InvestorIntentBook()
    book.add_intent(
        _intent(intent_id="intent:wa", intent_type="watch_adjustment")
    )
    book.add_intent(
        _intent(intent_id="intent:rr", intent_type="risk_review")
    )
    book.add_intent(
        _intent(intent_id="intent:wa2", intent_type="watch_adjustment")
    )
    matched = book.list_by_intent_type("watch_adjustment")
    assert tuple(i.intent_id for i in matched) == ("intent:wa", "intent:wa2")


def test_list_by_intent_direction():
    book = InvestorIntentBook()
    for d in (
        "increase_watch",
        "decrease_confidence",
        "engagement_watch",
        "hold_review",
        "risk_flag_watch",
        "deepen_due_diligence",
        "coverage_review",
    ):
        book.add_intent(_intent(intent_id=f"intent:{d}", intent_direction=d))
    for d in (
        "increase_watch",
        "decrease_confidence",
        "engagement_watch",
        "hold_review",
        "risk_flag_watch",
        "deepen_due_diligence",
        "coverage_review",
    ):
        matched = book.list_by_intent_direction(d)
        assert tuple(i.intent_id for i in matched) == (f"intent:{d}",)


def test_list_by_status():
    book = InvestorIntentBook()
    book.add_intent(_intent(intent_id="intent:active", status="active"))
    book.add_intent(_intent(intent_id="intent:retired", status="retired"))
    matched = book.list_by_status("active")
    assert tuple(i.intent_id for i in matched) == ("intent:active",)


def test_list_by_date_filters_exactly():
    book = InvestorIntentBook()
    book.add_intent(_intent(intent_id="intent:mar", as_of_date="2026-03-31"))
    book.add_intent(_intent(intent_id="intent:jun", as_of_date="2026-06-30"))
    mar = book.list_by_date("2026-03-31")
    assert tuple(i.intent_id for i in mar) == ("intent:mar",)
    assert book.list_by_date("2026-09-30") == ()


def test_list_by_date_accepts_date_object():
    book = InvestorIntentBook()
    book.add_intent(_intent(intent_id="intent:mar", as_of_date="2026-03-31"))
    matched = book.list_by_date(date(2026, 3, 31))
    assert tuple(i.intent_id for i in matched) == ("intent:mar",)


# ---------------------------------------------------------------------------
# Snapshot determinism
# ---------------------------------------------------------------------------


def test_snapshot_is_deterministic_and_sorted():
    book = InvestorIntentBook()
    book.add_intent(_intent(intent_id="intent:z"))
    book.add_intent(_intent(intent_id="intent:a"))
    book.add_intent(_intent(intent_id="intent:m"))

    snap1 = book.snapshot()
    snap2 = book.snapshot()
    assert snap1 == snap2
    assert snap1["intent_count"] == 3
    assert [i["intent_id"] for i in snap1["intents"]] == [
        "intent:a", "intent:m", "intent:z",
    ]


def test_snapshot_empty_book():
    snap = InvestorIntentBook().snapshot()
    assert snap == {"intent_count": 0, "intents": []}


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_type_exists():
    assert (
        RecordType("investor_intent_signal_added")
        is RecordType.INVESTOR_INTENT_SIGNAL_ADDED
    )
    assert (
        RecordType.INVESTOR_INTENT_SIGNAL_ADDED.value
        == "investor_intent_signal_added"
    )


def test_add_intent_writes_exactly_one_ledger_record():
    ledger = Ledger()
    book = InvestorIntentBook(ledger=ledger)
    book.add_intent(_intent(intent_id="intent:emit"))
    records = ledger.filter(event_type="investor_intent_signal_added")
    assert len(records) == 1
    record = records[0]
    assert record.record_type is RecordType.INVESTOR_INTENT_SIGNAL_ADDED
    assert record.object_id == "intent:emit"
    assert record.source == "investor:reference_pension_a"
    assert record.target == "firm:reference_manufacturer_a"
    assert record.space_id == "investor_intent"
    assert record.visibility == "internal_only"
    assert record.confidence == 0.5


def test_add_intent_payload_carries_full_field_set():
    ledger = Ledger()
    book = InvestorIntentBook(ledger=ledger)
    book.add_intent(
        _intent(
            intent_id="intent:payload",
            evidence_selected_observation_set_ids=("selection:a",),
            evidence_market_readout_ids=("readout:a",),
            evidence_firm_state_ids=("firm_state:a",),
            evidence_valuation_ids=("valuation:a",),
            evidence_dialogue_ids=("dialogue:a",),
            evidence_escalation_candidate_ids=("escalation:a",),
            evidence_stewardship_theme_ids=("theme:a",),
        )
    )
    payload = ledger.filter(
        event_type="investor_intent_signal_added"
    )[-1].payload
    assert payload["intent_id"] == "intent:payload"
    assert payload["investor_id"] == "investor:reference_pension_a"
    assert payload["target_company_id"] == "firm:reference_manufacturer_a"
    assert payload["as_of_date"] == "2026-03-31"
    assert payload["intent_type"] == "watch_adjustment"
    assert payload["intent_direction"] == "hold_review"
    assert payload["priority"] == "medium"
    assert payload["horizon"] == "medium_term"
    assert payload["status"] == "active"
    assert payload["visibility"] == "internal_only"
    assert payload["confidence"] == 0.5
    assert tuple(payload["evidence_selected_observation_set_ids"]) == (
        "selection:a",
    )
    assert tuple(payload["evidence_market_readout_ids"]) == ("readout:a",)
    assert tuple(payload["evidence_firm_state_ids"]) == ("firm_state:a",)
    assert tuple(payload["evidence_valuation_ids"]) == ("valuation:a",)
    assert tuple(payload["evidence_dialogue_ids"]) == ("dialogue:a",)
    assert tuple(payload["evidence_escalation_candidate_ids"]) == (
        "escalation:a",
    )
    assert tuple(payload["evidence_stewardship_theme_ids"]) == ("theme:a",)


def test_add_intent_payload_carries_no_order_or_recommendation_keys():
    ledger = Ledger()
    book = InvestorIntentBook(ledger=ledger)
    book.add_intent(_intent(intent_id="intent:audit"))
    payload_keys = set(
        ledger.filter(
            event_type="investor_intent_signal_added"
        )[-1].payload.keys()
    )
    forbidden = {
        "order",
        "order_id",
        "trade",
        "buy",
        "sell",
        "rebalance",
        "target_weight",
        "overweight",
        "underweight",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        "portfolio_allocation",
        "execution",
    }
    leaked = payload_keys & forbidden
    assert not leaked, (
        f"v1.12.1 investor intent payload must not carry order / "
        f"trade / rebalance / recommendation / execution keys; "
        f"found: {sorted(leaked)}"
    )


def test_add_intent_without_ledger_does_not_raise():
    book = InvestorIntentBook()
    book.add_intent(_intent())


def test_duplicate_add_emits_no_extra_ledger_record():
    ledger = Ledger()
    book = InvestorIntentBook(ledger=ledger)
    book.add_intent(_intent(intent_id="intent:once"))
    with pytest.raises(DuplicateInvestorIntentError):
        book.add_intent(_intent(intent_id="intent:once"))
    assert (
        len(ledger.filter(event_type="investor_intent_signal_added"))
        == 1
    )


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_investor_intents_book():
    kernel = _kernel()
    assert isinstance(kernel.investor_intents, InvestorIntentBook)
    assert kernel.investor_intents.ledger is kernel.ledger
    assert kernel.investor_intents.clock is kernel.clock


def test_kernel_add_intent_emits_to_kernel_ledger():
    kernel = _kernel()
    kernel.investor_intents.add_intent(_intent())
    records = kernel.ledger.filter(event_type="investor_intent_signal_added")
    assert len(records) == 1


def test_kernel_intent_simulation_date_uses_clock():
    kernel = _kernel()
    kernel.investor_intents.add_intent(_intent(intent_id="intent:wired"))
    records = kernel.ledger.filter(event_type="investor_intent_signal_added")
    assert records[-1].simulation_date == "2026-01-01"


# ---------------------------------------------------------------------------
# No-mutation guarantee against every other source-of-truth book
# ---------------------------------------------------------------------------


def test_investor_intents_book_does_not_mutate_other_kernel_books():
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
    }

    kernel.investor_intents.add_intent(_intent(intent_id="intent:k:a"))
    kernel.investor_intents.add_intent(
        _intent(
            intent_id="intent:k:b",
            investor_id="investor:b",
            target_company_id="firm:b",
            as_of_date="2026-04-15",
            intent_direction="risk_flag_watch",
            intent_type="risk_review",
        )
    )
    kernel.investor_intents.list_intents()
    kernel.investor_intents.list_by_investor("investor:reference_pension_a")
    kernel.investor_intents.list_by_target_company(
        "firm:reference_manufacturer_a"
    )
    kernel.investor_intents.list_by_intent_type("watch_adjustment")
    kernel.investor_intents.list_by_intent_direction("hold_review")
    kernel.investor_intents.list_by_status("active")
    kernel.investor_intents.list_by_date("2026-03-31")
    kernel.investor_intents.snapshot()

    for name, before in snaps_before.items():
        after = getattr(kernel, name).snapshot()
        assert after == before, f"book {name!r} was mutated"


# ---------------------------------------------------------------------------
# No-action invariant
# ---------------------------------------------------------------------------


def test_investor_intents_emits_only_intent_signal_added_records():
    ledger = Ledger()
    book = InvestorIntentBook(ledger=ledger)
    book.add_intent(_intent(intent_id="intent:audit"))
    assert len(ledger.records) == 1
    record = ledger.records[0]
    assert record.record_type is RecordType.INVESTOR_INTENT_SIGNAL_ADDED


def test_investor_intents_does_not_emit_action_or_pricing_records():
    """v1.12.1 add_intent must not emit any action / pricing /
    contract-mutation / firm-state / order / trade record."""
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
        "firm_latent_state_updated",
    }
    ledger = Ledger()
    book = InvestorIntentBook(ledger=ledger)
    book.add_intent(_intent(intent_id="intent:no_action"))
    seen = {r.event_type for r in ledger.records}
    assert seen.isdisjoint(forbidden_event_types), (
        f"v1.12.1 add_intent must not emit any action / pricing / "
        f"contract-mutation / firm-state record; saw forbidden "
        f"event types: {sorted(seen & forbidden_event_types)}"
    )


# ---------------------------------------------------------------------------
# Helper — deterministic rule set
# ---------------------------------------------------------------------------


def test_helper_returns_result_with_record_added_to_book():
    kernel = _kernel()
    result = run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
    )
    assert isinstance(result, InvestorIntentSignalResult)
    assert (
        kernel.investor_intents.get_intent(result.intent_id)
        is result.record
    )


def test_helper_is_idempotent_on_intent_id():
    kernel = _kernel()
    r1 = run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
    )
    r2 = run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
    )
    assert r1.record is r2.record
    assert (
        len(kernel.ledger.filter(event_type="investor_intent_signal_added"))
        == 1
    )


def test_helper_default_no_evidence_yields_hold_review():
    """No evidence → rule 5 fires → hold_review."""
    kernel = _kernel()
    r = run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
    )
    assert r.intent_direction == "hold_review"
    assert r.record.intent_type == "watch_adjustment"


def test_helper_engagement_evidence_yields_engagement_watch():
    """Dialogue or escalation evidence (without higher-priority
    triggers) → rule 4 fires → engagement_watch."""
    kernel = _kernel()
    r = run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        dialogue_ids=("dialogue:a",),
    )
    assert r.intent_direction == "engagement_watch"
    assert r.record.intent_type == "engagement_review"


def test_helper_constrained_market_yields_risk_flag_watch():
    """Selective_or_constrained readout (without high-pressure
    firm state) → rule 2 fires → risk_flag_watch."""
    kernel = _kernel()
    readout_id, _ = _seed_default_market_surface(
        kernel,
        as_of_date="2026-03-31",
        regime_overall="selective_or_constrained",
    )
    r = run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
    )
    assert r.intent_direction == "risk_flag_watch"
    assert r.record.intent_type == "risk_review"


def test_helper_high_funding_need_yields_deepen_due_diligence():
    """Firm funding_need_intensity ≥ 0.7 → rule 1 fires →
    deepen_due_diligence (highest priority)."""
    kernel = _kernel()
    fsid = _seed_firm_state(
        kernel,
        state_id="firm_state:high_funding",
        funding_need_intensity=0.75,
        market_access_pressure=0.65,
    )
    # Even with engagement evidence, rule 1 must win.
    r = run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        firm_state_ids=(fsid,),
        dialogue_ids=("dialogue:a",),
    )
    assert r.intent_direction == "deepen_due_diligence"
    assert r.record.intent_type == "risk_review"


def test_helper_low_valuation_confidence_yields_decrease_confidence():
    """Low valuation confidence (< 0.4) without higher-priority
    triggers → rule 3 fires → decrease_confidence."""
    from world.valuations import ValuationRecord

    kernel = _kernel()
    kernel.valuations.add_valuation(
        ValuationRecord(
            valuation_id="valuation:low_conf",
            subject_id="firm:reference_manufacturer_a",
            valuer_id="investor:reference_pension_a",
            valuation_type="reference_synthetic",
            purpose="reference_synthetic_purpose",
            method="dcf",
            as_of_date="2026-03-31",
            estimated_value=100.0,
            currency="reference_unit",
            confidence=0.2,
        )
    )
    r = run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        valuation_ids=("valuation:low_conf",),
    )
    assert r.intent_direction == "decrease_confidence"
    assert r.record.intent_type == "confidence_adjustment"


def test_helper_priority_order_high_funding_need_beats_engagement():
    """When both rule 1 (high funding_need) and rule 4
    (engagement) match, rule 1 wins per the documented priority
    order."""
    kernel = _kernel()
    fsid = _seed_firm_state(
        kernel,
        state_id="firm_state:high_funding",
        funding_need_intensity=0.8,
    )
    r = run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        firm_state_ids=(fsid,),
        dialogue_ids=("dialogue:a",),
        escalation_candidate_ids=("escalation:a",),
    )
    assert r.intent_direction == "deepen_due_diligence"


def test_helper_priority_order_constrained_market_beats_engagement():
    """When rule 2 (restrictive market) matches alongside rule 4
    (engagement), rule 2 wins."""
    kernel = _kernel()
    readout_id, _ = _seed_default_market_surface(
        kernel,
        as_of_date="2026-03-31",
        regime_overall="selective_or_constrained",
    )
    r = run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        dialogue_ids=("dialogue:a",),
    )
    assert r.intent_direction == "risk_flag_watch"


def test_helper_constructive_vs_constrained_yields_different_labels():
    """Headline endogenous-readability test: identical caller +
    identical engagement evidence, but constructive readout vs
    constrained readout produces different intent_direction."""
    k_constructive = _kernel()
    rid_c, _ = _seed_default_market_surface(
        k_constructive,
        as_of_date="2026-03-31",
        regime_overall="open_or_constructive",
    )
    r_constructive = run_reference_investor_intent_signal(
        k_constructive,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(rid_c,),
        dialogue_ids=("dialogue:a",),
    )

    k_constrained = _kernel()
    rid_x, _ = _seed_default_market_surface(
        k_constrained,
        as_of_date="2026-03-31",
        regime_overall="selective_or_constrained",
    )
    r_constrained = run_reference_investor_intent_signal(
        k_constrained,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(rid_x,),
        dialogue_ids=("dialogue:a",),
    )
    assert r_constructive.intent_direction == "engagement_watch"
    assert r_constrained.intent_direction == "risk_flag_watch"


def test_helper_records_evidence_id_tuples():
    """The intent record must carry the cited evidence id tuples
    so the v1.12.1 attention discipline (downstream consumers
    can re-walk the same evidence) is enforceable."""
    kernel = _kernel()
    r = run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        selected_observation_set_ids=("selection:a",),
        firm_state_ids=("firm_state:a",),
        valuation_ids=("valuation:a",),
        dialogue_ids=("dialogue:a",),
        escalation_candidate_ids=("escalation:a",),
        stewardship_theme_ids=("theme:a",),
    )
    assert r.record.evidence_selected_observation_set_ids == ("selection:a",)
    assert r.record.evidence_firm_state_ids == ("firm_state:a",)
    assert r.record.evidence_valuation_ids == ("valuation:a",)
    assert r.record.evidence_dialogue_ids == ("dialogue:a",)
    assert r.record.evidence_escalation_candidate_ids == ("escalation:a",)
    assert r.record.evidence_stewardship_theme_ids == ("theme:a",)


def test_helper_records_v1122_market_environment_evidence_id_tuple():
    """v1.12.2: the helper accepts a
    ``market_environment_state_ids`` kwarg and stores the tuple
    on the produced record's
    ``evidence_market_environment_state_ids`` slot. The slot is
    additive — pre-v1.12.2 callers (without the kwarg) still get
    an empty tuple."""
    kernel = _kernel()
    r = run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_environment_state_ids=("market_environment:2026-03-31",),
    )
    assert r.record.evidence_market_environment_state_ids == (
        "market_environment:2026-03-31",
    )


def test_helper_default_records_empty_market_environment_evidence():
    kernel = _kernel()
    r = run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
    )
    assert r.record.evidence_market_environment_state_ids == ()


def test_helper_does_not_mutate_evidence_books():
    kernel = _kernel()
    readout_id, cids = _seed_default_market_surface(
        kernel, as_of_date="2026-03-31", regime_overall="open_or_constructive"
    )
    fsid = _seed_firm_state(kernel, state_id="firm_state:e")
    snaps_before = {
        "market_conditions": kernel.market_conditions.snapshot(),
        "capital_market_readouts": kernel.capital_market_readouts.snapshot(),
        "firm_financial_states": kernel.firm_financial_states.snapshot(),
    }
    run_reference_investor_intent_signal(
        kernel,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(readout_id,),
        market_condition_ids=cids,
        firm_state_ids=(fsid,),
        dialogue_ids=("dialogue:a",),
    )
    for name, before in snaps_before.items():
        after = getattr(kernel, name).snapshot()
        assert after == before, f"book {name!r} was mutated by helper"


def test_helper_deterministic_for_identical_inputs():
    """Two fresh kernels with identical evidence must produce
    byte-identical record output."""
    k1 = _kernel()
    rid1, _ = _seed_default_market_surface(
        k1, as_of_date="2026-03-31", regime_overall="open_or_constructive"
    )
    r1 = run_reference_investor_intent_signal(
        k1,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(rid1,),
    )
    k2 = _kernel()
    rid2, _ = _seed_default_market_surface(
        k2, as_of_date="2026-03-31", regime_overall="open_or_constructive"
    )
    r2 = run_reference_investor_intent_signal(
        k2,
        investor_id="investor:reference_pension_a",
        target_company_id="firm:reference_manufacturer_a",
        as_of_date="2026-03-31",
        market_readout_ids=(rid2,),
    )
    assert r1.record.to_dict() == r2.record.to_dict()


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


def test_investor_intent_module_contains_no_jurisdiction_specific_identifiers():
    import re
    from pathlib import Path

    module_path = (
        Path(__file__).resolve().parent.parent / "world" / "investor_intent.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"jurisdiction-specific token {token!r} appeared in "
            f"world/investor_intent.py"
        )
