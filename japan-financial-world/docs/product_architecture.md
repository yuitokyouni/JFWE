# Product Architecture

This document describes the **public product architecture** of the
Financial World Engine project. It is distinct from the technical
architecture documents ([`architecture_v0.md`](architecture_v0.md),
[`architecture_v1.md`](architecture_v1.md)), which describe how the
code is structured. This document describes how the *project* is
structured into product layers, what is public, what is not, and how
the generic engine relates to Japan-specific calibration.

This document does **not** rename any Python package, module, import,
or repository path. The current code uses the JFWE / `japan-financial-
world` / `world` / `spaces` names; any future rename is a separate
migration not committed in this version. See
[`naming_policy.md`](naming_policy.md).

## TL;DR

There are five product layers. Two are generic and public. One is
Japan-specific and partially public. Two are Japan-specific and
private. The current repository is at the v1.7 freeze and corresponds
to the **FWE Core** layer.

```
┌──────────────────────────────────────────────────────────────────────┐
│  FWE Core            (public)        v0 + v1 — current freeze        │
│    Jurisdiction-neutral kernel + reference financial system          │
│    Registry, Clock, Scheduler, Ledger, EventBus, Books,              │
│    Projections, Signals, Valuation, Institutions, External           │
│    Processes, Relationships, Reference Loop                          │
├──────────────────────────────────────────────────────────────────────┤
│  FWE Reference       (public)        not started                     │
│    Fictional-country / fictional-market reference demo               │
│    Synthetic entities only — no real-world identifiers               │
├──────────────────────────────────────────────────────────────────────┤
│  FWE Public Demo     (public, optional future)                       │
│    Optional public demo layer using synthetic data                   │
│    Educational / illustrative only — not a production tool           │
├──────────────────────────────────────────────────────────────────────┤
│  JFWE Public         (partially public)        v2 territory          │
│    Japan public calibration                                          │
│    Public Japan data only, careful license handling                  │
│    Public release depends on redistribution rights                   │
├──────────────────────────────────────────────────────────────────────┤
│  JFWE Proprietary    (NEVER public)             v3 territory         │
│    Private / commercial Japan calibration                            │
│    Expert interviews, paid data, non-public assumptions,             │
│    proprietary templates, named-institution stress results,          │
│    client reports                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

## Layer definitions

### 1. FWE Core (public)

**Status:** v0 frozen at v0.16, v1 frozen at v1.7 — this is what the
current repository contains.

**What it is:** A jurisdiction-neutral world kernel plus a
jurisdiction-neutral reference financial system. FWE Core defines
*structure* (books, projections, transport, identity, scheduler) and
*reference content shape* (record types, books, action contract,
orchestrator), but no autonomous behavior and no calibration.

**Includes:**

- v0 kernel: `Registry`, `Clock`, `Scheduler`, `Ledger`, `State`,
  `EventBus`, `OwnershipBook`, `ContractBook`, `PriceBook`,
  `ConstraintBook`, `SignalBook`, `BalanceSheetProjector`,
  `ConstraintEvaluator`, `DomainSpace`, eight concrete spaces
  (Corporate, Banking, Investors, Exchange, Real Estate, Information,
  Policy, External).
- v1 reference layer: `ValuationBook`, `ValuationComparator`,
  `IntradayPhaseSpec`/`PhaseSequence`, `InstitutionBook`,
  `ExternalProcessBook`, `RelationshipCapitalBook`,
  `ReferenceLoopRunner`.

**Cadence:** Slow. Changes here are model-architecture changes and
require a milestone document.

**Public:** Yes. Published as the FWE Core open layer of the project.

### 2. FWE Reference (public)

**Status:** Not started. Planned as a future demo layer.

**What it is:** A fictional-country, fictional-market reference demo
that *populates* FWE Core with synthetic entities so the engine can be
demonstrated end-to-end without any real-world identifiers. Think
"Country X with Bank A, Firm B, Investor C, an external rate factor,
and a synthetic policy authority."

**Rules:**

- Uses synthetic entities only. No real bank names, no real listed
  firms, no real macro time series, no real central-bank identifiers.
- Self-contained: an FWE Reference run does not depend on any external
  data feed.
- Deterministic: synthetic populations and process specs are checked
  in or generated from a fixed seed.

**Cadence:** Medium. Updated when FWE Core's record shapes evolve, or
when the demo expands to cover a new behavior.

**Public:** Yes.

### 3. FWE Public Demo (public, optional future)

**Status:** Not committed. May or may not happen.

**What it is:** An optional layer above FWE Reference that turns the
synthetic reference into something easier to demo (interactive
visualization, scripted scenarios, narrative explanations). Still
synthetic; still not a production or investment tool.

**Rules:**

- No real-world identifiers, period. The point of staying synthetic at
  this layer is so the demo cannot be misused as an investment tool.
- No web UI, no hosted service, and no pricing decision is committed in
  this document; those are separate product decisions.
- Educational and illustrative only.

**Cadence:** Slow. Driven by external demo / education use cases.

**Public:** Yes if it ships.

### 4. JFWE Public (partially public)

**Status:** v2 territory. Not started.

**What it is:** Japan **public** calibration on top of FWE Core.
Populates FWE Core books with Japan public data: BOJ policy rate
history, MOF / Cabinet Office macro time series, MLIT real-estate
indices, FSA institutional registry, JPX listing-level masters,
TDnet / EDINET disclosures, etc.

**Rules:**

- **Public data only.** Every data source must have a license review on
  file (see [`v2_readiness_notes.md`](v2_readiness_notes.md)).
- **Redistribution-aware.** Some Japan public sources permit
  redistribution with attribution; others permit derived results only.
  JFWE Public's release boundary depends on which sources are used.
- **Reproducible from a fixed snapshot.** A JFWE Public run is tied to
  a specific data-source snapshot date; "latest" pulls are not
  permitted in committed runs.
- **No proprietary content.** Expert overrides, paid data, and non-
  public assumptions belong to JFWE Proprietary, not here.

**Cadence:** Medium-high. Driven by public-source release cycles
(monthly macro, quarterly Tankan, annual filings, etc.).

**Public:** Partial. Code that loads / structures the data is public
when license allows; raw data redistribution is gated per-source.

### 5. JFWE Proprietary (NEVER public)

**Status:** v3 territory. Not started.

**What it is:** Private / commercial Japan calibration. Layers
proprietary content on top of JFWE Public: paid news feeds, paid
analyst datasets, fund holdings beyond public minimums, expert
interview notes, internal consensus forecasts, expert overrides for
structural breaks, proprietary templates for stress scenarios, named-
institution stress results, client reports.

**Rules:**

- **Never published.** Code, data, parameters, and outputs in this
  layer are not redistributed publicly.
- **Access-controlled.** Read access is restricted to authorized
  users; write access is restricted further.
- **Audit-traceable.** Per the v0 ledger contract, every change is
  recorded; the proprietary layer inherits that property and adds
  source / license attribution per record.
- **Strict separation from JFWE Public.** A JFWE Public artifact must
  not embed proprietary content; a JFWE Proprietary artifact may
  reference but not inline public data.

**Cadence:** Vendor-driven, expert-meeting-driven.

**Public:** No. Ever.

## How the layers compose

```
JFWE Proprietary  (v3, never public)
       │  layers proprietary content on top of public calibration
       ▼
JFWE Public       (v2, partially public)
       │  populates FWE Core books with Japan public data
       ▼
FWE Public Demo   (optional future, public)
       │  optional polish layer above the reference demo
       ▼
FWE Reference     (planned, public)
       │  populates FWE Core with synthetic entities
       ▼
FWE Core          (v0 + v1, public; current freeze)
       structure + jurisdiction-neutral reference behavior
```

A higher layer only adds **content** to the lower layer. It does not
modify the lower layer's record shapes, book APIs, or invariants. This
is the same additivity rule that lets v1 sit on top of v0 without
re-litigating the kernel: v2 sits on top of v1 without re-litigating
the reference content; v3 sits on top of v2 without re-litigating the
public calibration.

## Public positioning (what FWE / JFWE is and is not)

State clearly:

- **FWE / JFWE is NOT a market predictor.** It does not forecast
  prices, returns, defaults, or any market outcome. It simulates a
  causal, auditable financial world; it does not predict the real
  world.
- **FWE / JFWE is NOT investment advice.** Outputs are not
  recommendations, signals, allocations, or solicitations. Anything
  that looks like a price, valuation, or institutional action in an
  FWE artifact is a **simulation record**, not a market view.
- **FWE / JFWE is NOT a calibrated Japan market model yet.** v2 has
  not started. The current code is fully jurisdiction-neutral. JFWE
  Public will be a calibrated Japan model when v2 ships; until then,
  any Japan-specific claim is out of scope.
- **FWE / JFWE IS a causal, auditable, multi-space financial-world
  simulation engine.** Every state-changing event is recorded in an
  append-only ledger with cross-references that form a complete
  causal graph. Eight domain spaces (corporate, banking, investors,
  exchange, real estate, information, policy, external) are wired
  through explicit world objects (ownership, contracts, prices,
  signals, constraints, valuations, institutions, external processes,
  relationships) with a strict no-cross-mutation rule.

These four lines are the public positioning. Marketing or external
descriptions of the project should not contradict them.

## Repo / package names today

Despite the project name and the layered product picture above, the
**current repository keeps its existing names**:

- Repository: `JWFE` (the GitHub repo name is unchanged in this
  version).
- Working directory: `japan-financial-world/`.
- Python packages: `world/`, `spaces/`, `tests/`, `docs/`,
  `examples/`, `schemas/`, `data/`.
- Imports: `from world.kernel import WorldKernel`, etc.

This is intentional. The product architecture above clarifies how the
project is *positioned*; it does not commit to a rename. A future
migration may move FWE Core code under an `fwe/` or `finworld/` package
namespace, with Japan calibration under a separate package, but that
migration is a discrete task with its own test-passing milestone — not
something this v1.7-era documentation change performs.

See [`naming_policy.md`](naming_policy.md) for the full naming rules
(why WFE is avoided, why FWE is preferred, and how to handle legacy
JFWE references).

## Where each layer's code / docs live (today)

| Layer            | Code location (today)                              | Docs location (today)                              |
| ---------------- | -------------------------------------------------- | -------------------------------------------------- |
| FWE Core         | `japan-financial-world/world/`, `japan-financial-world/spaces/` | `japan-financial-world/docs/v0_*`, `docs/v1_*`, `docs/world_model.md`, `docs/architecture_v*.md` |
| FWE Reference    | (not started — would live under a `reference/` package or similar) | (not started)                                |
| FWE Public Demo  | (not started — separate package if it ships)       | (not started)                                      |
| JFWE Public      | (v2; not started — would live under e.g. `calibrations/v2_jp_public/`) | `japan-financial-world/docs/v2_readiness_notes.md` (informal) |
| JFWE Proprietary | (v3; never public — separate private repo)         | (private)                                          |

Note that today *everything* lives under `japan-financial-world/`. That
is a legacy of the project's origin, not a design statement. The
current FWE Core code is jurisdiction-neutral despite the directory
name.

## What this document does not decide

This document is a positioning and product-layering statement. It
explicitly does not decide:

- Specific FWE Reference content (what fictional country / market /
  institutions it ships with).
- FWE Public Demo's UI / hosting / pricing — the "Public Demo" name is
  a layer label, not a product launch.
- Specific JFWE Public data sources or licenses (covered partially in
  `v2_readiness_notes.md`; full review is a v2 task).
- JFWE Proprietary's access-control model, audit policy, or
  vendor-onboarding process (a v3 planning task).
- Any rename of repository, package, or import path.

If a future task requires changing one of these decisions, it should
update this document and link to its own milestone record.
