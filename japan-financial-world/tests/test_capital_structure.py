"""
Tests for v1.14.3 CapitalStructureReviewCandidate +
CapitalStructureReviewBook.
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
from datetime import date

import pytest

from world.capital_structure import (
    CapitalStructureReviewBook,
    CapitalStructureReviewCandidate,
    COVENANT_HEADROOM_LABELS,
    DILUTION_CONCERN_LABELS,
    DuplicateCapitalStructureReviewError,
    LEVERAGE_PRESSURE_LABELS,
    LIQUIDITY_PRESSURE_LABELS,
    MARKET_ACCESS_LABELS,
    MATURITY_WALL_LABELS,
    RATING_PERCEPTION_LABELS,
    REVIEW_TYPE_LABELS,
    UnknownCapitalStructureReviewError,
)
from world.clock import Clock
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


def _candidate(
    *,
    review_candidate_id: str = (
        "capital_structure_review:reference_a:refinancing:2026-03-31"
    ),
    firm_id: str = "firm:reference_a",
    as_of_date: str = "2026-03-31",
    review_type_label: str = "refinancing_review",
    leverage_pressure_label: str = "elevated",
    liquidity_pressure_label: str = "elevated",
    maturity_wall_label: str = "approaching",
    dilution_concern_label: str = "moderate",
    covenant_headroom_label: str = "limited",
    market_access_label: str = "selective",
    rating_perception_label: str = "watch",
    status: str = "candidate",
    visibility: str = "internal_only",
    confidence: float = 0.5,
    source_need_ids: tuple[str, ...] = (),
    source_funding_option_ids: tuple[str, ...] = (),
    source_firm_state_ids: tuple[str, ...] = (),
    source_market_environment_state_ids: tuple[str, ...] = (),
    source_interbank_liquidity_state_ids: tuple[str, ...] = (),
    source_bank_credit_review_signal_ids: tuple[str, ...] = (),
    source_investor_intent_ids: tuple[str, ...] = (),
    source_indicative_market_pressure_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> CapitalStructureReviewCandidate:
    return CapitalStructureReviewCandidate(
        review_candidate_id=review_candidate_id,
        firm_id=firm_id,
        as_of_date=as_of_date,
        review_type_label=review_type_label,
        leverage_pressure_label=leverage_pressure_label,
        liquidity_pressure_label=liquidity_pressure_label,
        maturity_wall_label=maturity_wall_label,
        dilution_concern_label=dilution_concern_label,
        covenant_headroom_label=covenant_headroom_label,
        market_access_label=market_access_label,
        rating_perception_label=rating_perception_label,
        status=status,
        visibility=visibility,
        confidence=confidence,
        source_need_ids=source_need_ids,
        source_funding_option_ids=source_funding_option_ids,
        source_firm_state_ids=source_firm_state_ids,
        source_market_environment_state_ids=source_market_environment_state_ids,
        source_interbank_liquidity_state_ids=source_interbank_liquidity_state_ids,
        source_bank_credit_review_signal_ids=source_bank_credit_review_signal_ids,
        source_investor_intent_ids=source_investor_intent_ids,
        source_indicative_market_pressure_ids=source_indicative_market_pressure_ids,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Required-string validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"review_candidate_id": ""},
        {"firm_id": ""},
        {"as_of_date": ""},
        {"status": ""},
        {"visibility": ""},
    ],
)
def test_candidate_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _candidate(**kwargs)


def test_candidate_coerces_date_to_iso_string():
    c = _candidate(as_of_date=date(2026, 3, 31))
    assert c.as_of_date == "2026-03-31"


def test_candidate_is_frozen():
    c = _candidate()
    with pytest.raises(Exception):
        c.review_candidate_id = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Confidence (bounded, bool-rejecting)
# ---------------------------------------------------------------------------


def test_candidate_rejects_bool_confidence():
    with pytest.raises(ValueError):
        _candidate(confidence=True)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [-0.01, 1.01, -1.0, 2.0])
def test_candidate_rejects_out_of_range_confidence(bad):
    with pytest.raises(ValueError):
        _candidate(confidence=bad)


@pytest.mark.parametrize("good", [0.0, 0.5, 1.0])
def test_candidate_accepts_in_range_confidence(good):
    c = _candidate(confidence=good)
    assert c.confidence == float(good)


def test_candidate_rejects_non_numeric_confidence():
    with pytest.raises(ValueError):
        _candidate(confidence="0.5")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Source-id tuple validation
# ---------------------------------------------------------------------------


def test_candidate_rejects_empty_strings_in_source_tuples():
    for kwarg in (
        "source_need_ids",
        "source_funding_option_ids",
        "source_firm_state_ids",
        "source_market_environment_state_ids",
        "source_interbank_liquidity_state_ids",
        "source_bank_credit_review_signal_ids",
        "source_investor_intent_ids",
    ):
        with pytest.raises(ValueError):
            _candidate(**{kwarg: ("",)})


def test_candidate_to_dict_round_trips():
    c = _candidate(
        source_need_ids=(
            "corporate_financing_need:reference_a:2026-03-31",
        ),
        source_funding_option_ids=(
            "funding_option:reference_a:bank_loan:2026-03-31",
        ),
        source_firm_state_ids=(
            "firm_financial_state:reference_a:2026-03-31",
        ),
        source_market_environment_state_ids=("market_environment_state:Q3",),
        source_interbank_liquidity_state_ids=(
            "interbank_liquidity_state:bank_c:2026-03-31",
        ),
        source_bank_credit_review_signal_ids=(
            "bank_credit_review_signal:bank_c:reference_a:Q3",
        ),
        source_investor_intent_ids=(
            "investor_intent_signal:investor_a:reference_a:Q3",
        ),
        metadata={"note": "synthetic"},
    )
    out = c.to_dict()
    assert out["source_need_ids"] == [
        "corporate_financing_need:reference_a:2026-03-31"
    ]
    assert out["source_funding_option_ids"] == [
        "funding_option:reference_a:bank_loan:2026-03-31"
    ]
    assert out["source_firm_state_ids"] == [
        "firm_financial_state:reference_a:2026-03-31"
    ]
    assert out["source_market_environment_state_ids"] == [
        "market_environment_state:Q3"
    ]
    assert out["source_interbank_liquidity_state_ids"] == [
        "interbank_liquidity_state:bank_c:2026-03-31"
    ]
    assert out["source_bank_credit_review_signal_ids"] == [
        "bank_credit_review_signal:bank_c:reference_a:Q3"
    ]
    assert out["source_investor_intent_ids"] == [
        "investor_intent_signal:investor_a:reference_a:Q3"
    ]
    assert out["metadata"] == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# Closed-set label vocabularies — accept every listed value
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label", sorted(REVIEW_TYPE_LABELS))
def test_review_type_labels_accepted(label):
    c = _candidate(review_type_label=label)
    assert c.review_type_label == label


@pytest.mark.parametrize("label", sorted(LEVERAGE_PRESSURE_LABELS))
def test_leverage_pressure_labels_accepted(label):
    c = _candidate(leverage_pressure_label=label)
    assert c.leverage_pressure_label == label


@pytest.mark.parametrize("label", sorted(LIQUIDITY_PRESSURE_LABELS))
def test_liquidity_pressure_labels_accepted(label):
    c = _candidate(liquidity_pressure_label=label)
    assert c.liquidity_pressure_label == label


@pytest.mark.parametrize("label", sorted(MATURITY_WALL_LABELS))
def test_maturity_wall_labels_accepted(label):
    c = _candidate(maturity_wall_label=label)
    assert c.maturity_wall_label == label


@pytest.mark.parametrize("label", sorted(DILUTION_CONCERN_LABELS))
def test_dilution_concern_labels_accepted(label):
    c = _candidate(dilution_concern_label=label)
    assert c.dilution_concern_label == label


@pytest.mark.parametrize("label", sorted(COVENANT_HEADROOM_LABELS))
def test_covenant_headroom_labels_accepted(label):
    c = _candidate(covenant_headroom_label=label)
    assert c.covenant_headroom_label == label


@pytest.mark.parametrize("label", sorted(MARKET_ACCESS_LABELS))
def test_market_access_labels_accepted(label):
    c = _candidate(market_access_label=label)
    assert c.market_access_label == label


@pytest.mark.parametrize("label", sorted(RATING_PERCEPTION_LABELS))
def test_rating_perception_labels_accepted(label):
    c = _candidate(rating_perception_label=label)
    assert c.rating_perception_label == label


# ---------------------------------------------------------------------------
# Closed-set label vocabularies — reject out-of-set values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name",
    [
        "review_type_label",
        "leverage_pressure_label",
        "liquidity_pressure_label",
        "maturity_wall_label",
        "dilution_concern_label",
        "covenant_headroom_label",
        "market_access_label",
        "rating_perception_label",
    ],
)
def test_label_field_rejects_out_of_set_value(field_name):
    with pytest.raises(ValueError):
        _candidate(**{field_name: "not_a_real_label"})


def test_pinned_review_type_label_set_is_exact():
    assert REVIEW_TYPE_LABELS == frozenset(
        {
            "leverage_review",
            "liquidity_review",
            "refinancing_review",
            "dilution_review",
            "covenant_review",
            "market_access_review",
            "rating_perception_review",
            "unknown",
        }
    )


def test_pinned_leverage_pressure_label_set_is_exact():
    assert LEVERAGE_PRESSURE_LABELS == frozenset(
        {"low", "moderate", "elevated", "high", "unknown"}
    )


def test_pinned_liquidity_pressure_label_set_is_exact():
    assert LIQUIDITY_PRESSURE_LABELS == frozenset(
        {"low", "moderate", "elevated", "stressed", "unknown"}
    )


def test_pinned_maturity_wall_label_set_is_exact():
    assert MATURITY_WALL_LABELS == frozenset(
        {
            "none_visible",
            "manageable",
            "approaching",
            "concentrated",
            "unknown",
        }
    )


def test_pinned_dilution_concern_label_set_is_exact():
    assert DILUTION_CONCERN_LABELS == frozenset(
        {"not_applicable", "low", "moderate", "high", "unknown"}
    )


def test_pinned_covenant_headroom_label_set_is_exact():
    assert COVENANT_HEADROOM_LABELS == frozenset(
        {"not_applicable", "comfortable", "limited", "tight", "unknown"}
    )


def test_pinned_market_access_label_set_is_exact():
    assert MARKET_ACCESS_LABELS == frozenset(
        {"open", "selective", "constrained", "closed", "unknown"}
    )


def test_pinned_rating_perception_label_set_is_exact():
    assert RATING_PERCEPTION_LABELS == frozenset(
        {"stable", "watch", "negative_watch", "stressed", "unknown"}
    )


# ---------------------------------------------------------------------------
# Anti-fields — must NOT appear on dataclass or ledger payload
# ---------------------------------------------------------------------------


_FORBIDDEN_FIELDS = {
    "debt_amount",
    "equity_amount",
    "leverage_ratio",
    "debt_to_equity",
    "wacc",
    "WACC",
    "rating",
    "PD",
    "LGD",
    "EAD",
    "pd",
    "lgd",
    "ead",
    "spread",
    "coupon",
    "fee",
    "price",
    "approval",
    "execution",
    "executed",
    "recommendation",
    "investment_advice",
    "real_data_value",
    # plus the v1.14 family standard set
    "amount",
    "loan_amount",
    "interest_rate",
    "coupon_rate",
    "yield",
    "policy_rate",
    "interest",
    "tenor_years",
    "default_probability",
    "behavior_probability",
    "internal_rating",
    "decision_outcome",
    "order",
    "trade",
    "forecast_value",
    "actual_value",
    "underwriting",
    "syndication",
    "commitment",
    "allocation",
    "offering_price",
    "take_up_probability",
    "expected_return",
}


def test_candidate_has_no_anti_fields():
    field_names = {
        f.name for f in dataclass_fields(CapitalStructureReviewCandidate)
    }
    leaked = field_names & _FORBIDDEN_FIELDS
    assert not leaked


# ---------------------------------------------------------------------------
# Book — CRUD
# ---------------------------------------------------------------------------


def test_book_add_and_get_candidate():
    book = CapitalStructureReviewBook()
    c = _candidate()
    book.add_candidate(c)
    assert book.get_candidate(c.review_candidate_id) is c


def test_book_get_unknown_candidate_raises():
    book = CapitalStructureReviewBook()
    with pytest.raises(UnknownCapitalStructureReviewError):
        book.get_candidate("capital_structure_review:missing")
    with pytest.raises(KeyError):
        book.get_candidate("capital_structure_review:missing")


def test_book_duplicate_review_candidate_id_rejected():
    book = CapitalStructureReviewBook()
    book.add_candidate(_candidate())
    with pytest.raises(DuplicateCapitalStructureReviewError):
        book.add_candidate(_candidate())


def test_book_list_candidates_returns_all():
    book = CapitalStructureReviewBook()
    book.add_candidate(_candidate(review_candidate_id="capital_structure_review:a"))
    book.add_candidate(_candidate(review_candidate_id="capital_structure_review:b"))
    assert len(book.list_candidates()) == 2


def test_book_list_by_firm():
    book = CapitalStructureReviewBook()
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:a",
            firm_id="firm:p1",
        )
    )
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:b",
            firm_id="firm:p2",
        )
    )
    out = book.list_by_firm("firm:p1")
    assert len(out) == 1
    assert out[0].firm_id == "firm:p1"


def test_book_list_by_review_type():
    book = CapitalStructureReviewBook()
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:a",
            review_type_label="leverage_review",
        )
    )
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:b",
            review_type_label="refinancing_review",
        )
    )
    assert len(book.list_by_review_type("refinancing_review")) == 1


def test_book_list_by_market_access():
    book = CapitalStructureReviewBook()
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:a",
            market_access_label="open",
        )
    )
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:b",
            market_access_label="constrained",
        )
    )
    assert len(book.list_by_market_access("constrained")) == 1


def test_book_list_by_status():
    book = CapitalStructureReviewBook()
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:a", status="candidate"
        )
    )
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:b", status="superseded"
        )
    )
    assert len(book.list_by_status("superseded")) == 1


def test_book_list_by_date():
    book = CapitalStructureReviewBook()
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:a",
            as_of_date="2026-03-31",
        )
    )
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:b",
            as_of_date="2026-04-30",
        )
    )
    assert len(book.list_by_date("2026-04-30")) == 1


def test_book_list_by_need():
    book = CapitalStructureReviewBook()
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:a",
            source_need_ids=("corporate_financing_need:n1",),
        )
    )
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:b",
            source_need_ids=(
                "corporate_financing_need:n1",
                "corporate_financing_need:n2",
            ),
        )
    )
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:c",
            source_need_ids=("corporate_financing_need:n3",),
        )
    )
    out = book.list_by_need("corporate_financing_need:n1")
    assert {c.review_candidate_id for c in out} == {
        "capital_structure_review:a",
        "capital_structure_review:b",
    }
    assert (
        len(book.list_by_need("corporate_financing_need:never_referenced"))
        == 0
    )


def test_book_list_by_funding_option():
    book = CapitalStructureReviewBook()
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:a",
            source_funding_option_ids=("funding_option:o1",),
        )
    )
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:b",
            source_funding_option_ids=(
                "funding_option:o1",
                "funding_option:o2",
            ),
        )
    )
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:c",
            source_funding_option_ids=("funding_option:o3",),
        )
    )
    out = book.list_by_funding_option("funding_option:o1")
    assert {c.review_candidate_id for c in out} == {
        "capital_structure_review:a",
        "capital_structure_review:b",
    }
    assert (
        len(book.list_by_funding_option("funding_option:never_referenced"))
        == 0
    )


def test_book_snapshot_is_deterministic_and_sorted():
    book = CapitalStructureReviewBook()
    book.add_candidate(_candidate(review_candidate_id="capital_structure_review:b"))
    book.add_candidate(_candidate(review_candidate_id="capital_structure_review:a"))
    snap = book.snapshot()
    assert snap["candidate_count"] == 2
    assert [c["review_candidate_id"] for c in snap["candidates"]] == [
        "capital_structure_review:a",
        "capital_structure_review:b",
    ]
    assert book.snapshot() == snap


# ---------------------------------------------------------------------------
# Plain-id cross-references — accepted as data, not validated
# ---------------------------------------------------------------------------


def test_can_cite_corporate_financing_need_ids_as_plain_ids():
    book = CapitalStructureReviewBook()
    c = _candidate(
        source_need_ids=(
            "corporate_financing_need:reference_a:2026-03-31",
            "corporate_financing_need:reference_a:2026-04-30",
        ),
    )
    book.add_candidate(c)
    out = book.get_candidate(c.review_candidate_id)
    assert out.source_need_ids == (
        "corporate_financing_need:reference_a:2026-03-31",
        "corporate_financing_need:reference_a:2026-04-30",
    )


def test_can_cite_funding_option_candidate_ids_as_plain_ids():
    book = CapitalStructureReviewBook()
    c = _candidate(
        source_funding_option_ids=(
            "funding_option:reference_a:bank_loan:2026-03-31",
            "funding_option:reference_a:bond_issuance:2026-03-31",
        ),
    )
    book.add_candidate(c)
    out = book.get_candidate(c.review_candidate_id)
    assert out.source_funding_option_ids == (
        "funding_option:reference_a:bank_loan:2026-03-31",
        "funding_option:reference_a:bond_issuance:2026-03-31",
    )


def test_can_cite_market_environment_and_interbank_liquidity_ids_as_plain_ids():
    book = CapitalStructureReviewBook()
    c = _candidate(
        source_market_environment_state_ids=(
            "market_environment_state:2026Q3",
        ),
        source_interbank_liquidity_state_ids=(
            "interbank_liquidity_state:bank_c:2026-03-31",
        ),
    )
    book.add_candidate(c)
    out = book.get_candidate(c.review_candidate_id)
    assert out.source_market_environment_state_ids == (
        "market_environment_state:2026Q3",
    )
    assert out.source_interbank_liquidity_state_ids == (
        "interbank_liquidity_state:bank_c:2026-03-31",
    )


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_type_exists():
    assert (
        RecordType.CAPITAL_STRUCTURE_REVIEW_CANDIDATE_RECORDED.value
        == "capital_structure_review_candidate_recorded"
    )


def test_add_candidate_writes_exactly_one_ledger_record():
    ledger = Ledger()
    book = CapitalStructureReviewBook(ledger=ledger)
    book.add_candidate(_candidate())
    assert len(ledger.records) == 1
    rec = ledger.records[0]
    assert (
        rec.record_type
        is RecordType.CAPITAL_STRUCTURE_REVIEW_CANDIDATE_RECORDED
    )
    assert rec.space_id == "capital_structure_reviews"


def test_duplicate_add_emits_no_extra_ledger_record():
    ledger = Ledger()
    book = CapitalStructureReviewBook(ledger=ledger)
    book.add_candidate(_candidate())
    with pytest.raises(DuplicateCapitalStructureReviewError):
        book.add_candidate(_candidate())
    assert len(ledger.records) == 1


def test_ledger_payload_contains_label_fields():
    ledger = Ledger()
    book = CapitalStructureReviewBook(ledger=ledger)
    book.add_candidate(_candidate())
    rec = ledger.records[0]
    assert rec.payload["review_type_label"] == "refinancing_review"
    assert rec.payload["leverage_pressure_label"] == "elevated"
    assert rec.payload["liquidity_pressure_label"] == "elevated"
    assert rec.payload["maturity_wall_label"] == "approaching"
    assert rec.payload["dilution_concern_label"] == "moderate"
    assert rec.payload["covenant_headroom_label"] == "limited"
    assert rec.payload["market_access_label"] == "selective"
    assert rec.payload["rating_perception_label"] == "watch"


def test_ledger_payload_carries_no_anti_field_keys():
    ledger = Ledger()
    book = CapitalStructureReviewBook(ledger=ledger)
    book.add_candidate(_candidate())
    rec = ledger.records[0]
    leaked = set(rec.payload.keys()) & _FORBIDDEN_FIELDS
    assert not leaked


def test_ledger_emits_no_forbidden_event_types():
    ledger = Ledger()
    book = CapitalStructureReviewBook(ledger=ledger)
    book.add_candidate(_candidate())
    types = {rec.record_type for rec in ledger.records}
    assert types == {RecordType.CAPITAL_STRUCTURE_REVIEW_CANDIDATE_RECORDED}


def test_book_without_ledger_does_not_raise():
    book = CapitalStructureReviewBook()
    book.add_candidate(_candidate())


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_capital_structure_reviews_book():
    k = _kernel()
    assert isinstance(k.capital_structure_reviews, CapitalStructureReviewBook)
    assert k.capital_structure_reviews.ledger is k.ledger
    assert k.capital_structure_reviews.clock is k.clock


def test_kernel_simulation_date_uses_clock_for_candidate():
    k = _kernel()
    k.capital_structure_reviews.add_candidate(_candidate())
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
        "corporate_financing_needs": k.corporate_financing_needs.snapshot(),
        "funding_options": k.funding_options.snapshot(),
    }
    k.capital_structure_reviews.add_candidate(_candidate())
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
        / "capital_structure.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, token


# ---------------------------------------------------------------------------
# v1.15.6 — IndicativeMarketPressureRecord citation slot
# ---------------------------------------------------------------------------


def test_v1_15_6_candidate_accepts_indicative_market_pressure_evidence():
    c = _candidate(
        source_indicative_market_pressure_ids=(
            "indicative_market_pressure:security:reference_a:2026-03-31",
        ),
    )
    assert c.source_indicative_market_pressure_ids == (
        "indicative_market_pressure:security:reference_a:2026-03-31",
    )


def test_v1_15_6_candidate_rejects_empty_strings_in_pressure_evidence_tuple():
    with pytest.raises(ValueError):
        _candidate(source_indicative_market_pressure_ids=("",))


def test_v1_15_6_candidate_to_dict_round_trips_pressure_evidence():
    c = _candidate(
        source_indicative_market_pressure_ids=(
            "indicative_market_pressure:security:reference_a:2026-03-31",
        ),
    )
    out = c.to_dict()
    assert out["source_indicative_market_pressure_ids"] == [
        "indicative_market_pressure:security:reference_a:2026-03-31"
    ]


def test_v1_15_6_book_list_by_indicative_market_pressure():
    book = CapitalStructureReviewBook()
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:a",
            source_indicative_market_pressure_ids=(
                "indicative_market_pressure:p1",
            ),
        )
    )
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:b",
            source_indicative_market_pressure_ids=(
                "indicative_market_pressure:p1",
                "indicative_market_pressure:p2",
            ),
        )
    )
    book.add_candidate(
        _candidate(
            review_candidate_id="capital_structure_review:c",
            source_indicative_market_pressure_ids=(
                "indicative_market_pressure:p3",
            ),
        )
    )
    out = book.list_by_indicative_market_pressure(
        "indicative_market_pressure:p1"
    )
    assert {c.review_candidate_id for c in out} == {
        "capital_structure_review:a",
        "capital_structure_review:b",
    }
    assert (
        len(
            book.list_by_indicative_market_pressure(
                "indicative_market_pressure:never_referenced"
            )
        )
        == 0
    )


def test_v1_15_6_ledger_payload_carries_pressure_evidence_key():
    ledger = Ledger()
    book = CapitalStructureReviewBook(ledger=ledger)
    book.add_candidate(
        _candidate(
            source_indicative_market_pressure_ids=(
                "indicative_market_pressure:security:reference_a:2026-03-31",
            ),
        )
    )
    rec = ledger.records[0]
    assert "source_indicative_market_pressure_ids" in rec.payload
    assert list(rec.payload["source_indicative_market_pressure_ids"]) == [
        "indicative_market_pressure:security:reference_a:2026-03-31"
    ]
