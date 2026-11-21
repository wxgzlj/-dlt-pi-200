# DLT-PI-200 — China Super Lotto π Randomness Prospective Experiment

**Status: PREREGISTRATION DRAFT — NOT YET ACTIVE**

This repository records a prospective, fixed-horizon experiment comparing four π-derived / historical-frequency procedures and one matched uniform-random control for China Super Lotto (大乐透).

- Experiment ID: `DLT-PI-200`
- Planned horizon: 200 consecutive eligible future draws
- Planned budget: 10 distinct tickets per model per draw; 50 tickets total per draw
- Models: A, B1, B2, C, D
- Primary endpoint: mean front-zone hits per ticket, aggregated within draw first
- Secondary endpoint: mean back-zone hits per ticket, aggregated within draw first

## Official rule verification

The official game-rule page states 5 numbers from 01–35 and 2 numbers from 01–12, with 2 RMB per basic ticket; the Ministry of Finance approval and the Sports Lottery Center's January 16, 2026 notice establish that revised rules took effect from draw 26014. See:
- https://m.lottery.gov.cn/ksjz/m/yxgz_dlt/
- https://www.mof.gov.cn/gp/xxgkml/zhs/202601/t20260116_3982042.htm
- https://www.gstc.org.cn/newsDetail/010600/77722

The exact current prize schedule and any add-on / payout mechanics must be archived before any economic-value analysis. This experiment's primary and secondary endpoints are hit counts, not payout or profit.

## Activation gate

No draw is part of the confirmatory cohort until all of the following are complete and independently timestamped:

1. Official game rules and draw schedule are verified and archived.
2. Model algorithms, parameters, code, dependencies, and data-source versions are frozen.
3. Statistical analysis plan and power analysis are frozen.
4. A forecast containing all 50 tickets is generated before the official cutoff.
5. The forecast commitment is published in this public repository before the draw.

The first confirmatory draw is the first eligible draw after the completed activation anchor. No historical draw, including draw 26133, may be retroactively added.

## Repository map

- `PREREGISTRATION.md`: design, endpoints, inference, exclusions, stopping rules
- `MODEL_REGISTRY.md`: model definitions and parameter freeze requirements
- `LEDGER_SCHEMA.md`: append-only commit/reveal record format
- `src/`: reproducible π generation, ticket generation and scoring
- `ledger/`: per-draw commitments and post-draw reveals
- `data/`: verified rules and source metadata; do not store secrets here

## Integrity policy

Never rewrite or delete a committed forecast, reveal, or ledger entry. Corrections are new records that reference the original. Git commit history is a visible public timestamp trail, but the repository owner can still rewrite repository history; use signed tags or a second independent timestamp/backup service for stronger assurance. A SHA-256 hash proves content identity, not predictive validity.

## Current state

- Confirmatory draws completed: **0 / 200**
- Forecasts committed: **0**
- Official results audited: **0**
- Experiment active: **No**
- Blockers: final parameter approval; reproducible code/environment freeze; complete official historical draw snapshot for C; power analysis; activation commitment.
