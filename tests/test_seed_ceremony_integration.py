import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src" / "seed_ceremony.py"


class TestSeedCeremonyIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "ledger").mkdir()
        shutil.copy2(SOURCE, self.root / "src" / "seed_ceremony.py")

    def tearDown(self):
        self.tmp.cleanup()

    def run_create(self, draw="TEST-1", cutoff="2099-01-01T00:00:00Z"):
        return subprocess.run(
            [sys.executable, str(self.root / "src" / "seed_ceremony.py"),
             "create", "--draw-id", draw, "--cutoff-utc", cutoff],
            cwd=self.root, text=True, capture_output=True
        )

    def test_create_commitment_permissions_and_no_reroll(self):
        result = self.run_create()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        seed_path = self.root / output["private_seed_file"]
        public_path = self.root / output["public_commitment_file"]
        lock_path = self.root / output["lock_file"]
        seed = bytes.fromhex(seed_path.read_text(encoding="ascii").strip())
        record = json.loads(public_path.read_text(encoding="utf-8"))
        self.assertEqual(len(seed), 32)
        self.assertEqual(hashlib.sha256(seed).hexdigest(), record["seed_commitment_sha256"])
        self.assertTrue(lock_path.exists())
        if os.name == "posix":
            self.assertEqual(seed_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(lock_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual((self.root / "private" / "seeds").stat().st_mode & 0o777, 0o700)
        second = self.run_create()
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("SEED_CEREMONY_ALREADY_EXISTS", second.stderr)
        self.assertEqual(seed_path.read_text(encoding="ascii").strip(), seed.hex())

    def test_existing_public_file_blocks_before_private_seed_creation(self):
        public_dir = self.root / "ledger" / "seed_commitments"
        public_dir.mkdir(parents=True)
        (public_dir / "TEST-1.json").write_text("{}", encoding="utf-8")
        result = self.run_create()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "private" / "seeds" / "TEST-1.seed").exists())

    def test_naive_cutoff_is_rejected(self):
        result = self.run_create(draw="TEST-2", cutoff="2099-01-01T00:00:00")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "private" / "seeds" / "TEST-2.seed").exists())


if __name__ == "__main__":
    unittest.main()
