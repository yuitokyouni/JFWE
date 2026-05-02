"""
Tests for v1.13.3 InterbankLiquidityStateRecord +
InterbankLiquidityStateBook.
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
from datetime import date

import pytest

from world.clock import Clock
from world.interbank_liquidity import (
    DuplicateInterbankLiquidityStateError,
    InterbankLiquidityStateBook,
    InterbankLiquidityStateRecord,
    UnknownInterbankLiquidityStateError,
)
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State


def _kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 3, 31)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _state(
    *,
    liquidity_state_id: str = "interbank_liquidity_state:reference_a:2026-03-31",
    institution_id: str = "institution:reference_megabank_a",
    as_of_date: str = "2026-03-31",
    liquidity_regime: str = "normal",
    settlement_pressure: str = "low",
    reserve_access_label: str = "available",
    funding_stress_label: str = "low",
    status: str = "active",
    visibility: str = "internal_only",
    confidence: float = 0.5,
    source_settlement_account_ids: tuple[str, ...] = (),
    source_payment_instruction_ids: tuple[str, ...] = (),
    source_settlement_event_ids: tuple[str, ...] = (),
    source_market_environment_state_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> InterbankLiquidityStateRecord:
    return InterbankLiquidityStateRecord(
        liquidity_state_id=liquidity_state_id,
        institution_id=institution_id,
        as_of_date=as_of_date,
        liquidity_regime=liquidity_regime,
        settlement_pressure=settlement_pressure,
        reserve_access_label=reserve_access_label,
        funding_stress_label=funding_stress_label,
        status=status,
        visibility=visibility,
        confidence=confidence,
        source_settlement_account_ids=source_settlement_account_ids,
        source_payment_instruction_ids=source_payment_instruction_ids,
        source_settlement_event_ids=source_settlement_event_ids,
        source_market_environment_state_ids=source_market_environment_state_ids,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Record — required-field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"liquidity_state_id": ""},
        {"institution_id": ""},
        {"as_of_date": ""},
        {"liquidity_regime": ""},
        {"settlement_pressure": ""},
        {"reserve_access_label": ""},
        {"funding_stress_label": ""},
        {"status": ""},
        {"visibility": ""},
    ],
)
def test_state_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _state(**kwargs)


def test_state_coerces_date_to_iso_string():
    s = _state(as_of_date=date(2026, 3, 31))
    assert s.as_of_date == "2026-03-31"


def test_state_is_frozen():
    s = _state()
    with pytest.raises(Exception):
        s.liquidity_state_id = "tampered"  # type: ignore[misc]


def test_state_to_dict_round_trips():
    s = _state(
        source_settlement_account_ids=("settlement_account:a",),
        source_payment_instruction_ids=("payment_instruction:a",),
        source_settlement_event_ids=("settlement_event:a",),
        source_market_environment_state_ids=("market_environment_state:a",),
        metadata={"note": "synthetic"},
    )
    out = s.to_dict()
    assert out["source_settlement_account_ids"] == ["settlement_account:a"]
    assert out["source_payment_instruction_ids"] == ["payment_instruction:a"]
    assert out["source_settlement_event_ids"] == ["settlement_event:a"]
    assert out["source_market_environment_state_ids"] == [
        "market_environment_state:a"
    ]
    assert out["metadata"] == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


def test_state_rejects_bool_confidence():
    with pytest.raises(ValueError):
        _state(confidence=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        _state(confidence=False)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [-0.01, 1.01, -1.0, 2.0])
def test_state_rejects_out_of_range_confidence(bad):
    with pytest.raises(ValueError):
        _state(confidence=bad)


@pytest.mark.parametrize("good", [0.0, 0.5, 1.0])
def test_state_accepts_in_range_confidence(good):
    s = _state(confidence=good)
    assert s.confidence == float(good)


def test_state_rejects_non_numeric_confidence():
    with pytest.raises(ValueError):
        _state(confidence="0.5")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tuple normalisation
# ---------------------------------------------------------------------------


def test_state_rejects_empty_strings_in_source_tuples():
    with pytest.raises(ValueError):
        _state(source_settlement_account_ids=("",))
    with pytest.raises(ValueError):
        _state(source_payment_instruction_ids=("valid", ""))
    with pytest.raises(ValueError):
        _state(source_settlement_event_ids=("",))
    with pytest.raises(ValueError):
        _state(source_market_environment_state_ids=("",))


def test_state_normalises_source_tuples_from_iterable():
    s = _state(
        source_settlement_account_ids=iter(["a", "b"]),
    )
    assert s.source_settlement_account_ids == ("a", "b")


# ---------------------------------------------------------------------------
# Recommended label sets (pinned but not enforced)
# ---------------------------------------------------------------------------


_RECOMMENDED_LIQUIDITY_REGIMES = (
    "ample", "normal", "tight", "stressed", "unknown",
)
_RECOMMENDED_SETTLEMENT_PRESSURES = (
    "low", "moderate", "high", "severe", "unknown",
)
_RECOMMENDED_RESERVE_ACCESS = ("available", "constrained", "unknown")
_RECOMMENDED_FUNDING_STRESS = (
    "low", "moderate", "elevated", "stressed", "unknown",
)


@pytest.mark.parametrize("label", _RECOMMENDED_LIQUIDITY_REGIMES)
def test_recommended_liquidity_regimes_accepted(label):
    s = _state(liquidity_regime=label)
    assert s.liquidity_regime == label


@pytest.mark.parametrize("label", _RECOMMENDED_SETTLEMENT_PRESSURES)
def test_recommended_settlement_pressures_accepted(label):
    s = _state(settlement_pressure=label)
    assert s.settlement_pressure == label


@pytest.mark.parametrize("label", _RECOMMENDED_RESERVE_ACCESS)
def test_recommended_reserve_access_accepted(label):
    s = _state(reserve_access_label=label)
    assert s.reserve_access_label == label


@pytest.mark.parametrize("label", _RECOMMENDED_FUNDING_STRESS)
def test_recommended_funding_stress_accepted(label):
    s = _state(funding_stress_label=label)
    assert s.funding_stress_label == label


# ---------------------------------------------------------------------------
# Anti-fields
# ---------------------------------------------------------------------------


_FORBIDDEN_FIELDS = {
    "amount",
    "currency_value",
    "fx_rate",
    "balance",
    "debit",
    "credit",
    "policy_rate",
    "interest",
    "order",
    "trade",
    "recommendation",
    "investment_advice",
    "forecast_value",
    "actual_value",
    "real_data_value",
    "behavior_probability",
    "default_probability",
    "lending_decision",
    "loan_amount",
    "reserve_balance",
}


def test_state_record_has_no_anti_fields():
    field_names = {
        f.name for f in dataclass_fields(InterbankLiquidityStateRecord)
    }
    leaked = field_names & _FORBIDDEN_FIELDS
    assert not leaked


# ---------------------------------------------------------------------------
# Book — CRUD
# ---------------------------------------------------------------------------


def test_book_add_and_get_state():
    book = InterbankLiquidityStateBook()
    s = _state()
    book.add_state(s)
    assert book.get_state(s.liquidity_state_id) is s


def test_book_get_unknown_state_raises():
    book = InterbankLiquidityStateBook()
    with pytest.raises(UnknownInterbankLiquidityStateError):
        book.get_state("interbank_liquidity_state:missing")
    with pytest.raises(KeyError):
        book.get_state("interbank_liquidity_state:missing")


def test_book_duplicate_state_id_rejected():
    book = InterbankLiquidityStateBook()
    book.add_state(_state())
    with pytest.raises(DuplicateInterbankLiquidityStateError):
        book.add_state(_state())


def test_book_list_states_returns_all():
    book = InterbankLiquidityStateBook()
    book.add_state(_state(liquidity_state_id="interbank_liquidity_state:a"))
    book.add_state(_state(liquidity_state_id="interbank_liquidity_state:b"))
    assert len(book.list_states()) == 2


def test_book_list_by_institution():
    book = InterbankLiquidityStateBook()
    book.add_state(
        _state(
            liquidity_state_id="interbank_liquidity_state:a",
            institution_id="institution:p1",
        )
    )
    book.add_state(
        _state(
            liquidity_state_id="interbank_liquidity_state:b",
            institution_id="institution:p2",
        )
    )
    out = book.list_by_institution("institution:p1")
    assert len(out) == 1
    assert out[0].institution_id == "institution:p1"


def test_book_list_by_date():
    book = InterbankLiquidityStateBook()
    book.add_state(
        _state(
            liquidity_state_id="interbank_liquidity_state:a",
            as_of_date="2026-03-31",
        )
    )
    book.add_state(
        _state(
            liquidity_state_id="interbank_liquidity_state:b",
            as_of_date="2026-04-30",
        )
    )
    out = book.list_by_date("2026-04-30")
    assert len(out) == 1


def test_book_list_by_date_accepts_date_object():
    book = InterbankLiquidityStateBook()
    book.add_state(_state(as_of_date="2026-03-31"))
    out = book.list_by_date(date(2026, 3, 31))
    assert len(out) == 1


def test_book_list_by_liquidity_regime():
    book = InterbankLiquidityStateBook()
    book.add_state(
        _state(
            liquidity_state_id="interbank_liquidity_state:a",
            liquidity_regime="ample",
        )
    )
    book.add_state(
        _state(
            liquidity_state_id="interbank_liquidity_state:b",
            liquidity_regime="tight",
        )
    )
    out = book.list_by_liquidity_regime("tight")
    assert len(out) == 1


def test_book_get_latest_for_institution():
    book = InterbankLiquidityStateBook()
    s1 = _state(
        liquidity_state_id="interbank_liquidity_state:a",
        institution_id="institution:p1",
        as_of_date="2026-03-31",
    )
    s2 = _state(
        liquidity_state_id="interbank_liquidity_state:b",
        institution_id="institution:p1",
        as_of_date="2026-04-30",
    )
    book.add_state(s1)
    book.add_state(s2)
    assert book.get_latest_for_institution("institution:p1") is s2


def test_book_get_latest_for_unknown_institution_returns_none():
    book = InterbankLiquidityStateBook()
    assert book.get_latest_for_institution("institution:missing") is None


def test_book_snapshot_is_deterministic_and_sorted():
    book = InterbankLiquidityStateBook()
    book.add_state(_state(liquidity_state_id="interbank_liquidity_state:b"))
    book.add_state(_state(liquidity_state_id="interbank_liquidity_state:a"))
    snap = book.snapshot()
    assert snap["state_count"] == 2
    assert [s["liquidity_state_id"] for s in snap["states"]] == [
        "interbank_liquidity_state:a",
        "interbank_liquidity_state:b",
    ]


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_type_exists():
    assert (
        RecordType.INTERBANK_LIQUIDITY_STATE_RECORDED.value
        == "interbank_liquidity_state_recorded"
    )


def test_add_state_writes_one_ledger_record():
    ledger = Ledger()
    book = InterbankLiquidityStateBook(ledger=ledger)
    book.add_state(_state())
    assert len(ledger.records) == 1
    rec = ledger.records[0]
    assert rec.record_type is RecordType.INTERBANK_LIQUIDITY_STATE_RECORDED
    assert rec.space_id == "interbank_liquidity"


def test_ledger_payload_carries_no_anti_field_keys():
    ledger = Ledger()
    book = InterbankLiquidityStateBook(ledger=ledger)
    book.add_state(_state())
    rec = ledger.records[0]
    leaked = set(rec.payload.keys()) & _FORBIDDEN_FIELDS
    assert not leaked


def test_ledger_payload_contains_label_fields():
    ledger = Ledger()
    book = InterbankLiquidityStateBook(ledger=ledger)
    book.add_state(_state())
    rec = ledger.records[0]
    assert rec.payload["liquidity_regime"] == "normal"
    assert rec.payload["settlement_pressure"] == "low"
    assert rec.payload["reserve_access_label"] == "available"
    assert rec.payload["funding_stress_label"] == "low"


def test_book_without_ledger_does_not_raise():
    book = InterbankLiquidityStateBook()
    book.add_state(_state())


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_interbank_liquidity_book():
    k = _kernel()
    assert isinstance(k.interbank_liquidity, InterbankLiquidityStateBook)
    assert k.interbank_liquidity.ledger is k.ledger
    assert k.interbank_liquidity.clock is k.clock


def test_kernel_simulation_date_uses_clock_for_state():
    k = _kernel()
    k.interbank_liquidity.add_state(_state())
    rec = k.ledger.records[-1]
    assert rec.simulation_date == "2026-03-31"


# ---------------------------------------------------------------------------
# No-mutation invariant
# ---------------------------------------------------------------------------


def test_book_does_not_mutate_other_kernel_books():
    k = _kernel()
    snaps_before = {
        "ownership": k.ownership.snapshot(),
        "contracts": k.contracts.snapshot(),
        "prices": k.prices.snapshot(),
        "constraints": k.constraints.snapshot(),
        "signals": k.signals.snapshot(),
        "valuations": k.valuations.snapshot(),
        "settlement_accounts": k.settlement_accounts.snapshot(),
        "settlement_payments": k.settlement_payments.snapshot(),
        "attention_feedback": k.attention_feedback.snapshot(),
        "investor_intents": k.investor_intents.snapshot(),
        "market_environments": k.market_environments.snapshot(),
        "firm_financial_states": k.firm_financial_states.snapshot(),
    }
    k.interbank_liquidity.add_state(_state())
    for name, before in snaps_before.items():
        assert getattr(k, name).snapshot() == before, name


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
        / "interbank_liquidity.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, token
