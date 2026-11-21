# Append-only Ledger Schema

## Status

Schema draft for DLT-PI-200. No forecast has yet been committed.

## Canonical public ledger

- `ledger/events.jsonl`: unified append-only event chain containing COMMIT and REVEAL records in chronological order.
- `private/prospective-vault/`: local-only sealed forecast payloads and nonces; ignored by Git and never uploaded before reveal.

Do not edit or delete an existing JSONL line. Corrections are new events referencing the earlier event hash.

## Commit workflow

From a local clone at the repository root:

```bash
python src/fetch_history.py --output-dir data/history_snapshot
python src/pi_digits.py --digits 600000 --output data/pi_digits_600000.txt
python src/generate_forecast.py --draw-id 27001 --cutoff-utc 2026-11-23T13:10:00Z --history data/history_snapshot/history_snapshot.csv --output private/forecast_27001.json
python src/prospective.py commit private/forecast_27001.json
```

Use the actual next eligible draw ID and its official cutoff; the values above are examples, not a live forecast. The commit command validates the exact five models, ten tickets per model, ranges, uniqueness and cutoff, then stores payload+nonce in the ignored private vault and appends a public COMMIT event.

Before the cutoff, publish the updated `ledger/events.jsonl` in a Git commit. Record the Git commit URL/SHA in the experiment log. For stronger independent timestamping, mirror the commitment hash and ledger head to a second public append-only timestamp service. A local file or Git commit alone is not absolute immutability.

## Reveal workflow

After the official result is published, create a result JSON with:
- `official_source_url`
- `retrieved_at_utc`
- `raw_source_sha256`
- `front` (five integer values)
- `back` (two integer values)
- `result_status` (VERIFIED or USER_SUPPLIED_PENDING_VERIFICATION)

Then run:

```bash
python src/prospective.py reveal DLT-PI-200 DRAW_ID result.json
python src/prospective.py verify
```

The reveal publishes the exact payload and nonce and recomputes the commitment. A public clone can verify revealed payloads without the private vault. An unrevealed commitment cannot be independently opened by the public, by design.

## Commitment encoding

- Canonical payload: UTF-8 JSON, sorted keys, compact separators, no NaN/Infinity.
- Nonce: cryptographically random 32 bytes, hex-encoded in the private vault until reveal.
- Commitment: SHA-256(canonical_payload_bytes || nonce_raw_bytes).
- Each event includes previous-event hash and its own SHA-256 record hash.

## Event fields

COMMIT includes experiment/draw IDs, cutoff, commitment hash, payload hash, private vault references and event-chain hashes. It never includes the nonce or full forecast payload.

REVEAL includes the original payload, nonce, official result metadata, and the original commitment reference. Corrections are appended as new events; never replace a prior reveal.

## Limitations

The local script verifies content identity and the local hash chain. It does not itself prove that the GitHub commit was made before the cutoff, nor does it query the external timestamp anchor. Those checks must be performed independently. A SHA-256 hash does not prove predictive value.
