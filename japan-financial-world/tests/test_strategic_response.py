"""
Tests for v1.10.3 CorporateStrategicResponseCandidate +
StrategicResponseCandidateBook.

Covers field validation, immutability, ``add_candidate``
deduplication, unknown lookup, every list / filter method,
deterministic snapshots, ledger emission with the new
``RecordType.CORPORATE_STRATEGIC_RESPONSE_CANDIDATE_ADDED``, kernel
wiring of the new ``StrategicResponseCandidateBook``, the
no-mutation guarantee against every other v0/v1 source-of-truth
book in the kernel (including the v1.10.1 stewardship book, the
v1.10.2 dialogue book, and the v1.10.3 sibling escalation book),
and the v1.10.3 scope discipline that the record carries
*candidate metadata only* and never a transcript / content / notes
/ attendees / buyback / dividend-change / divestment / merger /
board-change / disclosure-filed field.

Identifier and tag strings used in this test suite are
jurisdiction-neutral and synthetic; no Japan-specific institution
name, regulator, code, or threshold appears anywhere in the test
body.
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
from world.state import State
from world.strategic_response import (
    CorporateStrategicResponseCandidate,
    DuplicateResponseCandidateError,
    StrategicResponseCandidateBook,
    UnknownResponseCandidateError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _candidate(
    *,
    response_candidate_id: str = (
        "response:reference_manufacturer_a:capital_allocation:2026Q1:001"
    ),
    company_id: str = "firm:reference_manufacturer_a",
    as_of_date: str = "2026-05-01",
    response_type: str = "capital_allocation_review",
    status: str = "draft",
    priority: str = "medium",
    horizon: str = "medium_term",
    expected_effect_label: str = "expected_efficiency_improvement_candidate",
    constraint_label: str = "subject_to_board_review",
    visibility: str = "internal_only",
    trigger_theme_ids: tuple[str, ...] = (),
    trigger_dialogue_ids: tuple[str, ...] = (),
    trigger_signal_ids: tuple[str, ...] = (),
    trigger_valuation_ids: tuple[str, ...] = (),
    trigger_industry_condition_ids: tuple[str, ...] = (),
    trigger_market_condition_ids: tuple[str, ...] = (),
    trigger_market_environment_state_ids: tuple[str, ...] = (),
    next_review_date: str | None = None,
    metadata: dict | None = None,
) -> CorporateStrategicResponseCandidate:
    return CorporateStrategicResponseCandidate(
        response_candidate_id=response_candidate_id,
        company_id=company_id,
        as_of_date=as_of_date,
        response_type=response_type,
        status=status,
        priority=priority,
        horizon=horizon,
        expected_effect_label=expected_effect_label,
        constraint_label=constraint_label,
        visibility=visibility,
        trigger_theme_ids=trigger_theme_ids,
        trigger_dialogue_ids=trigger_dialogue_ids,
        trigger_signal_ids=trigger_signal_ids,
        trigger_valuation_ids=trigger_valuation_ids,
        trigger_industry_condition_ids=trigger_industry_condition_ids,
        trigger_market_condition_ids=trigger_market_condition_ids,
        trigger_market_environment_state_ids=(
            trigger_market_environment_state_ids
        ),
        next_review_date=next_review_date,
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


# ---------------------------------------------------------------------------
# Record — field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"response_candidate_id": ""},
        {"company_id": ""},
        {"as_of_date": ""},
        {"response_type": ""},
        {"status": ""},
        {"priority": ""},
        {"horizon": ""},
        {"expected_effect_label": ""},
        {"constraint_label": ""},
        {"visibility": ""},
    ],
)
def test_response_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _candidate(**kwargs)


@pytest.mark.parametrize(
    "tuple_field",
    [
        "trigger_theme_ids",
        "trigger_dialogue_ids",
        "trigger_signal_ids",
        "trigger_valuation_ids",
        "trigger_industry_condition_ids",
        "trigger_market_condition_ids",
        "trigger_market_environment_state_ids",
    ],
)
def test_response_rejects_empty_strings_in_tuple_fields(tuple_field):
    bad = {tuple_field: ("valid", "")}
    with pytest.raises(ValueError):
        _candidate(**bad)


def test_response_coerces_dates_to_iso_strings():
    c = _candidate(
        as_of_date=date(2026, 5, 1),
        next_review_date=date(2026, 8, 1),
    )
    assert c.as_of_date == "2026-05-01"
    assert c.next_review_date == "2026-08-01"


def test_response_next_review_date_optional():
    c = _candidate(next_review_date=None)
    assert c.next_review_date is None


def test_response_rejects_non_date_next_review_date():
    with pytest.raises(ValueError):
        _candidate(next_review_date=12345)  # type: ignore[arg-type]


def test_response_rejects_next_review_date_before_as_of_date():
    with pytest.raises(ValueError):
        _candidate(as_of_date="2026-05-01", next_review_date="2026-04-01")


def test_response_accepts_next_review_date_equal_as_of_date():
    c = _candidate(as_of_date="2026-05-01", next_review_date="2026-05-01")
    assert c.as_of_date == c.next_review_date == "2026-05-01"


# ---------------------------------------------------------------------------
# Immutability & round-trip
# ---------------------------------------------------------------------------


def test_response_is_frozen():
    c = _candidate()
    with pytest.raises(Exception):
        c.response_candidate_id = "tampered"  # type: ignore[misc]


def test_response_to_dict_round_trips_fields():
    c = _candidate(
        trigger_theme_ids=("theme:cap",),
        trigger_dialogue_ids=("dialogue:001",),
        trigger_signal_ids=("signal:reference_firm_pressure_001",),
        trigger_valuation_ids=("valuation:reference_demo_001",),
        trigger_industry_condition_ids=(
            "industry_condition:reference_manufacturing:2026Q1",
        ),
        trigger_market_condition_ids=(
            "market_condition:reference_rates_general:2026-03-31",
        ),
        next_review_date="2026-08-01",
        metadata={"note": "synthetic"},
    )
    out = c.to_dict()
    assert out["response_candidate_id"] == c.response_candidate_id
    assert out["company_id"] == c.company_id
    assert out["as_of_date"] == c.as_of_date
    assert out["response_type"] == c.response_type
    assert out["status"] == c.status
    assert out["priority"] == c.priority
    assert out["horizon"] == c.horizon
    assert out["expected_effect_label"] == c.expected_effect_label
    assert out["constraint_label"] == c.constraint_label
    assert out["next_review_date"] == "2026-08-01"
    assert out["visibility"] == c.visibility
    assert out["trigger_theme_ids"] == ["theme:cap"]
    assert out["trigger_dialogue_ids"] == ["dialogue:001"]
    assert out["trigger_signal_ids"] == ["signal:reference_firm_pressure_001"]
    assert out["trigger_valuation_ids"] == ["valuation:reference_demo_001"]
    assert out["trigger_industry_condition_ids"] == [
        "industry_condition:reference_manufacturing:2026Q1"
    ]
    assert out["trigger_market_condition_ids"] == [
        "market_condition:reference_rates_general:2026-03-31"
    ]
    assert out["metadata"] == {"note": "synthetic"}


def test_response_default_trigger_industry_condition_ids_is_empty_tuple():
    """v1.10.4.1 added field is additive and defaults to ()."""
    c = _candidate()
    assert c.trigger_industry_condition_ids == ()


def test_response_default_trigger_market_condition_ids_is_empty_tuple():
    """v1.11.0 added field is additive and defaults to ()."""
    c = _candidate()
    assert c.trigger_market_condition_ids == ()


def test_response_metadata_is_independent_copy():
    src = {"note": "synthetic"}
    c = _candidate(metadata=src)
    src["note"] = "tampered"
    assert c.metadata["note"] == "synthetic"


# ---------------------------------------------------------------------------
# Anti-fields — no execution / transcript fields
# ---------------------------------------------------------------------------


def test_response_record_has_no_execution_or_content_field():
    """
    v1.10.3 corporate response candidate must store metadata only —
    never fields that would imply executed corporate actions or
    transcript content.
    """
    field_names = {
        f.name
        for f in dataclass_fields(CorporateStrategicResponseCandidate)
    }
    forbidden = {
        "transcript",
        "content",
        "contents",
        "notes",
        "minutes",
        "attendees",
        "buyback_executed",
        "dividend_changed",
        "divestment_executed",
        "merger_executed",
        "board_change_executed",
        "disclosure_filed",
        "verbatim",
        "paraphrase",
        "paraphrased",
        "body",
    }
    leaked = field_names & forbidden
    assert not leaked, (
        f"v1.10.3 corporate response candidate must not carry "
        f"execution / transcript fields; found: {sorted(leaked)}"
    )


# ---------------------------------------------------------------------------
# Book — add / get / dedup / unknown
# ---------------------------------------------------------------------------


def test_add_and_get_response_candidate():
    book = StrategicResponseCandidateBook()
    c = _candidate()
    book.add_candidate(c)
    assert book.get_candidate(c.response_candidate_id) is c


def test_get_response_unknown_raises():
    book = StrategicResponseCandidateBook()
    with pytest.raises(UnknownResponseCandidateError):
        book.get_candidate("does-not-exist")


def test_unknown_response_error_is_keyerror():
    err = UnknownResponseCandidateError("missing")
    assert isinstance(err, KeyError)


def test_duplicate_response_candidate_id_rejected():
    book = StrategicResponseCandidateBook()
    book.add_candidate(_candidate(response_candidate_id="resp:dup"))
    with pytest.raises(DuplicateResponseCandidateError):
        book.add_candidate(_candidate(response_candidate_id="resp:dup"))


def test_add_response_returns_record():
    book = StrategicResponseCandidateBook()
    c = _candidate()
    returned = book.add_candidate(c)
    assert returned is c


# ---------------------------------------------------------------------------
# Listings & filters
# ---------------------------------------------------------------------------


def test_list_response_candidates_in_insertion_order():
    book = StrategicResponseCandidateBook()
    book.add_candidate(_candidate(response_candidate_id="resp:a"))
    book.add_candidate(_candidate(response_candidate_id="resp:b"))
    book.add_candidate(_candidate(response_candidate_id="resp:c"))
    listed = book.list_candidates()
    assert tuple(c.response_candidate_id for c in listed) == (
        "resp:a",
        "resp:b",
        "resp:c",
    )


def test_list_response_candidates_empty_book():
    assert StrategicResponseCandidateBook().list_candidates() == ()


def test_list_response_by_company():
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:m",
            company_id="firm:reference_manufacturer_a",
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:r",
            company_id="firm:reference_retailer_a",
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:m2",
            company_id="firm:reference_manufacturer_a",
        )
    )
    matched = book.list_by_company("firm:reference_manufacturer_a")
    assert tuple(c.response_candidate_id for c in matched) == (
        "resp:m",
        "resp:m2",
    )


def test_list_response_by_type():
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:cap",
            response_type="capital_allocation_review",
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:gov",
            response_type="governance_change_review",
        )
    )
    matched = book.list_by_type("governance_change_review")
    assert tuple(c.response_candidate_id for c in matched) == ("resp:gov",)


def test_list_response_by_status():
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(response_candidate_id="resp:draft", status="draft")
    )
    book.add_candidate(
        _candidate(response_candidate_id="resp:active", status="active")
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:withdrawn", status="withdrawn"
        )
    )
    assert tuple(
        c.response_candidate_id for c in book.list_by_status("active")
    ) == ("resp:active",)


def test_list_response_by_priority():
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(response_candidate_id="resp:low", priority="low")
    )
    book.add_candidate(
        _candidate(response_candidate_id="resp:hi", priority="high")
    )
    assert tuple(
        c.response_candidate_id for c in book.list_by_priority("high")
    ) == ("resp:hi",)


def test_list_response_by_theme():
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:cap",
            trigger_theme_ids=("theme:cap", "theme:gov"),
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:gov_only",
            trigger_theme_ids=("theme:gov",),
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:none", trigger_theme_ids=()
        )
    )
    assert tuple(
        c.response_candidate_id for c in book.list_by_theme("theme:cap")
    ) == ("resp:cap",)
    assert sorted(
        c.response_candidate_id for c in book.list_by_theme("theme:gov")
    ) == ["resp:cap", "resp:gov_only"]
    assert book.list_by_theme("theme:missing") == ()


def test_list_response_by_dialogue():
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:linked",
            trigger_dialogue_ids=("dialogue:001",),
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:other",
            trigger_dialogue_ids=("dialogue:002",),
        )
    )
    assert tuple(
        c.response_candidate_id
        for c in book.list_by_dialogue("dialogue:001")
    ) == ("resp:linked",)


def test_list_response_by_industry_condition():
    """v1.10.4.1: type-correct cross-reference filter for v1.10.4
    industry-condition ids."""
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:cited",
            trigger_industry_condition_ids=(
                "industry_condition:cap",
                "industry_condition:gov",
            ),
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:gov_only",
            trigger_industry_condition_ids=("industry_condition:gov",),
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:none",
            trigger_industry_condition_ids=(),
        )
    )
    assert tuple(
        c.response_candidate_id
        for c in book.list_by_industry_condition("industry_condition:cap")
    ) == ("resp:cited",)
    assert sorted(
        c.response_candidate_id
        for c in book.list_by_industry_condition("industry_condition:gov")
    ) == ["resp:cited", "resp:gov_only"]
    assert (
        book.list_by_industry_condition("industry_condition:missing") == ()
    )


def test_list_by_industry_condition_does_not_match_signal_slot():
    """A condition_id sitting in trigger_signal_ids must NOT be
    surfaced by list_by_industry_condition. Field-level
    disambiguation is what v1.10.4.1 buys."""
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:miscategorized",
            trigger_signal_ids=("industry_condition:cap",),
        )
    )
    assert (
        book.list_by_industry_condition("industry_condition:cap") == ()
    )


def test_list_response_by_market_condition():
    """v1.11.0: type-correct cross-reference filter for v1.11.0
    market-condition ids."""
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:cited",
            trigger_market_condition_ids=(
                "market_condition:rates",
                "market_condition:credit",
            ),
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:credit_only",
            trigger_market_condition_ids=("market_condition:credit",),
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:none",
            trigger_market_condition_ids=(),
        )
    )
    assert tuple(
        c.response_candidate_id
        for c in book.list_by_market_condition("market_condition:rates")
    ) == ("resp:cited",)
    assert sorted(
        c.response_candidate_id
        for c in book.list_by_market_condition("market_condition:credit")
    ) == ["resp:cited", "resp:credit_only"]
    assert (
        book.list_by_market_condition("market_condition:missing") == ()
    )


def test_list_response_by_market_environment_state():
    """v1.12.2: type-correct cross-reference filter for v1.12.2
    market-environment-state ids."""
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:env_cited",
            trigger_market_environment_state_ids=(
                "market_environment:2026-03-31",
                "market_environment:2026-06-30",
            ),
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:env_q2_only",
            trigger_market_environment_state_ids=(
                "market_environment:2026-06-30",
            ),
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:env_none",
            trigger_market_environment_state_ids=(),
        )
    )
    assert tuple(
        c.response_candidate_id
        for c in book.list_by_market_environment_state(
            "market_environment:2026-03-31"
        )
    ) == ("resp:env_cited",)
    assert sorted(
        c.response_candidate_id
        for c in book.list_by_market_environment_state(
            "market_environment:2026-06-30"
        )
    ) == ["resp:env_cited", "resp:env_q2_only"]
    assert (
        book.list_by_market_environment_state("market_environment:missing")
        == ()
    )


def test_list_by_market_environment_state_does_not_match_other_slots():
    """An environment-state id sitting in any other trigger slot
    must NOT be surfaced by list_by_market_environment_state.
    Field-level disambiguation is what v1.12.2 buys."""
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:in_signal_slot",
            trigger_signal_ids=("market_environment:2026-03-31",),
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:in_industry_slot",
            trigger_industry_condition_ids=(
                "market_environment:2026-03-31",
            ),
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:in_market_condition_slot",
            trigger_market_condition_ids=(
                "market_environment:2026-03-31",
            ),
        )
    )
    assert (
        book.list_by_market_environment_state(
            "market_environment:2026-03-31"
        )
        == ()
    )


def test_list_by_market_condition_does_not_match_other_slots():
    """A market-condition id sitting in any other trigger slot
    must NOT be surfaced by list_by_market_condition. Field-level
    disambiguation is what v1.11.0 buys."""
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:in_signal_slot",
            trigger_signal_ids=("market_condition:rates",),
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:in_industry_slot",
            trigger_industry_condition_ids=("market_condition:rates",),
        )
    )
    assert (
        book.list_by_market_condition("market_condition:rates") == ()
    )


def test_list_response_by_date_filters_exactly():
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:may", as_of_date="2026-05-01"
        )
    )
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:jun", as_of_date="2026-06-01"
        )
    )
    may = book.list_by_date("2026-05-01")
    jun = book.list_by_date("2026-06-01")
    miss = book.list_by_date("2026-07-01")
    assert tuple(c.response_candidate_id for c in may) == ("resp:may",)
    assert tuple(c.response_candidate_id for c in jun) == ("resp:jun",)
    assert miss == ()


def test_list_response_by_date_accepts_date_object():
    book = StrategicResponseCandidateBook()
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:may", as_of_date="2026-05-01"
        )
    )
    matched = book.list_by_date(date(2026, 5, 1))
    assert tuple(c.response_candidate_id for c in matched) == ("resp:may",)


# ---------------------------------------------------------------------------
# Plain-id cross-references — no validation against any other book
# ---------------------------------------------------------------------------


def test_response_can_reference_unresolved_trigger_ids():
    book = StrategicResponseCandidateBook()
    c = _candidate(
        trigger_theme_ids=("theme:not-in-stewardship-book",),
        trigger_dialogue_ids=("dialogue:not-in-dialogue-book",),
        trigger_signal_ids=("signal:not-in-signal-book",),
        trigger_valuation_ids=("valuation:not-in-valuation-book",),
        trigger_industry_condition_ids=(
            "industry_condition:not-in-industry-book",
        ),
        trigger_market_condition_ids=(
            "market_condition:not-in-market-book",
        ),
    )
    book.add_candidate(c)
    assert book.get_candidate(c.response_candidate_id) is c


# ---------------------------------------------------------------------------
# Snapshot determinism
# ---------------------------------------------------------------------------


def test_response_snapshot_is_deterministic_and_sorted():
    book = StrategicResponseCandidateBook()
    book.add_candidate(_candidate(response_candidate_id="resp:z"))
    book.add_candidate(_candidate(response_candidate_id="resp:a"))
    book.add_candidate(_candidate(response_candidate_id="resp:m"))

    snap1 = book.snapshot()
    snap2 = book.snapshot()
    assert snap1 == snap2
    assert snap1["candidate_count"] == 3
    assert [c["response_candidate_id"] for c in snap1["candidates"]] == [
        "resp:a",
        "resp:m",
        "resp:z",
    ]


def test_response_snapshot_empty_book():
    snap = StrategicResponseCandidateBook().snapshot()
    assert snap == {"candidate_count": 0, "candidates": []}


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_response_record_type_exists():
    assert (
        RecordType("corporate_strategic_response_candidate_added")
        is RecordType.CORPORATE_STRATEGIC_RESPONSE_CANDIDATE_ADDED
    )
    assert (
        RecordType.CORPORATE_STRATEGIC_RESPONSE_CANDIDATE_ADDED.value
        == "corporate_strategic_response_candidate_added"
    )


def test_add_response_writes_exactly_one_ledger_record():
    ledger = Ledger()
    book = StrategicResponseCandidateBook(ledger=ledger)
    book.add_candidate(_candidate(response_candidate_id="resp:emit"))
    records = ledger.filter(
        event_type="corporate_strategic_response_candidate_added"
    )
    assert len(records) == 1
    record = records[0]
    assert (
        record.record_type
        is RecordType.CORPORATE_STRATEGIC_RESPONSE_CANDIDATE_ADDED
    )
    assert record.object_id == "resp:emit"
    assert record.source == "firm:reference_manufacturer_a"
    assert record.space_id == "strategic_response"
    assert record.agent_id == "firm:reference_manufacturer_a"
    assert record.visibility == "internal_only"


def test_add_response_payload_carries_full_field_set():
    ledger = Ledger()
    book = StrategicResponseCandidateBook(ledger=ledger)
    book.add_candidate(
        _candidate(
            response_candidate_id="resp:payload",
            trigger_theme_ids=("theme:cap",),
            trigger_dialogue_ids=("dialogue:001",),
            trigger_signal_ids=("signal:reference_firm_pressure_001",),
            trigger_valuation_ids=("valuation:reference_demo_001",),
            trigger_industry_condition_ids=(
                "industry_condition:reference_manufacturing:2026Q1",
            ),
            trigger_market_condition_ids=(
                "market_condition:reference_rates_general:2026-03-31",
            ),
            next_review_date="2026-08-01",
        )
    )
    payload = ledger.filter(
        event_type="corporate_strategic_response_candidate_added"
    )[-1].payload
    assert payload["response_candidate_id"] == "resp:payload"
    assert payload["company_id"] == "firm:reference_manufacturer_a"
    assert payload["as_of_date"] == "2026-05-01"
    assert payload["response_type"] == "capital_allocation_review"
    assert payload["status"] == "draft"
    assert payload["priority"] == "medium"
    assert payload["horizon"] == "medium_term"
    assert (
        payload["expected_effect_label"]
        == "expected_efficiency_improvement_candidate"
    )
    assert payload["constraint_label"] == "subject_to_board_review"
    assert payload["next_review_date"] == "2026-08-01"
    assert payload["visibility"] == "internal_only"
    assert tuple(payload["trigger_theme_ids"]) == ("theme:cap",)
    assert tuple(payload["trigger_dialogue_ids"]) == ("dialogue:001",)
    assert tuple(payload["trigger_signal_ids"]) == (
        "signal:reference_firm_pressure_001",
    )
    assert tuple(payload["trigger_valuation_ids"]) == (
        "valuation:reference_demo_001",
    )
    assert tuple(payload["trigger_industry_condition_ids"]) == (
        "industry_condition:reference_manufacturing:2026Q1",
    )
    assert tuple(payload["trigger_market_condition_ids"]) == (
        "market_condition:reference_rates_general:2026-03-31",
    )


def test_add_response_payload_carries_no_execution_or_content_keys():
    ledger = Ledger()
    book = StrategicResponseCandidateBook(ledger=ledger)
    book.add_candidate(_candidate(response_candidate_id="resp:audit"))
    payload_keys = set(
        ledger.filter(
            event_type="corporate_strategic_response_candidate_added"
        )[-1].payload.keys()
    )
    forbidden = {
        "transcript",
        "content",
        "notes",
        "minutes",
        "attendees",
        "buyback_executed",
        "dividend_changed",
        "divestment_executed",
        "merger_executed",
        "board_change_executed",
        "disclosure_filed",
        "verbatim",
        "paraphrase",
        "body",
    }
    leaked = payload_keys & forbidden
    assert not leaked, (
        f"v1.10.3 corporate response payload must not carry "
        f"execution / transcript keys; found: {sorted(leaked)}"
    )


def test_add_response_without_ledger_does_not_raise():
    book = StrategicResponseCandidateBook()
    book.add_candidate(_candidate())


def test_duplicate_response_emits_no_extra_ledger_record():
    ledger = Ledger()
    book = StrategicResponseCandidateBook(ledger=ledger)
    book.add_candidate(_candidate(response_candidate_id="resp:once"))
    with pytest.raises(DuplicateResponseCandidateError):
        book.add_candidate(_candidate(response_candidate_id="resp:once"))
    assert (
        len(
            ledger.filter(
                event_type="corporate_strategic_response_candidate_added"
            )
        )
        == 1
    )


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_strategic_response_book():
    kernel = _kernel()
    assert isinstance(
        kernel.strategic_responses, StrategicResponseCandidateBook
    )
    assert kernel.strategic_responses.ledger is kernel.ledger
    assert kernel.strategic_responses.clock is kernel.clock


def test_kernel_add_response_emits_to_kernel_ledger():
    kernel = _kernel()
    kernel.strategic_responses.add_candidate(_candidate())
    records = kernel.ledger.filter(
        event_type="corporate_strategic_response_candidate_added"
    )
    assert len(records) == 1


def test_kernel_response_simulation_date_uses_clock():
    kernel = _kernel()
    kernel.strategic_responses.add_candidate(
        _candidate(response_candidate_id="resp:wired")
    )
    records = kernel.ledger.filter(
        event_type="corporate_strategic_response_candidate_added"
    )
    assert records[-1].simulation_date == "2026-01-01"


# ---------------------------------------------------------------------------
# No-action invariant
# ---------------------------------------------------------------------------


def test_response_emits_only_response_candidate_added_records():
    ledger = Ledger()
    book = StrategicResponseCandidateBook(ledger=ledger)
    book.add_candidate(_candidate(response_candidate_id="resp:audit"))
    assert len(ledger.records) == 1
    record = ledger.records[0]
    assert (
        record.record_type
        is RecordType.CORPORATE_STRATEGIC_RESPONSE_CANDIDATE_ADDED
    )


def test_response_does_not_emit_corporate_action_or_trading_records():
    forbidden_event_types = {
        "order_submitted",
        "price_updated",
        "contract_created",
        "contract_status_updated",
        "contract_covenant_breached",
        "ownership_position_added",
        "ownership_transferred",
        "institution_action_recorded",
    }
    ledger = Ledger()
    book = StrategicResponseCandidateBook(ledger=ledger)
    book.add_candidate(_candidate(response_candidate_id="resp:no_action"))
    seen = {r.event_type for r in ledger.records}
    assert seen.isdisjoint(forbidden_event_types), (
        f"v1.10.3 strategic response add_candidate must not emit any "
        f"action-class record; saw forbidden event types: "
        f"{sorted(seen & forbidden_event_types)}"
    )


# ---------------------------------------------------------------------------
# No-mutation guarantee against every other source-of-truth book
# ---------------------------------------------------------------------------


def test_response_book_does_not_mutate_other_kernel_books():
    """
    Adding response candidates, filtering, and building snapshots
    must not mutate any other source-of-truth book — including the
    v1.10.1 StewardshipBook, the v1.10.2 DialogueBook, and the
    sibling v1.10.3 EscalationCandidateBook.
    """
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
        "industry_conditions": kernel.industry_conditions.snapshot(),
        "market_conditions": kernel.market_conditions.snapshot(),
    }

    kernel.strategic_responses.add_candidate(
        _candidate(
            response_candidate_id="resp:k:a",
            trigger_theme_ids=("theme:cap",),
            trigger_dialogue_ids=("dialogue:001",),
            trigger_signal_ids=("signal:reference_firm_pressure_001",),
            trigger_valuation_ids=("valuation:reference_demo_001",),
        )
    )
    kernel.strategic_responses.add_candidate(
        _candidate(
            response_candidate_id="resp:k:b",
            company_id="firm:reference_retailer_a",
            response_type="governance_change_review",
            status="active",
            priority="high",
            visibility="public",
            as_of_date="2026-06-01",
            next_review_date="2026-09-01",
        )
    )
    kernel.strategic_responses.list_candidates()
    kernel.strategic_responses.list_by_company(
        "firm:reference_manufacturer_a"
    )
    kernel.strategic_responses.list_by_type("capital_allocation_review")
    kernel.strategic_responses.list_by_status("draft")
    kernel.strategic_responses.list_by_priority("medium")
    kernel.strategic_responses.list_by_theme("theme:cap")
    kernel.strategic_responses.list_by_dialogue("dialogue:001")
    kernel.strategic_responses.list_by_industry_condition(
        "industry_condition:does-not-exist"
    )
    kernel.strategic_responses.list_by_market_condition(
        "market_condition:does-not-exist"
    )
    kernel.strategic_responses.list_by_date("2026-05-01")
    kernel.strategic_responses.snapshot()

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
        kernel.industry_conditions.snapshot()
        == snaps_before["industry_conditions"]
    )
    assert (
        kernel.market_conditions.snapshot()
        == snaps_before["market_conditions"]
    )


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


def test_strategic_response_module_contains_no_jurisdiction_specific_identifiers():
    import re
    from pathlib import Path

    module_path = (
        Path(__file__).resolve().parent.parent
        / "world"
        / "strategic_response.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"jurisdiction-specific token {token!r} appeared in "
            f"world/strategic_response.py"
        )
