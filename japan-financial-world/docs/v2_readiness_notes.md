# v2 Readiness Notes

This document is a **forward-looking note**, written at the v1.7 freeze, to
surface what v2 will need before its first milestone starts. It is not a
v2 design document and does not commit to any specific v2 schedule. The
purpose is to record (a) which v1 books v2 will populate, (b) which Japan
public data sources have been informally surveyed so far, (c) which
licenses or terms-of-use questions remain open, and (d) the v2 vs v3
boundary clarification that should be in place before v2 starts.

v2 is **Japan public calibration**. v3 is **Japan proprietary / commercial
calibration**. Neither v2 nor v3 changes v1 record shapes or v1 book APIs;
both layer data on top of the v1 contract.

## Data source inventory (informal, as of v1.7)

The following Japan public data categories have been informally identified
as candidates for v2. None has been formally licensed yet; each should
have a license review (see [License review](#license-review-open-questions))
before any data is ingested.

### Macroeconomic time series

| Category                          | Probable source(s)                              | v1 book that ingests        |
| --------------------------------- | ----------------------------------------------- | --------------------------- |
| Policy rate (uncollateralized overnight call rate, target / range) | BOJ Statistics  | `ExternalProcessBook` (`process_type=constant` revisions, plus discrete revision events) |
| Long-term JGB yields (2y, 5y, 10y, 20y, 30y, 40y) | Ministry of Finance (MOF), JBMA | `ExternalProcessBook` (per-tenor factors) |
| CPI / Core CPI / Core-Core CPI   | Statistics Bureau (Stat Bureau / e-Stat)       | `ExternalProcessBook`       |
| Industrial production index       | METI                                            | `ExternalProcessBook`       |
| GDP (nominal, real, deflator, components) | Cabinet Office                          | `ExternalProcessBook`       |
| Tankan business survey            | BOJ                                             | `ExternalProcessBook` (qualitative diffusion indices) |
| FX rates (USD/JPY, EUR/JPY)       | BOJ reference rate                              | `ExternalProcessBook`       |
| Real-estate price indices         | MLIT (Land Price Survey, Real Estate Transaction Index) | `ExternalProcessBook` |

All time series are stored as `ExternalFactorObservation` populations
referencing an `ExternalFactorProcess` spec. v2 picks process parameters
(drift, vol, regime probabilities) from the data; v1 stores the spec
shape but does not run it.

### Institutional registry

| Category                          | Probable source(s)                              | v1 book that ingests        |
| --------------------------------- | ----------------------------------------------- | --------------------------- |
| Listed equities (TSE Prime / Standard / Growth) | TSE / JPX listings              | `Registry` (kind=`firm`, `asset`); `InstitutionBook` for the issuing firm where it operates as an institution |
| Banks (Japanese-licensed banks, regional banks, shinkin) | FSA registry, JBA  | `InstitutionProfile` + `Registry` (kind=`bank`) |
| Securities firms                  | FSA registry, JSDA                              | `InstitutionProfile`        |
| Insurance companies               | FSA registry                                    | `InstitutionProfile`        |
| Pension funds (GPIF, KKR, public pension funds) | Public disclosures             | `InstitutionProfile`        |
| Government / ministries / agencies | Public records                                 | `InstitutionProfile`        |

Each entry becomes an `InstitutionProfile` with `jurisdiction_code="JP"`.
v1 does not enumerate `institution_type` values; v2 picks a controlled
vocabulary appropriate for Japan and documents it in a v2 design doc.

### Mandates and policy instruments

| Category                          | Probable source(s)                              | v1 book that ingests        |
| --------------------------------- | ----------------------------------------------- | --------------------------- |
| BOJ monetary policy mandate       | Bank of Japan Act, BOJ statements              | `MandateRecord`             |
| BOJ policy instruments (policy rate, JGB purchases, ETF purchases historical) | BOJ press releases / statements | `PolicyInstrumentProfile` |
| MOF / FSA regulatory mandates     | Public laws / ordinances                        | `MandateRecord`             |
| Capital adequacy / leverage / liquidity rules | Basel III JP implementation (FSA)        | (v1 has no rule book; reference rules expressed as `ConstraintRecord`s when v2 introduces them) |

Mandate text is structured: `effective_from`, optional
`effective_until`, `policy_targets`, free-form `metadata`. Cross-references
to instruments and authorities are stored as data.

### Corporate fundamentals

| Category                          | Probable source(s)                              | v1 book that ingests        |
| --------------------------------- | ----------------------------------------------- | --------------------------- |
| Listed-company financial filings (TDnet, EDINET) | TSE / FSA disclosure         | future v2-tier "fundamentals" book; v1.1 has the valuation layer but no fundamentals book yet |
| Earnings calendar                 | TDnet / company IR                              | `InformationSignal` (scheduled-event signals) |
| Corporate actions (dividends, splits, buyback announcements) | TDnet                | `InformationSignal` + `InstitutionalActionRecord` |

v1.1 introduced the valuation layer (`ValuationBook`) but did not introduce
a separate fundamentals book. Whether v2 reuses `ValuationRecord.assumptions`
to carry fundamentals or introduces a new book is a v2 design decision; it
does not change the v1 contract either way.

### Real-estate

| Category                          | Probable source(s)                              | v1 book that ingests        |
| --------------------------------- | ----------------------------------------------- | --------------------------- |
| J-REIT NAV / distribution / cap rate | TSE J-REIT data, ARES                       | `Registry` (kind=`asset`); `ValuationBook` |
| Land price survey                 | MLIT                                            | `ExternalProcessBook` (per-region factors) |
| Real-estate transaction index     | MLIT                                            | `ExternalProcessBook`       |

### Information dynamics (out of v2 default scope)

News generation, source credibility tracking, and narrative dynamics are
out of v1 scope and are **not** automatically in v2 scope either.
Whether v2 introduces a Japan-specific information layer depends on
whether public news data sources are licensable on terms compatible
with simulation use; if not, this category is deferred to v3.

## Entity mapping (v1 record shape ← Japan reality)

A v2 ingestion needs to commit to a mapping from Japan public records to
v1 record shapes. The mapping below is a starting point. Every column is
a v1 record-shape question that v2 will answer.

| Japan reality                     | v1 record shape                                  | Mapping question                                    |
| --------------------------------- | ------------------------------------------------ | --------------------------------------------------- |
| BOJ                               | `InstitutionProfile(institution_id="institution:boj", institution_type="central_bank", jurisdiction_code="JP")` | Institution-type controlled vocabulary?            |
| BOJ policy rate target            | `MandateRecord` + `ExternalFactorProcess`        | Two records (mandate + factor) or one with cross-ref? |
| BOJ rate-change announcement      | `InformationSignal` + `WorldEvent` + `InstitutionalActionRecord` | Which one is canonical? (Both per the action contract.) |
| Listed equity (e.g., 7203)        | `Registry(kind="firm")` + `Registry(kind="asset")` | One or two registry entries per ticker?           |
| Earnings disclosure               | `InformationSignal(signal_type="earnings_disclosure")` + `InstitutionalActionRecord` | Signal first or action first?                     |
| Bank lending exposure             | `ContractBook` (existing v0)                     | How to populate from public data (FSA aggregate vs disclosed loan books)? |
| Trade flow / FX intervention      | `ExternalFactorObservation` + `InformationSignal` | Granularity (transaction-level vs daily total)?    |
| J-REIT distribution               | `ContractBook` (distribution as obligation) or `InstitutionalActionRecord` | Which one fits J-REIT mechanics?                  |

These are open questions to resolve before v2 starts ingestion. The v1
record shapes are stable; the question is *which* v1 record shape fits
*which* Japan reality.

## License review (open questions)

Every public data source has a terms-of-use document. Before any v2
ingestion, the following must be confirmed for each source:

1. **Redistribution.** Can the data be redistributed inside the
   simulation engine, or only used for derived results?
2. **Caching.** Can the data be cached locally, and for how long?
3. **Attribution.** What attribution string is required?
4. **Commercial use.** Is commercial use allowed, restricted, or
   prohibited? (This question separates v2 from v3 in many cases — see
   [v2 vs v3 clarification](#v2-vs-v3-clarification).)
5. **Update obligations.** Are stale snapshots prohibited?
6. **Format / API stability.** Is there a published API or only HTML /
   PDF? (Affects ingestion code, not record shape.)

Sources informally identified above do not yet have license reviews on
file. The v2 milestone planning document should include a checklist
covering the above six questions for each source.

### Sources that are likely licensable for v2

- Government statistical sources (e-Stat, MOF, METI, Cabinet Office,
  MLIT) — typically permit redistribution with attribution under the
  Government of Japan Standard Terms of Use, but the specific URL set
  used must be verified.
- BOJ public data (policy rate history, FX reference rates, Tankan) —
  typically permit redistribution with attribution.
- JPX / TSE listing-level public data (listed-equity master data, daily
  closing prices) — terms vary by data product; some require a
  licensed feed even for the daily close.

### Sources that may be v3 only

- Real-time market data (intraday quotes, full-depth book).
- Tick data / trade-by-trade history.
- Proprietary news feeds (Nikkei QUICK news, Bloomberg news, Refinitiv
  news).
- Fund-level holdings disclosures beyond the public minimum.
- Detailed corporate fundamentals beyond what TDnet / EDINET makes
  public (e.g., paid analyst datasets).

The v3 layer is where these sources should live, because they typically
require a paid license and proprietary handling rules.

## v2 vs v3 clarification

A common source of confusion is "Japan data" being treated as one
category. v1.7 freeze codifies that it is **two** categories with
different cadence and review profiles.

| Layer | Owns                                                  | Review profile                          | Update cadence            |
| ----- | ----------------------------------------------------- | --------------------------------------- | ------------------------- |
| v2    | **Japan public calibration.** Government statistical sources, BOJ public series, JPX listing-level masters, public regulatory filings. Data that is freely or licensably available with attribution. | Reviewed by Japan macro / market specialists for **source credibility** and license compliance. | Aligns with public-source release cycles (monthly macro, quarterly Tankan, annual filings, etc.). |
| v3    | **Japan proprietary / commercial / expert calibration.** Paid news feeds, paid analyst datasets, fund holdings beyond public minimums, expert overrides for structural breaks, internal consensus forecasts, real-time market data. | Reviewed by domain experts for **proprietary-knowledge handling**, license compliance, and access-control rules. | Aligns with vendor delivery cadence and expert review meetings. |

### When a request is v2 vs when it is v3

- "Use the BOJ policy rate history" → **v2**. (Public, attributable.)
- "Use a paid Bloomberg news feed for narrative signals" → **v3**.
  (Paid, license-restricted.)
- "Use TSE Prime listing master to populate the registry" → **v2** if
  the daily-master license is in scope; otherwise **v3**.
- "Use a proprietary fund's monthly holdings disclosure" → **v3**.
- "Override the v2-calibrated AR(1) inflation process with an expert
  judgment for the 2024-2026 regime" → **v3** (expert override).
- "Add a J-GAAP-specific accounting rule" → **v2** if the rule is
  publicly documented; the implementation lives in a v2 milestone, not
  v1.

If a request straddles the boundary, default to v2 only if the *data*
and the *implementation* are both publicly available and licensable;
otherwise it is v3.

## Pre-v2 checklist

Before the v2.0 milestone starts, the following should be in place:

1. **License reviews on file** for every Japan public source planned
   for the first v2 milestone (BOJ, MOF, Cabinet Office, MLIT, JPX
   master data at minimum).
2. **Institution-type controlled vocabulary** chosen for v2 (central
   bank / commercial bank / regional bank / shinkin / securities firm
   / life insurer / non-life insurer / public pension / corporate pension
   / government agency / ministry / etc.).
3. **Mapping decisions** for the open questions above (one or two
   registry entries per ticker; signal-first or action-first for
   announcements; etc.).
4. **Data ingestion harness** decision: streaming pull vs static
   snapshot vs vendor SDK. v1 has no ingestion harness; this is a v2
   tooling concern, not a v1 record-shape concern.
5. **v2 / v3 separation pattern**: directory layout (e.g., `calibrations/v2_jp_public/` and `calibrations/v3_jp_proprietary/`), config-loader contract, and access-control conventions for v3.
6. **Versioning convention** for calibrations: a v2 calibration that
   uses BOJ data as of YYYY-MM-DD is reproducible from a fixed snapshot
   identifier, not from a "latest" pull.

These are the items that, if missing at v2.0 start, will create rework.
None of them is a v1 deliverable; they are recorded here so the v1.7
freeze hands off a clean readiness picture to the v2 planner.

## What v1.7 deliberately does NOT decide

v1.7 is a freeze of the reference financial system, not a v2 design
session. The following are explicitly **not** decided in this document:

- Specific v2 data vendor choices.
- The v2 directory layout (`calibrations/v2_jp_public/` vs alternatives).
- The v2 ingestion harness library / framework.
- The v2 institution-type controlled vocabulary.
- Whether v2 fundamentals live in `ValuationRecord.assumptions` or in a
  new fundamentals book.
- The v3 access-control model.

These belong to a v2.0 planning milestone (or its v3 counterpart). The
purpose of this document is solely to make sure the v1.7 freeze records
the v2-readiness picture before context fades.
