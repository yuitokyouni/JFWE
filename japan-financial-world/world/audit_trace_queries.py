"""
v1.29.4 — Deterministic audit trace query helpers.

Read-only, deterministic helpers over collections of
:class:`world.trace_edges.TraceEdgeRecord` (v1.29.1) and
:class:`world.citation_graph_projection.CitationGraphProjection`
(v1.29.3). Answers a small fixed catalogue of audit
questions; **does not** answer counterfactual questions.

v1.29.4 ships:

- :func:`list_edges_for_event` — every edge that
  references the given ``event_id`` as source or
  target.
- :func:`list_evidence_for_judgment_event` —
  evidence_ref_ids cited by edges that target the
  given ``event_id``.
- :func:`list_events_citing_evidence` — target
  event_ids of edges whose ``evidence_ref_ids`` /
  ``citation_ids`` contain the given evidence /
  citation id.
- :func:`list_edges_by_actor` — every edge whose
  ``actor_id`` matches.
- :func:`list_propagation_edges` — every edge with
  ``edge_category_label == "propagation"`` or
  ``edge_type_label == "propagated_to"``.
- :func:`list_contradiction_pairs` — every
  ``(source_event_id, target_event_id)`` pair from
  edges with ``edge_type_label == "contradicted_by"``.
- :func:`trace_lineage_to_origin` — bounded-depth
  ancestor walk from ``event_id`` along edges
  matching the lineage edge-types.
- :func:`summarize_audit_questions` — single-call
  bundle returning all of the above on a fixed
  question set.

Counterfactual boundary (binding):

- These helpers answer "**which** judgments depend on
  evidence X?" — i.e. they walk dependencies that
  exist in the event log + trace edges.
- They do **not** answer "**what would change** if
  evidence X were withdrawn?" — that requires future
  deterministic replay (v1.30+) and is **not**
  implemented in v1.29.

Determinism contract:

- All return values are deterministic given the same
  input collection, regardless of insertion order.
- All return values are tuples of plain values or
  frozen dataclasses, sorted by canonical keys.
- Cycle handling: lineage walk de-duplicates visited
  ``event_id`` and respects ``max_depth`` so cycles
  cannot diverge or grow unboundedly.
- No mutation of inputs. No graph database, no
  networkx, no SPARQL / Cypher / Gremlin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from world.citation_graph_projection import (
    CitationGraphProjection,
)
from world.trace_edges import (
    TraceEdgeRecord,
)


# ---------------------------------------------------------------------------
# Edge-type sets used by lineage / propagation queries
# ---------------------------------------------------------------------------


# A "lineage" edge is one whose semantics walk
# backward from a derived event toward its
# antecedents.
LINEAGE_EDGE_TYPE_LABELS: frozenset[str] = frozenset(
    {
        "cited_as_evidence",
        "derived_from",
        "reviewed_under",
        "constrained_by",
    }
)


PROPAGATION_EDGE_TYPE_LABELS: frozenset[str] = frozenset(
    {"propagated_to"}
)


CONTRADICTION_EDGE_TYPE_LABELS: frozenset[str] = (
    frozenset({"contradicted_by"})
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _materialise(
    trace_edges: Iterable[TraceEdgeRecord],
) -> tuple[TraceEdgeRecord, ...]:
    edges = tuple(trace_edges)
    for e in edges:
        if not isinstance(e, TraceEdgeRecord):
            raise TypeError(
                "trace_edges must contain "
                "TraceEdgeRecord instances; got "
                f"{type(e).__name__}"
            )
    return edges


def _validate_required_string(
    value: object, *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )
    return value


# ---------------------------------------------------------------------------
# Audit query helpers
# ---------------------------------------------------------------------------


def list_edges_for_event(
    event_id: str,
    trace_edges: Iterable[TraceEdgeRecord],
) -> tuple[TraceEdgeRecord, ...]:
    """Every edge that references ``event_id`` as
    source or target. Sorted by ``canonical_sort_key``.
    """
    _validate_required_string(
        event_id, field_name="event_id"
    )
    edges = _materialise(trace_edges)
    out = tuple(
        e
        for e in edges
        if e.source_event_id == event_id
        or e.target_event_id == event_id
    )
    return tuple(
        sorted(out, key=lambda e: e.canonical_sort_key)
    )


def list_evidence_for_judgment_event(
    event_id: str,
    trace_edges: Iterable[TraceEdgeRecord],
) -> tuple[str, ...]:
    """Sorted unique tuple of ``evidence_ref_ids``
    cited by edges whose ``target_event_id`` matches.
    """
    _validate_required_string(
        event_id, field_name="event_id"
    )
    edges = _materialise(trace_edges)
    seen: set[str] = set()
    for e in edges:
        if e.target_event_id != event_id:
            continue
        for ev in e.evidence_ref_ids:
            seen.add(ev)
    return tuple(sorted(seen))


def list_events_citing_evidence(
    evidence_ref_id: str,
    trace_edges: Iterable[TraceEdgeRecord],
) -> tuple[str, ...]:
    """Sorted unique tuple of target event_ids whose
    edges include ``evidence_ref_id`` in their
    ``evidence_ref_ids`` OR ``citation_ids``."""
    _validate_required_string(
        evidence_ref_id, field_name="evidence_ref_id"
    )
    edges = _materialise(trace_edges)
    seen: set[str] = set()
    for e in edges:
        if (
            evidence_ref_id in e.evidence_ref_ids
            or evidence_ref_id in e.citation_ids
        ):
            seen.add(e.target_event_id)
    return tuple(sorted(seen))


def list_edges_by_actor(
    actor_id: str,
    trace_edges: Iterable[TraceEdgeRecord],
) -> tuple[TraceEdgeRecord, ...]:
    """Every edge whose ``actor_id`` matches. Sorted
    by ``canonical_sort_key``."""
    _validate_required_string(
        actor_id, field_name="actor_id"
    )
    edges = _materialise(trace_edges)
    out = tuple(
        e for e in edges if e.actor_id == actor_id
    )
    return tuple(
        sorted(out, key=lambda e: e.canonical_sort_key)
    )


def list_propagation_edges(
    trace_edges: Iterable[TraceEdgeRecord],
) -> tuple[TraceEdgeRecord, ...]:
    """Every edge with
    ``edge_type_label in PROPAGATION_EDGE_TYPE_LABELS``
    OR ``edge_category_label == "propagation"``."""
    edges = _materialise(trace_edges)
    out = tuple(
        e
        for e in edges
        if (
            e.edge_type_label
            in PROPAGATION_EDGE_TYPE_LABELS
        )
        or e.edge_category_label == "propagation"
    )
    return tuple(
        sorted(out, key=lambda e: e.canonical_sort_key)
    )


def list_contradiction_pairs(
    trace_edges: Iterable[TraceEdgeRecord],
) -> tuple[tuple[str, str], ...]:
    """Sorted unique tuple of
    ``(source_event_id, target_event_id)`` pairs from
    edges with ``edge_type_label == "contradicted_by"``.
    """
    edges = _materialise(trace_edges)
    pairs: set[tuple[str, str]] = set()
    for e in edges:
        if (
            e.edge_type_label
            in CONTRADICTION_EDGE_TYPE_LABELS
        ):
            pairs.add(
                (e.source_event_id, e.target_event_id)
            )
    return tuple(sorted(pairs))


def trace_lineage_to_origin(
    event_id: str,
    trace_edges: Iterable[TraceEdgeRecord],
    *,
    max_depth: int = 16,
) -> tuple[str, ...]:
    """Bounded-depth ancestor walk from ``event_id``.

    Follows edges with ``edge_type_label`` in
    :data:`LINEAGE_EDGE_TYPE_LABELS`. The walk respects
    ``max_depth`` and de-duplicates visited
    ``event_id`` so cycles are safe and the result is
    deterministic regardless of input edge order.

    Returns a sorted tuple of every ancestor
    ``event_id`` reachable from ``event_id`` (excluding
    ``event_id`` itself).

    Cycle handling: an event_id visited at any depth
    is never revisited; the walk terminates either at
    ``max_depth`` or when the frontier is empty.
    """
    _validate_required_string(
        event_id, field_name="event_id"
    )
    if (
        not isinstance(max_depth, int)
        or isinstance(max_depth, bool)
        or max_depth < 0
    ):
        raise ValueError(
            "max_depth must be a non-negative int"
        )
    edges = _materialise(trace_edges)
    # Build target → list of (source_event_id) for
    # lineage-type edges only. Use sorted iteration
    # for determinism.
    parent_map: dict[str, set[str]] = {}
    for e in edges:
        if (
            e.edge_type_label
            not in LINEAGE_EDGE_TYPE_LABELS
        ):
            continue
        parent_map.setdefault(
            e.target_event_id, set()
        ).add(e.source_event_id)

    visited: set[str] = {event_id}
    ancestors: set[str] = set()
    frontier: list[str] = [event_id]
    depth = 0
    while frontier and depth < max_depth:
        next_frontier: list[str] = []
        for node in frontier:
            for parent in parent_map.get(
                node, set()
            ):
                if parent in visited:
                    continue
                visited.add(parent)
                ancestors.add(parent)
                next_frontier.append(parent)
        frontier = sorted(next_frontier)
        depth += 1
    return tuple(sorted(ancestors))


# ---------------------------------------------------------------------------
# Counterfactual boundary
# ---------------------------------------------------------------------------


COUNTERFACTUAL_REPLAY_NOT_IMPLEMENTED_MESSAGE: str = (
    "v1.29.4 audit query helpers answer questions "
    "about WHAT IS in the event log, never about "
    "WHAT COULD HAVE BEEN. Counterfactual replay "
    "('if evidence X were withdrawn before judgment "
    "Y, would Y change?') requires a future "
    "deterministic replay engine (likely v1.30+) and "
    "is NOT implemented in v1.29."
)


# ---------------------------------------------------------------------------
# Audit summary bundle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditTraceSummary:
    """Frozen bundle of audit-question results for one
    fixed event_id + actor_id pair."""

    event_id: str
    actor_id: str
    edges_for_event: tuple[
        TraceEdgeRecord, ...
    ] = field(default_factory=tuple)
    evidence_for_judgment: tuple[str, ...] = field(
        default_factory=tuple
    )
    edges_by_actor: tuple[
        TraceEdgeRecord, ...
    ] = field(default_factory=tuple)
    propagation_edges: tuple[
        TraceEdgeRecord, ...
    ] = field(default_factory=tuple)
    contradiction_pairs: tuple[
        tuple[str, str], ...
    ] = field(default_factory=tuple)
    lineage_ancestors: tuple[str, ...] = field(
        default_factory=tuple
    )
    projection_digest: str = ""


def summarize_audit_questions(
    projection: CitationGraphProjection,
    trace_edges: Sequence[TraceEdgeRecord],
    *,
    event_id: str,
    actor_id: str = "",
    max_depth: int = 16,
) -> AuditTraceSummary:
    """Single-call bundle returning a deterministic
    :class:`AuditTraceSummary`.

    The summary's `projection_digest` is copied from
    the supplied :class:`CitationGraphProjection` so a
    consumer can verify the projection was built over
    the same input set.
    """
    if not isinstance(
        projection, CitationGraphProjection
    ):
        raise TypeError(
            "projection must be a "
            "CitationGraphProjection instance"
        )
    _validate_required_string(
        event_id, field_name="event_id"
    )
    edges_for_event = list_edges_for_event(
        event_id, trace_edges
    )
    evidence_for_judgment = (
        list_evidence_for_judgment_event(
            event_id, trace_edges
        )
    )
    edges_by_actor: tuple[TraceEdgeRecord, ...] = ()
    if actor_id:
        edges_by_actor = list_edges_by_actor(
            actor_id, trace_edges
        )
    propagation_edges = list_propagation_edges(
        trace_edges
    )
    contradiction_pairs = list_contradiction_pairs(
        trace_edges
    )
    lineage_ancestors = trace_lineage_to_origin(
        event_id, trace_edges, max_depth=max_depth
    )
    return AuditTraceSummary(
        event_id=event_id,
        actor_id=actor_id,
        edges_for_event=edges_for_event,
        evidence_for_judgment=evidence_for_judgment,
        edges_by_actor=edges_by_actor,
        propagation_edges=propagation_edges,
        contradiction_pairs=contradiction_pairs,
        lineage_ancestors=lineage_ancestors,
        projection_digest=projection.projection_digest,
    )


__all__ = [
    "AuditTraceSummary",
    "CONTRADICTION_EDGE_TYPE_LABELS",
    "COUNTERFACTUAL_REPLAY_NOT_IMPLEMENTED_MESSAGE",
    "LINEAGE_EDGE_TYPE_LABELS",
    "PROPAGATION_EDGE_TYPE_LABELS",
    "list_contradiction_pairs",
    "list_edges_by_actor",
    "list_edges_for_event",
    "list_events_citing_evidence",
    "list_evidence_for_judgment_event",
    "list_propagation_edges",
    "summarize_audit_questions",
    "trace_lineage_to_origin",
]
