import unittest
from src.pi_digits import KNOWN_PREFIX, pi_fraction_digits

class TestPiDigits(unittest.TestCase):
    def test_known_prefix(self):
        self.assertEqual(pi_fraction_digits(50), KNOWN_PREFIX)

    def test_longer_prefix(self):
        digits=pi_fraction_digits(100)
        self.assertEqual(digits[:50], KNOWN_PREFIX)
        self.assertEqual(len(digits),100)

if __name__=="__main__":
    unittest.main()
