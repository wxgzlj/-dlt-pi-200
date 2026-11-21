# Implementation Audit — 2026-11-21

## State

- Design parameters: USER-APPROVED.
- Confirmatory cohort: 0 / 200.
- Experiment active: NO.
- Forecast commitments: 0.
- Official results audited: 0.

## Checks completed in this work session

| Check | Status | Evidence |
|---|---|---|
| 600,000-digit π computation | COMPUTED | Chudnovsky binary-splitting reproduction; SHA-256 in data/pi_600000.manifest.json |
| π known-prefix check | PASS | First 50 decimal digits match the embedded known prefix |
| π window allocation smoke test | PASS | Five draw identifiers × A/B1/B2; 2,048-digit windows; front/back separated; 10 distinct tickets per model |
| GitHub repository access | VERIFIED | Public repository; default branch main; write permission available |
| GitHub Actions CI | NOT VERIFIED | Workflow exists, but passing run/logs have not yet been inspected |
| Official history snapshot | MISSING | No committed raw snapshot/manifest or continuity audit yet |
| Power simulation | MISSING | MDE and target power approved; simulation/test implementation not yet published |
| Seed anti-reroll control | MISSING | Current generator creates a fresh OS seed on each invocation; one-seed-per-draw commitment must be implemented before activation |
| Commit–reveal integration | NOT VERIFIED | Code exists; clean round-trip and public independent-anchor test remain outstanding |

## Important implementation reconciliation

The approved design is 600,000 digits, not 1,000,000. The default in src/pi_digits.py and the forecast generator / ledger instructions has been aligned to 600,000. The actual code uses a deterministic per-draw/per-zone SHA-256 window selector; A/B1/B2 share the same windows and differ only by the declared digit transform. Documentation must continue to describe this implementation, not the earlier fixed-offset table.

The implemented C/D random stream is SHA-256 counter mode with rejection-based randbelow, not Python random.Random. The model registry and parameter record have been updated accordingly.

## Blocking defects / controls before activation

1. Prevent seed shopping. A single root seed must be committed to an independent public timestamp before generation. A second seed commitment for the same draw must be rejected. A failed generation must be recorded as a technical failure, not rerun with a replacement seed.
2. Complete the simulation-based power analysis. It must define the alternative-generation mechanism for a +0.10 front-hit MDE, draw-level paired test, confidence intervals, Holm correction and Monte Carlo error. Publish fixed seed and at least 100,000 simulations.
3. Add integration tests for complete 50-ticket generation, invalid payload rejection, duplicate commits, cutoff enforcement, commit/reveal verification and tamper detection.
4. Execute CI on the declared Python versions and inspect successful logs.
5. Retrieve the official history snapshot and audit draw IDs, dates, missing issues, duplicates, corrections, valid ranges and source hashes. Snapshot retrieval time must not be backdated.
6. Freeze exact Python patch version, runner image, code hashes, data hashes and analysis-plan hash.
7. Independently timestamp the activation record and every forecast commitment before the official draw cutoff.

No claim of predictive edge, adequate power, official history completeness, or experiment activation is made.
