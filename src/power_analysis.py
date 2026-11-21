#!/usr/bin/env python3
"""Parametric Monte Carlo power analysis for DLT-PI-200.

This is design planning, not a backtest or a claim of predictive information.
It calibrates draw-level paired noise to the exact variance under independently
uniform 10-ticket portfolios, then applies a predeclared location-shift
alternative. Actual deterministic portfolio covariance is not yet calibrated.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import math
import platform
import random
from pathlib import Path

N_DRAWS = 200
TICKETS_PER_MODEL = 10
FRONT_N = 35
FRONT_DRAW = 5
TICKET_COMBINATIONS = math.comb(FRONT_N, FRONT_DRAW)
ALPHA = 0.05
N_COMPARISONS = 4
MDE = 0.10
DEFAULT_SEED = 2026112101
EFFECT_GRID = (0.00, 0.05, 0.10, 0.15, 0.20)


def ticket_front_hit_variance() -> float:
    p = FRONT_DRAW / FRONT_N
    return FRONT_DRAW * p * (1.0 - p) * ((FRONT_N - FRONT_DRAW) / (FRONT_N - 1))


def paired_difference_sd() -> float:
    v_ticket = ticket_front_hit_variance()
    fpc = 1.0 - TICKETS_PER_MODEL / TICKET_COMBINATIONS
    v_portfolio_mean = v_ticket / TICKETS_PER_MODEL * fpc
    return math.sqrt(2.0 * v_portfolio_mean)


def _betacf(a: float, b: float, x: float) -> float:
    max_iter, eps, fpmin = 200, 3.0e-14, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def regularized_beta(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def student_t_two_sided_p(t_value: float, df: int) -> float:
    return regularized_beta(df / 2.0, 0.5, df / (df + t_value * t_value))


def holm_rejections(p_values: list[float], alpha: float = ALPHA) -> set[int]:
    order = sorted(range(len(p_values)), key=lambda i: (p_values[i], i))
    rejected: set[int] = set()
    for rank, index in enumerate(order):
        if p_values[index] <= alpha / (len(order) - rank):
            rejected.add(index)
        else:
            break
    return rejected


def mc_interval(rate: float, simulations: int) -> list[float]:
    se = math.sqrt(rate * (1.0 - rate) / simulations)
    return [max(0.0, rate - 1.96 * se), min(1.0, rate + 1.96 * se)]


def simulate_scenario(simulations: int, effect: float, sd_multiplier: float, seed: int) -> dict:
    """Simulate four paired t tests; candidate index 0 receives the shift.

    The four comparisons share the same D-control sample mean and residual
    vector. The joint multivariate-t construction is exact under Gaussian,
    mutually independent candidate residuals and a shared D residual vector.
    """
    rng = random.Random(seed)
    df = N_DRAWS - 1
    sigma = paired_difference_sd() * sd_multiplier
    noncentrality = effect * math.sqrt(N_DRAWS) / sigma
    any_reject = target_reject = 0

    for _ in range(simulations):
        control_mean = rng.gauss(0.0, 1.0)
        control_ss = rng.gammavariate(df / 2.0, 2.0)
        p_values = []
        for comparison in range(N_COMPARISONS):
            candidate_mean = rng.gauss(0.0, 1.0)
            z_numerator = (candidate_mean - control_mean) / math.sqrt(2.0)
            if comparison == 0:
                z_numerator += noncentrality
            candidate_ss = rng.gammavariate(df / 2.0, 2.0)
            cross_product_z = rng.gauss(0.0, 1.0)
            diff_ss = (
                candidate_ss + control_ss
                - 2.0 * math.sqrt(control_ss) * cross_product_z
            ) / 2.0
            t_stat = z_numerator / math.sqrt(max(diff_ss, 1e-15) / df)
            p_values.append(student_t_two_sided_p(t_stat, df))

        rejected = holm_rejections(p_values)
        any_reject += bool(rejected)
        target_reject += 0 in rejected

    family_rate = any_reject / simulations
    target_power = target_reject / simulations
    return {
        "effect_shift_front_hits_per_ticket": effect,
        "sd_multiplier": sd_multiplier,
        "simulations": simulations,
        "target_comparison": "A_vs_D_representative",
        "target_power": target_power,
        "target_power_mcse": math.sqrt(target_power * (1.0 - target_power) / simulations),
        "target_power_mc_95_interval": mc_interval(target_power, simulations),
        "family_rejection_rate": family_rate,
        "family_rejection_mcse": math.sqrt(family_rate * (1.0 - family_rate) / simulations),
        "family_rejection_mc_95_interval": mc_interval(family_rate, simulations),
    }


def build_report(simulations: int, seed: int) -> dict:
    baseline_sd = paired_difference_sd()
    curve = [
        simulate_scenario(simulations, effect, 1.0, seed + i * 100_003)
        for i, effect in enumerate(EFFECT_GRID)
    ]
    stress = [
        simulate_scenario(simulations, MDE, mult, seed + 900_001 + i * 100_003)
        for i, mult in enumerate((1.25, 1.50, 2.00))
    ]
    return {
        "experiment_id": "DLT-PI-200",
        "analysis_type": "PARAMETRIC_MONTE_CARLO_POWER_PLANNING_NOT_BACKTEST",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "runtime": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "prng": "random.Random MT19937",
            "base_seed": seed,
        },
        "registered_design": {
            "draws": N_DRAWS,
            "tickets_per_model_per_draw": TICKETS_PER_MODEL,
            "primary_endpoint": "draw-level mean front hits per ticket",
            "comparisons": ["A-D", "B1-D", "B2-D", "C-D"],
            "multiplicity": "Holm step-down, two-sided family-wise alpha=0.05",
            "mde": MDE,
            "target_power": 0.80,
        },
        "null_reference": {
            "ticket_front_hit_mean": FRONT_DRAW * FRONT_DRAW / FRONT_N,
            "ticket_front_hit_variance": ticket_front_hit_variance(),
            "front_ticket_combination_count": TICKET_COMBINATIONS,
            "portfolio_mean_variance_10_distinct_uniform_tickets": (
                ticket_front_hit_variance() / TICKETS_PER_MODEL
                * (1.0 - TICKETS_PER_MODEL / TICKET_COMBINATIONS)
            ),
            "paired_difference_sd": baseline_sd,
            "derivation": (
                "Hypergeometric(35,5,5) ticket-hit variance; finite-population correction "
                "for 10 distinct tickets sampled from C(35,5); independent candidate and D portfolios."
            ),
        },
        "alternative_model": {
            "type": "draw_level_location_shift",
            "description": (
                "One candidate's paired draw-level difference is shifted by the stated "
                "mean effect. This is a statistical power scenario, not a physical lottery "
                "mechanism and not evidence that a model can cause or predict the shift."
            ),
            "joint_test_approximation": (
                "Four numerator statistics and residual denominators share the same D-control "
                "component, giving the multivariate-t dependence implied by independent "
                "candidate residuals. A/B1/B2 dependence from shared pi windows is not "
                "empirically calibrated."
            ),
            "portfolio_assumption": (
                "Reference variance assumes candidate and D portfolios behave like "
                "independently sampled uniform 10-ticket portfolios. Actual deterministic "
                "portfolio number exposures may have a different variance."
            ),
        },
        "null_fwer_check": curve[0],
        "power_curve": curve,
        "mde_sensitivity_to_noise_inflation": stress,
        "interpretation": {
            "adequate_power_claim_allowed": False,
            "reason": (
                "Preliminary parametric estimate only. Before activation, validate the "
                "variance assumptions using the frozen portfolio generator and model-specific "
                "number-exposure/covariance diagnostics."
            ),
            "status": "PRELIMINARY_DESIGN_ESTIMATE_ONLY",
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulations", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=2026112101)
    parser.add_argument("--output", default="results/power_analysis_preliminary.json")
    parser.add_argument("--power-plan", default="POWER_ANALYSIS_PLAN.md")
    parser.add_argument("--preregistration-commit", default="d64002531a9a6661c533cb47acdc48d8a89e2ead")
    parser.add_argument("--allow-small-run", action="store_true")
    args = parser.parse_args()
    if args.simulations < 100_000 and not args.allow_small_run:
        parser.error("confirmatory planning run requires at least 100,000 simulations per scenario")
    report = build_report(args.simulations, args.seed)
    report["provenance"] = {
        "source_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "power_plan_sha256": hashlib.sha256(Path(args.power_plan).read_bytes()).hexdigest(),
        "preregistration_commit": args.preregistration_commit,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mde_power = next(x["target_power"] for x in report["power_curve"] if x["effect_shift_front_hits_per_ticket"] == MDE)
    stress_15 = next(x["target_power"] for x in report["mde_sensitivity_to_noise_inflation"] if x["sd_multiplier"] == 1.5)
    print(json.dumps({
        "status": "PRELIMINARY_POWER_REPORT_CREATED",
        "output": str(output),
        "simulations_per_scenario": args.simulations,
        "baseline_sd": report["null_reference"]["paired_difference_sd"],
        "mde_power": mde_power,
        "noise_inflation_1_5_mde_power": stress_15,
        "warning": "Preliminary parametric estimate only; not evidence of predictive edge."
    }, indent=2))


if __name__ == "__main__":
    main()
