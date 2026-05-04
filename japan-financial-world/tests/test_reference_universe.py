"""
Tests for v1.20.1 reference-universe storage —
``world.reference_universe``.

Pinned invariants:

- twelve closed-set vocabularies for the universe / sector /
  firm shapes;
- v1.20.0 hard naming boundary
  (``FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES``) disjoint from
  every closed-set vocabulary; dataclass field names disjoint;
  payload + metadata keys rejected at construction;
- frozen dataclasses with strict construction-time validation;
- duplicate id rejected on every add (no extra ledger record);
- unknown lookup raises;
- every list / filter method returns the right subset;
- snapshot determinism;
- ledger emits exactly one record per add;
- kernel wiring (``WorldKernel.reference_universe``);
- empty book does **not** move ``quarterly_default``
  (`f93bdf3f…b705897c`) or `monthly_reference`
  (`75a91cfa…91879d`) digest;
- :func:`build_generic_11_sector_reference_universe` produces
  exactly 11 sectors + 11 firm profiles, each with a
  ``_like`` sector label, jurisdiction-neutral synthetic ids;
  does **not** auto-register;
- explicit
  :func:`register_generic_11_sector_reference_universe` writes
  to the kernel's book + ledger and is byte-deterministic;
- no ``PriceBook`` / source-of-truth book mutation;
- jurisdiction-neutral identifier scan + licensed-taxonomy
  scan over module + test text.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from world.clock import Clock
from world.kernel import WorldKernel
from world.ledger import Ledger, RecordType
from world.reference_universe import (
    BALANCE_SHEET_STYLE_LABELS,
    DEMAND_CYCLICALITY_LABELS,
    DuplicateGenericSectorReferenceError,
    DuplicateReferenceUniverseProfileError,
    DuplicateSyntheticSectorFirmProfileError,
    FIRM_SIZE_LABELS,
    FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES,
    FUNDING_DEPENDENCY_LABELS,
    GenericReferenceUniverseFixture,
    GenericSectorReference,
    INPUT_COST_EXPOSURE_LABELS,
    ReferenceUniverseBook,
    ReferenceUniverseProfile,
    SECTOR_GROUP_LABELS,
    SECTOR_LABELS,
    SECTOR_TAXONOMY_LABELS,
    SENSITIVITY_LABELS,
    STATUS_LABELS,
    SyntheticSectorFirmProfile,
    UNIVERSE_PROFILE_LABELS,
    UnknownGenericSectorReferenceError,
    UnknownReferenceUniverseProfileError,
    UnknownSyntheticSectorFirmProfileError,
    VISIBILITY_LABELS,
    build_generic_11_sector_reference_universe,
    default_firm_id_order,
    default_sector_label_order,
    register_generic_11_sector_reference_universe,
)
from world.registry import Registry
from world.scheduler import Scheduler
from world.state import State


_MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "world"
    / "reference_universe.py"
)


# ---------------------------------------------------------------------------
# Closed-set vocabularies
# ---------------------------------------------------------------------------


def test_universe_profile_labels_closed_set():
    assert UNIVERSE_PROFILE_LABELS == frozenset(
        {
            "tiny_default",
            "generic_11_sector",
            "generic_broad_market",
            "custom_synthetic",
            "unknown",
        }
    )


def test_sector_taxonomy_labels_closed_set():
    assert SECTOR_TAXONOMY_LABELS == frozenset(
        {
            "generic_11_sector_reference",
            "generic_macro_sector_reference",
            "custom_synthetic",
            "unknown",
        }
    )


def test_sector_labels_closed_set():
    assert SECTOR_LABELS == frozenset(
        {
            "energy_like",
            "materials_like",
            "industrials_like",
            "consumer_discretionary_like",
            "consumer_staples_like",
            "health_care_like",
            "financials_like",
            "information_technology_like",
            "communication_services_like",
            "utilities_like",
            "real_estate_like",
            "unknown",
        }
    )


def test_sector_group_labels_closed_set():
    assert SECTOR_GROUP_LABELS == frozenset(
        {
            "cyclical",
            "defensive",
            "financial",
            "technology_related",
            "real_asset_related",
            "regulated_utility_like",
            "unknown",
        }
    )


def test_sensitivity_labels_closed_set():
    assert SENSITIVITY_LABELS == frozenset(
        {"low", "moderate", "high", "unknown"}
    )


def test_firm_size_labels_closed_set():
    assert FIRM_SIZE_LABELS == frozenset(
        {"small", "mid", "large", "mega_like", "unknown"}
    )


def test_balance_sheet_style_labels_closed_set():
    assert BALANCE_SHEET_STYLE_LABELS == frozenset(
        {
            "asset_light",
            "asset_heavy",
            "working_capital_intensive",
            "regulated_asset_base_like",
            "financial_balance_sheet",
            "unknown",
        }
    )


def test_funding_dependency_labels_closed_set():
    assert FUNDING_DEPENDENCY_LABELS == frozenset(
        {"low", "moderate", "high", "unknown"}
    )


def test_demand_cyclicality_labels_closed_set():
    assert DEMAND_CYCLICALITY_LABELS == frozenset(
        {
            "defensive",
            "moderate",
            "cyclical",
            "highly_cyclical",
            "unknown",
        }
    )


def test_input_cost_exposure_labels_closed_set():
    assert INPUT_COST_EXPOSURE_LABELS == frozenset(
        {"low", "moderate", "high", "unknown"}
    )


def test_status_labels_closed_set():
    assert STATUS_LABELS == frozenset(
        {
            "draft",
            "active",
            "stale",
            "superseded",
            "archived",
            "unknown",
        }
    )


def test_visibility_labels_closed_set():
    assert VISIBILITY_LABELS == frozenset(
        {"public", "restricted", "internal", "private", "unknown"}
    )


def test_sector_labels_all_carry_like_suffix_except_unknown():
    """v1.20.0 binding: every sector label except `unknown`
    carries the `_like` suffix to make the non-real-membership
    discipline visible at every read site."""
    for label in SECTOR_LABELS:
        if label == "unknown":
            continue
        assert label.endswith("_like"), (
            f"sector label {label!r} must carry the `_like` suffix"
        )


# ---------------------------------------------------------------------------
# Forbidden field-name boundary
# ---------------------------------------------------------------------------


_V1_20_0_PINNED_FORBIDDEN_NAMES = (
    "real_company_name",
    "real_sector_weight",
    "market_cap",
    "leverage_ratio",
    "revenue",
    "ebitda",
    "net_income",
    "real_financial_value",
    "gics",
    "msci",
    "sp_index",
    "topix",
    "nikkei",
    "jpx",
    "buy",
    "sell",
    "order",
    "trade",
    "execution",
    "recommendation",
    "investment_advice",
    "target_price",
    "expected_return",
    "market_price",
    "forecast_path",
    "japan_calibration",
    "llm_output",
    "llm_prose",
    "prompt_text",
)


def test_forbidden_field_names_includes_v1_20_0_pinned_set():
    pinned = set(_V1_20_0_PINNED_FORBIDDEN_NAMES)
    assert pinned <= FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES


def test_forbidden_field_names_disjoint_from_every_closed_set():
    for vocab in (
        UNIVERSE_PROFILE_LABELS,
        SECTOR_TAXONOMY_LABELS,
        SECTOR_LABELS,
        SECTOR_GROUP_LABELS,
        SENSITIVITY_LABELS,
        FIRM_SIZE_LABELS,
        BALANCE_SHEET_STYLE_LABELS,
        FUNDING_DEPENDENCY_LABELS,
        DEMAND_CYCLICALITY_LABELS,
        INPUT_COST_EXPOSURE_LABELS,
        STATUS_LABELS,
        VISIBILITY_LABELS,
    ):
        assert not (
            FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES & vocab
        )


def test_dataclass_field_names_disjoint_from_forbidden():
    for cls in (
        ReferenceUniverseProfile,
        GenericSectorReference,
        SyntheticSectorFirmProfile,
    ):
        fields = set(cls.__dataclass_fields__.keys())
        assert not (
            fields & FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES
        ), f"{cls.__name__} has a forbidden field name"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _profile(
    *,
    reference_universe_id: str = (
        "reference_universe:test:1"
    ),
    universe_profile_label: str = "generic_11_sector",
    firm_count: int = 11,
    sector_count: int = 11,
    investor_count: int = 4,
    bank_count: int = 3,
    period_count: int = 12,
    sector_taxonomy_label: str = "generic_11_sector_reference",
    synthetic_only: bool = True,
    status: str = "active",
    visibility: str = "internal",
    metadata: dict | None = None,
) -> ReferenceUniverseProfile:
    return ReferenceUniverseProfile(
        reference_universe_id=reference_universe_id,
        universe_profile_label=universe_profile_label,
        firm_count=firm_count,
        sector_count=sector_count,
        investor_count=investor_count,
        bank_count=bank_count,
        period_count=period_count,
        sector_taxonomy_label=sector_taxonomy_label,
        synthetic_only=synthetic_only,
        status=status,
        visibility=visibility,
        metadata=metadata or {},
    )


def _sector(
    *,
    sector_id: str = "sector:reference:energy",
    sector_label: str = "energy_like",
    sector_group_label: str = "cyclical",
    demand_sensitivity_label: str = "high",
    rate_sensitivity_label: str = "moderate",
    credit_sensitivity_label: str = "moderate",
    input_cost_sensitivity_label: str = "high",
    policy_sensitivity_label: str = "high",
    technology_disruption_sensitivity_label: str = "low",
    status: str = "active",
    visibility: str = "internal",
    metadata: dict | None = None,
) -> GenericSectorReference:
    return GenericSectorReference(
        sector_id=sector_id,
        sector_label=sector_label,
        sector_group_label=sector_group_label,
        demand_sensitivity_label=demand_sensitivity_label,
        rate_sensitivity_label=rate_sensitivity_label,
        credit_sensitivity_label=credit_sensitivity_label,
        input_cost_sensitivity_label=input_cost_sensitivity_label,
        policy_sensitivity_label=policy_sensitivity_label,
        technology_disruption_sensitivity_label=(
            technology_disruption_sensitivity_label
        ),
        status=status,
        visibility=visibility,
        metadata=metadata or {},
    )


def _firm(
    *,
    firm_profile_id: str = "firm_profile:firm:reference_energy_a",
    firm_id: str = "firm:reference_energy_a",
    sector_id: str = "sector:reference:energy",
    sector_label: str = "energy_like",
    firm_size_label: str = "large",
    balance_sheet_style_label: str = "asset_heavy",
    funding_dependency_label: str = "high",
    demand_cyclicality_label: str = "highly_cyclical",
    input_cost_exposure_label: str = "high",
    rate_sensitivity_label: str = "moderate",
    credit_sensitivity_label: str = "moderate",
    market_access_sensitivity_label: str = "moderate",
    status: str = "active",
    visibility: str = "internal",
    metadata: dict | None = None,
) -> SyntheticSectorFirmProfile:
    return SyntheticSectorFirmProfile(
        firm_profile_id=firm_profile_id,
        firm_id=firm_id,
        sector_id=sector_id,
        sector_label=sector_label,
        firm_size_label=firm_size_label,
        balance_sheet_style_label=balance_sheet_style_label,
        funding_dependency_label=funding_dependency_label,
        demand_cyclicality_label=demand_cyclicality_label,
        input_cost_exposure_label=input_cost_exposure_label,
        rate_sensitivity_label=rate_sensitivity_label,
        credit_sensitivity_label=credit_sensitivity_label,
        market_access_sensitivity_label=(
            market_access_sensitivity_label
        ),
        status=status,
        visibility=visibility,
        metadata=metadata or {},
    )


def _bare_kernel() -> WorldKernel:
    return WorldKernel(
        registry=Registry(),
        clock=Clock(current_date=date(2026, 3, 31)),
        scheduler=Scheduler(),
        ledger=Ledger(),
        state=State(),
    )


# ---------------------------------------------------------------------------
# Field validation
# ---------------------------------------------------------------------------


def test_universe_profile_accepts_minimal_required_fields():
    p = _profile()
    assert p.reference_universe_id == "reference_universe:test:1"
    assert p.universe_profile_label == "generic_11_sector"
    assert p.synthetic_only is True
    assert p.status == "active"
    assert p.visibility == "internal"


def test_universe_profile_rejects_empty_id():
    with pytest.raises(ValueError):
        _profile(reference_universe_id="")


def test_universe_profile_rejects_unknown_universe_profile_label():
    with pytest.raises(ValueError):
        _profile(universe_profile_label="rogue_universe")


def test_universe_profile_rejects_unknown_sector_taxonomy_label():
    with pytest.raises(ValueError):
        _profile(sector_taxonomy_label="custom_taxonomy_v2")


def test_universe_profile_rejects_unknown_status():
    with pytest.raises(ValueError):
        _profile(status="committed_for_audit")


def test_universe_profile_rejects_unknown_visibility():
    with pytest.raises(ValueError):
        _profile(visibility="public_marketing")


def test_universe_profile_rejects_negative_period_count():
    with pytest.raises(ValueError):
        _profile(period_count=-1)


def test_universe_profile_rejects_bool_for_period_count():
    with pytest.raises(ValueError):
        _profile(period_count=True)  # type: ignore[arg-type]


def test_universe_profile_rejects_string_for_firm_count():
    with pytest.raises(ValueError):
        _profile(firm_count="11")  # type: ignore[arg-type]


def test_universe_profile_rejects_non_bool_synthetic_only():
    with pytest.raises(ValueError):
        _profile(synthetic_only="True")  # type: ignore[arg-type]


def test_universe_profile_rejects_metadata_with_forbidden_key():
    with pytest.raises(ValueError):
        _profile(metadata={"market_cap": 1.0})


def test_universe_profile_rejects_metadata_with_real_financial_value_key():
    with pytest.raises(ValueError):
        _profile(metadata={"real_financial_value": 1.0})


def test_sector_reference_accepts_minimal_required_fields():
    s = _sector()
    assert s.sector_label == "energy_like"
    assert s.sector_group_label == "cyclical"


def test_sector_reference_rejects_unknown_sector_label():
    with pytest.raises(ValueError):
        _sector(sector_label="cryptocurrency_like")


def test_sector_reference_rejects_unknown_sector_group_label():
    with pytest.raises(ValueError):
        _sector(sector_group_label="custom_group")


def test_sector_reference_rejects_unknown_sensitivity_label():
    with pytest.raises(ValueError):
        _sector(rate_sensitivity_label="extreme")


def test_sector_reference_rejects_metadata_with_real_company_name():
    with pytest.raises(ValueError):
        _sector(metadata={"real_company_name": "X"})


def test_firm_profile_accepts_minimal_required_fields():
    f = _firm()
    assert f.firm_id == "firm:reference_energy_a"
    assert f.sector_label == "energy_like"


def test_firm_profile_rejects_unknown_firm_size_label():
    with pytest.raises(ValueError):
        _firm(firm_size_label="huge")


def test_firm_profile_rejects_unknown_balance_sheet_style_label():
    with pytest.raises(ValueError):
        _firm(balance_sheet_style_label="custom_style")


def test_firm_profile_rejects_unknown_demand_cyclicality_label():
    with pytest.raises(ValueError):
        _firm(demand_cyclicality_label="random")


def test_firm_profile_rejects_metadata_with_revenue_key():
    with pytest.raises(ValueError):
        _firm(metadata={"revenue": 1.0})


def test_firm_profile_rejects_metadata_with_leverage_ratio_key():
    with pytest.raises(ValueError):
        _firm(metadata={"leverage_ratio": 0.5})


# ---------------------------------------------------------------------------
# Immutability + to_dict
# ---------------------------------------------------------------------------


def test_universe_profile_is_immutable():
    p = _profile()
    with pytest.raises(Exception):
        p.reference_universe_id = "x"  # type: ignore[misc]


def test_sector_reference_is_immutable():
    s = _sector()
    with pytest.raises(Exception):
        s.sector_id = "x"  # type: ignore[misc]


def test_firm_profile_is_immutable():
    f = _firm()
    with pytest.raises(Exception):
        f.firm_profile_id = "x"  # type: ignore[misc]


def test_to_dict_round_trip_byte_identical_for_each_class():
    a = _profile()
    b = _profile()
    assert a.to_dict() == b.to_dict()
    a = _sector()
    b = _sector()
    assert a.to_dict() == b.to_dict()
    a = _firm()
    b = _firm()
    assert a.to_dict() == b.to_dict()


def test_to_dict_keys_disjoint_from_forbidden_for_each_class():
    for to_dict in (
        _profile().to_dict(),
        _sector().to_dict(),
        _firm().to_dict(),
    ):
        assert not (
            set(to_dict.keys())
            & FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES
        )
        assert not (
            set(to_dict["metadata"].keys())
            & FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES
        )


# ---------------------------------------------------------------------------
# ReferenceUniverseBook — universe profile
# ---------------------------------------------------------------------------


def test_book_add_get_list_universe_profile():
    book = ReferenceUniverseBook()
    p = _profile()
    book.add_universe_profile(p)
    assert (
        book.get_universe_profile(p.reference_universe_id) is p
    )
    assert book.list_universe_profiles() == (p,)


def test_book_duplicate_universe_profile_raises():
    book = ReferenceUniverseBook()
    book.add_universe_profile(_profile())
    with pytest.raises(DuplicateReferenceUniverseProfileError):
        book.add_universe_profile(_profile())


def test_book_unknown_universe_profile_raises():
    book = ReferenceUniverseBook()
    with pytest.raises(UnknownReferenceUniverseProfileError):
        book.get_universe_profile("missing")


def test_book_list_universe_profiles_by_profile_label():
    book = ReferenceUniverseBook()
    a = _profile(
        reference_universe_id="reference_universe:tiny:1",
        universe_profile_label="tiny_default",
    )
    b = _profile(
        reference_universe_id="reference_universe:generic:1",
        universe_profile_label="generic_11_sector",
    )
    book.add_universe_profile(a)
    book.add_universe_profile(b)
    assert book.list_universe_profiles_by_profile_label(
        "tiny_default"
    ) == (a,)
    assert book.list_universe_profiles_by_profile_label(
        "generic_11_sector"
    ) == (b,)


# ---------------------------------------------------------------------------
# ReferenceUniverseBook — sector reference
# ---------------------------------------------------------------------------


def test_book_add_get_list_sector_reference():
    book = ReferenceUniverseBook()
    s = _sector()
    book.add_sector_reference(s)
    assert book.get_sector_reference(s.sector_id) is s
    assert book.list_sector_references() == (s,)


def test_book_duplicate_sector_reference_raises():
    book = ReferenceUniverseBook()
    book.add_sector_reference(_sector())
    with pytest.raises(DuplicateGenericSectorReferenceError):
        book.add_sector_reference(_sector())


def test_book_unknown_sector_reference_raises():
    book = ReferenceUniverseBook()
    with pytest.raises(UnknownGenericSectorReferenceError):
        book.get_sector_reference("missing")


def test_book_list_sectors_by_label():
    book = ReferenceUniverseBook()
    a = _sector(
        sector_id="sector:reference:energy",
        sector_label="energy_like",
    )
    b = _sector(
        sector_id="sector:reference:financials",
        sector_label="financials_like",
        sector_group_label="financial",
    )
    book.add_sector_reference(a)
    book.add_sector_reference(b)
    assert book.list_sectors_by_label("energy_like") == (a,)
    assert book.list_sectors_by_label("financials_like") == (b,)


def test_book_list_sectors_by_group():
    book = ReferenceUniverseBook()
    a = _sector(
        sector_id="sector:reference:energy",
        sector_label="energy_like",
        sector_group_label="cyclical",
    )
    b = _sector(
        sector_id="sector:reference:utilities",
        sector_label="utilities_like",
        sector_group_label="regulated_utility_like",
    )
    book.add_sector_reference(a)
    book.add_sector_reference(b)
    assert book.list_sectors_by_group("cyclical") == (a,)
    assert book.list_sectors_by_group(
        "regulated_utility_like"
    ) == (b,)


def test_book_list_sectors_by_sensitivity_returns_correct_subset():
    book = ReferenceUniverseBook()
    a = _sector(
        sector_id="sector:reference:financials",
        sector_label="financials_like",
        sector_group_label="financial",
        rate_sensitivity_label="high",
    )
    b = _sector(
        sector_id="sector:reference:staples",
        sector_label="consumer_staples_like",
        sector_group_label="defensive",
        rate_sensitivity_label="low",
    )
    book.add_sector_reference(a)
    book.add_sector_reference(b)
    high_rate = book.list_sectors_by_sensitivity(
        dimension="rate_sensitivity_label",
        sensitivity_label="high",
    )
    assert high_rate == (a,)


def test_book_list_sectors_by_sensitivity_rejects_unknown_dimension():
    book = ReferenceUniverseBook()
    with pytest.raises(ValueError):
        book.list_sectors_by_sensitivity(
            dimension="unknown_dimension",
            sensitivity_label="high",
        )


def test_book_list_sectors_by_sensitivity_rejects_unknown_label():
    book = ReferenceUniverseBook()
    with pytest.raises(ValueError):
        book.list_sectors_by_sensitivity(
            dimension="rate_sensitivity_label",
            sensitivity_label="extreme",
        )


# ---------------------------------------------------------------------------
# ReferenceUniverseBook — firm profile
# ---------------------------------------------------------------------------


def test_book_add_get_list_firm_profile():
    book = ReferenceUniverseBook()
    f = _firm()
    book.add_firm_profile(f)
    assert book.get_firm_profile(f.firm_profile_id) is f
    assert book.list_firm_profiles() == (f,)


def test_book_duplicate_firm_profile_raises():
    book = ReferenceUniverseBook()
    book.add_firm_profile(_firm())
    with pytest.raises(DuplicateSyntheticSectorFirmProfileError):
        book.add_firm_profile(_firm())


def test_book_unknown_firm_profile_raises():
    book = ReferenceUniverseBook()
    with pytest.raises(UnknownSyntheticSectorFirmProfileError):
        book.get_firm_profile("missing")


def test_book_list_firms_by_sector():
    book = ReferenceUniverseBook()
    a = _firm()
    b = _firm(
        firm_profile_id=(
            "firm_profile:firm:reference_financials_a"
        ),
        firm_id="firm:reference_financials_a",
        sector_id="sector:reference:financials",
        sector_label="financials_like",
    )
    book.add_firm_profile(a)
    book.add_firm_profile(b)
    assert book.list_firms_by_sector(
        "sector:reference:energy"
    ) == (a,)
    assert book.list_firms_by_sector(
        "sector:reference:financials"
    ) == (b,)


def test_book_list_firms_by_size():
    book = ReferenceUniverseBook()
    a = _firm(firm_size_label="large")
    b = _firm(
        firm_profile_id="firm_profile:firm:reference_health_a",
        firm_id="firm:reference_health_a",
        sector_id="sector:reference:health_care",
        sector_label="health_care_like",
        firm_size_label="mid",
    )
    book.add_firm_profile(a)
    book.add_firm_profile(b)
    assert book.list_firms_by_size("large") == (a,)
    assert book.list_firms_by_size("mid") == (b,)


def test_book_list_firms_by_funding_dependency():
    book = ReferenceUniverseBook()
    a = _firm(funding_dependency_label="high")
    b = _firm(
        firm_profile_id="firm_profile:firm:reference_staples_a",
        firm_id="firm:reference_staples_a",
        sector_id="sector:reference:staples",
        sector_label="consumer_staples_like",
        funding_dependency_label="low",
    )
    book.add_firm_profile(a)
    book.add_firm_profile(b)
    assert book.list_firms_by_funding_dependency("high") == (a,)
    assert book.list_firms_by_funding_dependency("low") == (b,)


def test_book_list_firms_by_market_access_sensitivity():
    book = ReferenceUniverseBook()
    a = _firm(market_access_sensitivity_label="moderate")
    b = _firm(
        firm_profile_id="firm_profile:firm:reference_realty_a",
        firm_id="firm:reference_realty_a",
        sector_id="sector:reference:real_estate",
        sector_label="real_estate_like",
        market_access_sensitivity_label="high",
    )
    book.add_firm_profile(a)
    book.add_firm_profile(b)
    assert book.list_firms_by_market_access_sensitivity(
        "moderate"
    ) == (a,)
    assert book.list_firms_by_market_access_sensitivity(
        "high"
    ) == (b,)


# ---------------------------------------------------------------------------
# Snapshot determinism
# ---------------------------------------------------------------------------


def test_book_snapshot_deterministic():
    book = ReferenceUniverseBook()
    book.add_universe_profile(_profile())
    book.add_sector_reference(_sector())
    book.add_firm_profile(_firm())
    snap_a = book.snapshot()
    snap_b = book.snapshot()
    assert snap_a == snap_b
    assert "reference_universe_profiles" in snap_a
    assert "generic_sector_references" in snap_a
    assert "synthetic_sector_firm_profiles" in snap_a
    assert len(snap_a["reference_universe_profiles"]) == 1
    assert len(snap_a["generic_sector_references"]) == 1
    assert len(snap_a["synthetic_sector_firm_profiles"]) == 1


# ---------------------------------------------------------------------------
# Ledger emission
# ---------------------------------------------------------------------------


def test_ledger_emits_one_record_per_add_universe_profile():
    kernel = _bare_kernel()
    before = len(kernel.ledger.records)
    kernel.reference_universe.add_universe_profile(_profile())
    after = len(kernel.ledger.records)
    assert after - before == 1
    record = kernel.ledger.records[-1]
    assert record.record_type == (
        RecordType.REFERENCE_UNIVERSE_PROFILE_RECORDED
    )


def test_ledger_emits_one_record_per_add_sector_reference():
    kernel = _bare_kernel()
    before = len(kernel.ledger.records)
    kernel.reference_universe.add_sector_reference(_sector())
    after = len(kernel.ledger.records)
    assert after - before == 1
    record = kernel.ledger.records[-1]
    assert record.record_type == (
        RecordType.GENERIC_SECTOR_REFERENCE_RECORDED
    )


def test_ledger_emits_one_record_per_add_firm_profile():
    kernel = _bare_kernel()
    before = len(kernel.ledger.records)
    kernel.reference_universe.add_firm_profile(_firm())
    after = len(kernel.ledger.records)
    assert after - before == 1
    record = kernel.ledger.records[-1]
    assert record.record_type == (
        RecordType.SYNTHETIC_SECTOR_FIRM_PROFILE_RECORDED
    )


def test_duplicate_universe_profile_emits_no_extra_ledger_record():
    kernel = _bare_kernel()
    kernel.reference_universe.add_universe_profile(_profile())
    count_after_first = len(kernel.ledger.records)
    with pytest.raises(DuplicateReferenceUniverseProfileError):
        kernel.reference_universe.add_universe_profile(_profile())
    assert len(kernel.ledger.records) == count_after_first


def test_duplicate_sector_reference_emits_no_extra_ledger_record():
    kernel = _bare_kernel()
    kernel.reference_universe.add_sector_reference(_sector())
    count_after_first = len(kernel.ledger.records)
    with pytest.raises(DuplicateGenericSectorReferenceError):
        kernel.reference_universe.add_sector_reference(_sector())
    assert len(kernel.ledger.records) == count_after_first


def test_duplicate_firm_profile_emits_no_extra_ledger_record():
    kernel = _bare_kernel()
    kernel.reference_universe.add_firm_profile(_firm())
    count_after_first = len(kernel.ledger.records)
    with pytest.raises(DuplicateSyntheticSectorFirmProfileError):
        kernel.reference_universe.add_firm_profile(_firm())
    assert len(kernel.ledger.records) == count_after_first


def test_ledger_payload_keys_disjoint_from_forbidden_for_each_kind():
    kernel = _bare_kernel()
    kernel.reference_universe.add_universe_profile(_profile())
    kernel.reference_universe.add_sector_reference(_sector())
    kernel.reference_universe.add_firm_profile(_firm())
    for record in kernel.ledger.records:
        assert not (
            set(record.payload.keys())
            & FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES
        )


# ---------------------------------------------------------------------------
# Kernel wiring
# ---------------------------------------------------------------------------


def test_kernel_wires_reference_universe_book():
    kernel = _bare_kernel()
    assert isinstance(
        kernel.reference_universe, ReferenceUniverseBook
    )
    assert kernel.reference_universe.ledger is kernel.ledger
    assert kernel.reference_universe.list_universe_profiles() == ()
    assert kernel.reference_universe.list_sector_references() == ()
    assert kernel.reference_universe.list_firm_profiles() == ()


# ---------------------------------------------------------------------------
# No-mutation / digest invariants
# ---------------------------------------------------------------------------


def test_add_universe_profile_does_not_mutate_pricebook():
    kernel = _bare_kernel()
    snap_before = kernel.prices.snapshot()
    kernel.reference_universe.add_universe_profile(_profile())
    snap_after = kernel.prices.snapshot()
    assert snap_before == snap_after


def test_add_sector_reference_does_not_mutate_pricebook():
    kernel = _bare_kernel()
    snap_before = kernel.prices.snapshot()
    kernel.reference_universe.add_sector_reference(_sector())
    snap_after = kernel.prices.snapshot()
    assert snap_before == snap_after


def test_add_firm_profile_does_not_mutate_pricebook():
    kernel = _bare_kernel()
    snap_before = kernel.prices.snapshot()
    kernel.reference_universe.add_firm_profile(_firm())
    snap_after = kernel.prices.snapshot()
    assert snap_before == snap_after


def test_empty_reference_universe_does_not_move_quarterly_default_digest():
    """Wiring an empty ReferenceUniverseBook into WorldKernel
    must leave the ``quarterly_default`` ``living_world_digest``
    byte-identical to v1.18.last / v1.19.last."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import _run_default, _seed_kernel

    k = _seed_kernel()
    r = _run_default(k)
    assert (
        living_world_digest(k, r)
        == "f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c"
    )


def test_empty_reference_universe_does_not_move_monthly_reference_digest():
    """Wiring an empty ReferenceUniverseBook into WorldKernel
    must leave the ``monthly_reference`` ``living_world_digest``
    byte-identical to v1.19.3."""
    from examples.reference_world.living_world_replay import (
        living_world_digest,
    )
    from test_living_reference_world import (
        _BANK_IDS,
        _FIRM_IDS,
        _INVESTOR_IDS,
        _seed_kernel,
    )
    from world.reference_living_world import (
        run_living_reference_world,
    )

    k = _seed_kernel()
    r = run_living_reference_world(
        k,
        firm_ids=_FIRM_IDS,
        investor_ids=_INVESTOR_IDS,
        bank_ids=_BANK_IDS,
        profile="monthly_reference",
    )
    assert (
        living_world_digest(k, r)
        == "75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d"
    )


def test_no_actor_decision_event_types_emitted_by_reference_universe_book():
    kernel = _bare_kernel()
    kernel.reference_universe.add_universe_profile(_profile())
    kernel.reference_universe.add_sector_reference(_sector())
    kernel.reference_universe.add_firm_profile(_firm())
    forbidden = {
        "order_submitted",
        "trade_executed",
        "price_updated",
        "quote_disseminated",
        "clearing_completed",
        "settlement_completed",
        "ownership_transferred",
        "loan_approved",
        "security_issued",
        "underwriting_executed",
        "investor_action_taken",
        "firm_decision_recorded",
        "bank_approval_recorded",
    }
    seen = {rec.record_type.value for rec in kernel.ledger.records}
    assert not (seen & forbidden)


# ---------------------------------------------------------------------------
# Default 11-sector fixture builder
# ---------------------------------------------------------------------------


def test_build_generic_11_sector_universe_returns_eleven_sectors_eleven_firms():
    fixture = build_generic_11_sector_reference_universe()
    assert isinstance(fixture, GenericReferenceUniverseFixture)
    assert len(fixture.sector_references) == 11
    assert len(fixture.firm_profiles) == 11
    assert (
        fixture.universe_profile.universe_profile_label
        == "generic_11_sector"
    )
    assert fixture.universe_profile.firm_count == 11
    assert fixture.universe_profile.sector_count == 11
    assert (
        fixture.universe_profile.sector_taxonomy_label
        == "generic_11_sector_reference"
    )


def test_build_generic_11_sector_universe_uses_only_like_sector_labels():
    fixture = build_generic_11_sector_reference_universe()
    for sector in fixture.sector_references:
        assert sector.sector_label.endswith("_like"), (
            f"sector label {sector.sector_label!r} must carry "
            "the `_like` suffix"
        )
    for firm in fixture.firm_profiles:
        assert firm.sector_label.endswith("_like"), (
            f"firm sector label {firm.sector_label!r} must carry "
            "the `_like` suffix"
        )


def test_build_generic_11_sector_universe_uses_no_real_company_names():
    """All firm ids are jurisdiction-neutral plain ids of the
    form ``firm:reference_<sector>_a``. No real company name
    appears in the firm id, sector id, or any payload."""
    fixture = build_generic_11_sector_reference_universe()
    for firm in fixture.firm_profiles:
        firm_text = (
            firm.firm_id + " " + firm.firm_profile_id + " "
            + firm.sector_id
        ).lower()
        for token in _REAL_COMPANY_TOKENS:
            pattern = rf"\b{re.escape(token)}\b"
            assert re.search(pattern, firm_text) is None, (
                f"forbidden token {token!r} in firm record "
                f"{firm.firm_id!r}"
            )


_LICENSED_TAXONOMY_PROBE_TOKENS = (
    "gics",
    "msci",
    "sp_index",
    "topix",
    "nikkei",
    "jpx",
    "factset",
    "bloomberg",
    "refinitiv",
)


def test_build_generic_11_sector_universe_uses_no_licensed_taxonomy_dependency():
    fixture = build_generic_11_sector_reference_universe()
    licensed_tokens = _LICENSED_TAXONOMY_PROBE_TOKENS
    for sector in fixture.sector_references:
        sector_text = (
            sector.sector_id + " " + sector.sector_label + " "
            + sector.sector_group_label
        ).lower()
        for token in licensed_tokens:
            pattern = rf"\b{re.escape(token)}\b"
            assert re.search(pattern, sector_text) is None, (
                f"licensed-taxonomy token {token!r} in sector "
                f"record {sector.sector_id!r}"
            )


def test_build_generic_11_sector_universe_does_not_auto_register():
    """The builder is pure — it does not write to the kernel's
    book. The caller must explicitly invoke
    :func:`register_generic_11_sector_reference_universe` to
    store the fixture."""
    kernel = _bare_kernel()
    fixture = build_generic_11_sector_reference_universe()
    assert fixture is not None
    # The kernel's book remains empty.
    assert (
        kernel.reference_universe.list_universe_profiles() == ()
    )
    assert (
        kernel.reference_universe.list_sector_references() == ()
    )
    assert kernel.reference_universe.list_firm_profiles() == ()
    # No ledger records emitted by the pure builder.
    assert len(kernel.ledger.records) == 0


def test_build_generic_11_sector_universe_deterministic():
    a = build_generic_11_sector_reference_universe()
    b = build_generic_11_sector_reference_universe()
    assert a.universe_profile.to_dict() == (
        b.universe_profile.to_dict()
    )
    assert tuple(s.to_dict() for s in a.sector_references) == (
        tuple(s.to_dict() for s in b.sector_references)
    )
    assert tuple(f.to_dict() for f in a.firm_profiles) == (
        tuple(f.to_dict() for f in b.firm_profiles)
    )


def test_default_sector_label_order_pinned():
    assert default_sector_label_order() == (
        "energy_like",
        "materials_like",
        "industrials_like",
        "consumer_discretionary_like",
        "consumer_staples_like",
        "health_care_like",
        "financials_like",
        "information_technology_like",
        "communication_services_like",
        "utilities_like",
        "real_estate_like",
    )


def test_default_firm_id_order_pinned():
    firms = default_firm_id_order()
    assert len(firms) == 11
    for firm in firms:
        assert firm.startswith("firm:reference_"), firm
        assert firm.endswith("_a"), firm


# ---------------------------------------------------------------------------
# Explicit registration helper
# ---------------------------------------------------------------------------


def test_register_generic_11_sector_universe_writes_to_kernel():
    kernel = _bare_kernel()
    fixture = register_generic_11_sector_reference_universe(
        kernel.reference_universe
    )
    assert isinstance(fixture, GenericReferenceUniverseFixture)
    assert (
        len(kernel.reference_universe.list_universe_profiles())
        == 1
    )
    assert (
        len(kernel.reference_universe.list_sector_references())
        == 11
    )
    assert (
        len(kernel.reference_universe.list_firm_profiles()) == 11
    )
    # Ledger emits exactly 1 + 11 + 11 = 23 records.
    seen_event_types = {
        rec.record_type for rec in kernel.ledger.records
    }
    assert (
        RecordType.REFERENCE_UNIVERSE_PROFILE_RECORDED
        in seen_event_types
    )
    assert (
        RecordType.GENERIC_SECTOR_REFERENCE_RECORDED
        in seen_event_types
    )
    assert (
        RecordType.SYNTHETIC_SECTOR_FIRM_PROFILE_RECORDED
        in seen_event_types
    )


def test_register_generic_11_sector_universe_idempotent_or_raises_on_repeat():
    """Calling :func:`register_generic_11_sector_reference_universe`
    twice on the same book raises a ``Duplicate*Error`` because
    the fixture id pattern is deterministic. v1.20.1 does not
    silently dedupe — the caller must pick one fresh book per
    registration."""
    kernel = _bare_kernel()
    register_generic_11_sector_reference_universe(
        kernel.reference_universe
    )
    with pytest.raises(DuplicateReferenceUniverseProfileError):
        register_generic_11_sector_reference_universe(
            kernel.reference_universe
        )


# ---------------------------------------------------------------------------
# Forbidden-name + jurisdiction-neutral scans
# ---------------------------------------------------------------------------


_FORBIDDEN_TOKENS = (
    "toyota",
    "mufg",
    "smbc",
    "mizuho",
    "boj",
    "fsa",
    "jpx",
    "gpif",
    "tse",
    "nikkei",
    "topix",
    "sony",
    "jgb",
    "nyse",
    "nasdaq",
)


_LICENSED_TAXONOMY_TOKENS = (
    "gics",
    "msci",
    "factset",
    "bloomberg",
    "refinitiv",
)


# Real-company / real-issuer token list referenced by
# ``test_build_generic_11_sector_universe_uses_no_real_company_names``.
# Kept at module level so the test-file jurisdiction-neutral scan
# can strip the literal block before searching.
_REAL_COMPANY_TOKENS = (
    "toyota",
    "sony",
    "mufg",
    "smbc",
    "mizuho",
    "boj",
    "fsa",
    "jpx",
    "gpif",
    "tse",
    "nikkei",
    "topix",
    "jgb",
    "nyse",
    "nasdaq",
    "apple",
    "microsoft",
    "google",
    "amazon",
    "tesla",
)


def _strip_module_docstring(text: str) -> str:
    """Remove the module-level triple-quoted docstring from
    ``text`` so token scans do not match documentation
    references that legitimately mention forbidden tokens
    inside backticks."""
    lo = text.find('"""')
    if lo < 0:
        return text
    hi = text.find('"""', lo + 3)
    if hi < 0:
        return text
    return text[: lo] + text[hi + 3 :]


def _strip_forbidden_literal(text: str) -> str:
    """Strip the ``FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES``
    frozenset literal block (case-insensitive)."""
    lower = text.lower()
    open_idx = lower.find("forbidden_reference_universe_field_names")
    if open_idx < 0:
        return text
    close_idx = text.find(")", open_idx)
    if close_idx <= open_idx:
        return text
    return text[: open_idx] + text[close_idx:]


def test_module_jurisdiction_neutral_scan():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    text = _strip_module_docstring(text)
    text = _strip_forbidden_literal(text).lower()
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            "reference_universe.py outside the docstring + "
            "FORBIDDEN literal"
        )


def test_module_no_licensed_taxonomy_dependency_scan():
    text = _MODULE_PATH.read_text(encoding="utf-8")
    text = _strip_module_docstring(text)
    text = _strip_forbidden_literal(text).lower()
    for token in _LICENSED_TAXONOMY_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"licensed-taxonomy token {token!r} appears in "
            "reference_universe.py outside the docstring + "
            "FORBIDDEN literal"
        )


def test_test_file_jurisdiction_neutral_scan():
    text = Path(__file__).read_text(encoding="utf-8").lower()
    # Strip the local token-table tuple bodies before
    # scanning the rest of the file.
    for marker in (
        "_forbidden_tokens = (",
        "_licensed_taxonomy_tokens = (",
        "_real_company_tokens = (",
        "_v1_20_0_pinned_forbidden_names = (",
        "_licensed_taxonomy_probe_tokens = (",
    ):
        idx = text.find(marker)
        if idx != -1:
            close = text.find(")", idx) + 1
            if close > 0:
                text = text[:idx] + text[close:]
    for token in _FORBIDDEN_TOKENS:
        pattern = rf"\b{re.escape(token)}\b"
        assert re.search(pattern, text) is None, (
            f"forbidden token {token!r} appears in "
            "test_reference_universe.py outside the token tables"
        )


def test_module_text_does_not_carry_forbidden_phrases():
    """The module imports nothing from the forbidden list and
    does not declare any forbidden field name as a bare
    identifier. The :data:`FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES`
    frozenset itself contains the forbidden literals; strip
    the docstring + that block before scanning."""
    text = _MODULE_PATH.read_text(encoding="utf-8")
    text = _strip_module_docstring(text)
    text = _strip_forbidden_literal(text)
    for phrase in (
        "real_company_name",
        "real_sector_weight",
        "market_cap",
        "leverage_ratio",
        "real_financial_value",
        "japan_calibration",
        "llm_output",
        "llm_prose",
        "prompt_text",
        "investment_advice",
        "target_price",
        "expected_return",
        "forecast_path",
        "predicted_index",
    ):
        assert phrase not in text, (
            f"forbidden phrase {phrase!r} appears in "
            "reference_universe.py outside the docstring + "
            "FORBIDDEN literal"
        )
