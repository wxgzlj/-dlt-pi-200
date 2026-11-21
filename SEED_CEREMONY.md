# Seed Ceremony — DLT-PI-200

This procedure is mandatory for every confirmatory draw. It prevents choosing among multiple random seeds after inspecting generated tickets.

## 1. Create exactly one seed

Run once from the repository root, before the draw cutoff:

\`\`\`bash
python src/seed_ceremony.py create --draw-id 26134 --cutoff-utc "YYYY-MM-DDTHH:MM:SSZ"
\`\`\`

The script creates:
- Private 32-byte seed: \`private/seeds/26134.seed\` (ignored by Git; never publish).
- Public commitment: \`ledger/seed_commitments/26134.json\`.

Both files use exclusive creation. If either already exists, the command fails. Do not delete the files, change the seed, or try again. Record any failure as a protocol deviation.

## 2. Timestamp the public commitment

Publish only \`ledger/seed_commitments/26134.json\` to the public repository. Record the exact Git commit SHA, commit URL and UTC timestamp in a separate anchor attestation file:

\`\`\`json
{
  "seed_commitment_sha256": "<exact hash from the public commitment>",
  "anchor_url": "https://github.com/wxgzlj/-dlt-pi-200/commit/<commit-sha>",
  "anchor_commit_sha": "<full commit sha>",
  "anchored_at_utc": "<GitHub commit timestamp in UTC>"
}
\`\`\`

Save as \`ledger/seed_commitments/26134.anchor.json\`. The anchor must be created before the official draw cutoff. A repository commit is public evidence, but GitHub alone is not an independent immutable timestamp authority; preserve a second timestamp receipt where possible.

Before forecast generation, run `python src/audit_history.py --snapshot-dir data/history_snapshot/<snapshot_id> --cutoff-utc "<official-cutoff-utc>" --output data/history_snapshot/<snapshot_id>/audit.json` and require `status=PASS` (or explicitly resolve every warning). Use the same audited CSV path below.

## 3. Generate forecast once

Only after the public seed commitment has been timestamped:

\`\`\`bash
python src/generate_forecast.py \
  --draw-id 26134 \
  --cutoff-utc "YYYY-MM-DDTHH:MM:SSZ" \
  --history data/history_snapshot/<snapshot_id>/history_snapshot.csv \
  --history-audit data/history_snapshot/<snapshot_id>/audit.json \
  --seed-file private/seeds/26134.seed \
  --seed-commitment ledger/seed_commitments/26134.json \
  --seed-anchor ledger/seed_commitments/26134.anchor.json \
  --output private/26134.forecast.json
\`\`\`

The generator checks that the private seed hashes to the public commitment, that the experiment/draw identifiers match, that the anchor precedes forecast creation and cutoff, and that the supplied history-audit report is PASS and matches the exact CSV hash, row count and snapshot completion timestamp. It includes the seed hash, anchor reference and history-audit report/hash in the forecast payload.

Then validate and commit the forecast using the commit–reveal process. Do not rerun generation with a replacement seed. A technical failure is a recorded failure, not permission to draw another seed.

## 4. Important limitation

The generator validates the contents of the anchor-attestation JSON; it does not independently query GitHub or a trusted timestamp authority to prove the referenced commit time. The operator must verify the URL, commit SHA and timestamp against the public service before running the generator. This is an explicit residual trust boundary, not a cryptographic guarantee.
