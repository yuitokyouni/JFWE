"""
v1.25.4 — Investor mandate attention-context case study
helper.

Read-only helper that takes a stress-applied kernel + two
investor mandate profile ids and returns a deterministic
case-study report dict comparing how each profile
projects review-context labels + attention-bias labels
over the **same** v1.21.3 stress readout.

The case study demonstrates the v1.25.2 mandate-
conditioned attention/review-context contract: two
investors reviewing the same stress event under
different mandate profiles see different review-
context label sets — without producing trades,
allocations, recommendations, or any actor decision.

Read-only discipline (binding):

- The helper does NOT call
  :func:`world.stress_applications.apply_stress_program`,
  :func:`world.scenario_applications.apply_scenario_driver`,
  :meth:`world.investor_mandates.InvestorMandateBook.add_profile`,
  or any v1.15.x / v1.16.x investor-intent helper.
- The helper does NOT mutate any kernel book.
- The helper does NOT emit a ledger record (v1.25.4
  ships **no** new :class:`world.ledger.RecordType`).
- Same kernel state + same arguments → byte-identical
  report.

The report carries no portfolio allocation / target
weight / expected return / target price / forecast /
prediction / recommendation / actor decision / trade /
order / execution wording at any depth (verified by
the v1.25.4 pin tests).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Mapping

from world.forbidden_tokens import (
    FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES,
)
from world.investor_mandate_readout import (
    build_investor_mandate_readout,
)
from world.stress_readout import (
    build_stress_field_readout,
)

if TYPE_CHECKING:
    from world.kernel import WorldKernel


__all__ = (
    "build_investor_mandate_case_study_report",
    "render_investor_mandate_case_study_markdown",
)


# v1.25.4 — boundary statement carried verbatim into every
# rendered case-study summary. Mirrors the v1.21.3 / v1.23.3
# / v1.24.2 / v1.25.2 anti-claim block.
_CASE_STUDY_BOUNDARY_STATEMENT_LINES: tuple[str, ...] = (
    "Read-only investor mandate attention-context case ",
    "study. Descriptive projection only — no causality ",
    "claim. ",
    "No magnitude. No probability. No tracking-error value. ",
    "No portfolio allocation. No target weight. ",
    "No rebalancing. No buy / sell / order / trade / ",
    "execution. No investor action. No recommendation. ",
    "No expected return. No target price. ",
    "No interaction inference (no `amplify` / `dampen` / ",
    "`offset` / `coexist` label). No aggregate / combined / ",
    "net / dominant / composite stress result. ",
    "No price formation. No real data ingestion. ",
    "No real institutional identifiers. No Japan ",
    "calibration. No LLM execution.",
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


def _scan_metadata(metadata: Mapping[str, Any]) -> None:
    for kind, item in _walk_keys_and_string_values(metadata):
        if (
            kind == "key"
            and item
            in FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES
        ):
            raise ValueError(
                f"metadata contains forbidden key {item!r}"
            )


def build_investor_mandate_case_study_report(
    kernel: "WorldKernel",
    *,
    stress_program_application_id: str,
    mandate_profile_ids: Iterable[str],
    case_study_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic read-only case-study report
    over a stress-applied kernel + a list of investor
    mandate profile ids.

    Read-only discipline (binding) — see module
    docstring.

    The report shape is a plain ``dict`` (no new
    dataclass, no new RecordType). Every value is one
    of: a plain-id string, a tuple of plain-id strings,
    a tuple of (label, count) pairs, a tuple of human-
    readable warning strings, a small dict mapping
    investor id → label tuple, or the boundary
    statement string.

    Raises :class:`world.stress_applications.UnknownStressProgramApplicationError`
    when the cited ``stress_program_application_id`` is
    not present in the kernel; raises
    :class:`world.investor_mandates.UnknownInvestorMandateProfileError`
    when any cited mandate profile is missing.
    """
    profile_ids = tuple(mandate_profile_ids)
    if len(profile_ids) < 2:
        raise ValueError(
            "case study requires at least 2 mandate "
            "profile ids (the contrast is the point)"
        )
    if len(set(profile_ids)) != len(profile_ids):
        raise ValueError(
            "case study mandate_profile_ids contains "
            "duplicates"
        )

    stress_readout = build_stress_field_readout(
        kernel,
        stress_program_application_id=(
            stress_program_application_id
        ),
    )

    investor_ids: list[str] = []
    profile_ids_out: list[str] = []
    mandate_type_labels: list[str] = []
    review_context_labels_by_investor: dict[
        str, list[str]
    ] = {}
    attention_bias_labels_by_investor: dict[
        str, list[str]
    ] = {}
    cited_mandate_fields_union: list[str] = []
    seen_cited: set[str] = set()
    warnings: list[str] = []

    for mid in profile_ids:
        readout = build_investor_mandate_readout(
            kernel, mandate_profile_id=mid
        )
        profile_ids_out.append(mid)
        investor_ids.append(readout.investor_id)
        mandate_type_labels.append(
            readout.mandate_type_label
        )
        review_context_labels_by_investor[
            readout.investor_id
        ] = list(readout.review_context_labels)
        attention_bias_labels_by_investor[
            readout.investor_id
        ] = list(readout.selected_attention_bias_labels)
        for fname in readout.cited_mandate_fields:
            if fname not in seen_cited:
                seen_cited.add(fname)
                cited_mandate_fields_union.append(fname)
        for w in readout.warnings:
            warnings.append(
                f"profile {mid!r}: {w}"
            )

    # Diagnostic: did the two profiles project the same
    # review-context label set? If so, surface a warning
    # — the case study's whole point is to show
    # divergence, so identical projections is a
    # configuration smell.
    distinct_context_sets = {
        tuple(sorted(v))
        for v in review_context_labels_by_investor.values()
    }
    if len(distinct_context_sets) <= 1:
        warnings.append(
            "all investor profiles projected the same "
            "review_context_labels — the case study's "
            "contrast is degenerate"
        )

    if case_study_id is None:
        case_study_id = (
            "investor_mandate_case_study:"
            f"{stress_program_application_id}"
        )

    caller_metadata = dict(metadata or {})
    _scan_metadata(caller_metadata)

    return {
        "case_study_id": case_study_id,
        "stress_program_application_id": (
            stress_program_application_id
        ),
        "stress_readout_id": stress_readout.readout_id,
        "stress_program_template_id": (
            stress_readout.stress_program_template_id
        ),
        "investor_ids": tuple(investor_ids),
        "mandate_profile_ids": tuple(profile_ids_out),
        "mandate_type_labels": tuple(mandate_type_labels),
        "review_context_labels_by_investor": {
            inv: tuple(labels)
            for inv, labels in (
                review_context_labels_by_investor.items()
            )
        },
        "attention_bias_labels_by_investor": {
            inv: tuple(labels)
            for inv, labels in (
                attention_bias_labels_by_investor.items()
            )
        },
        "cited_mandate_fields": tuple(
            cited_mandate_fields_union
        ),
        "warnings": tuple(warnings),
        "metadata": caller_metadata,
        "boundary_statement": "".join(
            _CASE_STUDY_BOUNDARY_STATEMENT_LINES
        ),
    }


def render_investor_mandate_case_study_markdown(
    report: Mapping[str, Any],
) -> str:
    """Deterministic markdown rendering of the case-study
    report. Same report → byte-identical bytes.

    Sections:

    1. ``## Investor mandate case study`` — id +
       stress receipt + readout id.
    2. ``## Investors compared`` — investor / profile /
       mandate type tuple.
    3. ``## Review context labels by investor`` — per-
       investor closed-set label tuple.
    4. ``## Selected attention bias labels by investor``
       — per-investor closed-set bias tuple.
    5. ``## Cited mandate fields`` — plain-id list of
       mandate fields that contributed across investors.
    6. ``## Warnings`` — human-readable warnings.
    7. ``## Boundary statement`` — pinned anti-claim
       block.
    """
    if not isinstance(report, Mapping):
        raise TypeError(
            "report must be a Mapping; "
            f"got {type(report).__name__}"
        )

    out: list[str] = []
    out.append(
        "# Investor mandate case study — "
        f"{report.get('stress_program_template_id', '?')}"
    )
    out.append("")

    out.append("## Investor mandate case study")
    out.append("")
    out.append(
        "- **Case study id**: "
        f"`{report.get('case_study_id', '?')}`"
    )
    out.append(
        "- **Stress program application id**: "
        f"`{report.get('stress_program_application_id', '?')}`"
    )
    out.append(
        "- **Stress readout id**: "
        f"`{report.get('stress_readout_id', '?')}`"
    )
    out.append(
        "- **Stress program template id**: "
        f"`{report.get('stress_program_template_id', '?')}`"
    )
    out.append("")

    out.append("## Investors compared")
    out.append("")
    investor_ids = report.get("investor_ids", ()) or ()
    profile_ids = (
        report.get("mandate_profile_ids", ()) or ()
    )
    mandate_type_labels = (
        report.get("mandate_type_labels", ()) or ()
    )
    if not investor_ids:
        out.append("- (none)")
    else:
        for i in range(len(investor_ids)):
            inv = investor_ids[i]
            mid = (
                profile_ids[i]
                if i < len(profile_ids)
                else "?"
            )
            mtype = (
                mandate_type_labels[i]
                if i < len(mandate_type_labels)
                else "?"
            )
            out.append(
                f"- **Investor**: `{inv}` · "
                f"profile `{mid}` · type `{mtype}`"
            )
    out.append("")

    out.append("## Review context labels by investor")
    out.append("")
    rclbi = (
        report.get("review_context_labels_by_investor")
        or {}
    )
    if not rclbi:
        out.append("- (none)")
    else:
        for inv in sorted(rclbi.keys()):
            labels = rclbi.get(inv, ())
            label_str = (
                ", ".join(f"`{lbl}`" for lbl in labels)
                if labels
                else "(none)"
            )
            out.append(
                f"- **`{inv}`**: {label_str}"
            )
    out.append("")

    out.append("## Selected attention bias labels by investor")
    out.append("")
    ablbi = (
        report.get("attention_bias_labels_by_investor")
        or {}
    )
    if not ablbi:
        out.append("- (none)")
    else:
        for inv in sorted(ablbi.keys()):
            labels = ablbi.get(inv, ())
            label_str = (
                ", ".join(f"`{lbl}`" for lbl in labels)
                if labels
                else "(none)"
            )
            out.append(
                f"- **`{inv}`**: {label_str}"
            )
    out.append("")

    out.append("## Cited mandate fields")
    out.append("")
    cited = report.get("cited_mandate_fields", ()) or ()
    if not cited:
        out.append("- (none)")
    else:
        for fname in cited:
            out.append(f"- `{fname}`")
    out.append("")

    out.append("## Warnings")
    out.append("")
    warnings_list = report.get("warnings", ()) or ()
    if not warnings_list:
        out.append("- (none)")
    else:
        for w in warnings_list:
            out.append(f"- {w}")
    out.append("")

    out.append("## Boundary statement")
    out.append("")
    out.append(
        report.get(
            "boundary_statement",
            "".join(_CASE_STUDY_BOUNDARY_STATEMENT_LINES),
        )
    )
    out.append("")

    return "\n".join(out)
