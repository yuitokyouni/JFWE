# v1.10 Universal Engagement and Strategic Response — Design

> **Status:** v1.10.0 design / consolidation milestone. Docs-only.
> No runtime code changes in v1.10.0.
> **Layer:** FWE Core (public, jurisdiction-neutral).
> **Depends on:** v1.9.last public prototype freeze.
> **Blocks:** v1.10.1 (stewardship theme signal) and every concrete
> engagement / response milestone after it. Until v1.10.0 lands,
> the project lacks a written direction-of-travel for how investor
> engagement, portfolio-company dialogue, escalation, and corporate
> strategic response are represented in FWE.

## TL;DR — the core principle

> **Engagement is not the same as decision. Dialogue is not the same
> as outcome. v1.10 names the engagement / response layer as a
> *first-class*, *signal-only* extension of the v1.9 review stack —
> never as trading, lending, voting, or investment recommendation.**

v1.9 closed the diagnostic loop: firms post quarterly reports;
investors and banks form pressure assessments, valuation opinions,
and credit-review notes; the ledger captures every step. That loop
is **observation-and-assessment-only**. It does not yet name the
*relational* surface where investors raise stewardship themes with
firms, where firms respond, where dialogues are recorded, where an
investor escalates a concern, and where a firm sketches a strategic
response candidate.

v1.10 adds that surface. It does so in a way that:

- stays jurisdiction-neutral (no country-specific institutions, no
  domestic dataset names, no jurisdiction-specific thresholds);
- stays signal-only (no trading, no price formation, no lending
  decisions, no voting execution, no portfolio mutation);
- stays explainability-first (every new record fits the v1.8 / v1.9
  ledger discipline, with a `MechanismAdapter`-shaped surface where
  the work is non-trivial);
- defers meta-abstractions until at least two concrete
  specializations exist in public FWE.

This document is **design-only**. No `world/` or `spaces/` code is
committed in v1.10.0. The deliverable is: vocabulary, candidate FWE
object types, the existing v1.8 / v1.9 hooks each concept attaches
to, the explicit no-behavior boundary, what stays out of scope, and
the milestone sequence.

## Position in the version sequence

| Milestone | Scope | Status |
| --- | --- | --- |
| v1.9.last Public Prototype Freeze | Docs-only (§69 of `world_model.md`). | Shipped |
| v1.10.0 Universal Engagement / Strategic Response Consolidation | Docs-only — this document + `world_model.md` §70 + boundary updates. | Shipped |
| **v1.10.1 Stewardship theme signal** | **Code. `StewardshipThemeRecord` + `StewardshipBook` + ledger `STEWARDSHIP_THEME_ADDED` + kernel wiring + 58 tests.** | **Shipped** |
| v1.10.2 Portfolio-company dialogue record | Code. Concrete dialogue book + record shape. | Planned |
| v1.10.3 Investor escalation candidate + corporate strategic response candidate | Code. Two concrete `candidate`-shaped records. | Planned |
| v1.10.4 Optional industry demand context | Code. Optional context-signal shape. | Optional |
| v1.10.5 Living-world integration | Code. Wires v1.10.1–v1.10.3 into the multi-period sweep. | Planned |
| v1.10.last Freeze | Docs-only. Public engagement layer freeze. | Planned |
| v2.0 Japan public-data calibration design gate | — | Not started |

v1.10.0 itself ships **no behavior, no test additions, no new ledger
record types, no new books, and no new mechanisms.** The freeze
language of v1.9.last continues to hold throughout v1.10.0. The
test count is unchanged at `1626 / 1626`.

## What v1.10 extends

v1.9 took the engine from "diagnostic pressure / valuation / credit
review" through:

- corporate quarterly reporting (§49)
- firm operating pressure assessment (§64)
- reference valuation refresh lite (§65)
- bank credit review lite (§67)
- review routines (§55)
- the multi-period living reference world demo (§59)

v1.10 extends that into the **engagement and response** flow:

- an investor (or other steward) raises a stewardship theme signal;
- a portfolio-company dialogue is recorded;
- when a dialogue does not resolve, an investor escalation candidate
  is named;
- a corporate strategic response candidate is named on the firm side;
- optionally, an industry-level demand condition signal is recorded
  as context.

Everything in this list is a **signal** or a **candidate** — never an
action, never a contract change, never a price move, never a portfolio
trade.

## Hard boundary — what v1.10 must never do

v1.10 (every milestone, including v1.10.last) must not:

- introduce country-specific institution names;
- introduce source / report names from any private design probe;
- introduce jurisdiction-specific thresholds, regimes, or tiers;
- introduce domestic dataset names or paid-data references;
- introduce behavior probabilities derived from non-public reports;
- introduce bank-specific or sector-specific strategy assumptions;
- introduce forecast values as parameters;
- import paid / NDA / proprietary content;
- record confidential dialogue contents (verbatim or paraphrased);
- implement trading, price formation, lending decisions, corporate
  action execution, or voting execution;
- emit investment-recommendation language (direct or indirect) in
  code, docs, schemas, or demo output;
- consume real-world calibration data of any provenance.

These prohibitions are enforced at every v1.10 milestone, not only at
the v1.10.0 design gate. The `world/experiment.py::_FORBIDDEN_TOKENS`
forbidden-token scan continues to gate every commit.

## Meta-abstraction rule

Two meta-abstractions surfaced during the private design probe:

- `actor_business_model_transition_pressure` — a generalization of
  pressure on any actor's business model, abstracted across firms,
  banks, and investors;
- `actor_strategic_response_candidate` — a generalization of a
  candidate strategic response from any actor, abstracted across
  corporates, banks, and investors.

Both are explicitly **deferred** in v1.10.

The rule is: do not implement a meta-abstraction in public FWE
**until at least two concrete specializations of that abstraction
have been implemented and have stabilized.** The reason is that
generalizing prematurely tends to encode the first specialization's
shape into the meta layer and force every later concrete to bend to
fit. v1.10's concrete primitives are:

- `stewardship_theme_signal` (an investor-side engagement signal);
- `portfolio_company_dialogue_record` (a relational record);
- `investor_escalation_candidate` (an investor-side candidate);
- `corporate_strategic_response_candidate` (a corporate-side
  candidate);
- (optional) `industry_demand_condition_signal` (a context signal).

After v1.10.last lands and at least two concrete *response candidate*
specializations are stable in public FWE (e.g., the corporate one
plus a future bank-side or investor-side one), the meta-abstraction
gate can be reopened. Until then, v1.10 implements the concrete
primitives only.

## Selected concepts

The five selected concepts (four required + one optional) are
specified below. Each follows the same template:

- **purpose** — what the concept names in the world;
- **generic inputs** — what the concept reads;
- **generic outputs** — what the concept produces;
- **candidate FWE object type** — the v1.8 / v1.9 record family it
  fits into;
- **existing FWE hook** — the v1.8 / v1.9 plumbing it attaches to;
- **no-behavior boundary** — what the concept is explicitly *not*;
- **out of scope** — what must not enter v1.10's implementation;
- **future v2 mapping slot** — where the v2 calibration layer can
  later attach jurisdiction-specific naming, thresholds, and data,
  *without* changing the public shape.

### 1. `stewardship_theme_signal`

**Purpose.** Names a *theme* an investor (or other steward) is
prepared to raise across portfolio companies — for example, capital
allocation discipline, governance structure, disclosure quality,
operational efficiency, sustainability practice. The signal records
that the theme is *active* for that investor in that period; it does
not record any specific company conversation.

**Generic inputs.**
- the investor / steward identifier (an existing FWE agent);
- a synthetic theme tag (controlled vocabulary; jurisdiction-neutral);
- the period the signal is active in;
- an optional intensity level expressed as a small enumerated set
  (e.g., `low` / `medium` / `high`), illustrative only — never a
  calibrated probability.

**Generic outputs.**
- one append-only signal record per `(investor, theme, period)`;
- read-only book listing all active theme signals.

**Candidate FWE object type.** A new `signal`-shaped record in the
investor / information family, parallel to existing v1.8.x signal
emissions. Not a `Contract`, not a `Price`, not an `Ownership`
change.

**Existing FWE hook.** `InteractionBook` (§45), `RoutineBook` (§46),
and the v1.8.x `SignalBook` / information layer. v1.10.1 will most
likely shape the signal as an `InformationSignal` subtype emitted by
an investor review routine, with the routine wired to the v1.8.x
attention machinery so a heterogeneous-attention demo continues to
work.

**No-behavior boundary.** A theme signal does not *act*. It does
not vote. It does not trade. It does not change ownership. It does
not change contract terms. It does not allocate capital. It is a
named statement of an active theme, nothing more.

**Out of scope.** Per-jurisdiction stewardship code names, real
institutional steward names, paid-data theme taxonomies, calibrated
intensity probabilities, attribution to any real investor.

**Future v2 mapping slot.** v2 (Japan public calibration) may
attach a jurisdiction-specific theme taxonomy and synthetic
investor populations on top of the public shape. The public record
shape itself does not change.

### 2. `portfolio_company_dialogue_record`

**Purpose.** Names a *recorded engagement contact* between an
investor / steward and a portfolio company in a given period — that a
dialogue happened, what generic theme it concerned, and what its
generic outcome class was (e.g., `acknowledged` / `partial_response` /
`no_response`). It does not record verbatim or paraphrased dialogue
contents.

**Generic inputs.**
- the investor / steward identifier;
- the firm identifier (an existing FWE agent);
- the period the dialogue was held in;
- a reference to a `stewardship_theme_signal`, when one applies;
- a generic outcome class (controlled vocabulary;
  jurisdiction-neutral).

**Generic outputs.**
- one append-only dialogue record per
  `(investor, firm, theme, period)`;
- read-only book listing all dialogue records.

**Candidate FWE object type.** A new dialogue-record family in the
relational layer, sibling to the v1.5 `RelationshipCapital` book.
Not an `InstitutionalActionRecord`. Not a `Contract`. Not a
`ValuationRecord`.

**Existing FWE hook.** `RelationshipCapitalBook` (§40),
`InteractionBook` (§45), `RoutineBook` (§46). v1.10.2 will shape the
dialogue record as an entry in a new dialogue book, fired from a
review routine, and use the v1.8.x interaction topology to constrain
which `(investor, firm)` pairs may appear.

**No-behavior boundary.** A dialogue record is **not** the dialogue.
It carries metadata only — that a contact happened in this period,
under this theme, with this generic outcome class. Verbatim or
paraphrased contents are restricted artifacts under
`docs/public_private_boundary.md` and never appear in public FWE.

**Out of scope.** Verbatim text, paraphrased text, attendee lists,
named-institution dialogues, paid-data engagement disclosures,
calibrated outcome probabilities, identifiability of any real
relationship.

**Future v2 mapping slot.** v2 may attach synthetic populations of
investors and firms with jurisdiction-specific theme priors on top
of the public shape. v3 (proprietary) is the only layer in which
private dialogue contents could ever appear, and only inside the
restricted-redistribution bucket — never in this repository.

### 3. `investor_escalation_candidate`

**Purpose.** Names that, given a sequence of dialogue records that
did not resolve, an investor *could* escalate. The candidate is a
named option, **not** an executed escalation. It does not vote, does
not file, does not exit. It records that the investor has reached a
state where escalation is on the table.

**Generic inputs.**
- the investor / steward identifier;
- the firm identifier;
- the relevant theme;
- a reference to the prior dialogue record(s);
- the period in which the candidate is named;
- a generic candidate kind (controlled vocabulary; jurisdiction-
  neutral — for example `private_letter` / `public_statement` /
  `nominate_candidate` / `support_resolution` — used as illustrative
  enumerations only, with no calibrated probabilities).

**Generic outputs.**
- one append-only candidate record per `(investor, firm, theme,
  period, candidate_kind)`;
- read-only book listing all escalation candidates.

**Candidate FWE object type.** A `candidate`-shaped record, sibling
to v1.9.5's valuation-opinion records and v1.9.7's credit-review
notes. Diagnostic, not action. Not an `InstitutionalActionRecord`.

**Existing FWE hook.** `MechanismAdapter` (v1.9.3 contract).
v1.10.3 will most likely shape the escalation candidate as the
output of an escalation `MechanismAdapter` whose `apply(request)`
reads only the request's evidence (dialogue records, theme signals)
and returns a `MechanismOutputBundle`. No kernel parameter, no book
mutation outside the candidate book itself, full v1.9.3 hardening.

**No-behavior boundary.** A candidate is **not** an action. The
investor has not voted; has not filed; has not exited. The candidate
is the named option, scoped to the period, with no calibrated
probability of being taken.

**Out of scope.** Voting execution, AGM / EGM filings, real proxy
data, real escalation outcomes, named-institution escalation
histories, calibrated candidate-selection probabilities,
investment-recommendation language.

**Future v2 mapping slot.** v2 may attach synthetic populations of
investors with jurisdiction-specific candidate-kind taxonomies on
top of the public shape. The public record shape does not change.

### 4. `corporate_strategic_response_candidate`

**Purpose.** Names a strategic response a portfolio company *could*
take in response to one or more stewardship themes, dialogues, or
escalation candidates. The candidate is a named option, **not** an
executed corporate action. It does not buy back, does not divest,
does not restructure, does not change the board.

**Generic inputs.**
- the firm identifier;
- the relevant theme(s);
- references to prior dialogue records and escalation candidates,
  when applicable;
- the period in which the candidate is named;
- a generic response kind (controlled vocabulary; jurisdiction-
  neutral — for example `capital_allocation_review` /
  `governance_review` / `disclosure_review` /
  `operational_review` — used as illustrative enumerations only,
  with no calibrated probabilities).

**Generic outputs.**
- one append-only candidate record per `(firm, theme, period,
  response_kind)`;
- read-only book listing all response candidates.

**Candidate FWE object type.** A `candidate`-shaped record on the
corporate side, sibling to `investor_escalation_candidate`. Not an
`InstitutionalActionRecord`. Not a `Contract`. Not a corporate
action execution.

**Existing FWE hook.** `MechanismAdapter` (v1.9.3 contract). v1.10.3
will shape this candidate as the output of a corporate-response
`MechanismAdapter` symmetric to the escalation adapter, reading only
the request's evidence and returning a `MechanismOutputBundle`.

**No-behavior boundary.** A response candidate is **not** a
corporate action. No share repurchase, no dividend change, no
divestment, no merger, no governance change occurs. The firm has
not done anything; the candidate is the named option for the
period.

**Out of scope.** Corporate-action execution, real corporate-action
data, named-institution response histories, calibrated
response-selection probabilities, real disclosure documents,
investment-recommendation language.

**Future v2 mapping slot.** v2 may attach synthetic firm populations
with jurisdiction-specific response-kind taxonomies on top of the
public shape. The public record shape does not change.

### 5. `industry_demand_condition_signal` (optional)

**Purpose.** Names a generic *industry-level demand condition* (for
example `weakening` / `stable` / `strengthening`) as a context signal
that may inform a firm's pressure assessment, an investor's
stewardship theme, or a bank's credit-review note. The signal is
explicitly *contextual* — it does not drive a number on any balance
sheet, does not move a price, does not change a contract.

**Generic inputs.**
- a synthetic industry tag (controlled vocabulary; jurisdiction-
  neutral);
- a generic condition class;
- the period the signal applies to.

**Generic outputs.**
- one append-only signal record per `(industry, period)`;
- read-only book listing all industry demand-condition signals.

**Candidate FWE object type.** A `signal`-shaped record, sibling to
v1.8.x information signals.

**Existing FWE hook.** `SignalBook` / information layer (§26 area)
and the v1.8.x attention machinery, mirroring how v1.8.x already
handles macro-style signals.

**No-behavior boundary.** A demand-condition signal does not move
prices, does not change valuations except indirectly (and only when
a downstream `MechanismAdapter` is wired to read it), and does not
itself constitute a forecast. It is a named context state per
industry, per period.

**Out of scope.** Real industry data, paid-data industry feeds,
named-firm demand attribution, calibrated demand probabilities,
forecast values, investment-recommendation language.

**Future v2 mapping slot.** v2 may attach jurisdiction-specific
industry taxonomies and (later) optional public-data calibration on
top of the public shape, subject to per-source license review.

## Why these five concepts and not others

The private design probe explored a longer list. The public-FWE cut
keeps only those that:

1. fit the v1.8 / v1.9 ledger and book discipline without inventing
   a new persistence pattern;
2. are *signals* or *candidates* — never executions, never contract
   changes, never trades, never votes;
3. are jurisdiction-neutral by name and content;
4. either have a clear `MechanismAdapter` shape (escalation candidate,
   corporate response candidate) or a clear `SignalBook` /
   `RelationshipCapitalBook` shape (theme signal, dialogue record,
   industry demand condition);
5. cleanly defer to v2 for any jurisdiction-specific calibration.

Concepts that did not pass this cut — explicitly the two
meta-abstractions named above, and any concept that required
naming a real institution, a real source, a real threshold, or a
calibrated probability — are not in v1.10.

## How v1.10 fits the v1.9.last freeze

v1.9.last froze:

- the CLI surface (three reproducible entry points);
- the default fixture (3 firms × 2 investors × 2 banks × 4 periods);
- the per-period flow (corporate report → pressure → attention →
  valuation refresh → credit review → review routines);
- the reproducibility surface (Markdown report + JSON manifest +
  SHA-256 digest);
- the performance boundary (per-period 37 records, per-run
  `[148, 180]` total);
- the test surface (`1626 / 1626`);
- the scope language (no forecast, no investment advice, no price
  formation, no trading, no lending decisions, no Japan
  calibration, no real data, no scenarios, no production-scale
  traversal, no native rewrite, no web UI).

v1.10 *extends* the per-period flow only at later milestones
(v1.10.1+, all under their own freeze gates) and never relaxes any
of v1.9.last's anti-claims. v1.10.0 itself is **docs-only** and
changes none of those numbers. In particular:

- v1.10 must not increase the per-period record count of the
  v1.9.last fixture (any v1.10.x demo extension uses its own
  separately-scoped fixture or is gated off by default);
- v1.10 must not alter v1.9.last's Markdown / manifest /
  digest format;
- v1.10 must not weaken the eight-flag hard boundary of the
  reference world README.

## v1.10.1 — what shipped

v1.10.1 lands the first concrete primitive of the v1.10 layer: a
storage-and-audit shape for *stewardship themes*. The ship is
deliberately narrow; everything outside the storage layer (review
routines, attention integration, dialogue records, escalation /
corporate-response candidates, living-world integration) stays out
of v1.10.1 and lands at later milestones in the sequence.

**What v1.10.1 adds**

- `world/stewardship.py` — the immutable `StewardshipThemeRecord`
  dataclass and the append-only `StewardshipBook` store with
  `add_theme`, `get_theme`, `list_themes`, `list_by_owner`,
  `list_by_owner_type`, `list_by_theme_type`, `list_by_status`,
  `list_by_priority`, `list_active_as_of`, and `snapshot`.
- `world/ledger.py` — a new `RecordType.STEWARDSHIP_THEME_ADDED`
  enum value, emitted exactly once per `add_theme` call.
- `world/kernel.py` — wires `stewardship: StewardshipBook` in
  `WorldKernel`, with the same ledger / clock injection pattern
  used by every other v0/v1 source-of-truth book.
- `tests/test_stewardship.py` — 58 tests covering field validation,
  immutability, duplicate rejection, unknown-id lookup, every
  list / filter, the active-window predicate semantics
  (`is_active_on` + `list_active_as_of`), deterministic snapshots,
  ledger emission of the new record type, kernel wiring, the
  no-mutation guarantee against every other source-of-truth book in
  the kernel, the no-action invariant (a bare `add_theme` emits
  exactly one `STEWARDSHIP_THEME_ADDED` record and nothing else),
  and a jurisdiction-neutral identifier scan over both the new
  module and the test file itself.

**What v1.10.1 does not add**

The v1.10 hard boundary is binding. v1.10.1 does **not** add
voting, proxy voting, engagement execution, escalation, corporate
response, investment recommendation, trading, price formation, real
data ingestion, Japan calibration, jurisdiction-specific stewardship
codes, source-specific behavior probabilities, or any new
mechanism. A theme record is monitoring / attention storage only.

**Future hooks**

A `StewardshipThemeRecord` is shaped so that later milestones can
read it without rewriting the storage layer:

- v1.10.2 `portfolio_company_dialogue_record` will reference theme
  records by `theme_id`.
- v1.10.3 `investor_escalation_candidate` and
  `corporate_strategic_response_candidate` `MechanismAdapter`
  implementations will read theme records as part of their
  evidence bundle.
- v1.10.5 living-world integration will wire a review routine that
  consults `list_active_as_of` to decide which themes are in scope
  for a given simulation date.

**Test count**

v1.10.1 adds 58 tests. The total test count moves from
`1626 / 1626` (v1.10.0) to `1684 / 1684` (v1.10.1).

## v1.10 milestone sequence

1. **v1.10.0 — Universal Engagement / Strategic Response
   Consolidation Docs.** Shipped. This document + `world_model.md`
   §70 + boundary updates + roadmap update. No code, no test count
   change.
2. **v1.10.1 — `stewardship_theme_signal`.** Shipped. First concrete
   record shape + minimal book + ledger record type + kernel wiring.
   Tests exercise the no-behavior boundary explicitly.
3. **v1.10.2 — `portfolio_company_dialogue_record`.** Dialogue book
   + record shape + a review-routine emission path that reads
   v1.10.1's theme signals. Tests exercise that the dialogue record
   never carries verbatim or paraphrased contents.
4. **v1.10.3 — `investor_escalation_candidate` +
   `corporate_strategic_response_candidate`.** Two `MechanismAdapter`
   implementations satisfying the v1.9.3 / v1.9.3.1 contract,
   sibling to the v1.9.4 / v1.9.5 / v1.9.7 adapters. Tests
   exercise no-action / no-vote / no-corporate-action / no-trade
   boundaries.
5. **v1.10.4 — Optional `industry_demand_condition_signal`.**
   Optional later extension; can ship as a single signal book with
   no consumer mechanism.
6. **v1.10.5 — Living-world integration.** Wires v1.10.1–v1.10.3
   (and optionally v1.10.4) into the multi-period sweep behind a
   v1.10-scoped fixture, separate from the v1.9.last default
   fixture. The v1.9.last fixture remains byte-deterministic.
7. **v1.10.last — Public engagement layer freeze.** Docs-only.
   Mirrors v1.9.last's discipline: anti-claim list, scope-language
   agreement, forbidden-token scan clean, no investment-advice
   framings, CI green on the tag commit.

## v1.10.0 success criteria

§v1.10.0 is complete when **all** hold:

1. `docs/v1_10_universal_engagement_and_response_design.md` exists
   and covers the five selected concepts using the same template:
   purpose, generic inputs, generic outputs, candidate FWE object
   type, existing FWE hook, no-behavior boundary, out of scope,
   future v2 mapping slot.
2. `docs/world_model.md` carries a §70 v1.10.0 section pointing to
   this document and naming the meta-abstraction deferral rule.
3. `docs/public_private_boundary.md` carries a brief v1.10
   addendum reaffirming that engagement-layer artifacts (theme
   signals, dialogue records, escalation / response candidates,
   industry demand-condition signals) follow the same public /
   restricted rules — and in particular that verbatim or
   paraphrased dialogue contents are restricted regardless of
   jurisdiction.
4. `docs/test_inventory.md` headline reflects v1.10.0 (docs-only;
   no test count change from v1.9.last).
5. `README.md` roadmap section adds v1.10.x rows at "In progress"
   / "Planned" status, never claiming behavior the milestones have
   not yet shipped.
6. The full test suite continues to pass at `1626 / 1626`.
7. `compileall world spaces tests examples` is clean and `ruff
   check .` from the repo root is clean.
8. The forbidden-token word-boundary scan is clean.
9. No country-specific institution names, source / report names,
   jurisdiction-specific thresholds, domestic dataset names,
   behavior probabilities, bank-specific strategy assumptions,
   forecast values, paid / NDA / proprietary content, or
   confidential dialogue contents appear in the v1.10.0 docs.
10. No investment-recommendation language (direct or indirect)
    appears in the v1.10.0 docs.

## Anti-scope

v1.10.0 deliberately does **not** add: any new economic behavior,
any new mechanism, any new `MechanismAdapter`, any new ledger
record type, any new book, any new test; price formation, trading,
lending decisions, loan origination, covenant enforcement,
contract or constraint mutation, voting execution, AGM / EGM
filings, corporate-action execution, real-data ingestion, paid-data
ingestion, expert-input ingestion, Japan calibration, named
real-institution content, calibrated behavior probabilities,
forecast values, investment-recommendation framings, scenario
branching, stress logic, native (C++ / Julia / Rust / GPU)
rewrites, profiling harnesses, web UI. v1.10.0 is documentation
only.

## What this document does not decide

- The exact field schema for each record (decided at the
  per-milestone landing — v1.10.1 / v1.10.2 / v1.10.3 / v1.10.4).
- Which review routines emit each new record (decided at v1.10.5
  living-world integration).
- Whether v1.10.5 ships a separate demo entry point or extends the
  existing one with an opt-in flag (decided at v1.10.5).
- The specific `_FORBIDDEN_TOKENS` deltas needed to lock the v1.10
  scope language (decided at v1.10.last freeze).
- Whether the meta-abstractions
  (`actor_business_model_transition_pressure`,
  `actor_strategic_response_candidate`) ever ship in public FWE.
  That decision is reopened only after at least two concrete
  specializations are stable in public FWE.

## Cross-references

- v1.7 reference financial system: `docs/v1_reference_system_design.md`.
- v1.5 relationship capital layer: `docs/v1_relationship_capital_design.md`.
- v1.8 endogenous activity infrastructure:
  `docs/v1_endogenous_reference_dynamics_design.md`,
  `docs/v1_interaction_topology_design.md`,
  `docs/v1_reference_variable_layer_design.md`.
- v1.9 mechanism interface contract:
  `docs/model_mechanism_inventory.md`,
  `docs/behavioral_gap_audit.md`.
- v1.9.last public prototype freeze:
  `docs/v1_9_public_prototype_summary.md`,
  `docs/world_model.md` §69.
- Public / restricted boundary:
  `docs/public_private_boundary.md`.
- Performance boundary discipline:
  `docs/performance_boundary.md`.
- Naming policy: `docs/naming_policy.md`.

