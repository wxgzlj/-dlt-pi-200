import csv
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from src.generate_forecast import read_history
from src.fetch_history import normalize


class TestHistorySnapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "history.csv"
        self.cutoff = dt.datetime(2026, 11, 22, tzinfo=dt.timezone.utc)

    def tearDown(self):
        self.tmp.cleanup()

    def write_rows(self, rows, fields=None):
        fields = fields or ["draw_id", "draw_date", "snapshot_retrieved_at_utc", "front", "back"]
        with self.path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    def row(self, draw_id="26130", date="2026-11-18", snapshot="2026-11-21T12:00:00Z"):
        return {
            "draw_id": draw_id,
            "draw_date": date,
            "snapshot_retrieved_at_utc": snapshot,
            "front": "01 02 03 04 05",
            "back": "01 02",
        }

    def test_snapshot_time_is_used_as_conservative_availability_time(self):
        self.write_rows([self.row()])
        fc, bc, n, digest, snapshot = read_history(self.path, self.cutoff)
        self.assertEqual(n, 1)
        self.assertEqual(fc[1], 1)
        self.assertEqual(bc[1], 1)
        self.assertEqual(snapshot, "2026-11-21T12:00:00Z")
        self.assertEqual(len(digest), 64)

    def test_snapshot_at_or_after_cutoff_rejected(self):
        self.write_rows([self.row(snapshot="2026-11-22T00:00:00Z")])
        with self.assertRaisesRegex(ValueError, "at or after forecast cutoff"):
            read_history(self.path, self.cutoff)

    def test_mixed_snapshot_times_rejected(self):
        self.write_rows([
            self.row(),
            self.row(draw_id="26131", date="2026-11-19", snapshot="2026-11-21T12:00:01Z"),
        ])
        with self.assertRaisesRegex(ValueError, "share one snapshot"):
            read_history(self.path, self.cutoff)

    def test_old_ambiguous_publication_column_rejected(self):
        self.write_rows(
            [{"draw_id":"26130","draw_date":"2026-11-18","published_at_utc":"2026-11-21T12:00:00Z",
              "front":"01 02 03 04 05","back":"01 02"}],
            fields=["draw_id","draw_date","published_at_utc","front","back"],
        )
        with self.assertRaisesRegex(ValueError, "snapshot_retrieved_at_utc"):
            read_history(self.path, self.cutoff)

    def test_chronological_order_enforced(self):
        self.write_rows([
            self.row(draw_id="26131", date="2026-11-19"),
            self.row(draw_id="26130", date="2026-11-18"),
        ])
        with self.assertRaisesRegex(ValueError, "not sorted chronologically"):
            read_history(self.path, self.cutoff)

    def test_official_normalizer_uses_snapshot_field_name(self):
        item = {
            "lotteryDrawNum": "26130",
            "lotteryDrawTime": "2026-11-18",
            "lotteryDrawResult": "01 02 03 04 05 01 02",
        }
        row = normalize(item, "2026-11-21T12:00:00Z")
        self.assertIn("snapshot_retrieved_at_utc", row)
        self.assertNotIn("published_at_utc", row)


if __name__ == "__main__":
    unittest.main()
