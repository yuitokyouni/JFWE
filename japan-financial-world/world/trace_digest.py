"""
v1.29.5 — Trace digest + tamper-evidence integration.

Thin top-level digest helpers that delegate to the
v1.29.1 :func:`world.trace_edges.compute_trace_edge_leaf_digest`
boundary and the v1.29.3
:func:`world.citation_graph_projection.build_citation_graph_projection`
builder. v1.29.5 introduces **no** parallel hash
implementation — every digest path routes through the
single approved leaf-digest function.

v1.29.5 ships:

- :func:`compute_trace_edge_collection_digest` — clear-
  named alias for
  :func:`world.trace_edges.compute_trace_edge_leaf_digest`,
  binding for a "collection of edges" input (matches the
  v1.29 design pin §M.6 wording).
- :func:`compute_citation_graph_projection_digest` —
  builds a :class:`CitationGraphProjection` and returns
  its ``projection_digest``. Convenient one-call helper
  for tamper-evidence cross-checks.
- :func:`compute_event_log_trace_combined_digest` —
  composes the v1.28.4 event-log Merkle root + the
  v1.29.1 trace-edge collection digest + the v1.29.3
  projection digest into a single combined SHA-256
  surface. **The combined digest is a NEW separate
  surface** — it does not equal the legacy
  ``living_world_digest`` and does not modify the
  v1.28.4 Merkle root.

v1.29.5 explicitly does NOT ship:

- No change to the legacy `living_world_digest`. The
  four canonical hex values shipped at v1.21.last
  remain byte-identical.
- No change to the v1.28.4 Merkle root construction.
- No second leaf-hash implementation. Every digest
  path delegates to v1.29.1 / v1.28.4.
- No `WorldKernel` field. No `prev_hash` / `self_hash`
  chain.
- No graph database / PROV-O / RDF / SPARQL / Cypher /
  Gremlin / rdflib / networkx.
- No counterfactual replay.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

from world.citation_graph_projection import (
    build_citation_graph_projection,
)
from world.event_log_schema import (
    EventLogManifest,
    EventLogRecord,
    serialize_canonical_json,
)
from world.trace_edges import (
    TRACE_EDGE_SCHEMA_VERSION,
    TraceEdgeRecord,
    compute_trace_edge_leaf_digest,
)


# ---------------------------------------------------------------------------
# compute_trace_edge_collection_digest
# ---------------------------------------------------------------------------


def compute_trace_edge_collection_digest(
    records: Iterable[TraceEdgeRecord],
    *,
    schema_version: str = TRACE_EDGE_SCHEMA_VERSION,
) -> str:
    """Clear-named alias for the v1.29.1
    :func:`world.trace_edges.compute_trace_edge_leaf_digest`
    boundary.

    Routes verbatim through the single approved
    trace-edge leaf-hash implementation. A trace-edge
    "collection" is the same canonical object as a
    "trace-edge leaf" — the rename clarifies the intent
    at v1.29.5 callsites that work with an entire
    in-memory edge collection rather than a
    partition-cell leaf.
    """
    return compute_trace_edge_leaf_digest(
        records, schema_version=schema_version
    )


# ---------------------------------------------------------------------------
# compute_citation_graph_projection_digest
# ---------------------------------------------------------------------------


def compute_citation_graph_projection_digest(
    event_records: Iterable[EventLogRecord],
    trace_edges: Iterable[TraceEdgeRecord],
    *,
    run_id: str,
) -> str:
    """Build a deterministic projection over
    ``event_records`` + ``trace_edges`` and return its
    ``projection_digest``.

    This is a convenience wrapper over
    :func:`world.citation_graph_projection.build_citation_graph_projection`;
    callers that need the full projection should call
    that function directly.
    """
    projection = build_citation_graph_projection(
        event_records, trace_edges, run_id=run_id
    )
    return projection.projection_digest


# ---------------------------------------------------------------------------
# compute_event_log_trace_combined_digest
# ---------------------------------------------------------------------------


def compute_event_log_trace_combined_digest(
    *,
    event_log_root: Path | None = None,
    event_log_manifest: EventLogManifest | None = None,
    event_records: Iterable[EventLogRecord],
    trace_edges: Iterable[TraceEdgeRecord],
    run_id: str,
) -> str:
    """Compose a single combined digest over the v1.28
    event-log Merkle root + the v1.29 trace-edge
    collection digest + the v1.29.3 projection digest.

    The combined digest is a **new separate surface**:

    - It does NOT equal the legacy
      ``living_world_digest``.
    - It does NOT modify the v1.28.4 Merkle root.
    - It is constructed by hashing
      ``{"event_log_root_digest": …,
        "trace_edge_collection_digest": …,
        "citation_graph_projection_digest": …,
        "schema_version": TRACE_EDGE_SCHEMA_VERSION}``
      via the v1.28.1 canonical-JSON serializer (sort_keys=True
      so the top-level mapping is alphabetic).

    If ``event_log_root`` is supplied the v1.28.4
    :func:`world.event_log_merkle.compute_event_log_root_digest`
    is invoked. If it is not supplied, a placeholder
    sentinel ``"absent"`` is used in its slot — useful
    for in-memory smoke tests where no event log has
    been written.
    """
    if not isinstance(run_id, str) or not run_id:
        raise ValueError(
            "run_id must be a non-empty string"
        )
    materialised_events = tuple(event_records)
    materialised_edges = tuple(trace_edges)
    if event_log_root is None:
        event_log_root_digest = "absent"
    else:
        # Local import to avoid a top-level
        # event_log_merkle import in module load when
        # event_log_root is not supplied.
        from world.event_log_merkle import (
            compute_event_log_root_digest,
        )
        event_log_root_digest = (
            compute_event_log_root_digest(
                Path(event_log_root),
                event_log_manifest,
            )
        )
    trace_collection_digest = (
        compute_trace_edge_collection_digest(
            materialised_edges
        )
    )
    projection_digest = (
        compute_citation_graph_projection_digest(
            materialised_events,
            materialised_edges,
            run_id=run_id,
        )
    )
    payload: dict[str, Any] = {
        "citation_graph_projection_digest": (
            projection_digest
        ),
        "event_log_root_digest": event_log_root_digest,
        "schema_version": TRACE_EDGE_SCHEMA_VERSION,
        "trace_edge_collection_digest": (
            trace_collection_digest
        ),
    }
    body = serialize_canonical_json(
        payload, sort_keys=True
    )
    return hashlib.sha256(body).hexdigest()


__all__ = [
    "compute_citation_graph_projection_digest",
    "compute_event_log_trace_combined_digest",
    "compute_trace_edge_collection_digest",
]
