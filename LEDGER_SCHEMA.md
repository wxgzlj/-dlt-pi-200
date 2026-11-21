# Append-only Ledger Schema

## Status

Schema draft for DLT-PI-200. No forecast has yet been committed.

## Files

- `ledger/commitments.jsonl`: one append-only commitment event per draw.
- `ledger/reveals.jsonl`: one append-only reveal/audit event per draw.
- `ledger/README.md`: operational notes and event statuses.

Never edit an existing JSONL line. A correction is a new event referencing the earlier event hash.

## Canonical payload

Each forecast payload must contain:
- experiment_id
- draw_id
- scheduled_cutoff_utc
- created_at_utc
- game_rules_id
- model_registry_sha256
- analysis_plan_sha256
- code_sha256
- environment_manifest_sha256
- pi_source_sha256 (A/B1/B2 only)
- historical_snapshot_sha256 (C only)
- PRNG metadata and frozen seed/substream (stochastic models)
- exactly 10 tickets for each of A, B1, B2, C, D
- all model parameters
- nonce (32 random bytes as 64 lowercase hex characters)

## Commitment encoding

1. Serialize payload as UTF-8 JSON with lexicographically sorted object keys, compact separators `(",", ":")`, no NaN/Infinity, and no trailing newline.
2. Decode nonce from 64-character hex to 32 raw bytes.
3. Compute `SHA256(payload_utf8_bytes || nonce_raw_bytes)`.
4. Store the lowercase 64-character hex digest as the commitment.

The exact canonical JSON bytes and a known test vector must be implemented and tested before activation. The nonce is secret until reveal. Do not commit the nonce in the public commitment event.

## Commitment event fields

- schema_version
- event_type = "COMMIT"
- experiment_id
- draw_id
- created_at_utc
- scheduled_cutoff_utc
- payload_sha256
- commitment_sha256
- previous_event_sha256 (null for first event)
- repository_commit_url
- external_anchor_reference (required before activation; a GitHub commit alone is not fully independent)

## Reveal event fields

- schema_version
- event_type = "REVEAL"
- experiment_id
- draw_id
- revealed_at_utc
- payload (or immutable payload file reference)
- nonce
- official_result
- official_source_url
- source_retrieved_at_utc
- raw_source_sha256
- recomputed_commitment_sha256
- commitment_verified (boolean)
- per-ticket scoring
- model-level and draw-level summary
- previous_event_sha256

## Ledger integrity

Every event is hashed and references the previous event hash. The event chain is an audit aid; it does not replace independent timestamp anchoring. Public Git commits and an independent timestamp/append-only mirror should be retained. Do not force-push or rewrite published history.
