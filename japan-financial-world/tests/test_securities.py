"""
Tests for v1.15.1 ListedSecurityRecord + MarketVenueRecord +
SecurityMarketBook.
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
from world.securities import (
    DuplicateListedSecurityError,
    DuplicateMarketVenueError,
    INVESTOR_ACCESS_LABELS,
    ISSUE_PROFILE_LABELS,
    LIQUIDITY_PROFILE_LABELS,
    LISTING_STATUS_LABELS,
    ListedSecurityRecord,
    MarketVenueRecord,
    SAFE_INTENT_LABELS,
    SECURITY_TYPE_LABELS,
    SecurityMarketBook,
    UnknownListedSecurityError,
    UnknownMarketVenueError,
    VENUE_ROLE_LABELS,
    VENUE_STATUS_LABELS,
    VENUE_TYPE_LABELS,
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


def _security(
    *,
    security_id: str = "security:reference_a:equity:line_1",
    issuer_firm_id: str = "firm:reference_a",
    security_type_label: str = "equity",
    listing_status_label: str = "listed",
    primary_market_venue_id: str = "venue:reference_exchange_a",
    currency_label: str = "synthetic_currency_a",
    issue_profile_label: str = "seasoned",
    liquidity_profile_label: str = "liquid",
    investor_access_label: str = "broad",
    status: str = "active",
    visibility: str = "public",
    metadata: dict | None = None,
) -> ListedSecurityRecord:
    return ListedSecurityRecord(
        security_id=security_id,
        issuer_firm_id=issuer_firm_id,
        security_type_label=security_type_label,
        listing_status_label=listing_status_label,
        primary_market_venue_id=primary_market_venue_id,
        currency_label=currency_label,
        issue_profile_label=issue_profile_label,
        liquidity_profile_label=liquidity_profile_label,
        investor_access_label=investor_access_label,
        status=status,
        visibility=visibility,
        metadata=metadata or {},
    )


def _venue(
    *,
    venue_id: str = "venue:reference_exchange_a",
    venue_type_label: str = "exchange",
    venue_role_label: str = "listing_venue",
    status: str = "active",
    visibility: str = "public",
    supported_security_type_labels: tuple[str, ...] = ("equity",),
    supported_intent_labels: tuple[str, ...] = (
        "increase_interest",
        "reduce_interest",
        "hold_review",
    ),
    metadata: dict | None = None,
) -> MarketVenueRecord:
    return MarketVenueRecord(
        venue_id=venue_id,
        venue_type_label=venue_type_label,
        venue_role_label=venue_role_label,
        status=status,
        visibility=visibility,
        supported_security_type_labels=supported_security_type_labels,
        supported_intent_labels=supported_intent_labels,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# ListedSecurityRecord — required-string validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"security_id": ""},
        {"issuer_firm_id": ""},
        {"primary_market_venue_id": ""},
        {"currency_label": ""},
        {"status": ""},
        {"visibility": ""},
    ],
)
def test_security_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _security(**kwargs)


def test_security_is_frozen():
    s = _security()
    with pytest.raises(Exception):
        s.security_id = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ListedSecurityRecord — closed-set acceptance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label", sorted(SECURITY_TYPE_LABELS))
def test_security_type_labels_accepted(label):
    s = _security(security_type_label=label)
    assert s.security_type_label == label


@pytest.mark.parametrize("label", sorted(LISTING_STATUS_LABELS))
def test_listing_status_labels_accepted(label):
    s = _security(listing_status_label=label)
    assert s.listing_status_label == label


@pytest.mark.parametrize("label", sorted(ISSUE_PROFILE_LABELS))
def test_issue_profile_labels_accepted(label):
    s = _security(issue_profile_label=label)
    assert s.issue_profile_label == label


@pytest.mark.parametrize("label", sorted(LIQUIDITY_PROFILE_LABELS))
def test_liquidity_profile_labels_accepted(label):
    s = _security(liquidity_profile_label=label)
    assert s.liquidity_profile_label == label


@pytest.mark.parametrize("label", sorted(INVESTOR_ACCESS_LABELS))
def test_investor_access_labels_accepted(label):
    s = _security(investor_access_label=label)
    assert s.investor_access_label == label


# ---------------------------------------------------------------------------
# ListedSecurityRecord — closed-set rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name",
    [
        "security_type_label",
        "listing_status_label",
        "issue_profile_label",
        "liquidity_profile_label",
        "investor_access_label",
    ],
)
def test_security_label_field_rejects_out_of_set_value(field_name):
    with pytest.raises(ValueError):
        _security(**{field_name: "not_a_real_label"})


# ---------------------------------------------------------------------------
# ListedSecurityRecord — exact-set pinning
# ---------------------------------------------------------------------------


def test_pinned_security_type_label_set_is_exact():
    assert SECURITY_TYPE_LABELS == frozenset(
        {
            "equity",
            "corporate_bond",
            "convertible",
            "preferred_equity",
            "fund_unit",
            "loan_claim",
            "hybrid",
            "unknown",
        }
    )


def test_pinned_listing_status_label_set_is_exact():
    assert LISTING_STATUS_LABELS == frozenset(
        {
            "listed",
            "private",
            "suspended",
            "delisted",
            "proposed",
            "unknown",
        }
    )


def test_pinned_issue_profile_label_set_is_exact():
    assert ISSUE_PROFILE_LABELS == frozenset(
        {
            "seasoned",
            "newly_issued",
            "proposed",
            "legacy",
            "unknown",
        }
    )


def test_pinned_liquidity_profile_label_set_is_exact():
    assert LIQUIDITY_PROFILE_LABELS == frozenset(
        {
            "liquid",
            "moderate",
            "thin",
            "illiquid",
            "unknown",
        }
    )


def test_pinned_investor_access_label_set_is_exact():
    assert INVESTOR_ACCESS_LABELS == frozenset(
        {
            "broad",
            "qualified_only",
            "restricted",
            "private",
            "unknown",
        }
    )


# ---------------------------------------------------------------------------
# ListedSecurityRecord — to_dict round-trip
# ---------------------------------------------------------------------------


def test_security_to_dict_round_trips():
    s = _security(metadata={"note": "synthetic"})
    out = s.to_dict()
    assert out["security_id"] == "security:reference_a:equity:line_1"
    assert out["issuer_firm_id"] == "firm:reference_a"
    assert out["security_type_label"] == "equity"
    assert out["primary_market_venue_id"] == "venue:reference_exchange_a"
    assert out["metadata"] == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# MarketVenueRecord — required-string validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"venue_id": ""},
        {"visibility": ""},
    ],
)
def test_venue_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _venue(**kwargs)


def test_venue_is_frozen():
    v = _venue()
    with pytest.raises(Exception):
        v.venue_id = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MarketVenueRecord — closed-set acceptance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label", sorted(VENUE_TYPE_LABELS))
def test_venue_type_labels_accepted(label):
    v = _venue(venue_type_label=label)
    assert v.venue_type_label == label


@pytest.mark.parametrize("label", sorted(VENUE_ROLE_LABELS))
def test_venue_role_labels_accepted(label):
    v = _venue(venue_role_label=label)
    assert v.venue_role_label == label


@pytest.mark.parametrize("label", sorted(VENUE_STATUS_LABELS))
def test_venue_status_labels_accepted(label):
    v = _venue(status=label)
    assert v.status == label


# ---------------------------------------------------------------------------
# MarketVenueRecord — closed-set rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name",
    ["venue_type_label", "venue_role_label", "status"],
)
def test_venue_label_field_rejects_out_of_set_value(field_name):
    with pytest.raises(ValueError):
        _venue(**{field_name: "not_a_real_label"})


# ---------------------------------------------------------------------------
# MarketVenueRecord — exact-set pinning
# ---------------------------------------------------------------------------


def test_pinned_venue_type_label_set_is_exact():
    assert VENUE_TYPE_LABELS == frozenset(
        {
            "exchange",
            "broker",
            "dealer",
            "otc_network",
            "dark_pool",
            "primary_market_platform",
            "internal_crossing",
            "unknown",
        }
    )


def test_pinned_venue_role_label_set_is_exact():
    assert VENUE_ROLE_LABELS == frozenset(
        {
            "listing_venue",
            "intent_aggregator",
            "quote_collector",
            "primary_distribution_context",
            "secondary_market_context",
            "unknown",
        }
    )


def test_pinned_venue_status_label_set_is_exact():
    assert VENUE_STATUS_LABELS == frozenset(
        {"active", "inactive", "proposed", "archived", "unknown"}
    )


# ---------------------------------------------------------------------------
# Venue tuple slots: supported_security_type_labels
# ---------------------------------------------------------------------------


def test_venue_supports_every_security_type_label():
    """A venue may declare support for every closed-set
    security_type_label value."""
    v = _venue(
        supported_security_type_labels=tuple(sorted(SECURITY_TYPE_LABELS))
    )
    assert set(v.supported_security_type_labels) == SECURITY_TYPE_LABELS


def test_venue_rejects_out_of_set_supported_security_type_label():
    with pytest.raises(ValueError):
        _venue(supported_security_type_labels=("not_a_real_security_type",))


def test_venue_rejects_empty_string_in_supported_security_type_labels():
    with pytest.raises(ValueError):
        _venue(supported_security_type_labels=("",))


# ---------------------------------------------------------------------------
# Venue tuple slots: supported_intent_labels (safe-only)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label", sorted(SAFE_INTENT_LABELS))
def test_venue_accepts_every_safe_intent_label(label):
    v = _venue(supported_intent_labels=(label,))
    assert v.supported_intent_labels == (label,)


def test_venue_supports_every_safe_intent_label_at_once():
    """A venue may declare support for the entire safe-intent
    vocabulary in one record."""
    v = _venue(supported_intent_labels=tuple(sorted(SAFE_INTENT_LABELS)))
    assert set(v.supported_intent_labels) == SAFE_INTENT_LABELS


_FORBIDDEN_INTENT_LABELS = (
    "buy",
    "sell",
    "order",
    "target_weight",
    "overweight",
    "underweight",
    "execution",
)


@pytest.mark.parametrize("label", _FORBIDDEN_INTENT_LABELS)
def test_venue_rejects_forbidden_intent_label(label):
    """Forbidden trading verbs are rejected by closed-set
    membership on ``supported_intent_labels``."""
    with pytest.raises(ValueError):
        _venue(supported_intent_labels=(label,))


def test_venue_rejects_forbidden_intent_label_amid_safe_ones():
    """Even a single forbidden label among otherwise-safe ones is
    rejected — closed-set is evaluated per-entry."""
    with pytest.raises(ValueError):
        _venue(
            supported_intent_labels=(
                "increase_interest",
                "buy",
                "hold_review",
            )
        )


def test_venue_rejects_empty_string_in_supported_intent_labels():
    with pytest.raises(ValueError):
        _venue(supported_intent_labels=("",))


def test_pinned_safe_intent_label_set_is_exact():
    assert SAFE_INTENT_LABELS == frozenset(
        {
            "increase_interest",
            "reduce_interest",
            "hold_review",
            "liquidity_watch",
            "rebalance_review",
            "risk_reduction_review",
            "engagement_linked_review",
        }
    )


# ---------------------------------------------------------------------------
# MarketVenueRecord — to_dict round-trip
# ---------------------------------------------------------------------------


def test_venue_to_dict_round_trips():
    v = _venue(metadata={"note": "synthetic"})
    out = v.to_dict()
    assert out["venue_id"] == "venue:reference_exchange_a"
    assert out["venue_type_label"] == "exchange"
    assert out["supported_security_type_labels"] == ["equity"]
    assert out["supported_intent_labels"] == [
        "increase_interest",
        "reduce_interest",
        "hold_review",
    ]
    assert out["metadata"] == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# Anti-fields — must NOT appear on dataclass or ledger payload
# ---------------------------------------------------------------------------


_FORBIDDEN_FIELDS = {
    "order_id",
    "trade_id",
    "buy",
    "sell",
    "bid",
    "ask",
    "quote",
    "execution",
    "clearing",
    "settlement",
    "price",
    "target_price",
    "expected_return",
    "recommendation",
    "investment_advice",
    "real_data_value",
    # plus the v1.14.x family standard set
    "amount",
    "loan_amount",
    "interest_rate",
    "coupon",
    "coupon_rate",
    "spread",
    "fee",
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
    "underwriting",
    "syndication",
    "commitment",
    "allocation",
    "offering_price",
    "take_up_probability",
    "selected_option",
    "optimal_option",
    "approved",
    "executed",
}


def test_security_record_has_no_anti_fields():
    field_names = {f.name for f in dataclass_fields(ListedSecurityRecord)}
    leaked = field_names & _FORBIDDEN_FIELDS
    assert not leaked


def test_venue_record_has_no_anti_fields():
    field_names = {f.name for f in dataclass_fields(MarketVenueRecord)}
    leaked = field_names & _FORBIDDEN_FIELDS
    assert not leaked


# ---------------------------------------------------------------------------
# Book — securities CRUD
# ---------------------------------------------------------------------------


def test_book_add_and_get_security():
    book = SecurityMarketBook()
    s = _security()
    book.add_security(s)
    assert book.get_security(s.security_id) is s


def test_book_get_unknown_security_raises():
    book = SecurityMarketBook()
    with pytest.raises(UnknownListedSecurityError):
        book.get_security("security:missing")
    with pytest.raises(KeyError):
        book.get_security("security:missing")


def test_book_duplicate_security_id_rejected():
    book = SecurityMarketBook()
    book.add_security(_security())
    with pytest.raises(DuplicateListedSecurityError):
        book.add_security(_security())


def test_book_list_securities_returns_all():
    book = SecurityMarketBook()
    book.add_security(_security(security_id="security:a"))
    book.add_security(_security(security_id="security:b"))
    assert len(book.list_securities()) == 2


def test_book_list_by_issuer():
    book = SecurityMarketBook()
    book.add_security(
        _security(security_id="security:a", issuer_firm_id="firm:p1")
    )
    book.add_security(
        _security(security_id="security:b", issuer_firm_id="firm:p2")
    )
    out = book.list_by_issuer("firm:p1")
    assert len(out) == 1
    assert out[0].issuer_firm_id == "firm:p1"


def test_book_list_by_security_type():
    book = SecurityMarketBook()
    book.add_security(
        _security(security_id="security:a", security_type_label="equity")
    )
    book.add_security(
        _security(
            security_id="security:b", security_type_label="corporate_bond"
        )
    )
    assert len(book.list_by_security_type("corporate_bond")) == 1


def test_book_list_by_listing_status():
    book = SecurityMarketBook()
    book.add_security(
        _security(security_id="security:a", listing_status_label="listed")
    )
    book.add_security(
        _security(security_id="security:b", listing_status_label="suspended")
    )
    assert len(book.list_by_listing_status("suspended")) == 1


def test_book_list_by_primary_venue():
    book = SecurityMarketBook()
    book.add_security(
        _security(
            security_id="security:a",
            primary_market_venue_id="venue:a",
        )
    )
    book.add_security(
        _security(
            security_id="security:b",
            primary_market_venue_id="venue:b",
        )
    )
    assert len(book.list_by_primary_venue("venue:b")) == 1


# ---------------------------------------------------------------------------
# Book — venues CRUD
# ---------------------------------------------------------------------------


def test_book_add_and_get_venue():
    book = SecurityMarketBook()
    v = _venue()
    book.add_venue(v)
    assert book.get_venue(v.venue_id) is v


def test_book_get_unknown_venue_raises():
    book = SecurityMarketBook()
    with pytest.raises(UnknownMarketVenueError):
        book.get_venue("venue:missing")
    with pytest.raises(KeyError):
        book.get_venue("venue:missing")


def test_book_duplicate_venue_id_rejected():
    book = SecurityMarketBook()
    book.add_venue(_venue())
    with pytest.raises(DuplicateMarketVenueError):
        book.add_venue(_venue())


def test_book_list_venues_returns_all():
    book = SecurityMarketBook()
    book.add_venue(_venue(venue_id="venue:a"))
    book.add_venue(_venue(venue_id="venue:b"))
    assert len(book.list_venues()) == 2


def test_book_list_by_venue_type():
    book = SecurityMarketBook()
    book.add_venue(_venue(venue_id="venue:a", venue_type_label="exchange"))
    book.add_venue(_venue(venue_id="venue:b", venue_type_label="broker"))
    assert len(book.list_by_venue_type("broker")) == 1


def test_book_list_by_venue_role():
    book = SecurityMarketBook()
    book.add_venue(
        _venue(venue_id="venue:a", venue_role_label="listing_venue")
    )
    book.add_venue(
        _venue(venue_id="venue:b", venue_role_label="intent_aggregator")
    )
    assert len(book.list_by_venue_role("intent_aggregator")) == 1


# ---------------------------------------------------------------------------
# Snapshot determinism
# ---------------------------------------------------------------------------


def test_book_snapshot_is_deterministic_and_sorted():
    book = SecurityMarketBook()
    book.add_security(_security(security_id="security:b"))
    book.add_security(_security(security_id="security:a"))
    book.add_venue(_venue(venue_id="venue:b"))
    book.add_venue(_venue(venue_id="venue:a"))
    snap = book.snapshot()
    assert snap["security_count"] == 2
    assert snap["venue_count"] == 2
    assert [s["security_id"] for s in snap["securities"]] == [
        "security:a",
        "security:b",
    ]
    assert [v["venue_id"] for v in snap["venues"]] == [
        "venue:a",
        "venue:b",
    ]
    assert book.snapshot() == snap


# ---------------------------------------------------------------------------
# Plain-id cross-references — issuer firm id
# ---------------------------------------------------------------------------


def test_security_can_cite_issuer_firm_id_as_plain_id():
    """The issuer_firm_id is stored as a plain id; the book does
    not validate it against any other source-of-truth book."""
    book = SecurityMarketBook()
    s = _security(
        security_id="security:reference_a:equity:line_1",
        issuer_firm_id="firm:reference_a",
    )
    book.add_security(s)
    out = book.get_security(s.security_id)
    assert out.issuer_firm_id == "firm:reference_a"


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_types_exist():
    assert (
        RecordType.LISTED_SECURITY_REGISTERED.value
        == "listed_security_registered"
    )
    assert (
        RecordType.MARKET_VENUE_REGISTERED.value
        == "market_venue_registered"
    )


def test_add_security_writes_exactly_one_ledger_record():
    ledger = Ledger()
    book = SecurityMarketBook(ledger=ledger)
    book.add_security(_security())
    assert len(ledger.records) == 1
    rec = ledger.records[0]
    assert rec.record_type is RecordType.LISTED_SECURITY_REGISTERED
    assert rec.space_id == "security_market"


def test_add_venue_writes_exactly_one_ledger_record():
    ledger = Ledger()
    book = SecurityMarketBook(ledger=ledger)
    book.add_venue(_venue())
    assert len(ledger.records) == 1
    rec = ledger.records[0]
    assert rec.record_type is RecordType.MARKET_VENUE_REGISTERED
    assert rec.space_id == "security_market"


def test_duplicate_security_add_emits_no_extra_ledger_record():
    ledger = Ledger()
    book = SecurityMarketBook(ledger=ledger)
    book.add_security(_security())
    with pytest.raises(DuplicateListedSecurityError):
        book.add_security(_security())
    assert len(ledger.records) == 1


def test_duplicate_venue_add_emits_no_extra_ledger_record():
    ledger = Ledger()
    book = SecurityMarketBook(ledger=ledger)
    book.add_venue(_venue())
    with pytest.raises(DuplicateMarketVenueError):
        book.add_venue(_venue())
    assert len(ledger.records) == 1


def test_security_ledger_payload_contains_label_fields():
    ledger = Ledger()
    book = SecurityMarketBook(ledger=ledger)
    book.add_security(_security())
    rec = ledger.records[0]
    assert rec.payload["security_type_label"] == "equity"
    assert rec.payload["listing_status_label"] == "listed"
    assert rec.payload["issue_profile_label"] == "seasoned"
    assert rec.payload["liquidity_profile_label"] == "liquid"
    assert rec.payload["investor_access_label"] == "broad"
    assert rec.payload["primary_market_venue_id"] == "venue:reference_exchange_a"


def test_venue_ledger_payload_contains_label_fields():
    ledger = Ledger()
    book = SecurityMarketBook(ledger=ledger)
    book.add_venue(_venue())
    rec = ledger.records[0]
    assert rec.payload["venue_type_label"] == "exchange"
    assert rec.payload["venue_role_label"] == "listing_venue"
    assert rec.payload["status"] == "active"
    # The ledger freezes lists into tuples on append (see
    # world/ledger.py::_freeze).
    assert rec.payload["supported_security_type_labels"] == ("equity",)
    assert rec.payload["supported_intent_labels"] == (
        "increase_interest",
        "reduce_interest",
        "hold_review",
    )


def test_security_ledger_payload_carries_no_anti_field_keys():
    ledger = Ledger()
    book = SecurityMarketBook(ledger=ledger)
    book.add_security(_security())
    rec = ledger.records[0]
    leaked = set(rec.payload.keys()) & _FORBIDDEN_FIELDS
    assert not leaked


def test_venue_ledger_payload_carries_no_anti_field_keys():
    ledger = Ledger()
    book = SecurityMarketBook(ledger=ledger)
    book.add_venue(_venue())
    rec = ledger.records[0]
    leaked = set(rec.payload.keys()) & _FORBIDDEN_FIELDS
    assert not leaked


def test_ledger_emits_no_forbidden_event_types():
    """Adding securities + venues must produce only the two
    v1.15.1 record types — never any execution / order / trade /
    pricing event."""
    ledger = Ledger()
    book = SecurityMarketBook(ledger=ledger)
    book.add_security(_security(security_id="security:a"))
    book.add_security(_security(security_id="security:b"))
    book.add_venue(_venue(venue_id="venue:a"))
    book.add_venue(_venue(venue_id="venue:b"))
    types = {rec.record_type for rec in ledger.records}
    assert types == {
        RecordType.LISTED_SECURITY_REGISTERED,
        RecordType.MARKET_VENUE_REGISTERED,
    }


def test_book_without_ledger_does_not_raise():
    book = SecurityMarketBook()
    book.add_security(_security())
    book.add_venue(_venue())


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_security_market_book():
    k = _kernel()
    assert isinstance(k.security_market, SecurityMarketBook)
    assert k.security_market.ledger is k.ledger
    assert k.security_market.clock is k.clock


def test_kernel_simulation_date_uses_clock_for_security():
    k = _kernel()
    k.security_market.add_security(_security())
    rec = k.ledger.records[-1]
    assert rec.simulation_date == "2026-03-31"


def test_kernel_simulation_date_uses_clock_for_venue():
    k = _kernel()
    k.security_market.add_venue(_venue())
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
        "financing_paths": k.financing_paths.snapshot(),
    }
    k.security_market.add_security(_security())
    k.security_market.add_venue(_venue())
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
        / "securities.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, token
