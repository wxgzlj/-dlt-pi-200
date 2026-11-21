import hashlib
import unittest
from pathlib import Path

from src.power_analysis import cholesky_psd, current_source_hash, holm, ibeta, paired_sd, simulate, simulate_covariance, t_p, ticket_var, validate_covariance_panel, wilson


class TestPowerAnalysis(unittest.TestCase):
    def test_reference_variance(self):
        self.assertAlmostEqual(ticket_var(), 0.5402160864345739, places=12)
        self.assertAlmostEqual(paired_sd(), 0.3286942182511135, places=12)

    def test_student_t_tail(self):
        self.assertAlmostEqual(t_p(2.520615386, 199), 0.0125, places=8)
        self.assertAlmostEqual(ibeta(0.5, 0.5, 0.5), 0.5, places=12)

    def test_holm_step_down(self):
        self.assertEqual(holm([0.001, 0.01, 0.03, 0.8]), {0, 1})
        self.assertEqual(holm([0.02, 0.03, 0.04, 0.9]), set())

    def test_wilson_interval_at_boundary(self):
        low, high = wilson(1.0, 100000)
        self.assertLess(low, 1.0)
        self.assertEqual(high, 1.0)

    def test_cholesky_reconstructs_covariance(self):
        matrix = [[2.0, 1.0], [1.0, 2.0]]
        lower = cholesky_psd(matrix)
        reconstructed = [
            [sum(lower[i][k] * lower[j][k] for k in range(2)) for j in range(2)]
            for i in range(2)
        ]
        for i in range(2):
            for j in range(2):
                self.assertAlmostEqual(reconstructed[i][j], matrix[i][j], places=12)

    def test_non_psd_covariance_rejected(self):
        with self.assertRaisesRegex(ValueError, "positive semidefinite"):
            cholesky_psd([[1.0, 2.0], [2.0, 1.0]])

    def test_covariance_power_simulation_reproducible(self):
        v = paired_sd() ** 2
        matrix = [[v if i == j else v / 2 for j in range(4)] for i in range(4)]
        a = simulate_covariance(500, 0.10, 1.0, 123456, matrix, 1, "B1")
        b = simulate_covariance(500, 0.10, 1.0, 123456, matrix, 1, "B1")
        self.assertEqual(a, b)
        self.assertEqual(a["target_comparison"], "B1_vs_D")
        self.assertTrue(0.0 <= a["target_power"] <= 1.0)

    def test_covariance_panel_provenance_validation(self):
        v = paired_sd() ** 2
        matrix = [[v if i == j else v / 2 for j in range(4)] for i in range(4)]
        panel = {
            "status": "COMPUTED_FROM_FIXED_PORTFOLIOS_UNDER_UNIFORM_DRAW_NULL",
            "draw_count": 200,
            "paired_difference_models": ["A", "B1", "B2", "C"],
            "average_per_draw_paired_difference_covariance": matrix,
            "frozen_provenance": {
                "code_sha256": current_source_hash(),
                "analysis_plan_sha256": hashlib.sha256(Path("PREREGISTRATION.md").read_bytes()).hexdigest(),
                "pi_source_sha256": "3" * 64,
                "historical_snapshot_sha256": "4" * 64,
                "history_audit_sha256": "5" * 64,
                "history_snapshot_completed_at_utc": "2026-11-21T12:00:00Z",
                "historical_draw_count": 1200,
                "game_rules_id": "DLT-5x35-2x12-2026-revision",
            },
        }
        self.assertEqual(validate_covariance_panel(panel), matrix)

    def test_simulation_is_reproducible(self):
        a = simulate(500, 0.10, 1.0, 123456)
        b = simulate(500, 0.10, 1.0, 123456)
        self.assertEqual(a, b)
        self.assertTrue(0.0 <= a["target_power"] <= 1.0)


if __name__ == "__main__":
    unittest.main()
