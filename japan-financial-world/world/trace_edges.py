"""
v1.29.1 — TraceEdgeRecord schema + canonical serializer.

Canonical row shape for **inter-event relationships**.
Trace edges are the second canonical record class in the
v1.28 / v1.29 substrate stack:

- :class:`world.event_log_schema.EventLogRecord` — canonical
  for *event facts* (v1.28.1).
- :class:`TraceEdgeRecord` — canonical for *inter-event
  relationships* (v1.29.1).

Citation graph projections (v1.29.3+) and audit query
helpers (v1.29.4+) are read-only derivations over these
two canonical record classes.

v1.29.1 ships:

- closed-set label vocabularies
  (:data:`TRACE_EDGE_TYPE_LABELS`,
  :data:`TRACE_EDGE_CATEGORY_LABELS`,
  :data:`TRACE_EDGE_CONFIDENCE_LABELS`),
- frozen :class:`TraceEdgeRecord` dataclass with
  deterministic ``canonical_sort_key`` derivation,
- canonical-dict + canonical-JSON serializer routed
  through v1.28.1's
  :func:`world.event_log_schema.serialize_canonical_json`,
- :func:`compute_trace_edge_leaf_digest` — SHA-256 over
  canonically-sorted, canonically-serialised trace edges
  + a schema-version manifest sentinel.
- :data:`TRACE_EDGE_PROV_COMPAT_MAPPING` — descriptive
  prov-like name strings only; no rdflib / RDF / OWL /
  SPARQL / Cypher / Neo4j / networkx / graph database
  dependency.

v1.29.1 explicitly does NOT ship:

- No PROV-O / W3C-PROV runtime. The mapping is naming-
  level conceptual compatibility only — strings, not
  ontology export.
- No graph database. No Neo4j / TigerGraph /
  ArangoDB / etc.
- No SPARQL / Cypher / Gremlin query layer.
- No graph centrality / PageRank / community detection
  / embedding / probabilistic edge weight.
- No counterfactual replay engine.
- No `prev_hash` / `self_hash` chain on the record.
  Tamper evidence is delegated to the v1.28 event-log
  / manifest / Merkle substrate (per the v1.29 design
  pin clarification).
- No `WorldKernel` field. The module does not register
  itself with the kernel.
- No real Japanese identifier, no real-data adapter,
  no Japan calibration, no investment output, no
  sentiment label.

Every existing v1.21.last canonical
``living_world_digest`` value remains byte-identical at
v1.29.1.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, ClassVar, Iterable, Mapping

from world.event_log_schema import (
    serialize_canonical_json,
)


# ---------------------------------------------------------------------------
# Closed-set label vocabularies (binding for v1.29.x)
# ---------------------------------------------------------------------------


TRACE_EDGE_TYPE_LABELS: frozenset[str] = frozenset(
    {
        "attended_to",
        "cited_as_evidence",
        "constrained_by",
        "reviewed_under",
        "propagated_to",
        "contradicted_by",
        "superseded_by",
        "derived_from",
        "related_to",
        "unknown",
    }
)


TRACE_EDGE_CATEGORY_LABELS: frozenset[str] = frozenset(
    {
        "evidence",
        "attention",
        "review",
        "constraint",
        "propagation",
        "contradiction",
        "lineage",
        "annotation",
        "unknown",
    }
)


TRACE_EDGE_CONFIDENCE_LABELS: frozenset[str] = frozenset(
    {
        "asserted",
        "inferred",
        "weak",
        "unknown",
        "synthetic",
    }
)


# ---------------------------------------------------------------------------
# PROV-O-inspired conceptual mapping (descriptive only).
#
# These strings are *naming-level* conceptual hints for a
# future audit-report or interoperability layer. They are
# **not** an RDF / OWL / SPARQL implementation. No
# external ontology library is imported. Consumers that
# need formal PROV-O semantics must build their own
# mapping under a fresh design pin and license review.
# ---------------------------------------------------------------------------


TRACE_EDGE_PROV_COMPAT_MAPPING: Mapping[str, str] = {
    "attended_to": "jfwe:attendedTo",
    "cited_as_evidence": "prov:wasDerivedFromLike",
    "constrained_by": "jfwe:constrainedBy",
    "reviewed_under": "jfwe:reviewedUnder",
    "propagated_to": "prov:wasInfluencedByLike",
    "contradicted_by": "jfwe:contradictedBy",
    "superseded_by": "jfwe:supersededBy",
    "derived_from": "prov:wasDerivedFromLike",
    "related_to": "jfwe:relatedTo",
    "unknown": "jfwe:unknown",
}


# ---------------------------------------------------------------------------
# Canonical column order (binding for v1.29.x serialiser)
# ---------------------------------------------------------------------------


CANONICAL_TRACE_EDGE_COLUMN_ORDER: tuple[str, ...] = (
    "edge_id",
    "run_id",
    "source_event_id",
    "target_event_id",
    "edge_type_label",
    "edge_category_label",
    "evidence_ref_ids",
    "citation_ids",
    "actor_id",
    "period_id",
    "provenance_kind",
    "confidence_label",
    "notes",
    "canonical_sort_key",
)


# Default schema-version sentinel for the leaf-digest
# manifest section. Bumping this string changes every
# trace-edge leaf digest — by design.
TRACE_EDGE_SCHEMA_VERSION: str = "v1.29.1-trace-v1"


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


def _validate_optional_string(
    value: Any, *, field_name: str
) -> str:
    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string (possibly empty)"
        )
    return value


def _validate_label(
    value: Any, allowed: frozenset[str], *, field_name: str
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )
    if value not in allowed:
        raise ValueError(
            f"{field_name} must be one of {sorted(allowed)!r}; "
            f"got {value!r}"
        )
    return value


def _validate_string_tuple(
    value: Any, *, field_name: str
) -> tuple[str, ...]:
    """Accept tuple/list of non-empty strings; reject
    bare ``str`` and unordered containers."""
    if isinstance(value, str):
        raise ValueError(
            f"{field_name} must be an iterable of "
            "non-empty strings, not a single string"
        )
    if not isinstance(value, (tuple, list)):
        raise ValueError(
            f"{field_name} must be a tuple or list of "
            "non-empty strings"
        )
    normalised = tuple(value)
    for entry in normalised:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"{field_name} entries must be non-empty "
                f"strings; got {entry!r}"
            )
    return normalised


# ---------------------------------------------------------------------------
# TraceEdgeRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TraceEdgeRecord:
    """Immutable, append-only record of a directed
    relationship between two event-log records.

    A trace edge **describes** a relationship between
    two event-log records; it does **not** create a new
    event fact independently. Removing every trace edge
    must leave the underlying event-log substrate
    unchanged.

    Required non-empty fields: ``edge_id``, ``run_id``,
    ``source_event_id``, ``target_event_id``.
    Required closed-set fields: ``edge_type_label``
    (``TRACE_EDGE_TYPE_LABELS``), ``edge_category_label``
    (``TRACE_EDGE_CATEGORY_LABELS``), ``confidence_label``
    (``TRACE_EDGE_CONFIDENCE_LABELS``).
    Optional fields default to empty: ``actor_id``,
    ``period_id``, ``notes``, plus the citation /
    evidence tuples (default ``()``).

    The default ``canonical_sort_key`` is derived as

    ``f"run_id={run_id}/source={source_event_id}/"``
    ``f"target={target_event_id}/type={edge_type_label}/"``
    ``f"edge_id={edge_id}"``

    if not supplied. The trailing ``edge_id`` ensures
    sort stability when multiple edges share a
    source/target/type triple.

    The record carries no `prev_hash` / `self_hash`.
    Tamper evidence is delegated to the v1.28 event-log
    / manifest / Merkle substrate.
    """

    edge_id: str
    run_id: str
    source_event_id: str
    target_event_id: str
    edge_type_label: str
    edge_category_label: str
    evidence_ref_ids: tuple[str, ...] = ()
    citation_ids: tuple[str, ...] = ()
    actor_id: str = ""
    period_id: str = ""
    provenance_kind: str = "synthetic"
    confidence_label: str = "synthetic"
    notes: str = ""
    canonical_sort_key: str = ""

    REQUIRED_NON_EMPTY_FIELDS: ClassVar[tuple[str, ...]] = (
        "edge_id",
        "run_id",
        "source_event_id",
        "target_event_id",
        "provenance_kind",
    )

    LABEL_FIELDS: ClassVar[
        tuple[tuple[str, frozenset[str]], ...]
    ] = (
        ("edge_type_label", TRACE_EDGE_TYPE_LABELS),
        (
            "edge_category_label",
            TRACE_EDGE_CATEGORY_LABELS,
        ),
        (
            "confidence_label",
            TRACE_EDGE_CONFIDENCE_LABELS,
        ),
    )

    def __post_init__(self) -> None:
        for fname in self.REQUIRED_NON_EMPTY_FIELDS:
            _validate_required_string(
                getattr(self, fname), field_name=fname
            )
        for fname, allowed in self.LABEL_FIELDS:
            _validate_label(
                getattr(self, fname),
                allowed,
                field_name=fname,
            )
        # Tuple-of-non-empty-string fields. Empty tuple
        # allowed.
        for fname in ("evidence_ref_ids", "citation_ids"):
            object.__setattr__(
                self,
                fname,
                _validate_string_tuple(
                    getattr(self, fname),
                    field_name=fname,
                ),
            )
        # Optional plain-string fields (may be empty).
        for fname in ("actor_id", "period_id", "notes"):
            _validate_optional_string(
                getattr(self, fname), field_name=fname
            )
        # Derive default canonical_sort_key when omitted.
        if not self.canonical_sort_key:
            object.__setattr__(
                self,
                "canonical_sort_key",
                self._default_canonical_sort_key(),
            )
        else:
            _validate_required_string(
                self.canonical_sort_key,
                field_name="canonical_sort_key",
            )

    def _default_canonical_sort_key(self) -> str:
        return (
            f"run_id={self.run_id}"
            f"/source={self.source_event_id}"
            f"/target={self.target_event_id}"
            f"/type={self.edge_type_label}"
            f"/edge_id={self.edge_id}"
        )


# ---------------------------------------------------------------------------
# Canonical serialization
# ---------------------------------------------------------------------------


def trace_edge_to_canonical_dict(
    record: TraceEdgeRecord,
) -> dict[str, Any]:
    """Project a :class:`TraceEdgeRecord` into a
    canonical mapping ordered by
    :data:`CANONICAL_TRACE_EDGE_COLUMN_ORDER`.

    Tuples are converted to lists so the JSON serializer
    produces a stable representation. The returned
    dict's insertion order is the canonical column
    order; serialising it without ``sort_keys=True``
    preserves that order.
    """
    if not isinstance(record, TraceEdgeRecord):
        raise TypeError(
            "trace_edge_to_canonical_dict expects a "
            "TraceEdgeRecord instance"
        )
    out: dict[str, Any] = {}
    for col in CANONICAL_TRACE_EDGE_COLUMN_ORDER:
        value = getattr(record, col)
        if isinstance(value, tuple):
            out[col] = list(value)
        else:
            out[col] = value
    return out


def serialize_trace_edges_canonical_json(
    records: Iterable[TraceEdgeRecord],
) -> bytes:
    """Canonical JSON bytes for an ordered sequence of
    :class:`TraceEdgeRecord` instances.

    Records are NOT re-sorted here; the caller is
    responsible for canonical ordering. Use
    :func:`compute_trace_edge_leaf_digest` for the
    digest path, which sorts by ``canonical_sort_key``
    automatically.
    """
    items = [trace_edge_to_canonical_dict(r) for r in records]
    return serialize_canonical_json(items, sort_keys=False)


# ---------------------------------------------------------------------------
# Leaf digest function boundary (binding)
# ---------------------------------------------------------------------------


def compute_trace_edge_leaf_digest(
    records: Iterable[TraceEdgeRecord],
    *,
    schema_version: str = TRACE_EDGE_SCHEMA_VERSION,
) -> str:
    """Compute the SHA-256 leaf digest for a collection
    of trace edges.

    This is the **single** v1.29 trace-edge leaf-digest
    boundary. v1.29.5 trace-collection / projection
    digest helpers must route through this function;
    no parallel hash implementation is permitted.

    Procedure:

    1. Materialise records and sort by
       ``canonical_sort_key``.
    2. Project each record through
       :func:`trace_edge_to_canonical_dict`.
    3. Build a leaf-material mapping
       ``{"schema_version": …, "trace_edges": [...]}``
       so that bumping ``schema_version`` propagates
       through the digest.
    4. Serialise via the v1.28.1
       :func:`serialize_canonical_json` boundary
       (``sort_keys=False`` so column order in records
       is preserved; the top-level mapping has only two
       keys, alphabetic).
    5. Hash with SHA-256; return lowercase hex.

    Empty record list is allowed and produces a
    deterministic schema-only digest.
    """
    if (
        not isinstance(schema_version, str)
        or not schema_version
    ):
        raise ValueError(
            "schema_version must be a non-empty string"
        )
    materialised = tuple(records)
    for r in materialised:
        if not isinstance(r, TraceEdgeRecord):
            raise TypeError(
                "compute_trace_edge_leaf_digest expects "
                "TraceEdgeRecord instances; got "
                f"{type(r).__name__}"
            )
    sorted_records = sorted(
        materialised,
        key=lambda r: r.canonical_sort_key,
    )
    record_dicts = [
        trace_edge_to_canonical_dict(r)
        for r in sorted_records
    ]
    leaf_material: dict[str, Any] = {
        "schema_version": schema_version,
        "trace_edges": record_dicts,
    }
    leaf_bytes = serialize_canonical_json(
        leaf_material, sort_keys=False
    )
    return hashlib.sha256(leaf_bytes).hexdigest()


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "CANONICAL_TRACE_EDGE_COLUMN_ORDER",
    "TRACE_EDGE_CATEGORY_LABELS",
    "TRACE_EDGE_CONFIDENCE_LABELS",
    "TRACE_EDGE_PROV_COMPAT_MAPPING",
    "TRACE_EDGE_SCHEMA_VERSION",
    "TRACE_EDGE_TYPE_LABELS",
    "TraceEdgeRecord",
    "compute_trace_edge_leaf_digest",
    "serialize_trace_edges_canonical_json",
    "trace_edge_to_canonical_dict",
]
