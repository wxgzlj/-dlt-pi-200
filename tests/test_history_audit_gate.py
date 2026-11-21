import json
import tempfile
import unittest
from pathlib import Path

from src.generate_forecast import canonical, sha, verify_history_audit
from src.prospective import validate_history_audit


class TestHistoryAuditGate(unittest.TestCase):
    def setUp(self):
        self.audit = {
            "status": "PASS",
            "errors": [],
            "warnings": [],
            "csv_sha256_computed": "a" * 64,
            "draw_count": 1200,
            "snapshot_completed_at_utc": "2026-11-21T12:00:00Z",
        }
        self.audit_hash = sha(canonical(self.audit))
        self.payload = {
            "historical_snapshot_sha256": "a" * 64,
            "historical_draw_count": 1200,
            "history_snapshot_completed_at_utc": "2026-11-21T12:00:00Z",
            "history_audit": self.audit,
            "history_audit_sha256": self.audit_hash,
        }
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "audit.json"
        self.path.write_text(json.dumps(self.audit), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_generator_accepts_exact_matching_pass_audit(self):
        report, digest = verify_history_audit(
            self.path, "a" * 64, 1200, "2026-11-21T12:00:00Z"
        )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(digest, self.audit_hash)

    def test_generator_rejects_warning_status(self):
        bad = dict(self.audit, status="PASS_WITH_WARNINGS", warnings=["issue gap"])
        self.path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "must be PASS"):
            verify_history_audit(self.path, "a" * 64, 1200, "2026-11-21T12:00:00Z")

    def test_generator_rejects_hash_mismatch(self):
        with self.assertRaisesRegex(ValueError, "CSV hash"):
            verify_history_audit(self.path, "b" * 64, 1200, "2026-11-21T12:00:00Z")

    def test_commit_layer_accepts_matching_audit(self):
        validate_history_audit(self.payload)

    def test_commit_layer_rejects_tampered_audit(self):
        bad = dict(self.payload, history_audit_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "report hash mismatch"):
            validate_history_audit(bad)

    def test_commit_layer_rejects_nonpass_audit(self):
        bad_audit = dict(self.audit, status="PASS_WITH_WARNINGS", warnings=["gap"])
        bad = dict(self.payload, history_audit=bad_audit,
                   history_audit_sha256=sha(canonical(bad_audit)))
        with self.assertRaisesRegex(ValueError, "must have PASS status"):
            validate_history_audit(bad)


if __name__ == "__main__":
    unittest.main()
