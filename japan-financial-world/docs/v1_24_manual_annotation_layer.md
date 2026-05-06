# v1.24 Manual Annotation Layer — Design Note

*v1.24 is the **manual-annotation interaction layer**
candidate. It allows a human reviewer to attach explicit,
auditable annotations to existing citation-graph records —
v1.21.3 stress readouts, v1.22.1 export entries, v1.23.3
case-study reports, v1.18.2 scenario applications + context
shifts, the validation pin sub-dicts — without ever
inferring a combined stress effect, mutating the world,
triggering actor behavior, or claiming a causal proof.*

This document is **docs-only at v1.24.0**. It introduces no
runtime module, no new dataclass, no new ledger event, no
new test, no new label vocabulary, no new behavior. It is
the binding scope pin for v1.24.x; v1.24.1 / v1.24.2 /
v1.24.3 / v1.24.last must implement exactly to this design
or the design must be re-pinned.

The companion documents are:

- [`v1_23_substrate_hardening_validation_foundation.md`](v1_23_substrate_hardening_validation_foundation.md)
  §12 — the v1.23.last freeze v1.24 inherits.
- [`research_note_002_validating_stress_citation_graphs_without_price_prediction.md`](research_note_002_validating_stress_citation_graphs_without_price_prediction.md)
  §4.2 — the Cat 5 inter-reviewer reproducibility
  placeholder this layer materialises.
- [`case_study_001_attention_crowding_uncited_stress.md`](case_study_001_attention_crowding_uncited_stress.md)
  — the v1.23.3 read-only audit object reviewers will
  annotate over.
- [`world_model.md`](world_model.md) §133 — the
  constitutional position of v1.24.
- [`v1_21_stress_composition_layer.md`](v1_21_stress_composition_layer.md)
  *Deferred: StressInteractionRule* — the binding
  rationale for forbidding interaction-label inference.
  v1.24 reuses that rationale verbatim and **does not**
  loosen it.

---

## 1. Scope statement (binding)

v1.24's single goal is narrow: **let a human reviewer mark
existing citation-graph records with closed-set annotation
labels, append-only, read-only with respect to the world.**

Concretely:

- A **manual annotation** is a human-authored, append-only
  audit overlay on existing record ids.
- It **cites** — never mutates — its target records via
  plain-id references.
- It **does not** create downstream behavior, does not
  trigger any actor decision, does not feed into any
  classifier / closed-set rule / LLM, and does not
  propagate into the v1.21.x stress chain or the v1.18.x
  scenario chain.
- It **does not** infer a combined stress effect (no
  `amplify` / `dampen` / `offset` / `coexist` annotation
  is allowed, even if a reviewer authors it manually —
  the v1.21.0a *Deferred: StressInteractionRule* boundary
  applies to manual annotations too).
- Its closed-set vocabulary is small: `same_review_frame`,
  `shared_context_surface`, `uncited_stress_candidate`,
  `partial_application_note`, `citation_gap_note`,
  `needs_followup_review`,
  `reviewer_disagreement_placeholder`, `unknown`.

What v1.24 is (binding):

- **Human-authored only.** Every record carries
  `source_kind = "human"` and
  `reasoning_mode = "human_authored"`. The closed sets
  contain **exactly one element each** at v1.24; expanding
  them requires a fresh design pin.
- **Append-only.** Annotations are stored in a single
  append-only book; no annotation ever mutates a prior
  annotation, and no annotation ever mutates a cited
  record.
- **Read-only with respect to the world.** No source-of-
  truth book mutation, no scenario application, no stress
  application, no attention emission, no actor behavior,
  no ledger record beyond the storage event itself.
- **Boundary-preserved.** The v1.23.1 canonical
  `world.forbidden_tokens` composition applies verbatim:
  no annotation field, metadata key, payload key, or
  optional `note_text` value may carry a forbidden token.
- **Sequence is strictly serial.** v1.24.0 ships docs only;
  v1.24.1 ships storage; v1.24.2 ships the read-only
  readout + validation hook; v1.24.3 ships export +
  optional minimal UI; v1.24.last ships the docs-only
  freeze.

What v1.24 is **NOT** (binding):

- v1.24 is **NOT** auto-inference. No helper, classifier,
  closed-set rule table, LLM, or any other automated layer
  may emit a `ManualAnnotationRecord`. Records are
  inserted only by an explicit human-authored call to the
  storage book.
- v1.24 is **NOT** stress interaction inference. The
  v1.21.0a / v1.22.0 / v1.23.x interaction-label
  vocabulary (`amplify`, `dampen`, `offset`, `coexist`,
  `aggregate`, `composite`, `net`, `dominant`) remains
  forbidden across the entire annotation surface — the
  storage layer rejects these tokens at construction
  time.
- v1.24 is **NOT** causal proof. An annotation is a
  reviewer's observation about the citation graph, not an
  assertion that one record caused another.
- v1.24 is **NOT** investment advice / a recommendation /
  a forecast / a price / an outcome / an impact / a risk
  score. The v1.18.0 / v1.19.0 / v1.21.0a / v1.22.0
  forbidden-name boundary applies to annotation field
  names, payload keys, metadata keys, and the optional
  `note_text` value (forbidden-token boundary scan).
- v1.24 is **NOT** Japan-calibrated, real-data-driven, or
  LLM-authored. Public v1.x stays jurisdiction-neutral and
  synthetic; v1.24 inherits that boundary verbatim.
- v1.24 is **NOT** a UI rebuild. v1.24.3 may add a small
  read-only "Manual annotations" panel inside an existing
  sheet; it adds no tab, no backend, no scrollable
  free-text input.

---

## 2. Why v1.24 follows v1.23 (validation foundation)

The v1.23.2 validation foundation pinned four properties of
the audit object:

- **Cat 1 — Determinism.** Same kernel state → byte-
  identical readout, markdown summary, export entry.
- **Cat 2 — Boundary preservation.** The audit object
  carries no v1.21.0a / v1.22.0 forbidden token at any
  surface.
- **Cat 3 — Citation completeness.** Every plain-id
  citation in the readout resolves to an extant kernel
  record.
- **Cat 4 — Partial-application visibility.** When stress
  application is partial, the readout, markdown summary,
  and export entry all surface the partial state.

Two categories were left as placeholders in research note
002 §4.2:

- **Cat 5 — Inter-reviewer reproducibility (placeholder).**
  Two human reviewers reading the same readout + same
  fixture should reach the same audit conclusion. v1.23.2
  shipped only the format placeholder
  (`tests/fixtures/inter_reviewer/`).
- **Cat 6 — Null-model comparison (placeholder).** The
  citation-graph diff format between with-stress and
  without-stress kernels was deferred.

**v1.24 partially materialises Cat 5.** The format
placeholder gains a runtime surface: a reviewer can attach
a `ManualAnnotationRecord` to a v1.21.3 readout, a v1.22.1
export entry, or a v1.23.3 case-study report; a future
v1.x milestone (or external research collaboration) can
populate the annotation book with notes from multiple
reviewers and read them back via the v1.24.2 readout. The
inter-reviewer-agreement comparison itself is not pinned
at v1.24 — it requires a defined comparison protocol — but
the *substrate* the comparison will run on is shipped.

v1.24 does **not** address Cat 6. Null-model comparison
remains deferred.

The v1.24 framing is therefore: **manual annotation is the
v1.23.2 Cat 5 placeholder's runtime surface, scoped to
the v1.21.3 / v1.22.1 / v1.23.3 audit objects.**

---

## 3. What manual annotation is (binding)

A **manual annotation** is one immutable, human-authored
record attached to one or more existing citation-graph
record ids. It carries:

- a small closed-set scope label (the kind of record being
  annotated: stress readout, stress program application,
  scenario context shift, validation report, case study,
  citation graph, unknown);
- a small closed-set annotation label (the reviewer's
  observation: same review frame, shared context surface,
  uncited stress candidate, partial application note,
  citation gap note, follow-up review needed, reviewer
  disagreement placeholder, unknown);
- a tuple of plain-id citations to the records the
  annotation applies to;
- a `source_kind` of `"human"` and a `reasoning_mode` of
  `"human_authored"` — the closed sets contain exactly
  one element each at v1.24;
- a small reviewer-role label (e.g. `lead_reviewer`,
  `secondary_reviewer`, `unknown`) — the reviewer-role
  closed set is finalised at v1.24.1, but v1.24.0 pins
  the **shape** of the field;
- an optional `case_study_id` cross-reference (e.g. the
  v1.23.3 attention-crowding case study);
- an optional `created_for_record_id` cross-reference
  (the single primary record the annotation was created
  in response to, if there is one);
- an optional `note_text` free-form string — descriptive
  only, never source-of-truth, scanned at construction
  for v1.24.0 forbidden tokens;
- a small `boundary_flags` mapping, default-pinned to the
  v1.24 anti-claim set;
- an opaque `metadata` mapping, scanned for forbidden
  keys.

A manual annotation is **descriptive**, not interpretive.
It says "this is what I, the reviewer, observed about the
citation graph", not "this is what the citation graph
implies about the world."

---

## 4. What manual annotation is **NOT** (binding)

This list is itself part of the boundary. v1.24.x rejects
each item at construction time (forbidden-name scan,
closed-set membership check, source-kind / reasoning-mode
allowlist):

- **NOT auto-inference.** Records are inserted only by an
  explicit human-authored call to the storage book. No
  helper, classifier, closed-set rule, LLM, or other
  automated layer may emit a record. The storage layer
  does not provide an "auto-annotate" entry point.
- **NOT causal proof.** An annotation labelled
  `same_review_frame` does not assert that two records
  share a causal frame in the world; it asserts that the
  reviewer is reading them under one review frame.
- **NOT stress interaction inference.** No `amplify` /
  `dampen` / `offset` / `coexist` annotation is allowed,
  even when authored by a human. The v1.21.0a *Deferred:
  StressInteractionRule* boundary applies to manual
  annotations too — interaction-label inference is
  forbidden across the entire layer.
- **NOT aggregate stress output.** No `aggregate` /
  `combined` / `net` / `dominant` / `composite`
  annotation field, label, or value is allowed.
- **NOT a price / forecast / recommendation.** No
  `forecast` / `prediction` / `expected_return` /
  `target_price` / `recommendation` / `investment_advice`
  / `buy` / `sell` / `order` / `trade` / `execution`
  field, label, or value is allowed.
- **NOT an actor decision.** No `firm_decision` /
  `investor_action` / `bank_approval` /
  `trading_decision` / `optimal_capital_structure`
  field, label, or value is allowed.
- **NOT a real-data ingest.** No `real_data` /
  `japan_calibration` / real-issuer / licensed-taxonomy
  field, label, or value is allowed.
- **NOT LLM execution.** v1.24.x does not invoke any LLM
  at runtime. No `llm_output` / `llm_prose` /
  `prompt_text` field, label, or value is allowed.
- **NOT a source-of-truth mutation.** Annotation records
  cite — never mutate — their target records. The
  storage book emits exactly one ledger record per
  successful `add_annotation(...)` call (the storage
  event itself); pre-existing kernel-book snapshots
  remain byte-identical pre / post call.
- **NOT a downstream-behavior trigger.** The v1.18.2
  scenario chain, the v1.21.x stress chain, the v1.16.x
  closed-loop attention path, the v1.15.x / v1.16.x
  market-intent path, and the v1.14.x financing-path
  layer are all read-only with respect to manual
  annotations. No annotation is consumed as input to any
  of these.

---

## 5. What records manual annotations may cite (binding)

`cited_record_ids` is a tuple of plain-id citations. v1.24
does **not** invent a new record-id format; it reuses the
existing prefixes. The expected (binding closed set, at
v1.24.0 design level) cited-record kinds are:

- `stress_field_readout:<stress_program_application_id>`
  — a v1.21.3 :class:`StressFieldReadout` carrying
  `readout_id` of this shape.
- `stress_program_application:<...>` — a v1.21.2
  :class:`StressProgramApplicationRecord`.
- `stress_program_template:<...>` — a v1.21.1
  :class:`StressProgramTemplate`.
- `scenario_application:<...>` — a v1.18.2
  :class:`ScenarioDriverApplicationRecord`.
- `scenario_context_shift:<...>` — a v1.18.2
  :class:`ScenarioContextShiftRecord`.
- `attention_crowding_case_study:<stress_program_application_id>`
  — a v1.23.3 case-study report (the helper's
  `case_study_id` field).
- `validation_report:...` — a v1.23.2-shaped validation
  report id (no runtime record exists at v1.23.last; the
  cited-id format is reserved for a future v1.x
  validation-report record type, but a manual annotation
  may already cite the format).

The storage layer does **not** dereference these citations
to confirm they exist in any specific kernel book — that
would couple v1.24 to the v1.18.x / v1.21.x / v1.23.x
storage layers in a way that breaks the
"runtime-book-free" discipline. Instead, the v1.24.2
read-only readout (a separate module) will cross-reference
cited ids against the kernel's existing books and surface
**unresolved cited ids** under
`unresolved_cited_record_ids`. This mirrors the v1.21.3
*storage-existence audit* pattern and the v1.23.2 Cat 3
citation-completeness pin.

The v1.24.2 readout therefore answers the reviewer's
question "is the annotation pointing at something that
still exists?" without making the storage layer cross-
referencable in a way that constrains future schema
changes.

---

## 6. Why annotations are human-authored only (binding)

The v1.21.0a *Deferred: StressInteractionRule* design pin
(carried verbatim into v1.22.0 / v1.23.0 and again into
v1.24.0) gave three reasons interaction inference is
deferred to v1.22+ "as `manual_annotation` only — never
auto-inferred":

1. **Auto-inferred composition is a pseudo-causal
   claim.** A classifier that takes two stress steps and
   labels their composition as `amplify` is asserting a
   causal model of stress interaction. Public FWE
   declines to ground that model.
2. **No real-world feedback to validate against.** v1.x
   has no real-world stress episode to learn from; an
   auto-inference layer would be unfalsifiable in the
   public-FWE setting.
3. **The audit consumer is a human reviewer.** A reviewer
   reading "this stress amplified that one" wants to
   know which reviewer signed the claim, on what
   evidence, under what review frame — not a
   classifier's confidence score.

v1.24 inherits all three reasons. By scoping `source_kind`
to the closed singleton `{"human"}` and `reasoning_mode`
to `{"human_authored"}` — and by rejecting any other
value at construction — v1.24 enforces "human-authored
only" at the storage layer; it does not become a soft
convention that future code might violate.

The v1.24.x layer therefore introduces **no automated
annotation entry point** at any milestone:

- v1.24.1 storage exposes `add_annotation(record)` only.
  There is no `auto_annotate(...)`, no
  `infer_interaction(...)`, no `classify_review_frame(...)`,
  no `propose_annotation(...)`.
- v1.24.2 readout exposes `build_manual_annotation_readout(kernel)`
  only. There is no helper that emits annotations from
  the readout's own observations.
- v1.24.3 export adds an optional descriptive section.
  There is no UI control that auto-fills annotation text
  from the loaded bundle.

A future v1.x milestone that wants to add an automated
annotation source — for example a synthetic-reviewer
fixture for inter-reviewer reproducibility tests — must
extend `SOURCE_KIND_LABELS` and `REASONING_MODE_LABELS`
under a fresh design pin. v1.24.x does not pre-commit to
such an extension.

---

## 7. Why annotations never mutate the world (binding)

v1.24 carries forward the v0/v1 *append-only ledger,
no source-of-truth book mutation* discipline shared by
every other storage book. Specifically:

- The v1.24.1 storage book emits **exactly one ledger
  record** per successful `add_annotation(...)` call —
  the `manual_annotation_recorded` event itself. No
  other ledger record fires.
- The book mutates **no other kernel book**. The v1.18.x
  scenario chain, the v1.21.x stress chain, the v1.16.x
  closed-loop attention path, the v1.14.x financing-path
  layer, the v1.13.x settlement substrate, the v1.12.x
  attention layer, the v1.10.x / v1.11.x reference-
  variable layer, and every other source-of-truth book
  are byte-identical pre / post call.
- The book is **append-only**. There is no
  `update_annotation(...)`, no `delete_annotation(...)`,
  no `replace_annotation(...)`, no
  `mark_superseded(...)`. A reviewer who wants to revise
  an annotation appends a new annotation citing the
  prior one (with `annotation_label =
  "reviewer_disagreement_placeholder"` if the disagreement
  is the point); the original stays in the book.
- The book is **empty by default on the kernel**. An
  empty book emits no ledger record, leaving every
  existing `living_world_digest` byte-identical at
  v1.24.x:
  - `quarterly_default` —
    `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`
  - `monthly_reference` —
    `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`
  - `scenario_monthly_reference_universe` test-fixture —
    `5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`
  - v1.20.4 CLI bundle —
    `ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`

If v1.24.1 turns out to require a new `RecordType`
(`MANUAL_ANNOTATION_RECORDED`), the digest preservation
is guaranteed by the empty-by-default rule: an unstamped
default kernel never adds an annotation, so the new
record type never fires under any existing fixture.

---

## 8. Why annotations never trigger actor behavior (binding)

The v1.x boundary catalogue (v1.18.0 actor-decision
tokens, v1.19.0 run-export tokens, v1.21.0a stress tokens,
v1.22.0 export-side tokens) lists every term the
substrate forbids on the public-v1 surface. v1.24 does
**not** loosen any of these. Specifically:

- No annotation may carry a field, label, or value that
  matches a v1.18.0 actor-decision token (`firm_decision`,
  `investor_action`, `bank_approval`, `trading_decision`,
  `optimal_capital_structure`, `buy`, `sell`, `order`,
  `trade`, `execution`).
- No annotation may carry a field, label, or value that
  matches a v1.19.0 run-export token (`predicted_path`,
  `forecast_index`, `investment_recommendation`,
  `price_prediction`, `real_price_series`,
  `actual_price`, `quoted_price`, `last_trade`, `nav`,
  `index_value`, `benchmark_value`, `valuation_target`).
- No annotation may carry a field, label, or value that
  matches a v1.21.0a stress token (`stress_magnitude`,
  `stress_probability_weight`, `aggregate_*`,
  `combined_*`, `net_*`, `composite_*`, `dominant_*`,
  `predicted_stress_effect`, `interaction_label`,
  `composition_label`, `amplify`, `dampen`, `offset`,
  `coexist`).
- No annotation may carry a field, label, or value that
  matches a v1.22.0 export-side token (`impact`,
  `outcome`, `risk_score`, `amplification`, `dampening`,
  `offset_effect`, `dominant_stress`, `net_pressure`,
  `composite_risk`, `forecast`, `expected_response`,
  `prediction`, `recommendation`).

Mechanically, the v1.24.1 storage layer reuses the
v1.23.1 canonical
:data:`world.forbidden_tokens.FORBIDDEN_STRESS_PROGRAM_FIELD_NAMES`
+ a v1.24.0 manual-annotation delta (containing the
v1.24-specific anti-claim tokens that should also be
forbidden, e.g. `auto_annotation`, `auto_inference`,
`automatic_review`). The dataclass field-name guard runs
at construction time; payload-key + metadata-key + label
+ optional `note_text` scans run at construction time.

Because the storage layer rejects every forbidden token
at construction, no annotation can ever propagate a
forbidden token into a downstream consumer (the v1.24.2
readout, the v1.24.3 export, the v1.24.3 UI panel).

---

## 9. Why annotations are not causal proof (binding)

Manual annotations are **observations**, not **claims**.
An annotation labelled `uncited_stress_candidate` says
"the reviewer noticed that this stress step's citation
trail looks shorter than expected"; it does **not** say
"this stress step caused that downstream record to fail
to cite back". Four design choices enforce this:

1. **No causal-fields vocabulary.** v1.24 exposes no
   `causal_effect` / `impact_score` / `risk_score` /
   `forecast` / `prediction` / `expected_return` /
   `target_price` annotation field, label, or value.
   The forbidden list is binding (§8).
2. **No magnitude / probability.** The v1.21.0a
   "labels-not-numbers" discipline applies. An
   annotation has no numeric "strength", "confidence",
   or "weight" field. The reviewer-role closed set is
   the only authority signal.
3. **Multiset semantics.** Multiple annotations may
   attach to the same record. The v1.24.2 readout
   surfaces `annotation_label_counts` — a multiset of
   label occurrences — but **never** a causal
   reduction. The reviewer reads the counts; the system
   does not infer from them.
4. **Reviewer-disagreement placeholder.** The
   `reviewer_disagreement_placeholder` annotation label
   exists precisely so two reviewers can disagree
   without the system treating their disagreement as a
   "wrong" annotation. Both stay in the book; the
   system records the disagreement, doesn't resolve it.

A reader of the audit object can look at the annotation
multiset and see *what reviewers said*. They cannot read
*what the world is*.

---

## 10. Why annotations are not stress interaction inference (binding)

This is a re-pin of the v1.21.0a *Deferred:
StressInteractionRule* boundary, scoped to the manual-
annotation surface:

- **No `amplify` / `dampen` / `offset` / `coexist`
  annotation label.** These four tokens are
  hard-forbidden in `ANNOTATION_LABELS`. Even a
  human-authored attempt to label two stress programs as
  "amplify" is rejected at construction time.
- **No `interaction_label` / `composition_label` /
  `output_context_label` annotation field.** These three
  tokens are hard-forbidden in field names.
- **No `aggregate_*` / `combined_*` / `net_*` /
  `dominant_*` / `composite_*` annotation field, label,
  or value.** Hard-forbidden across the surface.
- **No multi-stress reduction.** An annotation may cite
  multiple stress program applications; the v1.24.2
  readout will surface that the same annotation cites
  multiple program-application ids. But no helper at any
  v1.24.x milestone reduces multiple stress program
  applications into a single "combined stress" label.

If a reviewer wants to express "I think these two stress
programs share a review frame", the legal annotation is
`same_review_frame` cited against both program-application
ids. The reviewer's observation is captured; no
interaction-strength claim is encoded.

The v1.24 surface is the *audit overlay* on the citation
graph; it does not extend the stress chain itself. The
v1.21.x chain remains read-only with respect to v1.24.x.

---

## 11. Proposed `ManualAnnotationRecord` shape (design level)

The dataclass shape below is the v1.24.0 design pin.
v1.24.1 implementation must match this shape exactly; any
field rename, addition, or removal requires a fresh
design pin (a v1.24.0a or later correction).

```python
@dataclass(frozen=True)
class ManualAnnotationRecord:
    """Immutable, append-only manual annotation over an
    existing citation-graph record id."""

    annotation_id: str
    annotation_scope_label: str
    annotation_label: str
    cited_record_ids: tuple[str, ...]
    source_kind: str = "human"
    reasoning_mode: str = "human_authored"
    reviewer_role_label: str = "unknown"
    case_study_id: str | None = None
    created_for_record_id: str | None = None
    note_text: str | None = None
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)
```

Field semantics (binding):

- `annotation_id` — stable id, unique within
  `ManualAnnotationBook`.
- `annotation_scope_label` — closed-set string, member
  of `ANNOTATION_SCOPE_LABELS` (§13.1).
- `annotation_label` — closed-set string, member of
  `ANNOTATION_LABELS` (§13.2). Forbidden tokens
  (`amplify` / `dampen` / `offset` / `coexist` /
  interaction-label vocabulary) are **not** in this set.
- `cited_record_ids` — non-empty tuple of plain-id
  citations. The book does not dereference these; the
  v1.24.2 readout surfaces unresolved citations
  separately.
- `source_kind` — closed-set singleton `"human"` at
  v1.24.x. Construction rejects any other value.
- `reasoning_mode` — closed-set singleton
  `"human_authored"` at v1.24.x. Construction rejects
  any other value.
- `reviewer_role_label` — closed-set string, member of
  `REVIEWER_ROLE_LABELS` (§13.3). Defaults to
  `"unknown"` so a reviewer who declines to self-
  identify can still annotate.
- `case_study_id` — optional plain-id reference to a
  v1.23.3 case-study report.
- `created_for_record_id` — optional plain-id reference
  to a single primary record the annotation was created
  for (one of the `cited_record_ids`).
- `note_text` — optional human-readable string.
  **Descriptive only; never source-of-truth.** Scanned
  at construction for forbidden tokens; if any
  v1.18.0 / v1.19.0 / v1.21.0a / v1.22.0 / v1.24.0
  forbidden token appears as a whole word
  (case-insensitive), construction raises.
- `boundary_flags` — small mapping defaulted to the
  v1.24 anti-claim set (§14).
- `metadata` — opaque mapping scanned for forbidden
  keys.

### 11.1 Required-field discipline

- `annotation_id`, `annotation_scope_label`,
  `annotation_label`, `cited_record_ids`,
  `source_kind`, `reasoning_mode` are required (must be
  non-empty).
- `cited_record_ids` must contain at least one plain-id;
  the empty tuple is rejected.
- `case_study_id`, `created_for_record_id`, `note_text`
  are optional and may be `None`.
- All optional plain-id fields, when present, must be
  non-empty strings.

### 11.2 Anti-fields (forbidden field names — binding)

The dataclass field set must NOT contain any of the
following — even via a future rename:

- v1.18.0 actor-decision tokens (full list in
  `world/forbidden_tokens.py:FORBIDDEN_TOKENS_BASE`);
- v1.19.0 run-export tokens (full list in
  `FORBIDDEN_TOKENS_V1_19_0_RUN_EXPORT_DELTA`);
- v1.21.0a stress tokens (full list in
  `FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA`);
- v1.22.0 export-side tokens (full list in
  `FORBIDDEN_TOKENS_V1_22_0_EXPORT_DELTA`);
- the v1.24.0 manual-annotation delta (this design pin):
  - `auto_annotation`
  - `auto_inference`
  - `automatic_review`
  - `llm_annotation`
  - `inferred_interaction`
  - `interaction_engine_output`
  - `causal_effect`
  - `causal_proof`

The runtime `world.forbidden_tokens.FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES`
composed set lands at v1.24.1 (per the v1.23.1 BASE +
delta + composed convention).

---

## 12. Proposed `ManualAnnotationBook` shape (design level)

```python
@dataclass
class ManualAnnotationBook:
    """Append-only storage for ManualAnnotationRecord."""

    ledger: Ledger | None = None
    clock: Clock | None = None
    _annotations: dict[str, ManualAnnotationRecord] = field(
        default_factory=dict
    )

    def add_annotation(
        self,
        annotation: ManualAnnotationRecord,
        *,
        simulation_date: Any = None,
    ) -> ManualAnnotationRecord:
        ...

    def get_annotation(
        self, annotation_id: str
    ) -> ManualAnnotationRecord:
        ...

    def list_annotations(
        self,
    ) -> tuple[ManualAnnotationRecord, ...]:
        ...

    def list_by_scope(
        self, annotation_scope_label: str
    ) -> tuple[ManualAnnotationRecord, ...]:
        ...

    def list_by_label(
        self, annotation_label: str
    ) -> tuple[ManualAnnotationRecord, ...]:
        ...

    def list_by_cited_record_id(
        self, cited_record_id: str
    ) -> tuple[ManualAnnotationRecord, ...]:
        ...

    def snapshot(self) -> dict[str, Any]:
        ...
```

Storage discipline (binding):

- One ledger record per successful
  `add_annotation(...)` call: a single
  `manual_annotation_recorded` event with the
  annotation's id as `object_id` and a payload
  carrying every dataclass field (modulo the optional
  `note_text` redaction discipline at v1.24.3 export).
- No ledger record on duplicate id (raises
  `DuplicateManualAnnotationError`).
- No mutation of any other source-of-truth book.
- No call to
  `world.stress_applications.apply_stress_program`.
- No call to
  `world.scenario_applications.apply_scenario_driver`.
- No automatic annotation helper. The book exposes
  `add_annotation(record)` only.

The kernel's `manual_annotations` field is wired with
`field(default_factory=ManualAnnotationBook)`; an empty
book emits no ledger record, leaving every existing
`living_world_digest` byte-identical.

---

## 13. Closed-set vocabularies (binding for v1.24.0 design)

### 13.1 `ANNOTATION_SCOPE_LABELS`

Closed set; v1.24.1 implementation must match exactly:

```python
ANNOTATION_SCOPE_LABELS: frozenset[str] = frozenset({
    "stress_readout",
    "stress_program_application",
    "scenario_context_shift",
    "validation_report",
    "case_study",
    "citation_graph",
    "unknown",
})
```

The set is intentionally small. Adding a scope label at
a later v1.24.x sub-milestone requires a fresh design
pin.

### 13.2 `ANNOTATION_LABELS`

Closed set; v1.24.1 implementation must match exactly:

```python
ANNOTATION_LABELS: frozenset[str] = frozenset({
    "same_review_frame",
    "shared_context_surface",
    "uncited_stress_candidate",
    "partial_application_note",
    "citation_gap_note",
    "needs_followup_review",
    "reviewer_disagreement_placeholder",
    "unknown",
})
```

Note: the set explicitly does **not** contain `amplify`,
`dampen`, `offset`, `coexist`, `aggregate`, `composite`,
`net`, `dominant`, `causal_effect`, `impact_score`,
`risk_score`, `forecast`, `prediction`,
`recommendation`, or any v1.18.0 / v1.19.0 / v1.21.0a /
v1.22.0 forbidden token. v1.24.1 will additionally
assert at construction that no
`ANNOTATION_LABELS` element matches a forbidden token.

### 13.3 `REVIEWER_ROLE_LABELS`

Closed set; v1.24.1 implementation must match exactly:

```python
REVIEWER_ROLE_LABELS: frozenset[str] = frozenset({
    "lead_reviewer",
    "secondary_reviewer",
    "external_reviewer",
    "self_review",
    "unknown",
})
```

### 13.4 `SOURCE_KIND_LABELS`

Closed set; v1.24.x:

```python
SOURCE_KIND_LABELS: frozenset[str] = frozenset({"human"})
```

### 13.5 `REASONING_MODE_LABELS`

Closed set; v1.24.x:

```python
REASONING_MODE_LABELS: frozenset[str] = frozenset({
    "human_authored",
})
```

Both 13.4 and 13.5 are **singletons** at v1.24.x.
Expanding either requires a fresh design pin.

---

## 14. Default boundary flags (binding)

Every emitted `ManualAnnotationRecord` carries the
following default `boundary_flags` mapping. v1.24.1
construction merges caller-supplied flags on top, but
the defaults below are non-removable:

```python
_DEFAULT_BOUNDARY_FLAGS_TUPLE: tuple[tuple[str, bool], ...] = (
    # v1.18.0 boundary
    ("no_actor_decision", True),
    ("no_llm_execution", True),
    ("no_price_formation", True),
    ("no_trading", True),
    ("no_financing_execution", True),
    ("no_investment_advice", True),
    ("synthetic_only", True),
    # v1.21.0a additions (re-pinned at v1.24.0)
    ("no_aggregate_stress_result", True),
    ("no_interaction_inference", True),
    ("no_field_value_claim", True),
    ("no_field_magnitude_claim", True),
    # v1.24.0 additions (manual-annotation specific)
    ("human_authored_only", True),
    ("no_auto_annotation", True),
    ("no_causal_proof", True),
    ("descriptive_only", True),
)
```

A caller can set additional flags to `True`; a caller
**cannot** set any of the defaults to `False`.
Construction rejects any `False` override of a default
flag.

---

## 15. Read-only annotation readout (binding shape for v1.24.2)

`world/manual_annotation_readout.py` (NEW at v1.24.2)
will ship:

```python
@dataclass(frozen=True)
class ManualAnnotationReadout:
    """Immutable, read-only multiset projection over the
    kernel's ManualAnnotationBook."""

    readout_id: str
    annotation_ids: tuple[str, ...]
    cited_record_ids: tuple[str, ...]
    annotation_label_counts: Mapping[str, int]
    annotations_by_scope: Mapping[str, tuple[str, ...]]
    unresolved_cited_record_ids: tuple[str, ...]
    warnings: tuple[str, ...]
    metadata: Mapping[str, Any]
```

Read-only discipline (binding):

- Re-running the readout helper on the same kernel state
  produces a byte-identical readout (the v1.23.2 Cat 1
  determinism pin extends to v1.24.2 verbatim).
- `annotation_label_counts` is a multiset count of label
  occurrences. **It is not a score.** A reviewer reads
  it; the system does not infer from it.
- `unresolved_cited_record_ids` lists every
  `cited_record_id` whose plain-id prefix matches one of
  the v1.24.0 supported prefixes (§5) but which does not
  resolve to an extant kernel record. The Cat 3
  citation-completeness pin extends to v1.24.2.
- `warnings` carries human-readable warning strings (e.g.
  "5 annotations cite stale stress_program_application
  ids").
- The readout emits **no** ledger record (no new
  `RecordType` at v1.24.2).
- The readout does **not** mutate any kernel book.
- The readout does **not** call
  `apply_stress_program` / `apply_scenario_driver` /
  `add_annotation`.
- No automatic interpretation. The readout never reduces
  multiple annotations into a "combined" annotation,
  never infers an interaction, never produces an
  outcome / impact / forecast / recommendation.

### 15.1 Optional v1.23.2 validation hook

v1.24.2 may extend the v1.23.2 validation report (the
sub-dict consumed by the v1.23.3 case-study helper) with
two **optional** fields:

- `manual_annotation_count` — total number of annotations
  in the kernel's book at readout time (a non-negative
  int; never a score).
- `unresolved_annotation_citation_count` — total number
  of unresolved cited ids across all annotations.

Both fields default to `0` (or are absent) when no
annotation book is present. The hook is **non-mandatory**:
a kernel without a manual-annotation book continues to
satisfy the v1.23.2 Cat 1-4 pins exactly as before. The
v1.23.2 test suite stays green without modification.

---

## 16. Optional static UI display (design level for v1.24.3)

v1.24.3 may add a small read-only panel to an existing
sheet of `examples/ui/fwe_workbench_mockup.html`. The
v1.20.5 11-tab ↔ 11-sheet bijection is preserved at
v1.24.last; v1.24.3 introduces no new tab.

The candidate panel content (binding shape, not pinned
location at v1.24.0):

- `annotation_ids` count.
- `cited_record_ids` count.
- Top-N `annotation_label_counts` rendered as a label →
  count list.
- `unresolved_cited_record_ids` count + first 5 ids.
- `warnings` count + first warning text.
- `note_text` rendered **only** when forbidden-token
  scanned and HTML-escaped via `textContent` (never
  `innerHTML`); the panel does not show free-form
  reviewer prose by default.

The panel does not auto-fill from the loaded bundle,
does not invoke any client-side classifier, does not
fetch / XHR, does not write to the file system, and
does not change the active sheet on click.

If v1.24.3 prefers export-only (no UI), the design pin
permits skipping the UI panel entirely; the design only
reserves *space* for it.

---

## 17. Forbidden tokens (binding)

The v1.24.0 forbidden-token list extends the v1.23.1
canonical composition with v1.24-specific tokens. The
combined set is binding for v1.24.x.

**Inherited from v1.23.1 canonical composition**
(verbatim, by reference):

- v1.18.0 actor-decision tokens.
- v1.19.0 run-export tokens.
- v1.19.3 real-indicator tokens.
- v1.20.0 real-issuer / licensed-taxonomy tokens.
- v1.21.0a stress / aggregate / interaction tokens.
- v1.22.0 export-side outcome / impact tokens.

**v1.24.0 manual-annotation delta** (new at this design
pin):

```python
FORBIDDEN_TOKENS_V1_24_0_MANUAL_ANNOTATION_DELTA: frozenset[str] = (
    frozenset({
        "auto_annotation",
        "auto_inference",
        "automatic_review",
        "automatic_annotation",
        "llm_annotation",
        "llm_authored",
        "inferred_interaction",
        "interaction_engine_output",
        "interaction_engine_label",
        "causal_effect",
        "causal_proof",
        "impact_score",
        "actor_decision",
    })
)
```

The composed
`FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES` set will be:

```python
FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES: frozenset[str] = (
    FORBIDDEN_TOKENS_BASE
    | FORBIDDEN_TOKENS_V1_19_0_RUN_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_19_3_REAL_INDICATOR_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_REAL_ISSUER_DELTA
    | FORBIDDEN_TOKENS_V1_20_0_LICENSED_TAXONOMY_DELTA
    | FORBIDDEN_TOKENS_V1_21_0A_STRESS_DELTA
    | FORBIDDEN_TOKENS_V1_22_0_EXPORT_DELTA
    | FORBIDDEN_TOKENS_V1_24_0_MANUAL_ANNOTATION_DELTA
)
```

Scan discipline (carried verbatim from v1.21.x storage):

- Dataclass field names checked against the composed set
  at construction time.
- Payload keys (the ledger payload mapping) checked at
  construction time.
- Metadata keys checked at construction time.
- `note_text`, when present, scanned at construction
  time using whole-word boundary regex (case-
  insensitive). The scan applies to every token in the
  composed set.

---

## 18. Sub-milestone sequence (binding for v1.24.x)

The sequence is **strictly serial**. v1.24.1 must not
start until v1.24.0 docs are merged and CI is green.
v1.24.2 must not start until v1.24.1 storage is byte-
stable. v1.24.3 must not start until v1.24.2 readout is
in place. v1.24.last must not start until v1.24.3 is
shipped and CI is green.

| Sub-milestone | Surface | What it ships |
| ------------- | ------- | ------------- |
| **v1.24.0** | docs only | This design note. §133 in `world_model.md`. README §9 roadmap-row refresh. |
| v1.24.1 | runtime + tests | `ManualAnnotationRecord` + `ManualAnnotationBook` storage in [`world/manual_annotations.py`](../world/manual_annotations.py) (NEW). Exceptions: `DuplicateManualAnnotationError`, `UnknownManualAnnotationError`. Closed-set constants per §13. Default boundary flags per §14. Forbidden-token composition per §17 (extending `world/forbidden_tokens.py` with the v1.24.0 delta + composed set). Optional `MANUAL_ANNOTATION_RECORDED` `RecordType` if convention requires ledger storage. **No no-stress / no-annotation behavior change.** **No digest movement.** ~ +12 tests. |
| v1.24.2 | runtime + tests | `ManualAnnotationReadout` + `build_manual_annotation_readout(...)` in [`world/manual_annotation_readout.py`](../world/manual_annotation_readout.py) (NEW). Optional v1.23.2 validation hook (§15.1) — non-mandatory; existing validation tests pass without annotations. **No ledger emission.** **No mutation.** ~ +9 tests. |
| v1.24.3 | export + optional UI + tests | Optional `manual_annotation_readout` payload section on `RunExportBundle` (descriptive-only, empty-by-default, omitted from JSON when empty so v1.21.last digests stay byte-identical). Optional minimal "Manual annotations" panel in an existing sheet of `examples/ui/fwe_workbench_mockup.html` (no new tab; `textContent` only; no Python in browser). ~ +8 tests. |
| **v1.24.last** | docs only | Final freeze. §18 cardinality re-pin. Hard-boundary re-pin. Future optional candidates (v1.24.x.x corrections, v1.25 mandate / benchmark pressure). |

### 18.1 Cardinality (binding for v1.24.x)

- **0** new closed-set vocabularies *outside* the four
  pinned in §13 (scope, label, reviewer-role, source-kind /
  reasoning-mode).
- **1** new dataclass: `ManualAnnotationRecord`. Plus
  one storage book + one read-only readout dataclass; no
  other dataclasses.
- **0** or **1** new `RecordType` value:
  `MANUAL_ANNOTATION_RECORDED` if convention requires.
- **1** new ledger event type:
  `manual_annotation_recorded` (only emitted when an
  annotation is added; an empty book is silent).
- **0** new tabs in the static UI (v1.20.5 / v1.22.2 /
  v1.23.2a / v1.23.2b 11-tab ↔ 11-sheet bijection
  preserved).
- v1.24.1 expected test delta: **+ ~ 12** (per §19).
- v1.24.2 expected test delta: **+ ~ 9** (per §19).
- v1.24.3 expected test delta: **+ ~ 8** (per §19).
- v1.24.last final test count target: **~ 4976** (subject
  to exact pin at each sub-milestone).

### 18.2 Digest preservation (binding)

Every v1.24.x sub-milestone preserves every v1.21.last
canonical `living_world_digest` byte-identical:

- `quarterly_default` —
  `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`.
- `monthly_reference` —
  `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`.
- `scenario_monthly_reference_universe` test-fixture —
  `5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`.
- v1.20.4 CLI bundle —
  `ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`.

Digest preservation is guaranteed by the empty-by-default
rule: every existing fixture seeds an empty
`ManualAnnotationBook`; the empty book emits no ledger
record; therefore no fixture's record count changes.

---

## 19. Test plan summary (per sub-milestone)

### v1.24.1 — manual annotation storage tests
*(target: ~ 12 new tests)*

1. `test_manual_annotation_record_validates_required_fields`
2. `test_manual_annotation_rejects_auto_or_llm_source_kind`
3. `test_manual_annotation_rejects_forbidden_field_names`
4. `test_manual_annotation_rejects_forbidden_metadata_keys`
5. `test_manual_annotation_rejects_forbidden_note_text`
6. `test_manual_annotation_rejects_forbidden_label_value`
7. `test_manual_annotation_book_add_get_list_snapshot`
8. `test_duplicate_annotation_emits_no_extra_ledger_record`
9. `test_annotation_storage_does_not_mutate_source_of_truth_books`
10. `test_annotation_storage_does_not_call_apply_helpers`
11. `test_world_kernel_manual_annotations_empty_by_default`
12. `test_existing_digests_unchanged_with_empty_annotation_book`

### v1.24.2 — manual annotation readout / validation hook tests
*(target: ~ 9 new tests)*

1. `test_manual_annotation_readout_is_read_only`
2. `test_readout_counts_annotation_labels_without_scores`
3. `test_readout_surfaces_unresolved_cited_record_ids`
4. `test_readout_does_not_emit_ledger_records`
5. `test_readout_does_not_mutate_kernel`
6. `test_readout_does_not_infer_interactions`
7. `test_readout_rejects_forbidden_metadata`
8. `test_validation_hook_optional_and_backward_compatible`
9. `test_existing_validation_tests_still_pass_without_annotations`

### v1.24.3 — manual annotation export / optional UI tests
*(target: ~ 8 new tests)*

1. `test_export_omits_manual_annotations_when_absent`
2. `test_existing_no_annotation_bundle_digest_unchanged`
3. `test_export_includes_annotations_when_present`
4. `test_export_keys_are_descriptive_only`
5. `test_export_carries_no_forbidden_wording`
6. `test_ui_no_new_tab_added_at_v1_24_3`
7. `test_ui_uses_textcontent_only_for_loaded_values`
8. `test_existing_stress_readout_ui_still_renders`

### v1.24.0 / v1.24.last — what ships in tests

**Nothing.** v1.24.0 is docs-only. Test count holds at
4947 / 4947 at v1.24.0 (and again at v1.24.last after
the v1.24.1-3 increments).

---

## 20. Hard boundary (re-pinned at v1.24.0)

v1.24.0 inherits and re-pins the v1.23.last hard
boundary in full. The boundary at v1.24.0 is therefore
identical to v1.23.last:

**No real-world output.**
- No price formation. No market price. No order. No
  trade. No execution. No clearing. No settlement. No
  financing execution.
- No forecast / expected return / target price /
  recommendation / investment advice.
- No magnitude / probability / expected response.
- No firm decision / investor action / bank approval
  logic.

**No real-world input.**
- No real data ingestion. No real institutional
  identifiers. No licensed taxonomy dependency. No
  Japan calibration.

**No autonomous reasoning.**
- No LLM execution at runtime.
- No LLM prose accepted as source-of-truth.
- No interaction auto-inference.
- No aggregate / combined / net / dominant / composite
  stress output.
- v1.24.x adds: **no auto-annotation, no automatic
  annotation helper, no LLM-authored annotation in
  public v1.x.**

**No source-of-truth book mutation.**
- v1.24.x adds one storage book + one read-only readout
  + one optional export section + one optional UI
  panel. No v1.24.x helper mutates any pre-existing
  kernel book; pre-existing book snapshots remain
  byte-identical pre / post any v1.24.x helper call
  (the only new mutation is the
  `manual_annotation_recorded` ledger event itself,
  fired exactly once per `add_annotation(...)` call).

**No backend in the UI.**
- v1.24.3 may touch the static UI mockup; the
  v1.20.5 / v1.22.2 / v1.23.2a / v1.23.2b loader
  discipline is preserved. No new tab. No new sheet.
  No backend / fetch / XHR / file-system write.

**No digest movement.**
- v1.24.x preserves every v1.21.last canonical
  living-world digest byte-identical at every
  sub-milestone.

---

## 21. Read-in order (for a v1.24 reviewer)

1. [`v1_23_substrate_hardening_validation_foundation.md`](v1_23_substrate_hardening_validation_foundation.md)
   §12 "v1.23.last freeze" — the v1.23.last hard
   boundary v1.24 inherits.
2. This document — the v1.24.0 design pin.
3. [`world_model.md`](world_model.md) §133 — the
   constitutional position.
4. [`research_note_002_validating_stress_citation_graphs_without_price_prediction.md`](research_note_002_validating_stress_citation_graphs_without_price_prediction.md)
   §4.2 — the Cat 5 inter-reviewer reproducibility
   placeholder this layer materialises.
5. [`v1_21_stress_composition_layer.md`](v1_21_stress_composition_layer.md)
   *Deferred: StressInteractionRule* — the binding
   rationale for forbidding interaction-label
   inference.
6. [`case_study_001_attention_crowding_uncited_stress.md`](case_study_001_attention_crowding_uncited_stress.md)
   — one of the audit objects v1.24.x reviewers will
   annotate over.

---

## 22. Deliverables for v1.24.0 (this PR)

- This design note:
  `docs/v1_24_manual_annotation_layer.md`.
- New section §133 in `docs/world_model.md` — "v1.24
  Manual Annotation Layer (design pointer, **v1.24.0
  design-only**)".
- README §9 roadmap-row refresh — the v1.24 row
  updates from "Optional candidate" to "Design scoped
  at v1.24.0".

No runtime code change. No UI implementation. No new
tests. No new dataclass. No new ledger event. No new
label vocabulary. No digest movement. No record-count
change. No pytest-count change.

---

## 23. Cardinality summary (binding at v1.24.0)

- **0** new dataclasses at v1.24.0 (the
  `ManualAnnotationRecord` shape is *designed* here, not
  *implemented*; it lands at v1.24.1).
- **0** new ledger event types at v1.24.0.
- **0** new label vocabularies at v1.24.0 (the four
  closed sets in §13 are *designed* here; they land at
  v1.24.1).
- **0** new runtime modules at v1.24.0.
- **0** new tests at v1.24.0.
- **0** new UI regions at v1.24.0; **0** new tabs at
  any v1.24.x milestone.
- v1.24.1 expected test delta: **+ ~ 12**.
- v1.24.2 expected test delta: **+ ~ 9**.
- v1.24.3 expected test delta: **+ ~ 8**.
- v1.24.last final test count target: **~ 4976**.
- v1.21.last canonical digests: **byte-identical at
  every v1.24.x sub-milestone**.

The v1.24 sequence is scoped. Subsequent work that
touches the manual-annotation layer must explicitly
re-open scope under a new design pin (a v1.24.0a or
later correction); silent extension is forbidden.

---

## 24. v1.24.last freeze (docs-only)

*Final pin section for the v1.24 sequence. Closes the
manual-annotation interaction layer milestone as a docs-
only freeze; v1.24.last ships **no** new code, **no** new
tests, **no** new ledger event types, **no** new
RecordTypes, **no** new label vocabularies, **no** UI
changes, and **no** export-schema changes. Subsequent work
must re-open scope under a fresh design pin.*

### 24.1 Shipped sequence

| Sub-milestone | Surface | What it shipped |
| ------------- | ------- | --------------- |
| **v1.24.0** | docs only | This design pin (§§1-23), §133 in `world_model.md`, README §9 row. |
| v1.24.1 | runtime + tests | `ManualAnnotationRecord` + `ManualAnnotationBook` storage in [`world/manual_annotations.py`](../world/manual_annotations.py); closed-set vocabularies (scope / label / reviewer-role / source-kind=human / reasoning-mode=human_authored / status / visibility); 15 default boundary flags (non-removable); `MANUAL_ANNOTATION_RECORDED` ledger event type added to [`world/ledger.py`](../world/ledger.py); `manual_annotations: ManualAnnotationBook` field wired into `WorldKernel`; v1.24.0 manual-annotation forbidden-token delta + composed `FORBIDDEN_MANUAL_ANNOTATION_FIELD_NAMES` added to [`world/forbidden_tokens.py`](../world/forbidden_tokens.py). 16 pin tests. **No digest movement.** |
| v1.24.2 | runtime + tests | `ManualAnnotationReadout` + `build_manual_annotation_readout(...)` + `render_manual_annotation_readout_markdown(...)` + optional non-mandatory v1.23.2 validation hook `build_manual_annotation_validation_hook_summary(...)` in [`world/manual_annotation_readout.py`](../world/manual_annotation_readout.py). 13 pin tests. **No ledger emission. No mutation. No automatic interpretation. Counts are counts, not scores.** |
| v1.24.3 | export + UI + tests | Optional descriptive-only `manual_annotation_readout` payload section on `RunExportBundle` (cardinality 0 or 1; empty-by-default; omitted from JSON when empty so v1.21.last digests stay byte-identical) via [`world/manual_annotation_export.py`](../world/manual_annotation_export.py) + minimal "Manual annotations" panel inside the existing Universe sheet of [`examples/ui/fwe_workbench_mockup.html`](../examples/ui/fwe_workbench_mockup.html) (no new tab; `textContent` only). 15 pin tests. |
| **v1.24.last** | docs only | This freeze section. §133 final freeze pin in `world_model.md`. README §4 / §9 refresh. v1.24 sequence frozen. |

### 24.2 Pinned at v1.24.last

- `pytest -q`: **4991 / 4991 passing** (+44 vs v1.23.last
  4947; sub-milestone deltas: v1.24.1 +16, v1.24.2 +13,
  v1.24.3 +15).
- `ruff check .`: clean.
- `python -m compileall -q world spaces tests examples`:
  clean.
- All v1.21.last canonical living-world digests preserved
  byte-identical at every v1.24.x sub-milestone:
  - `quarterly_default` —
    `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`
  - `monthly_reference` —
    `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`
  - `scenario_monthly_reference_universe` test-fixture —
    `5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`
  - v1.20.4 CLI bundle —
    `ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`
- Source-of-truth book mutations from v1.24.x helpers:
  **0**.
- Ledger emissions from v1.24.x helpers (other than the
  one `MANUAL_ANNOTATION_RECORDED` event per
  `add_annotation` call, which fires only when a caller
  explicitly adds an annotation): **0**.
- New `RecordType` values: **1**
  (`MANUAL_ANNOTATION_RECORDED`).
- New dataclasses: **2**
  (`ManualAnnotationRecord`, `ManualAnnotationReadout`).
- New label vocabularies: **0** new closed sets *outside*
  the four pinned at v1.24.0 design (scope, label,
  reviewer-role, source-kind / reasoning-mode singletons).
- New tabs: **0** (v1.20.5 11-tab ↔ 11-sheet bijection
  preserved at v1.24.last).
- Export schema changes: **1 optional / omitted-when-empty
  field** (`manual_annotation_readout`) added to
  `RunExportBundle`. Pre-v1.24 bundles serialise
  byte-identically.

### 24.3 Hard boundary re-pinned at v1.24.last

The v1.24.last hard boundary is identical to the v1.23.last
boundary plus the v1.24-specific additions, re-pinned in
full:

**No real-world output.**
- No price formation. No market price. No order. No trade.
  No execution. No clearing. No settlement. No financing
  execution.
- No forecast / expected return / target price /
  recommendation / investment advice.
- No magnitude / probability / expected response.
- No firm decision. No investor action. No bank approval
  logic.

**No real-world input.**
- No real data ingestion. No real institutional
  identifiers. No licensed taxonomy dependency. No Japan
  calibration.

**No autonomous reasoning.**
- No LLM execution at runtime. No LLM prose accepted as
  source-of-truth.
- **No auto-annotation.** No helper, classifier, closed-
  set rule table, LLM, or any other automated layer may
  emit a `ManualAnnotationRecord`. The storage layer
  exposes `add_annotation(record)` only — there is no
  `auto_annotate(...)`, `infer_interaction(...)`,
  `classify_review_frame(...)`, or
  `propose_annotation(...)` helper at any v1.24.x
  sub-milestone.
- **`source_kind = "human"` only.** The closed singleton
  is enforced at storage construction time; "auto" /
  "llm" / any other value raises.
- **`reasoning_mode = "human_authored"` only.** Same
  closed-singleton discipline.
- No interaction auto-inference. No `amplify` / `dampen`
  / `offset` / `coexist` annotation label is allowed,
  even when authored by a human (the closed
  `ANNOTATION_LABELS` set explicitly excludes them).
- No aggregate / combined / net / dominant / composite
  stress output via the annotation surface.
- No causal proof. An annotation is a reviewer
  observation, not an assertion that one record caused
  another.

**No source-of-truth book mutation.**
- v1.24.x ships one storage book + one read-only readout
  + one optional export section + one optional UI panel.
  No v1.24.x helper mutates any pre-existing kernel
  book; pre-existing book snapshots remain byte-
  identical pre / post any v1.24.x helper call. The
  only new mutation is the
  `manual_annotation_recorded` ledger event itself,
  fired exactly once per `add_annotation(...)` call.

**No backend in the UI.**
- v1.24.3 added the "Manual annotations" panel inside
  the existing Universe sheet; the v1.20.5 / v1.22.2 /
  v1.23.2a / v1.23.2b loader discipline is preserved.
  No new tab. No new sheet. No backend / fetch / XHR /
  file-system write. `textContent` only for caller-
  supplied values.

**No digest movement.**
- Every v1.24.x sub-milestone preserved every v1.21.last
  canonical living-world digest byte-identical.

### 24.4 Closing statement

v1.24.last freezes the manual annotation interaction
layer as a **human-authored, append-only audit overlay**
on existing citation-graph records. The sequence:

1. Did not move any digest.
2. Added one `RecordType`
   (`MANUAL_ANNOTATION_RECORDED`) and two dataclasses
   (`ManualAnnotationRecord`, `ManualAnnotationReadout`)
   — all empty-by-default on the kernel.
3. Did not introduce any label vocabulary outside the
   four design-pinned closed sets (scope, label, reviewer-
   role, source-kind / reasoning-mode singletons).
4. Did not infer interactions, aggregate stresses, or
   produce any predictive metric.
5. Did not surface free-form reviewer prose
   (`note_text`) in the export or the UI; v1.24.3
   exposes only the multiset shape of the annotation
   book.
6. Materialised the v1.23.2 Cat 5 *inter-reviewer
   reproducibility* placeholder's runtime surface.

The v1.24 sequence is **frozen**. Subsequent work touching
the manual-annotation layer requires a fresh design pin.

### 24.5 Future optional candidates (NOT planned at v1.24.last)

| Future milestone | Description | Status |
| ---------------- | ----------- | ------ |
| v1.25 candidate | **Institutional Investor Mandate / Benchmark Pressure** — bounded synthetic mandate / benchmark / peer-pressure constraints on the v1.15.5 / v1.16.2 investor-intent layer. Decoupled from the v1.21 / v1.22 / v1.23 / v1.24 stress + audit + annotation surface. Not blocked by v1.24; advances on its own cadence. | Optional candidate. Not started. Requires a fresh design pin. |
| v2.x | **Japan public calibration boundary design** — design-only first; no data ingestion. Gated on data / license boundary review. | Optional candidate. Not started. |
| v3.x | **Proprietary Japan calibration** — not public; would live in a private repository and would preserve every public-FWE boundary. | Not started. Not public. |

The v1.25 candidate is the next likely milestone, but its
implementation requires a fresh design pin; v1.24.last
makes no commitment about when or whether v1.25 starts.
