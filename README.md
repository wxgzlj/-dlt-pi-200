# DLT-PI-200 — China Super Lotto π Randomness Prospective Experiment

**Status: PREREGISTRATION DRAFT — NOT YET ACTIVE**

This repository records a prospective, fixed-horizon experiment comparing four π-derived selection procedures and one matched uniform-random control for China Super Lotto (大乐透).

- Experiment ID: `DLT-PI-200`
- Planned horizon: 200 consecutive eligible future draws
- Planned budget: 10 distinct tickets per model per draw; 50 tickets total per draw
- Models: A, B1, B2, C, D
- Primary endpoint: mean front-zone hits per ticket, aggregated within draw first
- Secondary endpoint: mean back-zone hits per ticket, aggregated within draw first

## Activation gate

No draw is part of the confirmatory cohort until all of the following are complete and independently timestamped:

1. Official game rules and draw schedule are verified and recorded.
2. Model algorithms, parameters, code, dependencies, and data-source versions are frozen.
3. Statistical analysis plan and power analysis are frozen.
4. A forecast containing all 50 tickets is generated before the official cutoff.
5. The forecast commitment is published in this public repository before the draw.

The first confirmatory draw is the first eligible draw after the completed activation anchor. No historical draw, including draw 26133, may be retroactively added.

## Repository map

- `PREREGISTRATION.md`: design, endpoints, inference, exclusions, stopping rules
- `MODEL_REGISTRY.md`: model definitions and parameter freeze requirements
- `LEDGER_SCHEMA.md`: append-only commit/reveal record format
- `ledger/`: per-draw commitments and post-draw reveals
- `src/`: deterministic generation and audit implementation
- `data/`: verified rules and source metadata; do not store secrets here

## Integrity policy

Never rewrite or delete a committed forecast, reveal, or ledger entry. Corrections are new records that reference the original. Git commit history is an external timestamp anchor, but the repository owner can still rewrite repository history; use signed tags or a second independent timestamp/backup service for stronger assurance. A SHA-256 hash proves content identity, not predictive validity.

## Current state

- Confirmatory draws completed: **0 / 200**
- Forecasts committed: **0**
- Official results audited: **0**
- Experiment active: **No**
- Blockers: official rules verification; exact model parameter freeze; reproducible code and environment freeze; power analysis; activation commitment.
