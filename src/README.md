# Source code

- `fetch_history.py`: retrieves paginated draw records from the official Sports Lottery API (`gameNo=85`), stores raw page responses, and creates a normalized CSV plus SHA-256 manifest.
- `pi_digits.py`: deterministic Chudnovsky binary-splitting π digit generator; standard library only.
- `generate_forecast.py`: builds all five model portfolios and the canonical pre-draw payload.
- `prospective.py`: commit–reveal event ledger; stores the unrevealed payload and nonce only in the ignored local `private/` vault.
- `audit_draw.py`: scores every ticket after the draw and reports descriptive results without claiming a one-draw edge.
- `tests/`: unit tests for the generator and π digit source.

Suggested preparation:

```bash
python src/fetch_history.py --output-dir data/history_snapshot
python src/pi_digits.py --digits 1000000 --output data/pi_digits_1000000.txt
python -m unittest discover -s tests -v
python src/prospective.py verify
```

The history downloader records the retrieval timestamp as `published_at_utc` for every row. This is a conservative snapshot-time proxy, not the exact original publication timestamp. A snapshot can only be used for a forecast cutoff strictly later than its retrieval time. It never backdates data.

The forecast generator intentionally fails closed on invalid history, post-cutoff history rows, invalid ticket structure, insufficient π digits, or duplicate portfolios. It does not publish commitments by itself. Run `python src/prospective.py commit <payload.json>` to append a COMMIT event, then publish `ledger/events.jsonl` before the cutoff. After the result, run `python src/prospective.py reveal <experiment_id> <draw_id> <result.json>`. The private vault must never be committed.

Before use, preserve the API raw pages, manifest, CSV, π source file, exact Python runtime version, and source-code hashes. Do not assume pagination completion alone proves historical completeness; audit issue continuity and source revisions.
