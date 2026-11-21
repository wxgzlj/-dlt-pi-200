# DLT-PI-200 Preregistration

**Status: DESIGN APPROVED — NOT ACTIVE.** The user approved the design parameters on 2026-11-21 (Asia/Shanghai). Exact implementation, statistical analysis, data and timestamp gates remain open; approval is not activation.

## 1. Research question

This is a virtual-ticket paper experiment. No real-money purchase is part of the protocol.

Do registered π-derived procedures A, B1, B2, or historical-frequency procedure C outperform a matched uniform-random control D in front-zone hits per ticket on future China Super Lotto draws?

This tests prospective predictive performance. It does not prove π is normal or a source of independent randomness.

## 2. Official game specification

The official Sports Lottery rules specify 5 distinct front numbers from 01–35 and 2 distinct back numbers from 01–12. Basic ticket price is RMB 2. The 2026 rule revision was approved by the Ministry of Finance and took effect from draw 26014 (2026-01-31).

Sources:
- Official rules page: https://m.lottery.gov.cn/ksjz/m/yxgz_dlt/
- Ministry of Finance approval, 财综〔2025〕51号: https://www.mof.gov.cn/gp/xxgkml/zhs/202601/t20260116_3982042.htm
- Sports Lottery Center rule-change notice: https://www.gstc.org.cn/newsDetail/010600/77722

Under this 5/35 + 2/12 format:
- Valid combinations: C(35,5) × C(12,2) = 21,425,712.
- Jackpot probability for one distinct ticket under a fair draw: 1 / 21,425,712.
- Expected front hits per ticket: 5/7 = 0.7142857.
- Expected back hits per ticket: 1/3 = 0.3333333.

Prize-tier/payout analysis is outside the primary endpoint and requires the current official prize schedule and draw-specific payout records. No ROI or expected-value claim is permitted without those data and player-choice / prize-sharing inputs.

## 3. Cohort and budget

- Experiment ID: DLT-PI-200.
- Horizon: 200 consecutive eligible future draws, beginning with the first eligible draw after the activation commitment is independently timestamped.
- Five models: A, B1, B2, C, D.
- Ten distinct tickets per model per draw; 50 tickets per draw.
- No model receives extra tickets, replacement seeds, or selective reruns.
- No historical draw is part of the confirmatory cohort.
- Draw 26133 is excluded because no complete pre-draw five-model forecast and independent commitment was recorded.

The official draw calendar must be archived at activation. Every scheduled draw remains in the ledger with explicit status. Cancelled/postponed/missing draw treatment must follow a frozen rule; no silent substitution or deletion.

## 4. Approved design parameters

The approved parameter set is recorded in DECISION_LOG.md and PARAMETER_DECISIONS.md. The current code and documents must be reconciled to this specification; the activation commit must freeze the final code and runtime hashes.

## 5. Endpoints

### Primary
For each draw and model, calculate the mean front-zone matches across the model's 10 tickets. Compare A-D, B1-D, B2-D and C-D using paired draw-level differences. The inferential unit is the draw, not the individual ticket.

### Secondary
Mean back-zone matches per ticket, aggregated within draw first. Analyze as a separate family with Holm correction.

### Descriptive
Full hit-count distributions, ticket duplication, number exposure, and portfolio overlap. Portfolio diversity is not predictive advantage.

## 6. Confirmatory tests

- Four primary comparisons: A-D, B1-D, B2-D, C-D.
- Two-sided family-wise alpha = 0.05.
- Holm step-down correction across four primary comparisons.
- Secondary back-zone family: same four comparisons, separately Holm-adjusted.
- Report paired effect sizes, 95% confidence intervals, raw p-values and adjusted p-values.
- Use a draw-cluster paired randomization test or draw-cluster bootstrap; exact implementation must be frozen before activation.
- No interim efficacy testing and no early stopping.

## 7. Power analysis — activation blocker

The 200-draw horizon is fixed, but adequacy is not assumed. Before activation, run reproducible simulation-based power analysis for a predeclared minimum effect of interest, using draw-level paired endpoints, four-comparison Holm correction, and realistic within-draw ticket dependence. Publish code, PRNG, seed, simulation count, Monte Carlo error and power curve.

Approved minimum effect of interest: +0.10 mean front-zone hits per ticket versus D. Approved target power: 80%. Run at least 100,000 Monte Carlo experiments with a fixed published simulation seed. These are design targets, not achieved power; do not describe the study as adequately powered until the simulation and its assumptions are implemented, run, and published.

## 8. Data and verification

Every result must preserve draw ID, date, front/back numbers, official source URL, retrieval time UTC, raw source snapshot and SHA-256. Status values: VERIFIED / USER_SUPPLIED_PENDING_VERIFICATION / MISSING / CORRECTED.

For model C, each forecast must include a historical data snapshot hash and prove every included draw was officially published before the forecast cutoff. No future result, post-cutoff correction, or incomplete record may enter the feature history.

## 9. Commit–reveal

Before each draw cutoff:
1. Generate all 50 tickets with frozen code and parameters.
2. Validate exact counts, number ranges, within-zone uniqueness and within-model ticket uniqueness.
3. Serialize canonical UTF-8 JSON with sorted keys and compact separators.
4. Generate a cryptographically random 32-byte nonce.
5. Compute SHA-256 over canonical payload bytes concatenated with raw nonce bytes.
6. Publish commitment and payload hash in this repository before cutoff.
7. Preserve payload and nonce; reveal only after official result publication.

After result publication, append official source metadata, reveal payload and nonce, recompute the commitment, and score every ticket. Never replace a commitment. GitHub alone is not a fully independent immutable archive; mirror each commitment to a second timestamp / append-only service.

## 10. Missingness and deviations

All scheduled cohort rows remain visible. Missing, delayed, cancelled, postponed, corrected or unavailable results receive explicit statuses. No draw may be silently removed or replaced. Any deviation is logged as a new event with reason and affected draw.

## 11. Decision language

Use one of:
- NO EVIDENCE OF EDGE
- EXPLORATORY SIGNAL ONLY
- OUT-OF-SAMPLE EDGE DETECTED BUT NOT ECONOMICALLY VALIDATED
- ECONOMIC VALUE SUPPORTED UNDER STATED ASSUMPTIONS

Economic value additionally requires official ticket costs, prize tiers, payouts, prize-pool allocation, and defensible player-choice distribution. Otherwise: EV_NOT_IDENTIFIABLE.

## 12. Activation checklist

- [x] User approves proposed exact design parameters
- [ ] Official rules and draw schedule archived
- [ ] Complete historical result dataset verified for C
- [ ] π digit generator and source prefix test pass
- [ ] D/C seed derivation, PRNG implementation and one-seed-per-draw anti-reroll control frozen
- [ ] Generator/auditor code and runtime frozen
- [ ] Minimum effect and target power declared
- [ ] Power analysis published
- [ ] Statistical test implementation frozen
- [ ] Canonicalization test vectors pass
- [ ] Activation commit SHA recorded
- [ ] First forecast committed and independently timestamped before cutoff

Until complete: DRAFT — NOT ACTIVE.


### Preliminary power result — does not close the activation gate

A parametric reference power analysis is now published in `POWER_ANALYSIS_PLAN.md` and `results/power_analysis_preliminary.json`. It ran 100,000 Monte Carlo replicates per scenario using the registered 200-draw horizon, +0.10 MDE and four-comparison Holm procedure. Under the idealized independent-uniform-portfolio variance reference, estimated target-comparison power was 96.213%. With 1.50× reference noise, it fell to 63.642%.

This is **not** certification that DLT-PI-200 is adequately powered: the deterministic A/B1/B2 portfolios share π windows, and the actual C/D portfolio exposure covariance has not been calibrated. The confirmatory test and confidence-interval method also remain to be frozen. The power-analysis activation checklist item therefore remains open.
