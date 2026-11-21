#!/usr/bin/env python3
"""One-seed-per-draw ceremony. Creates a private seed once and a public commitment.

The public commitment JSON must be independently timestamped (e.g. committed to
the public GitHub repository) BEFORE forecast generation. Never rerun with a
replacement seed. A failed generation is a recorded technical failure.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "private" / "seeds"
PUBLIC = ROOT / "ledger" / "seed_commitments"

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()

def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create", help="create exactly one seed commitment for a draw")
    p.add_argument("--draw-id", required=True)
    p.add_argument("--cutoff-utc", required=True)
    args = ap.parse_args()

    cutoff = dt.datetime.fromisoformat(args.cutoff_utc.replace("Z", "+00:00"))
    if cutoff.tzinfo is None:
        raise ValueError("cutoff must include Z or an explicit UTC offset")
    if dt.datetime.now(dt.timezone.utc) >= cutoff.astimezone(dt.timezone.utc):
        raise ValueError("cutoff has passed")

    # Restrict identifiers to safe filename characters.
    if not args.draw_id or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.draw_id):
        raise ValueError("draw-id may contain only ASCII letters, digits, hyphen and underscore")

    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    seed_path = PRIVATE / f"{args.draw_id}.seed"
    public_path = PUBLIC / f"{args.draw_id}.json"

    # Both files use exclusive creation: a second ceremony for this draw fails.
    seed = secrets.token_bytes(32)
    seed_hex = seed.hex()
    commitment = hashlib.sha256(seed).hexdigest()
    record = {
        "experiment_id": "DLT-PI-200",
        "draw_id": args.draw_id,
        "created_at_utc": utc_now(),
        "scheduled_cutoff_utc": args.cutoff_utc,
        "seed_commitment_sha256": commitment,
        "seed_bytes": 32,
        "algorithm": "SHA-256(seed_bytes)",
        "status": "AWAITING_EXTERNAL_TIMESTAMP_BEFORE_GENERATION"
    }
    try:
        fd = os.open(seed_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as f:
            f.write(seed_hex + "\n")
            f.flush()
            os.fsync(f.fileno())
        fd = os.open(public_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb") as f:
            f.write(canonical(record) + b"\n")
            f.flush()
            os.fsync(f.fileno())
    except FileExistsError:
        raise SystemExit("SEED_CEREMONY_ALREADY_EXISTS: do not create or select a replacement seed")
    print(json.dumps({
        "status": record["status"],
        "draw_id": args.draw_id,
        "seed_commitment_sha256": commitment,
        "public_commitment_file": str(public_path.relative_to(ROOT)),
        "private_seed_file": str(seed_path.relative_to(ROOT)),
        "next_step": "Publish the public commitment file to the public repository and obtain an independent timestamp BEFORE running generate_forecast.py. Never publish the private seed."
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
