from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from typing import Iterator

from world.attention import AttentionBook
from world.attention_feedback import AttentionFeedbackBook
from world.settlement_accounts import SettlementAccountBook
from world.settlement_payments import SettlementInstructionBook
from world.interbank_liquidity import InterbankLiquidityStateBook
from world.central_bank_signals import CentralBankSignalBook
from world.corporate_financing import CorporateFinancingNeedBook
from world.funding_options import FundingOptionCandidateBook
from world.capital_structure import CapitalStructureReviewBook
from world.financing_paths import CorporateFinancingPathBook
from world.securities import SecurityMarketBook
from world.market_intents import InvestorMarketIntentBook
from world.market_interest import AggregatedMarketInterestBook
from world.market_pressure import IndicativeMarketPressureBook
from world.balance_sheet import BalanceSheetProjector
from world.clock import Clock
from world.constraints import ConstraintBook, ConstraintEvaluator
from world.contracts import ContractBook
from world.event_bus import EventBus
from world.exposures import ExposureBook
from world.external_processes import ExternalProcessBook
from world.observation_menu_builder import ObservationMenuBuilder
from world.institutions import InstitutionBook
from world.interactions import InteractionBook
from world.ledger import Ledger
from world.ownership import OwnershipBook
from world.phases import IntradayPhaseSpec, PhaseSequence
from world.prices import PriceBook
from world.registry import RegisteredObject, Registry
from world.relationships import RelationshipCapitalBook
from world.routine_engine import RoutineEngine
from world.routines import RoutineBook
from world.scheduler import Phase, Scheduler, ScheduledTask, TaskSpec
from world.signals import SignalBook
from world.state import State
from world.engagement import DialogueBook, EscalationCandidateBook
from world.evidence import EvidenceResolver
from world.firm_state import FirmFinancialStateBook
from world.industry import IndustryConditionBook
from world.investor_intent import InvestorIntentBook
from world.market_conditions import MarketConditionBook
from world.market_environment import MarketEnvironmentBook
from world.market_surface_readout import CapitalMarketReadoutBook
from world.stewardship import StewardshipBook
from world.strategic_response import StrategicResponseCandidateBook
from world.valuations import ValuationBook, ValuationComparator
from world.variables import WorldVariableBook

if TYPE_CHECKING:
    from spaces.base import BaseSpace


@dataclass
class WorldKernel:
    registry: Registry
    clock: Clock
    scheduler: Scheduler
    ledger: Ledger
    state: State
    event_bus: EventBus = field(default_factory=EventBus)
    ownership: OwnershipBook = field(default_factory=OwnershipBook)
    contracts: ContractBook = field(default_factory=ContractBook)
    prices: PriceBook = field(default_factory=PriceBook)
    balance_sheets: BalanceSheetProjector | None = None
    constraints: ConstraintBook = field(default_factory=ConstraintBook)
    constraint_evaluator: ConstraintEvaluator | None = None
    signals: SignalBook = field(default_factory=SignalBook)
    valuations: ValuationBook = field(default_factory=ValuationBook)
    valuation_comparator: ValuationComparator | None = None
    institutions: InstitutionBook = field(default_factory=InstitutionBook)
    external_processes: ExternalProcessBook = field(
        default_factory=ExternalProcessBook
    )
    relationships: RelationshipCapitalBook = field(
        default_factory=RelationshipCapitalBook
    )
    interactions: InteractionBook = field(default_factory=InteractionBook)
    routines: RoutineBook = field(default_factory=RoutineBook)
    attention: AttentionBook = field(default_factory=AttentionBook)
    variables: WorldVariableBook = field(default_factory=WorldVariableBook)
    exposures: ExposureBook = field(default_factory=ExposureBook)
    stewardship: StewardshipBook = field(default_factory=StewardshipBook)
    engagement: DialogueBook = field(default_factory=DialogueBook)
    escalations: EscalationCandidateBook = field(
        default_factory=EscalationCandidateBook
    )
    strategic_responses: StrategicResponseCandidateBook = field(
        default_factory=StrategicResponseCandidateBook
    )
    industry_conditions: IndustryConditionBook = field(
        default_factory=IndustryConditionBook
    )
    market_conditions: MarketConditionBook = field(
        default_factory=MarketConditionBook
    )
    capital_market_readouts: CapitalMarketReadoutBook = field(
        default_factory=CapitalMarketReadoutBook
    )
    market_environments: MarketEnvironmentBook = field(
        default_factory=MarketEnvironmentBook
    )
    firm_financial_states: FirmFinancialStateBook = field(
        default_factory=FirmFinancialStateBook
    )
    investor_intents: InvestorIntentBook = field(
        default_factory=InvestorIntentBook
    )
    attention_feedback: AttentionFeedbackBook = field(
        default_factory=AttentionFeedbackBook
    )
    settlement_accounts: SettlementAccountBook = field(
        default_factory=SettlementAccountBook
    )
    settlement_payments: SettlementInstructionBook = field(
        default_factory=SettlementInstructionBook
    )
    interbank_liquidity: InterbankLiquidityStateBook = field(
        default_factory=InterbankLiquidityStateBook
    )
    central_bank_signals: CentralBankSignalBook = field(
        default_factory=CentralBankSignalBook
    )
    corporate_financing_needs: CorporateFinancingNeedBook = field(
        default_factory=CorporateFinancingNeedBook
    )
    funding_options: FundingOptionCandidateBook = field(
        default_factory=FundingOptionCandidateBook
    )
    capital_structure_reviews: CapitalStructureReviewBook = field(
        default_factory=CapitalStructureReviewBook
    )
    financing_paths: CorporateFinancingPathBook = field(
        default_factory=CorporateFinancingPathBook
    )
    security_market: SecurityMarketBook = field(
        default_factory=SecurityMarketBook
    )
    investor_market_intents: InvestorMarketIntentBook = field(
        default_factory=InvestorMarketIntentBook
    )
    aggregated_market_interest: AggregatedMarketInterestBook = field(
        default_factory=AggregatedMarketInterestBook
    )
    indicative_market_pressure: IndicativeMarketPressureBook = field(
        default_factory=IndicativeMarketPressureBook
    )
    routine_engine: RoutineEngine | None = None
    observation_menu_builder: ObservationMenuBuilder | None = None
    # v1.12.3 — read-only evidence resolution service. Stateless;
    # never mutates any other source-of-truth book; never emits
    # a ledger record by default. Future v1.12.x mechanisms will
    # consume the produced ActorContextFrame instead of scanning
    # books globally.
    evidence_resolver: EvidenceResolver | None = None

    def __post_init__(self) -> None:
        for book in (
            self.ownership,
            self.contracts,
            self.prices,
            self.constraints,
            self.signals,
            self.valuations,
            self.institutions,
            self.external_processes,
            self.relationships,
            self.interactions,
            self.routines,
            self.attention,
            self.variables,
            self.exposures,
            self.stewardship,
            self.engagement,
            self.escalations,
            self.strategic_responses,
            self.industry_conditions,
            self.market_conditions,
            self.capital_market_readouts,
            self.market_environments,
            self.firm_financial_states,
            self.investor_intents,
            self.attention_feedback,
            self.settlement_accounts,
            self.settlement_payments,
            self.interbank_liquidity,
            self.central_bank_signals,
            self.corporate_financing_needs,
            self.funding_options,
            self.capital_structure_reviews,
            self.financing_paths,
            self.security_market,
            self.investor_market_intents,
            self.aggregated_market_interest,
            self.indicative_market_pressure,
        ):
            if book.ledger is None:
                book.ledger = self.ledger
            if book.clock is None:
                book.clock = self.clock

        if self.balance_sheets is None:
            self.balance_sheets = BalanceSheetProjector(
                ownership=self.ownership,
                contracts=self.contracts,
                prices=self.prices,
                registry=self.registry,
                clock=self.clock,
                ledger=self.ledger,
            )

        if self.constraint_evaluator is None:
            self.constraint_evaluator = ConstraintEvaluator(
                book=self.constraints,
                projector=self.balance_sheets,
                clock=self.clock,
                ledger=self.ledger,
            )

        if self.valuation_comparator is None:
            self.valuation_comparator = ValuationComparator(
                valuations=self.valuations,
                prices=self.prices,
                ledger=self.ledger,
                clock=self.clock,
            )

        # v1.8.6 routine engine — thin plumbing that turns
        # RoutineExecutionRequest into a RoutineRunRecord on the
        # already-wired RoutineBook. The engine reads from
        # RoutineBook + InteractionBook + AttentionBook and writes
        # only to RoutineBook (via add_run_record's existing ledger
        # emission path). It does NOT hook into tick() / run() —
        # execution is caller-initiated.
        if self.routine_engine is None:
            self.routine_engine = RoutineEngine(
                routines=self.routines,
                interactions=self.interactions,
                attention=self.attention,
                clock=self.clock,
            )

        # v1.8.11 observation-menu builder — read-only join service
        # that builds per-actor ObservationMenu records from
        # visible signals, visible variable observations, and
        # active exposures, and writes them through
        # AttentionBook.add_menu's existing ledger emission path.
        # Does NOT hook into tick() / run().
        if self.observation_menu_builder is None:
            self.observation_menu_builder = ObservationMenuBuilder(
                attention=self.attention,
                signals=self.signals,
                variables=self.variables,
                exposures=self.exposures,
                interactions=self.interactions,
                clock=self.clock,
            )

        # v1.12.3 evidence resolver — stateless read-only helper
        # that turns the ids an actor selected (via
        # ``SelectedObservationSet``) plus optional explicit-id
        # kwargs into a structured ``ActorContextFrame``. Writes
        # nothing; never mutates any other source-of-truth book.
        # Future attention-conditioned mechanisms will consume
        # the frame instead of scanning books globally.
        if self.evidence_resolver is None:
            self.evidence_resolver = EvidenceResolver(kernel=self)

        # ------------------------------------------------------------------
        # v1.2.1 run-mode guard.
        #
        # The kernel exposes two execution paths:
        #   - tick() / run() — the v0 date-based path.
        #   - run_day_with_phases() / run_with_phases() — the v1.2 intraday
        #     phase path.
        #
        # Each simulation date must be processed by exactly one path.
        # Mixing them on the same date would advance the clock twice or
        # double-fire tasks, so the kernel records which mode was used for
        # each date and refuses to switch mid-date. The guard resets
        # naturally because the dict key is the simulation_date — once the
        # clock advances, the new date has no entry yet.
        # ------------------------------------------------------------------
        self._run_modes: dict = {}

    _RUN_MODE_TICK: str = "date_tick"
    _RUN_MODE_PHASES: str = "intraday_phase"

    def _enter_run_mode(self, mode: str) -> None:
        """
        Mark ``self.clock.current_date`` as being processed in ``mode``.

        Raises RuntimeError if the same date was previously processed in
        a different mode. Repeated calls in the *same* mode are
        idempotent (e.g. tick() processing one date and then re-entering
        tick mode at the same date after a manual clock rewind is OK;
        the modes match).
        """
        current = self.clock.current_date
        existing = self._run_modes.get(current)
        if existing is not None and existing != mode:
            raise RuntimeError(
                f"Cannot mix run modes on simulation date {current}: "
                f"already entered in {existing!r} mode; refusing to "
                f"enter {mode!r} mode. Use one of tick()/run() or "
                f"run_day_with_phases()/run_with_phases() per simulation "
                f"date, not both."
            )
        self._run_modes[current] = mode

    def register_object(self, obj: RegisteredObject) -> None:
        self.registry.register(obj)
        self.state.initialize_object(obj.id, obj.attributes)
        self.ledger.append(
            event_type="object_registered",
            simulation_date=self.clock.current_date,
            object_id=obj.id,
            payload={
                "kind": obj.kind,
                "type": obj.type,
                "space": obj.space,
            },
            space_id=obj.space,
        )

    def register_space(self, space: "BaseSpace") -> tuple[ScheduledTask, ...]:
        """
        Register a Space and its scheduled tasks.

        The space itself is registered in the Registry under its world_id
        so that future code can look it up by ID. State is not initialized
        for spaces because spaces are not state-bearing objects.

        Returns the tuple of scheduled tasks created for this space.
        """
        self.registry.register_space(
            space,
            object_id=space.world_id,
            metadata={"space_id": space.space_id},
        )
        self.ledger.append(
            event_type="object_registered",
            simulation_date=self.clock.current_date,
            object_id=space.world_id,
            payload={
                "kind": "space",
                "space_id": space.space_id,
                "frequencies": [freq.value for freq in space.frequencies],
            },
            space_id=space.space_id,
        )

        space.bind(self)

        scheduled = tuple(self.register_task(spec) for spec in space.task_specs())
        return scheduled

    def register_task(self, task: TaskSpec) -> ScheduledTask:
        scheduled = self.scheduler.register(task)
        self.ledger.append(
            event_type="task_scheduled",
            simulation_date=self.clock.current_date,
            task_id=task.id,
            object_id=task.target_id,
            payload={
                "name": task.name,
                "frequency": task.frequency.value,
            },
            space_id=task.space,
        )
        return scheduled

    def tick(self) -> None:
        self._enter_run_mode(self._RUN_MODE_TICK)
        due_tasks = self.scheduler.due_tasks(self.clock)
        for task in due_tasks:
            if callable(task.task):
                task.task(self)

            self.ledger.append(
                event_type="task_executed",
                simulation_date=self.clock.current_date,
                task_id=task.id,
                object_id=task.target_id,
                payload={
                    "name": task.display_name(),
                    "frequency": task.frequency.value,
                    "space": task.space,
                },
                space_id=task.space,
            )

        if self.clock.is_month_end():
            snapshot = self.state.snapshot(self.clock.current_date)
            self.ledger.append(
                event_type="state_snapshot_created",
                simulation_date=self.clock.current_date,
                object_id=snapshot.snapshot_id,
                payload={
                    "snapshot_id": snapshot.snapshot_id,
                    "state_hash": snapshot.state_hash,
                },
                snapshot_id=snapshot.snapshot_id,
                state_hash=snapshot.state_hash,
                space_id="world",
            )

        self.clock.advance()

    def run(self, days: int) -> None:
        if days < 0:
            raise ValueError("days must be non-negative")
        for _ in range(days):
            self.tick()

    # ------------------------------------------------------------------
    # v1.2 intraday phase dispatch (optional, additive)
    #
    # The methods below let callers run a single day phase-by-phase. The
    # v0 path (``tick`` / ``run``) is unchanged: it still fires every due
    # task regardless of declared phase, which is correct for v0 spaces
    # whose tasks all use Phase.MAIN. v1.2 phase-aware tasks should be
    # dispatched via ``run_day_with_phases``.
    # ------------------------------------------------------------------

    def iter_intraday_phases(
        self,
        sequence: PhaseSequence | None = None,
    ) -> Iterator[tuple[IntradayPhaseSpec, tuple[ScheduledTask, ...]]]:
        """
        Iterate the intraday phases for the current clock date, yielding
        each phase and the tasks due within it.

        This does *not* execute the tasks or advance the clock — it is a
        view, not a runner. Callers can use it to inspect what would
        happen, or to write their own dispatch loop. For the standard
        executor see :meth:`run_day_with_phases`.

        Tasks declared with ``Phase.MAIN`` are not included by any phase
        in this iterator; they are intentionally excluded so that the
        intraday dispatch is purely phase-aware. Use ``self.tick()``
        separately if you also need to fire MAIN tasks.
        """
        if sequence is None:
            sequence = PhaseSequence.default_phases()

        for phase_spec in sequence.list_phases():
            try:
                phase_value = Phase(phase_spec.phase_id)
            except ValueError:
                # Custom phase id with no enum mapping — no tasks can be
                # registered against it via TaskSpec, so it has no due
                # tasks. Yield it with an empty tuple for symmetry.
                yield phase_spec, ()
                continue
            due = self.scheduler.due_tasks(self.clock, phase=phase_value)
            yield phase_spec, due

    def run_day_with_phases(
        self,
        sequence: PhaseSequence | None = None,
    ) -> None:
        """
        Run one calendar day phase-by-phase, then advance the clock.

        For each phase in ``sequence`` (defaults to
        ``PhaseSequence.default_phases()``), the kernel runs every task
        registered with that phase whose frequency is due today. After
        all phases run, the kernel emits a ``state_snapshot_created``
        record on month-ends (mirroring v0 behavior in ``tick()``) and
        advances the clock by one day.

        ``Phase.MAIN`` tasks are *not* fired by this method. They are
        the v0 phase-agnostic bucket and continue to be dispatched
        through ``self.tick()``. A caller that wants both behaviors on
        the same day must compose them explicitly:

            kernel.tick()  # MAIN tasks + clock advance
            # (or)
            kernel.run_day_with_phases()  # phase-aware tasks + clock advance

        Mixing the two modes on the same simulation date is rejected by
        ``_enter_run_mode``: a date that has been processed in tick mode
        cannot subsequently be processed in phase mode, and vice versa.
        See §37.10 of `world_model.md` for the enforced rule.
        """
        self._enter_run_mode(self._RUN_MODE_PHASES)
        if sequence is None:
            sequence = PhaseSequence.default_phases()

        for phase_spec, due_tasks in self.iter_intraday_phases(sequence):
            for task in due_tasks:
                if callable(task.task):
                    task.task(self)

                self.ledger.append(
                    event_type="task_executed",
                    simulation_date=self.clock.current_date,
                    task_id=task.id,
                    object_id=task.target_id,
                    payload={
                        "name": task.display_name(),
                        "frequency": task.frequency.value,
                        "space": task.space,
                        "phase": phase_spec.phase_id,
                    },
                    space_id=task.space,
                )

        if self.clock.is_month_end():
            snapshot = self.state.snapshot(self.clock.current_date)
            self.ledger.append(
                event_type="state_snapshot_created",
                simulation_date=self.clock.current_date,
                object_id=snapshot.snapshot_id,
                payload={
                    "snapshot_id": snapshot.snapshot_id,
                    "state_hash": snapshot.state_hash,
                },
                snapshot_id=snapshot.snapshot_id,
                state_hash=snapshot.state_hash,
                space_id="world",
            )

        self.clock.advance()

    def run_with_phases(
        self,
        days: int,
        sequence: PhaseSequence | None = None,
    ) -> None:
        """Run ``days`` calendar days through intraday phases."""
        if days < 0:
            raise ValueError("days must be non-negative")
        for _ in range(days):
            self.run_day_with_phases(sequence)
