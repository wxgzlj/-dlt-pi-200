# Model Registry — DLT-PI-200

**Status: MODEL FAMILIES REGISTERED; EXACT PARAMETERS NOT YET FROZEN.**

All models produce exactly 10 distinct tickets per eligible draw. A ticket is 5 distinct front numbers (01–35) plus 2 distinct back numbers (01–12), subject to official rules verification.

## A — π direct mapping

- Transform: identity decimal digit blocks.
- Mapping: rejection sampling, not naive modulo.
- For modulus q and m-digit integer z, N=10^m and L=floor(N/q)×q. Reject z≥L; otherwise map to 1+(z mod q).
- Repeated numbers are rejected and the stream advances; record every consumed digit offset, rejection and duplicate.
- Front/back streams must use disjoint, frozen π digit intervals.
- Exact π source representation, digit indexing convention, block length, starting offsets, and ticket-stream allocation: **MISSING; must freeze before activation**.

## B1 — π fixed-block reversal

- Reverse the digits within each fixed-length block, then apply A's rejection-sampling map.
- Block length, π source intervals, offsets and ticket allocation: **MISSING; must freeze before activation**.
- Register as a separate model; do not tune on test outcomes.

## B2 — π digit 9-complement

- Replace each decimal digit d with 9−d, then apply A's rejection-sampling map.
- π source intervals, offsets, block length and ticket allocation: **MISSING; must freeze before activation**.
- Register as a separate model; do not tune on test outcomes.

## C — Historical-frequency weighted sampler (exploratory)

- Uses only official draws whose publication timestamps precede the forecast cutoff.
- A candidate smoothed marginal weight is p_i=(c_i+a)/(T+a+b), with declared smoothing parameters a,b.
- Sampling without replacement requires a fully specified algorithm; marginal weights alone do not define a joint distribution.
- Exact features, smoothing parameters, sampling algorithm, historical data source, cutoff policy and snapshot hash: **MISSING; must freeze before activation**.
- C is exploratory in rationale but remains one of the registered prospective comparisons; do not retune during the cohort.

## D — Uniform-random control

- Uniformly sample 5 distinct front numbers from 01–35 and 2 distinct back numbers from 01–12.
- Record PRNG name/version, language/runtime, seed, substream, and code hash.
- Seed is committed before the draw and never regenerated due to unfavorable output.
- Exact PRNG, seed derivation, substream separation and implementation: **MISSING; must freeze before activation**.

## Common constraints

- Exactly 10 tickets per model per draw.
- No duplicates within each model's 10 tickets.
- No replacement or regeneration after seeing any draw result.
- All models receive equal ticket budgets.
- All source data and code versions are hashed and preserved.
- Any change creates a new experiment ID/cohort; it cannot overwrite DLT-PI-200.
