# Japan Financial World

This package is the working area for the Japan Financial World Engine.

Design baseline:

- `docs/ontology.md`: objects that can exist in the world.
- `docs/scope.md`: v0 reproduction depth, in-scope behavior, and explicit
  non-goals.
- `docs/architecture.md`: spaces, layers, interaction rules, and scheduler
  order.
- `schemas/`: canonical YAML schemas for firms, investors, banks, markets,
  property markets, information signals, contracts, and assets.
- `world/`: orchestration and shared infrastructure.
- `data/sample/`: minimal sample firms, investors, banks, markets, assets, and
  contracts.
- `spaces/`: domain spaces for corporate, investors, banking, exchange, real
  estate, information, policy, and external macro behavior.

Implementation should follow the design docs before adding scenario-specific
logic. Cross-space effects must move through asset ownership, contracts, market
prices, information signals, or constraints.
