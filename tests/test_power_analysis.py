import unittest

from src.power_analysis import holm, ibeta, paired_sd, simulate, t_p, ticket_var, wilson


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

    def test_simulation_is_reproducible(self):
        a = simulate(500, 0.10, 1.0, 123456)
        b = simulate(500, 0.10, 1.0, 123456)
        self.assertEqual(a, b)
        self.assertTrue(0.0 <= a["target_power"] <= 1.0)


if __name__ == "__main__":
    unittest.main()
