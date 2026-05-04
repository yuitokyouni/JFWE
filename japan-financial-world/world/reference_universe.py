"""
v1.20.1 — Reference universe storage.

Storage-only foundation for the v1.20 monthly scenario
reference universe. v1.20.1 ships three immutable frozen
dataclasses (:class:`ReferenceUniverseProfile`,
:class:`GenericSectorReference`,
:class:`SyntheticSectorFirmProfile`), one append-only
:class:`ReferenceUniverseBook`, twelve closed-set
vocabularies, and one deterministic helper
(:func:`build_generic_11_sector_reference_universe`) that
constructs the v1.20.0 default universe (11 generic sectors +
11 representative firm profiles) **without** registering
anything on a kernel.

Critical design constraints carried verbatim from v1.20.0
(binding):

- The universe is **synthetic / generic / jurisdiction-
  neutral** — no real company names, no real sector index
  membership, no licensed taxonomy dependency. Every sector
  label carries the ``_like`` suffix; every firm id follows
  the ``firm:reference_<sector>_a`` pattern.
- Storage only. v1.20.1 does **not** ship the
  ``scenario_monthly_reference_universe`` run profile (that
  lands at v1.20.3). It does **not** ship the scenario
  schedule (v1.20.2). It does **not** mutate the
  ``PriceBook`` or any other source-of-truth book. It does
  **not** decide actor behavior.
- Empty by default on the kernel. The new
  :class:`WorldKernel.reference_universe` field is wired
  with ``field(default_factory=ReferenceUniverseBook)``;
  empty book → no ledger emission → byte-identical
  ``quarterly_default`` (`f93bdf3f…b705897c`) and
  ``monthly_reference`` (`75a91cfa…91879d`) digests.
- The future-LLM-compatibility audit shape pinned at
  v1.18.0 carries forward — ``reasoning_mode = "rule_based_fallback"``
  remains binding at v1.20.x; future LLM-mode reasoning
  policies can replace the rule table without changing the
  audit surface. v1.20.1 is storage-only and does not yet
  consume the audit shape, but the
  :data:`FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES`
  frozenset extends the v1.18.0 forbidden list with the
  v1.20.0-pinned licensed-taxonomy / real-data tokens
  (``gics`` / ``msci`` / ``topix`` / ``nikkei`` / ``jpx`` /
  ``real_company_name`` / ``market_cap`` / ``leverage_ratio``
  / etc.).

The module is **runtime-book-free** beyond the v0/v1 ledger +
clock convention shared by every other storage book — it does
not import any source-of-truth book on the engine side.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Mapping

from world.clock import Clock
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Closed-set vocabularies
# ---------------------------------------------------------------------------


UNIVERSE_PROFILE_LABELS: frozenset[str] = frozenset(
    {
        "tiny_default",
        "generic_11_sector",
        "generic_broad_market",
        "custom_synthetic",
        "unknown",
    }
)


SECTOR_TAXONOMY_LABELS: frozenset[str] = frozenset(
    {
        "generic_11_sector_reference",
        "generic_macro_sector_reference",
        "custom_synthetic",
        "unknown",
    }
)


SECTOR_LABELS: frozenset[str] = frozenset(
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


SECTOR_GROUP_LABELS: frozenset[str] = frozenset(
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


SENSITIVITY_LABELS: frozenset[str] = frozenset(
    {
        "low",
        "moderate",
        "high",
        "unknown",
    }
)


FIRM_SIZE_LABELS: frozenset[str] = frozenset(
    {
        "small",
        "mid",
        "large",
        "mega_like",
        "unknown",
    }
)


BALANCE_SHEET_STYLE_LABELS: frozenset[str] = frozenset(
    {
        "asset_light",
        "asset_heavy",
        "working_capital_intensive",
        "regulated_asset_base_like",
        "financial_balance_sheet",
        "unknown",
    }
)


FUNDING_DEPENDENCY_LABELS: frozenset[str] = frozenset(
    {
        "low",
        "moderate",
        "high",
        "unknown",
    }
)


DEMAND_CYCLICALITY_LABELS: frozenset[str] = frozenset(
    {
        "defensive",
        "moderate",
        "cyclical",
        "highly_cyclical",
        "unknown",
    }
)


INPUT_COST_EXPOSURE_LABELS: frozenset[str] = frozenset(
    {
        "low",
        "moderate",
        "high",
        "unknown",
    }
)


STATUS_LABELS: frozenset[str] = frozenset(
    {
        "draft",
        "active",
        "stale",
        "superseded",
        "archived",
        "unknown",
    }
)


VISIBILITY_LABELS: frozenset[str] = frozenset(
    {
        "public",
        "restricted",
        "internal",
        "private",
        "unknown",
    }
)


# v1.20.0 hard naming boundary on payload + metadata. Tests
# scan dataclass field names, payload keys, and metadata keys
# for any of the forbidden names below. The set composes the
# v1.18.0 actor-decision tokens, the v1.17.0 forbidden display
# names, the v1.19.3 Japan-real-data tokens, and the v1.20.0-
# pinned licensed-taxonomy / real-financial-value tokens. A
# `_like`-suffixed label such as ``regulated_utility_like`` is
# not in the forbidden set — only the bare licensed-taxonomy
# tokens are.
FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES: frozenset[str] = frozenset(
    {
        # v1.18.0 actor-decision / canonical-judgment tokens
        "firm_decision",
        "investor_action",
        "bank_approval",
        "trading_decision",
        "optimal_capital_structure",
        "buy",
        "sell",
        "order",
        "trade",
        "execution",
        # price / forecast / advice
        "price",
        "market_price",
        "predicted_index",
        "forecast_path",
        "expected_return",
        "target_price",
        "recommendation",
        "investment_advice",
        # real-data / Japan / LLM
        "real_data_value",
        "japan_calibration",
        "llm_output",
        "llm_prose",
        "prompt_text",
        # v1.20.0 real-issuer / real-financial / licensed-taxonomy
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
    }
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ReferenceUniverseError(Exception):
    """Base class for v1.20.1 reference-universe storage errors."""


class DuplicateReferenceUniverseProfileError(ReferenceUniverseError):
    """Raised when a reference_universe_id is added twice."""


class DuplicateGenericSectorReferenceError(ReferenceUniverseError):
    """Raised when a sector_id is added twice."""


class DuplicateSyntheticSectorFirmProfileError(ReferenceUniverseError):
    """Raised when a firm_profile_id is added twice."""


class UnknownReferenceUniverseProfileError(
    ReferenceUniverseError, KeyError
):
    """Raised when a reference_universe_id is not found."""


class UnknownGenericSectorReferenceError(
    ReferenceUniverseError, KeyError
):
    """Raised when a sector_id is not found."""


class UnknownSyntheticSectorFirmProfileError(
    ReferenceUniverseError, KeyError
):
    """Raised when a firm_profile_id is not found."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_label(
    value: Any, allowed: frozenset[str], *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    if value not in allowed:
        raise ValueError(
            f"{field_name} must be one of {sorted(allowed)!r}; "
            f"got {value!r}"
        )
    return value


def _validate_required_string(
    value: Any, *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _validate_non_negative_int(
    value: Any, *, field_name: str
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"{field_name} must be a non-negative int; "
            f"got {type(value).__name__}"
        )
    if value < 0:
        raise ValueError(
            f"{field_name} must be a non-negative int; got {value}"
        )
    return value


def _validate_bool(value: Any, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a bool; got {type(value).__name__}"
        )
    return value


def _scan_for_forbidden_keys(
    mapping: Mapping[str, Any], *, field_name: str
) -> None:
    """Reject any v1.20.0 forbidden field name appearing in a
    metadata or payload mapping."""
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if key in FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key {key!r} "
                "(v1.20.0 hard naming boundary — reference "
                "universe records do not carry actor-decision / "
                "price / forecast / advice / real-data / "
                "Japan-calibration / LLM / real-issuer / "
                "real-financial-value / licensed-taxonomy fields)"
            )


# ---------------------------------------------------------------------------
# ReferenceUniverseProfile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferenceUniverseProfile:
    """Immutable profile naming a synthetic universe shape.
    v1.20.1 is storage-only; v1.20.3 will project the profile
    onto a fresh kernel via the new
    ``scenario_monthly_reference_universe`` run profile.

    The dataclass:

    - has **no** real-taxonomy field — ``sector_taxonomy_label``
      names a *jurisdiction-neutral / vendor-neutral* category;
    - has **no** market-cap / financial-statement field;
    - has **no** actor-decision field;
    - is jurisdiction-neutral by construction.
    """

    reference_universe_id: str
    universe_profile_label: str
    firm_count: int
    sector_count: int
    investor_count: int
    bank_count: int
    period_count: int
    sector_taxonomy_label: str
    synthetic_only: bool = True
    status: str = "active"
    visibility: str = "internal"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "reference_universe_id",
        "universe_profile_label",
        "sector_taxonomy_label",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("universe_profile_label", UNIVERSE_PROFILE_LABELS),
        ("sector_taxonomy_label",  SECTOR_TAXONOMY_LABELS),
        ("status",                 STATUS_LABELS),
        ("visibility",             VISIBILITY_LABELS),
    )

    INT_FIELDS: ClassVar[tuple[str, ...]] = (
        "firm_count",
        "sector_count",
        "investor_count",
        "bank_count",
        "period_count",
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} is in the v1.20.0 "
                    "forbidden field-name set"
                )
        for name in self.REQUIRED_STRING_FIELDS:
            _validate_required_string(
                getattr(self, name), field_name=name
            )
        for name, allowed in self.LABEL_FIELDS:
            _validate_label(
                getattr(self, name), allowed, field_name=name
            )
        for name in self.INT_FIELDS:
            object.__setattr__(
                self,
                name,
                _validate_non_negative_int(
                    getattr(self, name), field_name=name
                ),
            )
        object.__setattr__(
            self,
            "synthetic_only",
            _validate_bool(self.synthetic_only, field_name="synthetic_only"),
        )
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(metadata_dict, field_name="metadata")
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_universe_id": self.reference_universe_id,
            "universe_profile_label": self.universe_profile_label,
            "firm_count": self.firm_count,
            "sector_count": self.sector_count,
            "investor_count": self.investor_count,
            "bank_count": self.bank_count,
            "period_count": self.period_count,
            "sector_taxonomy_label": self.sector_taxonomy_label,
            "synthetic_only": self.synthetic_only,
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# GenericSectorReference
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GenericSectorReference:
    """Immutable record naming one generic synthetic sector.

    Every label carries the ``_like`` suffix to make the
    non-real-membership discipline visible. The six sensitivity
    dimensions use a shared three-rung closed set
    (``low`` / ``moderate`` / ``high`` / ``unknown``).
    """

    sector_id: str
    sector_label: str
    sector_group_label: str
    demand_sensitivity_label: str
    rate_sensitivity_label: str
    credit_sensitivity_label: str
    input_cost_sensitivity_label: str
    policy_sensitivity_label: str
    technology_disruption_sensitivity_label: str
    status: str = "active"
    visibility: str = "internal"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "sector_id",
        "sector_label",
        "sector_group_label",
        "demand_sensitivity_label",
        "rate_sensitivity_label",
        "credit_sensitivity_label",
        "input_cost_sensitivity_label",
        "policy_sensitivity_label",
        "technology_disruption_sensitivity_label",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("sector_label",                              SECTOR_LABELS),
        ("sector_group_label",                        SECTOR_GROUP_LABELS),
        ("demand_sensitivity_label",                  SENSITIVITY_LABELS),
        ("rate_sensitivity_label",                    SENSITIVITY_LABELS),
        ("credit_sensitivity_label",                  SENSITIVITY_LABELS),
        ("input_cost_sensitivity_label",              SENSITIVITY_LABELS),
        ("policy_sensitivity_label",                  SENSITIVITY_LABELS),
        ("technology_disruption_sensitivity_label",   SENSITIVITY_LABELS),
        ("status",                                    STATUS_LABELS),
        ("visibility",                                VISIBILITY_LABELS),
    )

    SENSITIVITY_FIELDS: ClassVar[tuple[str, ...]] = (
        "demand_sensitivity_label",
        "rate_sensitivity_label",
        "credit_sensitivity_label",
        "input_cost_sensitivity_label",
        "policy_sensitivity_label",
        "technology_disruption_sensitivity_label",
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} is in the v1.20.0 "
                    "forbidden field-name set"
                )
        for name in self.REQUIRED_STRING_FIELDS:
            _validate_required_string(
                getattr(self, name), field_name=name
            )
        for name, allowed in self.LABEL_FIELDS:
            _validate_label(
                getattr(self, name), allowed, field_name=name
            )
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(metadata_dict, field_name="metadata")
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sector_id": self.sector_id,
            "sector_label": self.sector_label,
            "sector_group_label": self.sector_group_label,
            "demand_sensitivity_label": self.demand_sensitivity_label,
            "rate_sensitivity_label": self.rate_sensitivity_label,
            "credit_sensitivity_label": self.credit_sensitivity_label,
            "input_cost_sensitivity_label": (
                self.input_cost_sensitivity_label
            ),
            "policy_sensitivity_label": self.policy_sensitivity_label,
            "technology_disruption_sensitivity_label": (
                self.technology_disruption_sensitivity_label
            ),
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# SyntheticSectorFirmProfile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticSectorFirmProfile:
    """Immutable profile naming one synthetic representative
    firm. v1.20.1 ships one firm profile per sector in the
    default fixture (11 firms × 11 sectors)."""

    firm_profile_id: str
    firm_id: str
    sector_id: str
    sector_label: str
    firm_size_label: str
    balance_sheet_style_label: str
    funding_dependency_label: str
    demand_cyclicality_label: str
    input_cost_exposure_label: str
    rate_sensitivity_label: str
    credit_sensitivity_label: str
    market_access_sensitivity_label: str
    status: str = "active"
    visibility: str = "internal"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "firm_profile_id",
        "firm_id",
        "sector_id",
        "sector_label",
        "firm_size_label",
        "balance_sheet_style_label",
        "funding_dependency_label",
        "demand_cyclicality_label",
        "input_cost_exposure_label",
        "rate_sensitivity_label",
        "credit_sensitivity_label",
        "market_access_sensitivity_label",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("sector_label",                       SECTOR_LABELS),
        ("firm_size_label",                    FIRM_SIZE_LABELS),
        ("balance_sheet_style_label",          BALANCE_SHEET_STYLE_LABELS),
        ("funding_dependency_label",           FUNDING_DEPENDENCY_LABELS),
        ("demand_cyclicality_label",           DEMAND_CYCLICALITY_LABELS),
        ("input_cost_exposure_label",          INPUT_COST_EXPOSURE_LABELS),
        ("rate_sensitivity_label",             SENSITIVITY_LABELS),
        ("credit_sensitivity_label",           SENSITIVITY_LABELS),
        ("market_access_sensitivity_label",    SENSITIVITY_LABELS),
        ("status",                             STATUS_LABELS),
        ("visibility",                         VISIBILITY_LABELS),
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} is in the v1.20.0 "
                    "forbidden field-name set"
                )
        for name in self.REQUIRED_STRING_FIELDS:
            _validate_required_string(
                getattr(self, name), field_name=name
            )
        for name, allowed in self.LABEL_FIELDS:
            _validate_label(
                getattr(self, name), allowed, field_name=name
            )
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(metadata_dict, field_name="metadata")
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "firm_profile_id": self.firm_profile_id,
            "firm_id": self.firm_id,
            "sector_id": self.sector_id,
            "sector_label": self.sector_label,
            "firm_size_label": self.firm_size_label,
            "balance_sheet_style_label": self.balance_sheet_style_label,
            "funding_dependency_label": self.funding_dependency_label,
            "demand_cyclicality_label": self.demand_cyclicality_label,
            "input_cost_exposure_label": (
                self.input_cost_exposure_label
            ),
            "rate_sensitivity_label": self.rate_sensitivity_label,
            "credit_sensitivity_label": self.credit_sensitivity_label,
            "market_access_sensitivity_label": (
                self.market_access_sensitivity_label
            ),
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# ReferenceUniverseBook
# ---------------------------------------------------------------------------


@dataclass
class ReferenceUniverseBook:
    """Append-only storage for v1.20.1 reference-universe
    records.

    Mirrors the v1.18.1 / v1.19.3 storage-book convention:
    emits exactly one ledger record per ``add_*`` call, no
    extra ledger record on duplicate id, mutates no other
    source-of-truth book. Empty by default on the kernel —
    pinned by ``test_empty_reference_universe_does_not_move_*``
    trip-wire tests at v1.20.1.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _universe_profiles: dict[
        str, ReferenceUniverseProfile
    ] = field(default_factory=dict)
    _sector_references: dict[
        str, GenericSectorReference
    ] = field(default_factory=dict)
    _firm_profiles: dict[
        str, SyntheticSectorFirmProfile
    ] = field(default_factory=dict)

    def _now(self) -> datetime:
        if self.clock is not None:
            try:
                return self.clock.current_datetime()
            except Exception:
                pass
        return datetime.now(timezone.utc)

    # -- universe profile -------------------------------------------

    def add_universe_profile(
        self,
        profile: ReferenceUniverseProfile,
        *,
        simulation_date: Any = None,
    ) -> ReferenceUniverseProfile:
        if profile.reference_universe_id in self._universe_profiles:
            raise DuplicateReferenceUniverseProfileError(
                "Duplicate reference_universe_id: "
                f"{profile.reference_universe_id}"
            )
        self._universe_profiles[
            profile.reference_universe_id
        ] = profile

        if self.ledger is not None:
            payload = {
                "reference_universe_id": profile.reference_universe_id,
                "universe_profile_label": profile.universe_profile_label,
                "firm_count": profile.firm_count,
                "sector_count": profile.sector_count,
                "investor_count": profile.investor_count,
                "bank_count": profile.bank_count,
                "period_count": profile.period_count,
                "sector_taxonomy_label": profile.sector_taxonomy_label,
                "synthetic_only": profile.synthetic_only,
                "status": profile.status,
                "visibility": profile.visibility,
            }
            _scan_for_forbidden_keys(
                payload, field_name="ledger payload"
            )
            sim_date: Any = (
                simulation_date
                if simulation_date is not None
                else self._now()
            )
            self.ledger.append(
                event_type="reference_universe_profile_recorded",
                simulation_date=sim_date,
                object_id=profile.reference_universe_id,
                source=profile.universe_profile_label,
                payload=payload,
                space_id="reference_universe",
                visibility=profile.visibility,
            )
        return profile

    def get_universe_profile(
        self, reference_universe_id: str
    ) -> ReferenceUniverseProfile:
        try:
            return self._universe_profiles[reference_universe_id]
        except KeyError as exc:
            raise UnknownReferenceUniverseProfileError(
                "reference_universe_profile not found: "
                f"{reference_universe_id!r}"
            ) from exc

    def list_universe_profiles(
        self,
    ) -> tuple[ReferenceUniverseProfile, ...]:
        return tuple(self._universe_profiles.values())

    def list_universe_profiles_by_profile_label(
        self, universe_profile_label: str
    ) -> tuple[ReferenceUniverseProfile, ...]:
        return tuple(
            p
            for p in self._universe_profiles.values()
            if p.universe_profile_label == universe_profile_label
        )

    # -- sector reference -------------------------------------------

    def add_sector_reference(
        self,
        sector: GenericSectorReference,
        *,
        simulation_date: Any = None,
    ) -> GenericSectorReference:
        if sector.sector_id in self._sector_references:
            raise DuplicateGenericSectorReferenceError(
                "Duplicate sector_id: " f"{sector.sector_id}"
            )
        self._sector_references[sector.sector_id] = sector

        if self.ledger is not None:
            payload = {
                "sector_id": sector.sector_id,
                "sector_label": sector.sector_label,
                "sector_group_label": sector.sector_group_label,
                "demand_sensitivity_label": (
                    sector.demand_sensitivity_label
                ),
                "rate_sensitivity_label": sector.rate_sensitivity_label,
                "credit_sensitivity_label": (
                    sector.credit_sensitivity_label
                ),
                "input_cost_sensitivity_label": (
                    sector.input_cost_sensitivity_label
                ),
                "policy_sensitivity_label": (
                    sector.policy_sensitivity_label
                ),
                "technology_disruption_sensitivity_label": (
                    sector.technology_disruption_sensitivity_label
                ),
                "status": sector.status,
                "visibility": sector.visibility,
            }
            _scan_for_forbidden_keys(
                payload, field_name="ledger payload"
            )
            sim_date: Any = (
                simulation_date
                if simulation_date is not None
                else self._now()
            )
            self.ledger.append(
                event_type="generic_sector_reference_recorded",
                simulation_date=sim_date,
                object_id=sector.sector_id,
                source=sector.sector_label,
                payload=payload,
                space_id="reference_universe",
                visibility=sector.visibility,
            )
        return sector

    def get_sector_reference(
        self, sector_id: str
    ) -> GenericSectorReference:
        try:
            return self._sector_references[sector_id]
        except KeyError as exc:
            raise UnknownGenericSectorReferenceError(
                "sector_reference not found: " f"{sector_id!r}"
            ) from exc

    def list_sector_references(
        self,
    ) -> tuple[GenericSectorReference, ...]:
        return tuple(self._sector_references.values())

    def list_sectors_by_label(
        self, sector_label: str
    ) -> tuple[GenericSectorReference, ...]:
        return tuple(
            s
            for s in self._sector_references.values()
            if s.sector_label == sector_label
        )

    def list_sectors_by_group(
        self, sector_group_label: str
    ) -> tuple[GenericSectorReference, ...]:
        return tuple(
            s
            for s in self._sector_references.values()
            if s.sector_group_label == sector_group_label
        )

    def list_sectors_by_sensitivity(
        self,
        *,
        dimension: str,
        sensitivity_label: str,
    ) -> tuple[GenericSectorReference, ...]:
        if dimension not in GenericSectorReference.SENSITIVITY_FIELDS:
            raise ValueError(
                f"dimension must be one of "
                f"{sorted(GenericSectorReference.SENSITIVITY_FIELDS)!r}; "
                f"got {dimension!r}"
            )
        if sensitivity_label not in SENSITIVITY_LABELS:
            raise ValueError(
                f"sensitivity_label must be one of "
                f"{sorted(SENSITIVITY_LABELS)!r}; "
                f"got {sensitivity_label!r}"
            )
        return tuple(
            s
            for s in self._sector_references.values()
            if getattr(s, dimension) == sensitivity_label
        )

    # -- firm profile -----------------------------------------------

    def add_firm_profile(
        self,
        firm: SyntheticSectorFirmProfile,
        *,
        simulation_date: Any = None,
    ) -> SyntheticSectorFirmProfile:
        if firm.firm_profile_id in self._firm_profiles:
            raise DuplicateSyntheticSectorFirmProfileError(
                "Duplicate firm_profile_id: "
                f"{firm.firm_profile_id}"
            )
        self._firm_profiles[firm.firm_profile_id] = firm

        if self.ledger is not None:
            payload = {
                "firm_profile_id": firm.firm_profile_id,
                "firm_id": firm.firm_id,
                "sector_id": firm.sector_id,
                "sector_label": firm.sector_label,
                "firm_size_label": firm.firm_size_label,
                "balance_sheet_style_label": (
                    firm.balance_sheet_style_label
                ),
                "funding_dependency_label": (
                    firm.funding_dependency_label
                ),
                "demand_cyclicality_label": (
                    firm.demand_cyclicality_label
                ),
                "input_cost_exposure_label": (
                    firm.input_cost_exposure_label
                ),
                "rate_sensitivity_label": firm.rate_sensitivity_label,
                "credit_sensitivity_label": (
                    firm.credit_sensitivity_label
                ),
                "market_access_sensitivity_label": (
                    firm.market_access_sensitivity_label
                ),
                "status": firm.status,
                "visibility": firm.visibility,
            }
            _scan_for_forbidden_keys(
                payload, field_name="ledger payload"
            )
            sim_date: Any = (
                simulation_date
                if simulation_date is not None
                else self._now()
            )
            self.ledger.append(
                event_type="synthetic_sector_firm_profile_recorded",
                simulation_date=sim_date,
                object_id=firm.firm_profile_id,
                source=firm.sector_label,
                target=firm.firm_id,
                payload=payload,
                space_id="reference_universe",
                visibility=firm.visibility,
            )
        return firm

    def get_firm_profile(
        self, firm_profile_id: str
    ) -> SyntheticSectorFirmProfile:
        try:
            return self._firm_profiles[firm_profile_id]
        except KeyError as exc:
            raise UnknownSyntheticSectorFirmProfileError(
                "firm_profile not found: " f"{firm_profile_id!r}"
            ) from exc

    def list_firm_profiles(
        self,
    ) -> tuple[SyntheticSectorFirmProfile, ...]:
        return tuple(self._firm_profiles.values())

    def list_firms_by_sector(
        self, sector_id: str
    ) -> tuple[SyntheticSectorFirmProfile, ...]:
        return tuple(
            f
            for f in self._firm_profiles.values()
            if f.sector_id == sector_id
        )

    def list_firms_by_size(
        self, firm_size_label: str
    ) -> tuple[SyntheticSectorFirmProfile, ...]:
        return tuple(
            f
            for f in self._firm_profiles.values()
            if f.firm_size_label == firm_size_label
        )

    def list_firms_by_funding_dependency(
        self, funding_dependency_label: str
    ) -> tuple[SyntheticSectorFirmProfile, ...]:
        return tuple(
            f
            for f in self._firm_profiles.values()
            if f.funding_dependency_label == funding_dependency_label
        )

    def list_firms_by_market_access_sensitivity(
        self, market_access_sensitivity_label: str
    ) -> tuple[SyntheticSectorFirmProfile, ...]:
        return tuple(
            f
            for f in self._firm_profiles.values()
            if (
                f.market_access_sensitivity_label
                == market_access_sensitivity_label
            )
        )

    # -- snapshot ---------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        return {
            "reference_universe_profiles": [
                p.to_dict()
                for p in self._universe_profiles.values()
            ],
            "generic_sector_references": [
                s.to_dict()
                for s in self._sector_references.values()
            ],
            "synthetic_sector_firm_profiles": [
                f.to_dict() for f in self._firm_profiles.values()
            ],
        }


# ---------------------------------------------------------------------------
# Default 11-sector universe fixture
#
# Sector vocabulary mapping (closed set, jurisdiction-neutral):
#
#   energy_like                    -> cyclical
#   materials_like                 -> cyclical
#   industrials_like               -> cyclical
#   consumer_discretionary_like    -> cyclical
#   consumer_staples_like          -> defensive
#   health_care_like               -> defensive
#   financials_like                -> financial
#   information_technology_like    -> technology_related
#   communication_services_like    -> technology_related
#   utilities_like                 -> regulated_utility_like
#   real_estate_like               -> real_asset_related
#
# Sensitivity matrix uses the three-rung set (low / moderate /
# high). The matrix is jurisdiction-neutral and synthetic; it
# reflects a generic textbook reading of each sector group
# rather than any real-data calibration.
# ---------------------------------------------------------------------------


_DEFAULT_SECTOR_SPECS: tuple[
    tuple[str, str, str, str, str, str, str, str], ...
] = (
    # (sector_label, sector_group, demand, rate, credit,
    #  input_cost, policy, technology_disruption)
    ("energy_like",                 "cyclical",
     "high", "moderate", "moderate", "high", "high", "low"),
    ("materials_like",              "cyclical",
     "high", "moderate", "moderate", "high", "moderate", "low"),
    ("industrials_like",            "cyclical",
     "high", "moderate", "moderate", "high", "moderate", "moderate"),
    ("consumer_discretionary_like", "cyclical",
     "high", "moderate", "moderate", "moderate", "low", "moderate"),
    ("consumer_staples_like",       "defensive",
     "low", "low", "low", "high", "low", "low"),
    ("health_care_like",            "defensive",
     "low", "low", "low", "low", "high", "moderate"),
    ("financials_like",             "financial",
     "moderate", "high", "high", "low", "high", "moderate"),
    ("information_technology_like", "technology_related",
     "moderate", "high", "low", "low", "moderate", "high"),
    ("communication_services_like", "technology_related",
     "moderate", "moderate", "low", "low", "high", "high"),
    ("utilities_like",              "regulated_utility_like",
     "low", "high", "high", "high", "high", "low"),
    ("real_estate_like",            "real_asset_related",
     "moderate", "high", "high", "moderate", "moderate", "low"),
)


_DEFAULT_FIRM_SPECS: tuple[
    tuple[str, str, str, str, str, str, str, str, str], ...
] = (
    # (sector_label, firm_size, balance_sheet, funding_dep,
    #  demand_cyclicality, input_cost, rate_sens,
    #  credit_sens, market_access_sens)
    ("energy_like",
     "large", "asset_heavy",                "high",
     "highly_cyclical", "high", "moderate", "moderate", "moderate"),
    ("materials_like",
     "mid", "asset_heavy",                  "moderate",
     "highly_cyclical", "high", "moderate", "moderate", "moderate"),
    ("industrials_like",
     "mid", "working_capital_intensive",    "moderate",
     "cyclical", "high", "moderate", "moderate", "moderate"),
    ("consumer_discretionary_like",
     "mid", "working_capital_intensive",    "moderate",
     "highly_cyclical", "moderate", "moderate", "moderate", "moderate"),
    ("consumer_staples_like",
     "mid", "asset_light",                  "low",
     "defensive", "high", "low", "low", "low"),
    ("health_care_like",
     "mid", "asset_light",                  "low",
     "defensive", "low", "low", "low", "low"),
    ("financials_like",
     "large", "financial_balance_sheet",    "high",
     "moderate", "low", "high", "high", "high"),
    ("information_technology_like",
     "mid", "asset_light",                  "low",
     "moderate", "low", "high", "low", "low"),
    ("communication_services_like",
     "mid", "asset_light",                  "moderate",
     "moderate", "low", "moderate", "low", "moderate"),
    ("utilities_like",
     "mid", "regulated_asset_base_like",    "high",
     "defensive", "high", "high", "high", "high"),
    ("real_estate_like",
     "mid", "asset_heavy",                  "high",
     "moderate", "moderate", "high", "high", "high"),
)


def _sector_id_for(sector_label: str) -> str:
    # Strip the trailing ``_like`` suffix for the id stem so
    # a reader can read the id without the marketing-style
    # suffix; the ``_like`` discipline is enforced at the
    # ``sector_label`` field, not the plain id.
    stem = sector_label
    if stem.endswith("_like"):
        stem = stem[: -len("_like")]
    return f"sector:reference:{stem}"


def _firm_id_for(sector_label: str) -> str:
    stem = sector_label
    if stem.endswith("_like"):
        stem = stem[: -len("_like")]
    return f"firm:reference_{stem}_a"


def _firm_profile_id_for(firm_id: str) -> str:
    return f"firm_profile:{firm_id}"


@dataclass(frozen=True)
class GenericReferenceUniverseFixture:
    """Immutable bundle returned by
    :func:`build_generic_11_sector_reference_universe`. Carries
    the constructed records without registering anything on a
    kernel — the caller must explicitly invoke
    :func:`register_generic_11_sector_reference_universe` if
    storage is desired."""

    universe_profile: ReferenceUniverseProfile
    sector_references: tuple[GenericSectorReference, ...]
    firm_profiles: tuple[SyntheticSectorFirmProfile, ...]


def build_generic_11_sector_reference_universe(
    *,
    reference_universe_id: str = (
        "reference_universe:generic_11_sector"
    ),
    investor_count: int = 4,
    bank_count: int = 3,
    period_count: int = 12,
) -> GenericReferenceUniverseFixture:
    """Construct the v1.20.0-pinned default universe — one
    :class:`ReferenceUniverseProfile` + 11
    :class:`GenericSectorReference` records (one per sector
    label) + 11 :class:`SyntheticSectorFirmProfile` records
    (one representative firm per sector).

    The helper is **deterministic** and **does not register**
    anything on a kernel. To store the records the caller must
    invoke :func:`register_generic_11_sector_reference_universe`
    explicitly.

    Same arguments → byte-identical fixture.
    """
    universe_profile = ReferenceUniverseProfile(
        reference_universe_id=reference_universe_id,
        universe_profile_label="generic_11_sector",
        firm_count=len(_DEFAULT_FIRM_SPECS),
        sector_count=len(_DEFAULT_SECTOR_SPECS),
        investor_count=investor_count,
        bank_count=bank_count,
        period_count=period_count,
        sector_taxonomy_label="generic_11_sector_reference",
        synthetic_only=True,
    )

    sector_references: list[GenericSectorReference] = []
    for spec in _DEFAULT_SECTOR_SPECS:
        (
            sector_label,
            sector_group_label,
            demand,
            rate,
            credit,
            input_cost,
            policy,
            tech,
        ) = spec
        sector_references.append(
            GenericSectorReference(
                sector_id=_sector_id_for(sector_label),
                sector_label=sector_label,
                sector_group_label=sector_group_label,
                demand_sensitivity_label=demand,
                rate_sensitivity_label=rate,
                credit_sensitivity_label=credit,
                input_cost_sensitivity_label=input_cost,
                policy_sensitivity_label=policy,
                technology_disruption_sensitivity_label=tech,
            )
        )

    firm_profiles: list[SyntheticSectorFirmProfile] = []
    for spec in _DEFAULT_FIRM_SPECS:
        (
            sector_label,
            firm_size,
            balance_sheet,
            funding_dep,
            demand_cyc,
            input_cost,
            rate_sens,
            credit_sens,
            market_access_sens,
        ) = spec
        firm_id = _firm_id_for(sector_label)
        firm_profiles.append(
            SyntheticSectorFirmProfile(
                firm_profile_id=_firm_profile_id_for(firm_id),
                firm_id=firm_id,
                sector_id=_sector_id_for(sector_label),
                sector_label=sector_label,
                firm_size_label=firm_size,
                balance_sheet_style_label=balance_sheet,
                funding_dependency_label=funding_dep,
                demand_cyclicality_label=demand_cyc,
                input_cost_exposure_label=input_cost,
                rate_sensitivity_label=rate_sens,
                credit_sensitivity_label=credit_sens,
                market_access_sensitivity_label=market_access_sens,
            )
        )

    return GenericReferenceUniverseFixture(
        universe_profile=universe_profile,
        sector_references=tuple(sector_references),
        firm_profiles=tuple(firm_profiles),
    )


def register_generic_11_sector_reference_universe(
    book: ReferenceUniverseBook,
    fixture: GenericReferenceUniverseFixture | None = None,
    **builder_kwargs: Any,
) -> GenericReferenceUniverseFixture:
    """Explicit registration helper. Call this only when the
    caller wants the v1.20.0 default fixture stored on a
    kernel's :class:`ReferenceUniverseBook`. Raises
    ``Duplicate*Error`` if any record id is already present.

    The caller-supplied ``fixture`` (if any) is registered as-
    is; otherwise the helper builds the default fixture via
    :func:`build_generic_11_sector_reference_universe` (passing
    any additional keyword args through to the builder).
    """
    if fixture is None:
        fixture = build_generic_11_sector_reference_universe(
            **builder_kwargs
        )
    book.add_universe_profile(fixture.universe_profile)
    for sector in fixture.sector_references:
        book.add_sector_reference(sector)
    for firm in fixture.firm_profiles:
        book.add_firm_profile(firm)
    return fixture


# ---------------------------------------------------------------------------
# Iterables for tests / readers
# ---------------------------------------------------------------------------


def default_sector_label_order() -> tuple[str, ...]:
    """The pinned 11-sector ordering for the v1.20.0 default
    fixture. Mirrors ``_DEFAULT_SECTOR_SPECS``."""
    return tuple(spec[0] for spec in _DEFAULT_SECTOR_SPECS)


def default_firm_id_order() -> tuple[str, ...]:
    """The pinned 11-firm ordering for the v1.20.0 default
    fixture."""
    return tuple(
        _firm_id_for(spec[0]) for spec in _DEFAULT_FIRM_SPECS
    )


__all__ = [
    "BALANCE_SHEET_STYLE_LABELS",
    "DEMAND_CYCLICALITY_LABELS",
    "DuplicateGenericSectorReferenceError",
    "DuplicateReferenceUniverseProfileError",
    "DuplicateSyntheticSectorFirmProfileError",
    "FIRM_SIZE_LABELS",
    "FORBIDDEN_REFERENCE_UNIVERSE_FIELD_NAMES",
    "FUNDING_DEPENDENCY_LABELS",
    "GenericReferenceUniverseFixture",
    "GenericSectorReference",
    "INPUT_COST_EXPOSURE_LABELS",
    "ReferenceUniverseBook",
    "ReferenceUniverseError",
    "ReferenceUniverseProfile",
    "SECTOR_GROUP_LABELS",
    "SECTOR_LABELS",
    "SECTOR_TAXONOMY_LABELS",
    "SENSITIVITY_LABELS",
    "STATUS_LABELS",
    "SyntheticSectorFirmProfile",
    "UNIVERSE_PROFILE_LABELS",
    "UnknownGenericSectorReferenceError",
    "UnknownReferenceUniverseProfileError",
    "UnknownSyntheticSectorFirmProfileError",
    "VISIBILITY_LABELS",
    "build_generic_11_sector_reference_universe",
    "default_firm_id_order",
    "default_sector_label_order",
    "register_generic_11_sector_reference_universe",
]
