# Ledger

This directory contains the append-only prospective record.

- `commitments.jsonl`: created before each draw cutoff; no nonce or ticket payload in public commit event.
- `reveals.jsonl`: created only after official result publication; includes original payload, nonce, source metadata and complete scoring.

Current status: no commitments, no reveals, 0/200 confirmatory draws.

Do not delete or edit entries. Append correction events with explicit references.
