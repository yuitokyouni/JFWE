from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


class ExternalStateError(Exception):
    """Base class for external-space state errors."""


class DuplicateExternalFactorStateError(ExternalStateError):
    """Raised when a factor_id is added twice."""


class DuplicateExternalSourceStateError(ExternalStateError):
    """Raised when a source_id is added twice."""


@dataclass(frozen=True)
class ExternalFactorState:
    """
    Identity-level record for an external factor.

    An external factor is *something the world treats as exogenous*:
    a foreign exchange rate, a global commodity price, a non-domestic
    macro indicator, a foreign sovereign yield, a demographic trend, a
    weather index. v0.14 stores classification only — which factor,
    what type, what unit, what status. It does NOT store the current
    value, time series, distribution, or shock model.

    The ``unit`` field captures the dimension of the factor (e.g.,
    ``"USD/JPY"``, ``"USD/barrel"``, ``"%"``, ``"index_points"``,
    ``"persons"``) so that future milestones can interpret values
    correctly. v0.14 does not enforce any specific unit grammar — it
    is a free-form string label, like every other classifier.

    There is no ``current_value``, ``last_observed``, ``volatility``,
    ``shock_model``, or ``regime`` field. v0.14 does not implement
    external shock generation or stochastic processes.
    """

    factor_id: str
    factor_type: str = "unspecified"
    unit: str = "unspecified"
    status: str = "active"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.factor_id:
            raise ValueError("factor_id is required")
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "factor_type": self.factor_type,
            "unit": self.unit,
            "status": self.status,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ExternalSourceState:
    """
    Identity-level record for an external data source.

    An external data source is *where the world reads exogenous data
    from*: a foreign statistical agency, an international organization
    (IMF, World Bank, OECD), a commercial data vendor, a foreign
    central bank's open data feed. v0.14 stores classification only.
    It does NOT store the data itself — that lives elsewhere (in
    PriceBook for prices, in SignalBook for signals, in future
    factor-history layers for time series).

    Note on naming
    --------------
    InformationSpace also has a ``add_source_state`` method (§33) that
    classifies signal-producing entities. The two are distinct:

        - InformationSourceState: who *produces* signals about the
          domestic financial world (rating agencies, wires, regulators).
        - ExternalSourceState: where *exogenous data feeds in from*
          (foreign statistical agencies, international bodies, data
          vendors).

    The two often overlap in practice (e.g., a wire service can be
    both a signal source and an external data feed) but the
    classification axes are different. Each space keeps its own view.
    """

    source_id: str
    source_type: str = "unspecified"
    status: str = "active"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("source_id is required")
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "status": self.status,
            "metadata": dict(self.metadata),
        }
