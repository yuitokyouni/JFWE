"""
Tests for v1.14.4 CorporateFinancingPathRecord +
CorporateFinancingPathBook + ``build_corporate_financing_path``.
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
from datetime import date

import pytest

from world.capital_structure import CapitalStructureReviewCandidate
from world.clock import Clock
from world.corporate_financing import CorporateFinancingNeedRecord
from world.financing_paths import (
    COHERENCE_LABELS,
    CONSTRAINT_LABELS,
    CorporateFinancingPathBook,
    CorporateFinancingPathRecord,
    DuplicateCorporateFinancingPathError,
    NEXT_REVIEW_LABELS,
    PATH_STATUS_LABELS,
    PATH_TYPE_LABELS,
    UnknownCorporateFinancingPathError,
    build_corporate_financing_path,
)
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
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


def _path(
    *,
    financing_path_id: str = (
        "corporate_financing_path:reference_a:2026-03-31"
    ),
    firm_id: str = "firm:reference_a",
    as_of_date: str = "2026-03-31",
    path_type_label: str = "refinancing_path",
    path_status_label: str = "draft",
    coherence_label: str = "coherent",
    constraint_label: str = "no_obvious_constraint",
    next_review_label: str = "monitor",
    status: str = "active",
    visibility: str = "internal_only",
    confidence: float = 0.5,
    need_ids: tuple[str, ...] = (),
    funding_option_ids: tuple[str, ...] = (),
    capital_structure_review_ids: tuple[str, ...] = (),
    market_environment_state_ids: tuple[str, ...] = (),
    interbank_liquidity_state_ids: tuple[str, ...] = (),
    bank_credit_review_signal_ids: tuple[str, ...] = (),
    investor_intent_ids: tuple[str, ...] = (),
    indicative_market_pressure_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> CorporateFinancingPathRecord:
    return CorporateFinancingPathRecord(
        financing_path_id=financing_path_id,
        firm_id=firm_id,
        as_of_date=as_of_date,
        path_type_label=path_type_label,
        path_status_label=path_status_label,
        coherence_label=coherence_label,
        constraint_label=constraint_label,
        next_review_label=next_review_label,
        status=status,
        visibility=visibility,
        confidence=confidence,
        need_ids=need_ids,
        funding_option_ids=funding_option_ids,
        capital_structure_review_ids=capital_structure_review_ids,
        market_environment_state_ids=market_environment_state_ids,
        interbank_liquidity_state_ids=interbank_liquidity_state_ids,
        bank_credit_review_signal_ids=bank_credit_review_signal_ids,
        investor_intent_ids=investor_intent_ids,
        indicative_market_pressure_ids=indicative_market_pressure_ids,
        metadata=metadata or {},
    )


def _need(
    *,
    need_id: str,
    firm_id: str = "firm:reference_a",
    funding_purpose_label: str = "refinancing",
) -> CorporateFinancingNeedRecord:
    return CorporateFinancingNeedRecord(
        need_id=need_id,
        firm_id=firm_id,
        as_of_date="2026-03-31",
        funding_horizon_label="near_term",
        funding_purpose_label=funding_purpose_label,
        urgency_label="moderate",
        synthetic_size_label="reference_size_medium",
        status="active",
        visibility="internal_only",
        confidence=0.5,
    )


def _review(
    *,
    review_candidate_id: str,
    firm_id: str = "firm:reference_a",
    market_access_label: str = "open",
    liquidity_pressure_label: str = "moderate",
    leverage_pressure_label: str = "moderate",
    maturity_wall_label: str = "manageable",
    covenant_headroom_label: str = "comfortable",
    dilution_concern_label: str = "low",
    rating_perception_label: str = "stable",
) -> CapitalStructureReviewCandidate:
    return CapitalStructureReviewCandidate(
        review_candidate_id=review_candidate_id,
        firm_id=firm_id,
        as_of_date="2026-03-31",
        review_type_label="refinancing_review",
        leverage_pressure_label=leverage_pressure_label,
        liquidity_pressure_label=liquidity_pressure_label,
        maturity_wall_label=maturity_wall_label,
        dilution_concern_label=dilution_concern_label,
        covenant_headroom_label=covenant_headroom_label,
        market_access_label=market_access_label,
        rating_perception_label=rating_perception_label,
        status="candidate",
        visibility="internal_only",
        confidence=0.5,
    )


# ---------------------------------------------------------------------------
# Required-string validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"financing_path_id": ""},
        {"firm_id": ""},
        {"as_of_date": ""},
        {"status": ""},
        {"visibility": ""},
    ],
)
def test_path_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _path(**kwargs)


def test_path_coerces_date_to_iso_string():
    p = _path(as_of_date=date(2026, 3, 31))
    assert p.as_of_date == "2026-03-31"


def test_path_is_frozen():
    p = _path()
    with pytest.raises(Exception):
        p.financing_path_id = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


def test_path_rejects_bool_confidence():
    with pytest.raises(ValueError):
        _path(confidence=True)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [-0.01, 1.01, -1.0, 2.0])
def test_path_rejects_out_of_range_confidence(bad):
    with pytest.raises(ValueError):
        _path(confidence=bad)


@pytest.mark.parametrize("good", [0.0, 0.5, 1.0])
def test_path_accepts_in_range_confidence(good):
    p = _path(confidence=good)
    assert p.confidence == float(good)


def test_path_rejects_non_numeric_confidence():
    with pytest.raises(ValueError):
        _path(confidence="0.5")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Source-id tuple validation
# ---------------------------------------------------------------------------


def test_path_rejects_empty_strings_in_id_tuples():
    for kwarg in (
        "need_ids",
        "funding_option_ids",
        "capital_structure_review_ids",
        "market_environment_state_ids",
        "interbank_liquidity_state_ids",
        "bank_credit_review_signal_ids",
        "investor_intent_ids",
    ):
        with pytest.raises(ValueError):
            _path(**{kwarg: ("",)})


def test_path_to_dict_round_trips():
    p = _path(
        need_ids=("corporate_financing_need:n1",),
        funding_option_ids=("funding_option:o1",),
        capital_structure_review_ids=("capital_structure_review:r1",),
        market_environment_state_ids=("market_environment_state:Q3",),
        interbank_liquidity_state_ids=(
            "interbank_liquidity_state:bank_c:2026-03-31",
        ),
        bank_credit_review_signal_ids=(
            "bank_credit_review_signal:bank_c:reference_a:Q3",
        ),
        investor_intent_ids=(
            "investor_intent_signal:investor_a:reference_a:Q3",
        ),
        metadata={"note": "synthetic"},
    )
    out = p.to_dict()
    assert out["need_ids"] == ["corporate_financing_need:n1"]
    assert out["funding_option_ids"] == ["funding_option:o1"]
    assert out["capital_structure_review_ids"] == [
        "capital_structure_review:r1"
    ]
    assert out["market_environment_state_ids"] == [
        "market_environment_state:Q3"
    ]
    assert out["interbank_liquidity_state_ids"] == [
        "interbank_liquidity_state:bank_c:2026-03-31"
    ]
    assert out["bank_credit_review_signal_ids"] == [
        "bank_credit_review_signal:bank_c:reference_a:Q3"
    ]
    assert out["investor_intent_ids"] == [
        "investor_intent_signal:investor_a:reference_a:Q3"
    ]
    assert out["metadata"] == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# Closed-set label vocabularies — accept every listed value
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label", sorted(PATH_TYPE_LABELS))
def test_path_type_labels_accepted(label):
    p = _path(path_type_label=label)
    assert p.path_type_label == label


@pytest.mark.parametrize("label", sorted(PATH_STATUS_LABELS))
def test_path_status_labels_accepted(label):
    p = _path(path_status_label=label)
    assert p.path_status_label == label


@pytest.mark.parametrize("label", sorted(COHERENCE_LABELS))
def test_coherence_labels_accepted(label):
    p = _path(coherence_label=label)
    assert p.coherence_label == label


@pytest.mark.parametrize("label", sorted(CONSTRAINT_LABELS))
def test_constraint_labels_accepted(label):
    p = _path(constraint_label=label)
    assert p.constraint_label == label


@pytest.mark.parametrize("label", sorted(NEXT_REVIEW_LABELS))
def test_next_review_labels_accepted(label):
    p = _path(next_review_label=label)
    assert p.next_review_label == label


# ---------------------------------------------------------------------------
# Closed-set label vocabularies — reject out-of-set values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name",
    [
        "path_type_label",
        "path_status_label",
        "coherence_label",
        "constraint_label",
        "next_review_label",
    ],
)
def test_label_field_rejects_out_of_set_value(field_name):
    with pytest.raises(ValueError):
        _path(**{field_name: "not_a_real_label"})


def test_pinned_path_type_label_set_is_exact():
    assert PATH_TYPE_LABELS == frozenset(
        {
            "refinancing_path",
            "liquidity_buffer_path",
            "capex_funding_path",
            "acquisition_funding_path",
            "balance_sheet_repair_path",
            "working_capital_path",
            "mixed_path",
            "unknown",
        }
    )


def test_pinned_path_status_label_set_is_exact():
    assert PATH_STATUS_LABELS == frozenset(
        {"draft", "under_review", "stale", "superseded", "archived", "unknown"}
    )


def test_pinned_coherence_label_set_is_exact():
    assert COHERENCE_LABELS == frozenset(
        {
            "coherent",
            "partially_coherent",
            "conflicting_evidence",
            "insufficient_evidence",
            "unknown",
        }
    )


def test_pinned_constraint_label_set_is_exact():
    assert CONSTRAINT_LABELS == frozenset(
        {
            "market_access_constraint",
            "liquidity_constraint",
            "leverage_constraint",
            "dilution_constraint",
            "maturity_constraint",
            "covenant_constraint",
            "no_obvious_constraint",
            "unknown",
        }
    )


def test_pinned_next_review_label_set_is_exact():
    assert NEXT_REVIEW_LABELS == frozenset(
        {
            "monitor",
            "revisit_next_period",
            "request_more_evidence",
            "compare_options",
            "escalate_to_capital_structure_review",
            "unknown",
        }
    )


# ---------------------------------------------------------------------------
# Anti-fields — must NOT appear on dataclass or ledger payload
# ---------------------------------------------------------------------------


_FORBIDDEN_FIELDS = {
    "selected_option",
    "optimal_option",
    "approved",
    "executed",
    "commitment",
    "underwriting",
    "syndication",
    "allocation",
    "pricing",
    "interest_rate",
    "spread",
    "coupon",
    "fee",
    "offering_price",
    "target_price",
    "expected_return",
    "recommendation",
    "investment_advice",
    "real_data_value",
    # plus the v1.14.x family standard set
    "amount",
    "loan_amount",
    "coupon_rate",
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
    "order",
    "trade",
    "forecast_value",
    "actual_value",
    "take_up_probability",
    "leverage_ratio",
    "debt_to_equity",
    "wacc",
    "WACC",
}


def test_path_has_no_anti_fields():
    field_names = {
        f.name for f in dataclass_fields(CorporateFinancingPathRecord)
    }
    leaked = field_names & _FORBIDDEN_FIELDS
    assert not leaked


# ---------------------------------------------------------------------------
# Book — CRUD
# ---------------------------------------------------------------------------


def test_book_add_and_get_path():
    book = CorporateFinancingPathBook()
    p = _path()
    book.add_path(p)
    assert book.get_path(p.financing_path_id) is p


def test_book_get_unknown_path_raises():
    book = CorporateFinancingPathBook()
    with pytest.raises(UnknownCorporateFinancingPathError):
        book.get_path("corporate_financing_path:missing")
    with pytest.raises(KeyError):
        book.get_path("corporate_financing_path:missing")


def test_book_duplicate_path_id_rejected():
    book = CorporateFinancingPathBook()
    book.add_path(_path())
    with pytest.raises(DuplicateCorporateFinancingPathError):
        book.add_path(_path())


def test_book_list_paths_returns_all():
    book = CorporateFinancingPathBook()
    book.add_path(_path(financing_path_id="corporate_financing_path:a"))
    book.add_path(_path(financing_path_id="corporate_financing_path:b"))
    assert len(book.list_paths()) == 2


def test_book_list_by_firm():
    book = CorporateFinancingPathBook()
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:a",
            firm_id="firm:p1",
        )
    )
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:b",
            firm_id="firm:p2",
        )
    )
    out = book.list_by_firm("firm:p1")
    assert len(out) == 1
    assert out[0].firm_id == "firm:p1"


def test_book_list_by_path_type():
    book = CorporateFinancingPathBook()
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:a",
            path_type_label="refinancing_path",
        )
    )
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:b",
            path_type_label="capex_funding_path",
        )
    )
    assert len(book.list_by_path_type("capex_funding_path")) == 1


def test_book_list_by_path_status():
    book = CorporateFinancingPathBook()
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:a",
            path_status_label="draft",
        )
    )
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:b",
            path_status_label="archived",
        )
    )
    assert len(book.list_by_path_status("archived")) == 1


def test_book_list_by_coherence():
    book = CorporateFinancingPathBook()
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:a",
            coherence_label="coherent",
        )
    )
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:b",
            coherence_label="insufficient_evidence",
        )
    )
    assert len(book.list_by_coherence("insufficient_evidence")) == 1


def test_book_list_by_constraint():
    book = CorporateFinancingPathBook()
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:a",
            constraint_label="no_obvious_constraint",
        )
    )
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:b",
            constraint_label="market_access_constraint",
        )
    )
    assert len(book.list_by_constraint("market_access_constraint")) == 1


def test_book_list_by_status():
    book = CorporateFinancingPathBook()
    book.add_path(
        _path(financing_path_id="corporate_financing_path:a", status="active")
    )
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:b",
            status="superseded",
        )
    )
    assert len(book.list_by_status("superseded")) == 1


def test_book_list_by_date():
    book = CorporateFinancingPathBook()
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:a",
            as_of_date="2026-03-31",
        )
    )
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:b",
            as_of_date="2026-04-30",
        )
    )
    assert len(book.list_by_date("2026-04-30")) == 1


def test_book_list_by_need():
    book = CorporateFinancingPathBook()
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:a",
            need_ids=("corporate_financing_need:n1",),
        )
    )
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:b",
            need_ids=(
                "corporate_financing_need:n1",
                "corporate_financing_need:n2",
            ),
        )
    )
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:c",
            need_ids=("corporate_financing_need:n3",),
        )
    )
    out = book.list_by_need("corporate_financing_need:n1")
    assert {p.financing_path_id for p in out} == {
        "corporate_financing_path:a",
        "corporate_financing_path:b",
    }
    assert len(book.list_by_need("corporate_financing_need:never")) == 0


def test_book_list_by_funding_option():
    book = CorporateFinancingPathBook()
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:a",
            funding_option_ids=("funding_option:o1",),
        )
    )
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:b",
            funding_option_ids=(
                "funding_option:o1",
                "funding_option:o2",
            ),
        )
    )
    out = book.list_by_funding_option("funding_option:o1")
    assert {p.financing_path_id for p in out} == {
        "corporate_financing_path:a",
        "corporate_financing_path:b",
    }
    assert len(book.list_by_funding_option("funding_option:never")) == 0


def test_book_list_by_capital_structure_review():
    book = CorporateFinancingPathBook()
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:a",
            capital_structure_review_ids=("capital_structure_review:r1",),
        )
    )
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:b",
            capital_structure_review_ids=(
                "capital_structure_review:r1",
                "capital_structure_review:r2",
            ),
        )
    )
    out = book.list_by_capital_structure_review(
        "capital_structure_review:r1"
    )
    assert {p.financing_path_id for p in out} == {
        "corporate_financing_path:a",
        "corporate_financing_path:b",
    }
    assert (
        len(
            book.list_by_capital_structure_review(
                "capital_structure_review:never"
            )
        )
        == 0
    )


def test_book_snapshot_is_deterministic_and_sorted():
    book = CorporateFinancingPathBook()
    book.add_path(_path(financing_path_id="corporate_financing_path:b"))
    book.add_path(_path(financing_path_id="corporate_financing_path:a"))
    snap = book.snapshot()
    assert snap["path_count"] == 2
    assert [p["financing_path_id"] for p in snap["paths"]] == [
        "corporate_financing_path:a",
        "corporate_financing_path:b",
    ]
    assert book.snapshot() == snap


# ---------------------------------------------------------------------------
# Plain-id cross-references — accepted as data, not validated
# ---------------------------------------------------------------------------


def test_can_cite_corporate_financing_need_ids_as_plain_ids():
    book = CorporateFinancingPathBook()
    p = _path(
        need_ids=(
            "corporate_financing_need:reference_a:2026-03-31",
            "corporate_financing_need:reference_a:2026-04-30",
        ),
    )
    book.add_path(p)
    out = book.get_path(p.financing_path_id)
    assert out.need_ids == (
        "corporate_financing_need:reference_a:2026-03-31",
        "corporate_financing_need:reference_a:2026-04-30",
    )


def test_can_cite_funding_option_candidate_ids_as_plain_ids():
    book = CorporateFinancingPathBook()
    p = _path(
        funding_option_ids=(
            "funding_option:reference_a:bank_loan:2026-03-31",
            "funding_option:reference_a:bond_issuance:2026-03-31",
        ),
    )
    book.add_path(p)
    out = book.get_path(p.financing_path_id)
    assert out.funding_option_ids == (
        "funding_option:reference_a:bank_loan:2026-03-31",
        "funding_option:reference_a:bond_issuance:2026-03-31",
    )


def test_can_cite_capital_structure_review_ids_as_plain_ids():
    book = CorporateFinancingPathBook()
    p = _path(
        capital_structure_review_ids=(
            "capital_structure_review:reference_a:refinancing:2026-03-31",
        ),
    )
    book.add_path(p)
    out = book.get_path(p.financing_path_id)
    assert out.capital_structure_review_ids == (
        "capital_structure_review:reference_a:refinancing:2026-03-31",
    )


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_type_exists():
    assert (
        RecordType.CORPORATE_FINANCING_PATH_RECORDED.value
        == "corporate_financing_path_recorded"
    )


def test_add_path_writes_exactly_one_ledger_record():
    ledger = Ledger()
    book = CorporateFinancingPathBook(ledger=ledger)
    book.add_path(_path())
    assert len(ledger.records) == 1
    rec = ledger.records[0]
    assert rec.record_type is RecordType.CORPORATE_FINANCING_PATH_RECORDED
    assert rec.space_id == "financing_paths"


def test_duplicate_add_emits_no_extra_ledger_record():
    ledger = Ledger()
    book = CorporateFinancingPathBook(ledger=ledger)
    book.add_path(_path())
    with pytest.raises(DuplicateCorporateFinancingPathError):
        book.add_path(_path())
    assert len(ledger.records) == 1


def test_ledger_payload_contains_label_fields():
    ledger = Ledger()
    book = CorporateFinancingPathBook(ledger=ledger)
    book.add_path(_path())
    rec = ledger.records[0]
    assert rec.payload["path_type_label"] == "refinancing_path"
    assert rec.payload["path_status_label"] == "draft"
    assert rec.payload["coherence_label"] == "coherent"
    assert rec.payload["constraint_label"] == "no_obvious_constraint"
    assert rec.payload["next_review_label"] == "monitor"


def test_ledger_payload_carries_no_anti_field_keys():
    ledger = Ledger()
    book = CorporateFinancingPathBook(ledger=ledger)
    book.add_path(_path())
    rec = ledger.records[0]
    leaked = set(rec.payload.keys()) & _FORBIDDEN_FIELDS
    assert not leaked


def test_ledger_emits_no_forbidden_event_types():
    ledger = Ledger()
    book = CorporateFinancingPathBook(ledger=ledger)
    book.add_path(_path())
    types = {rec.record_type for rec in ledger.records}
    assert types == {RecordType.CORPORATE_FINANCING_PATH_RECORDED}


def test_book_without_ledger_does_not_raise():
    book = CorporateFinancingPathBook()
    book.add_path(_path())


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_financing_paths_book():
    k = _kernel()
    assert isinstance(k.financing_paths, CorporateFinancingPathBook)
    assert k.financing_paths.ledger is k.ledger
    assert k.financing_paths.clock is k.clock


def test_kernel_simulation_date_uses_clock_for_path():
    k = _kernel()
    k.financing_paths.add_path(_path())
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
        "capital_structure_reviews": k.capital_structure_reviews.snapshot(),
    }
    k.financing_paths.add_path(_path())
    for name, before in snaps_before.items():
        assert getattr(k, name).snapshot() == before, name


# ---------------------------------------------------------------------------
# Builder — deterministic synthetic-label rules
# ---------------------------------------------------------------------------


def test_builder_no_options_marks_insufficient_evidence():
    k = _kernel()
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        need_ids=(),
        funding_option_ids=(),
    )
    assert p.coherence_label == "insufficient_evidence"
    assert p.next_review_label == "request_more_evidence"
    assert p.path_status_label == "draft"


def test_builder_options_without_reviews_is_insufficient():
    k = _kernel()
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        funding_option_ids=("funding_option:o1",),
        capital_structure_review_ids=(),
    )
    assert p.coherence_label == "insufficient_evidence"
    assert p.constraint_label == "unknown"
    assert p.next_review_label == "request_more_evidence"


def test_builder_coherent_when_all_reviews_share_market_access():
    k = _kernel()
    k.capital_structure_reviews.add_candidate(
        _review(review_candidate_id="capital_structure_review:r1", market_access_label="open")
    )
    k.capital_structure_reviews.add_candidate(
        _review(review_candidate_id="capital_structure_review:r2", market_access_label="open")
    )
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        funding_option_ids=("funding_option:o1",),
        capital_structure_review_ids=(
            "capital_structure_review:r1",
            "capital_structure_review:r2",
        ),
    )
    assert p.coherence_label == "coherent"
    assert p.constraint_label == "no_obvious_constraint"
    assert p.next_review_label == "monitor"


def test_builder_partially_coherent_when_reviews_disagree():
    k = _kernel()
    k.capital_structure_reviews.add_candidate(
        _review(review_candidate_id="capital_structure_review:r1", market_access_label="open")
    )
    k.capital_structure_reviews.add_candidate(
        _review(review_candidate_id="capital_structure_review:r2", market_access_label="selective")
    )
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        funding_option_ids=("funding_option:o1",),
        capital_structure_review_ids=(
            "capital_structure_review:r1",
            "capital_structure_review:r2",
        ),
    )
    assert p.coherence_label == "partially_coherent"
    assert p.next_review_label == "compare_options"


def test_builder_market_access_constraint_dominates():
    k = _kernel()
    k.capital_structure_reviews.add_candidate(
        _review(
            review_candidate_id="capital_structure_review:r1",
            market_access_label="constrained",
            liquidity_pressure_label="stressed",
            leverage_pressure_label="high",
        )
    )
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        funding_option_ids=("funding_option:o1",),
        capital_structure_review_ids=("capital_structure_review:r1",),
    )
    assert p.constraint_label == "market_access_constraint"
    assert p.next_review_label == "escalate_to_capital_structure_review"


def test_builder_liquidity_constraint_when_no_market_access_issue():
    k = _kernel()
    k.capital_structure_reviews.add_candidate(
        _review(
            review_candidate_id="capital_structure_review:r1",
            market_access_label="open",
            liquidity_pressure_label="stressed",
        )
    )
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        funding_option_ids=("funding_option:o1",),
        capital_structure_review_ids=("capital_structure_review:r1",),
    )
    assert p.constraint_label == "liquidity_constraint"
    assert p.next_review_label == "escalate_to_capital_structure_review"


def test_builder_path_type_from_single_need_purpose():
    k = _kernel()
    k.corporate_financing_needs.add_need(
        _need(need_id="corporate_financing_need:n1", funding_purpose_label="growth_capex")
    )
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        need_ids=("corporate_financing_need:n1",),
    )
    assert p.path_type_label == "capex_funding_path"


def test_builder_path_type_mixed_when_needs_disagree():
    k = _kernel()
    k.corporate_financing_needs.add_need(
        _need(need_id="corporate_financing_need:n1", funding_purpose_label="refinancing")
    )
    k.corporate_financing_needs.add_need(
        _need(need_id="corporate_financing_need:n2", funding_purpose_label="acquisition")
    )
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        need_ids=(
            "corporate_financing_need:n1",
            "corporate_financing_need:n2",
        ),
    )
    assert p.path_type_label == "mixed_path"


def test_builder_path_type_unknown_when_no_needs_cited():
    k = _kernel()
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        need_ids=(),
    )
    assert p.path_type_label == "unknown"


def test_builder_default_path_id_is_deterministic():
    k = _kernel()
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
    )
    assert (
        p.financing_path_id
        == "corporate_financing_path:firm:reference_a:2026-03-31"
    )


def test_builder_writes_one_ledger_record():
    k = _kernel()
    build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
    )
    paths = [
        r
        for r in k.ledger.records
        if r.record_type is RecordType.CORPORATE_FINANCING_PATH_RECORDED
    ]
    assert len(paths) == 1


def test_builder_is_deterministic_across_fresh_kernels():
    """Same cited-record content + same args → same labels."""
    def build(kernel):
        kernel.corporate_financing_needs.add_need(
            _need(
                need_id="corporate_financing_need:n1",
                funding_purpose_label="refinancing",
            )
        )
        kernel.capital_structure_reviews.add_candidate(
            _review(
                review_candidate_id="capital_structure_review:r1",
                market_access_label="constrained",
            )
        )
        return build_corporate_financing_path(
            kernel,
            firm_id="firm:reference_a",
            as_of_date="2026-03-31",
            need_ids=("corporate_financing_need:n1",),
            funding_option_ids=("funding_option:o1",),
            capital_structure_review_ids=("capital_structure_review:r1",),
        )

    k_a = _kernel()
    k_b = _kernel()
    p_a = build(k_a)
    p_b = build(k_b)
    a = p_a.to_dict()
    b = p_b.to_dict()
    assert a == b


def test_builder_unresolved_ids_kept_but_skipped_for_label_derivation():
    """Cited ids that don't resolve in the kernel are stored on the
    record but do not contribute to label synthesis. With no
    resolvable need or review, the path_type / coherence / constraint
    labels should fall back to the empty-evidence defaults even
    though the ids appear on the record.
    """
    k = _kernel()
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        need_ids=("corporate_financing_need:does_not_exist",),
        funding_option_ids=("funding_option:o1",),
        capital_structure_review_ids=(
            "capital_structure_review:does_not_exist",
        ),
    )
    assert p.path_type_label == "unknown"
    # No reviews could be resolved, so coherence falls back to
    # insufficient_evidence and constraint is unknown.
    assert p.coherence_label == "insufficient_evidence"
    assert p.constraint_label == "unknown"
    # But the cited ids are still preserved on the record.
    assert p.need_ids == ("corporate_financing_need:does_not_exist",)
    assert p.capital_structure_review_ids == (
        "capital_structure_review:does_not_exist",
    )


def test_builder_does_not_scan_books_globally():
    """The helper must read only the cited ids — never iterate the
    full need or review books. We monkey-patch every list_* on the
    cited books to raise; if the helper calls any of them, the test
    fails.
    """
    k = _kernel()
    k.corporate_financing_needs.add_need(
        _need(need_id="corporate_financing_need:n1", funding_purpose_label="refinancing")
    )
    k.capital_structure_reviews.add_candidate(
        _review(review_candidate_id="capital_structure_review:r1")
    )

    def _boom(*_a, **_kw):  # pragma: no cover - must not fire
        raise AssertionError(
            "helper performed a global scan via list_* — forbidden"
        )

    # Trip-wires on every list/snapshot accessor of the cited books.
    for book_attr in ("corporate_financing_needs", "capital_structure_reviews"):
        book = getattr(k, book_attr)
        for method_name in dir(book):
            if method_name.startswith("list_") or method_name == "snapshot":
                setattr(book, method_name, _boom)

    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        need_ids=("corporate_financing_need:n1",),
        funding_option_ids=("funding_option:o1",),
        capital_structure_review_ids=("capital_structure_review:r1",),
    )
    assert p.path_type_label == "refinancing_path"


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
        / "financing_paths.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, token


# ---------------------------------------------------------------------------
# v1.15.6 — IndicativeMarketPressureRecord citation slot + helper override
# ---------------------------------------------------------------------------


def _pressure(
    *,
    market_pressure_id: str,
    security_id: str = "security:target",
    market_access_label: str = "open",
    demand_pressure_label: str = "balanced",
    liquidity_pressure_label: str = "normal",
    volatility_pressure_label: str = "calm",
    financing_relevance_label: str = "neutral_for_financing",
):
    from world.market_pressure import IndicativeMarketPressureRecord

    return IndicativeMarketPressureRecord(
        market_pressure_id=market_pressure_id,
        security_id=security_id,
        as_of_date="2026-03-31",
        demand_pressure_label=demand_pressure_label,
        liquidity_pressure_label=liquidity_pressure_label,
        volatility_pressure_label=volatility_pressure_label,
        market_access_label=market_access_label,
        financing_relevance_label=financing_relevance_label,
        status="active",
        visibility="internal_only",
        confidence=0.5,
    )


def test_v1_15_6_path_accepts_indicative_market_pressure_ids():
    p = _path(
        indicative_market_pressure_ids=(
            "indicative_market_pressure:security:reference_a:2026-03-31",
        ),
    )
    assert p.indicative_market_pressure_ids == (
        "indicative_market_pressure:security:reference_a:2026-03-31",
    )


def test_v1_15_6_path_rejects_empty_strings_in_pressure_tuple():
    with pytest.raises(ValueError):
        _path(indicative_market_pressure_ids=("",))


def test_v1_15_6_path_to_dict_round_trips_pressure_ids():
    p = _path(
        indicative_market_pressure_ids=(
            "indicative_market_pressure:security:reference_a:2026-03-31",
        ),
    )
    out = p.to_dict()
    assert out["indicative_market_pressure_ids"] == [
        "indicative_market_pressure:security:reference_a:2026-03-31"
    ]


def test_v1_15_6_book_list_by_indicative_market_pressure():
    book = CorporateFinancingPathBook()
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:a",
            indicative_market_pressure_ids=(
                "indicative_market_pressure:p1",
            ),
        )
    )
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:b",
            indicative_market_pressure_ids=(
                "indicative_market_pressure:p1",
                "indicative_market_pressure:p2",
            ),
        )
    )
    book.add_path(
        _path(
            financing_path_id="corporate_financing_path:c",
            indicative_market_pressure_ids=(
                "indicative_market_pressure:p3",
            ),
        )
    )
    out = book.list_by_indicative_market_pressure(
        "indicative_market_pressure:p1"
    )
    assert {p.financing_path_id for p in out} == {
        "corporate_financing_path:a",
        "corporate_financing_path:b",
    }
    assert (
        len(
            book.list_by_indicative_market_pressure(
                "indicative_market_pressure:never_referenced"
            )
        )
        == 0
    )


def test_v1_15_6_ledger_payload_carries_pressure_ids_key():
    ledger = Ledger()
    book = CorporateFinancingPathBook(ledger=ledger)
    book.add_path(
        _path(
            indicative_market_pressure_ids=(
                "indicative_market_pressure:security:reference_a:2026-03-31",
            ),
        )
    )
    rec = ledger.records[0]
    assert "indicative_market_pressure_ids" in rec.payload
    assert list(rec.payload["indicative_market_pressure_ids"]) == [
        "indicative_market_pressure:security:reference_a:2026-03-31"
    ]


def test_v1_15_6_builder_constrained_pressure_overrides_constraint():
    """When any cited pressure has market_access_label =
    constrained, the path's constraint_label is forced to
    market_access_constraint regardless of the review-derived
    label."""
    k = _kernel()
    k.capital_structure_reviews.add_candidate(
        _review(
            review_candidate_id="capital_structure_review:r1",
            market_access_label="open",  # review thinks access is fine
            liquidity_pressure_label="moderate",
            leverage_pressure_label="moderate",
            maturity_wall_label="manageable",
            covenant_headroom_label="comfortable",
            dilution_concern_label="low",
        )
    )
    k.indicative_market_pressure.add_record(
        _pressure(
            market_pressure_id="indicative_market_pressure:p_constrained",
            market_access_label="constrained",
        )
    )
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        funding_option_ids=("funding_option:o1",),
        capital_structure_review_ids=("capital_structure_review:r1",),
        indicative_market_pressure_ids=(
            "indicative_market_pressure:p_constrained",
        ),
    )
    assert p.constraint_label == "market_access_constraint"
    # Reviews said open, but pressure said constrained → conflict.
    assert p.coherence_label == "conflicting_evidence"
    # Conflict promotes next_review → compare_options.
    assert p.next_review_label == "compare_options"
    # Pressure ids are stored on the record.
    assert p.indicative_market_pressure_ids == (
        "indicative_market_pressure:p_constrained",
    )


def test_v1_15_6_builder_closed_pressure_also_overrides_constraint():
    k = _kernel()
    k.capital_structure_reviews.add_candidate(
        _review(
            review_candidate_id="capital_structure_review:r1",
            market_access_label="open",
        )
    )
    k.indicative_market_pressure.add_record(
        _pressure(
            market_pressure_id="indicative_market_pressure:p_closed",
            market_access_label="closed",
        )
    )
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        funding_option_ids=("funding_option:o1",),
        capital_structure_review_ids=("capital_structure_review:r1",),
        indicative_market_pressure_ids=(
            "indicative_market_pressure:p_closed",
        ),
    )
    assert p.constraint_label == "market_access_constraint"
    assert p.coherence_label == "conflicting_evidence"


def test_v1_15_6_builder_open_pressure_does_not_override():
    """When pressure says access is open, the path's constraint
    derivation falls through to the review-based rule (no
    pressure-driven override)."""
    k = _kernel()
    k.capital_structure_reviews.add_candidate(
        _review(
            review_candidate_id="capital_structure_review:r1",
            market_access_label="open",
        )
    )
    k.indicative_market_pressure.add_record(
        _pressure(
            market_pressure_id="indicative_market_pressure:p_open",
            market_access_label="open",
        )
    )
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        funding_option_ids=("funding_option:o1",),
        capital_structure_review_ids=("capital_structure_review:r1",),
        indicative_market_pressure_ids=(
            "indicative_market_pressure:p_open",
        ),
    )
    assert p.constraint_label == "no_obvious_constraint"
    assert p.coherence_label == "coherent"


def test_v1_15_6_builder_does_not_scan_pressure_book_globally():
    """The helper must read only the cited pressure ids — never
    iterate the full indicative_market_pressure book."""
    k = _kernel()
    k.capital_structure_reviews.add_candidate(
        _review(review_candidate_id="capital_structure_review:r1")
    )
    k.indicative_market_pressure.add_record(
        _pressure(market_pressure_id="indicative_market_pressure:cited")
    )

    def _boom(*_a, **_kw):  # pragma: no cover - must not fire
        raise AssertionError(
            "helper performed a global scan via list_* / snapshot — forbidden"
        )

    book = k.indicative_market_pressure
    for method_name in dir(book):
        if method_name.startswith("list_") or method_name == "snapshot":
            setattr(book, method_name, _boom)

    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        funding_option_ids=("funding_option:o1",),
        capital_structure_review_ids=("capital_structure_review:r1",),
        indicative_market_pressure_ids=(
            "indicative_market_pressure:cited",
        ),
    )
    # Helper completed without tripping the trip-wire.
    assert p.indicative_market_pressure_ids == (
        "indicative_market_pressure:cited",
    )


def test_v1_15_6_builder_unresolved_pressure_id_is_silently_skipped():
    """Mirrors the v1.14.4 behaviour for need / review ids: an
    unresolved pressure id is kept on the record (cited) but not
    used during label derivation."""
    k = _kernel()
    k.capital_structure_reviews.add_candidate(
        _review(
            review_candidate_id="capital_structure_review:r1",
            market_access_label="open",
        )
    )
    p = build_corporate_financing_path(
        k,
        firm_id="firm:reference_a",
        as_of_date="2026-03-31",
        funding_option_ids=("funding_option:o1",),
        capital_structure_review_ids=("capital_structure_review:r1",),
        indicative_market_pressure_ids=(
            "indicative_market_pressure:does_not_exist",
        ),
    )
    # No resolvable pressure → no override, falls through.
    assert p.constraint_label == "no_obvious_constraint"
    assert p.coherence_label == "coherent"
    # Cited id still preserved on the record.
    assert p.indicative_market_pressure_ids == (
        "indicative_market_pressure:does_not_exist",
    )
