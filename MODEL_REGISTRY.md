# Model Registry — DLT-PI-200

**Status: MODEL FAMILIES REGISTERED; DESIGN PARAMETERS USER-APPROVED; IMPLEMENTATION FREEZE PENDING.**

Each model produces exactly 10 distinct tickets per eligible draw. Ticket format: 5 distinct front numbers (01–35) and 2 distinct back numbers (01–12).

## A — π direct mapping
- Source: decimal expansion of π generated deterministically by the Chudnovsky binary-splitting algorithm in `src/pi_digits.py`.
- Mapping block length: 6 decimal digits.
- Transform: identity.
- Rejection sampling: for q∈{35,12}, N=10^6, L=floor(N/q)×q; reject z≥L; otherwise map to 1+(z mod q).
- Duplicate mapped numbers are skipped and the stream advances.
- Per-ticket windows and front/back offsets: see PARAMETER_DECISIONS.md.

## B1 — π fixed-block reversal
- Same π digit source, 6-digit blocks, rejection sampling and per-ticket windows as A.
- Transform each block by reversing its six digits before mapping.
- No parameter tuning during the cohort.

## B2 — π digit 9-complement
- Same π digit source, 6-digit blocks, rejection sampling and per-ticket windows as A.
- Transform each digit d to 9−d before mapping.
- No parameter tuning during the cohort.

## C — historical-frequency weighted sampler
- Input: official draw-history CSV snapshot, only records published before the forecast cutoff.
- For each number i, integer weight w_i = c_i + 1, where c_i is the number of prior appearances in that zone.
- Sequential probability-proportional-to-size sampling without replacement, separately for front (5 of 35) and back (2 of 12).
- Integer weighted selection uses rejection-based randbelow; no floating-point cumulative-weight sampling.
- This is a heuristic marginal-frequency model, not a joint probability model; exploratory only.
- Data snapshot hash, source and latest included publication timestamp are stored in every forecast payload.

## D — uniform-random control
- Uniform sample without replacement for each zone.
- PRNG: SHA-256 counter stream; `randbelow(n)` uses rejection sampling and ticket selection uses partial Fisher–Yates.
- Per-draw root seed: 32 bytes from OS CSPRNG; separate derived streams for C and D.
- Per-model sub-seeds: SHA-256 of root_seed || experiment_id || draw_id || model_id.
- The root seed and derivation metadata are included in the committed payload. One-seed-per-draw public seed commitment and anti-reroll enforcement remain activation blockers.

## π stream allocation proposal
See PARAMETER_DECISIONS.md. Each ticket receives a fixed, disjoint 2,048-digit window; front and back zones occupy non-overlapping blocks. If a window is exhausted, generation fails closed; it must not silently jump to a new window.

## Common constraints
- Exactly 10 tickets per model per draw.
- No duplicate tickets within a model.
- No replacement after observing a result.
- Equal ticket budgets across all models.
- Any change creates a new experiment ID/cohort; it cannot overwrite DLT-PI-200.
