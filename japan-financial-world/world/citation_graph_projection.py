"""
v1.29.3 — Deterministic CitationGraphProjection.

Read-only projection from a tuple of `EventLogRecord`
instances (v1.28.1) and a tuple of `TraceEdgeRecord`
instances (v1.29.1) into a frozen, deterministic
audit-oriented graph summary.

v1.29.3 ships:

- :class:`CitationGraphProjection` — frozen dataclass
  with sorted node / edge id tuples, sorted count
  pairs, and a ``projection_digest`` (SHA-256 over
  canonical material).
- :func:`build_citation_graph_projection` —
  deterministic builder.

The projection is **a materialised view, not a source
of truth** (per design pin §C):

- It mutates no event log file, no trace-edge file,
  no `_MANIFEST.json` sidecar, no v1.28.4 Merkle
  digest.
- Dropping the projection and rebuilding from the
  same event records + trace edges produces a
  byte-identical projection.
- It is not the audit-query layer (v1.29.4 is).
- It is not a graph database.
- It is not a citation-graph centrality / PageRank /
  community-detection / embedding surface — those
  are explicitly **forbidden** at v1.29.

v1.29.3 explicitly does NOT ship:

- No graph database (Neo4j / TigerGraph / etc.).
- No PROV-O / RDF / SPARQL / Cypher / rdflib /
  networkx.
- No counterfactual replay.
- No predictive output.
- No investment output.
- No `WorldKernel` field.
- No mutation of inputs.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Iterable

from world.event_log_schema import (
    EventLogRecord,
    serialize_canonical_json,
)
from world.trace_edges import (
    TRACE_EDGE_SCHEMA_VERSION,
    TraceEdgeRecord,
    trace_edge_to_canonical_dict,
)


# ---------------------------------------------------------------------------
# CitationGraphProjection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CitationGraphProjection:
    """Frozen deterministic graph-summary projection.

    All count fields are non-negative. Tuple-of-pair
    fields are sorted by key ascending so two
    projections of the same inputs are byte-identical.
    Disconnected event ids are surfaced separately
    (events that appear in no trace edge as either
    source or target).
    """

    run_id: str
    node_event_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    nodes_by_record_type: tuple[
        tuple[str, int], ...
    ] = field(default_factory=tuple)
    edges_by_type: tuple[
        tuple[str, int], ...
    ] = field(default_factory=tuple)
    edges_by_category: tuple[
        tuple[str, int], ...
    ] = field(default_factory=tuple)
    evidence_ref_counts: tuple[
        tuple[str, int], ...
    ] = field(default_factory=tuple)
    citation_ref_counts: tuple[
        tuple[str, int], ...
    ] = field(default_factory=tuple)
    actor_edge_counts: tuple[
        tuple[str, int], ...
    ] = field(default_factory=tuple)
    disconnected_event_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    dangling_source_event_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    dangling_target_event_ids: tuple[str, ...] = field(
        default_factory=tuple
    )
    projection_digest: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ordered_count_pairs(
    items: Iterable[str],
) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return tuple(sorted(counts.items()))


def _projection_payload_for_digest(
    *,
    run_id: str,
    node_event_ids: tuple[str, ...],
    edge_ids: tuple[str, ...],
    nodes_by_record_type: tuple[tuple[str, int], ...],
    edges_by_type: tuple[tuple[str, int], ...],
    edges_by_category: tuple[tuple[str, int], ...],
    evidence_ref_counts: tuple[tuple[str, int], ...],
    citation_ref_counts: tuple[tuple[str, int], ...],
    actor_edge_counts: tuple[tuple[str, int], ...],
    disconnected_event_ids: tuple[str, ...],
    dangling_source_event_ids: tuple[str, ...],
    dangling_target_event_ids: tuple[str, ...],
    sorted_edges: tuple[TraceEdgeRecord, ...],
) -> bytes:
    """Build the canonical payload bytes whose SHA-256
    is the projection digest. Edges are included as
    canonical dicts so the digest reacts to any edge-
    semantic change."""
    payload: dict[str, Any] = {
        "run_id": run_id,
        "schema_version": TRACE_EDGE_SCHEMA_VERSION,
        "node_event_ids": list(node_event_ids),
        "edge_ids": list(edge_ids),
        "nodes_by_record_type": [
            list(p) for p in nodes_by_record_type
        ],
        "edges_by_type": [
            list(p) for p in edges_by_type
        ],
        "edges_by_category": [
            list(p) for p in edges_by_category
        ],
        "evidence_ref_counts": [
            list(p) for p in evidence_ref_counts
        ],
        "citation_ref_counts": [
            list(p) for p in citation_ref_counts
        ],
        "actor_edge_counts": [
            list(p) for p in actor_edge_counts
        ],
        "disconnected_event_ids": list(
            disconnected_event_ids
        ),
        "dangling_source_event_ids": list(
            dangling_source_event_ids
        ),
        "dangling_target_event_ids": list(
            dangling_target_event_ids
        ),
        "edges": [
            trace_edge_to_canonical_dict(e)
            for e in sorted_edges
        ],
    }
    return serialize_canonical_json(
        payload, sort_keys=False
    )


# ---------------------------------------------------------------------------
# build_citation_graph_projection
# ---------------------------------------------------------------------------


def build_citation_graph_projection(
    event_records: Iterable[EventLogRecord],
    trace_edges: Iterable[TraceEdgeRecord],
    *,
    run_id: str,
) -> CitationGraphProjection:
    """Build a deterministic
    :class:`CitationGraphProjection` over a tuple of
    event-log records and a tuple of trace edges.

    Determinism contract (binding):

    - Inputs are not mutated.
    - Event records are sorted by `event_id` for the
      canonical node-id list and for the
      `nodes_by_record_type` count pairs.
    - Trace edges are sorted by `canonical_sort_key`
      for the canonical edge-id list, count
      aggregations, and the `projection_digest`
      payload.
    - Empty inputs yield empty outputs (deterministic).
    - Edges whose `source_event_id` /
      `target_event_id` are not present in the
      supplied event records surface in
      `dangling_source_event_ids` /
      `dangling_target_event_ids` (sorted).
    - Events that appear in no trace edge surface in
      `disconnected_event_ids` (sorted).
    - The `projection_digest` is SHA-256 lowercase
      hex over the canonical payload (which includes
      the edges in canonical sorted order, so any
      edge-semantic change propagates).
    """
    if not isinstance(run_id, str) or not run_id:
        raise ValueError(
            "run_id must be a non-empty string"
        )
    events = tuple(event_records)
    edges = tuple(trace_edges)
    for e in events:
        if not isinstance(e, EventLogRecord):
            raise TypeError(
                "event_records must contain "
                "EventLogRecord instances; got "
                f"{type(e).__name__}"
            )
    for te in edges:
        if not isinstance(te, TraceEdgeRecord):
            raise TypeError(
                "trace_edges must contain "
                "TraceEdgeRecord instances; got "
                f"{type(te).__name__}"
            )

    # Canonical orderings.
    sorted_events = sorted(events, key=lambda e: e.event_id)
    sorted_edges = tuple(
        sorted(edges, key=lambda x: x.canonical_sort_key)
    )

    node_event_ids = tuple(
        e.event_id for e in sorted_events
    )
    edge_ids = tuple(e.edge_id for e in sorted_edges)

    # Aggregations.
    nodes_by_record_type = _ordered_count_pairs(
        e.record_type for e in sorted_events
    )
    edges_by_type = _ordered_count_pairs(
        e.edge_type_label for e in sorted_edges
    )
    edges_by_category = _ordered_count_pairs(
        e.edge_category_label for e in sorted_edges
    )

    evidence_iter: list[str] = []
    citation_iter: list[str] = []
    actor_iter: list[str] = []
    for e in sorted_edges:
        for ev_id in e.evidence_ref_ids:
            evidence_iter.append(ev_id)
        for c_id in e.citation_ids:
            citation_iter.append(c_id)
        if e.actor_id:
            actor_iter.append(e.actor_id)

    evidence_ref_counts = _ordered_count_pairs(
        evidence_iter
    )
    citation_ref_counts = _ordered_count_pairs(
        citation_iter
    )
    actor_edge_counts = _ordered_count_pairs(actor_iter)

    # Connectivity.
    event_id_set = frozenset(node_event_ids)
    referenced: set[str] = set()
    dangling_sources: set[str] = set()
    dangling_targets: set[str] = set()
    for e in sorted_edges:
        if e.source_event_id in event_id_set:
            referenced.add(e.source_event_id)
        else:
            dangling_sources.add(e.source_event_id)
        if e.target_event_id in event_id_set:
            referenced.add(e.target_event_id)
        else:
            dangling_targets.add(e.target_event_id)
    disconnected = tuple(
        sorted(event_id_set - referenced)
    )
    dangling_source_event_ids = tuple(
        sorted(dangling_sources)
    )
    dangling_target_event_ids = tuple(
        sorted(dangling_targets)
    )

    payload_bytes = _projection_payload_for_digest(
        run_id=run_id,
        node_event_ids=node_event_ids,
        edge_ids=edge_ids,
        nodes_by_record_type=nodes_by_record_type,
        edges_by_type=edges_by_type,
        edges_by_category=edges_by_category,
        evidence_ref_counts=evidence_ref_counts,
        citation_ref_counts=citation_ref_counts,
        actor_edge_counts=actor_edge_counts,
        disconnected_event_ids=disconnected,
        dangling_source_event_ids=(
            dangling_source_event_ids
        ),
        dangling_target_event_ids=(
            dangling_target_event_ids
        ),
        sorted_edges=sorted_edges,
    )
    projection_digest = hashlib.sha256(
        payload_bytes
    ).hexdigest()

    return CitationGraphProjection(
        run_id=run_id,
        node_event_ids=node_event_ids,
        edge_ids=edge_ids,
        nodes_by_record_type=nodes_by_record_type,
        edges_by_type=edges_by_type,
        edges_by_category=edges_by_category,
        evidence_ref_counts=evidence_ref_counts,
        citation_ref_counts=citation_ref_counts,
        actor_edge_counts=actor_edge_counts,
        disconnected_event_ids=disconnected,
        dangling_source_event_ids=(
            dangling_source_event_ids
        ),
        dangling_target_event_ids=(
            dangling_target_event_ids
        ),
        projection_digest=projection_digest,
    )


__all__ = [
    "CitationGraphProjection",
    "build_citation_graph_projection",
]
