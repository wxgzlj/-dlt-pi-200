import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import fetch_history
from src.audit_history import audit_snapshot


def api_page(records, page):
    obj = {"errorCode": "0", "value": {"list": records}}
    raw = json.dumps(obj, separators=(",", ":")).encode()
    url = fetch_history.API + f"?gameNo=85&pageNo={page}&pageSize=2"
    return obj, raw, url


def record(issue, day, result):
    return {
        "lotteryDrawNum": issue,
        "lotteryDrawTime": day,
        "lotteryDrawResult": result,
    }


class TestFetchHistory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "snapshot"

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self):
        with patch.object(sys, "argv", [
            "fetch_history.py", "--output-dir", str(self.out),
            "--page-size", "2", "--delay", "0",
        ]):
            fetch_history.main()

    def test_stable_pagination_creates_auditable_snapshot(self):
        p1 = api_page([
            record("26131", "2026-11-19", "02 03 04 05 06 02 03"),
            record("26130", "2026-11-18", "01 02 03 04 05 01 02"),
        ], 1)
        p2 = api_page([
            record("26129", "2026-11-17", "03 04 05 06 07 03 04"),
        ], 2)
        with patch.object(fetch_history, "fetch_page", side_effect=[p1, p2, p1]), \
             patch.object(fetch_history.time, "sleep"):
            self.run_main()
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertEqual(manifest["draw_count"], 3)
        self.assertEqual(manifest["first_draw_id"], "26129")
        self.assertEqual(manifest["last_draw_id"], "26131")
        with (self.out / "history_snapshot.csv").open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        calendar_path = self.out / "calendar_attestation.json"
        calendar_source = b"synthetic official calendar fixture; test-only"
        (self.out / "calendar_source.html").write_bytes(calendar_source)
        calendar_path.write_text(json.dumps({
            "status": "VERIFIED",
            "source_url": "https://www.sporttery.cn/official/dlt-calendar",
            "retrieved_at_utc": "2098-12-31T23:00:00Z",
            "source_document_file": "calendar_source.html",
            "source_document_sha256": hashlib.sha256(calendar_source).hexdigest(),
            "draw_records": [{"draw_id": row["draw_id"], "draw_date": row["draw_date"]} for row in rows],
        }))
        result = audit_snapshot(self.out, "2099-01-01T00:00:00Z", calendar_path)
        self.assertEqual(result["status"], "PASS")

    def test_page_one_change_fails_closed(self):
        p1 = api_page([
            record("26131", "2026-11-19", "02 03 04 05 06 02 03"),
            record("26130", "2026-11-18", "01 02 03 04 05 01 02"),
        ], 1)
        p2 = api_page([
            record("26129", "2026-11-17", "03 04 05 06 07 03 04"),
        ], 2)
        changed = api_page([
            record("26132", "2026-11-20", "04 05 06 07 08 04 05"),
            record("26131", "2026-11-19", "02 03 04 05 06 02 03"),
        ], 1)
        with patch.object(fetch_history, "fetch_page", side_effect=[p1, p2, changed]), \
             patch.object(fetch_history.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "page 1 changed"):
                self.run_main()
        self.assertFalse((self.out / "manifest.json").exists())

    def test_existing_snapshot_is_not_overwritten(self):
        self.out.mkdir(parents=True)
        (self.out / "manifest.json").write_text("{}")
        with patch.object(fetch_history, "fetch_page") as mocked:
            with self.assertRaisesRegex(FileExistsError, "never overwrite"):
                self.run_main()
        mocked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
