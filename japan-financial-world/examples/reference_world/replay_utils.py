"""
Replay-determinism helpers for the FWE Reference Demo.

Two entry points:

- ``canonicalize_ledger(kernel)`` returns a list of dicts that
  represent the kernel's ledger trace stripped of fields that
  vary across runs but carry no semantic meaning (wall-clock
  ``timestamp`` and the hash-derived ``record_id``).
- ``ledger_digest(kernel)`` returns the hex-encoded SHA-256 digest
  of the canonical-form JSON.

Volatile fields (across two runs of the same demo):

  * ``record_id``       — derived from a stable hash of the record
                          body, which includes ``timestamp.isoformat()``.
                          Different timestamp -> different record_id.
  * ``timestamp``       — defaults to ``datetime.now(timezone.utc)``
                          on append; wall-clock dependent.
  * ``parent_record_ids`` — a tuple of ``record_id`` values, so
                            it inherits ``record_id``'s volatility
                            even though the *logical* parent
                            relationship is deterministic.

Canonicalization keeps semantic content and drops volatility:

  * ``record_id`` and ``timestamp`` are excluded.
  * ``parent_record_ids`` is rewritten as ``parent_sequences``: a
    sorted tuple of ``sequence`` indices that the parent record_ids
    resolve to within the same ledger. Sequences are deterministic
    counters (``len(records)`` at append time) and form a stable
    naming scheme across runs of a deterministic demo.

Anything else (record_type, source, target, object_id, payload,
metadata, simulation_date, correlation_id, causation_id, plus the
optional reproducibility fields) is preserved verbatim — the
volatility survey at v1.7-public-rc1+ showed they do not differ
across runs.

The helpers are intentionally simple: no test framework, no
project imports beyond stdlib. They can be used interactively to
diff two demo runs during development.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


_VOLATILE_FIELDS: tuple[str, ...] = ("record_id", "timestamp")


def _coerce_json_safe(value: Any) -> Any:
    """
    Convert ledger-record values into JSON-serializable form so the
    resulting dict round-trips through ``json.dumps(..., sort_keys=True)``
    and produces a stable byte string.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _coerce_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_coerce_json_safe(v) for v in value]
    if hasattr(value, "value") and not isinstance(value, type):
        # Enum members (e.g., RecordType): preserve the underlying value.
        try:
            return _coerce_json_safe(value.value)
        except AttributeError:
            pass
    return str(value)


def canonicalize_ledger(kernel: Any) -> list[dict[str, Any]]:
    """
    Return a deterministic, JSON-friendly list-of-dicts view of the
    kernel's ledger trace. See module docstring for the volatility
    rationale.

    Two runs of a deterministic demo must produce
    ``canonicalize_ledger(kernel_a) == canonicalize_ledger(kernel_b)``.
    """
    records = list(kernel.ledger.records)

    # Map every record_id seen in this ledger to its sequence index,
    # so we can rewrite parent_record_ids as parent_sequences.
    id_to_sequence: dict[str, int] = {
        r.record_id: r.sequence for r in records
    }

    canonical: list[dict[str, Any]] = []
    for record in records:
        # Resolve parent record_ids into parent sequences. A parent
        # not present in this ledger is preserved as a string with a
        # marker so two runs still compare equal as long as the same
        # marker appears in both.
        parent_seqs: list[int | str] = []
        for parent_id in record.parent_record_ids:
            if parent_id in id_to_sequence:
                parent_seqs.append(id_to_sequence[parent_id])
            else:
                parent_seqs.append(f"<external:{parent_id!s}>")

        canonical_record: dict[str, Any] = {
            "schema_version": record.schema_version,
            "sequence": record.sequence,
            "simulation_date": record.simulation_date,
            "record_type": _coerce_json_safe(record.record_type),
            "source": record.source,
            "target": record.target,
            "object_id": record.object_id,
            "payload": _coerce_json_safe(record.payload),
            "metadata": _coerce_json_safe(record.metadata),
            "parent_sequences": parent_seqs,
            "correlation_id": record.correlation_id,
            "causation_id": record.causation_id,
            "scenario_id": record.scenario_id,
            "run_id": record.run_id,
            "seed": record.seed,
            "space_id": record.space_id,
            "agent_id": record.agent_id,
            "snapshot_id": record.snapshot_id,
            "state_hash": record.state_hash,
            "visibility": record.visibility,
            "confidence": record.confidence,
        }

        # Defensive: fail loud if a future change accidentally lets
        # a volatile field leak into the canonical view.
        for forbidden in _VOLATILE_FIELDS:
            assert forbidden not in canonical_record, (
                f"canonical_record must not include volatile field {forbidden!r}"
            )

        canonical.append(canonical_record)

    return canonical


def ledger_digest(kernel: Any) -> str:
    """
    SHA-256 hex digest of the canonical-form JSON of the kernel's
    ledger trace. Two runs of a deterministic demo must produce the
    same digest.
    """
    canonical = canonicalize_ledger(kernel)
    payload = json.dumps(
        canonical,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
