#!/usr/bin/env python3
"""Read-only provenance and integrity audit for an official DLT history snapshot."""
from __future__ import annotations
import argparse
import csv
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

API = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
FIELDS = {"draw_id", "draw_date", "snapshot_retrieved_at_utc", "front", "back"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_utc(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include Z or explicit UTC offset")
    return parsed.astimezone(dt.timezone.utc)


def validate_row(row):
    issue = row["draw_id"].strip()
    if not issue.isdigit():
        raise ValueError(f"non-numeric draw_id: {issue}")
    dt.date.fromisoformat(row["draw_date"])
    front = [int(x) for x in row["front"].replace(",", " ").split()]
    back = [int(x) for x in row["back"].replace(",", " ").split()]
    if len(front) != 5 or len(set(front)) != 5 or any(x < 1 or x > 35 for x in front):
        raise ValueError(f"invalid front zone for issue {issue}")
    if len(back) != 2 or len(set(back)) != 2 or any(x < 1 or x > 12 for x in back):
        raise ValueError(f"invalid back zone for issue {issue}")
    return issue


def candidate_issue_gaps(draw_ids):
    groups = {}
    for issue in draw_ids:
        if len(issue) < 4:
            continue
        prefix, suffix = issue[:-3], int(issue[-3:])
        groups.setdefault(prefix, set()).add(suffix)
    gaps = []
    for prefix, values in sorted(groups.items()):
        if not values:
            continue
        for missing in range(min(values) + 1, max(values)):
            if missing not in values:
                gaps.append(f"{prefix}{missing:03d}")
    return gaps


def audit_snapshot(snapshot_dir: Path, cutoff_utc: str | None = None,
                   calendar_attestation_path: Path | None = None) -> dict:
    errors, warnings = [], []
    manifest_path = snapshot_dir / "manifest.json"
    csv_path = snapshot_dir / "history_snapshot.csv"
    bundle_path = snapshot_dir / "source_bundle.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    if manifest.get("source") != "official_sporttery_api" or manifest.get("endpoint") != API:
        errors.append("manifest source/endpoint mismatch")
    if manifest.get("gameNo") != "85":
        errors.append("manifest gameNo mismatch")
    if not manifest.get("page_1_stability_check", {}).get("signature_matches"):
        errors.append("page 1 stability check missing or failed")

    raw_csv = csv_path.read_bytes()
    csv_hash = sha(raw_csv)
    if csv_hash != manifest.get("csv_sha256"):
        errors.append("CSV SHA-256 does not match manifest")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not FIELDS.issubset(reader.fieldnames or []):
            errors.append("CSV columns do not match the snapshot schema")
            rows = []
        else:
            rows = list(reader)

    ids, dates, snapshot_times = [], [], set()
    seen = set()
    previous_date = None
    for row in rows:
        try:
            issue = validate_row(row)
            if issue in seen:
                errors.append(f"duplicate draw_id in CSV: {issue}")
            seen.add(issue)
            ids.append(issue)
            draw_date = dt.date.fromisoformat(row["draw_date"])
            dates.append(row["draw_date"])
            if previous_date is not None and draw_date < previous_date:
                errors.append("CSV is not sorted chronologically")
            previous_date = draw_date
            snapshot_times.add(parse_utc(row["snapshot_retrieved_at_utc"]))
        except Exception as exc:
            errors.append(str(exc))

    if len(rows) != manifest.get("draw_count"):
        errors.append("CSV row count does not match manifest draw_count")
    if ids:
        if ids[0] != manifest.get("first_draw_id") or ids[-1] != manifest.get("last_draw_id"):
            errors.append("CSV first/last issue IDs do not match manifest")
        if dates[0] != manifest.get("first_draw_date") or dates[-1] != manifest.get("last_draw_date"):
            errors.append("CSV first/last dates do not match manifest")

    try:
        completed = parse_utc(manifest["snapshot_completed_at_utc"])
        started = parse_utc(manifest["retrieval_started_at_utc"])
        if completed < started:
            errors.append("snapshot completion time precedes retrieval start")
        if len(snapshot_times) != 1 or next(iter(snapshot_times)) != completed:
            errors.append("CSV rows do not share manifest snapshot completion time")
        if bundle.get("snapshot_completed_at_utc") != manifest.get("snapshot_completed_at_utc"):
            errors.append("source bundle and manifest completion timestamps differ")
        if bundle.get("retrieval_started_at_utc") != manifest.get("retrieval_started_at_utc"):
            errors.append("source bundle and manifest retrieval start timestamps differ")
        if not bundle.get("page_1_stability_check", {}).get("signature_matches"):
            errors.append("source bundle page 1 stability attestation is missing or failed")
        if cutoff_utc and completed >= parse_utc(cutoff_utc):
            errors.append("snapshot completed at or after forecast cutoff")
    except Exception as exc:
        errors.append(f"invalid snapshot/cutoff timestamp: {exc}")

    page_records = manifest.get("pages", [])
    page_ids, page_seen = [], set()
    expected_pages = list(range(1, len(page_records) + 1))
    actual_pages = [p.get("page") for p in page_records]
    if actual_pages != expected_pages:
        errors.append("manifest page numbers are not contiguous from 1")
    raw_dir = snapshot_dir / "raw"
    for page in page_records:
        number = page.get("page")
        if not str(page.get("url", "")).startswith(API + "?"):
            errors.append(f"raw page {number} URL does not match the official API endpoint")
        path = raw_dir / f"page_{number:04d}.json"
        try:
            raw = path.read_bytes()
            if sha(raw) != page.get("sha256"):
                errors.append(f"raw page {number} SHA-256 mismatch")
            if len(raw) != page.get("bytes"):
                errors.append(f"raw page {number} byte count mismatch")
            obj = json.loads(raw.decode("utf-8"))
            if str(obj.get("errorCode")) != "0":
                errors.append(f"raw page {number} official API errorCode is not 0")
            records = obj.get("value", {}).get("list", [])
            for item in records:
                issue = str(item.get("lotteryDrawNum", "")).strip()
                if not issue or issue in page_seen:
                    errors.append(f"empty/duplicate issue across raw pages: {issue}")
                page_seen.add(issue)
                page_ids.append(issue)
        except Exception as exc:
            errors.append(f"cannot verify raw page {number}: {exc}")

    if set(page_ids) != set(ids) or len(page_ids) != len(ids):
        errors.append("raw page issue IDs do not exactly match normalized CSV issue IDs")
    if bundle.get("page_hashes") != page_records:
        errors.append("source bundle page hashes differ from manifest")

    gaps = candidate_issue_gaps(ids)
    duplicate_dates = sorted(d for d, count in Counter(dates).items() if count > 1)
    calendar_verified = False
    calendar_hash = None
    calendar_source_hash = None
    if calendar_attestation_path is not None:
        try:
            calendar_raw = calendar_attestation_path.read_bytes()
            calendar_hash = sha(calendar_raw)
            attestation = json.loads(calendar_raw.decode("utf-8"))
            host = urlparse(str(attestation.get("source_url", ""))).hostname or ""
            if attestation.get("status") != "VERIFIED":
                errors.append("calendar attestation status must be VERIFIED")
            if not (host == "sporttery.cn" or host.endswith(".sporttery.cn")):
                errors.append("calendar attestation source must be on the official sporttery.cn domain")
            calendar_time = parse_utc(attestation.get("retrieved_at_utc", ""))
            if cutoff_utc and calendar_time >= parse_utc(cutoff_utc):
                errors.append("official calendar attestation was retrieved at or after forecast cutoff")
            source_file = attestation.get("source_document_file")
            if not isinstance(source_file, str) or not source_file:
                errors.append("calendar attestation must reference a preserved raw source document")
            else:
                source_path = (snapshot_dir / source_file).resolve()
                if snapshot_dir.resolve() not in source_path.parents:
                    errors.append("calendar source document must be inside the snapshot directory")
                else:
                    source_raw = source_path.read_bytes()
                    calendar_source_hash = sha(source_raw)
                    if calendar_source_hash != attestation.get("source_document_sha256"):
                        errors.append("official calendar source document SHA-256 mismatch")
            calendar_rows = attestation.get("draw_records")
            if not isinstance(calendar_rows, list):
                errors.append("calendar attestation must include draw_records")
            else:
                calendar_pairs = []
                calendar_seen = set()
                for item in calendar_rows:
                    issue = str(item.get("draw_id", "")).strip()
                    day = str(item.get("draw_date", "")).strip()
                    if not issue or issue in calendar_seen:
                        errors.append(f"empty or duplicate issue in calendar attestation: {issue}")
                    calendar_seen.add(issue)
                    dt.date.fromisoformat(day)
                    calendar_pairs.append((issue, day))
                if sorted(calendar_pairs) != sorted(zip(ids, dates)):
                    errors.append("official calendar draw_records do not exactly match snapshot issue IDs and dates")
                if not errors:
                    calendar_verified = True
        except Exception as exc:
            errors.append(f"calendar attestation invalid: {exc}")
    else:
        warnings.append("official draw-calendar attestation missing; snapshot integrity alone does not certify historical completeness")
    if gaps and not calendar_verified:
        warnings.append("candidate issue-number gaps require official draw-calendar cross-check")
    if duplicate_dates and not calendar_verified:
        warnings.append("multiple issues share draw dates; verify against official calendar")

    return {
        "status": "FAIL" if errors else ("PASS" if calendar_verified else "PASS_WITH_WARNINGS"),
        "snapshot_dir": str(snapshot_dir),
        "draw_count": len(rows),
        "first_draw_id": ids[0] if ids else None,
        "last_draw_id": ids[-1] if ids else None,
        "snapshot_completed_at_utc": manifest.get("snapshot_completed_at_utc"),
        "csv_sha256_computed": csv_hash,
        "raw_page_count": len(page_records),
        "candidate_issue_gaps": gaps,
        "duplicate_draw_dates": duplicate_dates,
        "calendar_attestation_sha256": calendar_hash,
        "calendar_source_document_sha256": calendar_source_hash,
        "errors": errors,
        "warnings": warnings,
        "continuity_status": "VERIFIED_AGAINST_OFFICIAL_CALENDAR" if calendar_verified else "NOT_VERIFIED_OFFICIAL_CALENDAR_REQUIRED",
        "publication_time_status": "SNAPSHOT_COMPLETION_PROXY_NOT_ORIGINAL_PUBLICATION_TIME",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot-dir", required=True)
    ap.add_argument("--cutoff-utc")
    ap.add_argument("--calendar-attestation", help="JSON with official source_url, retrieved_at_utc, status=VERIFIED, and exact draw_records")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    calendar_path = Path(args.calendar_attestation) if args.calendar_attestation else None
    result = audit_snapshot(Path(args.snapshot_dir), args.cutoff_utc, calendar_path)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "errors": len(result["errors"]),
                      "warnings": len(result["warnings"]), "output": str(out)}, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
