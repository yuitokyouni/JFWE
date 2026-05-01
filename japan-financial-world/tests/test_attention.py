"""
Tests for v1.8.5 AttentionProfile + ObservationMenu +
SelectedObservationSet.

Covers field validation for the three immutable record types,
``AttentionBook`` CRUD + filter listings for each, the
``profile_matches_menu`` structural-overlap predicate, ledger
emission of the three new ``RecordType`` members, snapshot
determinism, kernel wiring, and the no-mutation guarantee against
every other v0/v1 source-of-truth book.
"""

from __future__ import annotations

from datetime import date

import pytest

from world.attention import (
    AttentionBook,
    AttentionProfile,
    DuplicateAttentionProfileError,
    DuplicateObservationMenuError,
    DuplicateSelectedObservationSetError,
    ObservationMenu,
    SelectedObservationSet,
    UnknownAttentionProfileError,
    UnknownObservationMenuError,
    UnknownSelectedObservationSetError,
)
from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _profile(
    *,
    profile_id: str = "profile:investor:reference_pension_a:value_screening",
    actor_id: str = "investor:reference_pension_a",
    actor_type: str = "investor",
    update_frequency: str = "MONTHLY",
    phase_id: str | None = None,
    watched_space_ids: tuple[str, ...] = ("corporate", "exchange"),
    watched_subject_ids: tuple[str, ...] = ("firm:reference_manufacturer_a",),
    watched_signal_types: tuple[str, ...] = ("earnings_disclosure",),
    watched_channels: tuple[str, ...] = (
        "interaction:corporate.earnings_to_information",
    ),
    watched_metrics: tuple[str, ...] = ("earnings", "valuation_gap"),
    watched_valuation_types: tuple[str, ...] = ("equity",),
    watched_constraint_types: tuple[str, ...] = (),
    watched_relationship_types: tuple[str, ...] = (),
    watched_variable_ids: tuple[str, ...] = (),
    watched_variable_groups: tuple[str, ...] = (),
    watched_exposure_types: tuple[str, ...] = (),
    watched_exposure_metrics: tuple[str, ...] = (),
    priority_weights: dict | None = None,
    missing_input_policy: str = "degraded",
    enabled: bool = True,
    metadata: dict | None = None,
) -> AttentionProfile:
    return AttentionProfile(
        profile_id=profile_id,
        actor_id=actor_id,
        actor_type=actor_type,
        update_frequency=update_frequency,
        phase_id=phase_id,
        watched_space_ids=watched_space_ids,
        watched_subject_ids=watched_subject_ids,
        watched_signal_types=watched_signal_types,
        watched_channels=watched_channels,
        watched_metrics=watched_metrics,
        watched_valuation_types=watched_valuation_types,
        watched_constraint_types=watched_constraint_types,
        watched_relationship_types=watched_relationship_types,
        watched_variable_ids=watched_variable_ids,
        watched_variable_groups=watched_variable_groups,
        watched_exposure_types=watched_exposure_types,
        watched_exposure_metrics=watched_exposure_metrics,
        priority_weights=priority_weights or {},
        missing_input_policy=missing_input_policy,
        enabled=enabled,
        metadata=metadata or {},
    )


def _menu(
    *,
    menu_id: str = "menu:investor:reference_pension_a:2026-03-31",
    actor_id: str = "investor:reference_pension_a",
    as_of_date: str = "2026-03-31",
    phase_id: str | None = None,
    available_signal_ids: tuple[str, ...] = (
        "signal:earnings:firm_a:2026Q1",
    ),
    available_valuation_ids: tuple[str, ...] = (
        "valuation:firm_a:2026Q1",
    ),
    available_constraint_ids: tuple[str, ...] = (),
    available_relationship_ids: tuple[str, ...] = (),
    available_price_ids: tuple[str, ...] = (
        "price:firm_a:2026-03-31",
    ),
    available_external_observation_ids: tuple[str, ...] = (),
    available_interaction_ids: tuple[str, ...] = (
        "interaction:corporate.earnings_to_information",
    ),
    metadata: dict | None = None,
) -> ObservationMenu:
    return ObservationMenu(
        menu_id=menu_id,
        actor_id=actor_id,
        as_of_date=as_of_date,
        phase_id=phase_id,
        available_signal_ids=available_signal_ids,
        available_valuation_ids=available_valuation_ids,
        available_constraint_ids=available_constraint_ids,
        available_relationship_ids=available_relationship_ids,
        available_price_ids=available_price_ids,
        available_external_observation_ids=available_external_observation_ids,
        available_interaction_ids=available_interaction_ids,
        metadata=metadata or {},
    )


def _selection(
    *,
    selection_id: str = "selection:1",
    actor_id: str = "investor:reference_pension_a",
    attention_profile_id: str = (
        "profile:investor:reference_pension_a:value_screening"
    ),
    menu_id: str = "menu:investor:reference_pension_a:2026-03-31",
    routine_run_id: str | None = None,
    selected_refs: tuple[str, ...] = (
        "signal:earnings:firm_a:2026Q1",
        "valuation:firm_a:2026Q1",
    ),
    skipped_refs: tuple[str, ...] = (),
    selection_reason: str = "profile_match",
    as_of_date: str = "2026-03-31",
    phase_id: str | None = None,
    status: str = "completed",
    metadata: dict | None = None,
) -> SelectedObservationSet:
    return SelectedObservationSet(
        selection_id=selection_id,
        actor_id=actor_id,
        attention_profile_id=attention_profile_id,
        menu_id=menu_id,
        routine_run_id=routine_run_id,
        selected_refs=selected_refs,
        skipped_refs=skipped_refs,
        selection_reason=selection_reason,
        as_of_date=as_of_date,
        phase_id=phase_id,
        status=status,
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
# AttentionProfile validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"profile_id": ""},
        {"actor_id": ""},
        {"actor_type": ""},
        {"update_frequency": ""},
        {"missing_input_policy": ""},
        {"phase_id": ""},
    ],
)
def test_profile_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _profile(**kwargs)


def test_profile_rejects_non_bool_enabled():
    with pytest.raises(ValueError):
        _profile(enabled="yes")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "tuple_field",
    [
        "watched_space_ids",
        "watched_subject_ids",
        "watched_signal_types",
        "watched_channels",
        "watched_metrics",
        "watched_valuation_types",
        "watched_constraint_types",
        "watched_relationship_types",
        "watched_variable_ids",
        "watched_variable_groups",
        "watched_exposure_types",
        "watched_exposure_metrics",
    ],
)
def test_profile_rejects_empty_strings_in_tuple_fields(tuple_field):
    bad = {tuple_field: ("valid", "")}
    with pytest.raises(ValueError):
        _profile(**bad)


def test_profile_priority_weights_must_be_numeric():
    with pytest.raises(ValueError):
        _profile(priority_weights={"key": "not-a-number"})  # type: ignore[arg-type]


def test_profile_priority_weights_rejects_bool():
    """bool is an int subclass; we want true numerics only."""
    with pytest.raises(ValueError):
        _profile(priority_weights={"key": True})  # type: ignore[arg-type]


def test_profile_priority_weights_preserved_and_numeric():
    p = _profile(priority_weights={"a": 0.5, "b": 2})
    assert isinstance(p.priority_weights, dict)
    assert p.priority_weights["a"] == 0.5
    assert p.priority_weights["b"] == 2.0
    assert isinstance(p.priority_weights["b"], float)


def test_profile_default_missing_input_policy_is_degraded():
    p = AttentionProfile(
        profile_id="p:1",
        actor_id="a:1",
        actor_type="investor",
        update_frequency="DAILY",
    )
    assert p.missing_input_policy == "degraded"


def test_profile_is_frozen():
    p = _profile()
    with pytest.raises(Exception):
        p.profile_id = "tampered"  # type: ignore[misc]


def test_profile_to_dict_round_trips_fields():
    p = _profile(priority_weights={"earnings": 1.0})
    d = p.to_dict()
    assert d["profile_id"] == p.profile_id
    assert d["actor_id"] == p.actor_id
    assert d["actor_type"] == p.actor_type
    assert d["priority_weights"] == {"earnings": 1.0}
    assert d["missing_input_policy"] == "degraded"


# ---------------------------------------------------------------------------
# v1.8.12: variable / exposure watch hooks
# ---------------------------------------------------------------------------


def test_profile_v1812_fields_default_empty():
    p = _profile()
    assert p.watched_variable_ids == ()
    assert p.watched_variable_groups == ()
    assert p.watched_exposure_types == ()
    assert p.watched_exposure_metrics == ()


def test_profile_v1812_fields_normalize_to_tuples():
    p = _profile(
        watched_variable_ids=["variable:cpi_yoy", "variable:jpy_usd"],
        watched_variable_groups=["fx", "rates"],
        watched_exposure_types=["funding_cost"],
        watched_exposure_metrics=["debt_service_burden"],
    )
    assert p.watched_variable_ids == ("variable:cpi_yoy", "variable:jpy_usd")
    assert p.watched_variable_groups == ("fx", "rates")
    assert p.watched_exposure_types == ("funding_cost",)
    assert p.watched_exposure_metrics == ("debt_service_burden",)


def test_profile_v1812_fields_appear_in_to_dict():
    p = _profile(
        watched_variable_ids=("variable:jgb_10y",),
        watched_variable_groups=("rates",),
        watched_exposure_types=("collateral",),
        watched_exposure_metrics=("collateral_value",),
    )
    d = p.to_dict()
    assert d["watched_variable_ids"] == ["variable:jgb_10y"]
    assert d["watched_variable_groups"] == ["rates"]
    assert d["watched_exposure_types"] == ["collateral"]
    assert d["watched_exposure_metrics"] == ["collateral_value"]


def test_profile_v1812_fields_appear_in_ledger_payload():
    ledger = Ledger()
    book = AttentionBook(ledger=ledger)
    book.add_profile(
        _profile(
            profile_id="p:1812",
            watched_variable_ids=("variable:cpi_yoy",),
            watched_variable_groups=("inflation",),
            watched_exposure_types=("input_cost",),
            watched_exposure_metrics=("operating_cost_pressure",),
        )
    )
    records = ledger.filter(event_type="attention_profile_added")
    payload = records[-1].payload
    assert tuple(payload["watched_variable_ids"]) == ("variable:cpi_yoy",)
    assert tuple(payload["watched_variable_groups"]) == ("inflation",)
    assert tuple(payload["watched_exposure_types"]) == ("input_cost",)
    assert tuple(payload["watched_exposure_metrics"]) == (
        "operating_cost_pressure",
    )


def test_profile_matches_menu_includes_v1812_dimensions():
    book = AttentionBook()
    profile = _profile(
        profile_id="p:1812:overlap",
        watched_variable_ids=("variable:jgb_10y",),
        watched_variable_groups=("rates",),
        watched_exposure_types=("funding_cost",),
        watched_exposure_metrics=("debt_service_burden",),
    )
    book.add_profile(profile)
    menu = ObservationMenu(
        menu_id="m:1812",
        actor_id=profile.actor_id,
        as_of_date="2026-04-30",
        available_variable_observation_ids=("o:jgb",),
        available_exposure_ids=("e:funding",),
    )
    book.add_menu(menu)
    summary = book.profile_matches_menu(profile.profile_id, menu.menu_id)
    per = summary["per_dimension"]
    assert "watched_variable_ids" in per
    assert "watched_variable_groups" in per
    assert "watched_exposure_types" in per
    assert "watched_exposure_metrics" in per
    assert per["watched_variable_ids"]["menu_available_count"] == 1
    assert per["watched_exposure_types"]["menu_available_count"] == 1
    assert summary["has_any_overlap"] is True


# ---------------------------------------------------------------------------
# ObservationMenu validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"menu_id": ""},
        {"actor_id": ""},
        {"as_of_date": ""},
        {"phase_id": ""},
    ],
)
def test_menu_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _menu(**kwargs)


def test_menu_coerces_date_to_iso_string():
    m = _menu(as_of_date=date(2026, 3, 31))
    assert m.as_of_date == "2026-03-31"


@pytest.mark.parametrize(
    "tuple_field",
    [
        "available_signal_ids",
        "available_valuation_ids",
        "available_constraint_ids",
        "available_relationship_ids",
        "available_price_ids",
        "available_external_observation_ids",
        "available_interaction_ids",
    ],
)
def test_menu_rejects_empty_strings_in_tuple_fields(tuple_field):
    bad = {tuple_field: ("valid", "")}
    with pytest.raises(ValueError):
        _menu(**bad)


def test_menu_accepts_empty_menu():
    """An entirely empty menu is a valid recorded state."""
    m = ObservationMenu(
        menu_id="menu:empty",
        actor_id="investor:x",
        as_of_date="2026-03-31",
    )
    assert m.total_available_count() == 0


def test_menu_accepts_partial_menu():
    """Some availability lists empty, others populated."""
    m = _menu(
        available_signal_ids=("signal:a",),
        available_valuation_ids=(),
        available_constraint_ids=(),
        available_relationship_ids=(),
        available_price_ids=(),
        available_external_observation_ids=(),
        available_interaction_ids=("interaction:x",),
    )
    assert m.total_available_count() == 2


def test_menu_is_frozen():
    m = _menu()
    with pytest.raises(Exception):
        m.menu_id = "tampered"  # type: ignore[misc]


def test_menu_to_dict_round_trips_fields():
    m = _menu()
    d = m.to_dict()
    assert d["menu_id"] == m.menu_id
    assert d["available_signal_ids"] == list(m.available_signal_ids)
    assert d["available_interaction_ids"] == list(m.available_interaction_ids)


# ---------------------------------------------------------------------------
# SelectedObservationSet validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"selection_id": ""},
        {"actor_id": ""},
        {"attention_profile_id": ""},
        {"menu_id": ""},
        {"selection_reason": ""},
        {"as_of_date": ""},
        {"status": ""},
        {"routine_run_id": ""},
        {"phase_id": ""},
    ],
)
def test_selection_rejects_empty_required_strings(kwargs):
    with pytest.raises(ValueError):
        _selection(**kwargs)


def test_selection_coerces_date_to_iso_string():
    s = _selection(as_of_date=date(2026, 3, 31))
    assert s.as_of_date == "2026-03-31"


@pytest.mark.parametrize(
    "tuple_field",
    ["selected_refs", "skipped_refs"],
)
def test_selection_rejects_empty_strings_in_tuple_fields(tuple_field):
    bad = {tuple_field: ("valid", "")}
    with pytest.raises(ValueError):
        _selection(**bad)


@pytest.mark.parametrize(
    "status",
    ["completed", "partial", "degraded", "empty"],
)
def test_selection_accepts_recommended_status_vocabulary(status):
    s = _selection(status=status)
    assert s.status == status


def test_selection_is_frozen():
    s = _selection()
    with pytest.raises(Exception):
        s.selection_id = "tampered"  # type: ignore[misc]


def test_selection_to_dict_round_trips_fields():
    s = _selection(routine_run_id="run:routine:1:2026Q1")
    d = s.to_dict()
    assert d["selection_id"] == s.selection_id
    assert d["routine_run_id"] == "run:routine:1:2026Q1"
    assert d["selected_refs"] == list(s.selected_refs)


def test_selection_does_not_enforce_subset_of_menu():
    """
    v1.8.5 documented behavior: selected_refs are NOT required to
    be a subset of any menu's available_*_ids. The storage layer
    persists what the caller gives it; engine layers may enforce
    subset semantics if they wish.
    """
    s = _selection(selected_refs=("signal:not_on_menu",))
    assert s.selected_refs == ("signal:not_on_menu",)


# ---------------------------------------------------------------------------
# AttentionBook: profile CRUD + listings
# ---------------------------------------------------------------------------


def test_add_and_get_profile():
    book = AttentionBook()
    p = _profile()
    book.add_profile(p)
    assert book.get_profile(p.profile_id) is p


def test_get_profile_unknown_raises():
    book = AttentionBook()
    with pytest.raises(UnknownAttentionProfileError):
        book.get_profile("profile:does_not_exist")


def test_duplicate_profile_id_rejected():
    book = AttentionBook()
    book.add_profile(_profile())
    with pytest.raises(DuplicateAttentionProfileError):
        book.add_profile(_profile())


def test_multiple_profiles_per_actor_allowed():
    """A bank may have separate daily-liquidity and quarterly-review
    profiles; this is the v1.8.2 design's "multiple profiles per
    actor" rule."""
    book = AttentionBook()
    book.add_profile(
        _profile(
            profile_id="profile:bank_a:liquidity_daily",
            actor_id="bank:reference_bank_a",
            actor_type="bank",
            update_frequency="DAILY",
        )
    )
    book.add_profile(
        _profile(
            profile_id="profile:bank_a:counterparty_quarterly",
            actor_id="bank:reference_bank_a",
            actor_type="bank",
            update_frequency="QUARTERLY",
        )
    )
    listed = book.list_profiles_by_actor("bank:reference_bank_a")
    assert len(listed) == 2


def test_disabled_profiles_excluded_by_default():
    book = AttentionBook()
    book.add_profile(_profile(profile_id="profile:enabled"))
    book.add_profile(_profile(profile_id="profile:disabled", enabled=False))
    ids = {p.profile_id for p in book.list_profiles()}
    assert ids == {"profile:enabled"}


def test_disabled_profiles_included_with_flag():
    book = AttentionBook()
    book.add_profile(_profile(profile_id="profile:enabled"))
    book.add_profile(_profile(profile_id="profile:disabled", enabled=False))
    ids = {p.profile_id for p in book.list_profiles(include_disabled=True)}
    assert ids == {"profile:enabled", "profile:disabled"}


def test_list_profiles_by_actor():
    book = AttentionBook()
    book.add_profile(_profile(profile_id="profile:a:1", actor_id="actor:a"))
    book.add_profile(_profile(profile_id="profile:a:2", actor_id="actor:a"))
    book.add_profile(_profile(profile_id="profile:b:1", actor_id="actor:b"))
    a_profiles = book.list_profiles_by_actor("actor:a")
    assert {p.profile_id for p in a_profiles} == {"profile:a:1", "profile:a:2"}
    assert book.list_profiles_by_actor("actor:unknown") == ()


def test_list_profiles_by_actor_type():
    book = AttentionBook()
    book.add_profile(_profile(profile_id="p:i1", actor_type="investor"))
    book.add_profile(_profile(profile_id="p:i2", actor_type="investor"))
    book.add_profile(_profile(profile_id="p:b1", actor_type="bank"))
    investors = book.list_profiles_by_actor_type("investor")
    assert {p.profile_id for p in investors} == {"p:i1", "p:i2"}


def test_list_profiles_by_watched_space():
    book = AttentionBook()
    book.add_profile(
        _profile(
            profile_id="p:1",
            watched_space_ids=("corporate", "exchange"),
        )
    )
    book.add_profile(
        _profile(
            profile_id="p:2",
            watched_space_ids=("policy",),
        )
    )
    corp = book.list_profiles_by_watched_space("corporate")
    assert {p.profile_id for p in corp} == {"p:1"}
    pol = book.list_profiles_by_watched_space("policy")
    assert {p.profile_id for p in pol} == {"p:2"}


def test_list_profiles_by_channel():
    book = AttentionBook()
    book.add_profile(
        _profile(
            profile_id="p:1",
            watched_channels=("interaction:corporate.earnings_to_information",),
        )
    )
    book.add_profile(
        _profile(
            profile_id="p:2",
            watched_channels=("interaction:bank.review_to_corporate",),
        )
    )
    earnings = book.list_profiles_by_channel(
        "interaction:corporate.earnings_to_information"
    )
    assert {p.profile_id for p in earnings} == {"p:1"}


def test_disabled_excluded_from_filter_listings_too():
    book = AttentionBook()
    book.add_profile(_profile(profile_id="p:enabled", actor_id="actor:a"))
    book.add_profile(
        _profile(profile_id="p:disabled", actor_id="actor:a", enabled=False)
    )
    assert {
        p.profile_id for p in book.list_profiles_by_actor("actor:a")
    } == {"p:enabled"}
    assert {
        p.profile_id
        for p in book.list_profiles_by_actor("actor:a", include_disabled=True)
    } == {"p:enabled", "p:disabled"}


# ---------------------------------------------------------------------------
# AttentionBook: menu CRUD + listings
# ---------------------------------------------------------------------------


def test_add_and_get_menu():
    book = AttentionBook()
    m = _menu()
    book.add_menu(m)
    assert book.get_menu(m.menu_id) is m


def test_get_menu_unknown_raises():
    book = AttentionBook()
    with pytest.raises(UnknownObservationMenuError):
        book.get_menu("menu:does_not_exist")


def test_duplicate_menu_id_rejected():
    book = AttentionBook()
    book.add_menu(_menu())
    with pytest.raises(DuplicateObservationMenuError):
        book.add_menu(_menu())


def test_book_accepts_empty_menu():
    book = AttentionBook()
    empty = ObservationMenu(
        menu_id="menu:empty",
        actor_id="investor:x",
        as_of_date="2026-03-31",
    )
    book.add_menu(empty)
    assert book.get_menu("menu:empty").total_available_count() == 0


def test_book_accepts_partial_menu():
    book = AttentionBook()
    partial = _menu(
        available_signal_ids=("signal:only_one",),
        available_valuation_ids=(),
        available_constraint_ids=(),
        available_relationship_ids=(),
        available_price_ids=(),
        available_external_observation_ids=(),
        available_interaction_ids=(),
    )
    book.add_menu(partial)
    assert book.get_menu(partial.menu_id).total_available_count() == 1


def test_list_menus_by_actor():
    book = AttentionBook()
    book.add_menu(_menu(menu_id="menu:1", actor_id="actor:a"))
    book.add_menu(_menu(menu_id="menu:2", actor_id="actor:a"))
    book.add_menu(_menu(menu_id="menu:3", actor_id="actor:b"))
    a_menus = book.list_menus_by_actor("actor:a")
    assert {m.menu_id for m in a_menus} == {"menu:1", "menu:2"}
    assert book.list_menus_by_actor("actor:unknown") == ()


def test_list_menus_by_date_accepts_str_and_date():
    book = AttentionBook()
    book.add_menu(_menu(menu_id="menu:1", as_of_date="2026-03-31"))
    book.add_menu(_menu(menu_id="menu:2", as_of_date="2026-06-30"))
    by_str = book.list_menus_by_date("2026-03-31")
    by_date = book.list_menus_by_date(date(2026, 3, 31))
    assert {m.menu_id for m in by_str} == {"menu:1"}
    assert {m.menu_id for m in by_date} == {"menu:1"}


# ---------------------------------------------------------------------------
# AttentionBook: selection CRUD + listings
# ---------------------------------------------------------------------------


def test_add_and_get_selection():
    book = AttentionBook()
    s = _selection()
    book.add_selection(s)
    assert book.get_selection(s.selection_id) is s


def test_get_selection_unknown_raises():
    book = AttentionBook()
    with pytest.raises(UnknownSelectedObservationSetError):
        book.get_selection("selection:does_not_exist")


def test_duplicate_selection_id_rejected():
    book = AttentionBook()
    book.add_selection(_selection())
    with pytest.raises(DuplicateSelectedObservationSetError):
        book.add_selection(_selection())


@pytest.mark.parametrize(
    "status",
    ["completed", "partial", "degraded", "empty"],
)
def test_book_accepts_selection_with_each_status(status):
    book = AttentionBook()
    book.add_selection(_selection(selection_id=f"selection:{status}", status=status))
    assert book.get_selection(f"selection:{status}").status == status


def test_list_selections_by_actor():
    book = AttentionBook()
    book.add_selection(_selection(selection_id="s:1", actor_id="actor:a"))
    book.add_selection(_selection(selection_id="s:2", actor_id="actor:a"))
    book.add_selection(_selection(selection_id="s:3", actor_id="actor:b"))
    a_sels = book.list_selections_by_actor("actor:a")
    assert {s.selection_id for s in a_sels} == {"s:1", "s:2"}


def test_list_selections_by_profile():
    book = AttentionBook()
    book.add_selection(_selection(selection_id="s:1", attention_profile_id="p:1"))
    book.add_selection(_selection(selection_id="s:2", attention_profile_id="p:1"))
    book.add_selection(_selection(selection_id="s:3", attention_profile_id="p:2"))
    p1 = book.list_selections_by_profile("p:1")
    assert {s.selection_id for s in p1} == {"s:1", "s:2"}


def test_list_selections_by_menu():
    book = AttentionBook()
    book.add_selection(_selection(selection_id="s:1", menu_id="menu:1"))
    book.add_selection(_selection(selection_id="s:2", menu_id="menu:1"))
    book.add_selection(_selection(selection_id="s:3", menu_id="menu:2"))
    m1 = book.list_selections_by_menu("menu:1")
    assert {s.selection_id for s in m1} == {"s:1", "s:2"}


def test_list_selections_by_status():
    book = AttentionBook()
    book.add_selection(_selection(selection_id="s:c", status="completed"))
    book.add_selection(_selection(selection_id="s:p", status="partial"))
    book.add_selection(_selection(selection_id="s:d", status="degraded"))
    book.add_selection(_selection(selection_id="s:e", status="empty"))
    assert {
        s.selection_id for s in book.list_selections_by_status("completed")
    } == {"s:c"}
    assert {
        s.selection_id for s in book.list_selections_by_status("partial")
    } == {"s:p"}
    assert {
        s.selection_id for s in book.list_selections_by_status("degraded")
    } == {"s:d"}
    assert {
        s.selection_id for s in book.list_selections_by_status("empty")
    } == {"s:e"}


# ---------------------------------------------------------------------------
# profile_matches_menu predicate
# ---------------------------------------------------------------------------


def test_profile_matches_menu_summary_shape():
    book = AttentionBook()
    book.add_profile(_profile())
    book.add_menu(_menu())
    summary = book.profile_matches_menu(
        "profile:investor:reference_pension_a:value_screening",
        "menu:investor:reference_pension_a:2026-03-31",
    )
    assert "profile_id" in summary
    assert "menu_id" in summary
    assert "has_any_overlap" in summary
    assert "per_dimension" in summary


def test_profile_matches_menu_finds_overlap_when_signals_present():
    """Profile watches earnings; menu has signals available."""
    book = AttentionBook()
    book.add_profile(_profile())  # watches signal_types + valuations + channels
    book.add_menu(_menu())  # menu has signals + valuations + interactions
    summary = book.profile_matches_menu(
        "profile:investor:reference_pension_a:value_screening",
        "menu:investor:reference_pension_a:2026-03-31",
    )
    assert summary["has_any_overlap"] is True
    # Watched dimensions populated => present in per_dimension.
    assert "watched_signal_types" in summary["per_dimension"]
    assert summary["per_dimension"]["watched_signal_types"][
        "menu_available_count"
    ] == 1


def test_profile_matches_menu_reports_no_overlap_when_menu_empty():
    book = AttentionBook()
    book.add_profile(_profile())
    book.add_menu(
        ObservationMenu(
            menu_id="menu:empty",
            actor_id="investor:reference_pension_a",
            as_of_date="2026-03-31",
        )
    )
    summary = book.profile_matches_menu(
        "profile:investor:reference_pension_a:value_screening",
        "menu:empty",
    )
    assert summary["has_any_overlap"] is False
    # Profile's watched dimensions still appear with menu_available_count=0.
    assert summary["per_dimension"]["watched_signal_types"][
        "menu_available_count"
    ] == 0


def test_profile_matches_menu_omits_unwatched_dimensions():
    """A profile that doesn't watch valuations gets no valuation row."""
    book = AttentionBook()
    book.add_profile(
        _profile(
            watched_signal_types=("earnings_disclosure",),
            watched_valuation_types=(),
            watched_constraint_types=(),
            watched_relationship_types=(),
            watched_channels=(),
        )
    )
    book.add_menu(_menu())
    summary = book.profile_matches_menu(
        "profile:investor:reference_pension_a:value_screening",
        "menu:investor:reference_pension_a:2026-03-31",
    )
    assert "watched_signal_types" in summary["per_dimension"]
    assert "watched_valuation_types" not in summary["per_dimension"]
    assert "watched_channels" not in summary["per_dimension"]


def test_profile_matches_menu_unknown_profile_raises():
    book = AttentionBook()
    book.add_menu(_menu())
    with pytest.raises(UnknownAttentionProfileError):
        book.profile_matches_menu(
            "profile:unknown",
            "menu:investor:reference_pension_a:2026-03-31",
        )


def test_profile_matches_menu_unknown_menu_raises():
    book = AttentionBook()
    book.add_profile(_profile())
    with pytest.raises(UnknownObservationMenuError):
        book.profile_matches_menu(
            "profile:investor:reference_pension_a:value_screening",
            "menu:unknown",
        )


def test_profile_matches_menu_does_not_mutate_book():
    book = AttentionBook()
    book.add_profile(_profile())
    book.add_menu(_menu())
    snap_before = book.snapshot()
    book.profile_matches_menu(
        "profile:investor:reference_pension_a:value_screening",
        "menu:investor:reference_pension_a:2026-03-31",
    )
    assert book.snapshot() == snap_before


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_is_deterministic_and_sorted():
    book = AttentionBook()
    book.add_profile(_profile(profile_id="p:beta"))
    book.add_profile(_profile(profile_id="p:alpha"))
    book.add_menu(_menu(menu_id="menu:beta"))
    book.add_menu(_menu(menu_id="menu:alpha"))
    book.add_selection(
        _selection(selection_id="s:beta", menu_id="menu:beta", attention_profile_id="p:beta")
    )
    book.add_selection(
        _selection(selection_id="s:alpha", menu_id="menu:alpha", attention_profile_id="p:alpha")
    )
    snap_a = book.snapshot()
    snap_b = book.snapshot()
    assert snap_a == snap_b
    assert [p["profile_id"] for p in snap_a["profiles"]] == sorted(
        p["profile_id"] for p in snap_a["profiles"]
    )
    assert [m["menu_id"] for m in snap_a["menus"]] == sorted(
        m["menu_id"] for m in snap_a["menus"]
    )
    assert [s["selection_id"] for s in snap_a["selections"]] == sorted(
        s["selection_id"] for s in snap_a["selections"]
    )


def test_snapshot_counts_disabled_profiles_separately():
    book = AttentionBook()
    book.add_profile(_profile(profile_id="p:e"))
    book.add_profile(_profile(profile_id="p:d", enabled=False))
    snap = book.snapshot()
    assert snap["profile_count"] == 2
    assert snap["enabled_profile_count"] == 1


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_record_types_exist():
    assert RecordType.ATTENTION_PROFILE_ADDED.value == "attention_profile_added"
    assert RecordType.OBSERVATION_MENU_CREATED.value == "observation_menu_created"
    assert RecordType.OBSERVATION_SET_SELECTED.value == "observation_set_selected"


def test_add_profile_writes_ledger_record_when_present():
    ledger = Ledger()
    clock = Clock(current_date=date(2026, 1, 1))
    book = AttentionBook(ledger=ledger, clock=clock)
    book.add_profile(_profile())
    records = ledger.filter(event_type="attention_profile_added")
    assert len(records) == 1
    rec = records[0]
    assert rec.object_id == "profile:investor:reference_pension_a:value_screening"
    assert rec.payload["actor_id"] == "investor:reference_pension_a"


def test_add_menu_writes_ledger_record_when_present():
    ledger = Ledger()
    clock = Clock(current_date=date(2026, 1, 1))
    book = AttentionBook(ledger=ledger, clock=clock)
    m = _menu()
    book.add_menu(m)
    records = ledger.filter(event_type="observation_menu_created")
    assert len(records) == 1
    rec = records[0]
    assert rec.object_id == m.menu_id
    # Use as_of_date as simulation_date.
    assert rec.simulation_date == m.as_of_date
    assert rec.payload["total_available_count"] == m.total_available_count()


def test_add_selection_writes_ledger_record_when_present():
    ledger = Ledger()
    clock = Clock(current_date=date(2026, 1, 1))
    book = AttentionBook(ledger=ledger, clock=clock)
    s = _selection(routine_run_id="run:routine:1:2026Q1")
    book.add_selection(s)
    records = ledger.filter(event_type="observation_set_selected")
    assert len(records) == 1
    rec = records[0]
    assert rec.object_id == s.selection_id
    assert rec.target == s.menu_id
    assert rec.simulation_date == s.as_of_date
    # routine_run_id flows to the ledger correlation_id field.
    assert rec.correlation_id == s.routine_run_id
    assert rec.payload["status"] == s.status
    # Ledger _freeze converts list payload entries to tuples; compare by tuple.
    assert tuple(rec.payload["selected_refs"]) == s.selected_refs


def test_add_methods_without_ledger_do_not_raise():
    book = AttentionBook()
    book.add_profile(_profile())
    book.add_menu(_menu())
    book.add_selection(_selection())


# ---------------------------------------------------------------------------
# Kernel wiring + no-mutation guarantee
# ---------------------------------------------------------------------------


def test_kernel_exposes_attention_book():
    kernel = _kernel()
    assert isinstance(kernel.attention, AttentionBook)
    assert kernel.attention.ledger is kernel.ledger
    assert kernel.attention.clock is kernel.clock


def test_kernel_add_profile_emits_to_kernel_ledger():
    kernel = _kernel()
    kernel.attention.add_profile(_profile())
    records = kernel.ledger.filter(event_type="attention_profile_added")
    assert len(records) == 1


def test_attention_book_does_not_mutate_other_kernel_books():
    """
    Adding profiles, menus, selections, building snapshots, and
    using the predicate must not mutate any other source-of-truth
    book.
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
    }

    # Exercise every attention-layer write + read.
    kernel.attention.add_profile(_profile())
    kernel.attention.add_menu(_menu())
    kernel.attention.add_selection(_selection())
    kernel.attention.list_profiles()
    kernel.attention.list_profiles_by_actor("investor:reference_pension_a")
    kernel.attention.list_profiles_by_actor_type("investor")
    kernel.attention.list_profiles_by_watched_space("corporate")
    kernel.attention.list_profiles_by_channel(
        "interaction:corporate.earnings_to_information"
    )
    kernel.attention.list_menus_by_actor("investor:reference_pension_a")
    kernel.attention.list_menus_by_date("2026-03-31")
    kernel.attention.list_selections_by_actor("investor:reference_pension_a")
    kernel.attention.list_selections_by_profile(
        "profile:investor:reference_pension_a:value_screening"
    )
    kernel.attention.list_selections_by_menu(
        "menu:investor:reference_pension_a:2026-03-31"
    )
    kernel.attention.list_selections_by_status("completed")
    kernel.attention.profile_matches_menu(
        "profile:investor:reference_pension_a:value_screening",
        "menu:investor:reference_pension_a:2026-03-31",
    )
    kernel.attention.snapshot()

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
