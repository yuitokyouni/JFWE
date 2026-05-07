# JFWE Answer Surface and Epistemic Boundary

*Positioning document. Clarifies what JFWE answers and
what it does not. No runtime change. No real data. No
investment advice. No legal-compliance claim. No
comparison to any named firm or product.*

---

## 1. The primitive question

JFWE does **not** primarily answer:

- "What will the index return be tomorrow?"
- "What will the price/index return be?"
- "Should we buy / sell / hold?"
- "What is the target price?"
- "What is the alpha?"
- "How would this strategy have backtested?"

JFWE **does** primarily answer:

> Given an event or evidence input, how would each
> **modeled actor** process the evidence, reallocate
> attention, cite supporting signals, and leave an
> auditable judgment trace?

That is the primitive answer surface. Every other
output is downstream of it.

---

## 2. Primitive output: a structured judgment ledger

JFWE's primitive output is **not a number**. It is a
**structured ledger** of judgment formation.

The trace shape is:

```
evidence  →  attention  →  review  →  citation graph  →  ledger
```

Concretely, for any input event:

- **Evidence.** What inputs entered the information
  environment (synthetic scenario drivers, stress
  programs, manual annotations, universe / calendar
  events, mandate profiles, strategic-relationship
  records — all the v1.18 → v1.27 record types).
- **Attention.** Which modeled actors attended to the
  evidence, given finite per-actor attention budgets
  with deterministic decay / crowding / saturation
  (the v1.12.last endogenous attention loop).
- **Review.** Which mandate / archetype / constraint
  shaped each actor's review (the v1.25 generic
  institutional-investor mandate / benchmark-pressure
  layer — closed-set archetypes only, never real
  institutional categories).
- **Citation graph.** Which records cited which
  earlier records as evidence, including manual
  annotations with v1.27.3 pseudonymous provenance.
- **Ledger.** The append-only `RecordType` event
  stream that records every storage-book emission
  with stable plain-id citations.

Every step in this chain is recoverable from the
append-only ledger. That recoverability is the value.

---

## 3. What is downstream, not primitive

Price, flow, and portfolio consequences **may** be
modeled downstream of the primitive judgment trace.
They are **not** the primitive answer surface of
JFWE. Downstream consequences are not part of public
v1.x — see
[`docs/v2_0_japan_public_calibration_boundary.md`](v2_0_japan_public_calibration_boundary.md)
§E for the explicit forbidden list (event-to-price
mapping, target-price / buy / sell / hold output,
portfolio construction output, alpha claim, backtest
claim).

The boundary is sharp: JFWE produces a judgment
trace; whatever a downstream consumer of that trace
chooses to do with it (in a separate, non-public
track) is out of scope.

---

## 4. Surprise events are inputs, not predictions

JFWE does **not** predict surprise events in advance.
A surprise event becomes part of the model only once
it has entered the information environment as an
input. After that, JFWE describes how modeled actors
process it, reallocate attention, cite evidence, and
update review state.

This is a deliberate choice. Predictive forecasts of
surprise events are out of scope; the primitive
question is the *judgment-formation response*, not
the *event probability*.

---

## 5. The system grows by cadence

There is no single punchline. The substrate grows
across milestones (v0.x → v1.27.last → v2.0.last →
v1.28.0 design pin), each adding a small, audited
piece. The cadence of the milestones is the artifact;
no single commit produces "the answer".

The answer surface (judgment-trace ledger) is itself
a cumulative artifact — the ledger captures every
emission across every milestone, queryable later for
post-event audit, stress review, and decision
archaeology.

---

## 6. Epistemic Boundary

The following are explicit epistemic limits. They
are **binding** and are not relaxed at any later
milestone without a fresh design pin.

### 6.1 No omniscience

JFWE does **not** claim omniscience. It does not
claim to know the full state of any real market, the
full population of any real participant set, or the
full information environment of any real event.

### 6.2 Modeled actors, not real participants

JFWE models a **finite, pinned set of modeled actor
archetypes** with deterministic processing rules. It
does **not** model:

- "every market participant",
- "all real human minds",
- the full empirical heterogeneity of any real
  market.

Every actor in JFWE is a **modeled actor**. The
language `_like` archetype suffix (e.g.
`pension_like`, `active_manager_like`,
`sovereign_like` from v1.25 mandate vocabularies) is
binding — these are not claims about real-world
institutional categories; they are closed-set
archetype labels for synthetic actors.

### 6.3 Diversity comes from explicit primitives

Where the modeled population produces diverse
behavior, the diversity comes from:

- **Heterogeneous archetypes** (closed-set
  `MANDATE_TYPE_LABELS` and equivalents).
- **Mandate profiles** (closed-set
  `BENCHMARK_PRESSURE_LABELS`,
  `LIQUIDITY_NEED_LABELS`,
  `LIABILITY_HORIZON_LABELS`,
  `STEWARDSHIP_PRIORITY_LABELS`,
  `REVIEW_FREQUENCY_LABELS`,
  `CONCENTRATION_TOLERANCE_LABELS`).
- **Constraints** (the v1.18 constraint records and
  their citation paths).
- **Attention budgets** (v1.12.last finite per-actor
  budget with deterministic decay / crowding /
  saturation).
- **Evidence resolvers** (v1.12.3 read-only
  resolution layer).

The diversity is **not** drawn from real-population
sampling, real-market histories, or real human
heterogeneity. It is drawn from explicit primitives
in the substrate.

### 6.4 Reproducibility from determinism + append-only

Reproducibility comes from:

- **Deterministic processing** at every storage
  book, readout, and export boundary (closed-set
  vocabularies; explicit sort orders; no wall-
  clock timestamps in canonical material; no
  Python memory addresses in canonical material).
- **Append-only ledger traces** (no in-place
  mutation of historical records; revisions append
  new records citing the prior; the v1.18 → v1.27
  storage-book convention).

The same evidence input applied to the same kernel
state must produce a byte-identical trace. This
property is enforced by the canonical
`living_world_digest` test fixtures
(`quarterly_default`, `monthly_reference`,
`scenario_monthly_reference_universe`, v1.20.4 CLI
bundle).

### 6.5 Surprise as input, not output

Surprise events are **inputs** to the model, not
outputs. JFWE does not produce surprise-event
forecasts. It produces judgment-formation traces
**conditional on** the events in the information
environment.

### 6.6 No legal-compliance claim

JFWE makes **no** legal-compliance claim of any
jurisdiction. It is not a regulatory compliance
artifact. It is not certified under any regulatory
framework. The substrate is research software per
the LICENSE and `Disclaimer` sections of the README.

### 6.7 No comparison to named firms or products

This document and its companion sections do **not**
compare JFWE to any named firm, product, vendor,
research provider, or competitive offering. The
positioning is intrinsic (what JFWE is and is not),
not relative.

---

## 7. Auditability surface

The judgment trace can be queried later for:

- **Post-event audit.** Reconstruct which modeled
  actors attended to which evidence, in which order,
  under which mandate, citing which records.
- **Stress review.** Replay how a stress-program
  application propagated through the citation graph
  (the v1.21 stress composition layer + v1.22
  stress readout reflection + v1.23 attention-
  crowding case study).
- **Decision archaeology.** Trace, after the fact,
  the substrate-level reasons a manual annotation
  was emitted, who (pseudonymously) authored it,
  under what authority, citing which evidence (the
  v1.24 manual annotation layer + v1.27.3
  provenance hardening).

These three queries are the **value-bearing**
queries of JFWE. None of them is a price forecast.
None of them is an investment recommendation. None
of them is an alpha claim.

---

## 8. Forbidden output classes (re-pinned)

JFWE forbids, at the substrate level, every output
class below — across every milestone, in every
storage book, in every readout, in every export
section:

- Buy / sell / hold labels.
- Target prices.
- Portfolio allocations / target weights /
  rebalancing decisions.
- Expected returns / forecasts /
  recommendations / advice.
- Tracking-error values / benchmark numerical
  comparisons / active share / alpha claims.
- Backtest claims of any form.
- Event-to-price mapping (already forbidden at
  v1.26.0).
- Centrality / systemic-importance / network-
  score outputs (already forbidden at v1.27.0).
- Ownership-percentage / voting-power / market-
  value fields on relationship records.

These forbidden classes are enforced by the v1.x
composed forbidden-token sets
(`FORBIDDEN_RUN_EXPORT_FIELD_NAMES` /
`FORBIDDEN_STRESS_*_FIELD_NAMES` /
`FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES` /
`FORBIDDEN_INVESTOR_MANDATE_FIELD_NAMES` /
`FORBIDDEN_UNIVERSE_CALENDAR_FIELD_NAMES` /
`FORBIDDEN_STRATEGIC_RELATIONSHIP_FIELD_NAMES` /
`FORBIDDEN_ANNOTATION_PROVENANCE_FIELD_NAMES`)
that scan every dataclass field name, payload
key, metadata key, and label value at construction
time.

---

## 9. Closing statement

JFWE is an **auditable judgment-trace engine**, not
a point-forecasting simulator. The primitive answer
surface is a structured ledger of judgment
formation, not a number. Surprise events are inputs.
Diversity is explicit. Reproducibility is
deterministic and ledger-based. Real-world
forecasting, investment advice, alpha claims, and
real-data calibration are out of scope.

The substrate grows by cadence. The cadence is the
artifact.
