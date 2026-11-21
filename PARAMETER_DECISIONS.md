# Parameter Decisions — DLT-PI-200

**Status: USER-APPROVED DESIGN PARAMETERS — IMPLEMENTATION FREEZE PENDING**

User approval recorded: 2026-11-21 (Asia/Shanghai). This approves the proposed experimental design below. It does not activate the experiment. Code, tests, power analysis, data audit, and external timestamp procedure must still pass.

## 1. π digit source and mapping

- Generate the first **600,000 decimal digits after the decimal point** of π with the Chudnovsky binary-splitting algorithm in `src/pi_digits.py`.
- Digit index 0 is the first digit after the decimal point; the leading integer digit 3 is excluded.
- Verify the generated prefix against the independent known prefix embedded in the generator.
- Fixed block length: 6 decimal digits. Leading zeros remain significant because every block is exactly six characters.
- For zone size q, let L = floor(10^6/q) × q. For q=35, L=999,985; for q=12, L=999,996.
- Reject z >= L. Otherwise map to 1 + (z mod q).
- Reject duplicate mapped numbers and continue to the next six-digit block.
- A 2,048-digit window is assigned to each ticket and each zone. Exhaustion is a hard error; no fallback window is allowed.

## 2. Deterministic π window allocation

- Split the 600,000-digit stream into two non-overlapping halves of 300,000 digits: first half for front, second half for back.
- For each draw and zone, compute SHA-256 of UTF-8 `DLT-PI-200|draw_id|ZONE`; interpret the digest as an unsigned big-endian integer and take modulo (300,000 - 20,480 + 1) to select the zone's starting offset within its half.
- Ticket i (0–9) receives the consecutive 2,048-digit window beginning at start + 2,048 × i.
- A, B1 and B2 use exactly the same windows for the same draw and ticket index. They differ only by transformation:
  - A: identity.
  - B1: reverse each six-digit block.
  - B2: replace each digit d with 9-d.
- Front and back streams are disjoint by construction. Ticket windows within each zone do not overlap.

## 3. C model

- Use every row in one verified official history snapshot whose retrieval has fully completed strictly before the forecast cutoff. The field `snapshot_retrieved_at_utc` is a conservative snapshot-availability proxy, not the original per-draw publication timestamp.
- Compute marginal appearance counts separately for front and back zones.
- Integer weight for number i is count(i)+1.
- Sequential probability-proportional-to-size sampling without replacement; select with integer cumulative weights and rejection-based randbelow. No floating-point weighting.
- No recency weighting, parameter tuning, or test-set feedback.
- Include the exact CSV SHA-256, snapshot-completion time, row count, and timestamp policy in every forecast payload.
- The snapshot completion time is a conservative availability proxy; all pages must be retrieved before cutoff, and the timestamp cannot be backdated. A separate official draw-calendar attestation must preserve the raw official calendar document and its SHA-256, and exactly reconcile the snapshot's issue IDs and dates before the audit can return PASS. Completeness and issue continuity must be audited separately.

## 4. C/D deterministic random stream and seed governance

- Runtime generator: SHA-256 counter stream, not Python's `random.Random`. Each block is SHA-256(seed_bytes || 8-byte big-endian counter).
- `randbelow(n)` uses rejection sampling; sampling without replacement uses partial Fisher–Yates for D and integer weighted selection for C.
- A single 32-byte root seed is used per draw. Model seeds are SHA-256(root_seed_bytes || UTF-8(experiment_id|draw_id|model_id)).
- The seed, its derivation, and all resulting tickets are inside the committed forecast payload; the nonce is separate and secret until reveal.
- **Seed-shopping control is an activation blocker:** the root seed must be generated once, its SHA-256 commitment must be independently timestamped before generation, and the protocol must reject a second seed commitment for the same draw. A failed generation is recorded as a technical failure; it cannot be rerun with a replacement seed.
- No reroll, seed replacement, or selective regeneration is permitted.

## 5. Runtime and reproducibility

- CI currently targets CPython 3.11 and 3.12. Before activation, freeze the exact patch version and runner image in the activation record.
- Record Python version, OS/runner image, all source-code hashes, parameter-file hash, history snapshot hash, π file hash, and analysis-plan hash.
- The generator and audit scripts must be standard-library-only unless any added dependency is explicitly frozen and hashed.

## 6. Primary analysis and power design

- Horizon: 200 consecutive eligible future draws; no interim efficacy testing and no early stopping.
- Five models A/B1/B2/C/D; exactly 10 distinct tickets per model per draw; 50 virtual tickets per draw.
- Primary endpoint: per-draw mean front-zone hits per ticket; inferential unit is the draw, not the individual ticket.
- Secondary endpoint: per-draw mean back-zone hits per ticket.
- Four primary pairwise comparisons: A-D, B1-D, B2-D, C-D; two-sided family-wise alpha 0.05; Holm correction.
- Secondary family: same four comparisons for back-zone hits, separately Holm-adjusted.
- Minimum effect of interest (MDE): +0.10 front hits per ticket versus D.
- Target power: 80%.
- At least 100,000 Monte Carlo experiments, with fixed published simulation seed and reported Monte Carlo standard error.
- Power analysis must model paired draw-level differences and within-draw dependence. Its alternative-generation mechanism, test statistic, confidence interval method, and Holm implementation must be documented and tested before activation.
- If estimated power is below 80% for the MDE, report the 200-draw design as underpowered. Do not extend the cohort or change MDE after seeing outcomes.

## 7. Interpretation guardrails

- π is deterministic; base-10 normality of π is unproved. This experiment cannot prove π normality.
- Under a fair draw, every legal combination has equal probability. The registered models are empirical candidates, not presumed superior.
- Failure to beat D means **NO EVIDENCE OF EDGE**.
- Hit counts do not establish profit. Without official payout, ticket-cost, player-choice and prize-sharing data, report `EV_NOT_IDENTIFIABLE`.

## 8. Remaining activation blockers

1. Implement seed commitment and one-seed-per-draw enforcement.
2. Resolve the analysis plan and implement reproducible power simulation and draw-level inference.
3. Run all unit/integration tests in a clean CI environment and inspect passing logs.
4. Download the official history snapshot; audit issue continuity, duplicates, corrections and source provenance.
5. Verify π generator at the full 600,000-digit target and publish the resulting SHA-256.
6. Freeze exact runtime, dependencies and code hashes.
7. Verify commit/reveal round-trip and independent timestamp anchoring.
8. Publish the activation commit and first pre-cutoff forecast commitment.

Until every blocker is closed, status remains **DRAFT — NOT ACTIVE**.
