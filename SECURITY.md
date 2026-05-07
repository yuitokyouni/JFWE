# Security and Public-Repo Hygiene

This document covers two related concerns:

1. **Security reporting.** How to responsibly report a vulnerability.
2. **Public-repo hygiene.** What may and may not appear in this
   repository, given that JFWE is intended as a public research-software
   project layered with a separate private calibration repository.

The hygiene rules below are reinforced by
[`japan-financial-world/docs/public_private_boundary.md`](japan-financial-world/docs/public_private_boundary.md);
this document is the operational summary.

## Reporting a vulnerability

This is research software, not a production service, but if you find
a security-relevant issue (sandbox escape via the YAML loader, code
execution via crafted input, accidental credential leak in repo
history, etc.), please:

1. **Do not open a public GitHub issue** for the vulnerability itself.
2. Email the maintainer directly with: a short description, reproduction
   steps, the affected commit hash, and (optionally) a suggested fix.
3. Allow a reasonable triage window (target: 14 days for an
   acknowledgement) before any public disclosure.

For non-security issues — bugs, design questions, milestone proposals
— public GitHub issues are fine.

## Public-repo hygiene rules

The following rules apply to **every commit on every branch** of this
repository. These are not aspirational; a commit that violates them
should be reverted.

### Never commit

- **Private calibration data.** Vendor-licensed feeds (Bloomberg,
  Refinitiv, QUICK, paid news), fund-level holdings beyond public
  disclosures, paid analyst datasets, expert-curated parameter sets.
  These belong in a separate, private calibration repository.
- **PII.** Names, emails, phone numbers, addresses, account numbers,
  ID numbers, or any other personally identifying information for any
  individual. The project tracks no individuals.
- **Expert interview notes (OB notes / NDA-restricted material).**
  Verbatim transcripts, paraphrased summaries, attributable quotes,
  or de-anonymizable observations from expert interviews. These belong
  in a private storage layer that the public code does not import.
- **Named-institution stress results.** "Bank A's losses under
  scenario S," counterparty-network visualizations with real names,
  sensitivity tables ranked by named institution. Public auditable
  traces tied to named institutions are off-limits in this repo,
  regardless of provenance.
- **Client reports or client-specific scenarios.** Anything authored
  for a specific client, including the existence of the relationship.
- **Credentials, API keys, tokens, or secrets** of any kind, even
  expired ones. The repository's git history is part of the public
  surface; deleting a leaked secret in HEAD does not remove it from
  the history.
- **Real ticker codes or real-firm identifiers** in synthetic example
  data. The reference layer must use `firm:reference_*`,
  `bank:reference_*`, etc. Real names are reserved for v2 (public
  calibration) or v3 (proprietary calibration), and even there, v3
  content does not land in this repo.

### May commit, with care

- **Public data source identifiers** (BOJ, FSA, MOF, MLIT, JPX, TSE,
  EDINET, TDnet) — *only* when the doc is explicitly describing what
  v2 will populate or what v1 deliberately avoids. Never as a present-
  day capability claim. Never with implied calibration.
- **License-clean public datasets** — the v2 milestone may introduce
  some, but every source must have a license review on file (see
  [`japan-financial-world/docs/v2_readiness_notes.md`](japan-financial-world/docs/v2_readiness_notes.md)).
- **Synthetic example data** — fictional firms, banks, investors, and
  markets, scaled to plausible-but-not-real numbers. Currency codes
  may appear (`JPY`, `USD`, etc.) but should not be presented as a
  Japan calibration claim.

## Public / private separation pattern

The intended pattern is:

```
PUBLIC repository (this one — JFWE on GitHub)
   FWE Core code (world/, spaces/)
   FWE Reference (planned synthetic demo)
   Tests, docs, schemas, synthetic examples
                  │
                  │  read-only dependency
                  ▼
PRIVATE repository (separate, not yet created)
   JFWE Public calibration code that depends on licensed sources
   JFWE Proprietary code, paid data, expert overrides,
       client templates, named-institution work
```

The private repository may import or depend on the public one; the
public repository must not import, reference by path, or otherwise
require the private one. The public repo must continue to build,
test, and run with the private layer absent.

## Secret scanning before public releases

Before tagging a release that will be advertised externally:

1. Run a secret scanner over the working tree and the full commit
   history (e.g., `gitleaks`, `trufflehog`, or GitHub's built-in
   secret scanning). Investigate every hit; do not assume false
   positives without checking.
2. If a real secret is found in history, treat it as compromised:
   rotate the credential at its source, then rewrite history (or
   accept the leak and document the rotation). Removing a secret
   from the working tree alone is insufficient.
3. Confirm `.gitignore` covers any local override files that may
   contain credentials (e.g., `.env`, `local_settings.py`,
   `secrets.toml`). The repository should not require these files
   to run; if it does, that is a bug.
4. Spot-check the most recent commits for accidental large binary,
   data, or notebook output drops.

The [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) at repo root
codifies this as a run-before-release list.

## Take-down policy

If you believe content in this repository violates the rules above
(e.g., a leaked secret, accidentally committed expert notes, a
real-institution claim), please email the maintainer with the file
and commit hash. The project will:

1. Confirm the violation.
2. Remove the content from HEAD.
3. Decide on a per-case basis whether to rewrite history (for severe
   violations) or accept the historical record (for minor ones).
4. Update this document or the public / private boundary doc if the
   violation revealed an unclear rule.
