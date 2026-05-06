"""
v1.26.2 — Per-entity reporting-calendar profile storage.

Generic, country-neutral storage-only foundation per
[`docs/v1_26_entity_lifecycle_reporting_calendar_foundation.md`](../docs/v1_26_entity_lifecycle_reporting_calendar_foundation.md)
§4 / §6.

v1.26.2 ships :class:`ReportingCalendarProfile` +
:class:`ReportingCalendarProfileBook` + the v1.26.0
closed-set vocabularies (``MONTH_LABELS`` /
``DISCLOSURE_CLUSTER_LABELS`` /
``REPORTING_INTENSITY_LABELS``). Read-only readout
lands at v1.26.3; export at v1.26.4; freeze at
v1.26.last.

Critical design constraints (binding, v1.26.0):

- Generic / jurisdiction-neutral. No real Japanese
  reporting calendar; the ``concentrated``
  ``disclosure_cluster_label`` describes synthetic
  clustering only.
- Append-only. Revisions append a new profile.
- Empty-by-default on the kernel.
- ``quarterly_reporting_month_labels`` 0-4 entries,
  duplicates rejected.
- No real data adapter (EDINET / TDnet / J-Quants /
  FSA), no event-to-price mapping, no forecast.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Iterable, Mapping

from world.clock import Clock
from world.forbidden_tokens import (
    FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES,
)
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Closed-set vocabularies (binding for v1.26.2)
# ---------------------------------------------------------------------------


MONTH_LABELS: frozenset[str] = frozenset(
    {
        "month_01",
        "month_02",
        "month_03",
        "month_04",
        "month_05",
        "month_06",
        "month_07",
        "month_08",
        "month_09",
        "month_10",
        "month_11",
        "month_12",
        "unknown",
    }
)


DISCLOSURE_CLUSTER_LABELS: frozenset[str] = frozenset(
    {
        "concentrated",
        "moderate",
        "dispersed",
        "unknown",
    }
)


REPORTING_INTENSITY_LABELS: frozenset[str] = frozenset(
    {
        "low",
        "medium",
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


# Soft cap on quarterly reporting months; v1.26 expects
# 0 (annual / unknown), 1, 2 (semi-annual), or 4 (quarterly).
QUARTERLY_REPORTING_MONTHS_MAX_LEN: int = 4


# ---------------------------------------------------------------------------
# Default boundary flags (binding per v1.26.0 §5.1)
# ---------------------------------------------------------------------------


_DEFAULT_BOUNDARY_FLAGS_TUPLE: tuple[tuple[str, bool], ...] = (
    ("no_actor_decision", True),
    ("no_llm_execution", True),
    ("no_price_formation", True),
    ("no_trading", True),
    ("no_financing_execution", True),
    ("no_investment_advice", True),
    ("synthetic_only", True),
    ("no_aggregate_stress_result", True),
    ("no_interaction_inference", True),
    ("no_field_value_claim", True),
    ("no_field_magnitude_claim", True),
    ("descriptive_only", True),
    ("no_real_data_ingestion", True),
    ("no_japan_calibration", True),
    ("no_real_company_name", True),
    ("no_market_effect_inference", True),
    ("no_event_to_price_mapping", True),
    ("no_forecast_from_calendar", True),
)


def _default_boundary_flags() -> dict[str, bool]:
    return dict(_DEFAULT_BOUNDARY_FLAGS_TUPLE)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ReportingCalendarProfileError(Exception):
    """Base class for v1.26.2 storage errors."""


class DuplicateReportingCalendarProfileError(
    ReportingCalendarProfileError
):
    """Raised when a ``reporting_calendar_profile_id`` is
    added twice."""


class UnknownReportingCalendarProfileError(
    ReportingCalendarProfileError, KeyError
):
    """Raised when a ``reporting_calendar_profile_id`` is
    not found."""


# ---------------------------------------------------------------------------
# Validation helpers
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
    reject_duplicates: bool = True,
) -> tuple[str, ...]:
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
        if reject_duplicates and entry in seen:
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
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if key in FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key "
                f"{key!r} (v1.26.0 universe / calendar "
                "boundary)"
            )


def _scan_label_value_for_forbidden_tokens(
    value: str, *, field_name: str
) -> None:
    if value in FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES:
        raise ValueError(
            f"{field_name} value {value!r} is forbidden"
        )


# ---------------------------------------------------------------------------
# ReportingCalendarProfile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReportingCalendarProfile:
    """Immutable, append-only record of one entity's
    reporting calendar."""

    reporting_calendar_profile_id: str
    entity_id: str
    fiscal_year_end_month_label: str
    quarterly_reporting_month_labels: tuple[str, ...] = (
        field(default_factory=tuple)
    )
    disclosure_cluster_label: str = "unknown"
    reporting_intensity_label: str = "unknown"
    status: str = "active"
    visibility: str = "internal"
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "reporting_calendar_profile_id",
        "entity_id",
        "fiscal_year_end_month_label",
        "disclosure_cluster_label",
        "reporting_intensity_label",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("fiscal_year_end_month_label", MONTH_LABELS),
        (
            "disclosure_cluster_label",
            DISCLOSURE_CLUSTER_LABELS,
        ),
        (
            "reporting_intensity_label",
            REPORTING_INTENSITY_LABELS,
        ),
        ("status", STATUS_LABELS),
        ("visibility", VISIBILITY_LABELS),
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} is in the "
                    "v1.26.0 forbidden field-name set"
                )
        for name in self.REQUIRED_STRING_FIELDS:
            _validate_required_string(
                getattr(self, name), field_name=name
            )
        for name, allowed in self.LABEL_FIELDS:
            _validate_label(
                getattr(self, name), allowed, field_name=name
            )
        for name, _ in self.LABEL_FIELDS:
            _scan_label_value_for_forbidden_tokens(
                getattr(self, name), field_name=name
            )
        # quarterly_reporting_month_labels — closed-set;
        # 0-4 entries; no duplicates.
        object.__setattr__(
            self,
            "quarterly_reporting_month_labels",
            _validate_label_tuple(
                self.quarterly_reporting_month_labels,
                MONTH_LABELS,
                field_name=(
                    "quarterly_reporting_month_labels"
                ),
                max_len=QUARTERLY_REPORTING_MONTHS_MAX_LEN,
                reject_duplicates=True,
            ),
        )
        # boundary_flags — defaults non-removable
        bf = dict(self.boundary_flags)
        for key, val in bf.items():
            if not isinstance(key, str) or not key:
                raise ValueError(
                    "boundary_flags keys must be non-empty"
                )
            if not isinstance(val, bool):
                raise ValueError(
                    f"boundary_flags[{key!r}] must be bool"
                )
        for default_key, default_val in (
            _DEFAULT_BOUNDARY_FLAGS_TUPLE
        ):
            if (
                default_key in bf
                and bf[default_key] != default_val
            ):
                raise ValueError(
                    f"boundary_flags[{default_key!r}] is a "
                    "v1.26.0 default; cannot be overridden"
                )
            bf.setdefault(default_key, default_val)
        _scan_for_forbidden_keys(
            bf, field_name="boundary_flags"
        )
        object.__setattr__(self, "boundary_flags", bf)
        # metadata
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(
            metadata_dict, field_name="metadata"
        )
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reporting_calendar_profile_id": (
                self.reporting_calendar_profile_id
            ),
            "entity_id": self.entity_id,
            "fiscal_year_end_month_label": (
                self.fiscal_year_end_month_label
            ),
            "quarterly_reporting_month_labels": list(
                self.quarterly_reporting_month_labels
            ),
            "disclosure_cluster_label": (
                self.disclosure_cluster_label
            ),
            "reporting_intensity_label": (
                self.reporting_intensity_label
            ),
            "status": self.status,
            "visibility": self.visibility,
            "boundary_flags": dict(self.boundary_flags),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# ReportingCalendarProfileBook
# ---------------------------------------------------------------------------


@dataclass
class ReportingCalendarProfileBook:
    """Append-only storage for v1.26.2
    :class:`ReportingCalendarProfile` instances."""

    ledger: Ledger | None = None
    clock: Clock | None = None
    _profiles: dict[str, ReportingCalendarProfile] = field(
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
        profile: ReportingCalendarProfile,
        *,
        simulation_date: Any = None,
    ) -> ReportingCalendarProfile:
        if not isinstance(
            profile, ReportingCalendarProfile
        ):
            raise TypeError(
                "profile must be a "
                "ReportingCalendarProfile"
            )
        if (
            profile.reporting_calendar_profile_id
            in self._profiles
        ):
            raise DuplicateReportingCalendarProfileError(
                "Duplicate reporting_calendar_profile_id: "
                f"{profile.reporting_calendar_profile_id!r}"
            )
        self._profiles[
            profile.reporting_calendar_profile_id
        ] = profile

        if self.ledger is not None:
            payload: dict[str, Any] = {
                "reporting_calendar_profile_id": (
                    profile.reporting_calendar_profile_id
                ),
                "entity_id": profile.entity_id,
                "fiscal_year_end_month_label": (
                    profile.fiscal_year_end_month_label
                ),
                "quarterly_reporting_month_labels": list(
                    profile.quarterly_reporting_month_labels
                ),
                "disclosure_cluster_label": (
                    profile.disclosure_cluster_label
                ),
                "reporting_intensity_label": (
                    profile.reporting_intensity_label
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
                    "reporting_calendar_profile_recorded"
                ),
                simulation_date=sim_date,
                object_id=(
                    profile.reporting_calendar_profile_id
                ),
                source=profile.entity_id,
                payload=payload,
                space_id="reporting_calendars",
                visibility=profile.visibility,
            )
        return profile

    def get_profile(
        self, reporting_calendar_profile_id: str
    ) -> ReportingCalendarProfile:
        try:
            return self._profiles[
                reporting_calendar_profile_id
            ]
        except KeyError as exc:
            raise UnknownReportingCalendarProfileError(
                "reporting_calendar_profile not found: "
                f"{reporting_calendar_profile_id!r}"
            ) from exc

    def list_profiles(
        self,
    ) -> tuple[ReportingCalendarProfile, ...]:
        return tuple(self._profiles.values())

    def list_by_entity(
        self, entity_id: str
    ) -> tuple[ReportingCalendarProfile, ...]:
        return tuple(
            p
            for p in self._profiles.values()
            if p.entity_id == entity_id
        )

    def list_by_fiscal_year_end_month(
        self, fiscal_year_end_month_label: str
    ) -> tuple[ReportingCalendarProfile, ...]:
        return tuple(
            p
            for p in self._profiles.values()
            if p.fiscal_year_end_month_label
            == fiscal_year_end_month_label
        )

    def list_by_reporting_month(
        self, month_label: str
    ) -> tuple[ReportingCalendarProfile, ...]:
        return tuple(
            p
            for p in self._profiles.values()
            if month_label
            in p.quarterly_reporting_month_labels
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "reporting_calendar_profiles": [
                p.to_dict()
                for p in self._profiles.values()
            ],
        }


__all__ = [
    "DISCLOSURE_CLUSTER_LABELS",
    "DuplicateReportingCalendarProfileError",
    "MONTH_LABELS",
    "QUARTERLY_REPORTING_MONTHS_MAX_LEN",
    "REPORTING_INTENSITY_LABELS",
    "ReportingCalendarProfile",
    "ReportingCalendarProfileBook",
    "ReportingCalendarProfileError",
    "STATUS_LABELS",
    "UnknownReportingCalendarProfileError",
    "VISIBILITY_LABELS",
]
