# Public history evidence bundle and timestamp protocol

**Activation gate: BLOCKED until a real bundle passes audit and has two independently verifiable anchors.**

## Why two stages

1. Fetch a fresh snapshot from the official Sports Lottery history API. Preserve every raw page, the normalized CSV, manifest and source bundle.
2. Obtain the official draw calendar as a separate raw document from an HTTPS `*.sporttery.cn` source. A human must inspect the document and transcribe the complete `draw_id` / `draw_date` list into `calendar_attestation.json`. The file must name the raw document and its SHA-256, set `status=VERIFIED`, include a timezone-aware retrieval timestamp, source URL and exact `draw_records`.
3. Run `src/audit_history.py`. It must return `PASS`, with no warnings or errors. The auditor checks the hashes and exact ID/date equality but does not parse the official document; human transcription remains an explicit trust boundary.
4. Run `src/build_evidence_bundle.py build --snapshot-dir ... --audit-report ... --output-dir ...`. This copies all snapshot artifacts, raw API pages, calendar document, attestation and audit report into one content-addressed bundle. It refuses a warning-bearing audit and never overwrites a non-empty output.
5. Run `src/build_evidence_bundle.py verify --bundle-dir ...` after copying/publishing. Publish the bundle in this public repository under `evidence/history/<snapshot-id>/`.
6. Anchor `evidence_manifest.json` before any 200-payload panel is generated:
   - Primary anchor: a public GitHub commit containing the complete bundle and manifest. Record the full commit SHA and GitHub commit URL; verify its timestamp from GitHub's commit API, not a local clock.
   - Independent secondary anchor: OpenTimestamps proof for the exact manifest file/hash. Keep the `.ots` receipt beside the bundle. A pending proof is not yet a confirmed Bitcoin-calendar timestamp; periodically upgrade it and verify it with `ots verify`. Do not claim confirmation until verification succeeds.
7. Only after both anchors verify may the history evidence manifest hash and public commit SHA be passed into panel generation. Panel payloads must bind the same history CSV hash, audit hash, calendar source hash, evidence-manifest hash and public anchor SHA.

## Candidate vs public bundle

A candidate snapshot is not yet public evidence and must not be used for C-model features. A snapshot that passes the local raw-page audit but lacks a separately checked official calendar is not complete. Do not fabricate calendar rows from the same history API or a third-party portal.

## Commands

```bash
python src/fetch_history.py --output-dir data/history_candidate/2026-11-21T235900Z
# Preserve the official calendar source document in that directory.
# Create calendar_attestation.json only after manually checking the raw official document.
python src/audit_history.py \
  --snapshot-dir data/history_candidate/2026-11-21T235900Z \
  --calendar-attestation data/history_candidate/2026-11-21T235900Z/calendar_attestation.json \
  --output data/history_candidate/2026-11-21T235900Z/audit_report.json
python src/build_evidence_bundle.py build \
  --snapshot-dir data/history_candidate/2026-11-21T235900Z \
  --audit-report data/history_candidate/2026-11-21T235900Z/audit_report.json \
  --output-dir evidence/history/2026-11-21T235900Z
python src/build_evidence_bundle.py verify --bundle-dir evidence/history/2026-11-21T235900Z
ots stamp evidence/history/2026-11-21T235900Z/evidence_manifest.json
# Commit the complete bundle and .ots receipt; then upgrade/verify the proof.
```

## Hard sequencing rule

Do not generate the 200-payload panel until:
- the bundle audit is PASS;
- every bundle file verifies against the manifest;
- the GitHub commit is public and independently checked;
- the OpenTimestamps proof is verified (not merely pending);
- the panel generator has been updated to embed the manifest hash and public anchor identifiers.

After that, generate exactly 200 synthetic/frozen panel payloads using the production generator. These are **simulation inputs, not prospective predictions**. Compute the exact A/B1/B2/C/D fixed-portfolio covariance, then run at least 100,000 covariance-aware simulations per registered null/alternative scenario. If the actual portfolio geometry or C-history snapshot changes, regenerate the panel and power report; do not reuse a stale panel.
