"""
v1.17.1 — Temporal Display Series.

The first concrete code milestone of the v1.17 UI / Report /
Temporal Display sequence. This module ships **display-only**
record types and a `DisplayTimelineBook` that holds them. It
**does not** create economic state, **does not** mutate any
source-of-truth book, **does not** touch the `PriceBook`,
**does not** emit any economic ledger event, and **does not**
introduce a higher-frequency simulation clock.

The five record types are:

- :class:`ReportingCalendar`         — a deterministic display
  axis (quarterly / monthly / daily_like).
- :class:`ReferenceTimelineSeries`   — a synthetic display
  series anchored to a calendar.
- :class:`SyntheticDisplayPath`      — a rendered path of
  synthetic display values produced by deterministic
  interpolation of cited quarterly anchor values.
- :class:`EventAnnotationRecord`     — an annotation rendered
  *below* a timeline.
- :class:`CausalTimelineAnnotation`  — a pair of records linked
  by a single named causal arrow already present (as a plain-id
  citation) in the kernel.

The closed-set vocabularies are pinned by frozensets at module
scope and validated at every record's ``__post_init__``.

This module is **runtime-book-free**: it imports no source-of-
truth book, no kernel, no ledger. The display-layer book is
not registered with :class:`world.kernel.WorldKernel` in
v1.17.1 — the design pointer in
``docs/v1_17_ui_report_temporal_display_design.md`` will track
whether v1.17.4 promotes the book into the kernel for the UI
workbench polish. v1.17.1 keeps the module standalone so it
cannot accidentally move ``living_world_digest``.

Hard naming boundary (v1.17.0). Allowed display kinds:
``synthetic_display_index`` / ``reference_timeline`` /
``indicative_pressure_path`` / ``event_annotation`` /
``causal_timeline`` / ``regime_comparison`` /
``attention_focus_density`` / ``display_series`` /
``reporting_calendar``. The forbidden binding list is pinned in
the module-level :data:`FORBIDDEN_DISPLAY_NAMES` frozenset
below; tests scan dataclass field names, ``to_dict`` keys,
payload metadata, and the module text against the closed set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, ClassVar, Iterable, Mapping


# ---------------------------------------------------------------------------
# Closed-set vocabularies
# ---------------------------------------------------------------------------


FREQUENCY_LABELS: frozenset[str] = frozenset(
    {
        "quarterly",
        "monthly",
        "daily_like",
        "unknown",
    }
)


INTERPOLATION_LABELS: frozenset[str] = frozenset(
    {
        "step",
        "linear",
        "hold_forward",
        "event_weighted",
        "unknown",
    }
)


ANNOTATION_TYPE_LABELS: frozenset[str] = frozenset(
    {
        "market_environment_change",
        "attention_shift",
        "market_pressure_change",
        "financing_constraint",
        "causal_checkpoint",
        "synthetic_event",
        "unknown",
    }
)


SEVERITY_LABELS: frozenset[str] = frozenset(
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
        "stale",
        "superseded",
        "archived",
        "unknown",
    }
)


VISIBILITY_LABELS: frozenset[str] = frozenset(
    {
        "internal_only",
        "shared_internal",
        "external_audit",
    }
)


# v1.17.0 hard naming boundary. Tests scan dataclass field names,
# `to_dict` keys, payload metadata, and the module text for any
# of the forbidden names below. The forbidden set is **disjoint**
# from `FREQUENCY_LABELS`, `INTERPOLATION_LABELS`,
# `ANNOTATION_TYPE_LABELS`, `SEVERITY_LABELS`, `STATUS_LABELS`,
# and `VISIBILITY_LABELS` by construction.
FORBIDDEN_DISPLAY_NAMES: frozenset[str] = frozenset(
    {
        "market_price",
        "predicted_index",
        "predicted_path",
        "expected_return",
        "target_price",
        "forecast_path",
        "forecast_index",
        "real_price_series",
        "actual_price",
        "quoted_price",
        "last_trade",
        "nav",
        "index_value",
        "benchmark_value",
        "valuation_target",
        "investment_recommendation",
        "price_prediction",
    }
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DisplayTimelineError(Exception):
    """Base class for display-timeline errors."""


class DuplicateReportingCalendarError(DisplayTimelineError):
    """Raised when a calendar_id is added twice."""


class UnknownReportingCalendarError(DisplayTimelineError, KeyError):
    """Raised when a calendar_id is not found."""


class DuplicateReferenceTimelineSeriesError(DisplayTimelineError):
    """Raised when a series_id is added twice."""


class UnknownReferenceTimelineSeriesError(DisplayTimelineError, KeyError):
    """Raised when a series_id is not found."""


class DuplicateSyntheticDisplayPathError(DisplayTimelineError):
    """Raised when a path_id is added twice."""


class UnknownSyntheticDisplayPathError(DisplayTimelineError, KeyError):
    """Raised when a path_id is not found."""


class DuplicateEventAnnotationError(DisplayTimelineError):
    """Raised when an annotation_id is added twice."""


class UnknownEventAnnotationError(DisplayTimelineError, KeyError):
    """Raised when an annotation_id is not found."""


class DuplicateCausalTimelineAnnotationError(DisplayTimelineError):
    """Raised when a causal_annotation_id is added twice."""


class UnknownCausalTimelineAnnotationError(DisplayTimelineError, KeyError):
    """Raised when a causal_annotation_id is not found."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_iso_date(value: date | str) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        # Validate by round-tripping through `date.fromisoformat`.
        date.fromisoformat(value)
        return value
    raise TypeError(
        "date must be a date, datetime, or ISO 8601 string; "
        f"got {type(value).__name__}"
    )


def _validate_label(
    value: str, allowed: frozenset[str], *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    if value not in allowed:
        raise ValueError(
            f"{field_name} must be one of {sorted(allowed)!r}; "
            f"got {value!r}"
        )
    return value


def _validate_string_tuple(
    value: Iterable[str], *, field_name: str
) -> tuple[str, ...]:
    normalized = tuple(value)
    for entry in normalized:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{field_name} entries must be non-empty strings; "
                f"got {entry!r}"
            )
    return normalized


def _validate_iso_date_tuple(
    value: Iterable[date | str], *, field_name: str
) -> tuple[str, ...]:
    return tuple(
        _coerce_iso_date(v) for v in value
    )


def _validate_unit_float(
    value: Any, *, field_name: str
) -> float:
    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a number, not a bool"
        )
    if not isinstance(value, (int, float)):
        raise ValueError(
            f"{field_name} must be a number in [0.0, 1.0]; "
            f"got {type(value).__name__}"
        )
    f = float(value)
    if not (0.0 <= f <= 1.0):
        raise ValueError(
            f"{field_name} must lie in [0.0, 1.0]; got {f}"
        )
    return f


def _validate_unit_float_tuple(
    value: Iterable[Any], *, field_name: str
) -> tuple[float, ...]:
    return tuple(
        _validate_unit_float(v, field_name=field_name) for v in value
    )


# ---------------------------------------------------------------------------
# ReportingCalendar
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReportingCalendar:
    """
    Immutable display-only calendar.

    A ``ReportingCalendar`` is a deterministic axis. It does
    **not** drive any economic update; the actual living-world
    update tick is the v1.16 quarterly ``simulation_period``.
    The calendar exists only so a UI / report can render
    quarterly records on a finer-grained visual axis.

    - ``frequency_label`` is one of ``FREQUENCY_LABELS``;
      ``daily_like`` carries the ``_like`` suffix to flag
      deliberately that no economic decision happens at this
      granularity.
    - ``date_points`` is the deterministic tuple of ISO date
      labels rendered on the axis. Same inputs → byte-identical
      tuple.
    - ``source_period_dates`` carries the underlying simulation
      period dates the calendar was built against (typically the
      v1.9.x ``period_dates`` of the run).
    """

    calendar_id: str
    start_date: str
    end_date: str
    frequency_label: str
    date_points: tuple[str, ...] = field(default_factory=tuple)
    source_period_dates: tuple[str, ...] = field(default_factory=tuple)
    status: str = "active"
    visibility: str = "internal_only"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "calendar_id",
        "start_date",
        "end_date",
        "frequency_label",
        "status",
        "visibility",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} is required")
        object.__setattr__(
            self, "start_date", _coerce_iso_date(self.start_date)
        )
        object.__setattr__(
            self, "end_date", _coerce_iso_date(self.end_date)
        )
        if self.start_date > self.end_date:
            raise ValueError(
                "start_date must be <= end_date"
            )
        _validate_label(
            self.frequency_label,
            FREQUENCY_LABELS,
            field_name="frequency_label",
        )
        _validate_label(
            self.status, STATUS_LABELS, field_name="status"
        )
        _validate_label(
            self.visibility,
            VISIBILITY_LABELS,
            field_name="visibility",
        )
        object.__setattr__(
            self,
            "date_points",
            _validate_iso_date_tuple(
                self.date_points, field_name="date_points"
            ),
        )
        object.__setattr__(
            self,
            "source_period_dates",
            _validate_iso_date_tuple(
                self.source_period_dates,
                field_name="source_period_dates",
            ),
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "calendar_id": self.calendar_id,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "frequency_label": self.frequency_label,
            "date_points": list(self.date_points),
            "source_period_dates": list(self.source_period_dates),
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# ReferenceTimelineSeries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferenceTimelineSeries:
    """
    Immutable reference timeline series — a deterministic
    rendering anchored to a :class:`ReportingCalendar`.

    Carries cited record ids (plain-id cross-references; never
    validated against the source-of-truth books at construction
    time — the v1.0 / v1.1 cross-reference rule).
    """

    series_id: str
    calendar_id: str
    series_label: str
    frequency_label: str
    date_points: tuple[str, ...] = field(default_factory=tuple)
    source_period_dates: tuple[str, ...] = field(default_factory=tuple)
    source_record_ids: tuple[str, ...] = field(default_factory=tuple)
    status: str = "active"
    visibility: str = "internal_only"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "series_id",
        "calendar_id",
        "series_label",
        "frequency_label",
        "status",
        "visibility",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} is required")
        _validate_label(
            self.frequency_label,
            FREQUENCY_LABELS,
            field_name="frequency_label",
        )
        _validate_label(
            self.status, STATUS_LABELS, field_name="status"
        )
        _validate_label(
            self.visibility,
            VISIBILITY_LABELS,
            field_name="visibility",
        )
        object.__setattr__(
            self,
            "date_points",
            _validate_iso_date_tuple(
                self.date_points, field_name="date_points"
            ),
        )
        object.__setattr__(
            self,
            "source_period_dates",
            _validate_iso_date_tuple(
                self.source_period_dates,
                field_name="source_period_dates",
            ),
        )
        object.__setattr__(
            self,
            "source_record_ids",
            _validate_string_tuple(
                self.source_record_ids,
                field_name="source_record_ids",
            ),
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "series_id": self.series_id,
            "calendar_id": self.calendar_id,
            "series_label": self.series_label,
            "frequency_label": self.frequency_label,
            "date_points": list(self.date_points),
            "source_period_dates": list(self.source_period_dates),
            "source_record_ids": list(self.source_record_ids),
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# SyntheticDisplayPath
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticDisplayPath:
    """
    Immutable synthetic display path.

    ``display_values`` is a synthetic ordering tuple in
    ``[0.0, 1.0]`` — **never** a price, return, market value,
    NAV, benchmark level, or forecast. Tests pin the absence of
    forbidden display-name fields on every payload.

    ``anchor_period_dates`` and ``anchor_values`` carry the
    underlying quarterly evidence the rendering was produced
    from. ``date_points`` and ``display_values`` are aligned —
    ``len(date_points) == len(display_values)``.

    ``interpolation_label`` is one of
    :data:`INTERPOLATION_LABELS`. The deterministic interpolation
    methods produce byte-identical output across two calls with
    the same inputs.
    """

    path_id: str
    calendar_id: str
    path_label: str
    date_points: tuple[str, ...] = field(default_factory=tuple)
    display_values: tuple[float, ...] = field(default_factory=tuple)
    anchor_period_dates: tuple[str, ...] = field(default_factory=tuple)
    anchor_values: tuple[float, ...] = field(default_factory=tuple)
    interpolation_label: str = "linear"
    source_market_environment_state_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    source_indicative_market_pressure_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    source_financing_path_ids: tuple[str, ...] = field(default_factory=tuple)
    source_attention_state_ids: tuple[str, ...] = field(default_factory=tuple)
    status: str = "active"
    visibility: str = "internal_only"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "path_id",
        "calendar_id",
        "path_label",
        "interpolation_label",
        "status",
        "visibility",
    )

    SOURCE_ID_TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "source_market_environment_state_ids",
        "source_indicative_market_pressure_ids",
        "source_financing_path_ids",
        "source_attention_state_ids",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} is required")
        _validate_label(
            self.interpolation_label,
            INTERPOLATION_LABELS,
            field_name="interpolation_label",
        )
        _validate_label(
            self.status, STATUS_LABELS, field_name="status"
        )
        _validate_label(
            self.visibility,
            VISIBILITY_LABELS,
            field_name="visibility",
        )
        object.__setattr__(
            self,
            "date_points",
            _validate_iso_date_tuple(
                self.date_points, field_name="date_points"
            ),
        )
        object.__setattr__(
            self,
            "display_values",
            _validate_unit_float_tuple(
                self.display_values, field_name="display_values"
            ),
        )
        if len(self.date_points) != len(self.display_values):
            raise ValueError(
                "date_points and display_values must have the same "
                "length; got "
                f"len(date_points)={len(self.date_points)} vs "
                f"len(display_values)={len(self.display_values)}"
            )
        object.__setattr__(
            self,
            "anchor_period_dates",
            _validate_iso_date_tuple(
                self.anchor_period_dates,
                field_name="anchor_period_dates",
            ),
        )
        object.__setattr__(
            self,
            "anchor_values",
            _validate_unit_float_tuple(
                self.anchor_values, field_name="anchor_values"
            ),
        )
        if len(self.anchor_period_dates) != len(self.anchor_values):
            raise ValueError(
                "anchor_period_dates and anchor_values must have "
                "the same length"
            )
        for name in self.SOURCE_ID_TUPLE_FIELDS:
            object.__setattr__(
                self,
                name,
                _validate_string_tuple(
                    getattr(self, name), field_name=name
                ),
            )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_id": self.path_id,
            "calendar_id": self.calendar_id,
            "path_label": self.path_label,
            "date_points": list(self.date_points),
            "display_values": list(self.display_values),
            "anchor_period_dates": list(self.anchor_period_dates),
            "anchor_values": list(self.anchor_values),
            "interpolation_label": self.interpolation_label,
            "source_market_environment_state_ids": list(
                self.source_market_environment_state_ids
            ),
            "source_indicative_market_pressure_ids": list(
                self.source_indicative_market_pressure_ids
            ),
            "source_financing_path_ids": list(
                self.source_financing_path_ids
            ),
            "source_attention_state_ids": list(
                self.source_attention_state_ids
            ),
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# EventAnnotationRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventAnnotationRecord:
    """
    Immutable event annotation rendered *below* a timeline.
    """

    annotation_id: str
    annotation_date: str
    annotation_label: str
    annotation_type_label: str
    severity_label: str
    source_record_ids: tuple[str, ...] = field(default_factory=tuple)
    display_lane_label: str = "default"
    status: str = "active"
    visibility: str = "internal_only"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "annotation_id",
        "annotation_date",
        "annotation_label",
        "annotation_type_label",
        "severity_label",
        "display_lane_label",
        "status",
        "visibility",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} is required")
        object.__setattr__(
            self,
            "annotation_date",
            _coerce_iso_date(self.annotation_date),
        )
        _validate_label(
            self.annotation_type_label,
            ANNOTATION_TYPE_LABELS,
            field_name="annotation_type_label",
        )
        _validate_label(
            self.severity_label,
            SEVERITY_LABELS,
            field_name="severity_label",
        )
        _validate_label(
            self.status, STATUS_LABELS, field_name="status"
        )
        _validate_label(
            self.visibility,
            VISIBILITY_LABELS,
            field_name="visibility",
        )
        object.__setattr__(
            self,
            "source_record_ids",
            _validate_string_tuple(
                self.source_record_ids,
                field_name="source_record_ids",
            ),
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "annotation_id": self.annotation_id,
            "annotation_date": self.annotation_date,
            "annotation_label": self.annotation_label,
            "annotation_type_label": self.annotation_type_label,
            "severity_label": self.severity_label,
            "source_record_ids": list(self.source_record_ids),
            "display_lane_label": self.display_lane_label,
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# CausalTimelineAnnotation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CausalTimelineAnnotation:
    """
    Immutable causal timeline annotation. Renders one named
    plain-id citation arrow that already exists in the kernel —
    cause record(s) → effect record(s) — without inventing a
    new economic edge.
    """

    causal_annotation_id: str
    annotation_date: str
    event_label: str
    affected_actor_ids: tuple[str, ...] = field(default_factory=tuple)
    source_record_ids: tuple[str, ...] = field(default_factory=tuple)
    downstream_record_ids: tuple[str, ...] = field(default_factory=tuple)
    causal_summary_label: str = "causal_checkpoint"
    status: str = "active"
    visibility: str = "internal_only"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "causal_annotation_id",
        "annotation_date",
        "event_label",
        "causal_summary_label",
        "status",
        "visibility",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "affected_actor_ids",
        "source_record_ids",
        "downstream_record_ids",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} is required")
        object.__setattr__(
            self,
            "annotation_date",
            _coerce_iso_date(self.annotation_date),
        )
        _validate_label(
            self.causal_summary_label,
            ANNOTATION_TYPE_LABELS,
            field_name="causal_summary_label",
        )
        _validate_label(
            self.status, STATUS_LABELS, field_name="status"
        )
        _validate_label(
            self.visibility,
            VISIBILITY_LABELS,
            field_name="visibility",
        )
        for name in self.TUPLE_FIELDS:
            object.__setattr__(
                self,
                name,
                _validate_string_tuple(
                    getattr(self, name), field_name=name
                ),
            )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "causal_annotation_id": self.causal_annotation_id,
            "annotation_date": self.annotation_date,
            "event_label": self.event_label,
            "affected_actor_ids": list(self.affected_actor_ids),
            "source_record_ids": list(self.source_record_ids),
            "downstream_record_ids": list(self.downstream_record_ids),
            "causal_summary_label": self.causal_summary_label,
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# DisplayTimelineBook
# ---------------------------------------------------------------------------


@dataclass
class DisplayTimelineBook:
    """
    Append-only storage for v1.17.1 display-layer records.

    The book is **standalone** — not registered with
    :class:`world.kernel.WorldKernel` in v1.17.1. It writes no
    ledger record; the v1.17.0 design pinned that display
    objects do not participate in evidence resolution.

    All ``add_*`` methods are idempotent on the record id (they
    raise ``Duplicate*Error`` if the id is already present); all
    ``get_*`` methods raise ``Unknown*Error`` if the id is not
    found; all ``list_*`` methods return immutable tuples in
    insertion order.
    """

    _calendars: dict[str, ReportingCalendar] = field(default_factory=dict)
    _series: dict[str, ReferenceTimelineSeries] = field(default_factory=dict)
    _paths: dict[str, SyntheticDisplayPath] = field(default_factory=dict)
    _event_annotations: dict[str, EventAnnotationRecord] = field(
        default_factory=dict
    )
    _causal_annotations: dict[str, CausalTimelineAnnotation] = field(
        default_factory=dict
    )
    _regime_comparison_panels: dict[str, "RegimeComparisonPanel"] = field(
        default_factory=dict
    )

    # --- ReportingCalendar -------------------------------------------------

    def add_calendar(self, calendar: ReportingCalendar) -> ReportingCalendar:
        if calendar.calendar_id in self._calendars:
            raise DuplicateReportingCalendarError(
                f"Duplicate calendar_id: {calendar.calendar_id}"
            )
        self._calendars[calendar.calendar_id] = calendar
        return calendar

    def get_calendar(self, calendar_id: str) -> ReportingCalendar:
        try:
            return self._calendars[calendar_id]
        except KeyError as exc:
            raise UnknownReportingCalendarError(
                f"calendar not found: {calendar_id!r}"
            ) from exc

    def list_calendars(self) -> tuple[ReportingCalendar, ...]:
        return tuple(self._calendars.values())

    # --- ReferenceTimelineSeries ------------------------------------------

    def add_reference_series(
        self, series: ReferenceTimelineSeries
    ) -> ReferenceTimelineSeries:
        if series.series_id in self._series:
            raise DuplicateReferenceTimelineSeriesError(
                f"Duplicate series_id: {series.series_id}"
            )
        self._series[series.series_id] = series
        return series

    def get_reference_series(self, series_id: str) -> ReferenceTimelineSeries:
        try:
            return self._series[series_id]
        except KeyError as exc:
            raise UnknownReferenceTimelineSeriesError(
                f"reference series not found: {series_id!r}"
            ) from exc

    def list_reference_series(self) -> tuple[ReferenceTimelineSeries, ...]:
        return tuple(self._series.values())

    # --- SyntheticDisplayPath ---------------------------------------------

    def add_display_path(
        self, path: SyntheticDisplayPath
    ) -> SyntheticDisplayPath:
        if path.path_id in self._paths:
            raise DuplicateSyntheticDisplayPathError(
                f"Duplicate path_id: {path.path_id}"
            )
        self._paths[path.path_id] = path
        return path

    def get_display_path(self, path_id: str) -> SyntheticDisplayPath:
        try:
            return self._paths[path_id]
        except KeyError as exc:
            raise UnknownSyntheticDisplayPathError(
                f"display path not found: {path_id!r}"
            ) from exc

    def list_display_paths(self) -> tuple[SyntheticDisplayPath, ...]:
        return tuple(self._paths.values())

    def list_paths_by_calendar(
        self, calendar_id: str
    ) -> tuple[SyntheticDisplayPath, ...]:
        return tuple(
            p for p in self._paths.values() if p.calendar_id == calendar_id
        )

    # --- EventAnnotationRecord --------------------------------------------

    def add_event_annotation(
        self, annotation: EventAnnotationRecord
    ) -> EventAnnotationRecord:
        if annotation.annotation_id in self._event_annotations:
            raise DuplicateEventAnnotationError(
                f"Duplicate annotation_id: {annotation.annotation_id}"
            )
        self._event_annotations[annotation.annotation_id] = annotation
        return annotation

    def get_event_annotation(
        self, annotation_id: str
    ) -> EventAnnotationRecord:
        try:
            return self._event_annotations[annotation_id]
        except KeyError as exc:
            raise UnknownEventAnnotationError(
                f"event annotation not found: {annotation_id!r}"
            ) from exc

    def list_event_annotations(self) -> tuple[EventAnnotationRecord, ...]:
        return tuple(self._event_annotations.values())

    # --- CausalTimelineAnnotation -----------------------------------------

    def add_causal_annotation(
        self, annotation: CausalTimelineAnnotation
    ) -> CausalTimelineAnnotation:
        if annotation.causal_annotation_id in self._causal_annotations:
            raise DuplicateCausalTimelineAnnotationError(
                f"Duplicate causal_annotation_id: "
                f"{annotation.causal_annotation_id}"
            )
        self._causal_annotations[
            annotation.causal_annotation_id
        ] = annotation
        return annotation

    def get_causal_annotation(
        self, causal_annotation_id: str
    ) -> CausalTimelineAnnotation:
        try:
            return self._causal_annotations[causal_annotation_id]
        except KeyError as exc:
            raise UnknownCausalTimelineAnnotationError(
                f"causal annotation not found: "
                f"{causal_annotation_id!r}"
            ) from exc

    def list_causal_annotations(
        self,
    ) -> tuple[CausalTimelineAnnotation, ...]:
        return tuple(self._causal_annotations.values())

    # --- combined views ----------------------------------------------------

    def list_annotations_by_date(
        self, annotation_date: date | str
    ) -> tuple[EventAnnotationRecord | CausalTimelineAnnotation, ...]:
        iso = _coerce_iso_date(annotation_date)
        events = tuple(
            a
            for a in self._event_annotations.values()
            if a.annotation_date == iso
        )
        causals = tuple(
            a
            for a in self._causal_annotations.values()
            if a.annotation_date == iso
        )
        return events + causals

    # --- RegimeComparisonPanel --------------------------------------------

    def add_regime_comparison_panel(
        self, panel: "RegimeComparisonPanel"
    ) -> "RegimeComparisonPanel":
        if panel.panel_id in self._regime_comparison_panels:
            raise DuplicateRegimeComparisonPanelError(
                f"Duplicate panel_id: {panel.panel_id}"
            )
        self._regime_comparison_panels[panel.panel_id] = panel
        return panel

    def get_regime_comparison_panel(
        self, panel_id: str
    ) -> "RegimeComparisonPanel":
        try:
            return self._regime_comparison_panels[panel_id]
        except KeyError as exc:
            raise UnknownRegimeComparisonPanelError(
                f"regime comparison panel not found: {panel_id!r}"
            ) from exc

    def list_regime_comparison_panels(
        self,
    ) -> tuple["RegimeComparisonPanel", ...]:
        return tuple(self._regime_comparison_panels.values())

    def snapshot(self) -> dict[str, Any]:
        return {
            "calendars": [c.to_dict() for c in self._calendars.values()],
            "reference_series": [
                s.to_dict() for s in self._series.values()
            ],
            "display_paths": [p.to_dict() for p in self._paths.values()],
            "event_annotations": [
                a.to_dict() for a in self._event_annotations.values()
            ],
            "causal_annotations": [
                a.to_dict() for a in self._causal_annotations.values()
            ],
            "regime_comparison_panels": [
                p.to_dict()
                for p in self._regime_comparison_panels.values()
            ],
        }


# ---------------------------------------------------------------------------
# Date helpers — deterministic, no current-date dependency, no
# randomness, no business-day calendar lookup. ``daily_like`` emits
# every calendar day; the ``_like`` suffix flags that no economic
# decision happens at this granularity.
# ---------------------------------------------------------------------------


def _step_months_anchored(
    anchor_year: int, anchor_month: int, anchor_day: int, steps: int
) -> date:
    """Return ``(anchor_year, anchor_month + steps, anchor_day)``
    with the day clamped to the last day of the resulting month.

    This anchors against the original ``anchor_day``, so a chain
    of monthly steps starting at a month-end stays month-end (no
    day-of-month drift through short months).
    """
    month_index = anchor_month - 1 + steps
    new_year = anchor_year + month_index // 12
    new_month = month_index % 12 + 1
    if new_month == 12:
        first_of_next = date(new_year + 1, 1, 1)
    else:
        first_of_next = date(new_year, new_month + 1, 1)
    last_day = (first_of_next - timedelta(days=1)).day
    return date(new_year, new_month, min(anchor_day, last_day))


def _generate_date_points(
    start_date: str, end_date: str, frequency_label: str
) -> tuple[str, ...]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if frequency_label == "quarterly":
        step_months = 3
        points: list[str] = []
        steps = 0
        while True:
            cursor = _step_months_anchored(
                start.year, start.month, start.day, steps * step_months
            )
            if cursor > end:
                break
            points.append(cursor.isoformat())
            steps += 1
        return tuple(points)
    if frequency_label == "monthly":
        points = []
        steps = 0
        while True:
            cursor = _step_months_anchored(
                start.year, start.month, start.day, steps
            )
            if cursor > end:
                break
            points.append(cursor.isoformat())
            steps += 1
        return tuple(points)
    if frequency_label == "daily_like":
        points = []
        cursor = start
        while cursor <= end:
            points.append(cursor.isoformat())
            cursor = cursor + timedelta(days=1)
        return tuple(points)
    if frequency_label == "unknown":
        return ()
    raise ValueError(
        f"unsupported frequency_label: {frequency_label!r}"
    )


# ---------------------------------------------------------------------------
# build_reporting_calendar
# ---------------------------------------------------------------------------


def build_reporting_calendar(
    *,
    calendar_id: str,
    start_date: date | str,
    end_date: date | str,
    frequency_label: str,
    source_period_dates: Iterable[date | str] = (),
    status: str = "active",
    visibility: str = "internal_only",
    metadata: Mapping[str, Any] | None = None,
) -> ReportingCalendar:
    """
    Deterministic helper. Same inputs → byte-identical
    :class:`ReportingCalendar`.

    Generates ``date_points`` from ``(start_date, end_date,
    frequency_label)`` using the deterministic helpers above.
    The helper does **not** mutate any kernel book and does
    **not** introduce a higher-frequency simulation clock.
    ``daily_like`` emits every calendar day; the ``_like``
    suffix flags that no economic decision happens at this
    granularity.
    """
    start_iso = _coerce_iso_date(start_date)
    end_iso = _coerce_iso_date(end_date)
    _validate_label(
        frequency_label,
        FREQUENCY_LABELS,
        field_name="frequency_label",
    )
    source_period_dates_iso = tuple(
        _coerce_iso_date(d) for d in source_period_dates
    )
    # For ``quarterly``, prefer the explicit source-period dates
    # (they are already the canonical quarter-end anchors and
    # avoid the month-end clamping problem of arithmetic
    # quarterly stepping). For ``monthly`` / ``daily_like``, the
    # finer-grained axis is always generated from
    # ``(start_date, end_date)``.
    if (
        frequency_label == "quarterly"
        and source_period_dates_iso
    ):
        date_points = source_period_dates_iso
    else:
        date_points = _generate_date_points(
            start_iso, end_iso, frequency_label
        )
    return ReportingCalendar(
        calendar_id=calendar_id,
        start_date=start_iso,
        end_date=end_iso,
        frequency_label=frequency_label,
        date_points=date_points,
        source_period_dates=source_period_dates_iso,
        status=status,
        visibility=visibility,
        metadata=dict(metadata or {}),
    )


# ---------------------------------------------------------------------------
# Interpolation kernels
# ---------------------------------------------------------------------------


def _interpolate_step(
    anchor_dates_iso: tuple[str, ...],
    anchor_values: tuple[float, ...],
    point_iso: str,
) -> float:
    """Step function. Hold the first anchor's value forward;
    switch only at exact anchor dates."""
    chosen = anchor_values[0]
    for adate, aval in zip(anchor_dates_iso, anchor_values):
        if point_iso >= adate:
            chosen = aval
        else:
            break
    return chosen


def _interpolate_linear(
    anchor_dates_iso: tuple[str, ...],
    anchor_values: tuple[float, ...],
    point_iso: str,
) -> float:
    """Linear interpolation between adjacent anchors. Outside
    the anchor range, hold the nearest anchor's value."""
    if point_iso <= anchor_dates_iso[0]:
        return anchor_values[0]
    if point_iso >= anchor_dates_iso[-1]:
        return anchor_values[-1]
    point = date.fromisoformat(point_iso)
    for i in range(len(anchor_dates_iso) - 1):
        a_iso = anchor_dates_iso[i]
        b_iso = anchor_dates_iso[i + 1]
        if a_iso <= point_iso <= b_iso:
            a_d = date.fromisoformat(a_iso)
            b_d = date.fromisoformat(b_iso)
            span = (b_d - a_d).days
            if span <= 0:
                return anchor_values[i]
            offset = (point - a_d).days
            t = offset / span
            return (
                anchor_values[i] * (1.0 - t)
                + anchor_values[i + 1] * t
            )
    # Fallback (shouldn't reach here).
    return anchor_values[-1]


def _interpolate_hold_forward(
    anchor_dates_iso: tuple[str, ...],
    anchor_values: tuple[float, ...],
    point_iso: str,
) -> float:
    """Hold the most recent anchor's value forward (equivalent
    to ``step``; named separately so a future v1.17.x can
    diverge them)."""
    return _interpolate_step(
        anchor_dates_iso, anchor_values, point_iso
    )


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


# ---------------------------------------------------------------------------
# build_synthetic_display_path
# ---------------------------------------------------------------------------


def build_synthetic_display_path(
    *,
    path_id: str,
    calendar: ReportingCalendar,
    path_label: str,
    anchor_period_dates: Iterable[date | str],
    anchor_values: Iterable[float],
    interpolation_label: str = "linear",
    source_market_environment_state_ids: Iterable[str] = (),
    source_indicative_market_pressure_ids: Iterable[str] = (),
    source_financing_path_ids: Iterable[str] = (),
    source_attention_state_ids: Iterable[str] = (),
    status: str = "active",
    visibility: str = "internal_only",
    metadata: Mapping[str, Any] | None = None,
) -> SyntheticDisplayPath:
    """
    Deterministic helper. Same inputs → byte-identical
    :class:`SyntheticDisplayPath`.

    Renders a synthetic display path on the
    :class:`ReportingCalendar`'s ``date_points`` axis from a
    tuple of cited quarterly ``anchor_values``. The display
    values are synthetic ordinals in ``[0.0, 1.0]`` —
    **never** prices, returns, or forecasts. The interpolation
    kernel is one of :data:`INTERPOLATION_LABELS`; ``unknown``
    and ``event_weighted`` defer the synthesis to v1.17.3 and
    fall back to ``hold_forward`` here.

    The helper does **not** mutate any kernel book and does
    **not** introduce a higher-frequency simulation clock.
    """
    _validate_label(
        interpolation_label,
        INTERPOLATION_LABELS,
        field_name="interpolation_label",
    )
    anchor_dates_iso = _validate_iso_date_tuple(
        anchor_period_dates, field_name="anchor_period_dates"
    )
    anchor_values_tuple = _validate_unit_float_tuple(
        anchor_values, field_name="anchor_values"
    )
    if len(anchor_dates_iso) != len(anchor_values_tuple):
        raise ValueError(
            "anchor_period_dates and anchor_values must have "
            "the same length"
        )
    if len(anchor_dates_iso) == 0:
        raise ValueError(
            "at least one anchor_period_date / anchor_value pair "
            "is required"
        )
    sorted_pairs = sorted(
        zip(anchor_dates_iso, anchor_values_tuple),
        key=lambda pair: pair[0],
    )
    anchor_dates_iso = tuple(p[0] for p in sorted_pairs)
    anchor_values_tuple = tuple(p[1] for p in sorted_pairs)

    if interpolation_label == "linear":
        kernel = _interpolate_linear
    elif interpolation_label == "step":
        kernel = _interpolate_step
    elif interpolation_label in ("hold_forward", "event_weighted", "unknown"):
        kernel = _interpolate_hold_forward
    else:  # pragma: no cover — guarded by _validate_label above
        raise ValueError(
            f"unsupported interpolation_label: {interpolation_label!r}"
        )

    display_values = tuple(
        _clamp_unit(
            kernel(anchor_dates_iso, anchor_values_tuple, point_iso)
        )
        for point_iso in calendar.date_points
    )

    return SyntheticDisplayPath(
        path_id=path_id,
        calendar_id=calendar.calendar_id,
        path_label=path_label,
        date_points=tuple(calendar.date_points),
        display_values=display_values,
        anchor_period_dates=anchor_dates_iso,
        anchor_values=anchor_values_tuple,
        interpolation_label=interpolation_label,
        source_market_environment_state_ids=tuple(
            source_market_environment_state_ids
        ),
        source_indicative_market_pressure_ids=tuple(
            source_indicative_market_pressure_ids
        ),
        source_financing_path_ids=tuple(source_financing_path_ids),
        source_attention_state_ids=tuple(source_attention_state_ids),
        status=status,
        visibility=visibility,
        metadata=dict(metadata or {}),
    )


# ---------------------------------------------------------------------------
# v1.17.2 — Regime comparison panel
#
# Display-only side-by-side comparison of the v1.16 closed-loop
# outcomes for two or three named regime presets (typically
# ``constructive`` / ``selective`` / ``constrained`` /
# ``tightening``). The two dataclasses below are immutable and
# closed-set; the helpers compute deterministic histograms from
# pre-extracted label tuples — they do **not** import any
# source-of-truth book. The kernel-reading driver lives in
# ``examples/reference_world/regime_comparison_report.py``.
#
# The panel is a rendering of records that already exist in the
# kernel; it does not invent a new economic edge, mutate any
# book, write to the ledger, or move ``living_world_digest``.
# ---------------------------------------------------------------------------


COMPARISON_AXIS_LABELS: frozenset[str] = frozenset(
    {
        "attention_focus",
        "market_intent_direction",
        "aggregated_market_interest",
        "indicative_market_pressure",
        "financing_path_constraint",
        "financing_path_coherence",
        "unresolved_refs",
        "record_count_digest",
    }
)


class DuplicateRegimeComparisonPanelError(DisplayTimelineError):
    """Raised when a panel_id is added twice."""


class UnknownRegimeComparisonPanelError(DisplayTimelineError, KeyError):
    """Raised when a panel_id is not found."""


def _validate_label_count_mapping(
    value: Mapping[str, Any], *, field_name: str
) -> Mapping[str, int]:
    """Coerce a label → count mapping into a deterministic int
    mapping. Bool counts and negative counts are rejected."""
    coerced: dict[str, int] = {}
    for label, count in dict(value).items():
        if not isinstance(label, str) or not label:
            raise ValueError(
                f"{field_name} keys must be non-empty strings"
            )
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError(
                f"{field_name} values must be non-negative ints"
            )
        if count < 0:
            raise ValueError(
                f"{field_name} values must be non-negative"
            )
        coerced[label] = count
    return coerced


@dataclass(frozen=True)
class NamedRegimePanel:
    """Immutable per-regime panel.

    Carries the deterministic histograms used by the v1.17.2
    regime comparison report. Every histogram is a label →
    int-count mapping. ``digest`` is optional — when present, it
    is the upstream ``living_world_digest`` of the regime's run
    (sample fixture in v1.17.2; production digest if the caller
    chooses to wire it).
    """

    regime_id: str
    digest: str | None = None
    record_count: int = 0
    unresolved_refs_count: int = 0
    attention_focus_histogram: Mapping[str, int] = field(default_factory=dict)
    market_intent_direction_histogram: Mapping[str, int] = field(
        default_factory=dict
    )
    aggregated_market_interest_histogram: Mapping[str, int] = field(
        default_factory=dict
    )
    indicative_market_pressure_histogram: Mapping[str, int] = field(
        default_factory=dict
    )
    financing_path_constraint_histogram: Mapping[str, int] = field(
        default_factory=dict
    )
    financing_path_coherence_histogram: Mapping[str, int] = field(
        default_factory=dict
    )
    # v1.17.3 — display-only event / causal annotations attached
    # to the regime panel. These let two regimes whose histograms
    # collide (e.g. constrained vs tightening) still differ
    # visibly through their per-regime causal trace.
    event_annotations: tuple["EventAnnotationRecord", ...] = field(
        default_factory=tuple
    )
    causal_annotations: tuple["CausalTimelineAnnotation", ...] = field(
        default_factory=tuple
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    HISTOGRAM_FIELDS: ClassVar[tuple[str, ...]] = (
        "attention_focus_histogram",
        "market_intent_direction_histogram",
        "aggregated_market_interest_histogram",
        "indicative_market_pressure_histogram",
        "financing_path_constraint_histogram",
        "financing_path_coherence_histogram",
    )

    def __post_init__(self) -> None:
        if not isinstance(self.regime_id, str) or not self.regime_id:
            raise ValueError("regime_id is required")
        if self.digest is not None and (
            not isinstance(self.digest, str) or not self.digest
        ):
            raise ValueError("digest must be a non-empty string or None")
        for name in ("record_count", "unresolved_refs_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(
                    f"{name} must be a non-negative int"
                )
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        for name in self.HISTOGRAM_FIELDS:
            object.__setattr__(
                self,
                name,
                _validate_label_count_mapping(
                    getattr(self, name), field_name=name
                ),
            )
        events = tuple(self.event_annotations)
        for entry in events:
            if not isinstance(entry, EventAnnotationRecord):
                raise ValueError(
                    "event_annotations entries must be "
                    "EventAnnotationRecord instances"
                )
        object.__setattr__(self, "event_annotations", events)
        causals = tuple(self.causal_annotations)
        for entry in causals:
            if not isinstance(entry, CausalTimelineAnnotation):
                raise ValueError(
                    "causal_annotations entries must be "
                    "CausalTimelineAnnotation instances"
                )
        object.__setattr__(self, "causal_annotations", causals)
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime_id": self.regime_id,
            "digest": self.digest,
            "record_count": self.record_count,
            "unresolved_refs_count": self.unresolved_refs_count,
            "attention_focus_histogram": dict(
                self.attention_focus_histogram
            ),
            "market_intent_direction_histogram": dict(
                self.market_intent_direction_histogram
            ),
            "aggregated_market_interest_histogram": dict(
                self.aggregated_market_interest_histogram
            ),
            "indicative_market_pressure_histogram": dict(
                self.indicative_market_pressure_histogram
            ),
            "financing_path_constraint_histogram": dict(
                self.financing_path_constraint_histogram
            ),
            "financing_path_coherence_histogram": dict(
                self.financing_path_coherence_histogram
            ),
            "event_annotations": [
                a.to_dict() for a in self.event_annotations
            ],
            "causal_annotations": [
                a.to_dict() for a in self.causal_annotations
            ],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RegimeComparisonPanel:
    """Immutable panel that collects two or three
    :class:`NamedRegimePanel` instances side-by-side, plus the
    closed-set comparison axes the report should walk."""

    panel_id: str
    regime_panels: tuple[NamedRegimePanel, ...] = field(default_factory=tuple)
    comparison_axes: tuple[str, ...] = field(default_factory=tuple)
    reporting_calendar_id: str = ""
    status: str = "active"
    visibility: str = "internal_only"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "panel_id",
        "status",
        "visibility",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} is required")
        if not isinstance(self.reporting_calendar_id, str):
            raise ValueError(
                "reporting_calendar_id must be a string (use \"\" if none)"
            )
        _validate_label(
            self.status, STATUS_LABELS, field_name="status"
        )
        _validate_label(
            self.visibility,
            VISIBILITY_LABELS,
            field_name="visibility",
        )
        normalized_panels: list[NamedRegimePanel] = []
        seen_regime_ids: set[str] = set()
        for entry in self.regime_panels:
            if not isinstance(entry, NamedRegimePanel):
                raise ValueError(
                    "regime_panels entries must be NamedRegimePanel "
                    "instances"
                )
            if entry.regime_id in seen_regime_ids:
                raise ValueError(
                    f"duplicate regime_id in regime_panels: "
                    f"{entry.regime_id!r}"
                )
            seen_regime_ids.add(entry.regime_id)
            normalized_panels.append(entry)
        object.__setattr__(
            self, "regime_panels", tuple(normalized_panels)
        )
        normalized_axes = tuple(self.comparison_axes)
        for axis in normalized_axes:
            _validate_label(
                axis,
                COMPARISON_AXIS_LABELS,
                field_name="comparison_axes",
            )
        object.__setattr__(self, "comparison_axes", normalized_axes)
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "regime_panels": [p.to_dict() for p in self.regime_panels],
            "comparison_axes": list(self.comparison_axes),
            "reporting_calendar_id": self.reporting_calendar_id,
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# build_named_regime_panel
# ---------------------------------------------------------------------------


def _histogram(labels: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label in labels:
        if not isinstance(label, str) or not label:
            raise ValueError(
                "histogram labels must be non-empty strings"
            )
        counts[label] = counts.get(label, 0) + 1
    return counts


def build_named_regime_panel(
    *,
    regime_id: str,
    digest: str | None = None,
    record_count: int = 0,
    unresolved_refs_count: int = 0,
    attention_focus_labels: Iterable[str] = (),
    market_intent_direction_labels: Iterable[str] = (),
    aggregated_market_interest_labels: Iterable[str] = (),
    indicative_market_pressure_labels: Iterable[str] = (),
    financing_path_constraint_labels: Iterable[str] = (),
    financing_path_coherence_labels: Iterable[str] = (),
    event_annotations: Iterable[EventAnnotationRecord] = (),
    causal_annotations: Iterable[CausalTimelineAnnotation] = (),
    metadata: Mapping[str, Any] | None = None,
) -> NamedRegimePanel:
    """Deterministic helper. Builds a :class:`NamedRegimePanel`
    from pre-extracted label tuples and (optionally)
    pre-built v1.17.3 :class:`EventAnnotationRecord` /
    :class:`CausalTimelineAnnotation` tuples. The caller is
    responsible for walking the kernel books and supplying
    those tuples (typically the
    ``examples.reference_world.regime_comparison_report``
    driver).

    Same inputs → byte-identical :class:`NamedRegimePanel`."""
    if not isinstance(regime_id, str) or not regime_id:
        raise ValueError("regime_id is required")
    return NamedRegimePanel(
        regime_id=regime_id,
        digest=digest,
        record_count=record_count,
        unresolved_refs_count=unresolved_refs_count,
        attention_focus_histogram=_histogram(attention_focus_labels),
        market_intent_direction_histogram=_histogram(
            market_intent_direction_labels
        ),
        aggregated_market_interest_histogram=_histogram(
            aggregated_market_interest_labels
        ),
        indicative_market_pressure_histogram=_histogram(
            indicative_market_pressure_labels
        ),
        financing_path_constraint_histogram=_histogram(
            financing_path_constraint_labels
        ),
        financing_path_coherence_histogram=_histogram(
            financing_path_coherence_labels
        ),
        event_annotations=tuple(event_annotations),
        causal_annotations=tuple(causal_annotations),
        metadata=dict(metadata or {}),
    )


# ---------------------------------------------------------------------------
# build_regime_comparison_panel
# ---------------------------------------------------------------------------


_DEFAULT_COMPARISON_AXES: tuple[str, ...] = (
    "attention_focus",
    "market_intent_direction",
    "aggregated_market_interest",
    "indicative_market_pressure",
    "financing_path_constraint",
    "financing_path_coherence",
    "unresolved_refs",
    "record_count_digest",
)


def build_regime_comparison_panel(
    *,
    panel_id: str,
    regime_panels: Iterable[NamedRegimePanel],
    comparison_axes: Iterable[str] = _DEFAULT_COMPARISON_AXES,
    reporting_calendar_id: str = "",
    status: str = "active",
    visibility: str = "internal_only",
    metadata: Mapping[str, Any] | None = None,
) -> RegimeComparisonPanel:
    """Deterministic helper. Bundles a set of
    :class:`NamedRegimePanel` instances into a
    :class:`RegimeComparisonPanel`. Comparison axes are
    closed-set (see :data:`COMPARISON_AXIS_LABELS`).

    Same inputs → byte-identical
    :class:`RegimeComparisonPanel`."""
    return RegimeComparisonPanel(
        panel_id=panel_id,
        regime_panels=tuple(regime_panels),
        comparison_axes=tuple(comparison_axes),
        reporting_calendar_id=reporting_calendar_id,
        status=status,
        visibility=visibility,
        metadata=dict(metadata or {}),
    )


# ---------------------------------------------------------------------------
# render_regime_comparison_markdown
# ---------------------------------------------------------------------------


_AXIS_TITLES: Mapping[str, str] = {
    "attention_focus": "Attention focus",
    "market_intent_direction": "Investor market intent direction",
    "aggregated_market_interest": "Aggregated market interest",
    "indicative_market_pressure": "Indicative market pressure",
    "financing_path_constraint": "Financing path constraint",
    "financing_path_coherence": "Financing path coherence",
    "unresolved_refs": "Unresolved refs",
    "record_count_digest": "Record count / digest",
}


_AXIS_TO_HISTOGRAM_FIELD: Mapping[str, str] = {
    "attention_focus": "attention_focus_histogram",
    "market_intent_direction": "market_intent_direction_histogram",
    "aggregated_market_interest": "aggregated_market_interest_histogram",
    "indicative_market_pressure": "indicative_market_pressure_histogram",
    "financing_path_constraint": "financing_path_constraint_histogram",
    "financing_path_coherence": "financing_path_coherence_histogram",
}


def _format_histogram_cell(hist: Mapping[str, int]) -> str:
    """Render a label → count mapping as a deterministic
    sorted-key list for the markdown cell."""
    if not hist:
        return "—"
    return ", ".join(
        f"{label} {count}" for label, count in sorted(hist.items())
    )


def _short_digest(digest: str | None) -> str:
    if digest is None:
        return "—"
    if len(digest) <= 16:
        return digest
    return digest[:8] + "…" + digest[-6:]


# ---------------------------------------------------------------------------
# v1.17.3 — Event annotation + causal timeline helpers
#
# The two helpers below read **anonymous record-like inputs** (duck-typed
# via ``getattr``) and emit deterministic display annotations using the
# v1.17.3 closed-set rule set. They do not import any source-of-truth
# book; the caller (typically
# ``examples/reference_world/regime_comparison_report.py``) is
# responsible for walking the kernel and supplying the records.
#
# The rules are:
#
# - Rule 1: ``MarketEnvironmentStateRecord.overall_market_access_label``
#   ∈ ``selective_or_constrained`` →
#   :data:`event_annotation: market_environment_change`.
# - Rule 2: ``IndicativeMarketPressureRecord.market_access_label`` ∈
#   ``{constrained, closed}`` →
#   :data:`event_annotation: market_pressure_change`.
# - Rule 3: ``CorporateFinancingPathRecord.constraint_label ==
#   market_access_constraint`` →
#   :data:`event_annotation: financing_constraint`.
# - Rule 4: ``CorporateFinancingPathRecord.coherence_label ==
#   conflicting_evidence`` →
#   :data:`event_annotation: causal_checkpoint` (kind = conflicting
#   financing evidence).
# - Rule 5: ``ActorAttentionStateRecord.focus_labels`` contains any of
#   ``{risk, financing, market_access, information_gap, dilution}`` →
#   :data:`event_annotation: attention_shift`.
#
# The causal helper renders three kinds of plain-id arrows that already
# exist in the kernel:
#
# - ``MarketEnvironmentState`` → ``IndicativeMarketPressure``  (cited
#   via the v1.15.4 ``source_market_environment_state_ids`` slot)
# - ``IndicativeMarketPressure`` → ``CorporateFinancingPath``  (cited
#   via the v1.15.6 ``indicative_market_pressure_ids`` slot)
# - prior-period ``IndicativeMarketPressure`` /
#   ``CorporateFinancingPath`` → next-period ``ActorAttentionState``
#   (cited via the v1.16.3 ``source_*_ids`` slots)
#
# Both helpers are pure functions over their inputs; same inputs →
# byte-identical tuple. Neither helper mutates any kernel book or
# writes to the ledger.
# ---------------------------------------------------------------------------


_RESTRICTIVE_ENV_OVERALL_LABELS: frozenset[str] = frozenset(
    {"selective_or_constrained"}
)
_RESTRICTIVE_PRESSURE_MARKET_ACCESS_LABELS: frozenset[str] = frozenset(
    {"constrained", "closed"}
)
_V1_16_3_FRESH_FOCUS_LABELS: frozenset[str] = frozenset(
    {"risk", "financing", "market_access", "information_gap", "dilution"}
)


def _coerce_iso_or_none(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return _coerce_iso_date(value)
    except (TypeError, ValueError):
        return None


def build_event_annotations_from_closed_loop_data(
    *,
    market_environment_states: Iterable[Any] = (),
    indicative_market_pressures: Iterable[Any] = (),
    financing_paths: Iterable[Any] = (),
    attention_states: Iterable[Any] = (),
    annotation_id_prefix: str = "event_annotation",
) -> tuple[EventAnnotationRecord, ...]:
    """Render closed-loop records into a deterministic tuple of
    :class:`EventAnnotationRecord` instances using the v1.17.3
    rule set.

    All inputs are anonymous record-like objects accessed via
    ``getattr``; the helper imports no source-of-truth book and
    is therefore safe under the v1.17.0 standalone-display
    discipline. Records that do not match any rule are silently
    skipped.

    Same inputs → byte-identical tuple.
    """
    annotations: list[EventAnnotationRecord] = []

    # Rule 1 — restrictive market environment. Capture the
    # env's full closed-set label set in metadata + label so two
    # regimes whose ``overall_market_access_label`` collide
    # (e.g. ``constrained`` vs ``tightening`` both at
    # ``selective_or_constrained``) still differ visibly through
    # subfield labels (``credit_regime`` /
    # ``funding_regime`` / ``volatility_regime`` / ...).
    for env in market_environment_states:
        env_id = getattr(env, "environment_state_id", None)
        env_date = _coerce_iso_or_none(getattr(env, "as_of_date", None))
        env_label = getattr(env, "overall_market_access_label", "unknown")
        if not isinstance(env_id, str) or not env_id or env_date is None:
            continue
        if env_label in _RESTRICTIVE_ENV_OVERALL_LABELS:
            credit_regime = getattr(env, "credit_regime", "unknown")
            liquidity_regime = getattr(env, "liquidity_regime", "unknown")
            funding_regime = getattr(env, "funding_regime", "unknown")
            volatility_regime = getattr(
                env, "volatility_regime", "unknown"
            )
            risk_appetite_regime = getattr(
                env, "risk_appetite_regime", "unknown"
            )
            rate_environment = getattr(env, "rate_environment", "unknown")
            refinancing_window = getattr(
                env, "refinancing_window", "unknown"
            )
            equity_valuation_regime = getattr(
                env, "equity_valuation_regime", "unknown"
            )
            annotations.append(
                EventAnnotationRecord(
                    annotation_id=(
                        f"{annotation_id_prefix}:market_environment_change:"
                        f"{env_id}"
                    ),
                    annotation_date=env_date,
                    annotation_label=(
                        f"market environment {env_label}"
                        f" · credit={credit_regime}"
                        f", funding={funding_regime}"
                        f", liquidity={liquidity_regime}"
                        f", volatility={volatility_regime}"
                        f", refi={refinancing_window}"
                    ),
                    annotation_type_label="market_environment_change",
                    severity_label="medium",
                    source_record_ids=(env_id,),
                    display_lane_label="market_environment",
                    metadata={
                        "overall_market_access_label": env_label,
                        "credit_regime": credit_regime,
                        "liquidity_regime": liquidity_regime,
                        "funding_regime": funding_regime,
                        "volatility_regime": volatility_regime,
                        "risk_appetite_regime": risk_appetite_regime,
                        "rate_environment": rate_environment,
                        "refinancing_window": refinancing_window,
                        "equity_valuation_regime": (
                            equity_valuation_regime
                        ),
                    },
                )
            )

    # Rule 2 — restrictive indicative market pressure.
    for p in indicative_market_pressures:
        pid = getattr(p, "market_pressure_id", None)
        pdate = _coerce_iso_or_none(getattr(p, "as_of_date", None))
        plabel = getattr(p, "market_access_label", "unknown")
        if not isinstance(pid, str) or not pid or pdate is None:
            continue
        if plabel in _RESTRICTIVE_PRESSURE_MARKET_ACCESS_LABELS:
            severity = "high" if plabel == "closed" else "medium"
            annotations.append(
                EventAnnotationRecord(
                    annotation_id=(
                        f"{annotation_id_prefix}:market_pressure_change:"
                        f"{pid}"
                    ),
                    annotation_date=pdate,
                    annotation_label=(
                        f"indicative market pressure access = {plabel}"
                    ),
                    annotation_type_label="market_pressure_change",
                    severity_label=severity,
                    source_record_ids=(pid,),
                    display_lane_label="market_pressure",
                    metadata={
                        "market_access_label": plabel,
                        "liquidity_pressure_label": getattr(
                            p, "liquidity_pressure_label", "unknown"
                        ),
                        "financing_relevance_label": getattr(
                            p, "financing_relevance_label", "unknown"
                        ),
                    },
                )
            )

    # Rule 3 + Rule 4 — financing path constraint / coherence.
    for fp in financing_paths:
        fpid = getattr(fp, "financing_path_id", None)
        fpdate = _coerce_iso_or_none(getattr(fp, "as_of_date", None))
        constraint = getattr(fp, "constraint_label", "unknown")
        coherence = getattr(fp, "coherence_label", "unknown")
        firm_id = getattr(fp, "firm_id", None)
        if not isinstance(fpid, str) or not fpid or fpdate is None:
            continue
        if constraint == "market_access_constraint":
            annotations.append(
                EventAnnotationRecord(
                    annotation_id=(
                        f"{annotation_id_prefix}:financing_constraint:"
                        f"{fpid}"
                    ),
                    annotation_date=fpdate,
                    annotation_label=(
                        "financing path constraint = "
                        "market_access_constraint"
                    ),
                    annotation_type_label="financing_constraint",
                    severity_label="medium",
                    source_record_ids=(fpid,),
                    display_lane_label="financing_path",
                    metadata={
                        "constraint_label": constraint,
                        "firm_id": firm_id or "unknown",
                    },
                )
            )
        if coherence == "conflicting_evidence":
            annotations.append(
                EventAnnotationRecord(
                    annotation_id=(
                        f"{annotation_id_prefix}:financing_coherence_conflict:"
                        f"{fpid}"
                    ),
                    annotation_date=fpdate,
                    annotation_label=(
                        "financing path coherence = conflicting_evidence"
                    ),
                    annotation_type_label="causal_checkpoint",
                    severity_label="medium",
                    source_record_ids=(fpid,),
                    display_lane_label="financing_path",
                    metadata={
                        "coherence_label": coherence,
                        "firm_id": firm_id or "unknown",
                    },
                )
            )

    # Rule 5 — attention focus widened to v1.16.3 fresh labels.
    for s in attention_states:
        sid = getattr(s, "attention_state_id", None)
        sdate = _coerce_iso_or_none(getattr(s, "as_of_date", None))
        focus = tuple(getattr(s, "focus_labels", ()))
        actor = getattr(s, "actor_id", None)
        if not isinstance(sid, str) or not sid or sdate is None:
            continue
        v1163_present = sorted(
            _V1_16_3_FRESH_FOCUS_LABELS & set(focus)
        )
        if v1163_present:
            annotations.append(
                EventAnnotationRecord(
                    annotation_id=(
                        f"{annotation_id_prefix}:attention_shift:{sid}"
                    ),
                    annotation_date=sdate,
                    annotation_label=(
                        "attention focus widened: "
                        + ", ".join(v1163_present)
                    ),
                    annotation_type_label="attention_shift",
                    severity_label="low",
                    source_record_ids=(sid,),
                    display_lane_label="attention",
                    metadata={
                        "actor_id": actor or "unknown",
                        "v1_16_3_focus_present": list(v1163_present),
                    },
                )
            )

    return tuple(annotations)


def build_causal_timeline_annotations_from_closed_loop_data(
    *,
    indicative_market_pressures: Iterable[Any] = (),
    financing_paths: Iterable[Any] = (),
    attention_states: Iterable[Any] = (),
    annotation_id_prefix: str = "causal_timeline",
) -> tuple[CausalTimelineAnnotation, ...]:
    """Render plain-id citations already present on closed-loop
    records into deterministic
    :class:`CausalTimelineAnnotation` arrows.

    Three causal kinds are emitted:

    - ``MarketEnvironmentState`` → ``IndicativeMarketPressure``
      (when the pressure becomes restrictive);
    - ``IndicativeMarketPressure`` → ``CorporateFinancingPath``
      (when the financing path picks up the
      ``market_access_constraint`` constraint);
    - prior-period ``IndicativeMarketPressure`` /
      ``CorporateFinancingPath`` → next-period
      ``ActorAttentionState`` (when v1.16.3 fresh focus labels
      appear).

    Same inputs → byte-identical tuple.
    """
    annotations: list[CausalTimelineAnnotation] = []

    # Causal 1 — env → pressure.
    for p in indicative_market_pressures:
        pid = getattr(p, "market_pressure_id", None)
        pdate = _coerce_iso_or_none(getattr(p, "as_of_date", None))
        plabel = getattr(p, "market_access_label", "unknown")
        env_ids = tuple(
            getattr(p, "source_market_environment_state_ids", ())
        )
        if (
            not isinstance(pid, str)
            or not pid
            or pdate is None
            or not env_ids
        ):
            continue
        if plabel in _RESTRICTIVE_PRESSURE_MARKET_ACCESS_LABELS:
            annotations.append(
                CausalTimelineAnnotation(
                    causal_annotation_id=(
                        f"{annotation_id_prefix}:env_to_pressure:{pid}"
                    ),
                    annotation_date=pdate,
                    event_label=(
                        f"market environment -> indicative pressure "
                        f"({plabel})"
                    ),
                    affected_actor_ids=(),
                    source_record_ids=env_ids,
                    downstream_record_ids=(pid,),
                    causal_summary_label="market_pressure_change",
                    metadata={
                        "effect_market_access_label": plabel,
                    },
                )
            )

    # Causal 2 — pressure → financing path constraint.
    for fp in financing_paths:
        fpid = getattr(fp, "financing_path_id", None)
        fpdate = _coerce_iso_or_none(getattr(fp, "as_of_date", None))
        constraint = getattr(fp, "constraint_label", "unknown")
        firm = getattr(fp, "firm_id", None)
        pressure_ids = tuple(
            getattr(fp, "indicative_market_pressure_ids", ())
        )
        if (
            not isinstance(fpid, str)
            or not fpid
            or fpdate is None
            or not pressure_ids
        ):
            continue
        if constraint == "market_access_constraint":
            annotations.append(
                CausalTimelineAnnotation(
                    causal_annotation_id=(
                        f"{annotation_id_prefix}:pressure_to_financing:"
                        f"{fpid}"
                    ),
                    annotation_date=fpdate,
                    event_label=(
                        "indicative pressure -> financing path "
                        "(market_access_constraint)"
                    ),
                    affected_actor_ids=((firm,) if firm else ()),
                    source_record_ids=pressure_ids,
                    downstream_record_ids=(fpid,),
                    causal_summary_label="financing_constraint",
                    metadata={
                        "effect_constraint_label": constraint,
                    },
                )
            )

    # Causal 3 — prior pressure / path → next-period attention.
    for s in attention_states:
        sid = getattr(s, "attention_state_id", None)
        sdate = _coerce_iso_or_none(getattr(s, "as_of_date", None))
        focus = set(getattr(s, "focus_labels", ()))
        actor = getattr(s, "actor_id", None)
        prior_pressure_ids = tuple(
            getattr(s, "source_indicative_market_pressure_ids", ())
        )
        prior_path_ids = tuple(
            getattr(s, "source_corporate_financing_path_ids", ())
        )
        if not isinstance(sid, str) or not sid or sdate is None:
            continue
        v1163_present = sorted(_V1_16_3_FRESH_FOCUS_LABELS & focus)
        if not v1163_present:
            continue
        if not prior_pressure_ids and not prior_path_ids:
            continue
        annotations.append(
            CausalTimelineAnnotation(
                causal_annotation_id=(
                    f"{annotation_id_prefix}:prior_to_attention:{sid}"
                ),
                annotation_date=sdate,
                event_label=(
                    "prior-period pressure / financing path -> "
                    "attention shift"
                ),
                affected_actor_ids=((actor,) if actor else ()),
                source_record_ids=prior_pressure_ids + prior_path_ids,
                downstream_record_ids=(sid,),
                causal_summary_label="attention_shift",
                metadata={
                    "v1_16_3_focus_present": v1163_present,
                },
            )
        )

    return tuple(annotations)


_MAX_EVENTS_PER_REGIME_IN_MARKDOWN: int = 6


def _format_events_summary_cell(
    events: tuple[EventAnnotationRecord, ...],
) -> str:
    """Render an event-type histogram cell — sorted by type
    then count. Stable across runs."""
    if not events:
        return "—"
    by_type: dict[str, int] = {}
    for ev in events:
        by_type[ev.annotation_type_label] = (
            by_type.get(ev.annotation_type_label, 0) + 1
        )
    return ", ".join(
        f"{label} {count}" for label, count in sorted(by_type.items())
    )


def _format_top_event_cell(
    events: tuple[EventAnnotationRecord, ...],
    *,
    limit: int = _MAX_EVENTS_PER_REGIME_IN_MARKDOWN,
) -> str:
    """Render a short list of the regime's first ``limit``
    annotations sorted by ``(date, type)``, each cell carrying
    date + type + first source id (truncated)."""
    if not events:
        return "—"
    sorted_events = sorted(
        events,
        key=lambda e: (
            e.annotation_date,
            e.annotation_type_label,
            e.annotation_id,
        ),
    )[:limit]
    fragments: list[str] = []
    for ev in sorted_events:
        first_src = (
            ev.source_record_ids[0] if ev.source_record_ids else "—"
        )
        if len(first_src) > 28:
            first_src = first_src[:14] + "…" + first_src[-12:]
        fragments.append(
            f"{ev.annotation_date} {ev.annotation_type_label} "
            f"[{first_src}]"
        )
    return "; ".join(fragments)


def _format_causal_summary_cell(
    causal: tuple[CausalTimelineAnnotation, ...],
) -> str:
    """Render a causal_summary histogram cell."""
    if not causal:
        return "—"
    by_kind: dict[str, int] = {}
    for c in causal:
        by_kind[c.causal_summary_label] = (
            by_kind.get(c.causal_summary_label, 0) + 1
        )
    return ", ".join(
        f"{label} {count}" for label, count in sorted(by_kind.items())
    )


def render_regime_comparison_markdown(
    panel: RegimeComparisonPanel,
) -> str:
    """Render a :class:`RegimeComparisonPanel` as a deterministic
    markdown section. Same panel → byte-identical markdown
    string. The section is **synthetic display only** —
    histograms are counts of the labels actually emitted by the
    v1.16 closed-loop records; no economic claim is made about
    the values.

    v1.17.3: when the panel's :class:`NamedRegimePanel` instances
    carry ``event_annotations`` and / or ``causal_annotations``,
    the renderer appends a per-regime "Events & causal trace"
    block below the histogram table. This makes two regimes
    whose histograms collide (e.g. ``constrained`` vs
    ``tightening``) still differ visibly, since the events and
    causal arrows cite specific record ids and dates.
    """
    if not isinstance(panel, RegimeComparisonPanel):
        raise TypeError(
            "render_regime_comparison_markdown expects a "
            "RegimeComparisonPanel"
        )

    # Stable column order: panel order is the input order.
    regime_panels = panel.regime_panels
    if not regime_panels:
        return (
            f"## Regime comparison — {panel.panel_id}\n"
            "\n"
            "_No regime panels supplied._\n"
        )

    header_cells = ["Axis"] + [p.regime_id for p in regime_panels]
    sep_cells = ["---"] + ["---" for _ in regime_panels]
    lines = [
        f"## Regime comparison — {panel.panel_id}",
        "",
        "| " + " | ".join(header_cells) + " |",
        "| " + " | ".join(sep_cells) + " |",
    ]

    axes = panel.comparison_axes or _DEFAULT_COMPARISON_AXES
    for axis in axes:
        title = _AXIS_TITLES.get(axis, axis)
        if axis == "unresolved_refs":
            cells = [str(p.unresolved_refs_count) for p in regime_panels]
        elif axis == "record_count_digest":
            cells = [
                f"{p.record_count} · {_short_digest(p.digest)}"
                for p in regime_panels
            ]
        else:
            histogram_field = _AXIS_TO_HISTOGRAM_FIELD.get(axis)
            if histogram_field is None:
                cells = ["—" for _ in regime_panels]
            else:
                cells = [
                    _format_histogram_cell(
                        getattr(p, histogram_field)
                    )
                    for p in regime_panels
                ]
        row = [title] + cells
        lines.append("| " + " | ".join(row) + " |")

    # v1.17.3 — events / causal-trace summary rows.
    has_events = any(p.event_annotations for p in regime_panels)
    has_causal = any(p.causal_annotations for p in regime_panels)
    if has_events:
        events_summary = [
            _format_events_summary_cell(p.event_annotations)
            for p in regime_panels
        ]
        lines.append(
            "| " + " | ".join(["Event annotations (by type)"] + events_summary) + " |"
        )
        top_events = [
            _format_top_event_cell(p.event_annotations)
            for p in regime_panels
        ]
        lines.append(
            "| " + " | ".join(["Top events (date · type · source)"] + top_events) + " |"
        )
    if has_causal:
        causal_summary = [
            _format_causal_summary_cell(p.causal_annotations)
            for p in regime_panels
        ]
        lines.append(
            "| " + " | ".join(["Causal arrows (by kind)"] + causal_summary) + " |"
        )

    lines.append("")
    lines.append(
        "_Synthetic display only — counts of the labels emitted "
        "by the v1.16 closed-loop records under each regime "
        "preset. Not a forecast, not a price, not a "
        "recommendation._"
    )

    # v1.17.3 — per-regime causal-trace block under the table.
    if has_events or has_causal:
        for regime_panel in regime_panels:
            if (
                not regime_panel.event_annotations
                and not regime_panel.causal_annotations
            ):
                continue
            lines.append("")
            lines.append(
                f"### {regime_panel.regime_id} — events & causal trace"
            )
            if regime_panel.event_annotations:
                lines.append("")
                lines.append("Top events:")
                lines.append("")
                top_n = sorted(
                    regime_panel.event_annotations,
                    key=lambda e: (
                        e.annotation_date,
                        e.annotation_type_label,
                        e.annotation_id,
                    ),
                )[: _MAX_EVENTS_PER_REGIME_IN_MARKDOWN]
                for ev in top_n:
                    src = (
                        ev.source_record_ids[0]
                        if ev.source_record_ids
                        else "—"
                    )
                    lines.append(
                        f"- {ev.annotation_date} · "
                        f"{ev.annotation_type_label} · "
                        f"{ev.severity_label} · "
                        f"`{src}` — {ev.annotation_label}"
                    )
            if regime_panel.causal_annotations:
                lines.append("")
                lines.append("Causal arrows:")
                lines.append("")
                top_n_causal = sorted(
                    regime_panel.causal_annotations,
                    key=lambda c: (
                        c.annotation_date,
                        c.causal_summary_label,
                        c.causal_annotation_id,
                    ),
                )[: _MAX_EVENTS_PER_REGIME_IN_MARKDOWN]
                for ca in top_n_causal:
                    first_src = (
                        ca.source_record_ids[0]
                        if ca.source_record_ids
                        else "—"
                    )
                    first_dst = (
                        ca.downstream_record_ids[0]
                        if ca.downstream_record_ids
                        else "—"
                    )
                    lines.append(
                        f"- {ca.annotation_date} · "
                        f"{ca.causal_summary_label} · "
                        f"`{first_src}` → `{first_dst}` — "
                        f"{ca.event_label}"
                    )

    lines.append("")
    return "\n".join(lines)
