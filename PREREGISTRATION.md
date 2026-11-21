# DLT-PI-200 Preregistration

**Status: DRAFT — NOT ACTIVE.** This document is the proposed protocol. It becomes frozen only after the activation commit explicitly identifies its Git commit SHA and the required supporting artifacts.

## 1. Research question

Do the registered π-derived procedures A, B1, B2, or historical-frequency procedure C outperform a matched uniform-random control D in the number of front-zone hits per ticket on future China Super Lotto draws?

This is a test of prospective predictive performance, not a test proving π is normal or a source of independent randomness.

## 2. Game and baseline

Planned game format: 5 distinct front numbers from 01–35 and 2 distinct back numbers from 01–12. This format and the current official rules/prize schedule must be verified against an authoritative lottery source before activation.

Under the stated fair-draw format:
- Valid combinations: C(35,5) × C(12,2) = 21,425,712.
- Jackpot probability for one distinct ticket: 1 / 21,425,712.
- Expected front hits per ticket: 5/7 = 0.7142857.
- Expected back hits per ticket: 1/3 = 0.3333333.

These are mathematical baselines conditional on the stated game format and fair independent draws, not observed model performance.

## 3. Cohort and budget

- Experiment ID: DLT-PI-200.
- Horizon: 200 consecutive eligible future draws, beginning with the first eligible draw after the activation commitment has been independently timestamped.
- Five models: A, B1, B2, C, D.
- Ten distinct tickets per model per draw; 50 tickets per draw.
- No model receives extra tickets, replacement seeds, or selective reruns.
- No historical draw is part of the confirmatory cohort.
- Draw 26133 is excluded from the prospective cohort because no complete pre-draw five-model forecast and independent commitment was recorded.

The scheduled draw register must be populated from the official calendar at activation. Postponed, cancelled, delayed, corrected, or unavailable draws remain in the register with explicit statuses; no silent substitution or deletion is allowed. The exact calendar extension rule must be frozen before activation.

## 4. Models

See MODEL_REGISTRY.md. Exact algorithm parameters, source intervals, random seeds, software versions, and code hashes remain activation blockers until specified and committed.

## 5. Endpoints

### Primary endpoint
For each draw and model, calculate the mean number of front-zone matches across that model's 10 tickets. Compare each of A/B1/B2/C against D using paired draw-level differences. The inferential unit is the draw, not the individual ticket.

### Secondary endpoint
Mean back-zone matches per ticket, aggregated within draw first. Analyze as a separate family with Holm correction.

### Descriptive endpoints
- Full match-count distributions by zone
- Prize-tier counts, only after official prize rules are verified
- Number of unique tickets within each model
- Number of unique tickets across all models
- Any-prize frequency, clearly descriptive and not equivalent to profitability

## 6. Confirmatory tests

- Four primary comparisons: A-D, B1-D, B2-D, C-D.
- Two-sided family-wise alpha = 0.05.
- Holm step-down correction across the four primary comparisons.
- Secondary back-zone family: same four comparisons, separately Holm-adjusted.
- Report paired effect sizes, 95% confidence intervals, raw p-values, adjusted p-values, and all draw-level observations.
- Use a draw-cluster paired randomization test or draw-cluster bootstrap; specify and freeze the exact implementation before activation.
- Do not treat the 10 tickets within a draw as independent observations.
- No interim efficacy testing and no early stopping for apparent success or failure.

## 7. Power analysis — required before activation

A 200-draw horizon is fixed by design, but sufficiency is not assumed. Before activation, run reproducible simulation-based power analysis for a predeclared minimum effect of interest, using the draw-level endpoint, four-comparison multiplicity correction, and plausible within-draw dependence. Publish the code, PRNG, seed, simulation count, Monte Carlo standard error, and results. If power is low, retain the 200-draw design and label it underpowered rather than silently changing the horizon or endpoint.

The minimum effect of interest and power target must be declared before activation. They are currently **MISSING**.

## 8. Data and verification

For every official result preserve:
- draw ID and scheduled/actual draw date
- front and back results
- official source URL and retrieval timestamp (UTC)
- raw response or source-file snapshot
- SHA-256 of the raw snapshot
- status: VERIFIED / USER_SUPPLIED_PENDING_VERIFICATION / MISSING / CORRECTED
- correction history, if any

User-pasted results remain USER_SUPPLIED_PENDING_VERIFICATION until independently matched to an authoritative official source.

## 9. Commit–reveal procedure

Before each draw cutoff:
1. Generate all 50 tickets in one run using frozen code and parameters.
2. Validate ticket counts, number ranges, within-zone uniqueness, and within-model ticket uniqueness.
3. Create canonical UTF-8 JSON with sorted keys and compact separators.
4. Generate a cryptographically random 32-byte nonce.
5. Compute SHA-256 over canonical JSON bytes concatenated with nonce bytes, according to the exact encoding specified in LEDGER_SCHEMA.md.
6. Publish the commitment and payload-file hash in this public repository before cutoff.
7. Keep payload and nonce unavailable for editing; reveal only after the official result is published.

After the official result:
1. Add official result metadata and source snapshot hash.
2. Reveal the exact payload and nonce.
3. Recompute and verify the commitment.
4. Score every ticket and report all models.
5. Append a new audit record; never replace the commitment.

GitHub public commits provide a visible timestamped trail but are not a fully independent immutable archive because repository history can be rewritten by an administrator. For stronger anchoring, mirror each commitment to a second independent timestamp service or public append-only system before the draw.

## 10. Missingness, corrections, and deviations

All scheduled cohort rows remain visible. Missing/cancelled/postponed results are not silently dropped or replaced. Any protocol deviation is logged with date, reason, affected draw, and impact. No retroactive forecast generation, seed shopping, parameter tuning, or selective exclusion is permitted.

## 11. Decision language

Final conclusions must use one of:
- NO EVIDENCE OF EDGE
- EXPLORATORY SIGNAL ONLY
- OUT-OF-SAMPLE EDGE DETECTED BUT NOT ECONOMICALLY VALIDATED
- ECONOMIC VALUE SUPPORTED UNDER STATED ASSUMPTIONS

The final label requires complete data, multiplicity-adjusted evidence, robust draw-level inference, and independent validation. Economic value additionally requires official ticket costs, prize tiers, payouts, prize-pool allocation, and defensible player-choice distribution. Without these, mark EV_NOT_IDENTIFIABLE.

## 12. Activation checklist

- [ ] Official game rules verified and archived
- [ ] Official draw schedule verified and archived
- [ ] Model parameters fully specified
- [ ] π source and digit offsets frozen; source hash recorded
- [ ] Historical dataset and cutoff rules for C frozen
- [ ] D PRNG, software version, seed-generation protocol and substreams frozen
- [ ] Generator/auditor code and dependencies frozen
- [ ] Code hash and environment manifest recorded
- [ ] Minimum effect of interest and power target declared
- [ ] Power analysis published
- [ ] Statistical test implementation frozen
- [ ] Ledger schema and canonicalization test vectors published
- [ ] Activation commit SHA recorded
- [ ] First draw forecast committed and independently timestamped before cutoff

Until every required item is checked, status remains DRAFT — NOT ACTIVE.
