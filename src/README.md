# Source code

- `fetch_history.py`: retrieves paginated draw records from the official Sports Lottery API (`gameNo=85`), preserves raw pages, rechecks page 1 for pagination drift, and writes a non-overwritable timestamped snapshot with a completion-time availability proxy.
- `audit_history.py`: read-only audit of CSV and raw-page hashes, page-to-CSV issue reconciliation, timestamp/cutoff consistency, and candidate issue gaps.
- `pi_digits.py`: deterministic Chudnovsky binary-splitting π digit generator; standard library only.
- `generate_forecast.py`: builds all five model portfolios only from a previously committed seed and timestamp-attestation file.
- `seed_ceremony.py`: creates exactly one 32-byte seed and its public SHA-256 commitment per draw using exclusive file creation.
- `prospective.py`: commit–reveal event ledger; stores the unrevealed payload and nonce only in the ignored local `private/` vault.
- `power_analysis.py`: parametric Monte Carlo power-planning engine with Holm correction and Wilson Monte Carlo intervals.
- `portfolio_covariance.py`: exact model score covariance from fixed front-number exposure vectors under a uniform 5-of-35 draw.
- `audit_draw.py`: scores every ticket after the draw and reports descriptive results without claiming a one-draw edge.
- `tests/`: unit and integration tests for π generation, ticket generation, seed governance, power-analysis mathematics, exact portfolio covariance, history snapshot schema, and raw-source audit.

Suggested preparation:

```bash
SNAPSHOT_DIR="data/history_snapshot/$(date -u +%Y%m%dT%H%M%SZ)"
python src/fetch_history.py --output-dir "$SNAPSHOT_DIR"
python src/audit_history.py --snapshot-dir "$SNAPSHOT_DIR" --calendar-attestation "$SNAPSHOT_DIR/calendar_attestation.json" --output "$SNAPSHOT_DIR/audit.json"
python src/pi_digits.py --digits 600000 --output data/pi_digits_600000.txt
# Follow SEED_CEREMONY.md; point --history to "$SNAPSHOT_DIR/history_snapshot.csv".
python -m unittest discover -s tests -v
python src/prospective.py verify
```

The history downloader records the snapshot completion time as `snapshot_retrieved_at_utc` for every row. This is a conservative availability proxy, not the exact original publication timestamp. It rechecks page 1 after pagination to detect a shifting API result set, refuses to overwrite an existing snapshot, and only permits use when snapshot completion strictly precedes the forecast cutoff.

The forecast generator intentionally fails closed on invalid history, post-cutoff or mixed-snapshot history rows, a missing/non-PASS history audit, audit/CSV hash mismatch, invalid ticket structure, insufficient π digits, mismatched seed commitments, missing/late anchor attestations, or duplicate portfolios. The preliminary power report is a parametric reference only; model-specific covariance calibration and integration with `power_analysis.py` remain open. The anchor JSON is operator-verified; the script does not independently query GitHub. It does not publish commitments by itself. Run `python src/prospective.py commit <payload.json>` to append a COMMIT event, then publish `ledger/events.jsonl` before the cutoff. After the result, run `python src/prospective.py reveal <experiment_id> <draw_id> <result.json>`. The private vault must never be committed.

The approved experiment parameter is 600,000 decimal digits, not 1,000,000. Before use, preserve the API raw pages, manifest, CSV, π source file, exact Python runtime version, and source-code hashes. Seed anti-reroll and power/inference implementation are still activation blockers. Do not assume pagination completion alone proves historical completeness; audit issue continuity and source revisions.
