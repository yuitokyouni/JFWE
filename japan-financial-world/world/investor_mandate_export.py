"""
v1.25.3 — Investor mandate readout export section.

Read-only descriptive-only export-side projection of a
kernel's
:class:`world.investor_mandate_readout.InvestorMandateReadout`.
v1.25.3 ships the export *section* — a tuple of one entry
per mandate profile carried inside
``RunExportBundle.investor_mandate_readout`` — and nothing
else. The section is omitted from
:meth:`RunExportBundle.to_dict` output when empty (the
default) so every pre-v1.25 bundle digest remains byte-
identical.

Allowed export keys (binding per design §13.1 + the
v1.25.0 / v1.25.2 closed-set whitelist):

- ``investor_id``
- ``mandate_profile_id``
- ``mandate_type_label``
- ``benchmark_pressure_label``
- ``liquidity_need_label``
- ``liability_horizon_label``
- ``stewardship_priority_labels``
- ``review_context_labels``
- ``selected_attention_bias_labels``
- ``cited_mandate_fields``
- ``warnings``

Forbidden export keys / values (binding):

- ``portfolio_allocation`` / ``target_weight`` /
  ``overweight`` / ``underweight`` / ``rebalance`` /
  ``weight_change`` / ``allocation_band``
- ``tracking_error_value`` / ``alpha`` /
  ``performance`` / ``expected_alpha``
- ``buy`` / ``sell`` / ``order`` / ``trade`` /
  ``execution``
- ``recommendation`` / ``investment_advice``
- ``expected_return`` / ``target_price`` /
  ``forecast`` / ``prediction``
- v1.18.0 / v1.19.0 / v1.21.0a / v1.22.0 / v1.24.0 /
  v1.25.0 forbidden tokens at any depth.

Read-only / no-mutation discipline:

- The helper does NOT call any apply / intent helper.
- The helper does NOT mutate any kernel book.
- The helper does NOT emit a ledger record (v1.25.3
  ships **no** new :class:`world.ledger.RecordType`).
- Same kernel state → byte-identical export section.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Mapping

from world.forbidden_tokens import (
    FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES,
)
from world.investor_mandate_readout import (
    InvestorMandateReadout,
    build_investor_mandate_readout,
)

if TYPE_CHECKING:
    from world.kernel import WorldKernel


__all__ = (
    "INVESTOR_MANDATE_READOUT_EXPORT_REQUIRED_KEYS",
    "build_investor_mandate_readout_export_section",
    "investor_mandate_readout_to_export_entry",
)


# v1.25.3 — descriptive-only key whitelist for the
# ``investor_mandate_readout`` payload section.
INVESTOR_MANDATE_READOUT_EXPORT_REQUIRED_KEYS: frozenset[str] = (
    frozenset(
        {
            "investor_id",
            "mandate_profile_id",
            "mandate_type_label",
            "benchmark_pressure_label",
            "liquidity_need_label",
            "liability_horizon_label",
            "stewardship_priority_labels",
            "review_context_labels",
            "selected_attention_bias_labels",
            "cited_mandate_fields",
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
    field_name: str = "investor_mandate_readout",
) -> None:
    """Scan an export entry against the v1.23.1 / v1.24.0
    / v1.25.0 canonical
    ``FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES`` composition
    at every key + every whole-string value at any depth."""
    for kind, item in _walk_keys_and_string_values(entry):
        if (
            kind == "key"
            and item
            in FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES
        ):
            raise ValueError(
                f"{field_name} entry contains forbidden "
                f"key {item!r} (v1.25.0 mandate boundary)"
            )
        if (
            kind == "value"
            and item
            in FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES
        ):
            raise ValueError(
                f"{field_name} entry contains forbidden "
                f"whole-string value {item!r} (v1.25.0 "
                "mandate boundary)"
            )


def investor_mandate_readout_to_export_entry(
    readout: InvestorMandateReadout,
) -> dict[str, Any]:
    """Project an :class:`InvestorMandateReadout` into the
    v1.25.3 descriptive-only export entry.

    Same readout → byte-identical entry. List-typed
    fields preserve the readout's emission order
    verbatim (no sorting, no de-duplication)."""
    if not isinstance(readout, InvestorMandateReadout):
        raise TypeError(
            "investor_mandate_readout_to_export_entry "
            "expects an InvestorMandateReadout instance"
        )
    entry: dict[str, Any] = {
        "investor_id": readout.investor_id,
        "mandate_profile_id": readout.mandate_profile_id,
        "mandate_type_label": readout.mandate_type_label,
        "benchmark_pressure_label": (
            readout.benchmark_pressure_label
        ),
        "liquidity_need_label": (
            readout.liquidity_need_label
        ),
        "liability_horizon_label": (
            readout.liability_horizon_label
        ),
        "stewardship_priority_labels": list(
            readout.stewardship_priority_labels
        ),
        "review_context_labels": list(
            readout.review_context_labels
        ),
        "selected_attention_bias_labels": list(
            readout.selected_attention_bias_labels
        ),
        "cited_mandate_fields": list(
            readout.cited_mandate_fields
        ),
        "warnings": list(readout.warnings),
    }
    _scan_export_entry_for_forbidden(entry)
    return entry


def build_investor_mandate_readout_export_section(
    kernel: "WorldKernel",
    *,
    mandate_profile_ids: Iterable[str] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return the v1.25.3 ``investor_mandate_readout``
    payload section for ``kernel``.

    Behaviour:

    - When ``kernel.investor_mandates`` is empty, returns
      ``()`` — the empty section. The export bundle's
      ``to_dict`` output omits the
      ``investor_mandate_readout`` key entirely,
      preserving byte-identity with pre-v1.25 bundles.
      **No digest movement.**
    - When ``kernel.investor_mandates`` has one or more
      profiles, returns a tuple of one entry per
      requested profile (or every profile if
      ``mandate_profile_ids`` is ``None``).

    Read-only:

    - Does not mutate ``kernel``.
    - Does not emit a ledger record.
    - Does not call any apply / intent helper.

    Same kernel state → byte-identical section.
    """
    book = getattr(kernel, "investor_mandates", None)
    if book is None:
        return ()
    profiles = book.list_profiles()
    if not profiles:
        return ()
    selected_ids: list[str]
    if mandate_profile_ids is None:
        selected_ids = [
            p.mandate_profile_id for p in profiles
        ]
    else:
        wanted = set(mandate_profile_ids)
        selected_ids = [
            p.mandate_profile_id
            for p in profiles
            if p.mandate_profile_id in wanted
        ]
    out: list[dict[str, Any]] = []
    for mid in selected_ids:
        readout = build_investor_mandate_readout(
            kernel, mandate_profile_id=mid
        )
        out.append(
            investor_mandate_readout_to_export_entry(readout)
        )
    return tuple(out)
