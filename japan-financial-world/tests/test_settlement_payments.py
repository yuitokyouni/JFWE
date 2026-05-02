"""
Tests for v1.13.2 PaymentInstructionRecord +
SettlementEventRecord + SettlementInstructionBook.
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
from datetime import date

import pytest

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.registry import Registry
from world.scheduler import Scheduler
from world.settlement_payments import (
    DuplicatePaymentInstructionError,
    DuplicateSettlementEventError,
    PaymentInstructionRecord,
    SettlementEventRecord,
    SettlementInstructionBook,
    UnknownPaymentInstructionError,
    UnknownSettlementEventError,
)
from world.state import State


def _kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 3, 31)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


def _instruction(
    *,
    instruction_id: str = "payment_instruction:reference_a",
    payer_account_id: str = "settlement_account:reference_megabank_a:reserve",
    payee_account_id: str = "settlement_account:reference_megabank_b:reserve",
    requested_settlement_date: str = "2026-03-31",
    synthetic_size_label: str = "reference_size_medium",
    instruction_type: str = "interbank_transfer",
    status: str = "queued",
    visibility: str = "internal_only",
    related_contract_ids: tuple[str, ...] = (),
    related_signal_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> PaymentInstructionRecord:
    return PaymentInstructionRecord(
        instruction_id=instruction_id,
        payer_account_id=payer_account_id,
        payee_account_id=payee_account_id,
        requested_settlement_date=requested_settlement_date,
        synthetic_size_label=synthetic_size_label,
        instruction_type=instruction_type,
        status=status,
        visibility=visibility,
        related_contract_ids=related_contract_ids,
        related_signal_ids=related_signal_ids,
        metadata=metadata or {},
    )


def _event(
    *,
    event_id: str = "settlement_event:reference_a:queued",
    instruction_id: str = "payment_instruction:reference_a",
    as_of_date: str = "2026-03-31",
    event_type: str = "settlement_queued",
    status: str = "queued",
    source_account_id: str = "settlement_account:reference_megabank_a:reserve",
    target_account_id: str = "settlement_account:reference_megabank_b:reserve",
    synthetic_size_label: str = "reference_size_medium",
    visibility: str = "internal_only",
    metadata: dict | None = None,
) -> SettlementEventRecord:
    return SettlementEventRecord(
        event_id=event_id,
        instruction_id=instruction_id,
        as_of_date=as_of_date,
        event_type=event_type,
        status=status,
        source_account_id=source_account_id,
        target_account_id=target_account_id,
        synthetic_size_label=synthetic_size_label,
        visibility=visibility,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# PaymentInstructionRecord — field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"instruction_id": ""},
        {"payer_account_id": ""},
        {"payee_account_id": ""},
        {"requested_settlement_date": ""},
        {"synthetic_size_label": ""},
        {"instruction_type": ""},
        {"status": ""},
        {"visibility": ""},
    ],
)
def test_instruction_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _instruction(**kwargs)


def test_instruction_coerces_date_to_iso_string():
    i = _instruction(requested_settlement_date=date(2026, 3, 31))
    assert i.requested_settlement_date == "2026-03-31"


def test_instruction_rejects_empty_strings_in_tuple_fields():
    with pytest.raises(ValueError):
        _instruction(related_contract_ids=("",))
    with pytest.raises(ValueError):
        _instruction(related_signal_ids=("valid", ""))


def test_instruction_is_frozen():
    i = _instruction()
    with pytest.raises(Exception):
        i.instruction_id = "tampered"  # type: ignore[misc]


def test_instruction_to_dict_round_trips():
    i = _instruction(
        related_contract_ids=("contract:a",),
        related_signal_ids=("signal:a",),
        metadata={"note": "synthetic"},
    )
    out = i.to_dict()
    assert out["related_contract_ids"] == ["contract:a"]
    assert out["related_signal_ids"] == ["signal:a"]
    assert out["metadata"] == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# SettlementEventRecord — field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"event_id": ""},
        {"instruction_id": ""},
        {"as_of_date": ""},
        {"event_type": ""},
        {"status": ""},
        {"source_account_id": ""},
        {"target_account_id": ""},
        {"synthetic_size_label": ""},
        {"visibility": ""},
    ],
)
def test_event_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _event(**kwargs)


def test_event_coerces_date_to_iso_string():
    e = _event(as_of_date=date(2026, 3, 31))
    assert e.as_of_date == "2026-03-31"


def test_event_is_frozen():
    e = _event()
    with pytest.raises(Exception):
        e.event_id = "tampered"  # type: ignore[misc]


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
}


def test_instruction_record_has_no_anti_fields():
    field_names = {f.name for f in dataclass_fields(PaymentInstructionRecord)}
    leaked = field_names & _FORBIDDEN_FIELDS
    assert not leaked


def test_event_record_has_no_anti_fields():
    field_names = {f.name for f in dataclass_fields(SettlementEventRecord)}
    leaked = field_names & _FORBIDDEN_FIELDS
    assert not leaked


# ---------------------------------------------------------------------------
# Book — instruction CRUD
# ---------------------------------------------------------------------------


def test_book_add_and_get_instruction():
    book = SettlementInstructionBook()
    i = _instruction()
    book.add_instruction(i)
    assert book.get_instruction(i.instruction_id) is i


def test_book_get_unknown_instruction_raises():
    book = SettlementInstructionBook()
    with pytest.raises(UnknownPaymentInstructionError):
        book.get_instruction("payment_instruction:missing")
    with pytest.raises(KeyError):
        book.get_instruction("payment_instruction:missing")


def test_book_duplicate_instruction_id_rejected():
    book = SettlementInstructionBook()
    book.add_instruction(_instruction())
    with pytest.raises(DuplicatePaymentInstructionError):
        book.add_instruction(_instruction())


def test_book_list_by_payer():
    book = SettlementInstructionBook()
    book.add_instruction(
        _instruction(
            instruction_id="payment_instruction:a",
            payer_account_id="settlement_account:p1",
        )
    )
    book.add_instruction(
        _instruction(
            instruction_id="payment_instruction:b",
            payer_account_id="settlement_account:p2",
        )
    )
    out = book.list_by_payer("settlement_account:p1")
    assert len(out) == 1


def test_book_list_by_payee():
    book = SettlementInstructionBook()
    book.add_instruction(
        _instruction(
            instruction_id="payment_instruction:a",
            payee_account_id="settlement_account:y1",
        )
    )
    book.add_instruction(
        _instruction(
            instruction_id="payment_instruction:b",
            payee_account_id="settlement_account:y2",
        )
    )
    out = book.list_by_payee("settlement_account:y2")
    assert len(out) == 1


def test_book_list_by_status():
    book = SettlementInstructionBook()
    book.add_instruction(
        _instruction(instruction_id="payment_instruction:a", status="queued")
    )
    book.add_instruction(
        _instruction(instruction_id="payment_instruction:b", status="settled")
    )
    out = book.list_by_status("settled")
    assert len(out) == 1


# ---------------------------------------------------------------------------
# Book — event CRUD
# ---------------------------------------------------------------------------


def test_book_add_and_get_event():
    book = SettlementInstructionBook()
    e = _event()
    book.add_event(e)
    assert book.get_event(e.event_id) is e


def test_book_duplicate_event_id_rejected():
    book = SettlementInstructionBook()
    book.add_event(_event())
    with pytest.raises(DuplicateSettlementEventError):
        book.add_event(_event())


def test_book_get_unknown_event_raises():
    book = SettlementInstructionBook()
    with pytest.raises(UnknownSettlementEventError):
        book.get_event("settlement_event:missing")
    with pytest.raises(KeyError):
        book.get_event("settlement_event:missing")


def test_book_list_events_by_instruction():
    book = SettlementInstructionBook()
    book.add_event(
        _event(
            event_id="settlement_event:a:1",
            instruction_id="payment_instruction:a",
        )
    )
    book.add_event(
        _event(
            event_id="settlement_event:b:1",
            instruction_id="payment_instruction:b",
        )
    )
    book.add_event(
        _event(
            event_id="settlement_event:a:2",
            instruction_id="payment_instruction:a",
            event_type="settlement_completed",
        )
    )
    a_events = book.list_events_by_instruction("payment_instruction:a")
    assert len(a_events) == 2
    b_events = book.list_events_by_instruction("payment_instruction:b")
    assert len(b_events) == 1


def test_book_snapshot_is_deterministic_and_sorted():
    book = SettlementInstructionBook()
    book.add_instruction(_instruction(instruction_id="payment_instruction:b"))
    book.add_instruction(_instruction(instruction_id="payment_instruction:a"))
    book.add_event(
        _event(
            event_id="settlement_event:b",
            instruction_id="payment_instruction:b",
        )
    )
    book.add_event(
        _event(
            event_id="settlement_event:a",
            instruction_id="payment_instruction:a",
        )
    )
    snap = book.snapshot()
    assert snap["instruction_count"] == 2
    assert [i["instruction_id"] for i in snap["instructions"]] == [
        "payment_instruction:a",
        "payment_instruction:b",
    ]
    assert snap["event_count"] == 2
    assert [e["event_id"] for e in snap["events"]] == [
        "settlement_event:a",
        "settlement_event:b",
    ]


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_types_exist():
    assert (
        RecordType.PAYMENT_INSTRUCTION_REGISTERED.value
        == "payment_instruction_registered"
    )
    assert (
        RecordType.SETTLEMENT_EVENT_RECORDED.value
        == "settlement_event_recorded"
    )


def test_add_instruction_writes_one_ledger_record():
    ledger = Ledger()
    book = SettlementInstructionBook(ledger=ledger)
    book.add_instruction(_instruction())
    assert len(ledger.records) == 1
    assert (
        ledger.records[0].record_type
        is RecordType.PAYMENT_INSTRUCTION_REGISTERED
    )


def test_add_event_writes_one_ledger_record():
    ledger = Ledger()
    book = SettlementInstructionBook(ledger=ledger)
    book.add_event(_event())
    assert len(ledger.records) == 1
    assert (
        ledger.records[0].record_type
        is RecordType.SETTLEMENT_EVENT_RECORDED
    )


def test_payloads_carry_no_anti_field_keys():
    ledger = Ledger()
    book = SettlementInstructionBook(ledger=ledger)
    book.add_instruction(_instruction())
    book.add_event(_event())
    for rec in ledger.records:
        leaked = set(rec.payload.keys()) & _FORBIDDEN_FIELDS
        assert not leaked


def test_book_without_ledger_does_not_raise():
    book = SettlementInstructionBook()
    book.add_instruction(_instruction())
    book.add_event(_event())


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_settlement_payments_book():
    k = _kernel()
    assert isinstance(k.settlement_payments, SettlementInstructionBook)
    assert k.settlement_payments.ledger is k.ledger
    assert k.settlement_payments.clock is k.clock


def test_kernel_simulation_date_uses_clock_for_instruction():
    k = _kernel()
    k.settlement_payments.add_instruction(_instruction())
    rec = k.ledger.records[-1]
    assert rec.simulation_date == "2026-03-31"


def test_kernel_simulation_date_uses_clock_for_event():
    k = _kernel()
    k.settlement_payments.add_event(_event())
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
        "attention_feedback": k.attention_feedback.snapshot(),
        "investor_intents": k.investor_intents.snapshot(),
    }
    k.settlement_payments.add_instruction(_instruction())
    k.settlement_payments.add_event(_event())
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
        / "settlement_payments.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, token
