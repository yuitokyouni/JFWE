"""
v1.8.5 AttentionProfile + ObservationMenu + SelectedObservationSet.

Implements the kernel-level attention layer named in the v1.8.2
Interaction Topology and Attention design (§44 of
``world_model.md`` and ``docs/v1_interaction_topology_design.md``):

- ``AttentionProfile`` — what an actor *tends to* watch (heterogeneous,
  static declaration).
- ``ObservationMenu`` — what is *available* to an actor at a date /
  phase (snapshot view).
- ``SelectedObservationSet`` — what was *actually selected* from a
  menu (record of attention).

Scope discipline (v1.8.5):

- ``AttentionBook`` stores the three record types and their
  filter / lookup APIs. It does **not** execute a routine, build
  the menu's contents from other books automatically, decide what
  to select, or take any economic action.
- The Routine engine (v1.8.6+) is what will eventually consume a
  ``SelectedObservationSet`` to produce a ``RoutineRunRecord``.
  v1.8.5 only persists the records.
- Cross-references (``actor_id``, ``attention_profile_id``,
  ``menu_id``, ``routine_run_id``, ``selected_refs``,
  ``skipped_refs``, the ``available_*_ids`` tuples) are recorded as
  data and **not** validated for resolution against any other book,
  per the v0/v1 cross-reference rule.
- v1.8.5 ships zero economic behavior: no price formation, no
  trading, no lending decisions, no corporate actions, no policy
  reaction functions, no Japan calibration.

A small read-only predicate, :meth:`AttentionBook.profile_matches_menu`,
returns a structural overlap summary between a profile and a menu
without inferring economic meaning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, ClassVar, Mapping

from world.clock import Clock
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AttentionError(Exception):
    """Base class for attention-layer errors."""


class DuplicateAttentionProfileError(AttentionError):
    """Raised when a profile_id is added twice."""


class DuplicateObservationMenuError(AttentionError):
    """Raised when a menu_id is added twice."""


class DuplicateSelectedObservationSetError(AttentionError):
    """Raised when a selection_id is added twice."""


class UnknownAttentionProfileError(AttentionError, KeyError):
    """Raised when a profile_id is not found."""


class UnknownObservationMenuError(AttentionError, KeyError):
    """Raised when a menu_id is not found."""


class UnknownSelectedObservationSetError(AttentionError, KeyError):
    """Raised when a selection_id is not found."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_iso_date(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise TypeError("date must be a date or ISO string")


def _normalize_string_tuple(
    value, *, field_name: str
) -> tuple[str, ...]:
    normalized = tuple(value)
    for entry in normalized:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{field_name} entries must be non-empty strings; "
                f"got {entry!r}"
            )
    return normalized


def _normalize_priority_weights(
    value: Mapping[str, Any] | None,
) -> dict[str, float]:
    """
    Coerce ``priority_weights`` into a deterministic ``dict[str, float]``.

    Accepts a mapping; rejects non-string keys, non-numeric values,
    and bool values (bool is an int subclass; we want true numerics
    only). Returns a regular dict (not a frozen ``MappingProxyType``)
    so downstream callers can read freely; the dataclass freezes the
    enclosing record.
    """
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(
            f"priority_weights must be a mapping; got {type(value).__name__}"
        )
    out: dict[str, float] = {}
    for k, v in value.items():
        if not isinstance(k, str) or not k:
            raise ValueError(
                f"priority_weights keys must be non-empty strings; got {k!r}"
            )
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(
                f"priority_weights[{k!r}] must be numeric (int or float); "
                f"got {type(v).__name__}"
            )
        out[k] = float(v)
    return out


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttentionProfile:
    """
    Heterogeneous attention declaration for one actor.

    Field semantics
    ---------------
    - ``profile_id`` is the stable id; unique within an
      ``AttentionBook``. Multiple profiles per actor are allowed
      (a bank may have a daily liquidity profile and a quarterly
      counterparty review profile).
    - ``actor_id`` and ``actor_type`` are required, free-form
      strings naming the actor whose attention this describes.
      Cross-references stored as data; not validated against the
      registry.
    - ``watched_*`` fields are tuples of free-form strings filtering
      what the actor cares about, drawn from controlled vocabularies
      the project will grow milestone by milestone:
      ``watched_space_ids`` (v0 space ids the actor reads from);
      ``watched_subject_ids`` (specific subjects the actor focuses
      on — firm tickers, asset ids, factor ids); ``watched_signal_types``
      (filter on ``InformationSignal.signal_type``);
      ``watched_channels`` (filter on ``InteractionSpec.channel_type``
      or ``interaction_id``); ``watched_metrics`` (derived metrics
      the actor cares about, e.g. ``"earnings"``, ``"dscr"``,
      ``"valuation_gap"``); ``watched_valuation_types`` /
      ``watched_constraint_types`` / ``watched_relationship_types``
      (filters on the corresponding v1 record types).
    - ``update_frequency`` is a required free-form label naming the
      cadence at which the actor refreshes its attention. The v0
      ``Frequency`` enum values are recommended (``"DAILY"`` /
      ``"MONTHLY"`` / ``"QUARTERLY"`` / ``"YEARLY"``) but not
      enforced.
    - ``phase_id`` is an optional intraday phase label (v1.2).
    - ``priority_weights`` is a mapping ``str -> float`` carrying
      optional ranking weights (v1.8.6+ engine layers may use
      these to resolve conflicts when the menu is over-large).
      v1.8.5 stores them only.
    - ``missing_input_policy`` defaults to ``"degraded"`` — the
      v1.8.1 anti-scenario default. Free-form string; the engine
      that interprets it lives in a later milestone.
    - ``enabled`` (default ``True``) is a flag mirroring v1.8.3 /
      v1.8.4. Disabled profiles remain in the book but are excluded
      from list views unless ``include_disabled=True``.
    - ``metadata`` is free-form for provenance, parameters, and
      owner notes.
    """

    profile_id: str
    actor_id: str
    actor_type: str
    update_frequency: str
    watched_space_ids: tuple[str, ...] = field(default_factory=tuple)
    watched_subject_ids: tuple[str, ...] = field(default_factory=tuple)
    watched_signal_types: tuple[str, ...] = field(default_factory=tuple)
    watched_channels: tuple[str, ...] = field(default_factory=tuple)
    watched_metrics: tuple[str, ...] = field(default_factory=tuple)
    watched_valuation_types: tuple[str, ...] = field(default_factory=tuple)
    watched_constraint_types: tuple[str, ...] = field(default_factory=tuple)
    watched_relationship_types: tuple[str, ...] = field(default_factory=tuple)
    # v1.8.12 — explicit hooks into the v1.8.9 / v1.8.10 layers.
    # Watch preferences, NOT decisions. Cross-references are
    # recorded as data and not validated against
    # WorldVariableBook / ExposureBook (per the v0/v1
    # cross-reference rule).
    watched_variable_ids: tuple[str, ...] = field(default_factory=tuple)
    watched_variable_groups: tuple[str, ...] = field(default_factory=tuple)
    watched_exposure_types: tuple[str, ...] = field(default_factory=tuple)
    watched_exposure_metrics: tuple[str, ...] = field(default_factory=tuple)
    phase_id: str | None = None
    priority_weights: Mapping[str, float] = field(default_factory=dict)
    missing_input_policy: str = "degraded"
    enabled: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id:
            raise ValueError("profile_id is required")
        if not isinstance(self.actor_id, str) or not self.actor_id:
            raise ValueError("actor_id is required")
        if not isinstance(self.actor_type, str) or not self.actor_type:
            raise ValueError("actor_type is required")
        if not isinstance(self.update_frequency, str) or not self.update_frequency:
            raise ValueError("update_frequency is required")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a bool")
        if (
            not isinstance(self.missing_input_policy, str)
            or not self.missing_input_policy
        ):
            raise ValueError("missing_input_policy is required")
        if self.phase_id is not None and not (
            isinstance(self.phase_id, str) and self.phase_id
        ):
            raise ValueError(
                "phase_id must be a non-empty string or None"
            )

        for tuple_field_name in (
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
        ):
            value = getattr(self, tuple_field_name)
            normalized = _normalize_string_tuple(
                value, field_name=tuple_field_name
            )
            object.__setattr__(self, tuple_field_name, normalized)

        object.__setattr__(
            self,
            "priority_weights",
            _normalize_priority_weights(self.priority_weights),
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "update_frequency": self.update_frequency,
            "phase_id": self.phase_id,
            "watched_space_ids": list(self.watched_space_ids),
            "watched_subject_ids": list(self.watched_subject_ids),
            "watched_signal_types": list(self.watched_signal_types),
            "watched_channels": list(self.watched_channels),
            "watched_metrics": list(self.watched_metrics),
            "watched_valuation_types": list(self.watched_valuation_types),
            "watched_constraint_types": list(self.watched_constraint_types),
            "watched_relationship_types": list(self.watched_relationship_types),
            "watched_variable_ids": list(self.watched_variable_ids),
            "watched_variable_groups": list(self.watched_variable_groups),
            "watched_exposure_types": list(self.watched_exposure_types),
            "watched_exposure_metrics": list(self.watched_exposure_metrics),
            "priority_weights": dict(self.priority_weights),
            "missing_input_policy": self.missing_input_policy,
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ObservationMenu:
    """
    What is *available* to an actor at a date / phase.

    A menu is a **snapshot view**. v1.8.5 stores menus that callers
    construct; it does not build menu contents automatically from
    other books. Empty or partial menus are normal — a menu with all
    ``available_*`` lists empty is a valid recorded state ("nothing
    visible to this actor at this date / phase"), not an error.

    The menu does not select. It does not infer economic meaning.
    Selection is recorded separately as a ``SelectedObservationSet``.
    """

    menu_id: str
    actor_id: str
    as_of_date: str
    phase_id: str | None = None
    available_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    available_valuation_ids: tuple[str, ...] = field(default_factory=tuple)
    available_constraint_ids: tuple[str, ...] = field(default_factory=tuple)
    available_relationship_ids: tuple[str, ...] = field(default_factory=tuple)
    available_price_ids: tuple[str, ...] = field(default_factory=tuple)
    available_external_observation_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    available_interaction_ids: tuple[str, ...] = field(default_factory=tuple)
    available_variable_observation_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    available_exposure_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    AVAILABLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "available_signal_ids",
        "available_valuation_ids",
        "available_constraint_ids",
        "available_relationship_ids",
        "available_price_ids",
        "available_external_observation_ids",
        "available_interaction_ids",
        "available_variable_observation_ids",
        "available_exposure_ids",
    )

    def __post_init__(self) -> None:
        if not isinstance(self.menu_id, str) or not self.menu_id:
            raise ValueError("menu_id is required")
        if not isinstance(self.actor_id, str) or not self.actor_id:
            raise ValueError("actor_id is required")
        if not isinstance(self.as_of_date, (str, date)) or (
            isinstance(self.as_of_date, str) and not self.as_of_date
        ):
            raise ValueError("as_of_date is required")
        if self.phase_id is not None and not (
            isinstance(self.phase_id, str) and self.phase_id
        ):
            raise ValueError(
                "phase_id must be a non-empty string or None"
            )

        object.__setattr__(self, "as_of_date", _coerce_iso_date(self.as_of_date))

        for tuple_field_name in self.AVAILABLE_FIELDS:
            value = getattr(self, tuple_field_name)
            normalized = _normalize_string_tuple(
                value, field_name=tuple_field_name
            )
            object.__setattr__(self, tuple_field_name, normalized)

        object.__setattr__(self, "metadata", dict(self.metadata))

    def total_available_count(self) -> int:
        return sum(
            len(getattr(self, name)) for name in self.AVAILABLE_FIELDS
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "menu_id": self.menu_id,
            "actor_id": self.actor_id,
            "as_of_date": self.as_of_date,
            "phase_id": self.phase_id,
            "available_signal_ids": list(self.available_signal_ids),
            "available_valuation_ids": list(self.available_valuation_ids),
            "available_constraint_ids": list(self.available_constraint_ids),
            "available_relationship_ids": list(self.available_relationship_ids),
            "available_price_ids": list(self.available_price_ids),
            "available_external_observation_ids": list(
                self.available_external_observation_ids
            ),
            "available_interaction_ids": list(self.available_interaction_ids),
            "available_variable_observation_ids": list(
                self.available_variable_observation_ids
            ),
            "available_exposure_ids": list(self.available_exposure_ids),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SelectedObservationSet:
    """
    What an actor *actually selected* from a menu.

    Persisted to the ledger so a future ``RoutineRunRecord`` can
    point at it via ``input_refs`` or via the ``routine_run_id``
    backlink stored here.

    A ``SelectedObservationSet`` is **not an economic action**. It
    records attention, not decision: the actor consumed these
    references in this run. Routines that act on selections (place
    trades, change lending terms, reprice contracts, file corporate
    actions) are out of scope for v1.8.5 — and out of scope for
    every milestone before v2 / v3 calibration.

    Field semantics
    ---------------
    - ``selection_id`` is the stable id; unique within an
      ``AttentionBook``.
    - ``actor_id`` mirrors the profile / menu actor.
    - ``attention_profile_id`` references the profile that drove
      the selection.
    - ``menu_id`` references the menu the selection was drawn from.
    - ``routine_run_id`` optionally links the selection to a
      ``RoutineRunRecord`` (forward-pointer; v1.8.5 stores the
      string but does not validate the link).
    - ``selected_refs`` are the record ids selected. v1.8.5 does
      **not** enforce that they are a subset of the menu's
      ``available_*_ids`` — the predicate is too speculative for a
      storage milestone, and the engine layer that consumes the
      selection can enforce it if it wishes. Stored deterministically
      as a tuple of strings (declaration order preserved).
    - ``skipped_refs`` are ids that were considered and intentionally
      skipped (e.g., already consumed in a prior run, low priority
      weight). Same storage discipline as ``selected_refs``.
    - ``selection_reason`` is a free-form label; suggested
      vocabulary: ``"profile_match"`` / ``"priority_top_k"`` /
      ``"recency"`` / ``"explicit"`` / ``"degraded_no_input"``.
    - ``as_of_date`` is ISO ``YYYY-MM-DD``.
    - ``phase_id`` is optional intraday phase.
    - ``status`` is free-form; recommended vocabulary:
      ``"completed"`` / ``"partial"`` / ``"degraded"`` /
      ``"empty"``. ``"empty"`` is a valid recorded state — it
      preserves the v1.8.1 anti-scenario discipline (the actor
      looked, found nothing relevant, and that is itself a valid
      audit fact).
    - ``metadata`` is free-form. Callers that want to carry
      ``parent_record_ids`` (e.g., when a selection is causally
      linked to a prior ledger record) put them under
      ``metadata["parent_record_ids"]``; v1.8.5 does not invent a
      dedicated field.
    """

    selection_id: str
    actor_id: str
    attention_profile_id: str
    menu_id: str
    selection_reason: str
    as_of_date: str
    status: str
    routine_run_id: str | None = None
    selected_refs: tuple[str, ...] = field(default_factory=tuple)
    skipped_refs: tuple[str, ...] = field(default_factory=tuple)
    phase_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.selection_id, str) or not self.selection_id:
            raise ValueError("selection_id is required")
        if not isinstance(self.actor_id, str) or not self.actor_id:
            raise ValueError("actor_id is required")
        if (
            not isinstance(self.attention_profile_id, str)
            or not self.attention_profile_id
        ):
            raise ValueError("attention_profile_id is required")
        if not isinstance(self.menu_id, str) or not self.menu_id:
            raise ValueError("menu_id is required")
        if (
            not isinstance(self.selection_reason, str)
            or not self.selection_reason
        ):
            raise ValueError("selection_reason is required")
        if not isinstance(self.as_of_date, (str, date)) or (
            isinstance(self.as_of_date, str) and not self.as_of_date
        ):
            raise ValueError("as_of_date is required")
        if not isinstance(self.status, str) or not self.status:
            raise ValueError("status is required")
        if self.routine_run_id is not None and not (
            isinstance(self.routine_run_id, str) and self.routine_run_id
        ):
            raise ValueError(
                "routine_run_id must be a non-empty string or None"
            )
        if self.phase_id is not None and not (
            isinstance(self.phase_id, str) and self.phase_id
        ):
            raise ValueError(
                "phase_id must be a non-empty string or None"
            )

        object.__setattr__(self, "as_of_date", _coerce_iso_date(self.as_of_date))

        for tuple_field_name in ("selected_refs", "skipped_refs"):
            value = getattr(self, tuple_field_name)
            normalized = _normalize_string_tuple(
                value, field_name=tuple_field_name
            )
            object.__setattr__(self, tuple_field_name, normalized)

        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_id": self.selection_id,
            "actor_id": self.actor_id,
            "attention_profile_id": self.attention_profile_id,
            "menu_id": self.menu_id,
            "routine_run_id": self.routine_run_id,
            "selection_reason": self.selection_reason,
            "as_of_date": self.as_of_date,
            "phase_id": self.phase_id,
            "selected_refs": list(self.selected_refs),
            "skipped_refs": list(self.skipped_refs),
            "status": self.status,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


# Mapping from AttentionProfile.watched_* dimension to the
# ObservationMenu.available_* field that holds the corresponding
# refs. Used by ``profile_matches_menu`` to compute structural
# overlap without inferring economic meaning.
_DIMENSION_TO_MENU_FIELD: tuple[tuple[str, str], ...] = (
    ("watched_signal_types", "available_signal_ids"),
    ("watched_valuation_types", "available_valuation_ids"),
    ("watched_constraint_types", "available_constraint_ids"),
    ("watched_relationship_types", "available_relationship_ids"),
    ("watched_channels", "available_interaction_ids"),
    # v1.8.12 hooks: profiles can declare interest in specific
    # variables (by id or group) and exposures (by type or metric).
    # The structural overlap predicate just reports counts; it
    # does not read the underlying records.
    ("watched_variable_ids", "available_variable_observation_ids"),
    ("watched_variable_groups", "available_variable_observation_ids"),
    ("watched_exposure_types", "available_exposure_ids"),
    ("watched_exposure_metrics", "available_exposure_ids"),
)


@dataclass
class AttentionBook:
    """
    Storage for ``AttentionProfile``, ``ObservationMenu``, and
    ``SelectedObservationSet`` records.

    The book is append-only, emits ledger records on each insert,
    and refuses to mutate any other source-of-truth book. v1.8.5
    ships storage and lookup only — no automatic menu construction,
    no selection logic, no routine execution, no economic behavior.

    Cross-references are recorded as data and not validated against
    any other book. The single helper that touches another book is
    :meth:`profile_matches_menu`, which is a pure read returning a
    structural overlap summary.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _profiles: dict[str, AttentionProfile] = field(default_factory=dict)
    _menus: dict[str, ObservationMenu] = field(default_factory=dict)
    _selections: dict[str, SelectedObservationSet] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Profile CRUD
    # ------------------------------------------------------------------

    def add_profile(self, profile: AttentionProfile) -> AttentionProfile:
        if profile.profile_id in self._profiles:
            raise DuplicateAttentionProfileError(
                f"Duplicate profile_id: {profile.profile_id}"
            )
        self._profiles[profile.profile_id] = profile

        if self.ledger is not None:
            self.ledger.append(
                event_type="attention_profile_added",
                simulation_date=self._now(),
                object_id=profile.profile_id,
                source=profile.actor_id,
                payload={
                    "profile_id": profile.profile_id,
                    "actor_id": profile.actor_id,
                    "actor_type": profile.actor_type,
                    "update_frequency": profile.update_frequency,
                    "phase_id": profile.phase_id,
                    "enabled": profile.enabled,
                    "missing_input_policy": profile.missing_input_policy,
                    "watched_space_ids": list(profile.watched_space_ids),
                    "watched_subject_ids": list(profile.watched_subject_ids),
                    "watched_signal_types": list(profile.watched_signal_types),
                    "watched_channels": list(profile.watched_channels),
                    "watched_metrics": list(profile.watched_metrics),
                    "watched_valuation_types": list(
                        profile.watched_valuation_types
                    ),
                    "watched_constraint_types": list(
                        profile.watched_constraint_types
                    ),
                    "watched_relationship_types": list(
                        profile.watched_relationship_types
                    ),
                    "watched_variable_ids": list(profile.watched_variable_ids),
                    "watched_variable_groups": list(
                        profile.watched_variable_groups
                    ),
                    "watched_exposure_types": list(
                        profile.watched_exposure_types
                    ),
                    "watched_exposure_metrics": list(
                        profile.watched_exposure_metrics
                    ),
                    "priority_weights": dict(profile.priority_weights),
                },
                space_id="attention",
                agent_id=profile.actor_id,
            )
        return profile

    def get_profile(self, profile_id: str) -> AttentionProfile:
        try:
            return self._profiles[profile_id]
        except KeyError as exc:
            raise UnknownAttentionProfileError(
                f"Attention profile not found: {profile_id!r}"
            ) from exc

    def list_profiles(
        self, *, include_disabled: bool = False
    ) -> tuple[AttentionProfile, ...]:
        return tuple(
            self._filter_profiles(self._profiles.values(), include_disabled)
        )

    def list_profiles_by_actor(
        self, actor_id: str, *, include_disabled: bool = False
    ) -> tuple[AttentionProfile, ...]:
        return tuple(
            self._filter_profiles(
                (
                    p
                    for p in self._profiles.values()
                    if p.actor_id == actor_id
                ),
                include_disabled,
            )
        )

    def list_profiles_by_actor_type(
        self, actor_type: str, *, include_disabled: bool = False
    ) -> tuple[AttentionProfile, ...]:
        return tuple(
            self._filter_profiles(
                (
                    p
                    for p in self._profiles.values()
                    if p.actor_type == actor_type
                ),
                include_disabled,
            )
        )

    def list_profiles_by_watched_space(
        self, space_id: str, *, include_disabled: bool = False
    ) -> tuple[AttentionProfile, ...]:
        return tuple(
            self._filter_profiles(
                (
                    p
                    for p in self._profiles.values()
                    if space_id in p.watched_space_ids
                ),
                include_disabled,
            )
        )

    def list_profiles_by_channel(
        self, channel: str, *, include_disabled: bool = False
    ) -> tuple[AttentionProfile, ...]:
        return tuple(
            self._filter_profiles(
                (
                    p
                    for p in self._profiles.values()
                    if channel in p.watched_channels
                ),
                include_disabled,
            )
        )

    # ------------------------------------------------------------------
    # Observation menu CRUD
    # ------------------------------------------------------------------

    def add_menu(self, menu: ObservationMenu) -> ObservationMenu:
        if menu.menu_id in self._menus:
            raise DuplicateObservationMenuError(
                f"Duplicate menu_id: {menu.menu_id}"
            )
        self._menus[menu.menu_id] = menu

        if self.ledger is not None:
            self.ledger.append(
                event_type="observation_menu_created",
                simulation_date=menu.as_of_date,
                object_id=menu.menu_id,
                source=menu.actor_id,
                payload={
                    "menu_id": menu.menu_id,
                    "actor_id": menu.actor_id,
                    "as_of_date": menu.as_of_date,
                    "phase_id": menu.phase_id,
                    "available_signal_count": len(menu.available_signal_ids),
                    "available_valuation_count": len(
                        menu.available_valuation_ids
                    ),
                    "available_constraint_count": len(
                        menu.available_constraint_ids
                    ),
                    "available_relationship_count": len(
                        menu.available_relationship_ids
                    ),
                    "available_price_count": len(menu.available_price_ids),
                    "available_external_observation_count": len(
                        menu.available_external_observation_ids
                    ),
                    "available_interaction_count": len(
                        menu.available_interaction_ids
                    ),
                    "available_variable_observation_count": len(
                        menu.available_variable_observation_ids
                    ),
                    "available_exposure_count": len(
                        menu.available_exposure_ids
                    ),
                    "total_available_count": menu.total_available_count(),
                },
                space_id="attention",
                agent_id=menu.actor_id,
            )
        return menu

    def get_menu(self, menu_id: str) -> ObservationMenu:
        try:
            return self._menus[menu_id]
        except KeyError as exc:
            raise UnknownObservationMenuError(
                f"Observation menu not found: {menu_id!r}"
            ) from exc

    def list_menus_by_actor(
        self, actor_id: str
    ) -> tuple[ObservationMenu, ...]:
        return tuple(
            menu
            for menu in self._menus.values()
            if menu.actor_id == actor_id
        )

    def list_menus_by_date(
        self, as_of_date: date | str
    ) -> tuple[ObservationMenu, ...]:
        target = _coerce_iso_date(as_of_date)
        return tuple(
            menu
            for menu in self._menus.values()
            if menu.as_of_date == target
        )

    # ------------------------------------------------------------------
    # Selected observation set CRUD
    # ------------------------------------------------------------------

    def add_selection(
        self, selection: SelectedObservationSet
    ) -> SelectedObservationSet:
        if selection.selection_id in self._selections:
            raise DuplicateSelectedObservationSetError(
                f"Duplicate selection_id: {selection.selection_id}"
            )
        self._selections[selection.selection_id] = selection

        if self.ledger is not None:
            self.ledger.append(
                event_type="observation_set_selected",
                simulation_date=selection.as_of_date,
                object_id=selection.selection_id,
                source=selection.actor_id,
                target=selection.menu_id,
                payload={
                    "selection_id": selection.selection_id,
                    "actor_id": selection.actor_id,
                    "attention_profile_id": selection.attention_profile_id,
                    "menu_id": selection.menu_id,
                    "routine_run_id": selection.routine_run_id,
                    "selection_reason": selection.selection_reason,
                    "as_of_date": selection.as_of_date,
                    "phase_id": selection.phase_id,
                    "status": selection.status,
                    "selected_count": len(selection.selected_refs),
                    "skipped_count": len(selection.skipped_refs),
                    "selected_refs": list(selection.selected_refs),
                    "skipped_refs": list(selection.skipped_refs),
                },
                space_id="attention",
                agent_id=selection.actor_id,
                correlation_id=selection.routine_run_id,
            )
        return selection

    def get_selection(self, selection_id: str) -> SelectedObservationSet:
        try:
            return self._selections[selection_id]
        except KeyError as exc:
            raise UnknownSelectedObservationSetError(
                f"Selected observation set not found: {selection_id!r}"
            ) from exc

    def list_selections_by_actor(
        self, actor_id: str
    ) -> tuple[SelectedObservationSet, ...]:
        return tuple(
            sel
            for sel in self._selections.values()
            if sel.actor_id == actor_id
        )

    def list_selections_by_profile(
        self, profile_id: str
    ) -> tuple[SelectedObservationSet, ...]:
        return tuple(
            sel
            for sel in self._selections.values()
            if sel.attention_profile_id == profile_id
        )

    def list_selections_by_menu(
        self, menu_id: str
    ) -> tuple[SelectedObservationSet, ...]:
        return tuple(
            sel
            for sel in self._selections.values()
            if sel.menu_id == menu_id
        )

    def list_selections_by_status(
        self, status: str
    ) -> tuple[SelectedObservationSet, ...]:
        return tuple(
            sel
            for sel in self._selections.values()
            if sel.status == status
        )

    # ------------------------------------------------------------------
    # Predicate
    # ------------------------------------------------------------------

    def profile_matches_menu(
        self, profile_id: str, menu_id: str
    ) -> dict[str, Any]:
        """
        Return a **structural overlap summary** between an
        ``AttentionProfile`` and an ``ObservationMenu``, without
        inferring economic meaning.

        The returned dict has these keys:

        - ``profile_id``, ``menu_id`` — echoed back for the caller.
        - ``has_any_overlap`` (``bool``) — ``True`` if any of the
          dimensions below is non-empty *and* the menu carries at
          least one available item in that dimension.
        - ``per_dimension`` (``dict[str, dict]``) — for each
          (watched-dimension, menu-field) pair, a sub-dict with
          ``watched_count`` (size of the profile's watched filter)
          and ``menu_available_count`` (size of the menu's
          corresponding availability list). Only dimensions where
          the profile has a non-empty watched filter are included.

        v1.8.5 deliberately does **not** check whether each
        available id has a *type* matching the profile's filter —
        that requires reading the underlying record books and is
        deferred to the v1.8.6 engine layer. The summary is
        therefore conservative: it tells the caller "is there
        structural potential for overlap?" not "are these specific
        records relevant?"

        Raises ``UnknownAttentionProfileError`` /
        ``UnknownObservationMenuError`` if either id is missing.
        """
        profile = self.get_profile(profile_id)
        menu = self.get_menu(menu_id)

        per_dimension: dict[str, dict[str, int]] = {}
        has_any_overlap = False
        for watched_field, menu_field in _DIMENSION_TO_MENU_FIELD:
            watched = getattr(profile, watched_field)
            available = getattr(menu, menu_field)
            if not watched:
                continue
            wcount = len(watched)
            mcount = len(available)
            per_dimension[watched_field] = {
                "watched_count": wcount,
                "menu_available_count": mcount,
            }
            if mcount > 0:
                has_any_overlap = True

        return {
            "profile_id": profile_id,
            "menu_id": menu_id,
            "has_any_overlap": has_any_overlap,
            "per_dimension": per_dimension,
        }

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        profiles = sorted(
            (p.to_dict() for p in self._profiles.values()),
            key=lambda item: item["profile_id"],
        )
        menus = sorted(
            (m.to_dict() for m in self._menus.values()),
            key=lambda item: item["menu_id"],
        )
        selections = sorted(
            (s.to_dict() for s in self._selections.values()),
            key=lambda item: item["selection_id"],
        )
        return {
            "profile_count": len(profiles),
            "enabled_profile_count": sum(
                1 for p in self._profiles.values() if p.enabled
            ),
            "menu_count": len(menus),
            "selection_count": len(selections),
            "profiles": profiles,
            "menus": menus,
            "selections": selections,
        }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_profiles(profiles, include_disabled: bool):
        for p in profiles:
            if include_disabled or p.enabled:
                yield p

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()
