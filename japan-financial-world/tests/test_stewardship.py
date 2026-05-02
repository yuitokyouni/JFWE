"""
Tests for v1.10.1 StewardshipThemeRecord + StewardshipBook.

Covers field validation, immutability, ``add_theme`` deduplication,
unknown lookup, every list / filter method, the active-window
predicate semantics (``is_active_on`` + ``list_active_as_of``),
deterministic snapshots, ledger emission with the new
``RecordType.STEWARDSHIP_THEME_ADDED``, kernel wiring of the new
``StewardshipBook``, and the no-mutation guarantee against every
other v0/v1 source-of-truth book in the kernel.

Also exercises the v1.10.1 scope discipline: identifier and tag
strings used in this test suite are jurisdiction-neutral and
synthetic; no Japan-specific institution name, regulator, code, or
threshold appears anywhere in the test body.
"""

from __future__ import annotations

from datetime import date

import pytest

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State
from world.stewardship import (
    DuplicateStewardshipThemeError,
    StewardshipBook,
    StewardshipThemeRecord,
    UnknownStewardshipThemeError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _theme(
    *,
    theme_id: str = "theme:reference_pension_a:capital_allocation:2026Q1",
    owner_id: str = "investor:reference_pension_a",
    owner_type: str = "investor",
    theme_type: str = "capital_allocation_discipline",
    title: str = "Capital allocation discipline",
    description: str = (
        "Generic, jurisdiction-neutral theme description used in tests."
    ),
    target_scope: str = "all_holdings",
    priority: str = "medium",
    horizon: str = "medium_term",
    status: str = "active",
    effective_from: str = "2026-01-01",
    effective_to: str | None = None,
    related_variable_ids: tuple[str, ...] = (),
    related_signal_ids: tuple[str, ...] = (),
    metadata: dict | None = None,
) -> StewardshipThemeRecord:
    return StewardshipThemeRecord(
        theme_id=theme_id,
        owner_id=owner_id,
        owner_type=owner_type,
        theme_type=theme_type,
        title=title,
        description=description,
        target_scope=target_scope,
        priority=priority,
        horizon=horizon,
        status=status,
        effective_from=effective_from,
        effective_to=effective_to,
        related_variable_ids=related_variable_ids,
        related_signal_ids=related_signal_ids,
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
# StewardshipThemeRecord — field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"theme_id": ""},
        {"owner_id": ""},
        {"owner_type": ""},
        {"theme_type": ""},
        {"title": ""},
        {"target_scope": ""},
        {"priority": ""},
        {"horizon": ""},
        {"status": ""},
        {"effective_from": ""},
    ],
)
def test_theme_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _theme(**kwargs)


def test_theme_description_must_be_string():
    with pytest.raises(ValueError):
        _theme(description=123)  # type: ignore[arg-type]


def test_theme_description_may_be_empty_string():
    """Description is optional content; empty string is allowed."""
    t = _theme(description="")
    assert t.description == ""


@pytest.mark.parametrize(
    "tuple_field",
    ["related_variable_ids", "related_signal_ids"],
)
def test_theme_rejects_empty_strings_in_tuple_fields(tuple_field):
    bad = {tuple_field: ("valid", "")}
    with pytest.raises(ValueError):
        _theme(**bad)


def test_theme_coerces_effective_dates_to_iso_strings():
    t = _theme(
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
    )
    assert t.effective_from == "2026-01-01"
    assert t.effective_to == "2026-12-31"


def test_theme_effective_to_optional():
    t = _theme(effective_to=None)
    assert t.effective_to is None


def test_theme_rejects_non_date_effective_to():
    with pytest.raises(ValueError):
        _theme(effective_to=12345)  # type: ignore[arg-type]


def test_theme_rejects_effective_to_before_effective_from():
    with pytest.raises(ValueError):
        _theme(effective_from="2026-06-01", effective_to="2026-01-01")


def test_theme_accepts_effective_to_equal_effective_from():
    t = _theme(effective_from="2026-01-01", effective_to="2026-01-01")
    assert t.effective_from == t.effective_to == "2026-01-01"


# ---------------------------------------------------------------------------
# StewardshipThemeRecord — immutability & round-trip
# ---------------------------------------------------------------------------


def test_theme_is_frozen():
    t = _theme()
    with pytest.raises(Exception):
        t.theme_id = "tampered"  # type: ignore[misc]


def test_theme_to_dict_round_trips_fields():
    t = _theme(
        related_variable_ids=("variable:reference_var_a",),
        related_signal_ids=("signal:reference_signal_a",),
        metadata={"note": "synthetic"},
    )
    d = t.to_dict()
    assert d["theme_id"] == t.theme_id
    assert d["owner_id"] == t.owner_id
    assert d["owner_type"] == t.owner_type
    assert d["theme_type"] == t.theme_type
    assert d["title"] == t.title
    assert d["target_scope"] == t.target_scope
    assert d["priority"] == t.priority
    assert d["horizon"] == t.horizon
    assert d["status"] == t.status
    assert d["effective_from"] == t.effective_from
    assert d["effective_to"] == t.effective_to
    assert d["related_variable_ids"] == ["variable:reference_var_a"]
    assert d["related_signal_ids"] == ["signal:reference_signal_a"]
    assert d["metadata"] == {"note": "synthetic"}


# ---------------------------------------------------------------------------
# is_active_on
# ---------------------------------------------------------------------------


def test_is_active_on_within_window():
    t = _theme(effective_from="2026-01-01", effective_to="2026-12-31")
    assert t.is_active_on("2026-06-15") is True


def test_is_active_on_includes_endpoints():
    t = _theme(effective_from="2026-01-01", effective_to="2026-12-31")
    assert t.is_active_on("2026-01-01") is True
    assert t.is_active_on("2026-12-31") is True


def test_is_active_on_excludes_before_start():
    t = _theme(effective_from="2026-01-01", effective_to="2026-12-31")
    assert t.is_active_on("2025-12-31") is False


def test_is_active_on_excludes_after_end():
    t = _theme(effective_from="2026-01-01", effective_to="2026-12-31")
    assert t.is_active_on("2027-01-01") is False


def test_is_active_on_open_ended_when_effective_to_is_none():
    t = _theme(effective_from="2026-01-01", effective_to=None)
    assert t.is_active_on("2026-01-01") is True
    assert t.is_active_on("2099-01-01") is True
    assert t.is_active_on("2025-12-31") is False


def test_is_active_on_accepts_date_object():
    t = _theme(effective_from="2026-01-01", effective_to="2026-12-31")
    assert t.is_active_on(date(2026, 6, 15)) is True
    assert t.is_active_on(date(2025, 12, 31)) is False


# ---------------------------------------------------------------------------
# StewardshipBook — add / get / dedup / unknown
# ---------------------------------------------------------------------------


def test_add_and_get_theme():
    book = StewardshipBook()
    t = _theme()
    book.add_theme(t)
    assert book.get_theme(t.theme_id) is t


def test_get_theme_unknown_raises():
    book = StewardshipBook()
    with pytest.raises(UnknownStewardshipThemeError):
        book.get_theme("does-not-exist")


def test_unknown_stewardship_theme_error_is_keyerror():
    """``UnknownStewardshipThemeError`` should also be a ``KeyError``."""
    err = UnknownStewardshipThemeError("missing")
    assert isinstance(err, KeyError)


def test_duplicate_theme_id_rejected():
    book = StewardshipBook()
    book.add_theme(_theme(theme_id="theme:dup"))
    with pytest.raises(DuplicateStewardshipThemeError):
        book.add_theme(_theme(theme_id="theme:dup"))


def test_add_theme_returns_record():
    book = StewardshipBook()
    t = _theme()
    returned = book.add_theme(t)
    assert returned is t


# ---------------------------------------------------------------------------
# Listings & filters
# ---------------------------------------------------------------------------


def test_list_themes_returns_all_in_insertion_order():
    book = StewardshipBook()
    a = _theme(theme_id="theme:a")
    b = _theme(theme_id="theme:b")
    c = _theme(theme_id="theme:c")
    book.add_theme(a)
    book.add_theme(b)
    book.add_theme(c)
    listed = book.list_themes()
    assert tuple(t.theme_id for t in listed) == ("theme:a", "theme:b", "theme:c")


def test_list_themes_empty_book():
    assert StewardshipBook().list_themes() == ()


def test_list_by_owner():
    book = StewardshipBook()
    book.add_theme(
        _theme(theme_id="theme:1", owner_id="investor:reference_pension_a")
    )
    book.add_theme(
        _theme(theme_id="theme:2", owner_id="investor:reference_pension_b")
    )
    book.add_theme(
        _theme(theme_id="theme:3", owner_id="investor:reference_pension_a")
    )
    matched = book.list_by_owner("investor:reference_pension_a")
    assert tuple(t.theme_id for t in matched) == ("theme:1", "theme:3")


def test_list_by_owner_no_match():
    book = StewardshipBook()
    book.add_theme(_theme(theme_id="theme:1", owner_id="investor:a"))
    assert book.list_by_owner("investor:other") == ()


def test_list_by_owner_type():
    book = StewardshipBook()
    book.add_theme(
        _theme(
            theme_id="theme:inv",
            owner_id="investor:a",
            owner_type="investor",
        )
    )
    book.add_theme(
        _theme(
            theme_id="theme:asset_owner",
            owner_id="asset_owner:b",
            owner_type="asset_owner",
        )
    )
    inv = book.list_by_owner_type("investor")
    ao = book.list_by_owner_type("asset_owner")
    assert tuple(t.theme_id for t in inv) == ("theme:inv",)
    assert tuple(t.theme_id for t in ao) == ("theme:asset_owner",)


def test_list_by_theme_type():
    book = StewardshipBook()
    book.add_theme(
        _theme(theme_id="theme:cap", theme_type="capital_allocation_discipline")
    )
    book.add_theme(
        _theme(theme_id="theme:gov", theme_type="governance_structure")
    )
    book.add_theme(
        _theme(theme_id="theme:cap2", theme_type="capital_allocation_discipline")
    )
    cap = book.list_by_theme_type("capital_allocation_discipline")
    assert tuple(t.theme_id for t in cap) == ("theme:cap", "theme:cap2")


def test_list_by_status():
    book = StewardshipBook()
    book.add_theme(_theme(theme_id="theme:draft", status="draft"))
    book.add_theme(_theme(theme_id="theme:active", status="active"))
    book.add_theme(_theme(theme_id="theme:retired", status="retired"))
    assert tuple(t.theme_id for t in book.list_by_status("active")) == (
        "theme:active",
    )
    assert tuple(t.theme_id for t in book.list_by_status("retired")) == (
        "theme:retired",
    )
    assert tuple(t.theme_id for t in book.list_by_status("draft")) == (
        "theme:draft",
    )


def test_list_by_priority():
    book = StewardshipBook()
    book.add_theme(_theme(theme_id="theme:low", priority="low"))
    book.add_theme(_theme(theme_id="theme:med", priority="medium"))
    book.add_theme(_theme(theme_id="theme:hi", priority="high"))
    assert tuple(t.theme_id for t in book.list_by_priority("high")) == (
        "theme:hi",
    )


# ---------------------------------------------------------------------------
# list_active_as_of
# ---------------------------------------------------------------------------


def test_list_active_as_of_filters_by_window():
    book = StewardshipBook()
    book.add_theme(
        _theme(
            theme_id="theme:past",
            effective_from="2025-01-01",
            effective_to="2025-12-31",
        )
    )
    book.add_theme(
        _theme(
            theme_id="theme:current",
            effective_from="2026-01-01",
            effective_to="2026-12-31",
        )
    )
    book.add_theme(
        _theme(
            theme_id="theme:future",
            effective_from="2027-01-01",
            effective_to="2027-12-31",
        )
    )
    book.add_theme(
        _theme(
            theme_id="theme:open_ended",
            effective_from="2024-01-01",
            effective_to=None,
        )
    )
    active = book.list_active_as_of("2026-06-15")
    assert sorted(t.theme_id for t in active) == [
        "theme:current",
        "theme:open_ended",
    ]


def test_list_active_as_of_accepts_date_object():
    book = StewardshipBook()
    book.add_theme(
        _theme(
            theme_id="theme:current",
            effective_from="2026-01-01",
            effective_to="2026-12-31",
        )
    )
    active = book.list_active_as_of(date(2026, 6, 15))
    assert tuple(t.theme_id for t in active) == ("theme:current",)


def test_list_active_as_of_empty_book():
    assert StewardshipBook().list_active_as_of("2026-06-15") == ()


def test_list_active_as_of_does_not_consult_status():
    """``list_active_as_of`` is a date-window predicate only."""
    book = StewardshipBook()
    # Status "retired" but no effective_to → still active by date window.
    book.add_theme(
        _theme(
            theme_id="theme:retired_open",
            status="retired",
            effective_from="2026-01-01",
            effective_to=None,
        )
    )
    active = book.list_active_as_of("2026-06-15")
    assert tuple(t.theme_id for t in active) == ("theme:retired_open",)


# ---------------------------------------------------------------------------
# Snapshot determinism
# ---------------------------------------------------------------------------


def test_snapshot_is_deterministic_and_sorted():
    book = StewardshipBook()
    # Insert in non-sorted order; snapshot must sort by theme_id.
    book.add_theme(_theme(theme_id="theme:z"))
    book.add_theme(_theme(theme_id="theme:a"))
    book.add_theme(_theme(theme_id="theme:m"))

    snap1 = book.snapshot()
    snap2 = book.snapshot()
    assert snap1 == snap2
    assert snap1["theme_count"] == 3
    assert [t["theme_id"] for t in snap1["themes"]] == [
        "theme:a",
        "theme:m",
        "theme:z",
    ]


def test_snapshot_empty_book():
    snap = StewardshipBook().snapshot()
    assert snap == {"theme_count": 0, "themes": []}


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_type_exists():
    """The new RecordType must be registered on the enum."""
    assert RecordType("stewardship_theme_added") is RecordType.STEWARDSHIP_THEME_ADDED
    assert RecordType.STEWARDSHIP_THEME_ADDED.value == "stewardship_theme_added"


def test_add_theme_writes_exactly_one_ledger_record():
    ledger = Ledger()
    book = StewardshipBook(ledger=ledger)
    book.add_theme(_theme(theme_id="theme:emit"))
    records = ledger.filter(event_type="stewardship_theme_added")
    assert len(records) == 1
    record = records[0]
    assert record.record_type is RecordType.STEWARDSHIP_THEME_ADDED
    assert record.object_id == "theme:emit"
    assert record.source == "investor:reference_pension_a"
    assert record.space_id == "stewardship"
    assert record.agent_id == "investor:reference_pension_a"


def test_add_theme_ledger_payload_carries_full_field_set():
    ledger = Ledger()
    book = StewardshipBook(ledger=ledger)
    book.add_theme(
        _theme(
            theme_id="theme:payload",
            related_variable_ids=("variable:reference_var_a",),
            related_signal_ids=("signal:reference_signal_a",),
        )
    )
    records = ledger.filter(event_type="stewardship_theme_added")
    payload = records[-1].payload
    assert payload["theme_id"] == "theme:payload"
    assert payload["owner_id"] == "investor:reference_pension_a"
    assert payload["owner_type"] == "investor"
    assert payload["theme_type"] == "capital_allocation_discipline"
    assert payload["title"] == "Capital allocation discipline"
    assert payload["target_scope"] == "all_holdings"
    assert payload["priority"] == "medium"
    assert payload["horizon"] == "medium_term"
    assert payload["status"] == "active"
    assert payload["effective_from"] == "2026-01-01"
    assert payload["effective_to"] is None
    assert tuple(payload["related_variable_ids"]) == (
        "variable:reference_var_a",
    )
    assert tuple(payload["related_signal_ids"]) == (
        "signal:reference_signal_a",
    )


def test_add_theme_without_ledger_does_not_raise():
    """A book without a ledger must still accept adds (it is just silent)."""
    book = StewardshipBook()
    book.add_theme(_theme())


def test_duplicate_add_emits_no_extra_ledger_record():
    ledger = Ledger()
    book = StewardshipBook(ledger=ledger)
    book.add_theme(_theme(theme_id="theme:once"))
    with pytest.raises(DuplicateStewardshipThemeError):
        book.add_theme(_theme(theme_id="theme:once"))
    records = ledger.filter(event_type="stewardship_theme_added")
    assert len(records) == 1


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_exposes_stewardship_book():
    kernel = _kernel()
    assert isinstance(kernel.stewardship, StewardshipBook)
    assert kernel.stewardship.ledger is kernel.ledger
    assert kernel.stewardship.clock is kernel.clock


def test_kernel_add_theme_emits_to_kernel_ledger():
    kernel = _kernel()
    kernel.stewardship.add_theme(_theme())
    records = kernel.ledger.filter(event_type="stewardship_theme_added")
    assert len(records) == 1


def test_kernel_stewardship_simulation_date_uses_clock():
    """
    With the kernel's clock current_date set, the ledger record's
    simulation_date should reflect that date (the book's ``_now``
    helper reads the clock).
    """
    kernel = _kernel()
    kernel.stewardship.add_theme(_theme(theme_id="theme:wired"))
    records = kernel.ledger.filter(event_type="stewardship_theme_added")
    assert records[-1].simulation_date == "2026-01-01"


# ---------------------------------------------------------------------------
# No-mutation guarantee against every other source-of-truth book
# ---------------------------------------------------------------------------


def test_stewardship_book_does_not_mutate_other_kernel_books():
    """
    Adding themes, filtering, computing active windows, and building
    snapshots must not mutate any other source-of-truth book.
    """
    kernel = _kernel()

    # Seed unrelated books with one entry each so snapshot equality
    # is meaningful.
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
    }

    # Exercise every stewardship-layer write + read.
    kernel.stewardship.add_theme(
        _theme(
            theme_id="theme:k:a",
            related_variable_ids=("variable:reference_var_a",),
            related_signal_ids=("signal:reference_signal_a",),
        )
    )
    kernel.stewardship.add_theme(
        _theme(
            theme_id="theme:k:b",
            owner_id="investor:reference_pension_b",
            owner_type="asset_owner",
            theme_type="governance_structure",
            status="draft",
            priority="high",
            effective_from="2026-03-01",
            effective_to="2026-09-30",
        )
    )
    kernel.stewardship.list_themes()
    kernel.stewardship.list_by_owner("investor:reference_pension_a")
    kernel.stewardship.list_by_owner_type("investor")
    kernel.stewardship.list_by_theme_type("capital_allocation_discipline")
    kernel.stewardship.list_by_status("active")
    kernel.stewardship.list_by_priority("medium")
    kernel.stewardship.list_active_as_of("2026-06-15")
    kernel.stewardship.snapshot()

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


# ---------------------------------------------------------------------------
# No-action invariant
# ---------------------------------------------------------------------------


def test_stewardship_emits_only_stewardship_theme_added_records():
    """
    A bare ``add_theme`` call must emit exactly one ledger record
    of type ``STEWARDSHIP_THEME_ADDED`` and no other record type.
    The book is monitoring / attention storage only — it must not
    incidentally emit any signal, valuation, contract, ownership,
    interaction, or other behavioral record.
    """
    ledger = Ledger()
    book = StewardshipBook(ledger=ledger)
    book.add_theme(_theme(theme_id="theme:audit"))
    assert len(ledger.records) == 1
    record = ledger.records[0]
    assert record.record_type is RecordType.STEWARDSHIP_THEME_ADDED


# ---------------------------------------------------------------------------
# Jurisdiction-neutral identifier scan
#
# This test reads its own source file and confirms that every test
# string is jurisdiction-neutral. The forbidden token list mirrors
# ``world/experiment.py::_FORBIDDEN_TOKENS``; this duplication is
# intentional so that the test fails locally even when the
# experiment-config scan does not run.
# ---------------------------------------------------------------------------


_FORBIDDEN_TOKENS = (
    "toyota", "mufg", "smbc", "mizuho", "boj", "fsa", "jpx",
    "gpif", "tse", "nikkei", "topix", "sony", "jgb", "nyse",
)


def test_test_file_contains_no_jurisdiction_specific_identifiers():
    import re
    from pathlib import Path

    text = Path(__file__).read_text(encoding="utf-8").lower()
    # Strip the forbidden-token list literal itself so the test does
    # not flag its own audit table.
    table_start = text.find("_forbidden_tokens = (")
    table_end = text.find(")", table_start) + 1
    if table_start != -1 and table_end > 0:
        text = text[:table_start] + text[table_end:]

    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"jurisdiction-specific token {token!r} appeared in test file"
        )


def test_stewardship_module_contains_no_jurisdiction_specific_identifiers():
    import re
    from pathlib import Path

    module_path = (
        Path(__file__).resolve().parent.parent / "world" / "stewardship.py"
    )
    text = module_path.read_text(encoding="utf-8").lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"jurisdiction-specific token {token!r} appeared in "
            f"world/stewardship.py"
        )
