import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class TestSeedCeremonySource(unittest.TestCase):
    def test_seed_ceremony_is_valid_python(self):
        ast.parse((ROOT / "src" / "seed_ceremony.py").read_text(encoding="utf-8"))

    def test_generator_no_longer_generates_its_own_seed(self):
        source = (ROOT / "src" / "generate_forecast.py").read_text(encoding="utf-8")
        self.assertNotIn("secrets.token_bytes", source)
        self.assertIn("--seed-commitment", source)
        self.assertIn("--seed-anchor", source)
        self.assertIn("root_seed_commitment_sha256", source)

if __name__ == "__main__":
    unittest.main()
