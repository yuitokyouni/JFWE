"""
v1.13.2 PaymentInstructionRecord + SettlementEventRecord +
SettlementInstructionBook.

Storage-only successor to v1.13.1 (settlement accounts). v1.13.2
ships **synthetic** payment-instruction records and synthetic
settlement-event records; both are append-only, label-based,
and ledger-auditable.

There are **no real amounts**, **no settlement execution**, **no
RTGS queue mechanics**, **no securities settlement execution**,
**no central-bank accounting**. Synthetic-size labels (e.g.,
``"reference_size_a"``, ``"reference_size_b"``) replace any real
currency value. Status fields are recorded labels, not states a
clearing process actually transitions through.

The book emits exactly one ledger record per ``add_*`` call —
``RecordType.PAYMENT_INSTRUCTION_REGISTERED`` and
``RecordType.SETTLEMENT_EVENT_RECORDED`` — and refuses to mutate
any other source-of-truth book in the kernel.

Anti-fields (binding)
=====================

The records deliberately have **no** ``amount``,
``currency_value``, ``fx_rate``, ``balance``, ``debit``,
``credit``, ``policy_rate``, ``interest``, ``order``, ``trade``,
``recommendation``, ``investment_advice``, ``forecast_value``,
``actual_value``, ``real_data_value``, ``behavior_probability``
field. Tests pin the absence on both the dataclass field set
and the ledger payload key set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, ClassVar, Iterable, Mapping

from world.clock import Clock
from world.ledger import Ledger


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SettlementPaymentError(Exception):
    """Base class for v1.13.2 settlement-payments-layer errors."""


class DuplicatePaymentInstructionError(SettlementPaymentError):
    """Raised when an instruction_id is added twice."""


class UnknownPaymentInstructionError(SettlementPaymentError, KeyError):
    """Raised when an instruction_id is not found."""


class DuplicateSettlementEventError(SettlementPaymentError):
    """Raised when an event_id is added twice."""


class UnknownSettlementEventError(SettlementPaymentError, KeyError):
    """Raised when an event_id is not found."""


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
# PaymentInstructionRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PaymentInstructionRecord:
    """Immutable record of one synthetic payment instruction.

    Field semantics
    ---------------
    - ``instruction_id`` is the stable id; unique within a
      ``SettlementInstructionBook``.
    - ``payer_account_id`` / ``payee_account_id`` are
      cross-references to ``SettlementAccountRecord`` ids.
      Stored as data; not validated against any other book per
      the v0/v1 cross-reference rule.
    - ``requested_settlement_date`` is the required ISO date.
    - ``synthetic_size_label`` is a free-form label (e.g.,
      ``"reference_size_small"``, ``"reference_size_medium"``,
      ``"reference_size_large"``). **Never** a real number.
    - ``instruction_type`` is a small free-form tag (e.g.,
      ``"interbank_transfer"``, ``"securities_settlement_leg"``,
      ``"liquidity_provision_leg"``).
    - ``status`` is a free-form lifecycle tag (``"queued"`` /
      ``"pending"`` / ``"settled"`` / ``"rejected"``).
    - ``visibility`` is a free-form generic visibility tag.
    - ``related_contract_ids`` and ``related_signal_ids`` are
      tuples of plain-id cross-references. Stored as data.
    - ``metadata`` is free-form.

    Anti-fields
    -----------
    See module docstring. v1.13.2 stores **no** amount, no
    currency value, no fx rate, no policy rate, no balance.
    """

    instruction_id: str
    payer_account_id: str
    payee_account_id: str
    requested_settlement_date: str
    synthetic_size_label: str
    instruction_type: str
    status: str
    visibility: str
    related_contract_ids: tuple[str, ...] = field(default_factory=tuple)
    related_signal_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "instruction_id",
        "payer_account_id",
        "payee_account_id",
        "requested_settlement_date",
        "synthetic_size_label",
        "instruction_type",
        "status",
        "visibility",
    )

    TUPLE_FIELDS: ClassVar[tuple[str, ...]] = (
        "related_contract_ids",
        "related_signal_ids",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, (str, date)) or (
                isinstance(value, str) and not value
            ):
                raise ValueError(f"{name} is required")

        object.__setattr__(
            self,
            "requested_settlement_date",
            _coerce_iso_date(self.requested_settlement_date),
        )

        for tuple_field_name in self.TUPLE_FIELDS:
            value = getattr(self, tuple_field_name)
            normalized = _normalize_string_tuple(
                value, field_name=tuple_field_name
            )
            object.__setattr__(self, tuple_field_name, normalized)

        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "instruction_id": self.instruction_id,
            "payer_account_id": self.payer_account_id,
            "payee_account_id": self.payee_account_id,
            "requested_settlement_date": self.requested_settlement_date,
            "synthetic_size_label": self.synthetic_size_label,
            "instruction_type": self.instruction_type,
            "status": self.status,
            "visibility": self.visibility,
            "related_contract_ids": list(self.related_contract_ids),
            "related_signal_ids": list(self.related_signal_ids),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# SettlementEventRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SettlementEventRecord:
    """Immutable record of one synthetic settlement event.

    Field semantics
    ---------------
    - ``event_id`` is the stable id; unique within a
      ``SettlementInstructionBook``.
    - ``instruction_id`` is the cross-reference to the
      :class:`PaymentInstructionRecord` the event refers to.
    - ``as_of_date`` is the required ISO date.
    - ``event_type`` is a small free-form lifecycle tag (e.g.,
      ``"settlement_queued"``, ``"settlement_completed"``,
      ``"settlement_failed"``, ``"settlement_partial"``).
    - ``status`` is a free-form status label.
    - ``source_account_id`` / ``target_account_id`` are
      cross-references to settlement-account ids.
    - ``synthetic_size_label`` is a free-form label.
    - ``visibility`` is a free-form tag.
    - ``metadata`` is free-form.
    """

    event_id: str
    instruction_id: str
    as_of_date: str
    event_type: str
    status: str
    source_account_id: str
    target_account_id: str
    synthetic_size_label: str
    visibility: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "event_id",
        "instruction_id",
        "as_of_date",
        "event_type",
        "status",
        "source_account_id",
        "target_account_id",
        "synthetic_size_label",
        "visibility",
    )

    def __post_init__(self) -> None:
        for name in self.REQUIRED_STRING_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, (str, date)) or (
                isinstance(value, str) and not value
            ):
                raise ValueError(f"{name} is required")

        object.__setattr__(
            self, "as_of_date", _coerce_iso_date(self.as_of_date)
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "instruction_id": self.instruction_id,
            "as_of_date": self.as_of_date,
            "event_type": self.event_type,
            "status": self.status,
            "source_account_id": self.source_account_id,
            "target_account_id": self.target_account_id,
            "synthetic_size_label": self.synthetic_size_label,
            "visibility": self.visibility,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


@dataclass
class SettlementInstructionBook:
    """Append-only storage for v1.13.2 payment instructions and
    settlement events. The book emits exactly one ledger record
    per ``add_instruction`` / ``add_event`` call and refuses to
    mutate any other source-of-truth book in the kernel.

    v1.13.2 ships storage and read-only listings only — no
    settlement execution, no balance update, no clearing logic,
    no securities delivery.
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _instructions: dict[str, PaymentInstructionRecord] = field(
        default_factory=dict
    )
    _events: dict[str, SettlementEventRecord] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Instruction CRUD
    # ------------------------------------------------------------------

    def add_instruction(
        self, instruction: PaymentInstructionRecord
    ) -> PaymentInstructionRecord:
        if instruction.instruction_id in self._instructions:
            raise DuplicatePaymentInstructionError(
                f"Duplicate instruction_id: {instruction.instruction_id}"
            )
        self._instructions[instruction.instruction_id] = instruction

        if self.ledger is not None:
            self.ledger.append(
                event_type="payment_instruction_registered",
                simulation_date=self._now(),
                object_id=instruction.instruction_id,
                source=instruction.payer_account_id,
                target=instruction.payee_account_id,
                payload={
                    "instruction_id": instruction.instruction_id,
                    "payer_account_id": instruction.payer_account_id,
                    "payee_account_id": instruction.payee_account_id,
                    "requested_settlement_date": (
                        instruction.requested_settlement_date
                    ),
                    "synthetic_size_label": instruction.synthetic_size_label,
                    "instruction_type": instruction.instruction_type,
                    "status": instruction.status,
                    "visibility": instruction.visibility,
                    "related_contract_ids": list(
                        instruction.related_contract_ids
                    ),
                    "related_signal_ids": list(
                        instruction.related_signal_ids
                    ),
                },
                space_id="settlement",
                visibility=instruction.visibility,
            )
        return instruction

    def get_instruction(
        self, instruction_id: str
    ) -> PaymentInstructionRecord:
        try:
            return self._instructions[instruction_id]
        except KeyError as exc:
            raise UnknownPaymentInstructionError(
                f"Payment instruction not found: {instruction_id!r}"
            ) from exc

    def list_instructions(self) -> tuple[PaymentInstructionRecord, ...]:
        return tuple(self._instructions.values())

    def list_by_payer(
        self, payer_account_id: str
    ) -> tuple[PaymentInstructionRecord, ...]:
        return tuple(
            i
            for i in self._instructions.values()
            if i.payer_account_id == payer_account_id
        )

    def list_by_payee(
        self, payee_account_id: str
    ) -> tuple[PaymentInstructionRecord, ...]:
        return tuple(
            i
            for i in self._instructions.values()
            if i.payee_account_id == payee_account_id
        )

    def list_by_status(
        self, status: str
    ) -> tuple[PaymentInstructionRecord, ...]:
        return tuple(
            i for i in self._instructions.values() if i.status == status
        )

    # ------------------------------------------------------------------
    # Event CRUD
    # ------------------------------------------------------------------

    def add_event(
        self, event: SettlementEventRecord
    ) -> SettlementEventRecord:
        if event.event_id in self._events:
            raise DuplicateSettlementEventError(
                f"Duplicate event_id: {event.event_id}"
            )
        self._events[event.event_id] = event

        if self.ledger is not None:
            self.ledger.append(
                event_type="settlement_event_recorded",
                simulation_date=self._now(),
                object_id=event.event_id,
                source=event.source_account_id,
                target=event.target_account_id,
                payload={
                    "event_id": event.event_id,
                    "instruction_id": event.instruction_id,
                    "as_of_date": event.as_of_date,
                    "event_type": event.event_type,
                    "status": event.status,
                    "source_account_id": event.source_account_id,
                    "target_account_id": event.target_account_id,
                    "synthetic_size_label": event.synthetic_size_label,
                    "visibility": event.visibility,
                },
                space_id="settlement",
                visibility=event.visibility,
            )
        return event

    def get_event(self, event_id: str) -> SettlementEventRecord:
        try:
            return self._events[event_id]
        except KeyError as exc:
            raise UnknownSettlementEventError(
                f"Settlement event not found: {event_id!r}"
            ) from exc

    def list_events(self) -> tuple[SettlementEventRecord, ...]:
        return tuple(self._events.values())

    def list_events_by_instruction(
        self, instruction_id: str
    ) -> tuple[SettlementEventRecord, ...]:
        return tuple(
            e
            for e in self._events.values()
            if e.instruction_id == instruction_id
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        instructions = sorted(
            (i.to_dict() for i in self._instructions.values()),
            key=lambda item: item["instruction_id"],
        )
        events = sorted(
            (e.to_dict() for e in self._events.values()),
            key=lambda item: item["event_id"],
        )
        return {
            "instruction_count": len(instructions),
            "instructions": instructions,
            "event_count": len(events),
            "events": events,
        }

    def _now(self) -> str | None:
        if self.clock is None or self.clock.current_date is None:
            return None
        return self.clock.current_date.isoformat()
