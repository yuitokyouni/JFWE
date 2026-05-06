# Research Note 002 — Validating Stress Citation Graphs without Price Prediction

*Companion note to v1.23.2 (Validation Foundation milestone).
Explains the research meaning of v1.23.2 — why the validation
layer asks "is this readout trustworthy as an audit object?"
**without** asking "did the model predict the right number?"
— and what kind of validation object the v1.23.2 pin set
actually is.*

This note is a research statement, not a design document.
The binding design pin lives in
[`v1_23_substrate_hardening_validation_foundation.md`](v1_23_substrate_hardening_validation_foundation.md)
§4; the v1.21 research framing this note inherits lives in
[`research_note_001_stress_composition_without_outcome_inference.md`](research_note_001_stress_composition_without_outcome_inference.md).
This note is the layer *above* those: what v1.23.2 is *for*,
in the sense of the research question it is meant to support.

---

## 1. Problem

Most validation work in quantitative finance modeling jumps
directly to **predictive accuracy**: pick a held-out
historical period, run the model, compare its output to the
realised series, compute an error metric (RMSE, MAE,
log-likelihood, hit rate), and call the error the "validation
score."

Predictive-accuracy validation is the wrong frame for the FWE
v1.21 stress layer, for three reasons that compound (and that
mirror the three reasons predictive scenario comparison was
the wrong frame for v1.21 itself, per research note 001):

1. **There is no number to compare against.** The v1.21.3
   stress field readout is a *citation graph* — plain-id
   references to v1.18.2 application records, v1.18.2
   context-shift records, and pre-existing context records —
   plus a small number of closed-set label tuples preserved
   in emission order. The readout has no price, no P&L, no
   default probability, no expected return. There is no
   metric to RMSE against.
2. **A "right answer" presupposes the engine is making a
   prediction.** v1.21 explicitly does not predict. It
   records that a synthetic stress stimulus was applied and
   surfaces the citation graph the stimulus produced. There
   is no claim about what should happen in the real world;
   therefore there is nothing to be right or wrong about in
   the predictive sense.
3. **The audit consumer is a human reviewer, not a backtest
   harness.** A reviewer asks "is the audit object I am
   looking at well-formed, internally consistent, and fully
   cited?" — not "did the model match the historical
   record." A predictive-accuracy frame optimises for the
   second question and gives the reviewer nothing to read.

v1.23.2 declines all three of those defaults.

---

## 2. Core idea

v1.23.2 reframes validation as **"is this readout
trustworthy as an audit object?"** — six concrete questions
about the readout itself, not about its agreement with any
external series. Four of the questions are pinned at v1.23.2;
two are placeholders for v1.24+ work.

Concretely:

- **Determinism (Cat 1).** Same kernel state → byte-identical
  readout, byte-identical markdown summary, byte-identical
  v1.22.1 export entry. A reviewer can re-run the audit and
  get the same audit object. *Pinned at v1.23.2.*
- **Boundary preservation (Cat 2).** Every emitted readout
  satisfies the v1.21.0a + v1.22.0 forbidden-name boundary
  at every load-bearing surface (dataclass field set,
  metadata keys, markdown render, v1.22.1 export entry). No
  outcome / interaction / forecast / advice token leaks
  past the boundary. *Pinned at v1.23.2 against the v1.23.1
  canonical composition in `world.forbidden_tokens`.*
- **Citation completeness (Cat 3).** Every plain-id
  citation in the readout resolves to an actual record in
  the corresponding kernel book. A "dangling citation" — a
  cited id that does not match any extant record — is a
  regression class the existing pins do not catch. *Pinned
  at v1.23.2.*
- **Partial-application visibility (Cat 4).** When at least
  one stress step did not produce a v1.18.2 application
  record, the readout MUST surface every required
  visibility field (counts, step ids, reason labels,
  warnings) — and that visibility MUST propagate through
  both the v1.21.3 markdown summary and the v1.22.1 export
  entry. A regression that silently dropped the
  partial-application banner from either surface would let
  a reviewer mistake a partial application for a complete
  one. *Pinned at v1.23.2.*
- **Inter-reviewer reproducibility (Cat 5).** Two human
  reviewers reading the same readout + same fixture should
  reach the same audit conclusion. v1.23.2 ships the
  *format* placeholder only — a `tests/fixtures/inter_reviewer/`
  directory with a stub schema and a parseable example.
  *Placeholder at v1.23.2; runtime annotation layer is
  the v1.24 candidate.*
- **Null-model comparison (Cat 6).** The natural null model
  is a kernel with scenario drivers applied but no stress
  program. v1.23.2 pins that
  `build_stress_readout_export_section` returns an empty
  section for the null model and a non-empty section for
  the stressed model — both calls succeed. The diff format
  is deferred. *Placeholder at v1.23.2.*

The validation object is the **readout itself**, not a
prediction the readout makes about a real-world outcome.
Validation passes when the audit object is well-formed,
internally consistent, fully cited, and boundary-preserving;
it does not depend on any external series.

---

## 3. Why the placeholders are placeholders

Categories 5 and 6 are not pinned at v1.23.2 because they
require artifacts the v1.23.2 surface cannot produce:

- **Cat 5 (inter-reviewer)** requires a reviewer panel. No
  such panel exists in the public FWE; v1.23.2 ships the
  *format* so a future v1.x milestone (or an external
  research collaboration) can populate the directory with
  signed reviewer notes. The format pins the closed-set
  `reviewer_kind = {"human"}` and `reasoning_mode = {"human_authored"}`
  discipline; v1.23.2 explicitly forbids any
  classifier / closed-set rule table / LLM auto-population.
- **Cat 6 (null-model diff)** requires a defined diff format
  over citation graphs. The v1.23.2 design declines to
  invent that format ad hoc — a citation-graph diff is a
  research artifact in its own right, and v1.23.2 ships
  only the fixture pair that makes the diff *possible* at a
  later milestone.

Both placeholders are scaffolding: they exist so the next
milestone has a fixed surface to build against.

---

## 4. What this is **not**

v1.23.2 explicitly does **not** introduce:

- a real-world price / index / yield / spread series to
  validate against;
- a statistical test (t-test, KS test, goodness-of-fit,
  hypothesis testing) — those would imply the readout is a
  random variable, which it is not at v1.x;
- a "validation score" — the validation pins are
  binary-pass or binary-fail; there is no continuous
  validation metric the layer reports;
- a prediction error / forecast / expected-response /
  outcome metric of any kind;
- a comparison to a real-world institution, real-world
  stress episode, or real-world reviewer;
- a new dataclass, a new ledger event, or a new label
  vocabulary;
- a Japan calibration or LLM execution path.

The v1.23.2 hard boundary is identical to the v1.22.last
hard boundary, re-pinned at v1.23.0.

---

## 5. Why this matters

The FWE v1.21–v1.23.x sequence is research software that
explicitly refuses to predict prices. A reviewer asked to
trust the resulting audit object reasonably wants to know
"is the audit object trustworthy?" — and the conventional
predictive-accuracy answer ("the model RMSEs to X%
historical error") is unavailable.

v1.23.2 supplies a different answer: the audit object is
deterministic, boundary-preserving, fully-cited, and
visibility-preserving. A reviewer can re-run the audit and
verify byte-identity; a reviewer can confirm no outcome
token leaks past the boundary; a reviewer can confirm
every cited id resolves; a reviewer can confirm partial
applications are surfaced. None of these are predictions;
all of them are properties of the audit object.

That is the v1.23.2 contribution: validation as audit-object
property checking, not as predictive-accuracy scoring.

---

## 6. Companion documents

- `v1_23_substrate_hardening_validation_foundation.md` §4 —
  the binding design pin for the four pinnable categories +
  two placeholder categories.
- `research_note_001_stress_composition_without_outcome_inference.md`
  — the v1.21 research framing v1.23.2 inherits.
- `world_model.md` §132 — the constitutional position of
  v1.23.x.
- `v1_22_static_ui_stress_readout_reflection.md` — the
  v1.22 layer the v1.23.2 pins audit.
- `v1_21_stress_composition_layer.md` — the v1.21 stress
  layer the readout is built on top of.

---

## 7. Future work

The v1.24 candidate **manual_annotation interaction layer**
will consume the Cat 5 reviewer-note format. The v1.25
candidate **institutional investor mandate / benchmark
pressure** is decoupled from the v1.23 validation surface
and is not blocked by the placeholders.

A future milestone may design the citation-graph diff format
that elevates Cat 6 from placeholder to pinnable. v1.23.2
makes no commitment about when or how that happens; the
fixture pair shipped at v1.23.2 is the substrate that
diff design will build on.
