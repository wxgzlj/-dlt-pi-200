import math
import unittest

from src.power_analysis import (
    holm_rejections,
    paired_difference_sd,
    regularized_beta,
    simulate_scenario,
    student_t_two_sided_p,
    ticket_front_hit_variance,
)


class TestPowerAnalysis(unittest.TestCase):
    def test_hypergeometric_reference_variance(self):
        self.assertAlmostEqual(ticket_front_hit_variance(), 0.5402160864345739, places=12)
        self.assertAlmostEqual(paired_difference_sd(), 0.3286942182511135, places=12)

    def test_student_t_tail_probability(self):
        self.assertAlmostEqual(student_t_two_sided_p(2.520615386, 199), 0.0125, places=8)
        self.assertAlmostEqual(regularized_beta(0.5, 0.5, 0.5), 0.5, places=12)

    def test_holm_step_down(self):
        self.assertEqual(holm_rejections([0.001, 0.01, 0.03, 0.8]), {0, 1})
        self.assertEqual(holm_rejections([0.02, 0.03, 0.04, 0.9]), set())

    def test_simulation_is_reproducible(self):
        a = simulate_scenario(500, 0.10, 1.0, 123456)
        b = simulate_scenario(500, 0.10, 1.0, 123456)
        self.assertEqual(a, b)
        self.assertTrue(0.0 <= a["target_power"] <= 1.0)
        self.assertTrue(0.0 <= a["family_rejection_rate"] <= 1.0)


if __name__ == "__main__":
    unittest.main()
