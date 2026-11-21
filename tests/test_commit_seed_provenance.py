import datetime as dt
import hashlib
import unittest

from src.prospective import validate_seed_provenance


class TestCommitSeedProvenance(unittest.TestCase):
    def setUp(self):
        self.seed = bytes.fromhex("ab" * 32)
        self.digest = hashlib.sha256(self.seed).hexdigest()
        self.cutoff = dt.datetime(2099, 1, 1, tzinfo=dt.timezone.utc)
        self.payload = {
            "created_at_utc": "2098-12-01T00:00:00Z",
            "root_seed_hex": self.seed.hex(),
            "root_seed_commitment_sha256": self.digest,
            "seed_anchor": {
                "seed_commitment_sha256": self.digest,
                "anchor_url": "https://github.com/example/repo/commit/" + "1" * 40,
                "anchor_commit_sha": "1" * 40,
                "anchored_at_utc": "2098-11-30T23:00:00Z",
            },
        }

    def test_valid_seed_provenance(self):
        validate_seed_provenance(self.payload, self.cutoff)

    def test_seed_hash_mismatch_rejected(self):
        bad = dict(self.payload, root_seed_commitment_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_seed_provenance(bad, self.cutoff)

    def test_anchor_after_forecast_creation_rejected(self):
        bad = dict(self.payload)
        bad["seed_anchor"] = dict(self.payload["seed_anchor"], anchored_at_utc="2098-12-02T00:00:00Z")
        with self.assertRaisesRegex(ValueError, "anchored before forecast"):
            validate_seed_provenance(bad, self.cutoff)

    def test_naive_timestamp_rejected(self):
        bad = dict(self.payload, created_at_utc="2098-12-01T00:00:00")
        with self.assertRaisesRegex(ValueError, "explicit UTC offset"):
            validate_seed_provenance(bad, self.cutoff)

    def test_short_commit_sha_rejected(self):
        bad = dict(self.payload)
        bad["seed_anchor"] = dict(self.payload["seed_anchor"], anchor_commit_sha="abc")
        with self.assertRaisesRegex(ValueError, "full 40-character"):
            validate_seed_provenance(bad, self.cutoff)


if __name__ == "__main__":
    unittest.main()
