from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping

from world.clock import Clock
from world.ledger import Ledger


class ContractError(Exception):
    """Base class for contract-book errors."""


class DuplicateContractError(ContractError):
    """Raised when a contract_id is added twice."""


class UnknownContractError(ContractError, KeyError):
    """Raised when a contract_id is not found."""


def _coerce_iso_date(value: date | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise TypeError("maturity_date must be date, ISO string, or None")


@dataclass(frozen=True)
class ContractRecord:
    """
    A single explicit obligation between parties.

    A ContractRecord is just structured data. It carries no logic about
    payment schedules, default triggers, covenant evaluation, or pricing.
    Those responsibilities belong to future agent / scenario code, not to
    the transport layer.
    """

    contract_id: str
    contract_type: str
    parties: tuple[str, ...]
    principal: float | None = None
    rate: float | None = None
    maturity_date: str | None = None
    collateral_asset_ids: tuple[str, ...] = field(default_factory=tuple)
    status: str = "active"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.contract_id:
            raise ValueError("contract_id is required")
        if not self.contract_type:
            raise ValueError("contract_type is required")
        if not self.parties:
            raise ValueError("contract must have at least one party")
        object.__setattr__(self, "parties", tuple(self.parties))
        object.__setattr__(
            self, "collateral_asset_ids", tuple(self.collateral_asset_ids)
        )
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(
            self, "maturity_date", _coerce_iso_date(self.maturity_date)
        )

    def with_status(self, status: str) -> ContractRecord:
        return ContractRecord(
            contract_id=self.contract_id,
            contract_type=self.contract_type,
            parties=self.parties,
            principal=self.principal,
            rate=self.rate,
            maturity_date=self.maturity_date,
            collateral_asset_ids=self.collateral_asset_ids,
            status=status,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_type": self.contract_type,
            "parties": list(self.parties),
            "principal": self.principal,
            "rate": self.rate,
            "maturity_date": self.maturity_date,
            "collateral_asset_ids": list(self.collateral_asset_ids),
            "status": self.status,
            "metadata": dict(self.metadata),
        }


@dataclass
class ContractBook:
    """
    Book of all explicit obligations in the world.

    Responsibility:
        - store contracts by contract_id
        - allow lookup by id, party, or type
        - track status transitions (active -> settled / defaulted / ...)
        - emit ledger records for creation and status changes

    Non-responsibility:
        - no scheduling of payments
        - no default detection
        - no covenant logic
        - no business interpretation of contract_type or status
    """

    ledger: Ledger | None = None
    clock: Clock | None = None
    _contracts: dict[str, ContractRecord] = field(default_factory=dict)

    def add_contract(self, contract: ContractRecord) -> ContractRecord:
        if contract.contract_id in self._contracts:
            raise DuplicateContractError(
                f"Duplicate contract_id: {contract.contract_id}"
            )
        self._contracts[contract.contract_id] = contract
        self._record(
            event_type="contract_created",
            object_id=contract.contract_id,
            payload={
                "contract_id": contract.contract_id,
                "contract_type": contract.contract_type,
                "parties": list(contract.parties),
                "principal": contract.principal,
                "rate": contract.rate,
                "maturity_date": contract.maturity_date,
                "collateral_asset_ids": list(contract.collateral_asset_ids),
                "status": contract.status,
            },
        )
        return contract

    def get_contract(self, contract_id: str) -> ContractRecord:
        try:
            return self._contracts[contract_id]
        except KeyError as exc:
            raise UnknownContractError(
                f"Contract not found: {contract_id!r}"
            ) from exc

    def list_by_party(self, party_id: str) -> tuple[ContractRecord, ...]:
        return tuple(
            contract
            for contract in self._contracts.values()
            if party_id in contract.parties
        )

    def list_by_type(self, contract_type: str) -> tuple[ContractRecord, ...]:
        return tuple(
            contract
            for contract in self._contracts.values()
            if contract.contract_type == contract_type
        )

    def all_contracts(self) -> tuple[ContractRecord, ...]:
        return tuple(self._contracts.values())

    def update_status(
        self,
        contract_id: str,
        new_status: str,
    ) -> ContractRecord:
        contract = self.get_contract(contract_id)
        previous_status = contract.status
        updated = contract.with_status(new_status)
        self._contracts[contract_id] = updated
        self._record(
            event_type="contract_status_updated",
            object_id=contract_id,
            payload={
                "contract_id": contract_id,
                "previous_status": previous_status,
                "new_status": new_status,
            },
        )
        return updated

    def snapshot(self) -> dict[str, Any]:
        contracts = sorted(
            (contract.to_dict() for contract in self._contracts.values()),
            key=lambda item: item["contract_id"],
        )
        return {"count": len(contracts), "contracts": contracts}

    def _record(
        self,
        *,
        event_type: str,
        object_id: str,
        payload: Mapping[str, Any],
    ) -> None:
        if self.ledger is None:
            return

        simulation_date = (
            self.clock.current_date if self.clock is not None else None
        )
        self.ledger.append(
            event_type=event_type,
            simulation_date=simulation_date,
            object_id=object_id,
            payload=dict(payload),
            space_id="contracts",
        )
