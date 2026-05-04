"""
v1.20.2 — Scenario schedule storage.

Storage-only foundation for the v1.20 monthly scenario
reference universe's scheduling layer. v1.20.2 ships two
immutable frozen dataclasses (:class:`ScenarioSchedule`,
:class:`ScheduledScenarioApplication`), one append-only
:class:`ScenarioScheduleBook`, six closed-set vocabularies, and
one deterministic helper
(:func:`build_default_scenario_monthly_schedule`) that
constructs the v1.20.0 default single-scenario schedule
**without** registering anything on a kernel.

Critical design constraints carried verbatim from v1.20.0
(binding):

- Storage only. v1.20.2 does **not** ship the
  ``scenario_monthly_reference_universe`` run profile (that
  lands at v1.20.3). It does **not** apply scenarios. It does
  **not** mutate the ``PriceBook`` or any other source-of-
  truth book. It does **not** decide actor behaviour.
- Empty by default on the kernel. The new
  :class:`WorldKernel.scenario_schedule` field is wired with
  ``field(default_factory=ScenarioScheduleBook)``; empty book
  → no ledger emission → byte-identical ``quarterly_default``
  (`f93bdf3f…b705897c`) and ``monthly_reference``
  (`75a91cfa…91879d`) digests.
- References are plain ids only. ``scenario_driver_template_ids``,
  ``affected_reference_universe_id``, ``affected_sector_ids``,
  and ``affected_firm_profile_ids`` carry plain-id citations
  to records the v1.18.1 / v1.20.1 storage books may or may
  not contain. The storage layer does **not** resolve / validate
  these references — v1.20.3 will check them at run-profile
  execution time.
- The future-LLM-compatibility audit shape pinned at v1.18.0
  carries forward — ``reasoning_mode = "rule_based_fallback"``
  remains binding at v1.20.x. v1.20.2 is storage-only and does
  not yet consume the audit shape, but the
  :data:`FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES` frozenset
  extends the v1.18.0 actor-decision / forecast / advice
  forbidden list with the v1.20.0-pinned licensed-taxonomy /
  real-data tokens (``gics`` / ``msci`` / ``factset`` /
  ``bloomberg`` / ``refinitiv`` / ``topix`` / ``nikkei`` /
  ``jpx`` / ``real_company_name`` / etc.).

The module is **runtime-book-free** beyond the v0/v1 ledger +
clock convention shared by every other storage book — it does
not import any source-of-truth book on the engine side.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Iterable, Mapping

from world.clock import Clock
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Closed-set vocabularies
# ---------------------------------------------------------------------------


RUN_PROFILE_LABELS: frozenset[str] = frozenset(
    {
        "scenario_monthly_reference_universe",
        "monthly_reference",
        "scenario_monthly",
        "quarterly_default",
        "unknown",
    }
)


SCHEDULE_POLICY_LABELS: frozenset[str] = frozenset(
    {
        "single_scenario",
        "multi_scenario_bounded",
        "display_only",
        "inactive",
        "unknown",
    }
)


APPLICATION_POLICY_LABELS: frozenset[str] = frozenset(
    {
        "apply_at_period_start",
        "apply_before_information_arrivals",
        "apply_after_information_arrivals",
        "apply_before_attention_update",
        "display_only",
        "unknown",
    }
)


SCHEDULED_MONTH_LABELS: frozenset[str] = frozenset(
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


# Bounds for monthly profile period indices (0-11).
MONTHLY_PERIOD_INDEX_MIN: int = 0
MONTHLY_PERIOD_INDEX_MAX: int = 11


# v1.20.0 hard naming boundary on payload + metadata. Tests
# scan dataclass field names, payload keys, and metadata keys
# for any of the forbidden names below. The set composes the
# v1.18.0 actor-decision tokens, the v1.17.0 forbidden display
# names, the v1.19.3 Japan-real-data tokens, and the v1.20.0-
# pinned licensed-taxonomy / real-financial tokens.
FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES: frozenset[str] = frozenset(
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
        "gics",
        "msci",
        "factset",
        "bloomberg",
        "refinitiv",
        "topix",
        "nikkei",
        "jpx",
    }
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ScenarioScheduleError(Exception):
    """Base class for v1.20.2 scenario-schedule errors."""


class DuplicateScenarioScheduleError(ScenarioScheduleError):
    """Raised when a scenario_schedule_id is added twice."""


class DuplicateScheduledScenarioApplicationError(
    ScenarioScheduleError
):
    """Raised when a scheduled_scenario_application_id is added
    twice."""


class UnknownScenarioScheduleError(
    ScenarioScheduleError, KeyError
):
    """Raised when a scenario_schedule_id is not found."""


class UnknownScheduledScenarioApplicationError(
    ScenarioScheduleError, KeyError
):
    """Raised when a scheduled_scenario_application_id is not
    found."""


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


def _validate_label_tuple(
    value: Iterable[str],
    allowed: frozenset[str],
    *,
    field_name: str,
) -> tuple[str, ...]:
    normalized = tuple(value)
    for entry in normalized:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{field_name} entries must be non-empty strings; "
                f"got {entry!r}"
            )
        if entry not in allowed:
            raise ValueError(
                f"{field_name} entry {entry!r} not in "
                f"{sorted(allowed)!r}"
            )
    return normalized


def _validate_period_index_tuple(
    value: Iterable[int], *, field_name: str
) -> tuple[int, ...]:
    """Each entry is an int in ``[MONTHLY_PERIOD_INDEX_MIN,
    MONTHLY_PERIOD_INDEX_MAX]``. Reject ``bool`` (which is
    otherwise a subclass of ``int``)."""
    normalized = tuple(value)
    out: list[int] = []
    for entry in normalized:
        if isinstance(entry, bool) or not isinstance(entry, int):
            raise ValueError(
                f"{field_name} entries must be int (not bool); "
                f"got {type(entry).__name__}"
            )
        if (
            entry < MONTHLY_PERIOD_INDEX_MIN
            or entry > MONTHLY_PERIOD_INDEX_MAX
        ):
            raise ValueError(
                f"{field_name} entry {entry!r} out of range "
                f"[{MONTHLY_PERIOD_INDEX_MIN}, "
                f"{MONTHLY_PERIOD_INDEX_MAX}]"
            )
        out.append(entry)
    return tuple(out)


def _validate_period_index(
    value: Any, *, field_name: str
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"{field_name} must be int (not bool); "
            f"got {type(value).__name__}"
        )
    if (
        value < MONTHLY_PERIOD_INDEX_MIN
        or value > MONTHLY_PERIOD_INDEX_MAX
    ):
        raise ValueError(
            f"{field_name} out of range "
            f"[{MONTHLY_PERIOD_INDEX_MIN}, "
            f"{MONTHLY_PERIOD_INDEX_MAX}]; got {value}"
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
        if key in FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key {key!r} "
                "(v1.20.0 hard naming boundary — scenario "
                "schedule records do not carry actor-decision / "
                "price / forecast / advice / real-data / "
                "Japan-calibration / LLM / real-issuer / "
                "licensed-taxonomy fields)"
            )


# ---------------------------------------------------------------------------
# ScenarioSchedule
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioSchedule:
    """Immutable record naming a scenario schedule attached to
    a synthetic reference universe + run profile. v1.20.2 is
    storage-only; v1.20.3 will consume the schedule when
    executing the ``scenario_monthly_reference_universe`` run
    profile.

    Citation discipline: ``scenario_driver_template_ids`` lists
    plain-id citations to v1.18.1
    :class:`ScenarioDriverTemplate` records.
    ``reference_universe_id`` is a plain-id citation to a
    v1.20.1 :class:`ReferenceUniverseProfile`. The storage
    layer does **not** check that the cited records exist —
    v1.20.3 will validate at run time.
    """

    scenario_schedule_id: str
    run_profile_label: str
    reference_universe_id: str
    scenario_driver_template_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    scheduled_month_labels: tuple[str, ...] = field(
        default_factory=tuple
    )
    scheduled_period_indices: tuple[int, ...] = field(
        default_factory=tuple
    )
    schedule_policy_label: str = "single_scenario"
    status: str = "active"
    visibility: str = "internal"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "scenario_schedule_id",
        "run_profile_label",
        "reference_universe_id",
        "schedule_policy_label",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("run_profile_label",       RUN_PROFILE_LABELS),
        ("schedule_policy_label",   SCHEDULE_POLICY_LABELS),
        ("status",                  STATUS_LABELS),
        ("visibility",              VISIBILITY_LABELS),
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES:
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
        object.__setattr__(
            self,
            "scenario_driver_template_ids",
            _validate_string_tuple(
                self.scenario_driver_template_ids,
                field_name="scenario_driver_template_ids",
            ),
        )
        object.__setattr__(
            self,
            "scheduled_month_labels",
            _validate_label_tuple(
                self.scheduled_month_labels,
                SCHEDULED_MONTH_LABELS,
                field_name="scheduled_month_labels",
            ),
        )
        object.__setattr__(
            self,
            "scheduled_period_indices",
            _validate_period_index_tuple(
                self.scheduled_period_indices,
                field_name="scheduled_period_indices",
            ),
        )
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(
            metadata_dict, field_name="metadata"
        )
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_schedule_id": self.scenario_schedule_id,
            "run_profile_label": self.run_profile_label,
            "reference_universe_id": self.reference_universe_id,
            "scenario_driver_template_ids": list(
                self.scenario_driver_template_ids
            ),
            "scheduled_month_labels": list(
                self.scheduled_month_labels
            ),
            "scheduled_period_indices": list(
                self.scheduled_period_indices
            ),
            "schedule_policy_label": self.schedule_policy_label,
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# ScheduledScenarioApplication
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScheduledScenarioApplication:
    """Immutable record naming one scheduled scenario
    application slot inside a :class:`ScenarioSchedule`.

    The record is **not** an applied scenario yet — v1.18.2's
    :class:`ScenarioDriverApplicationRecord` is only emitted
    when the v1.20.3 run profile fires the schedule. v1.20.2
    stores the *intent* to apply.
    """

    scheduled_scenario_application_id: str
    scenario_schedule_id: str
    scenario_driver_template_id: str
    scheduled_period_index: int
    scheduled_month_label: str
    application_policy_label: str = "apply_at_period_start"
    affected_reference_universe_id: str = ""
    affected_sector_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    affected_firm_profile_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    status: str = "active"
    visibility: str = "internal"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "scheduled_scenario_application_id",
        "scenario_schedule_id",
        "scenario_driver_template_id",
        "scheduled_month_label",
        "application_policy_label",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("scheduled_month_label",      SCHEDULED_MONTH_LABELS),
        ("application_policy_label",   APPLICATION_POLICY_LABELS),
        ("status",                     STATUS_LABELS),
        ("visibility",                 VISIBILITY_LABELS),
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES:
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
        # ``affected_reference_universe_id`` is optional — a
        # caller may leave it empty when the schedule applies
        # to the run profile's *active* universe. If supplied,
        # it must be a non-empty string.
        if (
            self.affected_reference_universe_id != ""
            and not isinstance(
                self.affected_reference_universe_id, str
            )
        ):
            raise ValueError(
                "affected_reference_universe_id must be a string"
            )
        object.__setattr__(
            self,
            "scheduled_period_index",
            _validate_period_index(
                self.scheduled_period_index,
                field_name="scheduled_period_index",
            ),
        )
        object.__setattr__(
            self,
            "affected_sector_ids",
            _validate_string_tuple(
                self.affected_sector_ids,
                field_name="affected_sector_ids",
            ),
        )
        object.__setattr__(
            self,
            "affected_firm_profile_ids",
            _validate_string_tuple(
                self.affected_firm_profile_ids,
                field_name="affected_firm_profile_ids",
            ),
        )
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(
            metadata_dict, field_name="metadata"
        )
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scheduled_scenario_application_id": (
                self.scheduled_scenario_application_id
            ),
            "scenario_schedule_id": self.scenario_schedule_id,
            "scenario_driver_template_id": (
                self.scenario_driver_template_id
            ),
            "scheduled_period_index": self.scheduled_period_index,
            "scheduled_month_label": self.scheduled_month_label,
            "application_policy_label": (
                self.application_policy_label
            ),
            "affected_reference_universe_id": (
                self.affected_reference_universe_id
            ),
            "affected_sector_ids": list(self.affected_sector_ids),
            "affected_firm_profile_ids": list(
                self.affected_firm_profile_ids
            ),
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# ScenarioScheduleBook
# ---------------------------------------------------------------------------


@dataclass
class ScenarioScheduleBook:
    """Append-only storage for v1.20.2 scenario-schedule
    records.

    Mirrors the v1.18.1 / v1.19.3 / v1.20.1 storage-book
    convention: emits exactly one ledger record per ``add_*``
    call, no extra ledger record on duplicate id, mutates no
    other source-of-truth book. Empty by default on the kernel
    — pinned by ``test_empty_scenario_schedule_does_not_move_*``
    trip-wire tests at v1.20.2.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _schedules: dict[str, ScenarioSchedule] = field(
        default_factory=dict
    )
    _scheduled_applications: dict[
        str, ScheduledScenarioApplication
    ] = field(default_factory=dict)

    def _now(self) -> datetime:
        if self.clock is not None:
            try:
                return self.clock.current_datetime()
            except Exception:
                pass
        return datetime.now(timezone.utc)

    # -- schedule ---------------------------------------------------

    def add_schedule(
        self,
        schedule: ScenarioSchedule,
        *,
        simulation_date: Any = None,
    ) -> ScenarioSchedule:
        if schedule.scenario_schedule_id in self._schedules:
            raise DuplicateScenarioScheduleError(
                "Duplicate scenario_schedule_id: "
                f"{schedule.scenario_schedule_id}"
            )
        self._schedules[
            schedule.scenario_schedule_id
        ] = schedule

        if self.ledger is not None:
            payload = {
                "scenario_schedule_id": (
                    schedule.scenario_schedule_id
                ),
                "run_profile_label": schedule.run_profile_label,
                "reference_universe_id": (
                    schedule.reference_universe_id
                ),
                "scenario_driver_template_ids": list(
                    schedule.scenario_driver_template_ids
                ),
                "scheduled_month_labels": list(
                    schedule.scheduled_month_labels
                ),
                "scheduled_period_indices": list(
                    schedule.scheduled_period_indices
                ),
                "schedule_policy_label": (
                    schedule.schedule_policy_label
                ),
                "status": schedule.status,
                "visibility": schedule.visibility,
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
                event_type="scenario_schedule_recorded",
                simulation_date=sim_date,
                object_id=schedule.scenario_schedule_id,
                source=schedule.run_profile_label,
                target=schedule.reference_universe_id,
                payload=payload,
                space_id="scenario_schedule",
                visibility=schedule.visibility,
            )
        return schedule

    def get_schedule(
        self, scenario_schedule_id: str
    ) -> ScenarioSchedule:
        try:
            return self._schedules[scenario_schedule_id]
        except KeyError as exc:
            raise UnknownScenarioScheduleError(
                "scenario_schedule not found: "
                f"{scenario_schedule_id!r}"
            ) from exc

    def list_schedules(self) -> tuple[ScenarioSchedule, ...]:
        return tuple(self._schedules.values())

    def list_by_run_profile(
        self, run_profile_label: str
    ) -> tuple[ScenarioSchedule, ...]:
        return tuple(
            s
            for s in self._schedules.values()
            if s.run_profile_label == run_profile_label
        )

    def list_by_reference_universe(
        self, reference_universe_id: str
    ) -> tuple[ScenarioSchedule, ...]:
        return tuple(
            s
            for s in self._schedules.values()
            if s.reference_universe_id == reference_universe_id
        )

    def list_by_schedule_policy(
        self, schedule_policy_label: str
    ) -> tuple[ScenarioSchedule, ...]:
        return tuple(
            s
            for s in self._schedules.values()
            if s.schedule_policy_label == schedule_policy_label
        )

    def list_by_status(
        self, status: str
    ) -> tuple[ScenarioSchedule, ...]:
        return tuple(
            s for s in self._schedules.values() if s.status == status
        )

    # -- scheduled application --------------------------------------

    def add_scheduled_application(
        self,
        application: ScheduledScenarioApplication,
        *,
        simulation_date: Any = None,
    ) -> ScheduledScenarioApplication:
        if (
            application.scheduled_scenario_application_id
            in self._scheduled_applications
        ):
            raise DuplicateScheduledScenarioApplicationError(
                "Duplicate scheduled_scenario_application_id: "
                f"{application.scheduled_scenario_application_id}"
            )
        self._scheduled_applications[
            application.scheduled_scenario_application_id
        ] = application

        if self.ledger is not None:
            payload = {
                "scheduled_scenario_application_id": (
                    application.scheduled_scenario_application_id
                ),
                "scenario_schedule_id": (
                    application.scenario_schedule_id
                ),
                "scenario_driver_template_id": (
                    application.scenario_driver_template_id
                ),
                "scheduled_period_index": (
                    application.scheduled_period_index
                ),
                "scheduled_month_label": (
                    application.scheduled_month_label
                ),
                "application_policy_label": (
                    application.application_policy_label
                ),
                "affected_reference_universe_id": (
                    application.affected_reference_universe_id
                ),
                "affected_sector_ids": list(
                    application.affected_sector_ids
                ),
                "affected_firm_profile_ids": list(
                    application.affected_firm_profile_ids
                ),
                "status": application.status,
                "visibility": application.visibility,
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
                event_type="scheduled_scenario_application_recorded",
                simulation_date=sim_date,
                object_id=(
                    application.scheduled_scenario_application_id
                ),
                source=application.scenario_schedule_id,
                target=application.scenario_driver_template_id,
                payload=payload,
                space_id="scenario_schedule",
                visibility=application.visibility,
            )
        return application

    def get_scheduled_application(
        self, scheduled_scenario_application_id: str
    ) -> ScheduledScenarioApplication:
        try:
            return self._scheduled_applications[
                scheduled_scenario_application_id
            ]
        except KeyError as exc:
            raise UnknownScheduledScenarioApplicationError(
                "scheduled_scenario_application not found: "
                f"{scheduled_scenario_application_id!r}"
            ) from exc

    def list_scheduled_applications(
        self,
    ) -> tuple[ScheduledScenarioApplication, ...]:
        return tuple(self._scheduled_applications.values())

    def list_applications_by_schedule(
        self, scenario_schedule_id: str
    ) -> tuple[ScheduledScenarioApplication, ...]:
        return tuple(
            a
            for a in self._scheduled_applications.values()
            if a.scenario_schedule_id == scenario_schedule_id
        )

    def list_applications_by_template(
        self, scenario_driver_template_id: str
    ) -> tuple[ScheduledScenarioApplication, ...]:
        return tuple(
            a
            for a in self._scheduled_applications.values()
            if (
                a.scenario_driver_template_id
                == scenario_driver_template_id
            )
        )

    def list_applications_by_month(
        self, scheduled_month_label: str
    ) -> tuple[ScheduledScenarioApplication, ...]:
        return tuple(
            a
            for a in self._scheduled_applications.values()
            if a.scheduled_month_label == scheduled_month_label
        )

    def list_applications_by_period_index(
        self, scheduled_period_index: int
    ) -> tuple[ScheduledScenarioApplication, ...]:
        return tuple(
            a
            for a in self._scheduled_applications.values()
            if a.scheduled_period_index == scheduled_period_index
        )

    def list_applications_by_application_policy(
        self, application_policy_label: str
    ) -> tuple[ScheduledScenarioApplication, ...]:
        return tuple(
            a
            for a in self._scheduled_applications.values()
            if (
                a.application_policy_label
                == application_policy_label
            )
        )

    def list_applications_by_reference_universe(
        self, reference_universe_id: str
    ) -> tuple[ScheduledScenarioApplication, ...]:
        return tuple(
            a
            for a in self._scheduled_applications.values()
            if (
                a.affected_reference_universe_id
                == reference_universe_id
            )
        )

    # -- snapshot ---------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        return {
            "scenario_schedules": [
                s.to_dict() for s in self._schedules.values()
            ],
            "scheduled_scenario_applications": [
                a.to_dict()
                for a in self._scheduled_applications.values()
            ],
        }


# ---------------------------------------------------------------------------
# Default monthly schedule fixture
#
# v1.20.0 design pin: the default test fixture applies one
# scenario driver (``credit_tightening_driver``) at month 4
# (period index 3, since the index is 0-based) on the v1.20.1
# generic 11-sector universe. Sectors / firms with high credit
# / funding sensitivity are the natural targets, but the
# storage layer leaves this empty (run-profile time at v1.20.3
# resolves the impact map).
# ---------------------------------------------------------------------------


def _scheduled_month_label_for(period_index_0_based: int) -> str:
    """Map a 0-based period index to the v1.20.2 closed-set
    month label (``month_01`` for index 0, …, ``month_12`` for
    index 11)."""
    if (
        period_index_0_based < MONTHLY_PERIOD_INDEX_MIN
        or period_index_0_based > MONTHLY_PERIOD_INDEX_MAX
    ):
        raise ValueError(
            f"period_index out of range "
            f"[{MONTHLY_PERIOD_INDEX_MIN}, "
            f"{MONTHLY_PERIOD_INDEX_MAX}]; "
            f"got {period_index_0_based}"
        )
    return f"month_{period_index_0_based + 1:02d}"


def build_default_scenario_monthly_schedule(
    *,
    scenario_schedule_id: str = (
        "scenario_schedule:scenario_monthly_reference_universe:"
        "default"
    ),
    reference_universe_id: str = (
        "reference_universe:generic_11_sector"
    ),
    scenario_driver_template_id: str = (
        "scenario_driver:credit_tightening:reference"
    ),
    scheduled_period_index: int = 3,
) -> tuple[ScenarioSchedule, ScheduledScenarioApplication]:
    """Construct the v1.20.0-pinned default monthly schedule —
    one :class:`ScenarioSchedule` + one
    :class:`ScheduledScenarioApplication`. The default applies
    ``credit_tightening_driver`` at month 4 (0-based period
    index 3) on the v1.20.1 ``generic_11_sector`` universe.

    The helper is **deterministic** and **does not register**
    anything on a kernel. Same arguments → byte-identical
    records.

    For storage, the caller must invoke a separate registration
    flow:

    >>> book = ScenarioScheduleBook()
    >>> schedule, application = build_default_scenario_monthly_schedule()
    >>> book.add_schedule(schedule)
    >>> book.add_scheduled_application(application)
    """
    month_label = _scheduled_month_label_for(scheduled_period_index)
    schedule = ScenarioSchedule(
        scenario_schedule_id=scenario_schedule_id,
        run_profile_label="scenario_monthly_reference_universe",
        reference_universe_id=reference_universe_id,
        scenario_driver_template_ids=(
            scenario_driver_template_id,
        ),
        scheduled_month_labels=(month_label,),
        scheduled_period_indices=(scheduled_period_index,),
        schedule_policy_label="single_scenario",
    )
    application = ScheduledScenarioApplication(
        scheduled_scenario_application_id=(
            f"scheduled_scenario_application:"
            f"{scenario_schedule_id}:{month_label}"
        ),
        scenario_schedule_id=scenario_schedule_id,
        scenario_driver_template_id=scenario_driver_template_id,
        scheduled_period_index=scheduled_period_index,
        scheduled_month_label=month_label,
        application_policy_label="apply_after_information_arrivals",
        affected_reference_universe_id=reference_universe_id,
        affected_sector_ids=(),
        affected_firm_profile_ids=(),
    )
    return schedule, application


__all__ = [
    "APPLICATION_POLICY_LABELS",
    "DuplicateScenarioScheduleError",
    "DuplicateScheduledScenarioApplicationError",
    "FORBIDDEN_SCENARIO_SCHEDULE_FIELD_NAMES",
    "MONTHLY_PERIOD_INDEX_MAX",
    "MONTHLY_PERIOD_INDEX_MIN",
    "RUN_PROFILE_LABELS",
    "SCHEDULED_MONTH_LABELS",
    "SCHEDULE_POLICY_LABELS",
    "STATUS_LABELS",
    "ScenarioSchedule",
    "ScenarioScheduleBook",
    "ScenarioScheduleError",
    "ScheduledScenarioApplication",
    "UnknownScenarioScheduleError",
    "UnknownScheduledScenarioApplicationError",
    "VISIBILITY_LABELS",
    "build_default_scenario_monthly_schedule",
]
