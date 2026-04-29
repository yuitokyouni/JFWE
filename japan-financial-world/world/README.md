# World

World infrastructure files:

```text
world/
  ids.py
  registry.py
  clock.py
  scheduler.py
  ledger.py
  state.py
  loader.py
  validation.py
```

`world/` owns orchestration and shared infrastructure. It does not contain
sector-specific behavior and does not contain ad hoc event modules.

## File Roles

- `ids.py`: deterministic ID generation.
- `registry.py`: shared object registry.
- `clock.py`: daily, monthly, quarterly, and yearly clock.
- `scheduler.py`: ordered space execution.
- `ledger.py`: append-only transition records.
- `state.py`: shared world state snapshots.
- `loader.py`: YAML sample-world loader.
- `validation.py`: lightweight validation helpers.

Domain behavior belongs in top-level `spaces/`.
