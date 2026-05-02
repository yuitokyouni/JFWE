"""
v1.10.1 StewardshipThemeRecord + StewardshipBook.

Implements the first concrete primitive of the v1.10 engagement /
strategic-response layer named in
``docs/v1_10_universal_engagement_and_response_design.md`` and in §70
of ``world_model.md``:

- ``StewardshipThemeRecord`` — a single immutable, append-only record
  naming an *active* stewardship theme that an investor / asset
  owner / steward declares it is *prepared to raise* across portfolio
  companies in a given period.
- ``StewardshipBook`` — append-only storage with read-only listings,
  a date-windowed active-themes view, and a deterministic snapshot.

Scope discipline (v1.10.1)
==========================

A ``StewardshipThemeRecord`` is a **monitoring / attention** input,
not an action. It can later feed the v1.8.5 ``ObservationMenuBuilder``,
the v1.8.5 ``AttentionBook``, the v1.10.2 portfolio-company dialogue
records, and the v1.10.3 escalation / corporate-response candidate
mechanisms. **It does not, by itself**:

- vote, file proxies, or execute any AGM / EGM action;
- engage, dialogue with, or contact any portfolio company;
- escalate any concern;
- produce any corporate-response candidate;
- recommend any investment, divestment, or weight change;
- trade, change ownership, or move any price;
- form any forecast or behavior probability;
- mutate any other source-of-truth book in the kernel.

The record fields are jurisdiction-neutral by construction. The book
refuses to validate the controlled-vocabulary fields against any
specific country, regulator, code, or named institution — those
calibrations live in v2 (Japan public-data) and beyond, not here.

Cross-references (``owner_id``, ``related_variable_ids``,
``related_signal_ids``) are recorded as data and **not** validated for
resolution against any other book, per the v0/v1 cross-reference rule
already used by ``world/attention.py`` and ``world/routines.py``.

v1.10.1 ships zero economic behavior: no price formation, no trading,
no lending decisions, no corporate actions, no policy reaction
functions, no Japan calibration, no calibrated behavior probabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, ClassVar, Iterable, Mapping

from world.clock import Clock
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class StewardshipError(Exception):
    """Base class for stewardship-layer errors."""


class DuplicateStewardshipThemeError(StewardshipError):
    """Raised when a theme_id is added twice."""


class UnknownStewardshipThemeError(StewardshipError, KeyError):
    """Raised when a theme_id is not found."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_iso_date(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise TypeError("date must be a date or ISO string")


def _coerce_optional_iso_date(value: date | str | None) -> str | None:
    if value is None:
        return None
    return _coerce_iso_date(value)


def _normalize_string_tuple(
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


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StewardshipThemeRecord:
    """
    Immutable record of one active stewardship theme.

    A theme record names that an investor / steward (the *owner*) has
    declared a particular theme active for the given period and target
    scope. The record is **monitoring / attention only**: it is the
    input shape that the v1.10.2 dialogue records, the v1.10.3
    escalation / corporate-response candidate mechanisms, and any
    future v1.8.5 attention-layer integration may read.

    Field semantics
    ---------------
    - ``theme_id`` is the stable id; unique within a
      ``StewardshipBook``. Themes are append-only — a theme is never
      mutated in place; instead, a new theme record is added (with a
      different ``theme_id``) when the steward's stance changes.
    - ``owner_id`` and ``owner_type`` name the investor / asset owner
      / steward. Free-form strings; cross-references are recorded as
      data and not validated against the registry.
    - ``theme_type`` is a free-form controlled-vocabulary tag; the
      project will grow the vocabulary milestone by milestone.
      Suggested generic, jurisdiction-neutral labels:
      ``"capital_allocation_discipline"``, ``"governance_structure"``,
      ``"disclosure_quality"``, ``"operational_efficiency"``,
      ``"sustainability_practice"``. v1.10.1 stores the tag without
      enforcing membership in any specific list.
    - ``title`` is a short jurisdiction-neutral label.
    - ``description`` is free-form, jurisdiction-neutral prose
      describing the theme. v1.10.1 does not parse or interpret it.
    - ``target_scope`` is a free-form controlled-vocabulary tag
      naming the scope at which the theme applies. Suggested generic
      labels: ``"all_holdings"``, ``"top_holdings"``,
      ``"sector_subset"``, ``"single_firm"``. v1.10.1 stores the tag
      without enforcing membership in any specific list.
    - ``priority`` is a small enumerated tag indicating the steward's
      illustrative importance ordering. Recommended values:
      ``"low"`` / ``"medium"`` / ``"high"``. **Never** a calibrated
      probability — explicit illustrative ordering only.
    - ``horizon`` is a free-form label naming the theme's horizon
      class. Recommended: ``"short_term"`` / ``"medium_term"`` /
      ``"long_term"``.
    - ``status`` is a small free-form tag tracking the theme's
      lifecycle stage in the steward's own framing. Recommended:
      ``"draft"`` / ``"active"`` / ``"under_review"`` /
      ``"retired"``. ``"retired"`` themes remain in the book for
      audit; the active-window predicate handles them via
      ``effective_to``.
    - ``effective_from`` is a required ISO ``YYYY-MM-DD`` date naming
      the period from which the theme is active.
    - ``effective_to`` is an optional ISO ``YYYY-MM-DD`` date naming
      the period after which the theme is no longer active. ``None``
      means "no declared end" — the theme is treated as active from
      ``effective_from`` onward by ``list_active_as_of`` until an
      explicit retirement date is recorded.
    - ``related_variable_ids`` and ``related_signal_ids`` are tuples
      of free-form strings that the steward declares are related to
      this theme. Cross-references are stored as data and not
      validated against ``WorldVariableBook`` / ``SignalBook`` — the
      v0/v1 cross-reference rule already used by ``world/attention.py``.
    - ``metadata`` is free-form for provenance, parameters, and
      owner notes.
    """

    theme_id: str
    owner_id: str
    owner_type: str
    theme_type: str
    title: str
    target_scope: str
    priority: str
    horizon: str
    status: str
    effective_from: str
    description: str = ""
    effective_to: str | None = None
    related_variable_ids: tuple[str, ...] = field(default_factory=tuple)
    related_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "theme_id",
        "owner_id",
        "owner_type",
        "theme_type",
        "title",
        "target_scope",
        "priority",
        "horizon",
        "status",
        "effective_from",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "related_variable_ids",
        "related_signal_ids",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, (str, date)) or (
                isinstance(value, str) and not value
            ):
                raise ValueError(f"{name} is required")

        if not isinstance(self.description, str):
            raise ValueError("description must be a string")

        if self.effective_to is not None and not isinstance(
            self.effective_to, (str, date)
        ):
            raise ValueError(
                "effective_to must be a date, ISO string, or None"
            )

        object.__setattr__(
            self, "effective_from", _coerce_iso_date(self.effective_from)
        )
        object.__setattr__(
            self,
            "effective_to",
            _coerce_optional_iso_date(self.effective_to),
        )

        if (
            self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError(
                "effective_to must be on or after effective_from"
            )

        for tuple_field_name in self.TUPLE_FIELDS:
            value = getattr(self, tuple_field_name)
            normalized = _normalize_string_tuple(
                value, field_name=tuple_field_name
            )
            object.__setattr__(self, tuple_field_name, normalized)

        object.__setattr__(self, "metadata", dict(self.metadata))

    def is_active_on(self, on_date: date | str) -> bool:
        """
        Return ``True`` iff the theme's active window contains
        ``on_date``.

        Window semantics: ``[effective_from, effective_to]`` inclusive
        on both ends. ``effective_to=None`` means "no declared end"
        (open-ended right side). The check is purely on the dates;
        ``status`` is not consulted — a record with status
        ``"retired"`` and no ``effective_to`` is still treated as
        active on every date >= ``effective_from`` until an explicit
        end date is recorded. The book's ``list_by_status`` filter is
        the natural complement when the caller wants status-based
        semantics.
        """
        target = _coerce_iso_date(on_date)
        if target < self.effective_from:
            return False
        if self.effective_to is not None and target > self.effective_to:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "owner_id": self.owner_id,
            "owner_type": self.owner_type,
            "theme_type": self.theme_type,
            "title": self.title,
            "description": self.description,
            "target_scope": self.target_scope,
            "priority": self.priority,
            "horizon": self.horizon,
            "status": self.status,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "related_variable_ids": list(self.related_variable_ids),
            "related_signal_ids": list(self.related_signal_ids),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class StewardshipBook:
    """
    Append-only storage for ``StewardshipThemeRecord`` instances.

    The book emits exactly one ledger record per ``add_theme`` call
    (``RecordType.STEWARDSHIP_THEME_ADDED``) and refuses to mutate any
    other source-of-truth book in the kernel. v1.10.1 ships storage
    and read-only listings only — no automatic theme inference, no
    engagement execution, no escalation, no corporate-response
    generation, no economic behavior.

    Cross-references (``owner_id``, ``related_variable_ids``,
    ``related_signal_ids``) are recorded as data and not validated
    against any other book, per the v0/v1 cross-reference rule.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _themes: dict[str, StewardshipThemeRecord] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_theme(
        self, theme: StewardshipThemeRecord
    ) -> StewardshipThemeRecord:
        if theme.theme_id in self._themes:
            raise DuplicateStewardshipThemeError(
                f"Duplicate theme_id: {theme.theme_id}"
            )
        self._themes[theme.theme_id] = theme

        if self.ledger is not None:
            self.ledger.append(
                event_type="stewardship_theme_added",
                simulation_date=self._now(),
                object_id=theme.theme_id,
                source=theme.owner_id,
                payload={
                    "theme_id": theme.theme_id,
                    "owner_id": theme.owner_id,
                    "owner_type": theme.owner_type,
                    "theme_type": theme.theme_type,
                    "title": theme.title,
                    "target_scope": theme.target_scope,
                    "priority": theme.priority,
                    "horizon": theme.horizon,
                    "status": theme.status,
                    "effective_from": theme.effective_from,
                    "effective_to": theme.effective_to,
                    "related_variable_ids": list(theme.related_variable_ids),
                    "related_signal_ids": list(theme.related_signal_ids),
                },
                space_id="stewardship",
                agent_id=theme.owner_id,
            )
        return theme

    def get_theme(self, theme_id: str) -> StewardshipThemeRecord:
        try:
            return self._themes[theme_id]
        except KeyError as exc:
            raise UnknownStewardshipThemeError(
                f"Stewardship theme not found: {theme_id!r}"
            ) from exc

    # ------------------------------------------------------------------
    # Listings
    # ------------------------------------------------------------------

    def list_themes(self) -> tuple[StewardshipThemeRecord, ...]:
        """Every theme, in insertion order."""
        return tuple(self._themes.values())

    def list_by_owner(
        self, owner_id: str
    ) -> tuple[StewardshipThemeRecord, ...]:
        return tuple(
            theme
            for theme in self._themes.values()
            if theme.owner_id == owner_id
        )

    def list_by_owner_type(
        self, owner_type: str
    ) -> tuple[StewardshipThemeRecord, ...]:
        return tuple(
            theme
            for theme in self._themes.values()
            if theme.owner_type == owner_type
        )

    def list_by_theme_type(
        self, theme_type: str
    ) -> tuple[StewardshipThemeRecord, ...]:
        return tuple(
            theme
            for theme in self._themes.values()
            if theme.theme_type == theme_type
        )

    def list_by_status(
        self, status: str
    ) -> tuple[StewardshipThemeRecord, ...]:
        return tuple(
            theme
            for theme in self._themes.values()
            if theme.status == status
        )

    def list_by_priority(
        self, priority: str
    ) -> tuple[StewardshipThemeRecord, ...]:
        return tuple(
            theme
            for theme in self._themes.values()
            if theme.priority == priority
        )

    def list_active_as_of(
        self, as_of: date | str
    ) -> tuple[StewardshipThemeRecord, ...]:
        """
        Return every theme whose active window contains ``as_of``.

        The check is purely on dates — see
        ``StewardshipThemeRecord.is_active_on``. ``status`` is not
        consulted; combine with ``list_by_status`` if status-based
        semantics are required.
        """
        target = _coerce_iso_date(as_of)
        return tuple(
            theme
            for theme in self._themes.values()
            if theme.is_active_on(target)
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        themes = sorted(
            (t.to_dict() for t in self._themes.values()),
            key=lambda item: item["theme_id"],
        )
        return {
            "theme_count": len(themes),
            "themes": themes,
        }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()
