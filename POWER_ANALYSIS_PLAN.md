# Power Analysis Plan — DLT-PI-200

**Status: PRELIMINARY DESIGN ANALYSIS; CONFIRMATORY TEST FREEZE PENDING.**

## 1. Fixed design inputs

- Cohort: 200 consecutive eligible draws.
- Five models; 10 distinct tickets per model per draw.
- Primary endpoint: each model's mean front hits per ticket, averaged within draw.
- Four primary comparisons: A-D, B1-D, B2-D, C-D.
- Two-sided family-wise alpha 0.05; Holm step-down correction.
- MDE: +0.10 front hits per ticket; target power 80%.
- At least 100,000 Monte Carlo replicates per scenario.

No horizon, MDE, alpha, ticket budget, or model parameter is changed by this analysis.

## 2. Reference null variance

For one ticket, front hits follow Hypergeometric(N=35, K=5, n=5):

`E[X] = 5/7`

`Var(X) = 5(5/35)(30/35)(30/34) = 0.5402160864`.

There are `C(35,5)=324,632` possible front tickets. For a reference portfolio of 10 distinct tickets sampled uniformly without replacement from that finite ticket population, the portfolio-mean variance is:

`Var(mean) = Var(X)/10 × (1 - 10/324632)`.

Assuming candidate and D portfolios are independently generated under this reference mechanism:

`SD(candidate mean - D mean) = 0.3286942183`.

This is an exact reference variance under the stated random-portfolio assumptions. It is **not** an empirical variance estimate for the deterministic π models or the frequency model C.

## 3. Test and multiplicity approximation

For planning, each comparison uses a draw-level paired Student t statistic with 199 degrees of freedom. The four p-values are adjusted using the exact Holm step-down algorithm. This is a planning approximation only; the final confirmatory inferential test (paired t, cluster bootstrap, or paired randomization) must be frozen in the preregistration before the first forecast.

The joint simulation represents four candidate-minus-D comparisons with one shared D sample mean and D residual vector. Candidate residual vectors are mutually independent in the reference model. The resulting multivariate-t construction captures the shared-control dependence under those assumptions. It does not calibrate the extra dependence among A/B1/B2 caused by their shared π windows.

## 4. Alternative and limitations

The alternative is a **draw-level location shift**: one candidate's paired difference has its mean shifted by the specified effect while the reference noise scale is retained. This is a statistical power scenario, not a physically specified lottery mechanism, not a claim that a model can create the shift, and not evidence of predictive ability.

Power is estimated for one representative candidate-versus-D comparison while the other three comparisons remain null. Model-specific powers are treated as exchangeable only for this reference scenario; actual portfolio exposure profiles may differ.

A sensitivity analysis multiplies the reference standard deviation by 1.25, 1.50 and 2.00. This directly tests how fragile the 80% target is to underestimation of portfolio-level noise.

## 5. Monte Carlo implementation

- Replicates: 100,000 per effect/noise scenario.
- PRNG: CPython `random.Random` (MT19937); preliminary run environment: CPython 3.13.5.
- Base seed: 2026112101; scenario-specific seeds are deterministic offsets from this base.
- Report: estimated power, family rejection rate, Monte Carlo standard error, and 95% Wilson Monte Carlo interval.
- The null scenario's family rejection rate is a simulation diagnostic for Holm family-wise error control; it is not a proof of control.

## 6. Preliminary results (2026-11-21)

| Mean shift | Reference-noise power | 95% Monte Carlo interval |
|---:|---:|---:|
| 0.00 | 1.374% target-comparison rejection | 1.304%–1.448% |
| 0.05 | 35.607% | 35.311%–35.904% |
| 0.10 | 96.213% | 96.093%–96.330% |
| 0.15 | 99.997% | 99.991%–99.999% |
| 0.20 | 100.000% | 99.996%–100.000% |

Under the null, the simulated family rejection rate was 4.347% (Monte Carlo SE 0.0645 percentage points; 95% Monte Carlo interval 4.222%–4.475%).

For the +0.10 MDE, power fell to:
- 82.291% (95% Wilson interval 82.053%–82.526%) when reference SD was multiplied by 1.25;
- 63.642% (95% Wilson interval 63.343%–63.940%) when multiplied by 1.50;
- 35.911% (95% Wilson interval 35.614%–36.209%) when multiplied by 2.00.

The simulation used 100,000 replicates per scenario. These are parametric planning estimates under the assumptions above.

## 7. Decision

The reference model exceeds 80% power at the registered MDE. However, a 50% increase in draw-level noise reduces power to about 64%. Because the actual deterministic A/B1/B2/C portfolios and their covariance structure have not yet been calibrated from a verified history snapshot and the frozen generator, **the experiment is not yet certified as adequately powered**.

Before activation:
1. Freeze the exact confirmatory test and confidence-interval method.
2. Generate a synthetic portfolio panel using the exact frozen A/B1/B2/C/D code, with a verified C-history snapshot and precommitted seed rules.
3. Compute model-specific draw-level exposure variance and cross-comparison covariance.
4. Re-run power analysis with those empirical design quantities and retain this reference analysis as a sensitivity benchmark.
5. Do not change the approved 200-draw horizon or +0.10 MDE if power is inadequate; report the limitation.

No predictive edge, adequate power, or economic value is established by this report.


## Automated reproduction

The repository workflow `.github/workflows/power-analysis.yml` reruns the 100,000-replicate-per-scenario analysis on CPython 3.12, runs the test file through unittest discovery, uploads the JSON artifact, and commits the generated report. The committed JSON is the canonical runtime-specific output; this document's preliminary numeric table must be reconciled to that output before the report is treated as final planning evidence.
