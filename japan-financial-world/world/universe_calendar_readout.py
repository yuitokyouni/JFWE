"""
v1.26.3 — Universe / calendar read-only readout.

Read-only multiset projection over the kernel's
:class:`world.universe_events.UniverseEventBook` +
:class:`world.reporting_calendar_profiles.ReportingCalendarProfileBook`
+ a caller-supplied ``as_of_period_id``.

Per the v1.26.0 design pin §3.5 + §7:

- Active-set computation walks events in
  ``effective_period_id`` lexicographic ascending order
  (with ``universe_event_id`` as tie-break) up to and
  **including** ``as_of_period_id``. ``entity_listed``
  / ``entity_renamed`` / ``entity_split`` add successors;
  ``entity_delisted`` / ``entity_merged`` / ``entity_renamed``
  / ``entity_split`` remove predecessors;
  ``entity_status_changed`` records the event but does
  not alter the active set; ``unknown`` events are
  surfaced as warnings without affecting the active
  set.
- Reporting-due semantics: the readout extracts a month
  label from ``as_of_period_id`` via a small
  deterministic rule (find the rightmost ``month_NN``
  substring; otherwise mark month label as
  ``"unknown"``). A profile is reporting-due if its
  ``quarterly_reporting_month_labels`` contains the
  extracted month label.

Read-only / no ledger emission / no kernel mutation /
no apply / intent / book-add helper call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Iterable, Mapping

from world.forbidden_tokens import (
    FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES,
)
from world.reporting_calendar_profiles import (
    ReportingCalendarProfile,
)
from world.universe_events import (
    UniverseEventRecord,
)

if TYPE_CHECKING:
    from world.kernel import WorldKernel


__all__ = (
    "UniverseCalendarReadout",
    "build_universe_calendar_readout",
    "render_universe_calendar_readout_markdown",
)


_BOUNDARY_STATEMENT_LINES: tuple[str, ...] = (
    "Read-only universe / calendar readout. ",
    "Multiset projection only — no causality claim. ",
    "No magnitude. No probability. No event-to-price ",
    "mapping. No earnings-surprise / event-study / ",
    "calendar-arbitrage inference. No portfolio / ",
    "universe weight. No allocation. No trade. No ",
    "order. No execution. No actor decision. No ",
    "investor action. No bank approval. No real data ",
    "ingestion. No real Japanese fiscal-year ",
    "distribution claim. No real institutional ",
    "identifiers. No Japan calibration. No LLM ",
    "execution.",
)


def _validate_required_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )
    return value


def _validate_string_tuple(
    value: Iterable[str], *, field_name: str
) -> tuple[str, ...]:
    normalised = tuple(value)
    for entry in normalised:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{field_name} entries must be non-empty"
            )
    return normalised


def _validate_count_pairs(
    value: Iterable[tuple[str, int]],
    *,
    field_name: str,
) -> tuple[tuple[str, int], ...]:
    normalised = tuple(value)
    for entry in normalised:
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise ValueError(
                f"{field_name} entries must be (str, int)"
            )
        label, count = entry
        if not isinstance(label, str) or not label:
            raise ValueError(
                f"{field_name} label must be non-empty"
            )
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError(
                f"{field_name} count must be int"
            )
        if count < 0:
            raise ValueError(
                f"{field_name} count must be >= 0"
            )
    return normalised


def _validate_non_neg_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be int")
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return value


def _scan_for_forbidden_keys(
    mapping: Mapping[str, Any], *, field_name: str
) -> None:
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if key in FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key "
                f"{key!r}"
            )


@dataclass(frozen=True)
class UniverseCalendarReadout:
    """Immutable, read-only universe / calendar
    multiset projection."""

    readout_id: str
    as_of_period_id: str
    active_entity_ids: tuple[str, ...]
    inactive_entity_ids: tuple[str, ...]
    lifecycle_event_ids: tuple[str, ...]
    listed_event_count: int
    delisted_event_count: int
    merged_event_count: int
    renamed_event_count: int
    split_event_count: int
    status_changed_event_count: int
    reporting_calendar_profile_ids: tuple[str, ...]
    reporting_due_entity_ids: tuple[str, ...]
    fiscal_year_end_month_counts: tuple[
        tuple[str, int], ...
    ]
    reporting_intensity_counts: tuple[
        tuple[str, int], ...
    ]
    disclosure_cluster_counts: tuple[
        tuple[str, int], ...
    ]
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "readout_id",
        "as_of_period_id",
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} forbidden"
                )
        for name in self.REQUIRED_STRING_FIELDS:
            _validate_required_string(
                getattr(self, name), field_name=name
            )
        for name in (
            "active_entity_ids",
            "inactive_entity_ids",
            "lifecycle_event_ids",
            "reporting_calendar_profile_ids",
            "reporting_due_entity_ids",
        ):
            object.__setattr__(
                self,
                name,
                _validate_string_tuple(
                    getattr(self, name), field_name=name
                ),
            )
        for name in (
            "listed_event_count",
            "delisted_event_count",
            "merged_event_count",
            "renamed_event_count",
            "split_event_count",
            "status_changed_event_count",
        ):
            object.__setattr__(
                self,
                name,
                _validate_non_neg_int(
                    getattr(self, name), field_name=name
                ),
            )
        for name in (
            "fiscal_year_end_month_counts",
            "reporting_intensity_counts",
            "disclosure_cluster_counts",
        ):
            object.__setattr__(
                self,
                name,
                _validate_count_pairs(
                    getattr(self, name), field_name=name
                ),
            )
        warnings = tuple(self.warnings)
        for entry in warnings:
            if not isinstance(entry, str) or not entry:
                raise ValueError(
                    "warnings must be non-empty strings"
                )
        object.__setattr__(self, "warnings", warnings)
        metadata_dict = dict(self.metadata)
        _scan_for_forbidden_keys(
            metadata_dict, field_name="metadata"
        )
        object.__setattr__(self, "metadata", metadata_dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "readout_id": self.readout_id,
            "as_of_period_id": self.as_of_period_id,
            "active_entity_ids": list(
                self.active_entity_ids
            ),
            "inactive_entity_ids": list(
                self.inactive_entity_ids
            ),
            "lifecycle_event_ids": list(
                self.lifecycle_event_ids
            ),
            "listed_event_count": self.listed_event_count,
            "delisted_event_count": (
                self.delisted_event_count
            ),
            "merged_event_count": self.merged_event_count,
            "renamed_event_count": (
                self.renamed_event_count
            ),
            "split_event_count": self.split_event_count,
            "status_changed_event_count": (
                self.status_changed_event_count
            ),
            "reporting_calendar_profile_ids": list(
                self.reporting_calendar_profile_ids
            ),
            "reporting_due_entity_ids": list(
                self.reporting_due_entity_ids
            ),
            "fiscal_year_end_month_counts": [
                list(p)
                for p in self.fiscal_year_end_month_counts
            ],
            "reporting_intensity_counts": [
                list(p) for p in self.reporting_intensity_counts
            ],
            "disclosure_cluster_counts": [
                list(p) for p in self.disclosure_cluster_counts
            ],
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_MONTH_LABEL_RE = re.compile(r"month_(0[1-9]|1[0-2])")


def _extract_month_label(
    as_of_period_id: str,
) -> str:
    """Extract a month label from a period id. The rule is
    deterministic: find the rightmost ``month_NN`` (NN in
    01..12) substring in the period id; if none, return
    ``"unknown"``."""
    matches = list(_MONTH_LABEL_RE.finditer(as_of_period_id))
    if not matches:
        return "unknown"
    return matches[-1].group(0)


def _ordered_count_pairs(
    items: Iterable[str],
) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return tuple(counts.items())


def _walk_active_set(
    events: tuple[UniverseEventRecord, ...],
    *,
    as_of_period_id: str,
) -> tuple[
    set[str], set[str], list[str], dict[str, int],
    list[str],
]:
    """Walk events in ``effective_period_id`` order up to
    and INCLUDING ``as_of_period_id``. Return
    ``(active_ids, ever_seen_ids, applied_event_ids,
    event_type_counts, warnings)``."""
    sorted_events = sorted(
        events,
        key=lambda e: (
            e.effective_period_id,
            e.universe_event_id,
        ),
    )
    active: set[str] = set()
    ever_seen: set[str] = set()
    applied: list[str] = []
    event_type_counts: dict[str, int] = {
        "entity_listed": 0,
        "entity_delisted": 0,
        "entity_merged": 0,
        "entity_renamed": 0,
        "entity_split": 0,
        "entity_status_changed": 0,
        "unknown": 0,
    }
    warnings: list[str] = []
    for ev in sorted_events:
        if ev.effective_period_id > as_of_period_id:
            break
        applied.append(ev.universe_event_id)
        ever_seen.update(ev.affected_entity_ids)
        ever_seen.update(ev.predecessor_entity_ids)
        ever_seen.update(ev.successor_entity_ids)
        et = ev.event_type_label
        if et in event_type_counts:
            event_type_counts[et] += 1
        if et == "entity_listed":
            for eid in ev.affected_entity_ids:
                active.add(eid)
        elif et == "entity_delisted":
            for eid in ev.affected_entity_ids:
                active.discard(eid)
        elif et in ("entity_merged", "entity_renamed", "entity_split"):
            for eid in ev.predecessor_entity_ids:
                active.discard(eid)
            for eid in ev.successor_entity_ids:
                active.add(eid)
        elif et == "entity_status_changed":
            # Recorded; active set unchanged.
            pass
        else:
            # ``unknown`` — surface a diagnostic; do not
            # mutate the active set.
            warnings.append(
                f"unknown event_type_label on event "
                f"{ev.universe_event_id!r}; active set "
                "unchanged"
            )
    return active, ever_seen, applied, event_type_counts, warnings


def build_universe_calendar_readout(
    kernel: "WorldKernel",
    *,
    as_of_period_id: str,
    readout_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> UniverseCalendarReadout:
    """Build a deterministic read-only universe / calendar
    readout. Read-only: no ledger emission, no kernel
    mutation, no apply / intent / book-add helper call."""
    if not isinstance(as_of_period_id, str) or not as_of_period_id:
        raise ValueError(
            "as_of_period_id must be a non-empty string"
        )

    universe_book = getattr(kernel, "universe_events", None)
    calendar_book = getattr(
        kernel, "reporting_calendars", None
    )
    events: tuple[UniverseEventRecord, ...] = (
        universe_book.list_events()
        if universe_book is not None
        else ()
    )
    profiles: tuple[ReportingCalendarProfile, ...] = (
        calendar_book.list_profiles()
        if calendar_book is not None
        else ()
    )

    active, ever_seen, applied, event_type_counts, warnings = (
        _walk_active_set(
            events, as_of_period_id=as_of_period_id
        )
    )
    inactive = ever_seen - active

    # Reporting-due semantics.
    month_label = _extract_month_label(as_of_period_id)
    reporting_due_entity_ids: list[str] = []
    seen_due: set[str] = set()
    for prof in profiles:
        if (
            month_label != "unknown"
            and month_label in prof.quarterly_reporting_month_labels
        ):
            if prof.entity_id not in seen_due:
                seen_due.add(prof.entity_id)
                reporting_due_entity_ids.append(
                    prof.entity_id
                )

    # Inactive-reporting-profile diagnostic.
    if profiles and (active or inactive):
        for prof in profiles:
            if prof.entity_id in inactive:
                warnings.append(
                    f"reporting_calendar_profile "
                    f"{prof.reporting_calendar_profile_id!r} "
                    f"cites inactive entity "
                    f"{prof.entity_id!r}"
                )

    fye_counts = _ordered_count_pairs(
        p.fiscal_year_end_month_label for p in profiles
    )
    intensity_counts = _ordered_count_pairs(
        p.reporting_intensity_label for p in profiles
    )
    disclosure_counts = _ordered_count_pairs(
        p.disclosure_cluster_label for p in profiles
    )

    if readout_id is None:
        readout_id = (
            f"universe_calendar_readout:{as_of_period_id}"
        )

    caller_metadata = dict(metadata or {})
    _scan_for_forbidden_keys(
        caller_metadata, field_name="metadata"
    )

    return UniverseCalendarReadout(
        readout_id=readout_id,
        as_of_period_id=as_of_period_id,
        active_entity_ids=tuple(sorted(active)),
        inactive_entity_ids=tuple(sorted(inactive)),
        lifecycle_event_ids=tuple(applied),
        listed_event_count=event_type_counts["entity_listed"],
        delisted_event_count=event_type_counts[
            "entity_delisted"
        ],
        merged_event_count=event_type_counts["entity_merged"],
        renamed_event_count=event_type_counts[
            "entity_renamed"
        ],
        split_event_count=event_type_counts["entity_split"],
        status_changed_event_count=event_type_counts[
            "entity_status_changed"
        ],
        reporting_calendar_profile_ids=tuple(
            p.reporting_calendar_profile_id
            for p in profiles
        ),
        reporting_due_entity_ids=tuple(
            reporting_due_entity_ids
        ),
        fiscal_year_end_month_counts=fye_counts,
        reporting_intensity_counts=intensity_counts,
        disclosure_cluster_counts=disclosure_counts,
        warnings=tuple(warnings),
        metadata=caller_metadata,
    )


def render_universe_calendar_readout_markdown(
    readout: UniverseCalendarReadout,
) -> str:
    if not isinstance(readout, UniverseCalendarReadout):
        raise TypeError(
            "readout must be a UniverseCalendarReadout"
        )
    out: list[str] = []
    out.append(
        f"# Universe / calendar readout — {readout.as_of_period_id}"
    )
    out.append("")

    out.append("## Universe / calendar readout")
    out.append("")
    out.append(f"- **Readout id**: `{readout.readout_id}`")
    out.append(
        f"- **As-of period**: `{readout.as_of_period_id}`"
    )
    out.append("")

    out.append("## Active entities")
    out.append("")
    if not readout.active_entity_ids:
        out.append("- (none)")
    else:
        for eid in readout.active_entity_ids:
            out.append(f"- `{eid}`")
    out.append("")

    out.append("## Inactive entities")
    out.append("")
    if not readout.inactive_entity_ids:
        out.append("- (none)")
    else:
        for eid in readout.inactive_entity_ids:
            out.append(f"- `{eid}`")
    out.append("")

    out.append("## Lifecycle event counts")
    out.append("")
    out.append(
        f"- `entity_listed`: {readout.listed_event_count}"
    )
    out.append(
        f"- `entity_delisted`: {readout.delisted_event_count}"
    )
    out.append(
        f"- `entity_merged`: {readout.merged_event_count}"
    )
    out.append(
        f"- `entity_renamed`: {readout.renamed_event_count}"
    )
    out.append(
        f"- `entity_split`: {readout.split_event_count}"
    )
    out.append(
        f"- `entity_status_changed`: "
        f"{readout.status_changed_event_count}"
    )
    out.append("")

    out.append("## Reporting calendar profiles")
    out.append("")
    if not readout.reporting_calendar_profile_ids:
        out.append("- (none)")
    else:
        for pid in readout.reporting_calendar_profile_ids:
            out.append(f"- `{pid}`")
    out.append("")

    out.append("## Reporting-due entities")
    out.append("")
    if not readout.reporting_due_entity_ids:
        out.append("- (none)")
    else:
        for eid in readout.reporting_due_entity_ids:
            out.append(f"- `{eid}`")
    out.append("")

    out.append("## Fiscal-year-end month distribution")
    out.append("")
    if not readout.fiscal_year_end_month_counts:
        out.append("- (none)")
    else:
        for label, count in (
            readout.fiscal_year_end_month_counts
        ):
            out.append(f"- `{label}`: {count}")
    out.append("")

    out.append(
        "## Disclosure cluster + reporting intensity distribution"
    )
    out.append("")
    out.append("**Disclosure cluster:**")
    if not readout.disclosure_cluster_counts:
        out.append("- (none)")
    else:
        for label, count in readout.disclosure_cluster_counts:
            out.append(f"- `{label}`: {count}")
    out.append("")
    out.append("**Reporting intensity:**")
    if not readout.reporting_intensity_counts:
        out.append("- (none)")
    else:
        for label, count in readout.reporting_intensity_counts:
            out.append(f"- `{label}`: {count}")
    out.append("")

    out.append("## Warnings")
    out.append("")
    if not readout.warnings:
        out.append("- (none)")
    else:
        for w in readout.warnings:
            out.append(f"- {w}")
    out.append("")

    out.append("## Boundary statement")
    out.append("")
    out.append("".join(_BOUNDARY_STATEMENT_LINES))
    out.append("")

    return "\n".join(out)
