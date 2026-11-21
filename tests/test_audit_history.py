import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.audit_history import audit_snapshot


def make_snapshot(root):
    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True)
    records = [
        {"lotteryDrawNum": "26130", "lotteryDrawTime": "2026-11-18", "lotteryDrawResult": "01 02 03 04 05 01 02"},
        {"lotteryDrawNum": "26131", "lotteryDrawTime": "2026-11-19", "lotteryDrawResult": "02 03 04 05 06 02 03"},
    ]
    raw = json.dumps({"errorCode": "0", "value": {"list": records}}, separators=(",", ":")).encode()
    (raw_dir / "page_0001.json").write_bytes(raw)
    page = {"page": 1, "url": "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?pageNo=1",
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    completed = "2026-11-21T12:00:00Z"
    rows = [
        {"draw_id": "26130", "draw_date": "2026-11-18", "snapshot_retrieved_at_utc": completed,
         "front": "01 02 03 04 05", "back": "01 02"},
        {"draw_id": "26131", "draw_date": "2026-11-19", "snapshot_retrieved_at_utc": completed,
         "front": "02 03 04 05 06", "back": "02 03"},
    ]
    csv_path = root / "history_snapshot.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    manifest = {
        "source": "official_sporttery_api",
        "endpoint": "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry",
        "gameNo": "85",
        "retrieval_started_at_utc": "2026-11-21T11:59:00Z",
        "snapshot_completed_at_utc": completed,
        "draw_count": 2,
        "first_draw_id": "26130",
        "last_draw_id": "26131",
        "first_draw_date": "2026-11-18",
        "last_draw_date": "2026-11-19",
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "pages": [page],
        "page_1_stability_check": {"re_fetched": True, "signature_matches": True},
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    bundle = {
        "retrieval_started_at_utc": "2026-11-21T11:59:00Z",
        "snapshot_completed_at_utc": completed,
        "page_hashes": [page],
        "page_1_stability_check": {"re_fetched": True, "signature_matches": True},
    }
    (root / "source_bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    calendar_source = b"synthetic official calendar fixture; test-only"
    (root / "calendar_source.html").write_bytes(calendar_source)
    calendar_path = root / "calendar_attestation.json"
    calendar = {
        "status": "VERIFIED",
        "source_url": "https://www.sporttery.cn/official/dlt-calendar",
        "retrieved_at_utc": "2026-11-21T12:10:00Z",
        "source_document_file": "calendar_source.html",
        "source_document_sha256": hashlib.sha256(calendar_source).hexdigest(),
        "draw_records": [
            {"draw_id": "26130", "draw_date": "2026-11-18"},
            {"draw_id": "26131", "draw_date": "2026-11-19"},
        ],
    }
    calendar_path.write_text(json.dumps(calendar), encoding="utf-8")
    return csv_path, raw_dir / "page_0001.json", calendar_path


class TestHistoryAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.csv_path, self.raw_path, self.calendar_path = make_snapshot(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_snapshot_passes(self):
        result = audit_snapshot(self.root, "2026-11-22T00:00:00Z", self.calendar_path)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["draw_count"], 2)
        self.assertEqual(result["errors"], [])

    def test_snapshot_after_cutoff_fails(self):
        result = audit_snapshot(self.root, "2026-11-21T11:00:00Z", self.calendar_path)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("at or after forecast cutoff" in e for e in result["errors"]))

    def test_csv_tampering_fails(self):
        self.csv_path.write_text(self.csv_path.read_text() + "\n", encoding="utf-8")
        result = audit_snapshot(self.root, calendar_attestation_path=self.calendar_path)
        self.assertTrue(any("CSV SHA-256" in e for e in result["errors"]))

    def test_missing_calendar_attestation_is_not_full_pass(self):
        result = audit_snapshot(self.root)
        self.assertEqual(result["status"], "PASS_WITH_WARNINGS")
        self.assertEqual(result["continuity_status"], "NOT_VERIFIED_OFFICIAL_CALENDAR_REQUIRED")

    def test_calendar_mismatch_fails(self):
        calendar = json.loads(self.calendar_path.read_text())
        calendar["draw_records"] = calendar["draw_records"][:1]
        self.calendar_path.write_text(json.dumps(calendar))
        result = audit_snapshot(self.root, calendar_attestation_path=self.calendar_path)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("do not exactly match" in e for e in result["errors"]))

    def test_calendar_timestamp_must_precede_cutoff(self):
        result = audit_snapshot(self.root, "2026-11-21T12:05:00Z", self.calendar_path)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("calendar attestation was retrieved" in e for e in result["errors"]))

    def test_raw_page_tampering_fails(self):
        self.raw_path.write_bytes(self.raw_path.read_bytes() + b" ")
        result = audit_snapshot(self.root, calendar_attestation_path=self.calendar_path)
        self.assertTrue(any("raw page 1 SHA-256" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
