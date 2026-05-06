"""
v1.25.2 — Investor mandate / benchmark-pressure read-only
attention / review-context readout.

Read-only descriptive projection that joins an
:class:`world.investor_mandates.InvestorMandateProfile` to
the v1.16.x investor-intent surface and exposes:

- ``review_context_labels`` — closed-set tuple describing
  which review contexts the investor's mandate emphasises
  (benchmark / liquidity / liability_horizon / stewardship /
  funding_access / governance / unknown);
- ``selected_attention_bias_labels`` — closed-set tuple
  describing which attention dimensions the mandate
  emphasises (market_access_review / liquidity_review /
  stewardship_review / capital_discipline_review /
  governance_review / disclosure_review / unknown);
- ``cited_mandate_fields`` — plain-id list of mandate fields
  that contributed to the projection (so a reviewer can
  trace which closed-set labels drove the projection);
- ``warnings`` — human-readable warnings (e.g. an
  investor without any registered mandate profile);
- ``metadata`` — opaque, scanned for forbidden keys.

Read-only discipline (binding):

- Re-running the helper on the same kernel state produces
  a byte-identical readout. Cat 1 determinism pin extends
  verbatim.
- The readout emits **no** ledger record; v1.25.2 ships
  no new :class:`world.ledger.RecordType`.
- The readout does **not** mutate any kernel book.
- The readout does **not** call
  :func:`world.stress_applications.apply_stress_program`,
  :func:`world.scenario_applications.apply_scenario_driver`,
  :meth:`world.investor_mandates.InvestorMandateBook.add_profile`,
  or any v1.15.x / v1.16.x investor-intent helper.
- **No automatic interpretation.** The readout never
  emits a market intent, never produces an investor
  action, never produces a recommendation, never reduces
  multiple mandates into a "combined" mandate, never
  outputs a risk score / forecast / target weight /
  expected return / target price.
- **No interaction inference.** No amplify / dampen /
  offset / coexist / aggregate / composite / net /
  dominant token in the readout's labels or markdown.

The mapping from mandate fields → bias / review-context
labels is **deterministic, rule-based, and small**; it
lives in this module as a few short tables, not as a
classifier or LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Iterable, Mapping

from world.forbidden_tokens import (
    FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES,
)
from world.investor_mandates import (
    InvestorMandateProfile,
)

if TYPE_CHECKING:
    from world.kernel import WorldKernel


__all__ = (
    "InvestorMandateReadout",
    "MANDATE_ATTENTION_BIAS_LABELS",
    "MANDATE_REVIEW_CONTEXT_LABELS",
    "build_investor_mandate_readout",
    "render_investor_mandate_readout_markdown",
)


# ---------------------------------------------------------------------------
# Closed-set vocabularies (binding for v1.25.2; pinned per
# v1.25.0 design §12.1).
# ---------------------------------------------------------------------------


# v1.25.2 — selected attention bias labels. Six
# mandate-driven attention dimensions + ``unknown``. The
# vocabulary aligns with the user task list: market_access /
# liquidity / stewardship / capital_discipline / governance /
# disclosure.
MANDATE_ATTENTION_BIAS_LABELS: frozenset[str] = frozenset(
    {
        "market_access_review",
        "liquidity_review",
        "stewardship_review",
        "capital_discipline_review",
        "governance_review",
        "disclosure_review",
        "unknown",
    }
)


# v1.25.2 — review context labels. Six mandate-driven
# review-context dimensions + ``unknown``. Aligns with the
# user task list: benchmark / liquidity /
# liability_horizon / stewardship / funding_access /
# governance.
MANDATE_REVIEW_CONTEXT_LABELS: frozenset[str] = frozenset(
    {
        "benchmark_context",
        "liquidity_context",
        "liability_horizon_context",
        "stewardship_context",
        "funding_access_context",
        "governance_context",
        "unknown",
    }
)


# ---------------------------------------------------------------------------
# Boundary statement carried verbatim into every rendered
# markdown summary. Mirrors the v1.21.3 / v1.23.3 / v1.24.2
# anti-claim block, scoped to the mandate readout surface.
# ---------------------------------------------------------------------------


_BOUNDARY_STATEMENT_LINES: tuple[str, ...] = (
    "Read-only investor mandate / benchmark-pressure ",
    "attention-review-context readout. Descriptive ",
    "projection only — no causality claim. ",
    "No magnitude. No probability. No tracking-error value. ",
    "No benchmark identifier. No portfolio allocation. ",
    "No target weight. No rebalancing. ",
    "No buy / sell / order / trade / execution. ",
    "No investor action. No recommendation. ",
    "No expected return. No target price. ",
    "No interaction inference (no `amplify` / `dampen` / ",
    "`offset` / `coexist` label). No aggregate / combined / ",
    "net / dominant / composite stress result. ",
    "No price formation. No real data ingestion. ",
    "No real institutional identifiers. No Japan calibration. ",
    "No LLM execution. No LLM prose as source-of-truth.",
)


# ---------------------------------------------------------------------------
# Deterministic field → label mappings (v1.25.2 binding).
# Each tuple is ``(closed_set_label_value, projected_label)``.
# The mapping is intentionally small; expanding it requires a
# fresh design pin.
# ---------------------------------------------------------------------------


_BENCHMARK_PRESSURE_TO_REVIEW_CONTEXT: tuple[
    tuple[str, str], ...
] = (
    ("none", "unknown"),
    ("low", "benchmark_context"),
    ("moderate", "benchmark_context"),
    ("high", "benchmark_context"),
    ("unknown", "unknown"),
)


_LIQUIDITY_NEED_TO_REVIEW_CONTEXT: tuple[
    tuple[str, str], ...
] = (
    ("low", "unknown"),
    ("moderate", "liquidity_context"),
    ("high", "liquidity_context"),
    ("unknown", "unknown"),
)


_LIABILITY_HORIZON_TO_REVIEW_CONTEXT: tuple[
    tuple[str, str], ...
] = (
    ("short", "liability_horizon_context"),
    ("medium", "liability_horizon_context"),
    ("long", "liability_horizon_context"),
    ("unknown", "unknown"),
)


_STEWARDSHIP_PRIORITY_TO_REVIEW_CONTEXT: tuple[
    tuple[str, str], ...
] = (
    ("capital_discipline", "stewardship_context"),
    ("governance_review", "governance_context"),
    ("climate_disclosure", "stewardship_context"),
    ("liquidity_resilience", "liquidity_context"),
    ("funding_access", "funding_access_context"),
    ("unknown", "unknown"),
)


_BENCHMARK_PRESSURE_TO_BIAS: tuple[
    tuple[str, str], ...
] = (
    ("none", "unknown"),
    ("low", "market_access_review"),
    ("moderate", "market_access_review"),
    ("high", "market_access_review"),
    ("unknown", "unknown"),
)


_LIQUIDITY_NEED_TO_BIAS: tuple[
    tuple[str, str], ...
] = (
    ("low", "unknown"),
    ("moderate", "liquidity_review"),
    ("high", "liquidity_review"),
    ("unknown", "unknown"),
)


_STEWARDSHIP_PRIORITY_TO_BIAS: tuple[
    tuple[str, str], ...
] = (
    ("capital_discipline", "capital_discipline_review"),
    ("governance_review", "governance_review"),
    ("climate_disclosure", "disclosure_review"),
    ("liquidity_resilience", "liquidity_review"),
    ("funding_access", "market_access_review"),
    ("unknown", "unknown"),
)


# ---------------------------------------------------------------------------
# Validation helpers
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
    normalised = tuple(value)
    for entry in normalised:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{field_name} entries must be non-empty "
                f"strings; got {entry!r}"
            )
    return normalised


def _validate_label_tuple(
    value: Iterable[str],
    allowed: frozenset[str],
    *,
    field_name: str,
) -> tuple[str, ...]:
    normalised = tuple(value)
    for entry in normalised:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{field_name} entries must be non-empty "
                f"strings; got {entry!r}"
            )
        if entry not in allowed:
            raise ValueError(
                f"{field_name} entry {entry!r} not in "
                f"{sorted(allowed)!r}"
            )
    return normalised


def _scan_for_forbidden_keys(
    mapping: Mapping[str, Any], *, field_name: str
) -> None:
    for key in mapping.keys():
        if not isinstance(key, str):
            continue
        if key in FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES:
            raise ValueError(
                f"{field_name} contains forbidden key "
                f"{key!r} (v1.25.0 mandate boundary)"
            )


# ---------------------------------------------------------------------------
# InvestorMandateReadout
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InvestorMandateReadout:
    """Immutable, read-only mandate-conditioned attention /
    review-context projection over a single
    :class:`InvestorMandateProfile`.

    Every field is one of: a plain-id string, a closed-set
    label string, a tuple of plain-id strings, a tuple of
    closed-set labels, a tuple of human-readable warnings,
    or an opaque metadata mapping scanned for forbidden
    keys.

    No field is a reduction. No field carries a magnitude,
    a probability, a tracking-error number, a target
    weight, an expected return, or a recommendation.
    """

    readout_id: str
    investor_id: str
    mandate_profile_id: str
    mandate_type_label: str
    benchmark_pressure_label: str
    liquidity_need_label: str
    liability_horizon_label: str
    stewardship_priority_labels: tuple[str, ...]
    review_context_labels: tuple[str, ...]
    selected_attention_bias_labels: tuple[str, ...]
    cited_mandate_fields: tuple[str, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "readout_id",
        "investor_id",
        "mandate_profile_id",
        "mandate_type_label",
        "benchmark_pressure_label",
        "liquidity_need_label",
        "liability_horizon_label",
    )

    def __post_init__(self) -> None:
        for fname in self.__dataclass_fields__.keys():
            if fname in FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES:
                raise ValueError(
                    f"dataclass field {fname!r} is in the "
                    "v1.25.0 mandate forbidden field-name "
                    "set"
                )
        for name in self.REQUIRED_STRING_FIELDS:
            _validate_required_string(
                getattr(self, name), field_name=name
            )
        object.__setattr__(
            self,
            "stewardship_priority_labels",
            _validate_string_tuple(
                self.stewardship_priority_labels,
                field_name="stewardship_priority_labels",
            ),
        )
        object.__setattr__(
            self,
            "review_context_labels",
            _validate_label_tuple(
                self.review_context_labels,
                MANDATE_REVIEW_CONTEXT_LABELS,
                field_name="review_context_labels",
            ),
        )
        object.__setattr__(
            self,
            "selected_attention_bias_labels",
            _validate_label_tuple(
                self.selected_attention_bias_labels,
                MANDATE_ATTENTION_BIAS_LABELS,
                field_name=(
                    "selected_attention_bias_labels"
                ),
            ),
        )
        object.__setattr__(
            self,
            "cited_mandate_fields",
            _validate_string_tuple(
                self.cited_mandate_fields,
                field_name="cited_mandate_fields",
            ),
        )
        warnings = tuple(self.warnings)
        for entry in warnings:
            if not isinstance(entry, str) or not entry:
                raise ValueError(
                    "warnings entries must be non-empty "
                    "strings"
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
            "investor_id": self.investor_id,
            "mandate_profile_id": self.mandate_profile_id,
            "mandate_type_label": self.mandate_type_label,
            "benchmark_pressure_label": (
                self.benchmark_pressure_label
            ),
            "liquidity_need_label": (
                self.liquidity_need_label
            ),
            "liability_horizon_label": (
                self.liability_horizon_label
            ),
            "stewardship_priority_labels": list(
                self.stewardship_priority_labels
            ),
            "review_context_labels": list(
                self.review_context_labels
            ),
            "selected_attention_bias_labels": list(
                self.selected_attention_bias_labels
            ),
            "cited_mandate_fields": list(
                self.cited_mandate_fields
            ),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# build_investor_mandate_readout — read-only helper
# ---------------------------------------------------------------------------


def _ordered_unique(
    items: Iterable[str],
) -> tuple[str, ...]:
    """De-duplicate a stream of strings preserving the
    order of first occurrence."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return tuple(out)


def _project_review_contexts(
    profile: InvestorMandateProfile,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return ``(review_context_labels,
    cited_mandate_fields)`` per the v1.25.2 deterministic
    mapping."""
    contexts: list[str] = []
    cited: list[str] = []

    bp_map = dict(_BENCHMARK_PRESSURE_TO_REVIEW_CONTEXT)
    bp_label = bp_map.get(
        profile.benchmark_pressure_label, "unknown"
    )
    if bp_label != "unknown":
        contexts.append(bp_label)
        cited.append("benchmark_pressure_label")

    ln_map = dict(_LIQUIDITY_NEED_TO_REVIEW_CONTEXT)
    ln_label = ln_map.get(
        profile.liquidity_need_label, "unknown"
    )
    if ln_label != "unknown":
        contexts.append(ln_label)
        cited.append("liquidity_need_label")

    lh_map = dict(_LIABILITY_HORIZON_TO_REVIEW_CONTEXT)
    lh_label = lh_map.get(
        profile.liability_horizon_label, "unknown"
    )
    if lh_label != "unknown":
        contexts.append(lh_label)
        cited.append("liability_horizon_label")

    sp_map = dict(_STEWARDSHIP_PRIORITY_TO_REVIEW_CONTEXT)
    for sp in profile.stewardship_priority_labels:
        sp_label = sp_map.get(sp, "unknown")
        if sp_label != "unknown":
            contexts.append(sp_label)
            cited.append("stewardship_priority_labels")

    if not contexts:
        contexts.append("unknown")
    return _ordered_unique(contexts), _ordered_unique(cited)


def _project_attention_bias(
    profile: InvestorMandateProfile,
) -> tuple[str, ...]:
    """Return the attention-bias label tuple per the
    v1.25.2 deterministic mapping."""
    out: list[str] = []
    bp_map = dict(_BENCHMARK_PRESSURE_TO_BIAS)
    bp = bp_map.get(profile.benchmark_pressure_label, "unknown")
    if bp != "unknown":
        out.append(bp)
    ln_map = dict(_LIQUIDITY_NEED_TO_BIAS)
    ln = ln_map.get(profile.liquidity_need_label, "unknown")
    if ln != "unknown":
        out.append(ln)
    sp_map = dict(_STEWARDSHIP_PRIORITY_TO_BIAS)
    for sp in profile.stewardship_priority_labels:
        b = sp_map.get(sp, "unknown")
        if b != "unknown":
            out.append(b)
    if not out:
        out.append("unknown")
    return _ordered_unique(out)


def build_investor_mandate_readout(
    kernel: "WorldKernel",
    *,
    mandate_profile_id: str,
    readout_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> InvestorMandateReadout:
    """Build a deterministic read-only mandate-conditioned
    attention / review-context readout over the kernel's
    :class:`InvestorMandateBook`.

    Read-only discipline (binding):

    - Does NOT call
      :func:`world.stress_applications.apply_stress_program`,
      :func:`world.scenario_applications.apply_scenario_driver`,
      :meth:`world.investor_mandates.InvestorMandateBook.add_profile`,
      or any v1.15.x / v1.16.x investor-intent helper.
    - Does NOT mutate any kernel book.
    - Does NOT emit a ledger record (v1.25.2 ships no
      new :class:`world.ledger.RecordType`).

    Same kernel state + same arguments → byte-identical
    readout.

    Raises :class:`world.investor_mandates.UnknownInvestorMandateProfileError`
    when the cited ``mandate_profile_id`` is not present
    in :attr:`world.kernel.WorldKernel.investor_mandates`.
    """
    profile = kernel.investor_mandates.get_profile(
        mandate_profile_id
    )

    review_contexts, cited_fields = (
        _project_review_contexts(profile)
    )
    attention_bias = _project_attention_bias(profile)

    warnings: list[str] = []
    if (
        len(review_contexts) == 1
        and review_contexts[0] == "unknown"
    ):
        warnings.append(
            "mandate profile has no projected review "
            "context labels (every closed-set label "
            "mapped to 'unknown')"
        )

    if readout_id is None:
        readout_id = (
            f"investor_mandate_readout:{mandate_profile_id}"
        )

    caller_metadata = dict(metadata or {})
    _scan_for_forbidden_keys(
        caller_metadata, field_name="metadata"
    )

    return InvestorMandateReadout(
        readout_id=readout_id,
        investor_id=profile.investor_id,
        mandate_profile_id=profile.mandate_profile_id,
        mandate_type_label=profile.mandate_type_label,
        benchmark_pressure_label=(
            profile.benchmark_pressure_label
        ),
        liquidity_need_label=profile.liquidity_need_label,
        liability_horizon_label=(
            profile.liability_horizon_label
        ),
        stewardship_priority_labels=tuple(
            profile.stewardship_priority_labels
        ),
        review_context_labels=review_contexts,
        selected_attention_bias_labels=attention_bias,
        cited_mandate_fields=cited_fields,
        warnings=tuple(warnings),
        metadata=caller_metadata,
    )


# ---------------------------------------------------------------------------
# render_investor_mandate_readout_markdown
# ---------------------------------------------------------------------------


def render_investor_mandate_readout_markdown(
    readout: InvestorMandateReadout,
) -> str:
    """Deterministic markdown rendering of an
    :class:`InvestorMandateReadout`. Same readout → same
    bytes.

    Sections:

    1. ``## Investor mandate readout`` — id + investor +
       mandate profile cited.
    2. ``## Mandate profile`` — closed-set label
       summary.
    3. ``## Review context labels (multiset)`` — projected
       review-context closed-set labels.
    4. ``## Selected attention bias labels (multiset)`` —
       projected attention-bias closed-set labels.
    5. ``## Cited mandate fields`` — plain-id list of the
       mandate fields that contributed.
    6. ``## Warnings`` — human-readable warnings.
    7. ``## Boundary statement`` — pinned anti-claim
       block.
    """
    if not isinstance(readout, InvestorMandateReadout):
        raise TypeError(
            "readout must be an InvestorMandateReadout; "
            f"got {type(readout).__name__}"
        )

    out: list[str] = []
    out.append(
        f"# Investor mandate readout — {readout.mandate_profile_id}"
    )
    out.append("")

    # 1. Header.
    out.append("## Investor mandate readout")
    out.append("")
    out.append(f"- **Readout id**: `{readout.readout_id}`")
    out.append(
        f"- **Investor id**: `{readout.investor_id}`"
    )
    out.append(
        f"- **Mandate profile id**: "
        f"`{readout.mandate_profile_id}`"
    )
    out.append("")

    # 2. Mandate profile (closed-set summary).
    out.append("## Mandate profile")
    out.append("")
    out.append(
        f"- **Mandate type**: `{readout.mandate_type_label}`"
    )
    out.append(
        "- **Benchmark pressure**: "
        f"`{readout.benchmark_pressure_label}`"
    )
    out.append(
        "- **Liquidity need**: "
        f"`{readout.liquidity_need_label}`"
    )
    out.append(
        "- **Liability horizon**: "
        f"`{readout.liability_horizon_label}`"
    )
    sp = readout.stewardship_priority_labels
    out.append(
        "- **Stewardship priorities**: "
        + (", ".join(f"`{s}`" for s in sp) if sp else "(none)")
    )
    out.append("")

    # 3. Review context labels.
    out.append("## Review context labels (multiset)")
    out.append("")
    if not readout.review_context_labels:
        out.append("- (none)")
    else:
        for label in readout.review_context_labels:
            out.append(f"- `{label}`")
    out.append("")

    # 4. Selected attention bias labels.
    out.append("## Selected attention bias labels (multiset)")
    out.append("")
    if not readout.selected_attention_bias_labels:
        out.append("- (none)")
    else:
        for label in (
            readout.selected_attention_bias_labels
        ):
            out.append(f"- `{label}`")
    out.append("")

    # 5. Cited mandate fields.
    out.append("## Cited mandate fields")
    out.append("")
    if not readout.cited_mandate_fields:
        out.append("- (none)")
    else:
        for fname in readout.cited_mandate_fields:
            out.append(f"- `{fname}`")
    out.append("")

    # 6. Warnings.
    out.append("## Warnings")
    out.append("")
    if not readout.warnings:
        out.append("- (none)")
    else:
        for w in readout.warnings:
            out.append(f"- {w}")
    out.append("")

    # 7. Boundary statement.
    out.append("## Boundary statement")
    out.append("")
    out.append("".join(_BOUNDARY_STATEMENT_LINES))
    out.append("")

    return "\n".join(out)
