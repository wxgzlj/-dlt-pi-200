import contextlib
import datetime as dt
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import src.prospective as prospective

def iso(x):
    return x.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")

def valid_payload(root, now):
    seed = bytes.fromhex("ab" * 32)
    anchor_time = now - dt.timedelta(minutes=2)
    created_time = now - dt.timedelta(minutes=1)
    ticket = {"front": [1, 2, 3, 4, 5], "back": [1, 2]}
    models = ["A", "B1", "B2", "C", "D"]
    return {
        "experiment_id": "DLT-PI-200", "draw_id": "TEST1",
        "scheduled_cutoff_utc": iso(now + dt.timedelta(hours=2)),
        "created_at_utc": iso(created_time), "game_rules_id": "test-rules",
        "models": models, "tickets": {m: [dict(ticket, front=[1,2,3,4,5+i] if False else [1,2,3,4,5]) for _ in range(10)] for m in models},
        "code_sha256": "0"*64, "analysis_plan_sha256": "1"*64, "primary_endpoint": "front hits",
        "root_seed_hex": seed.hex(), "root_seed_commitment_sha256": hashlib.sha256(seed).hexdigest(),
        "seed_anchor": {"seed_commitment_sha256": hashlib.sha256(seed).hexdigest(),
            "anchor_url": "https://example.invalid/commit/abc", "anchor_commit_sha": "a"*40,
            "anchored_at_utc": iso(anchor_time)}
    }

class TestCommitSeedGovernance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ledger = self.root / "ledger" / "events.jsonl"
        self.vault = self.root / "private" / "vault"
        self.patches = [
            patch.object(prospective, "ROOT", self.root),
            patch.object(prospective, "LEDGER", self.ledger),
            patch.object(prospective, "VAULT", self.vault),
        ]
        for p in self.patches: p.start()
        self.now = dt.datetime.now(dt.timezone.utc)
        self.payload_path = self.root / "payload.json"

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()

    def run_commit(self, payload):
        self.payload_path.write_text(json.dumps(payload), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            prospective.cmd_commit(type("Args", (), {"payload": str(self.payload_path)})())

    def test_valid_seed_anchor_can_commit(self):
        self.run_commit(valid_payload(self.root, self.now))
        record = json.loads(self.ledger.read_text().splitlines()[0])
        self.assertEqual(record["type"], "commit")
        self.assertTrue((self.root / record["sealed_payload"]).exists())

    def test_missing_seed_governance_is_rejected(self):
        payload = valid_payload(self.root, self.now)
        del payload["seed_anchor"]
        with self.assertRaisesRegex(ValueError, "seed_anchor"): self.run_commit(payload)
        self.assertFalse(self.ledger.exists())

    def test_seed_hash_mismatch_is_rejected(self):
        payload = valid_payload(self.root, self.now)
        payload["root_seed_commitment_sha256"] = "f"*64
        with self.assertRaisesRegex(ValueError, "does not match"): self.run_commit(payload)
        self.assertFalse(self.ledger.exists())

    def test_late_anchor_is_rejected(self):
        payload = valid_payload(self.root, self.now)
        payload["seed_anchor"]["anchored_at_utc"] = iso(self.now + dt.timedelta(hours=1))
        with self.assertRaisesRegex(ValueError, "strictly before"): self.run_commit(payload)
        self.assertFalse(self.ledger.exists())

if __name__ == "__main__": unittest.main()
