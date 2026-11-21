# Exact Portfolio Covariance — DLT-PI-200

## Purpose

The power reference model assumes each candidate and D portfolio behaves like an independently sampled uniform portfolio of ten tickets. That is not guaranteed for A/B1/B2, which share π windows, or for C, which uses historical weights.

This module computes the **exact conditional first and second moments** of each fixed portfolio's front-hit score under a uniform 5-of-35 winning draw. It does not assume that the model portfolios themselves are random or independent.

## Derivation

For model m, let c_{m,i} be the number of its ten tickets containing front number i. For a winning set W of five numbers:

`S_m(W) = (1/10) × Σ_i c_{m,i} I(i∈W)`

Every ticket contains five distinct numbers, so `Σ_i c_{m,i}=50` and:

`E[S_m] = (5/35) × (50/10) = 5/7`.

For two fixed portfolios m,n, under simple random sampling of five winning numbers from 35:

`Cov(S_m,S_n) = [5×30 / (35×34×10²)] × Σ_i (c_{m,i}-c̄_m)(c_{n,i}-c̄_n)`.

For paired comparisons against D:

`Cov(S_m-S_D, S_n-S_D) = Cov(S_m,S_n)-Cov(S_m,S_D)-Cov(S_D,S_n)+Var(S_D)`.

This gives the full 4×4 covariance matrix for A-D, B1-D, B2-D and C-D, including their dependence through the shared D control and overlapping number exposures.

## Input and output

Input is one JSON forecast payload or a JSONL panel of exactly 200 payloads. Each payload must have:
- `experiment_id = DLT-PI-200`
- a non-empty, unique `draw_id`
- exactly models A, B1, B2, C, D
- ten distinct legal front tickets per model
- identical source-code, preregistration, π-source, history-snapshot, history-audit and game-rule hashes across all 200 payloads
- a PASS history-audit object whose canonical hash matches the payload

Single-payload diagnostic:

```bash
python src/portfolio_covariance.py --payload private/forecast.json --output results/one_draw_covariance.json
```

200-draw panel:

```bash
python src/portfolio_covariance.py --panel-jsonl data/simulation_portfolio_panel.jsonl --output results/portfolio_covariance.json
```

The panel analyzer verifies that the payload source-code hash matches the current `src/` tree and that the analysis-plan hash matches the current `PREREGISTRATION.md`. It rejects mixed code/data/parameter versions. The panel output includes the average per-draw paired-difference covariance and the covariance of the 200-draw mean. It also retains draw-level exposure and covariance diagnostics.

Feed the panel output into the covariance-aware power engine:

```bash
python src/power_analysis.py --portfolio-covariance results/portfolio_covariance.json --target-model A --simulations 100000 --output results/power_A.json
```

Repeat with `--target-model B1`, `B2`, and `C`. The engine uses the supplied average covariance in a multivariate-t/Wishart approximation; it does not yet model draw-to-draw covariance heterogeneity exactly.

## Verification and limitations

- The covariance formula is tested against exhaustive enumeration on a smaller finite population.
- Identical portfolios produce zero paired-difference variance, as they must.
- Duplicate tickets and duplicate/missing draw IDs are rejected.
- These are exact conditional moments **given the fixed ticket portfolios and a uniform draw mechanism**. They do not prove that any model predicts the draw, and they do not cover a biased/non-uniform lottery mechanism.
- The current Monte Carlo power engine has not yet been wired to consume this matrix. That integration and a verified C-history/synthetic 200-payload panel remain required before power adequacy can be certified.
