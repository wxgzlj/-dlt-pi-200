# DLT-PI-200 — China Super Lotto π Randomness Prospective Experiment

**Status: DESIGN APPROVED — IMPLEMENTATION IN PROGRESS — NOT ACTIVE**

This repository records a prospective, fixed-horizon paper experiment comparing four π-derived / historical-frequency procedures and one matched uniform-random control for China Super Lotto (大乐透). No real-money tickets are required or recommended.

- Experiment ID: `DLT-PI-200`
- Planned horizon: 200 consecutive eligible future draws
- Planned budget: 10 virtual tickets per model per draw; 50 virtual tickets total per draw
- Models: A, B1, B2, C, D
- Primary endpoint: mean front-zone hits per ticket, aggregated within draw first
- Secondary endpoint: mean back-zone hits per ticket, aggregated within draw first

## Official rule verification

Official sources confirm the 5-from-35 front zone and 2-from-12 back zone; the official calculator states a basic ticket costs RMB 2 and that the revised rules apply from draw 26014 (2026-01-31). The Ministry of Finance approved the rule change under 财综〔2025〕51号. See:
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
- `PARAMETER_DECISIONS.md`: user-approved design parameters; implementation and activation gates remain open
- `LEDGER_SCHEMA.md`: append-only commit/reveal record format
- `src/`: official history snapshot downloader/auditor, reproducible π generation, ticket generator, seed ceremony, power simulation and exact portfolio covariance diagnostics
- `POWER_ANALYSIS_PLAN.md` / `results/power_analysis_preliminary.json`: parametric power-planning assumptions and reproducible Monte Carlo output
- `PORTFOLIO_COVARIANCE.md`: exact covariance of fixed ticket portfolios under a uniform draw
- `src/audit_history.py`: raw-page/CSV integrity audit plus mandatory official draw-calendar attestation bound to a preserved raw source document/hash
- `tests/` and `.github/workflows/`: unit tests and CI workflows
- `ledger/`: per-draw commitments and post-draw reveals
- `data/`: verified rules and source metadata; do not store secrets here

## Integrity policy

Never rewrite or delete a committed forecast, reveal, or ledger entry. Corrections are new records that reference the original. Git commit history is a visible public timestamp trail, but the repository owner can still rewrite repository history; use signed tags or a second independent timestamp/backup service for stronger assurance. A SHA-256 hash proves content identity, not predictive validity.

## Current state

- Confirmatory draws completed: **0 / 200**
- Forecasts committed: **0**
- Official results audited: **0**
- Experiment active: **No**
- Seed governance: one-time seed ceremony, persistent fail-closed lock, generator checks, and ledger-layer seed/anchor validation implemented; integration tests added. External anchor authenticity is still manually verified.
- Power analysis: preliminary 100,000-replicate-per-scenario parametric report published; +0.10 MDE power is 96.213% under the idealized reference variance, but 63.642% under 1.5× noise. This does not certify adequate power.
- History audit gate: a full PASS requires the preserved raw official calendar document, its SHA-256, and an exact issue-ID/date match. The generator and commit ledger reject snapshots without this attestation.
- Portfolio covariance: exact exposure/covariance calculator and covariance-aware multivariate power mode are implemented; no real 200-payload portfolio panel has yet been generated, so model-specific power is not certified.
- Remaining blockers: obtain a fresh official history snapshot and independent official calendar evidence; publish/preserve the snapshot and evidence bundle for external review; generate the 200-payload panel including C; run model-specific covariance-aware power simulations; freeze the final inferential test; complete generator→commit→reveal→verify round-trip and tamper tests; inspect latest CI; freeze runtime; independently timestamp activation.
