"""
v1.21.1 — Stress program storage.

Storage-only foundation for the v1.21 Stress Composition Layer.
v1.21.1 ships two immutable frozen dataclasses
(:class:`StressStep`, :class:`StressProgramTemplate`) and one
append-only :class:`StressProgramBook` for naming and persisting
**bundles of existing v1.18.1 ScenarioDriverTemplate ids** as
ordered stress programs.

Critical design constraints carried verbatim from v1.21.0a
(binding):

- **Storage only.** v1.21.1 does **not** ship the
  ``apply_stress_program(...)`` thin orchestrator (that lands at
  v1.21.2), does **not** ship :class:`StressFieldReadout` (that
  lands at v1.21.3), does **not** apply scenarios, does **not**
  emit context shifts, does **not** infer interactions, and
  does **not** mutate the ``PriceBook`` or any other source-of-
  truth book.
- **Empty by default on the kernel.** The new
  ``WorldKernel.stress_programs`` field is wired with
  ``field(default_factory=StressProgramBook)``; an empty book
  emits no ledger record, leaving every existing
  ``living_world_digest`` byte-identical:

  - ``quarterly_default``      — `f93bdf3f…b705897c`
  - ``monthly_reference``      — `75a91cfa…91879d`
  - ``scenario_monthly_reference_universe`` test fixture —
    `5003fdfaa45d…f15566eb6`

- **Plain-id citation only.** Each :class:`StressStep` cites a
  v1.18.1 ``scenario_driver_template_id`` via plain-id field
  reference. The storage layer does **not** resolve the
  citation against any v1.18.1
  :class:`world.scenario_drivers.ScenarioDriverTemplateBook` —
  v1.21.2 will validate at run-helper invocation time.
- **No interaction inference, no aggregate fields.** v1.21.1
  emits no ``interaction_label``, no ``composition_label``,
  no ``output_context_label``, no ``aggregate_*`` /
  ``combined_*`` / ``net_*`` / ``dominant_*`` /
  ``composite_*`` field. The v1.21.0a-corrected design
  excludes these on principle (auto-inferred composition would
  be a pseudo-causal claim — see
  ``docs/v1_21_stress_composition_layer.md`` *Deferred:
  StressInteractionRule* section for the binding rationale).
- **No magnitudes, no probabilities, no expected responses.**
  :data:`FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES` extends the
  v1.18.0 / v1.19.3 / v1.20.0 forbidden-field-name lists with
  the v1.21.0a aggregate / composite / net / dominant /
  forecast-shaped tokens. Any forbidden token appearing as a
  dataclass field name, a payload key, or a metadata key is
  rejected at construction time.
- **Cardinality bounded.** A program carries 1, 2, or 3 stress
  steps (binding closed range). Step indices must form a dense
  zero-based ordinal sequence; duplicate indices and duplicate
  step ids are rejected at construction time.

The module is **runtime-book-free** beyond the v0/v1 ledger +
clock convention shared by every other storage book — it does
not import any source-of-truth book on the engine side, does
not import :mod:`world.scenario_drivers`, and does not import
:mod:`world.scenario_applications`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Mapping

from world.clock import Clock
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Closed-set vocabularies (small; v1.21.0a reuse-first discipline)
# ---------------------------------------------------------------------------


# v1.21.0a — small program-purpose closed set. Justified in
# the v1.21 design note because no v1.18 / v1.20 vocabulary
# names a *program* (the program is itself a v1.21 concept).
PROGRAM_PURPOSE_LABELS: frozenset[str] = frozenset(
    {
        "single_credit_tightening_stress",
        "single_funding_window_closure_stress",
        "single_information_gap_stress",
        "twin_credit_funding_stress",
        "twin_credit_information_gap_stress",
        "multi_stress_demonstration",
        "custom_synthetic",
        "unknown",
    }
)


# v1.21.0a — reused from v1.18.1 verbatim as a string constant
# enumeration. The book does not depend on this set being
# imported from world.scenario_drivers (so v1.21.1 stays
# runtime-book-free and import-light); the set's contents
# mirror v1.18.1 ``EVENT_DATE_POLICY_LABELS``.
EVENT_DATE_POLICY_LABELS: frozenset[str] = frozenset(
    {
        "quarter_start",
        "quarter_end",
        "month_start",
        "month_end",
        "ad_hoc",
        "unknown",
    }
)


# v1.21.0a — reused from v1.20.2 ``SCHEDULED_MONTH_LABELS``
# verbatim. A stress step records the month label only as a
# *plan*; v1.21.1 storage does not bind the step to a specific
# period yet (v1.21.2's helper takes an explicit per-step
# ``as_of_date`` kwarg).
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


# v1.21.0a — reused from v1.18.1 ``STATUS_LABELS`` verbatim.
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


# v1.21.0a — reused from v1.18.1 ``VISIBILITY_LABELS`` verbatim.
VISIBILITY_LABELS: frozenset[str] = frozenset(
    {
        "public",
        "restricted",
        "internal",
        "private",
        "unknown",
    }
)


# Cardinality binding from v1.21.0a (binding):
#   1 ≤ step_count ≤ 3
PROGRAM_MIN_STEP_COUNT: int = 1
PROGRAM_MAX_STEP_COUNT: int = 3


# ---------------------------------------------------------------------------
# Hard naming boundary
#
# Composes the v1.18.0 actor-decision tokens, the v1.19.3
# Japan-real-data tokens, the v1.20.0 real-issuer / real-
# financial / licensed-taxonomy tokens, and the v1.21.0a
# aggregate / composite / net / dominant / forecast-shaped
# tokens. Scanned across every dataclass field name, every
# payload key, and every metadata key at construction time;
# also scanned by the test-file module-text scan against the
# rendered source module + test text (with the literal block
# stripped).
# ---------------------------------------------------------------------------


FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES: frozenset[str] = frozenset(
    {
        # v1.18.0 actor-decision / canonical-judgment tokens
        "firm_decision",
        "investor_action",
        "bank_approval",
        "trading_decision",
        "optimal_capital_structure",
        # bare trading verbs / surfaces
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
        "real_data",
        "real_data_value",
        "japan_calibration",
        "llm_output",
        "llm_prose",
        "prompt_text",
        # v1.19.3 Japan real-indicator tokens
        "real_indicator_value",
        "cpi_value",
        "gdp_value",
        "policy_rate",
        "real_release_date",
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
        "factset",
        "bloomberg",
        "refinitiv",
        "topix",
        "nikkei",
        "jpx",
        "sp_index",
        # v1.21.0a forecast-shaped tokens
        "stress_magnitude",
        "stress_magnitude_in_basis_points",
        "stress_magnitude_in_percent",
        "stress_probability_weight",
        "expected_field_response",
        "expected_stress_path",
        "stress_forecast_path",
        "stress_buy_signal",
        "stress_sell_signal",
        "stress_target_price",
        "stress_expected_return",
        "stress_outcome_label",
        # v1.21.0a aggregate / composite / net / dominant tokens
        "aggregate_shift_direction",
        "aggregate_context_label",
        "combined_context_label",
        "combined_shift_direction",
        "net_pressure_label",
        "net_stress_direction",
        "composite_risk_label",
        "composite_market_access_label",
        "dominant_stress_label",
        "total_stress_intensity",
        "stress_amplification_score",
        "predicted_stress_effect",
        "projected_stress_effect",
        # v1.21.0a interaction tokens (deferred to v1.22+ as
        # manual_annotation only — never inferred; never a
        # dataclass field at v1.21.x)
        "interaction_label",
        "composition_label",
        "output_context_label",
        "dominant_shift_direction_label",
        "amplify",
        "dampen",
        "offset",
        "coexist",
    }
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class StressProgramError(Exception):
    """Base class for v1.21.1 stress-program storage errors."""


class DuplicateStressProgramTemplateError(StressProgramError):
    """Raised when a stress_program_template_id is added twice."""


class UnknownStressProgramTemplateError(
    StressProgramError, KeyError
):
    """Raised when a stress_program_template_id is not found."""


# ---------------------------------------------------------------------------
# Small validation helpers (mirror the v1.20.x discipline)
# ---------------------------------------------------------------------------


def _validate_required_string(value: Any, *, field_name: str) -> str:
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


def _validate_non_negative_int(
    value: Any, *, field_name: str
) -> int:
    """Reject ``bool`` (which is otherwise an ``int`` subclass)
    and any negative int."""
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


def _scan_for_forbidden_keys(
    mapping: Mapping[str, Any], *, field_name: str
) -> None:
    """Reject any v1.21.0a forbidden field name appearing in a
    metadata or payload mapping."""
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if key in FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key {key!r} "
                "(v1.21.0a hard naming boundary — stress program "
                "records do not carry actor-decision / price / "
                "forecast / advice / real-data / Japan-calibration "
                "/ LLM / real-issuer / licensed-taxonomy / "
                "magnitude / probability / aggregate / composite "
                "/ net / dominant / interaction fields)"
            )


# ---------------------------------------------------------------------------
# StressStep
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StressStep:
    """Immutable record naming one stress step inside a
    :class:`StressProgramTemplate`. Wraps a v1.18.1
    ``scenario_driver_template_id`` plain-id citation with an
    ordinal ``step_index`` and a small set of label fields.

    A stress step is **the plan**, not a runtime application.
    The runtime emission lives in v1.21.2's
    :class:`StressProgramApplicationRecord` (not yet
    implemented). v1.21.1 ships storage only.

    Citation discipline: ``scenario_driver_template_id`` is a
    **plain-id citation** to a v1.18.1
    :class:`world.scenario_drivers.ScenarioDriverTemplate`. The
    storage layer does **not** resolve the citation. v1.21.2
    will validate at the apply-helper boundary.

    The dataclass:

    - has **no** ``stress_magnitude`` field — the design
      forbids magnitudes (see
      ``FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES``).
    - has **no** ``stress_probability_weight`` field — the
      design forbids probability weights.
    - has **no** ``decay_label`` / ``decay_coefficient`` /
      ``decay_*`` field — labels-not-numbers carries to the
      decay axis.
    - has **no** ``interaction_label`` /
      ``composition_label`` / ``output_context_label`` field
      — auto-inferred composition is deferred (see
      ``docs/v1_21_stress_composition_layer.md`` *Deferred:
      StressInteractionRule*).
    - has **no** ``expected_*`` / ``predicted_*`` /
      ``forecasted_*`` field — forecast-shaped tokens are
      forbidden.
    """

    stress_step_id: str
    parent_stress_program_template_id: str
    step_index: int
    scenario_driver_template_id: str
    event_date_policy_label: str = "ad_hoc"
    scheduled_month_label: str = "unknown"
    status: str = "active"
    visibility: str = "internal"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "stress_step_id",
        "parent_stress_program_template_id",
        "scenario_driver_template_id",
        "event_date_policy_label",
        "scheduled_month_label",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("event_date_policy_label", EVENT_DATE_POLICY_LABELS),
        ("scheduled_month_label",   SCHEDULED_MONTH_LABELS),
        ("status",                  STATUS_LABELS),
        ("visibility",              VISIBILITY_LABELS),
    )

    def __post_init__(self) -> None:
        # Trip-wire: a future field rename must not collide
        # with the v1.21.0a forbidden list. Pinned by
        # ``test_stress_program_fields_do_not_include_forbidden_names``.
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES:
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
            "step_index",
            _validate_non_negative_int(
                self.step_index, field_name="step_index"
            ),
        )
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(
            metadata_dict, field_name="metadata"
        )
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stress_step_id": self.stress_step_id,
            "parent_stress_program_template_id": (
                self.parent_stress_program_template_id
            ),
            "step_index": self.step_index,
            "scenario_driver_template_id": (
                self.scenario_driver_template_id
            ),
            "event_date_policy_label": (
                self.event_date_policy_label
            ),
            "scheduled_month_label": self.scheduled_month_label,
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# StressProgramTemplate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StressProgramTemplate:
    """Immutable record naming a *bundle* of v1.18.1 scenario
    drivers as an ordered stress program. The composition unit
    of the v1.21 sequence.

    Cardinality (binding):

    - 1 ≤ ``len(stress_steps)`` ≤ 3.
    - ``step_index`` values form a dense zero-based ordinal
      sequence ``(0, 1, …, n-1)``; duplicate indices are
      rejected.
    - ``stress_step_id`` values are unique within the program.

    Each step carries a plain-id citation to a v1.18.1
    :class:`world.scenario_drivers.ScenarioDriverTemplate`. The
    program itself does **not** resolve the citations.

    The dataclass:

    - has **no** ``aggregate_*`` / ``combined_*`` / ``net_*``
      / ``dominant_*`` / ``composite_*`` field — auto-
      reduction is forbidden.
    - has **no** ``interaction_*`` field — auto-inferred
      composition is deferred (see
      ``docs/v1_21_stress_composition_layer.md`` *Deferred:
      StressInteractionRule*).
    - has **no** ``expected_*`` / ``predicted_*`` /
      ``forecasted_*`` / ``stress_magnitude_*`` /
      ``stress_probability_weight`` field — forecast-shaped
      tokens are forbidden.
    """

    stress_program_template_id: str
    program_label: str
    program_purpose_label: str
    stress_steps: tuple[StressStep, ...]
    status: str = "active"
    visibility: str = "internal"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "stress_program_template_id",
        "program_label",
        "program_purpose_label",
        "status",
        "visibility",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("program_purpose_label", PROGRAM_PURPOSE_LABELS),
        ("status",                STATUS_LABELS),
        ("visibility",            VISIBILITY_LABELS),
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES:
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

        if not isinstance(self.stress_steps, tuple):
            object.__setattr__(
                self, "stress_steps", tuple(self.stress_steps)
            )
        steps = self.stress_steps
        for entry in steps:
            if not isinstance(entry, StressStep):
                raise ValueError(
                    "stress_steps entries must be StressStep "
                    f"instances; got {type(entry).__name__}"
                )

        if (
            len(steps) < PROGRAM_MIN_STEP_COUNT
            or len(steps) > PROGRAM_MAX_STEP_COUNT
        ):
            raise ValueError(
                "stress_steps must contain between "
                f"{PROGRAM_MIN_STEP_COUNT} and "
                f"{PROGRAM_MAX_STEP_COUNT} entries (v1.21.0a "
                f"cardinality binding); got {len(steps)}"
            )

        # Each step must reference *this* program's id (a plain-
        # id sanity check; the storage layer still does not
        # resolve the parent program in any other book).
        for step in steps:
            if (
                step.parent_stress_program_template_id
                != self.stress_program_template_id
            ):
                raise ValueError(
                    "stress_step.parent_stress_program_template_id "
                    f"({step.parent_stress_program_template_id!r}) "
                    "must match "
                    f"stress_program_template_id "
                    f"({self.stress_program_template_id!r})"
                )

        # Reject duplicate step ids and duplicate step indices.
        seen_ids: set[str] = set()
        seen_indices: set[int] = set()
        for step in steps:
            if step.stress_step_id in seen_ids:
                raise ValueError(
                    "duplicate stress_step_id in stress_steps: "
                    f"{step.stress_step_id!r}"
                )
            seen_ids.add(step.stress_step_id)
            if step.step_index in seen_indices:
                raise ValueError(
                    "duplicate step_index in stress_steps: "
                    f"{step.step_index}"
                )
            seen_indices.add(step.step_index)

        # Step indices must form a dense zero-based ordinal
        # sequence (0, 1, …, n-1). Pinning the dense form makes
        # the v1.21.2 ordinal-walk helper unambiguous.
        expected = set(range(len(steps)))
        if seen_indices != expected:
            raise ValueError(
                "step_index values must form a dense zero-based "
                f"sequence {sorted(expected)!r}; got "
                f"{sorted(seen_indices)!r}"
            )

        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(
            metadata_dict, field_name="metadata"
        )
        object.__setattr__(self, "metadata", metadata_dict)

    @property
    def step_count(self) -> int:
        return len(self.stress_steps)

    def steps_in_ordinal_order(self) -> tuple[StressStep, ...]:
        """Return the stress steps sorted by ``step_index`` so a
        downstream consumer (e.g. v1.21.2's helper) can walk them
        deterministically regardless of the construction order
        the caller used."""
        return tuple(
            sorted(self.stress_steps, key=lambda s: s.step_index)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stress_program_template_id": (
                self.stress_program_template_id
            ),
            "program_label": self.program_label,
            "program_purpose_label": self.program_purpose_label,
            "stress_steps": [
                s.to_dict() for s in self.stress_steps
            ],
            "step_count": self.step_count,
            "status": self.status,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# StressProgramBook
# ---------------------------------------------------------------------------


@dataclass
class StressProgramBook:
    """Append-only storage for v1.21.1 stress programs.

    Mirrors the v1.18.1 / v1.19.3 / v1.20.1 / v1.20.2 storage-
    book convention: emits **exactly one ledger record** per
    successful ``add_program(...)`` call (a single
    ``STRESS_PROGRAM_TEMPLATE_RECORDED`` event), no extra
    ledger record on duplicate id, mutates no other source-of-
    truth book.

    v1.21.0a deliberately stores **only program-level** ledger
    records — per-step ledger records are not emitted. Steps
    appear in the program record's payload as a list. Any
    future per-step record-type addition would have to be
    motivated by a downstream consumer that cannot walk the
    program record's payload itself (no such consumer exists in
    v1.21.x).

    Empty by default on the kernel — pinned by
    :func:`tests.test_stress_programs.test_world_kernel_empty_stress_program_book_by_default`
    and the digest trip-wire tests at v1.21.1.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _programs: dict[str, StressProgramTemplate] = field(
        default_factory=dict
    )

    def _now(self) -> datetime:
        if self.clock is not None:
            try:
                return self.clock.current_datetime()
            except Exception:
                pass
        return datetime.now(timezone.utc)

    def add_program(
        self,
        program: StressProgramTemplate,
        *,
        simulation_date: Any = None,
    ) -> StressProgramTemplate:
        if (
            program.stress_program_template_id
            in self._programs
        ):
            raise DuplicateStressProgramTemplateError(
                "Duplicate stress_program_template_id: "
                f"{program.stress_program_template_id!r}"
            )
        self._programs[
            program.stress_program_template_id
        ] = program

        if self.ledger is not None:
            payload = {
                "stress_program_template_id": (
                    program.stress_program_template_id
                ),
                "program_label": program.program_label,
                "program_purpose_label": (
                    program.program_purpose_label
                ),
                "step_count": program.step_count,
                "stress_steps": [
                    s.to_dict() for s in program.stress_steps
                ],
                "status": program.status,
                "visibility": program.visibility,
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
                    "stress_program_template_recorded"
                ),
                simulation_date=sim_date,
                object_id=program.stress_program_template_id,
                source=program.program_purpose_label,
                payload=payload,
                space_id="stress_programs",
                visibility=program.visibility,
            )
        return program

    def get_program(
        self, stress_program_template_id: str
    ) -> StressProgramTemplate:
        try:
            return self._programs[stress_program_template_id]
        except KeyError as exc:
            raise UnknownStressProgramTemplateError(
                "stress_program_template not found: "
                f"{stress_program_template_id!r}"
            ) from exc

    def list_programs(
        self,
    ) -> tuple[StressProgramTemplate, ...]:
        return tuple(self._programs.values())

    def list_by_status(
        self, status: str
    ) -> tuple[StressProgramTemplate, ...]:
        return tuple(
            p for p in self._programs.values() if p.status == status
        )

    def list_by_purpose(
        self, program_purpose_label: str
    ) -> tuple[StressProgramTemplate, ...]:
        return tuple(
            p
            for p in self._programs.values()
            if p.program_purpose_label == program_purpose_label
        )

    def list_steps_by_program(
        self, stress_program_template_id: str
    ) -> tuple[StressStep, ...]:
        program = self.get_program(stress_program_template_id)
        return program.steps_in_ordinal_order()

    def snapshot(self) -> dict[str, Any]:
        return {
            "stress_programs": [
                p.to_dict() for p in self._programs.values()
            ],
        }


__all__ = [
    "DuplicateStressProgramTemplateError",
    "EVENT_DATE_POLICY_LABELS",
    "FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES",
    "PROGRAM_MAX_STEP_COUNT",
    "PROGRAM_MIN_STEP_COUNT",
    "PROGRAM_PURPOSE_LABELS",
    "SCHEDULED_MONTH_LABELS",
    "STATUS_LABELS",
    "StressProgramBook",
    "StressProgramError",
    "StressProgramTemplate",
    "StressStep",
    "UnknownStressProgramTemplateError",
    "VISIBILITY_LABELS",
]
