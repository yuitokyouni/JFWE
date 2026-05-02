"""
Tests for v1.14.1 CorporateFinancingNeedRecord +
CorporateFinancingNeedBook.
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
from datetime import date

import pytest

from world.clock import Clock
from world.corporate_financing import (
    CorporateFinancingNeedBook,
    CorporateFinancingNeedRecord,
    DuplicateCorporateFinancingNeedError,
    UnknownCorporateFinancingNeedError,
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


def _need(
    *,
    need_id: str = "corporate_financing_need:reference_a:2026-03-31",
    firm_id: str = "firm:reference_a",
    as_of_date: str = "2026-03-31",
    funding_horizon_label: str = "near_term",
    funding_purpose_label: str = "working_capital",
    urgency_label: str = "moderate",
    synthetic_size_label: str = "reference_size_medium",
    status: str = "active",
    visibility: str = "internal_only",
    confidence: float = 0.5,
    source_firm_financial_state_ids: tuple[str, ...] = (),
    source_market_environment_state_ids: tuple[str, ...] = (),
    source_corporate_signal_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> CorporateFinancingNeedRecord:
    return CorporateFinancingNeedRecord(
        need_id=need_id,
        firm_id=firm_id,
        as_of_date=as_of_date,
        funding_horizon_label=funding_horizon_label,
        funding_purpose_label=funding_purpose_label,
        urgency_label=urgency_label,
        synthetic_size_label=synthetic_size_label,
        status=status,
        visibility=visibility,
        confidence=confidence,
        source_firm_financial_state_ids=source_firm_financial_state_ids,
        source_market_environment_state_ids=source_market_environment_state_ids,
        source_corporate_signal_ids=source_corporate_signal_ids,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Record validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"need_id": ""},
        {"firm_id": ""},
        {"as_of_date": ""},
        {"funding_horizon_label": ""},
        {"funding_purpose_label": ""},
        {"urgency_label": ""},
        {"synthetic_size_label": ""},
        {"status": ""},
        {"visibility": ""},
    ],
)
def test_need_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _need(**kwargs)


def test_need_coerces_date_to_iso_string():
    n = _need(as_of_date=date(2026, 3, 31))
    assert n.as_of_date == "2026-03-31"


def test_need_is_frozen():
    n = _need()
    with pytest.raises(Exception):
        n.need_id = "tampered"  # type: ignore[misc]


def test_need_rejects_bool_confidence():
    with pytest.raises(ValueError):
        _need(confidence=True)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [-0.01, 1.01, -1.0, 2.0])
def test_need_rejects_out_of_range_confidence(bad):
    with pytest.raises(ValueError):
        _need(confidence=bad)


@pytest.mark.parametrize("good", [0.0, 0.5, 1.0])
def test_need_accepts_in_range_confidence(good):
    n = _need(confidence=good)
    assert n.confidence == float(good)


def test_need_rejects_non_numeric_confidence():
    with pytest.raises(ValueError):
        _need(confidence="0.5")  # type: ignore[arg-type]


def test_need_rejects_empty_strings_in_source_tuples():
    with pytest.raises(ValueError):
        _need(source_firm_financial_state_ids=("",))
    with pytest.raises(ValueError):
        _need(source_market_environment_state_ids=("valid", ""))
    with pytest.raises(ValueError):
        _need(source_corporate_signal_ids=("",))


def test_need_to_dict_round_trips():
    n = _need(
        source_firm_financial_state_ids=("firm_financial_state:a",),
        source_market_environment_state_ids=("market_environment_state:a",),
        source_corporate_signal_ids=("information_signal:a",),
        metadata={"note": "synthetic"},
    )
    out = n.to_dict()
    assert out["source_firm_financial_state_ids"] == ["firm_financial_state:a"]
    assert out["source_market_environment_state_ids"] == [
        "market_environment_state:a"
    ]
    assert out["source_corporate_signal_ids"] == ["information_signal:a"]
    assert out["metadata"] == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# Recommended labels (pinned but not enforced)
# ---------------------------------------------------------------------------


_RECOMMENDED_HORIZONS = (
    "immediate", "near_term", "medium_term", "long_term", "unknown",
)
_RECOMMENDED_PURPOSES = (
    "working_capital",
    "refinancing",
    "growth_capex",
    "acquisition",
    "restructuring",
    "unknown",
)
_RECOMMENDED_URGENCIES = (
    "low", "moderate", "elevated", "critical", "unknown",
)
_RECOMMENDED_SIZE_LABELS = (
    "reference_size_small",
    "reference_size_medium",
    "reference_size_large",
    "unknown",
)


@pytest.mark.parametrize("label", _RECOMMENDED_HORIZONS)
def test_recommended_horizons_accepted(label):
    n = _need(funding_horizon_label=label)
    assert n.funding_horizon_label == label


@pytest.mark.parametrize("label", _RECOMMENDED_PURPOSES)
def test_recommended_purposes_accepted(label):
    n = _need(funding_purpose_label=label)
    assert n.funding_purpose_label == label


@pytest.mark.parametrize("label", _RECOMMENDED_URGENCIES)
def test_recommended_urgencies_accepted(label):
    n = _need(urgency_label=label)
    assert n.urgency_label == label


@pytest.mark.parametrize("label", _RECOMMENDED_SIZE_LABELS)
def test_recommended_size_labels_accepted(label):
    n = _need(synthetic_size_label=label)
    assert n.synthetic_size_label == label


# ---------------------------------------------------------------------------
# Anti-fields
# ---------------------------------------------------------------------------


_FORBIDDEN_FIELDS = {
    "amount",
    "currency_value",
    "fx_rate",
    "balance",
    "loan_amount",
    "interest_rate",
    "coupon",
    "tenor_years",
    "coverage_ratio",
    "decision_outcome",
    "default_probability",
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
    "rating",
    "internal_rating",
    "pd",
    "lgd",
    "ead",
    "haircut_percentage",
    "spread",
    "yield",
    "coupon_rate",
}


def test_need_record_has_no_anti_fields():
    field_names = {
        f.name for f in dataclass_fields(CorporateFinancingNeedRecord)
    }
    leaked = field_names & _FORBIDDEN_FIELDS
    assert not leaked


# ---------------------------------------------------------------------------
# Book — CRUD
# ---------------------------------------------------------------------------


def test_book_add_and_get_need():
    book = CorporateFinancingNeedBook()
    n = _need()
    book.add_need(n)
    assert book.get_need(n.need_id) is n


def test_book_get_unknown_need_raises():
    book = CorporateFinancingNeedBook()
    with pytest.raises(UnknownCorporateFinancingNeedError):
        book.get_need("corporate_financing_need:missing")
    with pytest.raises(KeyError):
        book.get_need("corporate_financing_need:missing")


def test_book_duplicate_need_id_rejected():
    book = CorporateFinancingNeedBook()
    book.add_need(_need())
    with pytest.raises(DuplicateCorporateFinancingNeedError):
        book.add_need(_need())


def test_book_list_needs_returns_all():
    book = CorporateFinancingNeedBook()
    book.add_need(_need(need_id="corporate_financing_need:a"))
    book.add_need(_need(need_id="corporate_financing_need:b"))
    assert len(book.list_needs()) == 2


def test_book_list_by_firm():
    book = CorporateFinancingNeedBook()
    book.add_need(
        _need(
            need_id="corporate_financing_need:a",
            firm_id="firm:p1",
        )
    )
    book.add_need(
        _need(
            need_id="corporate_financing_need:b",
            firm_id="firm:p2",
        )
    )
    out = book.list_by_firm("firm:p1")
    assert len(out) == 1
    assert out[0].firm_id == "firm:p1"


def test_book_list_by_date():
    book = CorporateFinancingNeedBook()
    book.add_need(
        _need(
            need_id="corporate_financing_need:a",
            as_of_date="2026-03-31",
        )
    )
    book.add_need(
        _need(
            need_id="corporate_financing_need:b",
            as_of_date="2026-04-30",
        )
    )
    assert len(book.list_by_date("2026-04-30")) == 1


def test_book_list_by_urgency():
    book = CorporateFinancingNeedBook()
    book.add_need(
        _need(need_id="corporate_financing_need:a", urgency_label="low")
    )
    book.add_need(
        _need(
            need_id="corporate_financing_need:b", urgency_label="critical"
        )
    )
    assert len(book.list_by_urgency("critical")) == 1


def test_book_list_by_purpose():
    book = CorporateFinancingNeedBook()
    book.add_need(
        _need(
            need_id="corporate_financing_need:a",
            funding_purpose_label="working_capital",
        )
    )
    book.add_need(
        _need(
            need_id="corporate_financing_need:b",
            funding_purpose_label="refinancing",
        )
    )
    assert len(book.list_by_purpose("refinancing")) == 1


def test_book_get_latest_for_firm():
    book = CorporateFinancingNeedBook()
    n1 = _need(
        need_id="corporate_financing_need:a",
        firm_id="firm:p1",
        as_of_date="2026-03-31",
    )
    n2 = _need(
        need_id="corporate_financing_need:b",
        firm_id="firm:p1",
        as_of_date="2026-04-30",
    )
    book.add_need(n1)
    book.add_need(n2)
    assert book.get_latest_for_firm("firm:p1") is n2


def test_book_get_latest_for_unknown_firm_returns_none():
    book = CorporateFinancingNeedBook()
    assert book.get_latest_for_firm("firm:missing") is None


def test_book_snapshot_is_deterministic_and_sorted():
    book = CorporateFinancingNeedBook()
    book.add_need(_need(need_id="corporate_financing_need:b"))
    book.add_need(_need(need_id="corporate_financing_need:a"))
    snap = book.snapshot()
    assert snap["need_count"] == 2
    assert [n["need_id"] for n in snap["needs"]] == [
        "corporate_financing_need:a",
        "corporate_financing_need:b",
    ]


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_type_exists():
    assert (
        RecordType.CORPORATE_FINANCING_NEED_RECORDED.value
        == "corporate_financing_need_recorded"
    )


def test_add_need_writes_one_ledger_record():
    ledger = Ledger()
    book = CorporateFinancingNeedBook(ledger=ledger)
    book.add_need(_need())
    assert len(ledger.records) == 1
    rec = ledger.records[0]
    assert rec.record_type is RecordType.CORPORATE_FINANCING_NEED_RECORDED
    assert rec.space_id == "corporate_financing"


def test_ledger_payload_contains_label_fields():
    ledger = Ledger()
    book = CorporateFinancingNeedBook(ledger=ledger)
    book.add_need(_need())
    rec = ledger.records[0]
    assert rec.payload["funding_horizon_label"] == "near_term"
    assert rec.payload["funding_purpose_label"] == "working_capital"
    assert rec.payload["urgency_label"] == "moderate"
    assert rec.payload["synthetic_size_label"] == "reference_size_medium"


def test_ledger_payload_carries_no_anti_field_keys():
    ledger = Ledger()
    book = CorporateFinancingNeedBook(ledger=ledger)
    book.add_need(_need())
    rec = ledger.records[0]
    leaked = set(rec.payload.keys()) & _FORBIDDEN_FIELDS
    assert not leaked


def test_book_without_ledger_does_not_raise():
    book = CorporateFinancingNeedBook()
    book.add_need(_need())


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_corporate_financing_needs_book():
    k = _kernel()
    assert isinstance(k.corporate_financing_needs, CorporateFinancingNeedBook)
    assert k.corporate_financing_needs.ledger is k.ledger
    assert k.corporate_financing_needs.clock is k.clock


def test_kernel_simulation_date_uses_clock_for_need():
    k = _kernel()
    k.corporate_financing_needs.add_need(_need())
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
        "interbank_liquidity": k.interbank_liquidity.snapshot(),
        "central_bank_signals": k.central_bank_signals.snapshot(),
        "attention_feedback": k.attention_feedback.snapshot(),
        "investor_intents": k.investor_intents.snapshot(),
        "market_environments": k.market_environments.snapshot(),
        "firm_financial_states": k.firm_financial_states.snapshot(),
    }
    k.corporate_financing_needs.add_need(_need())
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
        / "corporate_financing.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, token
