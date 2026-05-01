# Japan Financial World (legacy directory name)

This package is the working area for the Financial World Engine. The
top-level repository README at the root is the authoritative entry point;
see it for the project layers (FWE Core / FWE Reference / JFWE Public /
JFWE Proprietary), the disclaimer, and the v0 / v1 freeze status. The
`japan-financial-world/` directory name is preserved for legacy reasons
and is not a calibration claim — see
[`docs/naming_policy.md`](docs/naming_policy.md).

Design baseline:

- `docs/world_model.md`: constitutional design log; every milestone
  has a section. **Start here.**
- `docs/v0_release_summary.md`, `docs/v1_release_summary.md`: what
  each freeze actually delivered.
- `docs/architecture_v0.md`, `docs/architecture_v1.md`: text diagrams
  of the kernel and the v1 books / orchestrator.
- `docs/v0_scope.md`, `docs/v1_scope.md`: in / out scope per freeze.
- `docs/ontology.md`, `docs/architecture.md`, `docs/scope.md`:
  long-term ontology / architecture / scope ambition (carries Japan
  framing as a *future* target — see banners at the top of each).
- `schemas/`: canonical YAML schemas for firms, investors, banks, markets,
  property markets, information signals, contracts, and assets.
- `world/`: kernel + v1 reference layer code.
- `data/sample/`: synthetic sample firms, investors, banks, markets,
  assets, and contracts. Illustrative; not calibrated.
- `spaces/`: domain spaces for corporate, investors, banking, exchange, real
  estate, information, policy, and external.

Implementation follows the design docs before adding scenario-specific
logic. Cross-space effects must move through asset ownership, contracts,
market prices, information signals, or constraints.
