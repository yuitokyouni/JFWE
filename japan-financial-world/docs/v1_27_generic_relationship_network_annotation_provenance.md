# v1.27 Generic Strategic Relationship Network + Annotation Provenance Hardening — Design Note

*v1.27 is the **last generic substrate addition** before
v2.0 Japan public calibration boundary design begins. It
adds two independent primitives: (1) a generic strategic
relationship record type (cross-shareholding-like /
supplier-customer-like / group-affiliation-like /
governance-relationship-like / commercial-relationship-
like — all closed-set archetypes, no real company names,
no percentages, no voting power), and (2) annotation
provenance hardening over the v1.24 manual-annotation
surface (pseudonymous reviewer-role / authority /
authorization metadata as a companion record; no real
person data; no LLM authoring).*

This document is **docs-only at v1.27.0**. It introduces
no runtime module, no new dataclass, no new ledger event,
no new test, no new label vocabulary, no new behavior.
v1.27.1 / v1.27.2 / v1.27.3 / v1.27.last must implement
exactly to this design or the design must be re-pinned.

---

## 1. Scope statement (binding)

v1.27 closes the last two substrate gaps the post-v1.25
review identified:

1. **Generic strategic relationship network.** Real-world
   reviewers care about cross-shareholding, supplier-
   customer relationships, group affiliations,
   lender relationships, and governance overlap.
   v1.x has no substrate for any of these. v1.27.1
   adds a generic `StrategicRelationshipRecord` —
   `_like` archetype labels, no real company names, no
   percentages, no voting power.
2. **Annotation provenance hardening.** v1.24 manual
   annotations carry `source_kind = "human"` /
   `reasoning_mode = "human_authored"` but no
   reviewer-role / authority / authorization metadata.
   v1.27.3 adds a companion
   `ManualAnnotationProvenanceRecord` — pseudonymous
   only, no real person names, no real institution
   names, no LLM authoring, no compliance claim.

What v1.27 is **NOT** (binding):

- **NOT real data ingestion.** No EDINET / TDnet /
  J-Quants / FSA-filing adapter. No real Japanese
  cross-shareholding extraction. No real company
  names.
- **NOT a percentage / voting / market-value
  surface.** Strategic relationships carry **no**
  ownership percentage, **no** voting power, **no**
  market value, **no** shareholder identifier
  beyond plain-id citation.
- **NOT a network-centrality / systemic-importance
  surface.** v1.27.2 readout exposes counts only —
  no centrality score, no systemic-importance
  score, no risk score.
- **NOT real reviewer identity.** Provenance records
  carry pseudonymous `annotator_id_label` (closed
  format like `reviewer_lead_a`, never a real
  email or person name).
- **NOT a compliance / SOC2 / FISC claim.**
  Provenance records carry closed-set
  `authority_label` / `evidence_access_scope_label`
  describing the audit context, not a regulatory
  compliance assertion.
- **NOT LLM authoring.** v1.27.x records are
  human-authored or substrate-defaulted only.

---

## 2. `StrategicRelationshipRecord` (binding for v1.27.1)

```python
@dataclass(frozen=True)
class StrategicRelationshipRecord:
    """Immutable, append-only record of one generic
    strategic relationship between two entities."""

    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type_label: str
    direction_label: str
    evidence_ref_ids: tuple[str, ...]
    effective_from_period_id: str
    effective_to_period_id: str | None
    status: str = "active"
    visibility: str = "internal"
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)
```

### 2.1 Closed sets

```python
RELATIONSHIP_TYPE_LABELS: frozenset[str] = frozenset({
    "strategic_holding_like",
    "supplier_customer_like",
    "group_affiliation_like",
    "lender_relationship_like",
    "governance_relationship_like",
    "commercial_relationship_like",
    "unknown",
})

DIRECTION_LABELS: frozenset[str] = frozenset({
    "directed",
    "reciprocal",
    "undirected",
    "unknown",
})
```

### 2.2 Field semantics

- `source_entity_id` / `target_entity_id` — plain-id
  citations.
- `relationship_type_label` — closed-set; `_like`
  suffix is binding.
- `direction_label` — closed-set.
- `evidence_ref_ids` — plain-id citation tuple
  (manual annotations, scenario applications, etc.).
- `effective_from_period_id` — non-empty.
- `effective_to_period_id` — optional; when
  ``None``, the relationship is open-ended; when
  set, must be ≥ `effective_from_period_id`
  lexicographically.

### 2.3 Forbidden tokens (binding)

The v1.27.0 forbidden-token delta extends the v1.26.0
canonical composition:

```python
FORBIDDEN_TOKENS_V1_27_0_RELATIONSHIP_DELTA: frozenset[str] = (
    frozenset({
        # v1.27.0 ownership / voting / value prohibitions
        "ownership_percentage",
        "voting_power",
        "voting_share",
        "controlling_interest_pct",
        "share_count",
        "share_class",
        "market_value",
        "fair_value",
        "carrying_value",
        # v1.27.0 network-score prohibitions
        "centrality_score",
        "systemic_importance_score",
        "network_centrality",
        "betweenness_centrality",
        "eigenvector_centrality",
        # v1.27.0 real-data adapter prohibitions
        "edgar_filing",
        "tepco_holding",
    })
)
```

### 2.4 Default boundary flags

The v1.26.0 default flags + new v1.27.0 additions:

- `no_ownership_percentage`
- `no_voting_power`
- `no_market_value`
- `no_centrality_score`
- `no_real_company_relationship`

---

## 3. `ManualAnnotationProvenanceRecord` (binding for v1.27.3)

```python
@dataclass(frozen=True)
class ManualAnnotationProvenanceRecord:
    """Immutable, append-only provenance metadata
    companion record for a v1.24
    ManualAnnotationRecord."""

    provenance_id: str
    annotation_id: str
    annotator_id_label: str
    reviewer_role_label: str
    authority_label: str
    authorization_ref_id: str | None
    review_context_id: str | None
    evidence_access_scope_label: str
    audit_period_id: str
    status: str = "active"
    visibility: str = "internal"
    boundary_flags: Mapping[str, bool] = field(
        default_factory=_default_boundary_flags
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)
```

### 3.1 Closed sets

```python
AUTHORITY_LABELS: frozenset[str] = frozenset({
    "self_review",
    "delegated_review",
    "supervisory_review",
    "audit_review",
    "unknown",
})

EVIDENCE_ACCESS_SCOPE_LABELS: frozenset[str] = frozenset({
    "public_synthetic",
    "internal_synthetic",
    "restricted_synthetic",
    "unknown",
})
```

`reviewer_role_label` reuses v1.24
`REVIEWER_ROLE_LABELS`. `annotator_id_label` is a
**pseudonymous** plain-id (e.g.
`reviewer_lead_a` / `analyst_b`); v1.27.3 storage
explicitly forbids `@` characters (anti-email-leak)
and any token resembling a real-person
name pattern.

### 3.2 Forbidden tokens (binding for v1.27.3)

```python
FORBIDDEN_TOKENS_V1_27_3_PROVENANCE_DELTA: frozenset[str] = (
    frozenset({
        # v1.27.3 real-identity prohibitions
        "real_person_name",
        "personal_email",
        "phone_number",
        "national_id",
        "employee_id",
        # v1.27.3 compliance-claim prohibitions
        "soc2_compliance",
        "fisc_compliance",
        "iso27001_certified",
        "regulatory_attestation",
    })
)
```

### 3.3 Anti-email-leak rule

v1.27.3 storage rejects any `annotator_id_label`
containing `@` (heuristic anti-email guard).

---

## 4. Read-only readouts

### 4.1 `StrategicRelationshipReadout` (v1.27.2)

```python
@dataclass(frozen=True)
class StrategicRelationshipReadout:
    readout_id: str
    as_of_period_id: str
    relationship_ids: tuple[str, ...]
    entity_ids: tuple[str, ...]
    relationship_type_counts: tuple[tuple[str, int], ...]
    direction_counts: tuple[tuple[str, int], ...]
    reciprocal_relationship_count: int
    active_relationship_count: int
    evidence_ref_ids: tuple[str, ...]
    warnings: tuple[str, ...]
    metadata: Mapping[str, Any]
```

Counts only — no centrality score, no systemic-
importance score.

### 4.2 v1.27.3 provenance hook

The v1.24.2 `build_manual_annotation_readout` may
optionally surface `provenance_count` +
`provenance_authority_counts` when a kernel carries
`ManualAnnotationProvenanceBook`. The hook is
**non-mandatory** — every v1.24.2 test passes
without provenance.

---

## 5. Sub-milestone sequence

| Sub-milestone | Surface |
| ------------- | ------- |
| **v1.27.0** | docs only |
| v1.27.1 | StrategicRelationship storage + tests (~12) |
| v1.27.2 | StrategicRelationshipReadout + optional export + tests (~9) |
| v1.27.3 | ManualAnnotationProvenance storage + tests (~10) |
| v1.27.last | docs-only freeze |

Final test count target: ~ 5107.

---

## 6. Hard boundary (re-pinned at v1.27.0)

v1.27.0 inherits v1.26.last hard boundary verbatim
plus:

- No ownership percentage / voting power / share
  count / market value / fair value / carrying value.
- No centrality / systemic-importance / network
  score.
- No real-data adapter (EDGAR / EDINET / TDnet /
  J-Quants / FSA filing).
- No real-company relationship claim.
- No LLM-authored annotation in public v1.x.
- No real-person name / email / national-id /
  employee-id in provenance records.
- No SOC2 / FISC / ISO27001 / regulatory-
  attestation compliance claim.

The empty-by-default rule preserves every existing
fixed fixture byte-identically.

---

## 7. v1.27.last freeze (docs-only)

*Final pin section for the v1.27 sequence. v1.27.last
ships **no** new code, no new tests, no new
RecordTypes, no new dataclasses, no new label
vocabularies, no UI regions, no export-schema
changes.*

### 7.1 Shipped sequence

| Sub-milestone | Surface |
| ------------- | ------- |
| v1.27.0 | docs-only design pin |
| v1.27.1 | StrategicRelationship storage (13 tests) |
| v1.27.2 | StrategicRelationshipReadout + optional export (13 tests) |
| v1.27.3 | ManualAnnotationProvenance storage (11 tests) |
| v1.27.last | this freeze |

### 7.2 Pinned at v1.27.last

- `pytest -q`: **5113 / 5113 passing** (+37 vs v1.26.last).
- `ruff check .`: clean.
- `python -m compileall -q world spaces tests examples`:
  clean.
- All v1.21.last canonical living-world digests
  preserved byte-identical at every v1.27.x sub-
  milestone:
  - `quarterly_default` —
    `f93bdf3f4203c20d4a58e956160b0bb1004dcdecf0648a92cc961401b705897c`
  - `monthly_reference` —
    `75a91cfa35cbbc29d321ffab045eb07ce4d2ba77dc4514a009bb4e596c91879d`
  - `scenario_monthly_reference_universe` —
    `5003fdfaa45d5b5212130b1158729c692616cf2a8df9b425b226baef15566eb6`
  - v1.20.4 CLI bundle —
    `ec37715b8b5532841311bbf14d087cf4dcca731a9dc5de3b2868f32700731aaf`
- Source-of-truth book mutations from v1.27.x
  helpers: 0.
- Ledger emissions from v1.27.x helpers (other than
  the one
  `STRATEGIC_RELATIONSHIP_RECORDED` /
  `MANUAL_ANNOTATION_PROVENANCE_RECORDED` event per
  caller-initiated `add_relationship` /
  `add_provenance` call): 0.
- New `RecordType` values: 2.
- New dataclasses: 3 (`StrategicRelationshipRecord`,
  `StrategicRelationshipReadout`,
  `ManualAnnotationProvenanceRecord`).
- New tabs: 0.
- Export schema changes: 1 optional /
  omitted-when-empty field
  (`strategic_relationship_readout`).

### 7.3 Closing statement

v1.27 substrate is generic and country-neutral. It
adds the strategic relationship network +
annotation provenance hardening primitives but does
**not** ingest real data, claim any Japan
calibration, name any real company, expose any
ownership percentage / voting power / market value
/ centrality score, or carry any real-person /
compliance-claim metadata. The pseudonymous
``annotator_id_label`` + the anti-email-leak guard
keep provenance records identity-safe; the closed-
set ``RELATIONSHIP_TYPE_LABELS`` /
``DIRECTION_LABELS`` keep relationship descriptors
archetypal-only. The empty-by-default rule
preserves every existing fixed fixture byte-
identically.

The v1.27 sequence is **frozen**. v1.27 closes the
**last generic substrate addition** in public v1.x.
The next milestone is **v2.0 — Japan Public
Calibration Boundary Design** (docs-only design
pin), which begins the explicit Japan calibration
work that v1.24 / v1.25 / v1.26 / v1.27 prepared the
substrate for.
