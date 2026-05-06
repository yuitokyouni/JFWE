"""
v1.25.1 — Institutional investor mandate / benchmark
pressure layer storage.

Storage-only foundation for the v1.25 Institutional
Investor Mandate / Benchmark Pressure Layer (per
[`docs/v1_25_institutional_investor_mandate_benchmark_pressure.md`](../docs/v1_25_institutional_investor_mandate_benchmark_pressure.md)).
v1.25.1 ships one immutable frozen dataclass
(:class:`InvestorMandateProfile`), one append-only
:class:`InvestorMandateBook`, and the v1.25.0 closed-set
vocabularies — and nothing else. Read-only readout
(v1.25.2), export (v1.25.3), case study (v1.25.4), and
freeze (v1.25.last) are strictly later sub-milestones.

Critical design constraints carried verbatim from the
v1.25.0 design pin (binding):

- **Attention / review context conditioning only.** A
  mandate profile is descriptive: it carries closed-set
  labels for mandate type / benchmark pressure / liquidity
  need / liability horizon / stewardship priorities /
  review frequency / concentration tolerance. **No**
  portfolio allocation, **no** target weight, **no**
  rebalancing field, **no** trade / order / execution
  field, **no** expected return / target price /
  recommendation field, **no** tracking-error value field,
  **no** benchmark identifier field. The
  :data:`world.forbidden_tokens.FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES`
  composed set forbids these tokens at every payload
  surface.
- **Append-only.** No profile ever mutates a prior
  profile. A reviewer who wants to revise a mandate
  appends a new profile (the prior profile remains in
  the book).
- **Read-only with respect to the world.** The book
  emits **exactly one ledger record** per successful
  ``add_profile(...)`` call (a single
  :data:`world.ledger.RecordType.INVESTOR_MANDATE_PROFILE_RECORDED`
  event). It mutates **no other source-of-truth book**;
  pre-existing kernel-book snapshots remain byte-
  identical pre / post call.
- **No automatic profile entry point.** The book
  exposes :meth:`InvestorMandateBook.add_profile`
  only. There is **no** ``auto_profile(...)``,
  ``infer_mandate(...)``,
  ``classify_archetype(...)``,
  or ``propose_profile(...)`` helper.
- **No investor intent / market intent / actor
  decision.** Adding a profile does **not** emit any
  v1.15.5 / v1.16.2 :class:`InvestorMarketIntentRecord`,
  does **not** call any v1.15.x / v1.16.x intent
  helper, and does **not** modify the v1.16.x closed-
  loop attention emission.
- **Empty by default on the kernel.** The
  ``WorldKernel.investor_mandates`` field is wired
  with ``field(default_factory=InvestorMandateBook)``;
  an empty book emits no ledger record, leaving every
  v1.21.last canonical ``living_world_digest`` byte-
  identical at v1.25.x:

  - ``quarterly_default`` —
    ``f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c``
  - ``monthly_reference`` —
    ``75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d``
  - ``scenario_monthly_reference_universe`` test-fixture
    — ``5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6``
  - v1.20.4 CLI bundle —
    ``ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf``

The module is **runtime-book-free** beyond the v0/v1
ledger + clock convention shared by every other storage
book. It does not import any source-of-truth book on the
engine side, does not call the v1.15.x / v1.16.x
investor-intent helpers, does not call the v1.18.2 /
v1.21.x apply helpers, and does not register itself with
the v1.16.x closed-loop attention path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Iterable, Mapping

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES,
)
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Closed-set vocabularies (binding for v1.25.1; expanding any
# of these closed sets requires a fresh v1.25.x.x design pin).
# ---------------------------------------------------------------------------


# v1.25.0 — mandate type closed set. The ``_like`` suffix is
# binding: the labels describe **archetypes**, not real
# institutional categories. v1.25.x carries no claim that any
# specific real-world investor matches any specific archetype.
MANDATE_TYPE_LABELS: frozenset[str] = frozenset(
    {
        "pension_like",
        "insurance_like",
        "active_manager_like",
        "passive_manager_like",
        "sovereign_like",
        "endowment_like",
        "unknown",
    }
)


# v1.25.0 — benchmark pressure closed set. Five descriptive
# bands. **No numeric mapping**; the labels are not "0% / 25%
# / 50% / 75%" tracking-error buckets in disguise. The label
# describes how much the investor's review process emphasises
# a benchmark frame, not which trades they place.
BENCHMARK_PRESSURE_LABELS: frozenset[str] = frozenset(
    {
        "none",
        "low",
        "moderate",
        "high",
        "unknown",
    }
)


# v1.25.0 — liquidity need closed set.
LIQUIDITY_NEED_LABELS: frozenset[str] = frozenset(
    {
        "low",
        "moderate",
        "high",
        "unknown",
    }
)


# v1.25.0 — liability horizon closed set.
LIABILITY_HORIZON_LABELS: frozenset[str] = frozenset(
    {
        "short",
        "medium",
        "long",
        "unknown",
    }
)


# v1.25.0 — stewardship priority closed set. Carried in
# ``stewardship_priority_labels`` as a tuple; duplicates
# rejected at construction.
STEWARDSHIP_PRIORITY_LABELS: frozenset[str] = frozenset(
    {
        "capital_discipline",
        "governance_review",
        "climate_disclosure",
        "liquidity_resilience",
        "funding_access",
        "unknown",
    }
)


# v1.25.0 — review frequency closed set.
REVIEW_FREQUENCY_LABELS: frozenset[str] = frozenset(
    {
        "monthly",
        "quarterly",
        "event_driven",
        "unknown",
    }
)


# v1.25.0 — concentration tolerance closed set.
CONCENTRATION_TOLERANCE_LABELS: frozenset[str] = frozenset(
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


# v1.25.1 — soft cap on the per-profile stewardship priority
# tuple. The design intent is "small". Six is the closed-set
# cardinality; a profile may carry every priority once.
STEWARDSHIP_PRIORITY_TUPLE_MAX_LEN: int = (
    len(STEWARDSHIP_PRIORITY_LABELS)
)


# ---------------------------------------------------------------------------
# Default boundary flags (binding per v1.25.0 design §9).
#
# Every emitted ``InvestorMandateProfile`` carries these
# flags. Callers may add additional ``True`` flags but
# **cannot** override any default to ``False``.
# ---------------------------------------------------------------------------


_DEFAULT_BOUNDARY_FLAGS_TUPLE: tuple[tuple[str, bool], ...] = (
    # v1.18.0 boundary
    ("no_actor_decision", True),
    ("no_llm_execution", True),
    ("no_price_formation", True),
    ("no_trading", True),
    ("no_financing_execution", True),
    ("no_investment_advice", True),
    ("synthetic_only", True),
    # v1.21.0a additions (re-pinned at v1.25.0)
    ("no_aggregate_stress_result", True),
    ("no_interaction_inference", True),
    ("no_field_value_claim", True),
    ("no_field_magnitude_claim", True),
    # v1.25.0 additions (mandate-specific)
    ("descriptive_only", True),
    ("no_portfolio_allocation", True),
    ("no_target_weight", True),
    ("no_rebalancing", True),
    ("no_expected_return_claim", True),
    ("no_tracking_error_value", True),
    ("no_benchmark_identification", True),
    ("attention_review_context_only", True),
)


def _default_boundary_flags() -> dict[str, bool]:
    return dict(_DEFAULT_BOUNDARY_FLAGS_TUPLE)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InvestorMandateError(Exception):
    """Base class for v1.25.1 investor-mandate storage
    errors."""


class DuplicateInvestorMandateProfileError(
    InvestorMandateError
):
    """Raised when a ``mandate_profile_id`` is added
    twice."""


class UnknownInvestorMandateProfileError(
    InvestorMandateError, KeyError
):
    """Raised when a ``mandate_profile_id`` is not found."""


# ---------------------------------------------------------------------------
# Small validation helpers (mirror the v1.21.x / v1.24.x
# discipline)
# ---------------------------------------------------------------------------


def _validate_required_string(
    value: Any, *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )
    return value


def _validate_label(
    value: Any, allowed: frozenset[str], *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )
    if value not in allowed:
        raise ValueError(
            f"{field_name} must be one of {sorted(allowed)!r}; "
            f"got {value!r}"
        )
    return value


def _validate_label_tuple(
    value: Iterable[str],
    allowed: frozenset[str],
    *,
    field_name: str,
    max_len: int | None = None,
) -> tuple[str, ...]:
    """Validate a tuple of closed-set labels. Rejects
    duplicates, empty entries, non-members. Optionally
    enforces a max length."""
    normalised = tuple(value)
    seen: set[str] = set()
    for entry in normalised:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{field_name} entries must be non-empty "
                f"strings; got {entry!r}"
            )
        if entry not in allowed:
            raise ValueError(
                f"{field_name} entry {entry!r} not in "
                f"{sorted(allowed)!r}"
            )
        if entry in seen:
            raise ValueError(
                f"{field_name} contains duplicate entry "
                f"{entry!r}"
            )
        seen.add(entry)
    if max_len is not None and len(normalised) > max_len:
        raise ValueError(
            f"{field_name} length must be <= {max_len}; "
            f"got {len(normalised)}"
        )
    return normalised


def _scan_for_forbidden_keys(
    mapping: Mapping[str, Any], *, field_name: str
) -> None:
    """Reject any v1.25.0 forbidden-name token appearing as
    a key in a metadata or payload mapping."""
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if key in FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key "
                f"{key!r} (v1.25.0 mandate boundary — "
                "investor mandate profiles do not carry "
                "actor-decision / portfolio / trade / "
                "expected-return / target-price / "
                "tracking-error / benchmark-number / "
                "real-data / Japan-calibration / LLM / "
                "interaction / aggregate / mandate-as-action "
                "tokens)"
            )


def _scan_label_value_for_forbidden_tokens(
    value: str, *, field_name: str
) -> None:
    """Reject any label whose text matches a forbidden
    token. Belt-and-braces guard against future closed-set
    extensions."""
    if value in FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES:
        raise ValueError(
            f"{field_name} value {value!r} is in the "
            "v1.25.0 mandate forbidden-name set"
        )


# ---------------------------------------------------------------------------
# InvestorMandateProfile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InvestorMandateProfile:
    """Immutable, append-only investor mandate / benchmark
    pressure / liquidity / stewardship profile cited by an
    investor via plain id.

    Cardinality:

    - One record per ``add_profile(...)`` call.
    - ``investor_id`` is a plain-id citation to a v1.16.x
      investor; the storage book does **not** dereference
      the citation.

    The record carries no ``portfolio_allocation`` /
    ``target_weight`` / ``overweight`` / ``underweight`` /
    ``rebalance`` / ``tracking_error_value`` /
    ``alpha`` / ``performance`` / ``expected_return`` /
    ``recommendation`` / ``buy`` / ``sell`` / ``order`` /
    ``trade`` / ``execution`` field, label, or value. The
    v1.25.0 forbidden-token boundary is scanned at
    construction time via the dataclass field-name guard +
    the metadata-key scan + the label-value scan.
    """

    mandate_profile_id: str
    investor_id: str
    mandate_type_label: str
    benchmark_pressure_label: str
    liquidity_need_label: str
    liability_horizon_label: str
    review_frequency_label: str
    concentration_tolerance_label: str
    stewardship_priority_labels: tuple[str, ...] = field(
        default_factory=tuple
    )
    status: str = "active"
    visibility: str = "internal"
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "mandate_profile_id",
        "investor_id",
        "mandate_type_label",
        "benchmark_pressure_label",
        "liquidity_need_label",
        "liability_horizon_label",
        "review_frequency_label",
        "concentration_tolerance_label",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("mandate_type_label",            MANDATE_TYPE_LABELS),
        ("benchmark_pressure_label",      BENCHMARK_PRESSURE_LABELS),
        ("liquidity_need_label",          LIQUIDITY_NEED_LABELS),
        ("liability_horizon_label",       LIABILITY_HORIZON_LABELS),
        ("review_frequency_label",        REVIEW_FREQUENCY_LABELS),
        ("concentration_tolerance_label", CONCENTRATION_TOLERANCE_LABELS),
        ("status",                        STATUS_LABELS),
        ("visibility",                    VISIBILITY_LABELS),
    )

    def __post_init__(self) -> None:
        # Trip-wire: a future field rename must not collide
        # with the v1.25.0 forbidden list.
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} is in the "
                    "v1.25.0 mandate forbidden field-name "
                    "set"
                )
        for name in self.REQUIRED_STRING_FIELDS:
            _validate_required_string(
                getattr(self, name), field_name=name
            )
        for name, allowed in self.LABEL_FIELDS:
            _validate_label(
                getattr(self, name), allowed, field_name=name
            )
        # Belt-and-braces: scan label values against the
        # forbidden set even though the closed-set
        # membership check above already rules out
        # forbidden content from the pinned closed sets.
        for name, _ in self.LABEL_FIELDS:
            _scan_label_value_for_forbidden_tokens(
                getattr(self, name), field_name=name
            )
        # stewardship_priority_labels — closed-set tuple.
        object.__setattr__(
            self,
            "stewardship_priority_labels",
            _validate_label_tuple(
                self.stewardship_priority_labels,
                STEWARDSHIP_PRIORITY_LABELS,
                field_name="stewardship_priority_labels",
                max_len=STEWARDSHIP_PRIORITY_TUPLE_MAX_LEN,
            ),
        )
        # boundary_flags — accept a mapping of
        # (str -> bool); reject any default override to
        # False; reject forbidden keys.
        bf = dict(self.boundary_flags)
        for key, val in bf.items():
            if not isinstance(key, str) or not key:
                raise ValueError(
                    "boundary_flags keys must be "
                    "non-empty strings"
                )
            if not isinstance(val, bool):
                raise ValueError(
                    f"boundary_flags[{key!r}] must be "
                    f"bool; got {type(val).__name__}"
                )
        for default_key, default_val in _DEFAULT_BOUNDARY_FLAGS_TUPLE:
            if default_key in bf and bf[default_key] != default_val:
                raise ValueError(
                    f"boundary_flags[{default_key!r}] is "
                    "a v1.25.0 default; cannot be "
                    "overridden to "
                    f"{bf[default_key]!r}"
                )
            bf.setdefault(default_key, default_val)
        _scan_for_forbidden_keys(
            bf, field_name="boundary_flags"
        )
        object.__setattr__(self, "boundary_flags", bf)
        # metadata — opaque, scanned for forbidden keys.
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(
            metadata_dict, field_name="metadata"
        )
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mandate_profile_id": self.mandate_profile_id,
            "investor_id": self.investor_id,
            "mandate_type_label": self.mandate_type_label,
            "benchmark_pressure_label": (
                self.benchmark_pressure_label
            ),
            "liquidity_need_label": (
                self.liquidity_need_label
            ),
            "liability_horizon_label": (
                self.liability_horizon_label
            ),
            "review_frequency_label": (
                self.review_frequency_label
            ),
            "concentration_tolerance_label": (
                self.concentration_tolerance_label
            ),
            "stewardship_priority_labels": list(
                self.stewardship_priority_labels
            ),
            "status": self.status,
            "visibility": self.visibility,
            "boundary_flags": dict(self.boundary_flags),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# InvestorMandateBook
# ---------------------------------------------------------------------------


@dataclass
class InvestorMandateBook:
    """Append-only storage for v1.25.1
    :class:`InvestorMandateProfile` instances.

    Mirrors the v1.18.1 / v1.19.3 / v1.20.1 / v1.20.2 /
    v1.21.1 / v1.21.2 / v1.24.1 storage-book convention:
    emits **exactly one ledger record** per successful
    ``add_profile(...)`` call (a single
    :data:`world.ledger.RecordType.INVESTOR_MANDATE_PROFILE_RECORDED`
    event), no extra ledger record on duplicate id, mutates
    no other source-of-truth book.

    **No automatic profile entry point.** The book exposes
    ``add_profile(profile)`` only. There is no helper that
    auto-fills, infers, classifies, or proposes profiles.

    **Multiple profiles per investor allowed** — append-only
    discipline: a reviewer revises a mandate by adding a new
    profile with a new ``mandate_profile_id``, citing the
    same ``investor_id``. The prior profile remains in the
    book. ``list_by_investor(investor_id)`` returns every
    profile cited against the same investor in insertion
    order.

    Empty by default on the kernel — pinned by
    ``test_world_kernel_investor_mandates_empty_by_default``
    + the digest trip-wires.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _profiles: dict[str, InvestorMandateProfile] = field(
        default_factory=dict
    )

    def _now(self) -> datetime:
        if self.clock is not None:
            try:
                return self.clock.current_datetime()
            except Exception:
                pass
        return datetime.now(timezone.utc)

    def add_profile(
        self,
        profile: InvestorMandateProfile,
        *,
        simulation_date: Any = None,
    ) -> InvestorMandateProfile:
        if not isinstance(profile, InvestorMandateProfile):
            raise TypeError(
                "profile must be an "
                "InvestorMandateProfile instance"
            )
        if profile.mandate_profile_id in self._profiles:
            raise DuplicateInvestorMandateProfileError(
                "Duplicate mandate_profile_id: "
                f"{profile.mandate_profile_id!r}"
            )
        self._profiles[profile.mandate_profile_id] = profile

        if self.ledger is not None:
            payload: dict[str, Any] = {
                "mandate_profile_id": (
                    profile.mandate_profile_id
                ),
                "investor_id": profile.investor_id,
                "mandate_type_label": (
                    profile.mandate_type_label
                ),
                "benchmark_pressure_label": (
                    profile.benchmark_pressure_label
                ),
                "liquidity_need_label": (
                    profile.liquidity_need_label
                ),
                "liability_horizon_label": (
                    profile.liability_horizon_label
                ),
                "review_frequency_label": (
                    profile.review_frequency_label
                ),
                "concentration_tolerance_label": (
                    profile.concentration_tolerance_label
                ),
                "stewardship_priority_labels": list(
                    profile.stewardship_priority_labels
                ),
                "status": profile.status,
                "visibility": profile.visibility,
                "boundary_flags": dict(
                    profile.boundary_flags
                ),
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
                event_type=(
                    "investor_mandate_profile_recorded"
                ),
                simulation_date=sim_date,
                object_id=profile.mandate_profile_id,
                source=profile.investor_id,
                payload=payload,
                space_id="investor_mandates",
                visibility=profile.visibility,
            )
        return profile

    def get_profile(
        self, mandate_profile_id: str
    ) -> InvestorMandateProfile:
        try:
            return self._profiles[mandate_profile_id]
        except KeyError as exc:
            raise UnknownInvestorMandateProfileError(
                "investor_mandate_profile not found: "
                f"{mandate_profile_id!r}"
            ) from exc

    def list_profiles(
        self,
    ) -> tuple[InvestorMandateProfile, ...]:
        return tuple(self._profiles.values())

    def list_by_investor(
        self, investor_id: str
    ) -> tuple[InvestorMandateProfile, ...]:
        return tuple(
            p
            for p in self._profiles.values()
            if p.investor_id == investor_id
        )

    def list_by_mandate_type(
        self, mandate_type_label: str
    ) -> tuple[InvestorMandateProfile, ...]:
        return tuple(
            p
            for p in self._profiles.values()
            if p.mandate_type_label == mandate_type_label
        )

    def list_by_benchmark_pressure(
        self, benchmark_pressure_label: str
    ) -> tuple[InvestorMandateProfile, ...]:
        return tuple(
            p
            for p in self._profiles.values()
            if p.benchmark_pressure_label
            == benchmark_pressure_label
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "investor_mandate_profiles": [
                p.to_dict()
                for p in self._profiles.values()
            ],
        }


__all__ = [
    "BENCHMARK_PRESSURE_LABELS",
    "CONCENTRATION_TOLERANCE_LABELS",
    "DuplicateInvestorMandateProfileError",
    "InvestorMandateBook",
    "InvestorMandateError",
    "InvestorMandateProfile",
    "LIABILITY_HORIZON_LABELS",
    "LIQUIDITY_NEED_LABELS",
    "MANDATE_TYPE_LABELS",
    "REVIEW_FREQUENCY_LABELS",
    "STATUS_LABELS",
    "STEWARDSHIP_PRIORITY_LABELS",
    "STEWARDSHIP_PRIORITY_TUPLE_MAX_LEN",
    "UnknownInvestorMandateProfileError",
    "VISIBILITY_LABELS",
]
