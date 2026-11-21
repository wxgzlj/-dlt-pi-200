# Decision Log — DLT-PI-200

## 2026-11-21 — User approval of proposed design

The user explicitly approved the proposed parameter set in chat.

Approved design:
- 200 consecutive eligible future draws.
- Models A, B1, B2, C and D.
- 10 distinct virtual tickets per model per draw (50 total).
- π source: first 600,000 decimal digits; six-digit blocks; 2,048-digit per-ticket windows.
- A identity mapping; B1 reverse each six-digit block; B2 digit complement d -> 9-d.
- C: historical marginal counts + 1; sequential integer weighted sampling without replacement.
- D: uniform sampling without replacement.
- Primary endpoint: mean front hits per ticket, aggregated at draw level.
- Secondary endpoint: mean back hits per ticket, aggregated at draw level.
- Four primary comparisons against D, two-sided family-wise alpha 0.05, Holm correction.
- MDE +0.10 front hits per ticket; target power 80%; at least 100,000 power simulations.
- No interim efficacy tests, early stopping, model retuning, seed shopping, or selective exclusion.

This is approval of the design, not evidence that the implementation is complete. The exact code, statistical test implementation, seed commitment mechanism, data snapshot, runtime and independent timestamp procedure remain activation gates.

The first confirmatory draw must be the first eligible draw after activation and its forecast commitment are independently timestamped before the official cutoff. Draw 26133 is excluded. No predictions have been counted toward the 200-draw cohort.
