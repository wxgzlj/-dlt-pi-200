import itertools
import unittest

from src.portfolio_covariance import (
    analyze_payload, analyze_panel, exposure_vector, score_covariance,
    score_mean, validate_front_portfolio,
)


def ten_tickets():
    return [{"front": list(c)} for c in list(itertools.combinations(range(1, 36), 5))[:10]]


def payload(draw_id="SYNTH-1"):
    tickets = ten_tickets()
    return {
        "experiment_id": "DLT-PI-200",
        "draw_id": draw_id,
        "models": ["A", "B1", "B2", "C", "D"],
        "tickets_per_model": 10,
        "code_sha256": "1" * 64,
        "analysis_plan_sha256": "2" * 64,
        "pi_source_sha256": "3" * 64,
        "historical_snapshot_sha256": "4" * 64,
        "history_audit_sha256": "5" * 64,
        "history_snapshot_completed_at_utc": "2026-11-21T12:00:00Z",
        "game_rules_id": "DLT-5x35-2x12-2026-revision",
        "parameters": {"pi_block_length": 6, "pi_window_digits": 2048},
        "tickets": {m: tickets for m in ("A", "B1", "B2", "C", "D")},
    }


class TestPortfolioCovariance(unittest.TestCase):
    def test_exact_covariance_matches_exhaustive_small_population(self):
        x = [0, 1, 2, 0, 3, 1]
        y = [1, 0, 2, 1, 0, 2]
        k, n = 2, len(x)
        outcomes = [
            (sum(x[i] for i in c), sum(y[i] for i in c))
            for c in itertools.combinations(range(n), k)
        ]
        mx = sum(a for a, _ in outcomes) / len(outcomes)
        my = sum(b for _, b in outcomes) / len(outcomes)
        brute = sum((a-mx)*(b-my) for a,b in outcomes) / len(outcomes)
        self.assertAlmostEqual(score_covariance(x, y, draw_size=k, ticket_count=1), brute, places=12)

    def test_exposure_total_and_expected_mean(self):
        e = exposure_vector(ten_tickets())
        self.assertEqual(sum(e), 50)
        self.assertAlmostEqual(score_mean(e), 5/7, places=12)

    def test_identical_model_portfolios_have_zero_paired_difference_variance(self):
        sample = payload()
        result = analyze_payload(sample)
        for row in result["paired_difference_covariance_matrix"]:
            for value in row:
                self.assertAlmostEqual(value, 0.0, places=12)

    def test_duplicate_ticket_rejected(self):
        tickets = ten_tickets()
        tickets[1] = tickets[0]
        with self.assertRaisesRegex(ValueError, "duplicate ticket"):
            validate_front_portfolio(tickets)

    def test_panel_rejects_duplicate_draw_ids(self):
        base = payload("SYNTH-0")
        payloads = [dict(base, draw_id=f"SYNTH-{i}") for i in range(200)]
        payloads[1]["draw_id"] = "SYNTH-0"
        with self.assertRaisesRegex(ValueError, "duplicate draw_id"):
            analyze_panel(payloads)

    def test_panel_rejects_mixed_code_provenance(self):
        base = payload("SYNTH-0")
        payloads = [dict(base, draw_id=f"SYNTH-{i}") for i in range(200)]
        payloads[50] = dict(payloads[50], code_sha256="9" * 64)
        with self.assertRaisesRegex(ValueError, "mixes frozen provenance"):
            analyze_panel(payloads)

    def test_panel_requires_200_payloads(self):
        sample = payload()
        with self.assertRaisesRegex(ValueError, "exactly 200"):
            analyze_panel([sample])


if __name__ == "__main__":
    unittest.main()
