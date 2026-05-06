"""
v1.21.3 — Stress field readout: read-only multiset projection
+ deterministic markdown summary.

v1.21.3 ships:

- :class:`StressFieldReadout` — one immutable frozen
  dataclass; a **read-only multiset projection** over a
  v1.21.2 :class:`StressProgramApplicationRecord` and the
  v1.18.2
  :class:`world.scenario_applications.ScenarioDriverApplicationRecord`
  / :class:`world.scenario_applications.ScenarioContextShiftRecord`
  records that the program application emitted.
- :func:`build_stress_field_readout` — the read-only helper.
  Walks the kernel's existing storage books to compute a
  descriptive view of which steps resolved, which did not,
  and which underlying v1.18.2 records were emitted.
- :func:`render_stress_field_summary_markdown` —
  deterministic markdown renderer; same readout → same
  markdown bytes.

Critical design constraints (binding, carried verbatim from
v1.21.0a):

- **Read-only.** The helper does not mutate the kernel, does
  not append ledger records, does not call
  :func:`world.stress_applications.apply_stress_program`,
  does not call
  :func:`world.scenario_applications.apply_scenario_driver`,
  and does not register any new template, schedule, program,
  or application. v1.21.3 emits **no** ledger event of any
  kind.
- **Multiset only.** The dataclass carries plain-id citations
  and label tuples preserved in emitted order. **No
  reductions.** No ``aggregate_*``, ``combined_*``, ``net_*``,
  ``dominant_*``, ``composite_*``, ``expected_*``,
  ``predicted_*``, ``forecasted_*``, ``stress_magnitude``,
  ``stress_probability_weight``, ``stress_amplification_score``,
  ``total_stress_intensity``, ``outcome``, ``impact``,
  ``result_score``, ``risk_score``, ``interaction_label``,
  ``composition_label``, or ``output_context_label`` field.
- **Partial application MUST be visible.** When a v1.21.2
  ``apply_stress_program(...)`` call had any unresolved step
  (the helper catches per-step exceptions and continues),
  :attr:`StressFieldReadout.unresolved_step_count` is > 0,
  :attr:`unresolved_step_ids` lists the affected step ids,
  :attr:`unresolved_reason_labels` lists a parallel
  closed-set reason label per unresolved step, and
  :attr:`warnings` carries one human-readable
  ``"partial application:"`` message + one warning per
  unresolved step. The markdown renderer surfaces all of
  this prominently before any other section.
- **Reasons are storage-existence checks, not effect
  inferences.** The closed set ``UNRESOLVED_REASON_LABELS``
  is small: ``template_missing`` (the cited
  ``scenario_driver_template_id`` is not in the kernel's
  v1.18.1 ``ScenarioDriverTemplateBook`` at readout time)
  and ``unknown_failure`` (the template exists; the v1.21.2
  helper's per-step ``apply_scenario_driver(...)`` raised
  for some other reason that the receipt did not preserve).
  The classification is a storage-existence audit — never a
  composition / interaction / effect inference.
- **No ledger emission.** v1.21.3 ships **no** new
  :class:`world.ledger.RecordType` value. Re-running the
  helper on the same input produces a byte-identical
  readout (same id, same multiset).

The module is **runtime-book-free**: it imports only the
v1.18.2 / v1.21.1 / v1.21.2 dataclasses + their book types
for type hints, and reads from ``kernel.scenario_drivers``,
``kernel.scenario_applications``, ``kernel.stress_programs``,
and ``kernel.stress_applications`` only. It never imports
``world.market_environment``, ``world.firm_state``,
``world.investor_intent``, ``world.financing_paths``,
``world.prices``, ``world.contracts``, or any other
source-of-truth book.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Iterable, Mapping, TYPE_CHECKING

from world.scenario_applications import (
    ScenarioContextShiftRecord,
    ScenarioDriverApplicationRecord,
)
from world.stress_applications import (
    FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES,
    StressProgramApplicationRecord,
    UnknownStressProgramApplicationError,
)
from world.stress_programs import (
    StressProgramTemplate,
    StressStep,
)

if TYPE_CHECKING:
    from world.kernel import WorldKernel


# ---------------------------------------------------------------------------
# Closed-set vocabularies
# ---------------------------------------------------------------------------


# Tiny closed set for the per-unresolved-step reason label.
# Carries forward the v1.21.0a discipline: labels-not-numbers,
# storage-existence audit only, no composition / interaction /
# effect inference. The classifier is :func:`_classify_unresolved_reason`
# below.
UNRESOLVED_REASON_LABELS: frozenset[str] = frozenset(
    {
        "template_missing",
        "unknown_failure",
    }
)


# v1.21.3 does not introduce new status / visibility
# vocabularies — readouts are derived projections, not
# canonical records.


# ---------------------------------------------------------------------------
# Hard naming boundary
#
# Mirrors v1.21.2 ``FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES``
# verbatim. v1.21.3 explicitly does NOT introduce additional
# tokens — the v1.21.0a list is exhaustive for the stress
# layer through v1.21.x.
# ---------------------------------------------------------------------------


FORBIDDEN_STRESS_READOUT_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_STRESS_APPLICATION_FIELD_NAMES
)


# ---------------------------------------------------------------------------
# Boundary statement (used by the markdown renderer; pinned so
# the rendered text always carries the same anti-claim block)
# ---------------------------------------------------------------------------


_BOUNDARY_STATEMENT_LINES: tuple[str, ...] = (
    "Synthetic stress program audit — append-only / read-only. ",
    "Multiset projection only — no causality claim. ",
    "No magnitude. No probability. No aggregate / combined / "
    "net / dominant / composite stress result. ",
    "No interaction inference (no `amplify` / `dampen` / "
    "`offset` / `coexist` label). ",
    "No price formation. No trading. No order. No execution. "
    "No clearing. No settlement. No financing execution. ",
    "No firm decision. No investor action. No bank approval "
    "logic. ",
    "No investment advice. No real data ingestion. No real "
    "indicator values. No real institutional identifiers. ",
    "No Japan calibration. No LLM execution. No LLM prose as "
    "source-of-truth.",
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _validate_required_string(
    value: Any, *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{field_name} must be a non-empty string"
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


def _scan_for_forbidden_keys(
    mapping: Mapping[str, Any], *, field_name: str
) -> None:
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if key in FORBIDDEN_STRESS_READOUT_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key {key!r} "
                "(v1.21.0a hard naming boundary — stress field "
                "readout records do not carry actor-decision / "
                "price / forecast / advice / real-data / "
                "Japan-calibration / LLM / real-issuer / "
                "licensed-taxonomy / magnitude / probability / "
                "aggregate / composite / net / dominant / "
                "interaction fields)"
            )


# ---------------------------------------------------------------------------
# StressFieldReadout
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StressFieldReadout:
    """Immutable, read-only multiset projection over a v1.21.2
    :class:`StressProgramApplicationRecord` and the underlying
    v1.18.2 records the program application emitted.

    Every field is one of:

    - a plain-id citation (``stress_program_application_id``,
      ``stress_program_template_id``, ``readout_id``,
      ``as_of_date``);
    - a non-negative count (``total_step_count``,
      ``resolved_step_count``, ``unresolved_step_count``);
    - a tuple of plain-id citations preserved in emitted /
      step-ordinal order (``active_step_ids``,
      ``unresolved_step_ids``,
      ``scenario_driver_template_ids``,
      ``scenario_application_ids``,
      ``scenario_context_shift_ids``,
      ``source_context_record_ids``,
      ``downstream_citation_ids``);
    - a tuple of closed-set label strings preserved in
      emitted order (``context_surface_labels``,
      ``shift_direction_labels``,
      ``scenario_family_labels``,
      ``unresolved_reason_labels``);
    - a tuple of human-readable warning strings
      (``warnings``);
    - an opaque metadata mapping scanned for forbidden keys
      (``metadata``).

    No field is a reduction. No field carries a magnitude, a
    probability, a forecast, a recommendation, or a
    composition / interaction label.
    """

    readout_id: str
    stress_program_application_id: str
    stress_program_template_id: str
    as_of_date: str
    total_step_count: int
    resolved_step_count: int
    unresolved_step_count: int
    active_step_ids: tuple[str, ...]
    unresolved_step_ids: tuple[str, ...]
    unresolved_reason_labels: tuple[str, ...]
    scenario_driver_template_ids: tuple[str, ...]
    scenario_application_ids: tuple[str, ...]
    scenario_context_shift_ids: tuple[str, ...]
    context_surface_labels: tuple[str, ...]
    shift_direction_labels: tuple[str, ...]
    scenario_family_labels: tuple[str, ...]
    source_context_record_ids: tuple[str, ...]
    downstream_citation_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "readout_id",
        "stress_program_application_id",
        "stress_program_template_id",
        "as_of_date",
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_STRESS_READOUT_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} is in the "
                    "v1.21.0a forbidden field-name set"
                )
        for name in self.REQUIRED_STRING_FIELDS:
            _validate_required_string(
                getattr(self, name), field_name=name
            )
        for name in (
            "total_step_count",
            "resolved_step_count",
            "unresolved_step_count",
        ):
            object.__setattr__(
                self,
                name,
                _validate_non_negative_int(
                    getattr(self, name), field_name=name
                ),
            )
        if (
            self.resolved_step_count
            + self.unresolved_step_count
            != self.total_step_count
        ):
            raise ValueError(
                "resolved_step_count + unresolved_step_count "
                f"({self.resolved_step_count} + "
                f"{self.unresolved_step_count}) must equal "
                f"total_step_count ({self.total_step_count})"
            )
        for name in (
            "active_step_ids",
            "unresolved_step_ids",
            "scenario_driver_template_ids",
            "scenario_application_ids",
            "scenario_context_shift_ids",
            "source_context_record_ids",
            "downstream_citation_ids",
        ):
            object.__setattr__(
                self,
                name,
                _validate_string_tuple(
                    getattr(self, name), field_name=name
                ),
            )
        # Label tuples — preserved as multisets, no reduction.
        for name in (
            "context_surface_labels",
            "shift_direction_labels",
            "scenario_family_labels",
        ):
            object.__setattr__(
                self,
                name,
                _validate_string_tuple(
                    getattr(self, name), field_name=name
                ),
            )
        # unresolved_reason_labels: closed set + length must
        # match unresolved_step_ids.
        object.__setattr__(
            self,
            "unresolved_reason_labels",
            _validate_label_tuple(
                self.unresolved_reason_labels,
                UNRESOLVED_REASON_LABELS,
                field_name="unresolved_reason_labels",
            ),
        )
        if (
            len(self.unresolved_reason_labels)
            != len(self.unresolved_step_ids)
        ):
            raise ValueError(
                "unresolved_reason_labels length "
                f"({len(self.unresolved_reason_labels)}) "
                "must match unresolved_step_ids length "
                f"({len(self.unresolved_step_ids)})"
            )
        # active_step_ids + unresolved_step_ids count check.
        if len(self.active_step_ids) != self.resolved_step_count:
            raise ValueError(
                "active_step_ids length "
                f"({len(self.active_step_ids)}) must equal "
                f"resolved_step_count ({self.resolved_step_count})"
            )
        if (
            len(self.unresolved_step_ids)
            != self.unresolved_step_count
        ):
            raise ValueError(
                "unresolved_step_ids length "
                f"({len(self.unresolved_step_ids)}) must equal "
                "unresolved_step_count "
                f"({self.unresolved_step_count})"
            )
        # warnings — opaque human-readable strings, but each
        # entry must be a non-empty string.
        warnings = tuple(self.warnings)
        for entry in warnings:
            if not isinstance(entry, str) or not entry:
                raise ValueError(
                    "warnings entries must be non-empty strings; "
                    f"got {entry!r}"
                )
        object.__setattr__(self, "warnings", warnings)
        # metadata — opaque but cannot smuggle a forbidden key.
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(
            metadata_dict, field_name="metadata"
        )
        object.__setattr__(self, "metadata", metadata_dict)

    @property
    def is_partial(self) -> bool:
        """True when at least one stress step did not produce
        a v1.18.2 application record."""
        return self.unresolved_step_count > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "readout_id": self.readout_id,
            "stress_program_application_id": (
                self.stress_program_application_id
            ),
            "stress_program_template_id": (
                self.stress_program_template_id
            ),
            "as_of_date": self.as_of_date,
            "total_step_count": self.total_step_count,
            "resolved_step_count": self.resolved_step_count,
            "unresolved_step_count": (
                self.unresolved_step_count
            ),
            "active_step_ids": list(self.active_step_ids),
            "unresolved_step_ids": list(
                self.unresolved_step_ids
            ),
            "unresolved_reason_labels": list(
                self.unresolved_reason_labels
            ),
            "scenario_driver_template_ids": list(
                self.scenario_driver_template_ids
            ),
            "scenario_application_ids": list(
                self.scenario_application_ids
            ),
            "scenario_context_shift_ids": list(
                self.scenario_context_shift_ids
            ),
            "context_surface_labels": list(
                self.context_surface_labels
            ),
            "shift_direction_labels": list(
                self.shift_direction_labels
            ),
            "scenario_family_labels": list(
                self.scenario_family_labels
            ),
            "source_context_record_ids": list(
                self.source_context_record_ids
            ),
            "downstream_citation_ids": list(
                self.downstream_citation_ids
            ),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# build_stress_field_readout — read-only helper
# ---------------------------------------------------------------------------


def _classify_unresolved_reason(
    *, kernel: "WorldKernel", scenario_driver_template_id: str
) -> str:
    """Storage-existence audit — never a composition / effect
    inference. Returns ``"template_missing"`` if the cited
    ``scenario_driver_template_id`` is not present in the
    kernel's v1.18.1 ``ScenarioDriverTemplateBook`` at readout
    time, ``"unknown_failure"`` otherwise."""
    try:
        kernel.scenario_drivers.get_template(
            scenario_driver_template_id
        )
    except Exception:
        return "template_missing"
    return "unknown_failure"


def _readout_id_for(
    stress_program_application_id: str,
) -> str:
    return (
        f"stress_field_readout:"
        f"{stress_program_application_id}"
    )


def build_stress_field_readout(
    kernel: "WorldKernel",
    *,
    stress_program_application_id: str,
    readout_id: str | None = None,
    downstream_citation_ids: Iterable[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> StressFieldReadout:
    """Read-only multiset projection over a v1.21.2
    :class:`StressProgramApplicationRecord` and the v1.18.2
    records the program application emitted.

    Behaviour pinned by the v1.21.0a-corrected design:

    - Reads only:
      * ``kernel.stress_applications`` — to fetch the named
        :class:`StressProgramApplicationRecord`;
      * ``kernel.stress_programs`` — to fetch the cited
        :class:`StressProgramTemplate`;
      * ``kernel.scenario_applications`` — to fetch the cited
        v1.18.2
        :class:`world.scenario_applications.ScenarioDriverApplicationRecord`
        / :class:`world.scenario_applications.ScenarioContextShiftRecord`
        records;
      * ``kernel.scenario_drivers`` — only when classifying
        unresolved-step reasons (storage-existence audit).
    - Does NOT call
      :func:`world.stress_applications.apply_stress_program`.
    - Does NOT call
      :func:`world.scenario_applications.apply_scenario_driver`.
    - Does NOT mutate any kernel book.
    - Does NOT emit any ledger record (v1.21.3 is read-only;
      no new RecordType).
    - Surfaces partial application via
      :attr:`StressFieldReadout.unresolved_step_count`,
      :attr:`unresolved_step_ids`,
      :attr:`unresolved_reason_labels`, and a parallel
      :attr:`warnings` list.

    Re-running the helper on the same kernel + same input
    arguments produces a byte-identical readout.

    Raises :class:`UnknownStressProgramApplicationError` when
    the cited ``stress_program_application_id`` is not present
    in :attr:`world.kernel.WorldKernel.stress_applications`.
    """
    receipt: StressProgramApplicationRecord = (
        kernel.stress_applications.get_application(
            stress_program_application_id
        )
    )
    program: StressProgramTemplate = (
        kernel.stress_programs.get_program(
            receipt.stress_program_template_id
        )
    )

    # Walk the program's steps in dense step_index order. This
    # preserves the v1.21.2 emission order without depending on
    # any per-step application_id format.
    ordered_steps: tuple[StressStep, ...] = (
        program.steps_in_ordinal_order()
    )
    total_step_count = len(ordered_steps)

    # Build the resolved-step set by reading v1.18.2
    # application records whose
    # ``metadata["stress_program_application_id"]`` matches
    # this receipt. The v1.21.2 helper writes that key on
    # every per-step apply_scenario_driver(...) call.
    v1_18_app_records_by_step: dict[
        str, ScenarioDriverApplicationRecord
    ] = {}
    for app in kernel.scenario_applications.list_applications():
        md = app.metadata or {}
        if (
            md.get("stress_program_application_id")
            == stress_program_application_id
        ):
            step_id = md.get("stress_step_id")
            if isinstance(step_id, str) and step_id:
                v1_18_app_records_by_step[step_id] = app

    # active_step_ids preserves dense step_index order.
    active_step_ids: list[str] = []
    unresolved_step_ids: list[str] = []
    unresolved_reason_labels: list[str] = []
    scenario_driver_template_ids: list[str] = []

    for step in ordered_steps:
        scenario_driver_template_ids.append(
            step.scenario_driver_template_id
        )
        if step.stress_step_id in v1_18_app_records_by_step:
            active_step_ids.append(step.stress_step_id)
        else:
            unresolved_step_ids.append(step.stress_step_id)
            reason = _classify_unresolved_reason(
                kernel=kernel,
                scenario_driver_template_id=(
                    step.scenario_driver_template_id
                ),
            )
            unresolved_reason_labels.append(reason)

    # Receipt's scenario_application_ids preserves step order
    # already (the v1.21.2 helper appended in the per-step
    # loop). We pass it through verbatim so the readout cites
    # the same multiset.
    scenario_application_ids = list(
        receipt.scenario_application_ids
    )
    scenario_context_shift_ids = list(
        receipt.scenario_context_shift_ids
    )

    # Read context-shift records to surface the per-shift
    # multisets. Preserve the order in which the receipt
    # cites the ids (which mirrors v1.18.2 emission order).
    shifts_by_id: dict[str, ScenarioContextShiftRecord] = {}
    for shift in (
        kernel.scenario_applications.list_context_shifts()
    ):
        shifts_by_id[shift.scenario_context_shift_id] = shift

    context_surface_labels: list[str] = []
    shift_direction_labels: list[str] = []
    scenario_family_labels: list[str] = []
    source_context_record_ids: list[str] = []
    seen_source_ids: set[str] = set()

    for shift_id in scenario_context_shift_ids:
        shift = shifts_by_id.get(shift_id)
        if shift is None:
            # Defensive: the receipt cites a shift id the
            # kernel no longer has. Record a warning later;
            # for now skip the per-shift projection.
            continue
        context_surface_labels.append(
            shift.context_surface_label
        )
        shift_direction_labels.append(
            shift.shift_direction_label
        )
        scenario_family_labels.append(
            shift.scenario_family_label
        )
        # source_context_record_ids — preserve order, but
        # de-dupe within the readout (the receipt already
        # exposes the cited ids verbatim; the readout
        # surfaces the union for inspection).
        for src_id in shift.affected_context_record_ids:
            if src_id not in seen_source_ids:
                seen_source_ids.add(src_id)
                source_context_record_ids.append(src_id)

    # Build warnings.
    warnings: list[str] = []
    unresolved_step_count = len(unresolved_step_ids)
    resolved_step_count = len(active_step_ids)
    if unresolved_step_count > 0:
        warnings.append(
            "partial application: "
            f"{resolved_step_count} of {total_step_count} "
            "steps resolved"
        )
        for step_id, reason in zip(
            unresolved_step_ids, unresolved_reason_labels
        ):
            warnings.append(
                f"step {step_id} unresolved ({reason})"
            )

    # Stale shift-id citations (defensive — should not happen
    # in v1.21.x but worth surfacing if a future change
    # decouples the shift book from the receipt).
    stale_count = len(scenario_context_shift_ids) - len(
        context_surface_labels
    )
    if stale_count > 0:
        warnings.append(
            f"{stale_count} cited context shift id(s) not "
            "found in kernel.scenario_applications"
        )

    if readout_id is None:
        readout_id = _readout_id_for(
            stress_program_application_id
        )

    caller_metadata = dict(metadata or {})
    _scan_for_forbidden_keys(
        caller_metadata, field_name="metadata"
    )

    return StressFieldReadout(
        readout_id=readout_id,
        stress_program_application_id=(
            stress_program_application_id
        ),
        stress_program_template_id=(
            receipt.stress_program_template_id
        ),
        as_of_date=receipt.as_of_date,
        total_step_count=total_step_count,
        resolved_step_count=resolved_step_count,
        unresolved_step_count=unresolved_step_count,
        active_step_ids=tuple(active_step_ids),
        unresolved_step_ids=tuple(unresolved_step_ids),
        unresolved_reason_labels=tuple(
            unresolved_reason_labels
        ),
        scenario_driver_template_ids=tuple(
            scenario_driver_template_ids
        ),
        scenario_application_ids=tuple(
            scenario_application_ids
        ),
        scenario_context_shift_ids=tuple(
            scenario_context_shift_ids
        ),
        context_surface_labels=tuple(context_surface_labels),
        shift_direction_labels=tuple(shift_direction_labels),
        scenario_family_labels=tuple(scenario_family_labels),
        source_context_record_ids=tuple(
            source_context_record_ids
        ),
        downstream_citation_ids=tuple(
            _validate_string_tuple(
                downstream_citation_ids,
                field_name="downstream_citation_ids",
            )
        ),
        warnings=tuple(warnings),
        metadata=caller_metadata,
    )


# ---------------------------------------------------------------------------
# render_stress_field_summary_markdown — deterministic renderer
# ---------------------------------------------------------------------------


def _format_multiset_line(label: str, items: tuple[str, ...]) -> str:
    """Format a multiset as a comma-separated list, preserving
    the input order. Empty multiset renders as ``(none)``."""
    if not items:
        return f"- **{label}**: (none)"
    return f"- **{label}**: " + ", ".join(items)


def _format_id_list(label: str, ids: tuple[str, ...]) -> str:
    if not ids:
        return f"- **{label}**: (none)"
    bullets = "\n".join(f"  - `{i}`" for i in ids)
    return f"- **{label}** ({len(ids)}):\n{bullets}"


def render_stress_field_summary_markdown(
    readout: StressFieldReadout,
) -> str:
    """Deterministic markdown rendering of a
    :class:`StressFieldReadout`. Same readout → same bytes.

    The rendered text:

    1. Opens with the program-application summary (cited ids,
       step count, as-of date).
    2. Surfaces step resolution prominently — when
       ``readout.is_partial`` is True, a **PARTIAL APPLICATION**
       banner appears before any other section, with the
       per-step reason list.
    3. Lists the emitted scenario applications.
    4. Lists the emitted context shifts.
    5. Surfaces the context-surface multiset preserved in
       emission order.
    6. Surfaces the shift-direction multiset preserved in
       emission order.
    7. Surfaces the scenario-family multiset preserved in
       emission order.
    8. Lists the warnings.
    9. Closes with the v1.21.3 boundary statement.

    The renderer emits no ``impact`` / ``outcome`` /
    ``amplification`` / ``dampening`` / ``offset effect`` /
    ``dominant stress`` / ``net pressure`` / ``composite
    risk`` / ``forecast`` / ``expected response`` /
    ``prediction`` / ``recommendation`` text. Pinned by
    :func:`tests.test_stress_readout.test_markdown_summary_contains_no_forecast_or_recommendation_language`.
    """
    if not isinstance(readout, StressFieldReadout):
        raise TypeError(
            "readout must be a StressFieldReadout; "
            f"got {type(readout).__name__}"
        )

    out: list[str] = []
    out.append(
        "# Stress field readout — "
        f"{readout.stress_program_template_id}"
    )
    out.append("")

    # 1. Program application summary.
    out.append("## Program application")
    out.append("")
    out.append(
        f"- **Readout id**: `{readout.readout_id}`"
    )
    out.append(
        "- **Stress program application id**: "
        f"`{readout.stress_program_application_id}`"
    )
    out.append(
        "- **Stress program template id**: "
        f"`{readout.stress_program_template_id}`"
    )
    out.append(
        f"- **As-of date**: `{readout.as_of_date}`"
    )
    out.append("")

    # 2. Step resolution.
    out.append("## Step resolution")
    out.append("")
    if readout.is_partial:
        out.append(
            "> **PARTIAL APPLICATION** — at least one stress "
            "step did not resolve. The cited stress program "
            "was applied as a partial set; some steps did "
            "**not** produce a v1.18.2 scenario application "
            "record. See the per-step reason list below."
        )
        out.append("")
    out.append(
        f"- **Total step count**: {readout.total_step_count}"
    )
    out.append(
        f"- **Resolved step count**: "
        f"{readout.resolved_step_count}"
    )
    out.append(
        f"- **Unresolved step count**: "
        f"{readout.unresolved_step_count}"
    )
    out.append(
        _format_id_list(
            "Active step ids (resolved)",
            readout.active_step_ids,
        )
    )
    if readout.unresolved_step_ids:
        out.append("")
        out.append(
            "- **Unresolved step ids** ("
            f"{len(readout.unresolved_step_ids)}):"
        )
        for step_id, reason in zip(
            readout.unresolved_step_ids,
            readout.unresolved_reason_labels,
        ):
            out.append(
                f"  - `{step_id}` — reason: `{reason}`"
            )
    else:
        out.append(
            _format_id_list(
                "Unresolved step ids", ()
            )
        )
    out.append("")

    # 3. Emitted scenario applications.
    out.append("## Emitted scenario applications")
    out.append("")
    out.append(
        _format_id_list(
            "Scenario application ids",
            readout.scenario_application_ids,
        )
    )
    out.append("")

    # 4. Emitted context shifts.
    out.append("## Emitted context shifts")
    out.append("")
    out.append(
        _format_id_list(
            "Scenario context shift ids",
            readout.scenario_context_shift_ids,
        )
    )
    out.append("")

    # 5. Context-surface multiset.
    out.append("## Context surfaces (multiset)")
    out.append("")
    out.append(
        _format_multiset_line(
            "Context surface labels",
            readout.context_surface_labels,
        )
    )
    out.append("")

    # 6. Shift-direction multiset.
    out.append("## Shift directions (multiset)")
    out.append("")
    out.append(
        _format_multiset_line(
            "Shift direction labels",
            readout.shift_direction_labels,
        )
    )
    out.append("")

    # 7. Scenario-family multiset.
    out.append("## Scenario families (multiset)")
    out.append("")
    out.append(
        _format_multiset_line(
            "Scenario family labels",
            readout.scenario_family_labels,
        )
    )
    out.append("")

    # Source context record ids (multiset).
    out.append("## Cited source context record ids")
    out.append("")
    out.append(
        _format_id_list(
            "Source context record ids",
            readout.source_context_record_ids,
        )
    )
    out.append("")

    # Downstream citations (optional).
    out.append("## Downstream citations")
    out.append("")
    out.append(
        _format_id_list(
            "Downstream citation ids",
            readout.downstream_citation_ids,
        )
    )
    out.append("")

    # 8. Warnings.
    out.append("## Warnings")
    out.append("")
    if readout.warnings:
        for w in readout.warnings:
            out.append(f"- {w}")
    else:
        out.append("- (none)")
    out.append("")

    # 9. Boundary statement.
    out.append("## Boundary statement")
    out.append("")
    out.append("".join(_BOUNDARY_STATEMENT_LINES))
    out.append("")

    return "\n".join(out)


__all__ = [
    "FORBIDDEN_STRESS_READOUT_FIELD_NAMES",
    "StressFieldReadout",
    "UNRESOLVED_REASON_LABELS",
    "UnknownStressProgramApplicationError",
    "build_stress_field_readout",
    "render_stress_field_summary_markdown",
]
