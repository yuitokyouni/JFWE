"""
v1.21.2 — Stress program application: thin orchestrator over
the existing v1.18 scenario-driver application chain.

v1.21.2 ships:

- :class:`StressProgramApplicationRecord` — one immutable
  frozen dataclass; the **program-level** receipt for a single
  :func:`apply_stress_program` call. Cites — never mutates —
  the underlying v1.18.2
  :class:`world.scenario_applications.ScenarioDriverApplicationRecord`
  ids and the v1.18.2
  :class:`world.scenario_applications.ScenarioContextShiftRecord`
  ids that the existing v1.18.2 helper produced.
- :class:`StressProgramApplicationBook` — one append-only
  storage book. Emits exactly one
  ``stress_program_application_recorded`` ledger event per
  successful ``add_application(...)`` call. **No per-step
  stress application ledger record** — the per-step records
  live in ``world.scenario_applications`` at v1.18.2.
- :func:`apply_stress_program` — the **thin orchestrator**.
  Walks a v1.21.1 :class:`StressProgramTemplate`'s steps in
  dense ``step_index`` order, calls the existing v1.18.2
  :func:`world.scenario_applications.apply_scenario_driver`
  exactly once per step, and emits one program-level receipt
  collecting the underlying ids.

Critical design constraints carried verbatim from v1.21.0a
(binding):

- **Thin orchestration only.** v1.21.2 does **not** infer any
  interaction between stress steps, does **not** classify
  overlap, does **not** compute magnitude, does **not** reduce
  multiple context shifts into one combined label, does **not**
  decide actor behaviour. Every emitted v1.18.2 record stays
  unchanged in shape and in ledger position; v1.21.2 adds
  exactly one program-level receipt on top.
- **No source-of-truth book mutation.** ``PriceBook``,
  ``ContractBook``, ``ConstraintBook``, ``OwnershipBook``,
  ``InstitutionsBook``, ``MarketEnvironmentBook``,
  ``FirmFinancialStateBook``, ``InterbankLiquidityStateBook``,
  ``IndustryConditionBook``, ``MarketConditionBook``,
  ``InvestorMarketIntentBook``, ``FinancingPathBook`` — all
  byte-identical pre / post call. The orchestrator writes only
  to ``kernel.scenario_applications`` (via the existing v1.18.2
  helper) and ``kernel.stress_applications`` (this module's
  book).
- **No new closed-set vocabulary.** The
  ``application_status_label`` reuses v1.18.2
  :data:`world.scenario_applications.APPLICATION_STATUS_LABELS`
  verbatim.
- **No new ScenarioDriverTemplate.** The orchestrator does not
  create or modify v1.18.1 templates; it only calls the
  v1.18.2 helper which reads from
  ``kernel.scenario_drivers``.
- **No interaction / aggregate / composite / net / dominant
  fields.** ``FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES``
  composes the v1.18.0 / v1.19.3 / v1.20.0 / v1.21.0a /
  v1.21.1 forbidden-token lists; rejection is enforced at
  every dataclass construction, every payload key, and every
  metadata key.

Cardinality binding (carried forward from v1.21.0a +
v1.21.1):

- ≤ 1 stress program per kernel (enforced by the v1.21.1
  ``StressProgramBook``).
- ≤ 3 stress steps per program (enforced by v1.21.1
  ``StressProgramTemplate.__post_init__``).
- ≤ 60 v1.21 records added per stress-applied run; pinned by
  ``test_apply_stress_program_added_record_count_within_60``.
- ``manifest.record_count ≤ 4000`` remains binding.

The module is **runtime-book-free** beyond the v1.18.2 helper
+ the v1.21.1 storage book + the v0/v1 ledger / clock
convention shared by every other storage book. It does not
import any source-of-truth book on the engine side.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, ClassVar, Iterable, Mapping, TYPE_CHECKING

from world.clock import Clock
from world.ledger import Ledger
from world.scenario_applications import (
    APPLICATION_STATUS_LABELS,
    apply_scenario_driver,
)
from world.stress_programs import (
    FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES,
    StressProgramTemplate,
)

if TYPE_CHECKING:
    from world.kernel import WorldKernel


# ---------------------------------------------------------------------------
# Closed-set vocabularies (REUSE-FIRST — no new vocabulary at v1.21.2)
# ---------------------------------------------------------------------------


# REUSED VERBATIM from v1.18.2 ``APPLICATION_STATUS_LABELS``.
# v1.21.0a §"Closed-set vocabulary discipline" requires reuse
# wherever possible; this is one of those cases.
STRESS_PROGRAM_APPLICATION_STATUS_LABELS: frozenset[str] = (
    APPLICATION_STATUS_LABELS
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


# v1.21.2 default reasoning-policy id. The audit shape mirrors
# v1.18.0: a future LLM-mode reasoning policy may replace the
# v1.21.x rule-based fallback under the same shape (different
# ``reasoning_policy_id``) without changing the audit surface.
DEFAULT_STRESS_PROGRAM_APPLICATION_REASONING_POLICY_ID: str = (
    "v1.21.2:stress_program_application:rule_based_fallback"
)


# Default boundary flags stamped onto every emitted record.
# Composes the v1.18.2 default 7-flag set with the v1.21.0a
# additions (no_aggregate_stress_result,
# no_interaction_inference, no_field_value_claim,
# no_field_magnitude_claim).
_DEFAULT_BOUNDARY_FLAGS_TUPLE: tuple[tuple[str, bool], ...] = (
    ("no_actor_decision", True),
    ("no_llm_execution", True),
    ("no_price_formation", True),
    ("no_trading", True),
    ("no_financing_execution", True),
    ("no_investment_advice", True),
    ("synthetic_only", True),
    # v1.21.0a additions
    ("no_aggregate_stress_result", True),
    ("no_interaction_inference", True),
    ("no_field_value_claim", True),
    ("no_field_magnitude_claim", True),
)


def _default_boundary_flags() -> dict[str, bool]:
    return dict(_DEFAULT_BOUNDARY_FLAGS_TUPLE)


# ---------------------------------------------------------------------------
# Hard naming boundary
#
# Mirrors v1.21.1 ``FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES``
# verbatim. v1.21.2 explicitly does NOT introduce additional
# tokens — the v1.21.0a-corrected list is exhaustive for the
# stress layer through v1.21.x.
# ---------------------------------------------------------------------------


FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class StressApplicationError(Exception):
    """Base class for v1.21.2 stress-application errors."""


class DuplicateStressProgramApplicationError(
    StressApplicationError
):
    """Raised when a stress_program_application_id is added
    twice."""


class UnknownStressProgramApplicationError(
    StressApplicationError, KeyError
):
    """Raised when a stress_program_application_id is not
    found."""


# ---------------------------------------------------------------------------
# Small validation helpers
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


def _validate_non_negative_int(
    value: Any, *, field_name: str
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"{field_name} must be int (not bool); "
            f"got {type(value).__name__}"
        )
    if value < 0:
        raise ValueError(
            f"{field_name} must be >= 0; got {value}"
        )
    return value


def _coerce_iso_date(value: Any) -> str:
    if isinstance(value, str):
        if not value:
            raise ValueError(
                "as_of_date must be a non-empty ISO date"
            )
        return value
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(
        "as_of_date must be date or str; got "
        f"{type(value).__name__}"
    )


def _scan_for_forbidden_keys(
    mapping: Mapping[str, Any], *, field_name: str
) -> None:
    """Reject any v1.21.0a forbidden field name appearing in a
    metadata or payload mapping."""
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if key in FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key {key!r} "
                "(v1.21.0a hard naming boundary — stress program "
                "application records do not carry actor-decision "
                "/ price / forecast / advice / real-data / "
                "Japan-calibration / LLM / real-issuer / "
                "licensed-taxonomy / magnitude / probability / "
                "aggregate / composite / net / dominant / "
                "interaction fields)"
            )


# ---------------------------------------------------------------------------
# StressProgramApplicationRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StressProgramApplicationRecord:
    """Immutable program-level receipt for a single
    :func:`apply_stress_program` call.

    Cardinality:

    - One record per ``apply_stress_program(...)`` call,
      regardless of how many ``StressStep`` entries the program
      carries.
    - ``scenario_application_ids`` lists one v1.18.2
      :class:`ScenarioDriverApplicationRecord` id per stress
      step that successfully resolved (in ``step_index``
      order).
    - ``scenario_context_shift_ids`` lists every v1.18.2
      :class:`ScenarioContextShiftRecord` id emitted by the
      cited scenario applications, in the order the v1.18.2
      helper produced them (per-application ordinal sub-
      sequence preserved).
    - ``unresolved_step_count`` counts steps that did **not**
      produce a v1.18.2 application record (e.g. a missing
      template); 0 in the happy path.

    The record carries no aggregate / combined / net /
    dominant / composite / interaction / expected /
    predicted / forecasted field. The v1.21.0a forbidden
    naming boundary is scanned at construction time via the
    dataclass field-name guard + the metadata-key scan.
    """

    stress_program_application_id: str
    stress_program_template_id: str
    as_of_date: str
    scenario_application_ids: tuple[str, ...]
    scenario_context_shift_ids: tuple[str, ...]
    unresolved_step_count: int
    application_status_label: str
    reasoning_mode: str = "rule_based_fallback"
    reasoning_policy_id: str = (
        DEFAULT_STRESS_PROGRAM_APPLICATION_REASONING_POLICY_ID
    )
    reasoning_slot: str = "future_llm_compatible"
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    status: str = "active"
    visibility: str = "internal"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "stress_program_application_id",
        "stress_program_template_id",
        "as_of_date",
        "application_status_label",
        "reasoning_mode",
        "reasoning_policy_id",
        "reasoning_slot",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        (
            "application_status_label",
            STRESS_PROGRAM_APPLICATION_STATUS_LABELS,
        ),
        ("status",     STATUS_LABELS),
        ("visibility", VISIBILITY_LABELS),
    )

    def __post_init__(self) -> None:
        # Trip-wire: a future field rename must not collide
        # with the v1.21.0a forbidden list. Pinned by
        # ``test_stress_program_application_forbidden_field_names``.
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} is in the v1.21.0a "
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
            "as_of_date",
            _coerce_iso_date(self.as_of_date),
        )
        object.__setattr__(
            self,
            "scenario_application_ids",
            _validate_string_tuple(
                self.scenario_application_ids,
                field_name="scenario_application_ids",
            ),
        )
        object.__setattr__(
            self,
            "scenario_context_shift_ids",
            _validate_string_tuple(
                self.scenario_context_shift_ids,
                field_name="scenario_context_shift_ids",
            ),
        )
        object.__setattr__(
            self,
            "unresolved_step_count",
            _validate_non_negative_int(
                self.unresolved_step_count,
                field_name="unresolved_step_count",
            ),
        )
        # boundary_flags must be a mapping of string keys to
        # bool values; reject forbidden keys via the standard
        # scan.
        bf = dict(self.boundary_flags)
        for key, val in bf.items():
            if not isinstance(key, str) or not key:
                raise ValueError(
                    "boundary_flags keys must be non-empty "
                    "strings"
                )
            if not isinstance(val, bool):
                raise ValueError(
                    f"boundary_flags[{key!r}] must be bool; "
                    f"got {type(val).__name__}"
                )
        _scan_for_forbidden_keys(
            bf, field_name="boundary_flags"
        )
        object.__setattr__(self, "boundary_flags", bf)
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(
            metadata_dict, field_name="metadata"
        )
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stress_program_application_id": (
                self.stress_program_application_id
            ),
            "stress_program_template_id": (
                self.stress_program_template_id
            ),
            "as_of_date": self.as_of_date,
            "scenario_application_ids": list(
                self.scenario_application_ids
            ),
            "scenario_context_shift_ids": list(
                self.scenario_context_shift_ids
            ),
            "unresolved_step_count": self.unresolved_step_count,
            "application_status_label": (
                self.application_status_label
            ),
            "reasoning_mode": self.reasoning_mode,
            "reasoning_policy_id": self.reasoning_policy_id,
            "reasoning_slot": self.reasoning_slot,
            "boundary_flags": dict(self.boundary_flags),
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# StressProgramApplicationBook
# ---------------------------------------------------------------------------


@dataclass
class StressProgramApplicationBook:
    """Append-only storage for v1.21.2
    :class:`StressProgramApplicationRecord` instances.

    Mirrors the v1.18.1 / v1.19.3 / v1.20.1 / v1.20.2 / v1.21.1
    storage-book convention: emits **exactly one ledger
    record** per successful ``add_application(...)`` call (a
    single ``stress_program_application_recorded`` event), no
    extra ledger record on duplicate id, mutates no other
    source-of-truth book.

    **No per-step stress-application ledger record is emitted.**
    Per-step records live at v1.18.2 in
    :class:`world.scenario_applications.ScenarioApplicationBook`
    (one
    :class:`world.scenario_applications.ScenarioDriverApplicationRecord`
    per stress step that successfully resolved).

    Empty by default on the kernel — pinned by
    :func:`tests.test_stress_applications.test_world_kernel_empty_stress_application_book_by_default`
    and the digest trip-wire tests at v1.21.2.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _applications: dict[
        str, StressProgramApplicationRecord
    ] = field(default_factory=dict)

    def _now(self) -> datetime:
        if self.clock is not None:
            try:
                return self.clock.current_datetime()
            except Exception:
                pass
        return datetime.now(timezone.utc)

    def add_application(
        self,
        application: StressProgramApplicationRecord,
        *,
        simulation_date: Any = None,
    ) -> StressProgramApplicationRecord:
        if (
            application.stress_program_application_id
            in self._applications
        ):
            raise DuplicateStressProgramApplicationError(
                "Duplicate stress_program_application_id: "
                f"{application.stress_program_application_id!r}"
            )
        self._applications[
            application.stress_program_application_id
        ] = application

        if self.ledger is not None:
            payload = {
                "stress_program_application_id": (
                    application.stress_program_application_id
                ),
                "stress_program_template_id": (
                    application.stress_program_template_id
                ),
                "as_of_date": application.as_of_date,
                "scenario_application_ids": list(
                    application.scenario_application_ids
                ),
                "scenario_context_shift_ids": list(
                    application.scenario_context_shift_ids
                ),
                "unresolved_step_count": (
                    application.unresolved_step_count
                ),
                "application_status_label": (
                    application.application_status_label
                ),
                "reasoning_mode": application.reasoning_mode,
                "reasoning_policy_id": (
                    application.reasoning_policy_id
                ),
                "reasoning_slot": application.reasoning_slot,
                "boundary_flags": dict(
                    application.boundary_flags
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
                else application.as_of_date
            )
            self.ledger.append(
                event_type=(
                    "stress_program_application_recorded"
                ),
                simulation_date=sim_date,
                object_id=(
                    application.stress_program_application_id
                ),
                source=application.stress_program_template_id,
                payload=payload,
                space_id="stress_applications",
                visibility=application.visibility,
            )
        return application

    def get_application(
        self, stress_program_application_id: str
    ) -> StressProgramApplicationRecord:
        try:
            return self._applications[
                stress_program_application_id
            ]
        except KeyError as exc:
            raise UnknownStressProgramApplicationError(
                "stress_program_application not found: "
                f"{stress_program_application_id!r}"
            ) from exc

    def list_applications(
        self,
    ) -> tuple[StressProgramApplicationRecord, ...]:
        return tuple(self._applications.values())

    def list_by_program(
        self, stress_program_template_id: str
    ) -> tuple[StressProgramApplicationRecord, ...]:
        return tuple(
            a
            for a in self._applications.values()
            if (
                a.stress_program_template_id
                == stress_program_template_id
            )
        )

    def list_by_date(
        self, as_of_date: Any
    ) -> tuple[StressProgramApplicationRecord, ...]:
        iso = _coerce_iso_date(as_of_date)
        return tuple(
            a
            for a in self._applications.values()
            if a.as_of_date == iso
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "stress_program_applications": [
                a.to_dict()
                for a in self._applications.values()
            ],
        }


# ---------------------------------------------------------------------------
# apply_stress_program — the thin orchestrator
# ---------------------------------------------------------------------------


def apply_stress_program(
    kernel: "WorldKernel",
    *,
    stress_program_template_id: str,
    as_of_date: Any,
    source_context_record_ids: Iterable[str] = (),
    stress_program_application_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> StressProgramApplicationRecord:
    """Deterministic, append-only application of a v1.21.1
    :class:`StressProgramTemplate` over the existing v1.18.2
    scenario-driver application chain.

    Behaviour pinned by the v1.21.0a-corrected design and
    re-pinned by v1.21.2 trip-wire tests:

    - **Resolves** the program from
      :attr:`world.kernel.WorldKernel.stress_programs` (raises
      :class:`UnknownStressProgramTemplateError` if missing).
    - **Walks** the program's :class:`StressStep` instances in
      dense ``step_index`` order (the v1.21.1 storage already
      enforced ``0..n-1``). For each step, calls the existing
      v1.18.2 :func:`world.scenario_applications.apply_scenario_driver`
      exactly once with:

      * ``scenario_driver_template_id =
        step.scenario_driver_template_id``
      * ``as_of_date`` = the program-level ``as_of_date`` —
        v1.21.2 fires every step on the program's date by
        default; per-step scheduling is reserved for a future
        milestone.
      * ``source_context_record_ids`` = the program-level cited
        ids (passed verbatim).
      * ``metadata`` = an audit-shape dict citing
        ``stress_program_template_id``, ``stress_step_id``, and
        the program-level
        ``stress_program_application_id``.

    - **Collects** the underlying
      :class:`world.scenario_applications.ScenarioDriverApplicationRecord`
      ids in ordinal step order, and the
      :class:`world.scenario_applications.ScenarioContextShiftRecord`
      ids from the per-step
      :attr:`ScenarioDriverApplicationRecord.emitted_context_shift_ids`
      tuples (in step order, with the per-step ordinal
      sub-sequence preserved).
    - **Emits** exactly **one** program-level
      :class:`StressProgramApplicationRecord` via
      :meth:`StressProgramApplicationBook.add_application`. No
      per-step stress-application ledger record is emitted.
    - **Never mutates** any pre-existing context record. The
      ``MarketEnvironmentBook`` / ``FirmFinancialStateBook`` /
      ``InterbankLiquidityStateBook`` /
      ``IndustryConditionBook`` / ``MarketConditionBook`` /
      ``PriceBook`` / ``ContractBook`` / ``OwnershipBook`` /
      ``ConstraintBook`` / ``InstitutionsBook`` /
      ``InvestorMarketIntentBook`` / ``FinancingPathBook``
      snapshots are byte-identical pre / post call.
    - **Does not infer interactions.** v1.21.2 emits no
      ``interaction_label``, no ``composition_label``, no
      ``output_context_label``, no ``aggregate_*`` /
      ``combined_*`` / ``net_*`` / ``dominant_*`` /
      ``composite_*`` / ``expected_*`` / ``predicted_*`` /
      ``forecasted_*`` field. The v1.21.0a-corrected design
      explicitly excludes interaction inference (see
      ``docs/v1_21_stress_composition_layer.md`` *Deferred:
      StressInteractionRule*).
    - **Does not decide actor behaviour.** No actor decision,
      no investor action, no bank approval, no trading, no
      financing execution, no investment advice, no LLM
      execution.

    Cardinality (binding):

    - ≤ 3 underlying v1.18.2
      :class:`ScenarioDriverApplicationRecord` records emitted
      (one per step that resolves; the v1.21.1 storage caps
      step count at 3).
    - The v1.18.2 helper emits 0–N
      :class:`ScenarioContextShiftRecord` records per step
      (the v1.18.2
      ``_build_shift_specs`` table determines the per-family
      shift count). For the v1.18.2 default fixture families
      this is at most 2 per step; a 3-step program therefore
      emits at most 6 context shifts.
    - Plus exactly 1 v1.21.2 program-level receipt. Total
      v1.21.x records added per stress-applied run ≤ 60
      (the ≤ 60 bound carries forward from v1.21.0a §130.4
      and is pinned by
      ``test_apply_stress_program_added_record_count_within_60``).

    The returned record is the program-level receipt that the
    caller can cite downstream (e.g., the v1.21.3 readout
    helper, when implemented).
    """
    program: StressProgramTemplate = (
        kernel.stress_programs.get_program(
            stress_program_template_id
        )
    )

    iso_date = _coerce_iso_date(as_of_date)

    cited_source_ids = _validate_string_tuple(
        source_context_record_ids,
        field_name="source_context_record_ids",
    )

    if stress_program_application_id is None:
        stress_program_application_id = (
            f"stress_program_application:"
            f"{stress_program_template_id}:{iso_date}"
        )

    caller_metadata = dict(metadata or {})
    _scan_for_forbidden_keys(
        caller_metadata, field_name="metadata"
    )

    # Walk the steps in dense step_index order. The v1.21.1
    # ``StressProgramTemplate`` already enforced the dense
    # 0..n-1 invariant; ``steps_in_ordinal_order()`` returns
    # them sorted defensively.
    ordered_steps = program.steps_in_ordinal_order()

    scenario_application_ids: list[str] = []
    scenario_context_shift_ids: list[str] = []
    unresolved_step_count = 0

    for step in ordered_steps:
        step_metadata: dict[str, Any] = {
            "stress_program_template_id": (
                stress_program_template_id
            ),
            "stress_step_id": step.stress_step_id,
            "stress_program_application_id": (
                stress_program_application_id
            ),
            "step_index": step.step_index,
        }
        # Per-step unique scenario application id. Without this
        # explicit id, the v1.18.2 helper would default to
        # ``scenario_application:{template_id}:{iso_date}``,
        # which collides if two steps cite the same template
        # on the same date — the second add_application would
        # raise DuplicateScenarioApplicationError. Composing
        # the program id + step index makes each step's id
        # distinct without changing the v1.18.2 default
        # behaviour for callers that bypass the orchestrator.
        per_step_application_id = (
            f"scenario_application:"
            f"{stress_program_application_id}:"
            f"step_{step.step_index:02d}:"
            f"{step.scenario_driver_template_id}"
        )
        try:
            v1_18_application = apply_scenario_driver(
                kernel,
                scenario_driver_template_id=(
                    step.scenario_driver_template_id
                ),
                as_of_date=iso_date,
                source_context_record_ids=cited_source_ids,
                application_id=per_step_application_id,
                metadata=step_metadata,
            )
        except Exception:
            # Step did not resolve (e.g., missing v1.18.1
            # template). v1.21.2 records the step as
            # unresolved and continues — the program-level
            # receipt's ``unresolved_step_count`` reflects
            # the failure count without re-raising.
            unresolved_step_count += 1
            continue
        scenario_application_ids.append(
            v1_18_application.scenario_application_id
        )
        scenario_context_shift_ids.extend(
            v1_18_application.emitted_context_shift_ids
        )

    if unresolved_step_count == len(ordered_steps):
        application_status_label = "rejected"
    elif unresolved_step_count > 0:
        application_status_label = "degraded_unresolved_refs"
    elif scenario_context_shift_ids:
        application_status_label = "applied_as_context_shift"
    else:
        application_status_label = "prepared"

    record = StressProgramApplicationRecord(
        stress_program_application_id=(
            stress_program_application_id
        ),
        stress_program_template_id=stress_program_template_id,
        as_of_date=iso_date,
        scenario_application_ids=tuple(scenario_application_ids),
        scenario_context_shift_ids=tuple(
            scenario_context_shift_ids
        ),
        unresolved_step_count=unresolved_step_count,
        application_status_label=application_status_label,
        metadata=caller_metadata,
    )

    kernel.stress_applications.add_application(record)
    return record


__all__ = [
    "DEFAULT_STRESS_PROGRAM_APPLICATION_REASONING_POLICY_ID",
    "DuplicateStressProgramApplicationError",
    "FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES",
    "STATUS_LABELS",
    "STRESS_PROGRAM_APPLICATION_STATUS_LABELS",
    "StressApplicationError",
    "StressProgramApplicationBook",
    "StressProgramApplicationRecord",
    "UnknownStressProgramApplicationError",
    "VISIBILITY_LABELS",
    "apply_stress_program",
]
