from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from world.events import WorldEvent
from world.external_processes import ExternalFactorObservation
from world.institutions import InstitutionalActionRecord
from world.ledger import RecordType
from world.signals import InformationSignal
from world.valuations import ValuationGap, ValuationRecord


@dataclass
class ReferenceLoopRunner:
    """
    Thin orchestrator for the v1.6 reference closed loop.

    The runner does not decide anything. Each method takes explicit
    record references as inputs, builds the next record in the chain
    with appropriate cross-references (``related_ids``, ``input_refs``,
    ``output_refs``, ``parent_record_ids``, ``evidence_refs``), and
    delegates the actual write to the existing kernel-level book that
    owns the record type. The runner's job is solely to wire the chain
    so the resulting ledger forms a complete causal graph.

    The loop is structural, not behavioral. v1.6 does not implement
    price formation, investor trading, bank credit decisions,
    corporate actions, policy decisions, relationship-driven behavior,
    or external shock propagation. It demonstrates that all the v1
    record types can be linked into a single end-to-end trace
    without any module mutating state outside its own book.
    """

    kernel: Any  # WorldKernel — typed as Any to avoid an import cycle.

    # ------------------------------------------------------------------
    # Step 1: external observation
    # ------------------------------------------------------------------

    def record_external_observation(
        self,
        process_id: str,
        as_of_date: str,
        phase_id: str | None = None,
        *,
        source_id: str = "system",
    ) -> ExternalFactorObservation:
        """
        Step 1. Record an external factor observation through the
        constant-process helper. The observation is stamped with the
        given ``phase_id`` (e.g., ``"overnight"``).
        """
        return self.kernel.external_processes.create_constant_observation(
            process_id,
            as_of_date,
            phase_id=phase_id,
            source_id=source_id,
        )

    # ------------------------------------------------------------------
    # Step 2: signal from observation
    # ------------------------------------------------------------------

    def emit_signal_from_observation(
        self,
        observation: ExternalFactorObservation,
        signal_id: str,
        signal_type: str,
        source_id: str,
        subject_id: str,
        *,
        visibility: str = "public",
        confidence: float = 1.0,
    ) -> InformationSignal:
        """
        Step 2. Emit an information signal that references the
        observation in ``related_ids`` and carries its identifying
        fields in ``payload``.
        """
        signal = InformationSignal(
            signal_id=signal_id,
            signal_type=signal_type,
            subject_id=subject_id,
            source_id=source_id,
            published_date=observation.as_of_date,
            visibility=visibility,
            confidence=confidence,
            payload={
                "observation_id": observation.observation_id,
                "factor_id": observation.factor_id,
                "value": observation.value,
            },
            related_ids=(observation.observation_id,),
        )
        return self.kernel.signals.add_signal(signal)

    # ------------------------------------------------------------------
    # Step 3: valuation referencing the signal
    # ------------------------------------------------------------------

    def record_valuation_from_signal(
        self,
        signal: InformationSignal,
        valuation_id: str,
        subject_id: str,
        valuer_id: str,
        valuation_type: str,
        purpose: str,
        method: str,
        as_of_date: str,
        estimated_value: float | None,
        currency: str = "unspecified",
        numeraire: str = "unspecified",
        confidence: float = 1.0,
        assumptions: Mapping[str, Any] | None = None,
    ) -> ValuationRecord:
        """
        Step 3. Record a valuation that explicitly references the
        signal in ``related_ids`` and ``inputs``.
        """
        valuation = ValuationRecord(
            valuation_id=valuation_id,
            subject_id=subject_id,
            valuer_id=valuer_id,
            valuation_type=valuation_type,
            purpose=purpose,
            method=method,
            as_of_date=as_of_date,
            estimated_value=estimated_value,
            currency=currency,
            numeraire=numeraire,
            confidence=confidence,
            assumptions=dict(assumptions or {}),
            inputs={"signal_id": signal.signal_id},
            related_ids=(signal.signal_id,),
        )
        return self.kernel.valuations.add_valuation(valuation)

    # ------------------------------------------------------------------
    # Step 4: comparator → ValuationGap
    # ------------------------------------------------------------------

    def compare_valuation_to_price(
        self,
        valuation_id: str,
    ) -> ValuationGap:
        """
        Step 4. Compare the valuation to the latest priced observation
        (via the existing ``ValuationComparator``). The comparator
        emits ``valuation_compared`` to the ledger with
        ``parent_record_ids`` linking back to the originating
        ``valuation_added`` record.
        """
        return self.kernel.valuation_comparator.compare_to_latest_price(
            valuation_id
        )

    # ------------------------------------------------------------------
    # Step 5: institutional action consuming valuation + gap
    # ------------------------------------------------------------------

    def record_institutional_action(
        self,
        action_id: str,
        institution_id: str,
        action_type: str,
        as_of_date: str,
        valuation: ValuationRecord,
        gap: ValuationGap,
        *,
        phase_id: str | None = None,
        instrument_ids: tuple[str, ...] = (),
        planned_output_signal_id: str | None = None,
        extra_input_refs: tuple[str, ...] = (),
        extra_target_ids: tuple[str, ...] = (),
    ) -> InstitutionalActionRecord:
        """
        Step 5. Record an institutional action whose:

        - ``input_refs`` include the valuation_id (and any caller-
          supplied extras).
        - ``output_refs`` include the planned follow-up signal id, if
          provided. v1.3 documents that ``output_refs`` claims
          authorship over records the action's writer creates; the
          loop runner creates that signal in step 6.
        - ``parent_record_ids`` link to the ledger record_id of the
          originating ``valuation_added`` and ``valuation_compared``
          records, so the audit trail forms a causal graph.
        - ``payload`` carries the gap's numeric outcome for queries.

        The action does not mutate any other book. Per v1.3's
        4-property action contract, side effects (a follow-up signal,
        an event publication) are produced by the runner's later
        steps and merely *referenced* by this action.
        """
        # Look up parent ledger records for the causal graph.
        parent_ids: tuple[str, ...] = ()
        valuation_added = self.kernel.ledger.query(
            record_type=RecordType.VALUATION_ADDED,
            object_id=valuation.valuation_id,
        )
        if valuation_added:
            parent_ids = parent_ids + (valuation_added[0].record_id,)
        valuation_compared = self.kernel.ledger.query(
            record_type=RecordType.VALUATION_COMPARED,
            object_id=valuation.valuation_id,
        )
        if valuation_compared:
            parent_ids = parent_ids + (valuation_compared[0].record_id,)

        input_refs = (valuation.valuation_id,) + tuple(extra_input_refs)
        target_ids = (valuation.subject_id,) + tuple(extra_target_ids)
        output_refs: tuple[str, ...] = ()
        if planned_output_signal_id is not None:
            output_refs = (planned_output_signal_id,)

        action = InstitutionalActionRecord(
            action_id=action_id,
            institution_id=institution_id,
            action_type=action_type,
            as_of_date=as_of_date,
            phase_id=phase_id,
            input_refs=input_refs,
            output_refs=output_refs,
            target_ids=target_ids,
            instrument_ids=instrument_ids,
            payload={
                "valuation_id": valuation.valuation_id,
                "estimated_value": gap.estimated_value,
                "observed_price": gap.observed_price,
                "absolute_gap": gap.absolute_gap,
                "relative_gap": gap.relative_gap,
            },
            parent_record_ids=parent_ids,
        )
        return self.kernel.institutions.add_action_record(action)

    # ------------------------------------------------------------------
    # Step 6: follow-up signal referencing the action
    # ------------------------------------------------------------------

    def emit_signal_from_action(
        self,
        action: InstitutionalActionRecord,
        signal_id: str,
        signal_type: str,
        source_id: str,
        subject_id: str,
        *,
        visibility: str = "public",
        confidence: float = 1.0,
    ) -> InformationSignal:
        """
        Step 6. Emit a follow-up signal that references the action in
        ``related_ids`` and carries the ``action_id`` in ``payload``.
        Pair with ``planned_output_signal_id`` from step 5 so the
        action's ``output_refs`` already names this signal.
        """
        signal = InformationSignal(
            signal_id=signal_id,
            signal_type=signal_type,
            subject_id=subject_id,
            source_id=source_id,
            published_date=action.as_of_date,
            visibility=visibility,
            confidence=confidence,
            payload={"action_id": action.action_id},
            related_ids=(action.action_id,),
        )
        return self.kernel.signals.add_signal(signal)

    # ------------------------------------------------------------------
    # Step 7: publish a WorldEvent referencing the follow-up signal
    # ------------------------------------------------------------------

    def publish_signal_event(
        self,
        signal: InformationSignal,
        event_id: str,
        source_space: str,
        target_spaces: tuple[str, ...],
        *,
        event_type: str = "signal_emitted",
        delay_days: int = 0,
        on_date: Any = None,
    ) -> WorldEvent:
        """
        Step 7. Publish a WorldEvent that references the signal by
        ``signal_id`` (in payload and ``related_ids``). The bus
        delivers per the v0.3 next-tick rule; on day D+1 the targets
        receive ``event_delivered`` ledger records that complete the
        chain.

        The runner also records ``event_published`` to the ledger so
        the audit trail matches what ``BaseSpace`` records when a
        space's ``emit()`` returns events. Direct bus publication
        (the runner path) and space-driven publication (the
        BaseSpace path) thus produce equivalent ledger entries.
        """
        event = WorldEvent(
            event_id=event_id,
            simulation_date=signal.published_date,
            source_space=source_space,
            target_spaces=target_spaces,
            event_type=event_type,
            payload={"signal_id": signal.signal_id},
            related_ids=(signal.signal_id,),
            delay_days=delay_days,
        )
        published = self.kernel.event_bus.publish(event, on_date=on_date)

        # Mirror the BaseSpace audit trail for runner-driven publishes.
        current_date = self.kernel.clock.current_date
        self.kernel.ledger.append(
            event_type="event_published",
            simulation_date=current_date,
            object_id=event.event_id,
            source=event.source_space,
            payload={
                "event_type": event.event_type,
                "source_space": event.source_space,
                "target_spaces": list(event.target_spaces),
                "visibility": event.visibility,
                "delay_days": event.delay_days,
                "related_ids": list(event.related_ids),
            },
            space_id=event.source_space,
            correlation_id=event.event_id,
            confidence=event.confidence,
        )
        return published
