# Parameter Decisions — DLT-PI-200

**Status: PROPOSED — USER APPROVAL REQUIRED BEFORE FREEZE**

These defaults are concrete and reproducible, but they do not become active until the user approves them and an activation commit records the exact Git tree/code hashes.

## 1. π digit source and mapping

- Generate the first 600,000 digits after the decimal point of π with the Chudnovsky binary-splitting algorithm implemented in `src/pi_digits.py`.
- Decimal digit index 0 means the first digit immediately after the decimal point; no leading integer digit is included.
- Validate the generated prefix against the independently published π archive prefix recorded in the script.
- Block length: 6 digits, left-padded only if a block begins with zero (the source stream is fixed-width, so no actual padding operation is needed).
- Rejection thresholds: for q=35, accept z < 999,985; for q=12, accept z < 999,996.
- Map accepted z to 1 + (z mod q).
- Reject duplicate mapped numbers and advance by exactly six digits.

## 2. Fixed π digit windows

All offsets are zero-based digit indices in the decimal expansion after the decimal point. Each ticket has a 2,048-digit window. A zone may consume sequential 6-digit blocks only within its own window; window exhaustion is a hard error.

| Model | Front window start | Back window start |
|---|---:|---:|
| A | 0 + 2,048 × ticket_index | 100,000 + 2,048 × ticket_index |
| B1 | 200,000 + 2,048 × ticket_index | 300,000 + 2,048 × ticket_index |
| B2 | 400,000 + 2,048 × ticket_index | 500,000 + 2,048 × ticket_index |

ticket_index is 0 through 9. These windows are disjoint across all model/zone/ticket streams.

## 3. C model

- Frequency count is computed separately by zone from every verified official draw whose publication timestamp is strictly earlier than scheduled_cutoff_utc.
- Add-one smoothing: integer weight = count + 1.
- Sequential weighted sampling without replacement, separately by zone.
- No parameter tuning and no recency weighting.
- The exact source CSV, retrieval timestamp and SHA-256 are included in the forecast payload.

## 4. D and C random seeds

- Generate one 32-byte root seed from the operating system CSPRNG for each draw before ticket generation.
- Derive each model seed as SHA-256(root_seed_bytes || UTF8(experiment_id + "|" + draw_id + "|" + model_id)).
- Use Python 3.12.x `random.Random` only as a deterministic bit generator; implement explicit randbelow(n) using getrandbits(k) with rejection, and explicit partial Fisher–Yates.
- Record exact Python patch version, operating system, code hash and derived seed hashes.
- The full root seed is part of the pre-draw payload and therefore is committed before the draw. No re-seeding after seeing outputs.

## 5. C historical data input schema

CSV columns:
- draw_id
- published_at_utc (ISO-8601 with Z or explicit UTC offset)
- front (five space-separated integers)
- back (two space-separated integers)

Rows with invalid numbers, duplicate draw IDs, invalid timestamps, or publication timestamps at/after cutoff cause generation to fail. No silent row skipping.

## 6. Runtime and power analysis

- Runtime proposal: CPython 3.12.x; exact patch version and platform image must be frozen before activation.
- Minimum effect of interest (MDE): +0.10 mean front hits per ticket versus D.
- Target power: 80%, two-sided family-wise alpha 0.05 with four Holm-adjusted primary comparisons.
- Simulation count: at least 100,000 Monte Carlo experiments, fixed seed and reported Monte Carlo standard error.
- If estimated power is below 80% for the MDE, report the design as underpowered; do not alter the horizon after seeing results.

## 7. Explicit caveat

Even perfectly reproducible π mappings do not establish that π digits are independent or uniformly distributed. The models are tested empirically against D; they are not presumed superior. A fair draw gives every legal ticket the same probability.
