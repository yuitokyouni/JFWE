"""
v1.24.3 — Manual annotation readout export section.

Read-only descriptive-only export-side projection of a
kernel's :class:`world.manual_annotation_readout.ManualAnnotationReadout`.
v1.24.3 ships the export *section* — a single dict carried
inside ``RunExportBundle.manual_annotation_readout`` — and
nothing else. The section is omitted from
:meth:`RunExportBundle.to_dict` output when empty (the
default) so every pre-v1.24 bundle digest remains byte-
identical.

Allowed export keys (binding per design §15 + §17):

- ``readout_id``
- ``annotation_ids``
- ``cited_record_ids``
- ``annotation_label_counts`` — list of two-element
  ``[label, count]`` lists
- ``annotations_by_scope`` — list of two-element
  ``[scope, count]`` lists
- ``unresolved_cited_record_ids``
- ``reviewer_role_counts`` — list of two-element
  ``[role, count]`` lists
- ``warnings``

Forbidden export keys / values (binding):

- ``impact`` / ``outcome`` / ``risk_score`` /
  ``forecast`` / ``prediction`` / ``recommendation`` /
  ``causal_effect`` / ``amplify`` / ``dampen`` /
  ``offset`` / ``dominant`` / ``net`` / ``composite`` /
  ``expected_return`` / ``target_price`` / ``buy`` /
  ``sell`` / ``trade`` / ``order`` / ``execution``.
- The export shape itself is scanned at construction
  time (key + whole-string value) against the v1.23.1
  canonical
  :data:`world.forbidden_tokens.FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES`
  composition.

Read-only / no-mutation discipline:

- The helper does NOT call
  :func:`world.stress_applications.apply_stress_program`,
  :func:`world.scenario_applications.apply_scenario_driver`,
  or
  :meth:`world.manual_annotations.ManualAnnotationBook.add_annotation`.
- The helper does NOT mutate any kernel book.
- The helper does NOT emit a ledger record (v1.24.3
  ships **no** new :class:`world.ledger.RecordType`).
- Same kernel state → byte-identical export section.

The deliberately-omitted ``note_text`` field (and the
boundary-flag mapping) are NOT projected into the export
section. v1.24.3 keeps the export descriptive-only;
free-form reviewer prose is not surfaced as part of the
canonical bundle shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Mapping

from world.forbidden_tokens import (
    FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES,
)
from world.manual_annotation_readout import (
    ManualAnnotationReadout,
    build_manual_annotation_readout,
)

if TYPE_CHECKING:
    from world.kernel import WorldKernel


__all__ = (
    "MANUAL_ANNOTATION_READOUT_EXPORT_REQUIRED_KEYS",
    "build_manual_annotation_readout_export_section",
    "manual_annotation_readout_to_export_entry",
)


# v1.24.3 — descriptive-only key whitelist for the
# ``manual_annotation_readout`` payload section. Mirrors
# the design pin §17 + the ``ManualAnnotationReadout``
# field set, minus ``metadata`` (opaque caller context
# is not surfaced in the export).
MANUAL_ANNOTATION_READOUT_EXPORT_REQUIRED_KEYS: frozenset[str] = (
    frozenset(
        {
            "readout_id",
            "annotation_ids",
            "cited_record_ids",
            "annotation_label_counts",
            "annotations_by_scope",
            "unresolved_cited_record_ids",
            "reviewer_role_counts",
            "warnings",
        }
    )
)


def _walk_keys_and_string_values(value: Any):
    """Walk a JSON-like value and yield every dict key +
    every string value at any depth."""
    if isinstance(value, str):
        yield ("value", value)
        return
    if isinstance(value, Mapping):
        for k, v in value.items():
            if isinstance(k, str):
                yield ("key", k)
            yield from _walk_keys_and_string_values(v)
        return
    if isinstance(value, (list, tuple)):
        for entry in value:
            yield from _walk_keys_and_string_values(entry)


def _scan_export_entry_for_forbidden(
    entry: Mapping[str, Any],
    *,
    field_name: str = "manual_annotation_readout",
) -> None:
    """Scan an export entry against the v1.23.1 canonical
    ``FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES`` composition
    at every key + every whole-string value."""
    for kind, item in _walk_keys_and_string_values(entry):
        if (
            kind == "key"
            and item in FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES
        ):
            raise ValueError(
                f"{field_name} entry contains forbidden "
                f"key {item!r} (v1.24.0 manual-annotation "
                "boundary)"
            )
        if (
            kind == "value"
            and item in FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES
        ):
            raise ValueError(
                f"{field_name} entry contains forbidden "
                f"whole-string value {item!r} (v1.24.0 "
                "manual-annotation boundary)"
            )


def manual_annotation_readout_to_export_entry(
    readout: ManualAnnotationReadout,
) -> dict[str, Any]:
    """Project a :class:`ManualAnnotationReadout` into the
    v1.24.3 descriptive-only export entry.

    The mapping mirrors
    :data:`MANUAL_ANNOTATION_READOUT_EXPORT_REQUIRED_KEYS`
    exactly. ``metadata`` is intentionally dropped; the
    v1.24.3 design pin restricts the export shape to
    plain-id citation surfaces and per-label /
    per-scope / per-role count lists.

    Same readout → byte-identical entry. List-typed
    fields preserve the readout's emission order
    verbatim (no sorting, no de-duplication).
    """
    if not isinstance(readout, ManualAnnotationReadout):
        raise TypeError(
            "manual_annotation_readout_to_export_entry "
            "expects a ManualAnnotationReadout instance"
        )
    entry: dict[str, Any] = {
        "readout_id": readout.readout_id,
        "annotation_ids": list(readout.annotation_ids),
        "cited_record_ids": list(
            readout.cited_record_ids
        ),
        "annotation_label_counts": [
            [label, count]
            for label, count in (
                readout.annotation_label_counts
            )
        ],
        "annotations_by_scope": [
            [scope, count]
            for scope, count in readout.annotations_by_scope
        ],
        "unresolved_cited_record_ids": list(
            readout.unresolved_cited_record_ids
        ),
        "reviewer_role_counts": [
            [role, count]
            for role, count in readout.reviewer_role_counts
        ],
        "warnings": list(readout.warnings),
    }
    _scan_export_entry_for_forbidden(entry)
    return entry


def build_manual_annotation_readout_export_section(
    kernel: "WorldKernel",
    *,
    annotation_ids: Iterable[str] = (),
    case_study_id: str | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return the v1.24.3 ``manual_annotation_readout``
    payload section for ``kernel``.

    Behaviour:

    - When ``kernel.manual_annotations`` is empty, returns
      ``()`` — the empty section. The export bundle's
      ``to_dict`` output omits the
      ``manual_annotation_readout`` key entirely,
      preserving byte-identity with pre-v1.24 bundles.
      **No digest movement.**
    - When ``kernel.manual_annotations`` has one or more
      records, returns a tuple of exactly one entry —
      the readout projected via
      :func:`manual_annotation_readout_to_export_entry`.

    Read-only:

    - Does not mutate ``kernel``.
    - Does not emit a ledger record.
    - Does not call
      :func:`world.stress_applications.apply_stress_program`.
    - Does not call
      :func:`world.scenario_applications.apply_scenario_driver`.
    - Does not call
      :meth:`world.manual_annotations.ManualAnnotationBook.add_annotation`.

    Same kernel state → byte-identical section.
    """
    book = getattr(kernel, "manual_annotations", None)
    if book is None:
        return ()
    if not book.list_annotations():
        return ()
    readout = build_manual_annotation_readout(
        kernel,
        annotation_ids=annotation_ids,
        case_study_id=case_study_id,
    )
    if readout.annotation_count == 0:
        return ()
    return (
        manual_annotation_readout_to_export_entry(readout),
    )
