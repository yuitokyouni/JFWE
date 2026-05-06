# Case Study 002 — Investor Mandate Attention Context

*Companion case study to v1.25.4 (Generic investor
mandate / benchmark-pressure case-study milestone).
Demonstrates how the v1.25.2 mandate-conditioned
attention/review-context readout differentiates two
investor archetypes reviewing **the same** v1.21.3
stress readout — without producing trades, allocations,
recommendations, or any actor decision.*

This case study is a **research-defensible read-only
demonstration**, not a prediction. It pins, in code:

- two investor archetypes (e.g. a `pension_like` profile
  with `liability_horizon = "long"` /
  `benchmark_pressure = "low"`, and an
  `active_manager_like` profile with
  `liability_horizon = "short"` /
  `benchmark_pressure = "high"`);
- the **same** stress program application — the v1.21.2
  receipt, the v1.21.3 readout, and the v1.18.2 +
  v1.18.2 records the program emitted are byte-identical
  for both investors;
- different `review_context_labels` and
  `selected_attention_bias_labels` projected by the
  v1.25.2 mandate readout for each investor;
- zero v1.16.2 `InvestorMarketIntentRecord` emitted, zero
  trades, zero allocations, zero recommendations.

The case study **does not** claim:

- a price prediction, a forecast, or an expected
  response;
- a trade / order / execution / allocation / target
  weight / overweight / underweight / rebalancing;
- a tracking-error value, an alpha number, a
  performance metric;
- a recommendation, an investment-advice surface, or
  any actor-decision logic;
- a real-world investor archetype, a real-world
  institution, or a real-world stress episode;
- an interaction-inference label (no `amplify` /
  `dampen` / `offset` / `coexist`);
- an aggregate / combined / net / dominant / composite
  stress output.

The companion documents are:

- [`v1_25_institutional_investor_mandate_benchmark_pressure.md`](v1_25_institutional_investor_mandate_benchmark_pressure.md)
  §14 — the v1.25.4 design pin.
- [`research_note_002_validating_stress_citation_graphs_without_price_prediction.md`](research_note_002_validating_stress_citation_graphs_without_price_prediction.md)
  — the validation framing v1.25.4 inherits.
- [`case_study_001_attention_crowding_uncited_stress.md`](case_study_001_attention_crowding_uncited_stress.md)
  — the v1.23.3 case study v1.25.4 sits alongside.

---

## 1. Problem framing

The v1.25.0 design pin §14 frames the case study: two
investors, both reviewing the same v1.21.3 stress
readout, project **different** review-context labels
and **different** selected attention-bias labels because
their mandate profiles differ. The point is not that
one investor is "right" and the other "wrong"; both are
descriptive projections. The point is that the v1.25.2
readout faithfully surfaces the difference — without
producing any actor behavior.

A reviewer reading the case-study report can:

1. Confirm both investors share the same
   `stress_program_application_id` /
   `stress_readout_id`.
2. Read each investor's `review_context_labels` tuple
   and notice the difference (e.g. one carries
   `benchmark_context`, the other does not).
3. Read each investor's
   `selected_attention_bias_labels` tuple and notice
   the bias difference (e.g. one carries
   `liquidity_review`, the other does not).
4. Verify the kernel emitted **zero** new investor /
   market-intent / actor-decision records during the
   case-study build.
5. Confirm the rendered markdown carries no trade /
   order / allocation / recommendation / forecast /
   target-weight / expected-return wording outside the
   pinned boundary-statement disclaimer block.

That is the v1.25.4 contribution: a research-defensible
demonstration that mandate-conditioned attention diverges
across archetypes, without inventing any actor-behavior
mechanism.

---

## 2. What the case-study report contains

The v1.25.4 helper
:func:`world.investor_mandate_case_study.build_investor_mandate_case_study_report`
takes a stress-applied kernel + a stress program
application id + a list of mandate profile ids and
returns a deterministic ``dict`` with the following
keys:

| Key | Type | Source |
| --- | ---- | ------ |
| `case_study_id` | `str` | derived from the program-application id |
| `stress_program_application_id` | `str` | caller-supplied |
| `stress_readout_id` | `str` | from v1.21.3 readout |
| `stress_program_template_id` | `str` | from v1.21.3 readout |
| `investor_ids` | `tuple[str, ...]` | per-profile, in input order |
| `mandate_profile_ids` | `tuple[str, ...]` | as supplied |
| `mandate_type_labels` | `tuple[str, ...]` | per profile |
| `review_context_labels_by_investor` | `dict[str, tuple[str, ...]]` | from v1.25.2 readout per profile |
| `attention_bias_labels_by_investor` | `dict[str, tuple[str, ...]]` | from v1.25.2 readout per profile |
| `cited_mandate_fields` | `tuple[str, ...]` | union of cited fields across profiles |
| `warnings` | `tuple[str, ...]` | per-profile warnings + degenerate-case diagnostic |
| `metadata` | `dict` | opaque caller metadata, scanned for forbidden keys |
| `boundary_statement` | `str` | pinned anti-claim block |

The companion renderer
:func:`world.investor_mandate_case_study.render_investor_mandate_case_study_markdown`
emits a deterministic 7-section markdown summary; same
report → byte-identical bytes.

---

## 3. Read-only / no-mutation discipline

The helper is read-only:

- It does **not** call
  :func:`world.stress_applications.apply_stress_program` —
  the case study runs after the program has already
  been applied.
- It does **not** call
  :func:`world.scenario_applications.apply_scenario_driver`.
- It does **not** call
  :meth:`world.investor_mandates.InvestorMandateBook.add_profile`
  or any v1.15.x / v1.16.x investor-intent helper.
- It does **not** mutate any kernel book — every
  relevant snapshot is byte-identical pre / post call.
- It does **not** emit a ledger record. v1.25.4 ships
  **no** new RecordType.

Re-running the helper on the same kernel state with the
same arguments produces a byte-identical report. Cat 1
determinism extends verbatim.

---

## 4. Hard boundary (re-pinned at v1.25.4)

v1.25.4 inherits and re-pins the v1.25.0 hard boundary
in full:

**No real-world output.**
- No price formation, no market price, no order, no
  trade, no execution, no clearing, no settlement, no
  financing execution.
- No forecast path, no expected return, no target
  price, no recommendation, no investment advice.
- No magnitude, no probability, no expected response.
- No firm decision, no investor action, no bank
  approval logic.
- No portfolio allocation, no target weight, no
  overweight, no underweight, no rebalancing.

**No real-world input.**
- No real data ingestion.
- No real institutional identifiers.
- No licensed taxonomy dependency.
- No Japan calibration.

**No autonomous reasoning.**
- No LLM execution at runtime.
- No LLM prose accepted as source-of-truth.
- No interaction auto-inference.
- No aggregate / combined / net / dominant / composite
  stress output.
- No tracking-error value, no benchmark identifier, no
  alpha / performance metric.

**No source-of-truth book mutation.**
- v1.25.4 is read-only over an already stress-applied
  kernel. Pre-existing book snapshots remain byte-
  identical pre / post any v1.25.4 helper call.

**No new UI region.**
- v1.25.4 does not touch the static UI mockup.

**No digest movement.**
- All v1.18.last / v1.19.last / v1.20.last / v1.21.last
  / v1.22.last canonical ``living_world_digest`` values
  remain byte-identical at v1.25.4.

---

## 5. What v1.25.4 supports

The case study is a research artifact: it shows, in
code, that the v1.25.2 mandate-conditioned attention/
review-context readout is **legible enough to support
mandate-divergence audit without predictive accuracy
scoring**. A reviewer reading the case study's output
can:

1. Identify exactly which closed-set review-context
   labels each investor's mandate projects under the
   shared stress event.
2. Identify exactly which attention-bias labels each
   investor's mandate emphasises.
3. Re-run the helper and verify byte-identity (Cat 1).
4. Verify that the kernel emitted no investor /
   market-intent / actor-decision records (Cat
   read-only-discipline).
5. Confirm the rendered markdown carries no trade /
   allocation / recommendation / forecast / target-
   weight / expected-return wording outside the
   pinned boundary statement.

That is the v1.25.4 contribution: a research-defensible
demonstration of mandate-conditioned attention
divergence, without inventing any new audit semantics.

---

## 6. Future work

Future milestones may extend the case study to:

- the **citation-graph diff format** (research note
  002 §4.2 Cat 6 placeholder) — comparing the cited /
  uncited sets across mandates;
- the **inter-reviewer reproducibility** layer
  (research note 002 §4.2 Cat 5 placeholder) —
  pairing each per-investor readout with a v1.24
  manual annotation from a reviewer who reads only
  one of the two profiles;
- the **v1.26 entity lifecycle + reporting calendar**
  candidate — letting mandates condition over time-
  varying entity universes;
- the **v1.27 generic strategic relationship
  network** candidate — letting mandates condition
  over relationship-graph context.

None of these are in scope at v1.25.4. The case study
ships the substrate they will build on.
