from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

import copy
import hashlib
import json


class RecordType(str, Enum):
    OBJECT_REGISTERED = "object_registered"
    TASK_SCHEDULED = "task_scheduled"
    TASK_EXECUTED = "task_executed"
    SIGNAL_EMITTED = "signal_emitted"
    SIGNAL_ADDED = "signal_added"
    SIGNAL_OBSERVED = "signal_observed"
    EVENT_PUBLISHED = "event_published"
    EVENT_DELIVERED = "event_delivered"
    PERCEIVED_STATE_UPDATED = "perceived_state_updated"
    ORDER_SUBMITTED = "order_submitted"
    PRICE_UPDATED = "price_updated"
    BANK_WARNING = "bank_warning"
    CONTRACT_CREATED = "contract_created"
    CONTRACT_STATUS_UPDATED = "contract_status_updated"
    CONTRACT_COVENANT_BREACHED = "contract_covenant_breached"
    OWNERSHIP_POSITION_ADDED = "ownership_position_added"
    OWNERSHIP_TRANSFERRED = "ownership_transferred"
    BALANCE_SHEET_VIEW_CREATED = "balance_sheet_view_created"
    CONSTRAINT_ADDED = "constraint_added"
    CONSTRAINT_EVALUATED = "constraint_evaluated"
    FIRM_STATE_ADDED = "firm_state_added"
    BANK_STATE_ADDED = "bank_state_added"
    INVESTOR_STATE_ADDED = "investor_state_added"
    MARKET_STATE_ADDED = "market_state_added"
    LISTING_ADDED = "listing_added"
    STATE_SNAPSHOT_CREATED = "state_snapshot_created"
    WARNING = "warning"
    ERROR = "error"


class RecordList(list):
    def __call__(self) -> list:
        return list(self)


def _coerce_timestamp(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)

    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if not isinstance(value, datetime):
        raise TypeError("timestamp must be datetime, ISO string, or None")

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _coerce_simulation_date(value: date | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise TypeError("simulation_date must be date, string, or None")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, set):
        return tuple(_freeze(v) for v in sorted(value, key=str))
    return copy.deepcopy(value)


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return copy.deepcopy(value)


def _json_safe(value: Any) -> Any:
    return _thaw(value)


def _stable_hash(value: Any, length: int = 16) -> str:
    raw = json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


@dataclass(frozen=True)
class LedgerRecord:
    schema_version: str
    record_id: str
    sequence: int
    timestamp: datetime
    simulation_date: str | None
    record_type: RecordType
    source: str | None = None
    target: str | None = None
    object_id: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    # Future event-chain graph support.
    parent_record_ids: tuple[str, ...] = field(default_factory=tuple)
    correlation_id: str | None = None
    causation_id: str | None = None

    # Optional reproducibility and provenance fields.
    scenario_id: str | None = None
    run_id: str | None = None
    seed: int | None = None
    space_id: str | None = None
    agent_id: str | None = None
    snapshot_id: str | None = None
    state_hash: str | None = None
    visibility: str | None = None
    confidence: float | None = None

    @property
    def event_type(self) -> str:
        return self.record_type.value

    @property
    def task_id(self) -> str | None:
        value = self.metadata.get("task_id")
        return str(value) if value is not None else None

    @property
    def created_at(self) -> datetime:
        return self.timestamp

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", _coerce_timestamp(self.timestamp))
        object.__setattr__(self, "simulation_date", _coerce_simulation_date(self.simulation_date))
        object.__setattr__(self, "record_type", RecordType(self.record_type))
        object.__setattr__(self, "payload", _freeze(dict(self.payload)))
        object.__setattr__(self, "metadata", _freeze(dict(self.metadata)))
        object.__setattr__(self, "parent_record_ids", tuple(self.parent_record_ids))
        if self.causation_id and self.causation_id not in self.parent_record_ids:
            object.__setattr__(
                self,
                "parent_record_ids",
                (*self.parent_record_ids, self.causation_id),
            )
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "sequence": self.sequence,
            "timestamp": self.timestamp.isoformat(),
            "simulation_date": self.simulation_date,
            "record_type": self.record_type.value,
            "source": self.source,
            "target": self.target,
            "object_id": self.object_id,
            "payload": _thaw(self.payload),
            "metadata": _thaw(self.metadata),
            "parent_record_ids": list(self.parent_record_ids),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "scenario_id": self.scenario_id,
            "run_id": self.run_id,
            "seed": self.seed,
            "space_id": self.space_id,
            "agent_id": self.agent_id,
            "snapshot_id": self.snapshot_id,
            "state_hash": self.state_hash,
            "visibility": self.visibility,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LedgerRecord:
        return cls(
            schema_version=data.get("schema_version", "ledger_record.v1"),
            record_id=data["record_id"],
            sequence=int(data["sequence"]),
            timestamp=_coerce_timestamp(data["timestamp"]),
            simulation_date=data.get("simulation_date"),
            record_type=RecordType(data["record_type"]),
            source=data.get("source"),
            target=data.get("target"),
            object_id=data.get("object_id"),
            payload=data.get("payload") or {},
            metadata=data.get("metadata") or {},
            parent_record_ids=tuple(data.get("parent_record_ids") or ()),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            scenario_id=data.get("scenario_id"),
            run_id=data.get("run_id"),
            seed=data.get("seed"),
            space_id=data.get("space_id"),
            agent_id=data.get("agent_id"),
            snapshot_id=data.get("snapshot_id"),
            state_hash=data.get("state_hash"),
            visibility=data.get("visibility"),
            confidence=data.get("confidence"),
        )


@dataclass
class Ledger:
    records: RecordList = field(default_factory=RecordList)

    def append(
        self,
        record_type: RecordType | str | None = None,
        *,
        event_type: str | None = None,
        schema_version: str = "ledger_record.v1",
        simulation_date: date | str | None = None,
        timestamp: datetime | str | None = None,
        source: str | None = None,
        target: str | None = None,
        object_id: str | None = None,
        task_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        parent_record_ids: Iterable[str] | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        scenario_id: str | None = None,
        run_id: str | None = None,
        seed: int | None = None,
        space_id: str | None = None,
        agent_id: str | None = None,
        snapshot_id: str | None = None,
        state_hash: str | None = None,
        visibility: str | None = None,
        confidence: float | None = None,
    ) -> LedgerRecord:
        if record_type is None:
            if event_type is None:
                raise TypeError("record_type or event_type is required")
            record_type = event_type

        sequence = len(self.records)
        record_type = RecordType(record_type)
        timestamp = _coerce_timestamp(timestamp)
        simulation_date = _coerce_simulation_date(simulation_date)
        payload = dict(payload or {})
        metadata = dict(metadata or {})
        if task_id is not None:
            metadata.setdefault("task_id", task_id)
        parent_record_ids = tuple(parent_record_ids or ())
        if causation_id and causation_id not in parent_record_ids:
            parent_record_ids = (*parent_record_ids, causation_id)

        record_body = {
            "schema_version": schema_version,
            "sequence": sequence,
            "timestamp": timestamp.isoformat(),
            "simulation_date": simulation_date,
            "record_type": record_type.value,
            "source": source,
            "target": target,
            "object_id": object_id,
            "task_id": task_id,
            "payload": payload,
            "metadata": metadata,
            "parent_record_ids": list(parent_record_ids),
            "correlation_id": correlation_id,
            "causation_id": causation_id,
            "scenario_id": scenario_id,
            "run_id": run_id,
            "seed": seed,
            "space_id": space_id,
            "agent_id": agent_id,
            "snapshot_id": snapshot_id,
            "state_hash": state_hash,
            "visibility": visibility,
            "confidence": confidence,
        }

        record_id = f"rec_{_stable_hash(record_body)}"

        record = LedgerRecord(
            schema_version=schema_version,
            record_id=record_id,
            sequence=sequence,
            timestamp=timestamp,
            simulation_date=simulation_date,
            record_type=record_type,
            source=source,
            target=target,
            object_id=object_id,
            payload=payload,
            metadata=metadata,
            parent_record_ids=parent_record_ids,
            correlation_id=correlation_id,
            causation_id=causation_id,
            scenario_id=scenario_id,
            run_id=run_id,
            seed=seed,
            space_id=space_id,
            agent_id=agent_id,
            snapshot_id=snapshot_id,
            state_hash=state_hash,
            visibility=visibility,
            confidence=confidence,
        )

        self.records.append(record)
        return record

    def query(
        self,
        *,
        record_type: RecordType | str | None = None,
        object_id: str | None = None,
        source: str | None = None,
        target: str | None = None,
        correlation_id: str | None = None,
        scenario_id: str | None = None,
        run_id: str | None = None,
        space_id: str | None = None,
        agent_id: str | None = None,
        task_id: str | None = None,
    ) -> tuple[LedgerRecord, ...]:
        expected_type = RecordType(record_type) if record_type is not None else None

        result: list[LedgerRecord] = []
        for record in self.records:
            if expected_type is not None and record.record_type != expected_type:
                continue
            if object_id is not None and record.object_id != object_id:
                continue
            if source is not None and record.source != source:
                continue
            if target is not None and record.target != target:
                continue
            if correlation_id is not None and record.correlation_id != correlation_id:
                continue
            if scenario_id is not None and record.scenario_id != scenario_id:
                continue
            if run_id is not None and record.run_id != run_id:
                continue
            if space_id is not None and record.space_id != space_id:
                continue
            if agent_id is not None and record.agent_id != agent_id:
                continue
            if task_id is not None and record.task_id != task_id:
                continue
            result.append(record)

        return tuple(result)

    def filter(
        self,
        event_type: str | None = None,
        task_id: str | None = None,
    ) -> list[LedgerRecord]:
        return list(self.query(record_type=event_type, task_id=task_id))

    def children_of(self, record_id: str) -> tuple[LedgerRecord, ...]:
        return tuple(
            record
            for record in self.records
            if record_id in record.parent_record_ids
        )

    def warning(
        self,
        message: str,
        *,
        simulation_date: date | str | None = None,
        source: str | None = None,
        target: str | None = None,
        object_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        parent_record_ids: Iterable[str] | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        scenario_id: str | None = None,
        run_id: str | None = None,
        space_id: str | None = None,
        agent_id: str | None = None,
    ) -> LedgerRecord:
        return self.append(
            RecordType.WARNING,
            simulation_date=simulation_date,
            source=source,
            target=target,
            object_id=object_id,
            payload={"message": message},
            metadata=metadata,
            parent_record_ids=parent_record_ids,
            correlation_id=correlation_id,
            causation_id=causation_id,
            scenario_id=scenario_id,
            run_id=run_id,
            space_id=space_id,
            agent_id=agent_id,
        )

    def error(
        self,
        message: str,
        *,
        simulation_date: date | str | None = None,
        source: str | None = None,
        target: str | None = None,
        object_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        parent_record_ids: Iterable[str] | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        scenario_id: str | None = None,
        run_id: str | None = None,
        space_id: str | None = None,
        agent_id: str | None = None,
    ) -> LedgerRecord:
        return self.append(
            RecordType.ERROR,
            simulation_date=simulation_date,
            source=source,
            target=target,
            object_id=object_id,
            payload={"message": message},
            metadata=metadata,
            parent_record_ids=parent_record_ids,
            correlation_id=correlation_id,
            causation_id=causation_id,
            scenario_id=scenario_id,
            run_id=run_id,
            space_id=space_id,
            agent_id=agent_id,
        )

    def to_jsonl(self) -> str:
        return "\n".join(
            json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True)
            for record in self.records
        )

    @classmethod
    def from_jsonl(cls, text: str) -> Ledger:
        ledger = cls()
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            ledger.records.append(LedgerRecord.from_dict(json.loads(line)))
        return ledger

    def write_jsonl(self, path: str | Path) -> None:
        Path(path).write_text(self.to_jsonl(), encoding="utf-8")

    @classmethod
    def read_jsonl(cls, path: str | Path) -> Ledger:
        return cls.from_jsonl(Path(path).read_text(encoding="utf-8"))
