import itertools
import unittest

from src.portfolio_covariance import (
    analyze_payload, analyze_panel, exposure_vector, score_covariance,
    score_mean, validate_front_portfolio,
)


def ten_tickets():
    return [{"front": list(c)} for c in list(itertools.combinations(range(1, 36), 5))[:10]]


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
        tickets = ten_tickets()
        payload = {
            "experiment_id": "DLT-PI-200",
            "draw_id": "SYNTH-1",
            "tickets": {m: tickets for m in ("A", "B1", "B2", "C", "D")},
        }
        result = analyze_payload(payload)
        for row in result["paired_difference_covariance_matrix"]:
            for value in row:
                self.assertAlmostEqual(value, 0.0, places=12)

    def test_duplicate_ticket_rejected(self):
        tickets = ten_tickets()
        tickets[1] = tickets[0]
        with self.assertRaisesRegex(ValueError, "duplicate ticket"):
            validate_front_portfolio(tickets)

    def test_panel_rejects_duplicate_draw_ids(self):
        tickets = ten_tickets()
        base = {
            "experiment_id": "DLT-PI-200",
            "draw_id": "SYNTH-0",
            "tickets": {m: tickets for m in ("A", "B1", "B2", "C", "D")},
        }
        payloads = [dict(base, draw_id=f"SYNTH-{i}") for i in range(200)]
        payloads[1]["draw_id"] = "SYNTH-0"
        with self.assertRaisesRegex(ValueError, "duplicate draw_id"):
            analyze_panel(payloads)

    def test_panel_requires_200_payloads(self):
        payload = {
            "experiment_id": "DLT-PI-200",
            "draw_id": "SYNTH-1",
            "tickets": {m: ten_tickets() for m in ("A", "B1", "B2", "C", "D")},
        }
        with self.assertRaisesRegex(ValueError, "exactly 200"):
            analyze_panel([payload])


if __name__ == "__main__":
    unittest.main()
