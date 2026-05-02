"""
v1.12.3 EvidenceRef + ActorContextFrame + EvidenceResolver.

A read-only **evidence resolution layer** that turns the ids an
actor selected (via ``SelectedObservationSet``) plus optional
explicit-id kwargs into a structured, actor-specific
``ActorContextFrame``. The frame is the *information bottleneck*
that future attention-conditioned mechanisms (v1.12.4 investor
intent, v1.12.5 valuation, v1.12.6 bank credit review, v1.12.7
next-period feedback) will consume — instead of silently
scanning all books for context, those mechanisms will read only
what the resolver surfaced for *this* actor on *this* date.

This milestone is a **substrate**, not a behavior change. Every
existing mechanism continues to consume evidence the way it did
before; v1.12.3 simply ships the resolver, the dataclasses, the
prefix dispatch, and the tests that pin the discipline. Future
v1.12.x milestones will refactor mechanisms one by one to
consume ``ActorContextFrame`` instead of evidence ids directly.

Per ``docs/world_model.md`` §83 and the v1.12.3 task spec:

- ``EvidenceRef`` — immutable record of one resolved evidence id
  plus its bucket and resolution status. Carries lightweight
  metadata only (id, type, source book, status); never the full
  record content. Confidential dialogue / engagement content
  must **not** flow through this layer.
- ``ActorContextFrame`` — immutable per-(actor, period) frame
  carrying the resolved evidence ids partitioned by bucket
  (signals / variable observations / exposures /
  market_conditions / market_readouts / market_environment_states
  / industry_conditions / firm_states / valuations / dialogues
  / escalation_candidates) plus the unresolved-ref tail.
- ``EvidenceResolver`` — read-only helper. Takes a kernel + an
  actor + selection ids + explicit ids; resolves each against
  the appropriate book by id-prefix dispatch; emits one
  ``ActorContextFrame``. Idempotent / deterministic / never
  mutates any source-of-truth book. By default it does **not**
  emit any ledger record either; a future audit milestone may
  optionally turn that on.
- ``EvidenceResolutionError`` — base error class.
- ``StrictEvidenceResolutionError`` — raised in strict mode when
  any cited id fails to resolve.

Anti-fields and anti-claims (binding)
-------------------------------------

The dataclasses store **only** ids and lightweight bucket /
status metadata. They deliberately have **no** ``content``,
``transcript``, ``notes``, ``minutes``, ``attendees``,
``order``, ``trade``, ``buy``, ``sell``, ``rebalance``,
``target_weight``, ``expected_return``, ``target_price``,
``recommendation``, ``investment_advice``, or
``portfolio_allocation`` field. Tests pin the absence on the
dataclass field set.

The resolver:

- writes nothing — no ledger record by default, no mutation of
  any other source-of-truth book in the kernel;
- reads only the ids the caller passes (the actor's
  selection refs + the caller's explicit-id kwargs); it does
  **not** scan the kernel's other books globally;
- never produces a price, yield, spread, index level, forecast,
  expected return, recommendation, target price, deal advice,
  order, trade, allocation, lending decision, voting / proxy
  filing / corporate-action execution, real financial number,
  Japan calibration, or LLM-agent execution;
- never enforces membership of any free-form tag against any
  controlled vocabulary;
- never copies confidential dialogue / engagement content into
  the frame — only the dialogue_id is surfaced.

Determinism
-----------

Resolution is order-preserving (input order is preserved per
bucket, with duplicates collapsed in first-seen order). This
keeps two fresh resolves of the same input byte-identical and
makes the frame safe to digest / canonicalize alongside the
v1.9.2 living-world replay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, ClassVar, Iterable, Mapping, Sequence

from world.attention import (
    AttentionBook,
    SelectedObservationSet,
    UnknownSelectedObservationSetError,
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class EvidenceResolutionError(Exception):
    """Base class for v1.12.3 evidence-resolution errors."""


class StrictEvidenceResolutionError(EvidenceResolutionError):
    """Raised when ``strict=True`` and at least one cited id
    fails to resolve."""


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


# ---------------------------------------------------------------------------
# Bucket vocabulary
# ---------------------------------------------------------------------------


# v1.12.3 bucket names — the canonical labels that appear on the
# frame's ``resolved_*`` slots, on every ``EvidenceRef.ref_type``,
# and in the deterministic prefix-dispatch table below.
BUCKET_SIGNAL: str = "signal"
BUCKET_VARIABLE_OBSERVATION: str = "variable_observation"
BUCKET_EXPOSURE: str = "exposure"
BUCKET_MARKET_CONDITION: str = "market_condition"
BUCKET_MARKET_READOUT: str = "market_readout"
BUCKET_MARKET_ENVIRONMENT_STATE: str = "market_environment_state"
BUCKET_INDUSTRY_CONDITION: str = "industry_condition"
BUCKET_FIRM_STATE: str = "firm_state"
BUCKET_VALUATION: str = "valuation"
BUCKET_DIALOGUE: str = "dialogue"
BUCKET_ESCALATION_CANDIDATE: str = "escalation_candidate"
# v1.12.4 — stewardship theme bucket. Added so the
# attention-conditioned investor-intent helper can resolve theme
# ids through the same substrate as every other piece of
# evidence; theme ids start with ``theme:`` per the v1.10.x
# orchestrator's id convention.
BUCKET_STEWARDSHIP_THEME: str = "stewardship_theme"

ALL_BUCKETS: tuple[str, ...] = (
    BUCKET_SIGNAL,
    BUCKET_VARIABLE_OBSERVATION,
    BUCKET_EXPOSURE,
    BUCKET_MARKET_CONDITION,
    BUCKET_MARKET_READOUT,
    BUCKET_MARKET_ENVIRONMENT_STATE,
    BUCKET_INDUSTRY_CONDITION,
    BUCKET_FIRM_STATE,
    BUCKET_VALUATION,
    BUCKET_DIALOGUE,
    BUCKET_ESCALATION_CANDIDATE,
    BUCKET_STEWARDSHIP_THEME,
)


STATUS_RESOLVED: str = "resolved"
STATUS_UNRESOLVED: str = "unresolved"


# ---------------------------------------------------------------------------
# EvidenceRef
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceRef:
    """
    Immutable record of one resolved evidence id plus its bucket
    and resolution status. Carries **only** id + lightweight
    metadata — no full record content, no confidential dialogue
    text, no attendee list, no transcript.

    Field semantics
    ---------------
    - ``ref_id`` is the cited id (non-empty string).
    - ``ref_type`` is the bucket label (one of ``ALL_BUCKETS``
      when ``status == "resolved"``; the literal
      ``"unresolved"`` is permitted as a placeholder when the
      caller wants a pre-bucket marker, but the resolver itself
      always assigns a real bucket label and uses ``status`` to
      flag resolution).
    - ``source_book`` is a free-form string naming the
      kernel-level book attribute (``"signals"`` /
      ``"variables"`` / ``"exposures"`` / ``"market_conditions"``
      / ``"capital_market_readouts"`` /
      ``"market_environments"`` / ``"industry_conditions"`` /
      ``"firm_financial_states"`` / ``"valuations"`` /
      ``"engagement"`` / ``"escalations"``). When unresolved, it
      is the string ``"unknown"``.
    - ``status`` is ``"resolved"`` or ``"unresolved"``.
    - ``metadata`` is free-form lightweight provenance (e.g., the
      origin slot — ``"selection"`` vs ``"explicit_kwarg"``).
      **Must not** carry confidential content.
    """

    ref_id: str
    ref_type: str
    source_book: str
    status: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "ref_id",
        "ref_type",
        "source_book",
        "status",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} is required")
        if self.status not in (STATUS_RESOLVED, STATUS_UNRESOLVED):
            raise ValueError(
                f"status must be {STATUS_RESOLVED!r} or "
                f"{STATUS_UNRESOLVED!r}; got {self.status!r}"
            )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "ref_id": self.ref_id,
            "ref_type": self.ref_type,
            "source_book": self.source_book,
            "status": self.status,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# ActorContextFrame
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActorContextFrame:
    """
    Immutable per-(actor, period) evidence frame.

    Bucketed resolved-id tuples carry only ids — no content. Two
    fresh resolves of the same input produce byte-identical
    frames; field declaration order pins the bucket order.

    Field semantics
    ---------------
    - ``context_frame_id`` — stable id; required and non-empty.
    - ``actor_id`` — actor whose attention this frame represents.
    - ``actor_type`` — small free-form tag (``"investor"`` /
      ``"bank"`` / ``"firm"`` / ``"reviewer"`` / etc.); the
      resolver does not enforce a vocabulary.
    - ``as_of_date`` — ISO ``YYYY-MM-DD`` string.
    - ``selected_observation_set_ids`` — selection ids the
      resolver walked. Stored as data; not validated against
      ``AttentionBook`` for resolution beyond what
      :func:`resolve_actor_context` did.
    - ``resolved_*_ids`` — eleven bucket tuples (one per bucket
      in :data:`ALL_BUCKETS`). Order is *first-seen* order,
      duplicates collapsed.
    - ``unresolved_refs`` — tuple of :class:`EvidenceRef`
      instances with ``status == "unresolved"`` in the order
      they were first encountered. The resolver never raises
      on unknown ids unless the caller passed ``strict=True``.
    - ``status`` is a small free-form lifecycle tag
      (``"resolved"`` / ``"partially_resolved"`` /
      ``"empty"``).
    - ``confidence`` is a synthetic ``[0.0, 1.0]`` ordering of
      how cleanly the inputs resolved. Defaults to ``1.0`` when
      every cited id resolved, falls below 1.0 proportionally
      when some failed. Booleans rejected. **Never** a
      calibrated probability.
    - ``metadata`` is free-form lightweight provenance; must
      **not** carry confidential dialogue content, attendee
      lists, named-client material, expert-interview content,
      transcripts, or non-public company information.

    Anti-fields
    -----------
    The frame deliberately has **no** ``content``,
    ``transcript``, ``notes``, ``minutes``, ``attendees``,
    ``order``, ``trade``, ``buy``, ``sell``, ``rebalance``,
    ``target_weight``, ``expected_return``, ``target_price``,
    ``recommendation``, ``investment_advice``,
    ``portfolio_allocation``, ``execution`` field. Tests pin
    the absence.
    """

    context_frame_id: str
    actor_id: str
    actor_type: str
    as_of_date: str
    status: str
    confidence: float
    selected_observation_set_ids: tuple[str, ...] = field(default_factory=tuple)
    resolved_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    resolved_variable_observation_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    resolved_exposure_ids: tuple[str, ...] = field(default_factory=tuple)
    resolved_market_condition_ids: tuple[str, ...] = field(default_factory=tuple)
    resolved_market_readout_ids: tuple[str, ...] = field(default_factory=tuple)
    resolved_market_environment_state_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    resolved_industry_condition_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    resolved_firm_state_ids: tuple[str, ...] = field(default_factory=tuple)
    resolved_valuation_ids: tuple[str, ...] = field(default_factory=tuple)
    resolved_dialogue_ids: tuple[str, ...] = field(default_factory=tuple)
    resolved_escalation_candidate_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    resolved_stewardship_theme_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    unresolved_refs: tuple[EvidenceRef, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "context_frame_id",
        "actor_id",
        "actor_type",
        "as_of_date",
        "status",
    )

    BUCKET_TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "selected_observation_set_ids",
        "resolved_signal_ids",
        "resolved_variable_observation_ids",
        "resolved_exposure_ids",
        "resolved_market_condition_ids",
        "resolved_market_readout_ids",
        "resolved_market_environment_state_ids",
        "resolved_industry_condition_ids",
        "resolved_firm_state_ids",
        "resolved_valuation_ids",
        "resolved_dialogue_ids",
        "resolved_escalation_candidate_ids",
        "resolved_stewardship_theme_ids",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, (str, date)) or (
                isinstance(value, str) and not value
            ):
                raise ValueError(f"{name} is required")

        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
        ):
            raise ValueError("confidence must be a number")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError(
                "confidence must be between 0 and 1 inclusive "
                "(synthetic ordering only; not a calibrated "
                "probability)"
            )
        object.__setattr__(self, "confidence", float(self.confidence))

        object.__setattr__(
            self, "as_of_date", _coerce_iso_date(self.as_of_date)
        )

        for tuple_field_name in self.BUCKET_TUPLE_FIELDS:
            value = getattr(self, tuple_field_name)
            normalized = _normalize_string_tuple(
                value, field_name=tuple_field_name
            )
            object.__setattr__(self, tuple_field_name, normalized)

        unresolved = tuple(self.unresolved_refs)
        for ref in unresolved:
            if not isinstance(ref, EvidenceRef):
                raise ValueError(
                    "unresolved_refs entries must be EvidenceRef "
                    f"instances; got {type(ref).__name__}"
                )
        object.__setattr__(self, "unresolved_refs", unresolved)

        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_frame_id": self.context_frame_id,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "as_of_date": self.as_of_date,
            "status": self.status,
            "confidence": self.confidence,
            "selected_observation_set_ids": list(
                self.selected_observation_set_ids
            ),
            "resolved_signal_ids": list(self.resolved_signal_ids),
            "resolved_variable_observation_ids": list(
                self.resolved_variable_observation_ids
            ),
            "resolved_exposure_ids": list(self.resolved_exposure_ids),
            "resolved_market_condition_ids": list(
                self.resolved_market_condition_ids
            ),
            "resolved_market_readout_ids": list(
                self.resolved_market_readout_ids
            ),
            "resolved_market_environment_state_ids": list(
                self.resolved_market_environment_state_ids
            ),
            "resolved_industry_condition_ids": list(
                self.resolved_industry_condition_ids
            ),
            "resolved_firm_state_ids": list(self.resolved_firm_state_ids),
            "resolved_valuation_ids": list(self.resolved_valuation_ids),
            "resolved_dialogue_ids": list(self.resolved_dialogue_ids),
            "resolved_escalation_candidate_ids": list(
                self.resolved_escalation_candidate_ids
            ),
            "resolved_stewardship_theme_ids": list(
                self.resolved_stewardship_theme_ids
            ),
            "unresolved_refs": [r.to_dict() for r in self.unresolved_refs],
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Prefix dispatch
# ---------------------------------------------------------------------------


# v1.12.3 deterministic id-prefix dispatch table. Order matters
# only if two prefixes collide (longer-prefix-first wins). Each
# entry is (id_prefix, bucket_label, kernel_book_attribute,
# getter_method_name).
#
# The resolver uses ``str.startswith`` against this table. The
# table is illustrative — it covers every id-prefix the v1.9 →
# v1.12.2 living-world fixture currently emits — and a future
# milestone can extend it without touching the dataclasses.
_PREFIX_TABLE: tuple[tuple[str, str, str, str], ...] = (
    # variable observations come *before* the bare "obs:" or
    # "exposure:" entries because their prefix is the longest
    # and matches first.
    (
        "obs:variable:",
        BUCKET_VARIABLE_OBSERVATION,
        "variables",
        "get_observation",
    ),
    (
        "exposure:",
        BUCKET_EXPOSURE,
        "exposures",
        "get_exposure",
    ),
    (
        "market_condition:",
        BUCKET_MARKET_CONDITION,
        "market_conditions",
        "get_condition",
    ),
    # capital-market readout ids start with ``readout:`` per
    # ``world.market_surface_readout._default_readout_id``.
    (
        "readout:",
        BUCKET_MARKET_READOUT,
        "capital_market_readouts",
        "get_readout",
    ),
    (
        "market_environment:",
        BUCKET_MARKET_ENVIRONMENT_STATE,
        "market_environments",
        "get_state",
    ),
    (
        "industry_condition:",
        BUCKET_INDUSTRY_CONDITION,
        "industry_conditions",
        "get_condition",
    ),
    (
        "firm_state:",
        BUCKET_FIRM_STATE,
        "firm_financial_states",
        "get_state",
    ),
    (
        "valuation:",
        BUCKET_VALUATION,
        "valuations",
        "get_valuation",
    ),
    (
        "dialogue:",
        BUCKET_DIALOGUE,
        "engagement",
        "get_dialogue",
    ),
    (
        "escalation:",
        BUCKET_ESCALATION_CANDIDATE,
        "escalations",
        "get_candidate",
    ),
    # v1.12.4 — stewardship theme prefix dispatch.
    (
        "theme:",
        BUCKET_STEWARDSHIP_THEME,
        "stewardship",
        "get_theme",
    ),
    # The ``signal:`` prefix is intentionally last among the
    # short-prefix entries so a more specific prefix gets a
    # chance to match first.
    (
        "signal:",
        BUCKET_SIGNAL,
        "signals",
        "get_signal",
    ),
)


_BUCKET_TO_FRAME_FIELD: Mapping[str, str] = {
    BUCKET_SIGNAL: "resolved_signal_ids",
    BUCKET_VARIABLE_OBSERVATION: "resolved_variable_observation_ids",
    BUCKET_EXPOSURE: "resolved_exposure_ids",
    BUCKET_MARKET_CONDITION: "resolved_market_condition_ids",
    BUCKET_MARKET_READOUT: "resolved_market_readout_ids",
    BUCKET_MARKET_ENVIRONMENT_STATE: "resolved_market_environment_state_ids",
    BUCKET_INDUSTRY_CONDITION: "resolved_industry_condition_ids",
    BUCKET_FIRM_STATE: "resolved_firm_state_ids",
    BUCKET_VALUATION: "resolved_valuation_ids",
    BUCKET_DIALOGUE: "resolved_dialogue_ids",
    BUCKET_ESCALATION_CANDIDATE: "resolved_escalation_candidate_ids",
    BUCKET_STEWARDSHIP_THEME: "resolved_stewardship_theme_ids",
}


def _classify_by_prefix(
    ref_id: str,
) -> tuple[str | None, str | None, str | None]:
    """Return ``(bucket, source_book, getter_method_name)`` for
    ``ref_id`` based on the v1.12.3 prefix table, or
    ``(None, None, None)`` if no prefix matches."""
    for prefix, bucket, source_book, getter in _PREFIX_TABLE:
        if ref_id.startswith(prefix):
            return bucket, source_book, getter
    return None, None, None


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceResolver:
    """
    Read-only evidence resolution helper.

    Parameters
    ----------
    kernel
        The :class:`world.kernel.WorldKernel` to read from. The
        resolver never mutates the kernel; it only calls the
        per-book getters (``get_signal`` / ``get_observation`` /
        etc.) to confirm an id resolves. Unresolved ids are
        recorded as data on the frame's ``unresolved_refs`` tail
        and never raise unless ``strict=True``.

    Notes
    -----
    Instances are cheap and immutable; the resolver carries no
    per-call state. v1.12.3 ships one stateless helper because
    every interesting input lives on the call's keyword args.
    """

    kernel: Any

    def resolve_actor_context(
        self,
        *,
        actor_id: str,
        actor_type: str,
        as_of_date: date | str,
        selected_observation_set_ids: Sequence[str] = (),
        explicit_signal_ids: Sequence[str] = (),
        explicit_variable_observation_ids: Sequence[str] = (),
        explicit_exposure_ids: Sequence[str] = (),
        explicit_market_condition_ids: Sequence[str] = (),
        explicit_market_readout_ids: Sequence[str] = (),
        explicit_market_environment_state_ids: Sequence[str] = (),
        explicit_industry_condition_ids: Sequence[str] = (),
        explicit_firm_state_ids: Sequence[str] = (),
        explicit_valuation_ids: Sequence[str] = (),
        explicit_dialogue_ids: Sequence[str] = (),
        explicit_escalation_candidate_ids: Sequence[str] = (),
        explicit_stewardship_theme_ids: Sequence[str] = (),
        context_frame_id: str | None = None,
        strict: bool = False,
        metadata: Mapping[str, Any] | None = None,
    ) -> ActorContextFrame:
        """Resolve evidence for one (actor, period) pair into an
        :class:`ActorContextFrame`. See module docstring for the
        full contract.
        """
        return resolve_actor_context(
            self.kernel,
            actor_id=actor_id,
            actor_type=actor_type,
            as_of_date=as_of_date,
            selected_observation_set_ids=selected_observation_set_ids,
            explicit_signal_ids=explicit_signal_ids,
            explicit_variable_observation_ids=explicit_variable_observation_ids,
            explicit_exposure_ids=explicit_exposure_ids,
            explicit_market_condition_ids=explicit_market_condition_ids,
            explicit_market_readout_ids=explicit_market_readout_ids,
            explicit_market_environment_state_ids=(
                explicit_market_environment_state_ids
            ),
            explicit_industry_condition_ids=explicit_industry_condition_ids,
            explicit_firm_state_ids=explicit_firm_state_ids,
            explicit_valuation_ids=explicit_valuation_ids,
            explicit_dialogue_ids=explicit_dialogue_ids,
            explicit_escalation_candidate_ids=explicit_escalation_candidate_ids,
            explicit_stewardship_theme_ids=explicit_stewardship_theme_ids,
            context_frame_id=context_frame_id,
            strict=strict,
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# Module-level resolve helper (callable directly)
# ---------------------------------------------------------------------------


_EXPLICIT_BUCKET_KWARGS: tuple[tuple[str, str], ...] = (
    ("explicit_signal_ids", BUCKET_SIGNAL),
    ("explicit_variable_observation_ids", BUCKET_VARIABLE_OBSERVATION),
    ("explicit_exposure_ids", BUCKET_EXPOSURE),
    ("explicit_market_condition_ids", BUCKET_MARKET_CONDITION),
    ("explicit_market_readout_ids", BUCKET_MARKET_READOUT),
    (
        "explicit_market_environment_state_ids",
        BUCKET_MARKET_ENVIRONMENT_STATE,
    ),
    ("explicit_industry_condition_ids", BUCKET_INDUSTRY_CONDITION),
    ("explicit_firm_state_ids", BUCKET_FIRM_STATE),
    ("explicit_valuation_ids", BUCKET_VALUATION),
    ("explicit_dialogue_ids", BUCKET_DIALOGUE),
    ("explicit_escalation_candidate_ids", BUCKET_ESCALATION_CANDIDATE),
    ("explicit_stewardship_theme_ids", BUCKET_STEWARDSHIP_THEME),
)


_BUCKET_TO_SOURCE_BOOK: Mapping[str, str] = {
    BUCKET_SIGNAL: "signals",
    BUCKET_VARIABLE_OBSERVATION: "variables",
    BUCKET_EXPOSURE: "exposures",
    BUCKET_MARKET_CONDITION: "market_conditions",
    BUCKET_MARKET_READOUT: "capital_market_readouts",
    BUCKET_MARKET_ENVIRONMENT_STATE: "market_environments",
    BUCKET_INDUSTRY_CONDITION: "industry_conditions",
    BUCKET_FIRM_STATE: "firm_financial_states",
    BUCKET_VALUATION: "valuations",
    BUCKET_DIALOGUE: "engagement",
    BUCKET_ESCALATION_CANDIDATE: "escalations",
    BUCKET_STEWARDSHIP_THEME: "stewardship",
}


_BUCKET_TO_GETTER: Mapping[str, str] = {
    BUCKET_SIGNAL: "get_signal",
    BUCKET_VARIABLE_OBSERVATION: "get_observation",
    BUCKET_EXPOSURE: "get_exposure",
    BUCKET_MARKET_CONDITION: "get_condition",
    BUCKET_MARKET_READOUT: "get_readout",
    BUCKET_MARKET_ENVIRONMENT_STATE: "get_state",
    BUCKET_INDUSTRY_CONDITION: "get_condition",
    BUCKET_FIRM_STATE: "get_state",
    BUCKET_VALUATION: "get_valuation",
    BUCKET_DIALOGUE: "get_dialogue",
    BUCKET_ESCALATION_CANDIDATE: "get_candidate",
    BUCKET_STEWARDSHIP_THEME: "get_theme",
}


def _default_context_frame_id(
    actor_id: str, as_of_date: str
) -> str:
    return f"context_frame:{actor_id}:{as_of_date}"


def _resolve_one(
    kernel: Any,
    *,
    ref_id: str,
    bucket: str,
    source_book: str,
    getter: str,
) -> bool:
    """Best-effort resolve of one id against the named getter.
    Returns True iff the getter returned without error."""
    book = getattr(kernel, source_book, None)
    if book is None:
        return False
    method = getattr(book, getter, None)
    if method is None:
        return False
    try:
        method(ref_id)
    except Exception:
        return False
    return True


def _append_unique(
    bucket_to_ids: dict[str, list[str]], bucket: str, ref_id: str
) -> None:
    """Append ``ref_id`` to ``bucket_to_ids[bucket]`` only if it
    is not already there. Preserves first-seen order."""
    ids = bucket_to_ids.setdefault(bucket, [])
    if ref_id not in ids:
        ids.append(ref_id)


def resolve_actor_context(
    kernel: Any,
    *,
    actor_id: str,
    actor_type: str,
    as_of_date: date | str,
    selected_observation_set_ids: Sequence[str] = (),
    explicit_signal_ids: Sequence[str] = (),
    explicit_variable_observation_ids: Sequence[str] = (),
    explicit_exposure_ids: Sequence[str] = (),
    explicit_market_condition_ids: Sequence[str] = (),
    explicit_market_readout_ids: Sequence[str] = (),
    explicit_market_environment_state_ids: Sequence[str] = (),
    explicit_industry_condition_ids: Sequence[str] = (),
    explicit_firm_state_ids: Sequence[str] = (),
    explicit_valuation_ids: Sequence[str] = (),
    explicit_dialogue_ids: Sequence[str] = (),
    explicit_escalation_candidate_ids: Sequence[str] = (),
    explicit_stewardship_theme_ids: Sequence[str] = (),
    context_frame_id: str | None = None,
    strict: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> ActorContextFrame:
    """
    Resolve evidence for one ``(actor, period)`` pair into an
    :class:`ActorContextFrame`. Read-only over the kernel; never
    mutates any source-of-truth book; never emits a ledger
    record.

    Behavior
    --------
    - Walks ``selected_observation_set_ids`` against
      ``kernel.attention``; for each resolved selection's
      ``selected_refs``, classifies each ref by id-prefix and
      attempts to resolve it against the matching book. Selections
      that themselves fail to resolve become an unresolved-ref
      entry with ``ref_type="selection"``; their selected_refs
      contribution is empty.
    - Walks each ``explicit_*_ids`` kwarg with the bucket the
      kwarg names. The explicit kwargs take precedence over the
      prefix table — a caller who passes
      ``explicit_signal_ids=("intent:foo",)`` lands "intent:foo"
      in the signal bucket regardless of its actual prefix. This
      lets callers override the dispatch when their ids do not
      follow the orchestrator's id conventions.
    - Each cited id is resolved against the appropriate book
      (``getattr(kernel, source_book).get_*(ref_id)``). A
      successful return puts the id in the bucket's
      ``resolved_*_ids`` tuple; a raise puts it in
      ``unresolved_refs``.
    - When ``strict=True`` and at least one cited id failed to
      resolve (selection-or-ref), raises
      :class:`StrictEvidenceResolutionError`.

    Determinism
    -----------
    Each bucket preserves *first-seen* order across selection
    refs and explicit kwargs combined; duplicates are collapsed
    in first-seen order. Two fresh calls with the same inputs
    produce byte-identical frames.

    The per-bucket resolved-id tuples are *not* re-sorted; the
    order on the frame is the order the resolver encountered them,
    starting with the first selection's selected_refs in input
    order, then the second selection's, then the explicit kwargs
    in their declared order. This is the order future
    attention-conditioned mechanisms will read in.
    """
    if kernel is None:
        raise ValueError("kernel is required")
    if not isinstance(actor_id, str) or not actor_id:
        raise ValueError("actor_id is required and must be a non-empty string")
    if not isinstance(actor_type, str) or not actor_type:
        raise ValueError(
            "actor_type is required and must be a non-empty string"
        )

    iso_date = _coerce_iso_date(as_of_date)
    cfid = context_frame_id or _default_context_frame_id(actor_id, iso_date)

    bucket_to_ids: dict[str, list[str]] = {b: [] for b in ALL_BUCKETS}
    unresolved: list[EvidenceRef] = []
    cited_count = 0
    failed_count = 0
    seen_unresolved_ids: set[tuple[str, str]] = set()

    def _emit_unresolved(
        ref_id: str, *, ref_type: str, source_book: str, origin: str
    ) -> None:
        """Record an unresolved ref unless we have already
        recorded the same (ref_id, ref_type) pair earlier — keeps
        the unresolved tail deterministic and free of the same
        dup the resolved tuples already drop."""
        nonlocal failed_count
        key = (ref_id, ref_type)
        if key in seen_unresolved_ids:
            return
        seen_unresolved_ids.add(key)
        unresolved.append(
            EvidenceRef(
                ref_id=ref_id,
                ref_type=ref_type,
                source_book=source_book,
                status=STATUS_UNRESOLVED,
                metadata={"origin": origin},
            )
        )
        failed_count += 1

    # ------------------------------------------------------------------
    # Pass 1 — walk selected_observation_set_ids.
    # ------------------------------------------------------------------
    selection_id_tuple = _normalize_string_tuple(
        selected_observation_set_ids,
        field_name="selected_observation_set_ids",
    )
    attention_book: AttentionBook | None = getattr(kernel, "attention", None)
    for sel_id in selection_id_tuple:
        cited_count += 1
        selection: SelectedObservationSet | None = None
        if attention_book is not None:
            try:
                selection = attention_book.get_selection(sel_id)
            except UnknownSelectedObservationSetError:
                selection = None
            except Exception:
                selection = None
        if selection is None:
            _emit_unresolved(
                sel_id,
                ref_type="selection",
                source_book="attention",
                origin="selection",
            )
            continue
        for ref_id in selection.selected_refs:
            cited_count += 1
            bucket, source_book, getter = _classify_by_prefix(ref_id)
            if bucket is None:
                _emit_unresolved(
                    ref_id,
                    ref_type="unknown_prefix",
                    source_book="unknown",
                    origin="selection",
                )
                continue
            if _resolve_one(
                kernel,
                ref_id=ref_id,
                bucket=bucket,
                source_book=source_book,
                getter=getter,
            ):
                _append_unique(bucket_to_ids, bucket, ref_id)
            else:
                _emit_unresolved(
                    ref_id,
                    ref_type=bucket,
                    source_book=source_book,
                    origin="selection",
                )

    # ------------------------------------------------------------------
    # Pass 2 — walk explicit-id kwargs in declaration order.
    # ------------------------------------------------------------------
    explicit_payload: dict[str, Sequence[str]] = {
        "explicit_signal_ids": explicit_signal_ids,
        "explicit_variable_observation_ids": explicit_variable_observation_ids,
        "explicit_exposure_ids": explicit_exposure_ids,
        "explicit_market_condition_ids": explicit_market_condition_ids,
        "explicit_market_readout_ids": explicit_market_readout_ids,
        "explicit_market_environment_state_ids": (
            explicit_market_environment_state_ids
        ),
        "explicit_industry_condition_ids": explicit_industry_condition_ids,
        "explicit_firm_state_ids": explicit_firm_state_ids,
        "explicit_valuation_ids": explicit_valuation_ids,
        "explicit_dialogue_ids": explicit_dialogue_ids,
        "explicit_escalation_candidate_ids": explicit_escalation_candidate_ids,
        "explicit_stewardship_theme_ids": explicit_stewardship_theme_ids,
    }
    for kwarg_name, bucket in _EXPLICIT_BUCKET_KWARGS:
        ids = _normalize_string_tuple(
            explicit_payload[kwarg_name], field_name=kwarg_name
        )
        source_book = _BUCKET_TO_SOURCE_BOOK[bucket]
        getter = _BUCKET_TO_GETTER[bucket]
        for ref_id in ids:
            cited_count += 1
            if _resolve_one(
                kernel,
                ref_id=ref_id,
                bucket=bucket,
                source_book=source_book,
                getter=getter,
            ):
                _append_unique(bucket_to_ids, bucket, ref_id)
            else:
                _emit_unresolved(
                    ref_id,
                    ref_type=bucket,
                    source_book=source_book,
                    origin="explicit_kwarg",
                )

    # ------------------------------------------------------------------
    # Strict mode short-circuit.
    # ------------------------------------------------------------------
    if strict and unresolved:
        raise StrictEvidenceResolutionError(
            f"strict resolution failed: {len(unresolved)} unresolved "
            f"refs out of {cited_count} cited "
            f"(first: {unresolved[0].ref_id!r})"
        )

    # ------------------------------------------------------------------
    # Compose the frame.
    # ------------------------------------------------------------------
    if cited_count == 0:
        status = "empty"
        confidence = 1.0
    elif failed_count == 0:
        status = "resolved"
        confidence = 1.0
    else:
        status = "partially_resolved"
        confidence = max(
            0.0, 1.0 - (failed_count / cited_count)
        )

    bucket_kwargs = {
        _BUCKET_TO_FRAME_FIELD[b]: tuple(bucket_to_ids[b])
        for b in ALL_BUCKETS
    }

    return ActorContextFrame(
        context_frame_id=cfid,
        actor_id=actor_id,
        actor_type=actor_type,
        as_of_date=iso_date,
        status=status,
        confidence=confidence,
        selected_observation_set_ids=selection_id_tuple,
        unresolved_refs=tuple(unresolved),
        metadata=dict(metadata or {}),
        **bucket_kwargs,
    )
