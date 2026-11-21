# Implementation Audit — 2026-11-21

## State

- Design parameters: USER-APPROVED.
- Confirmatory cohort: 0 / 200.
- Experiment active: NO.
- Forecast commitments: 0.
- Official results audited: 0.

## Checks completed in this work session

| Check | Status | Evidence |
|---|---|---|
| 600,000-digit π computation | COMPUTED | Chudnovsky binary-splitting reproduction; SHA-256 in data/pi_600000.manifest.json |
| π known-prefix check | PASS | First 50 decimal digits match the embedded known prefix |
| π window allocation smoke test | PASS | Five draw identifiers × A/B1/B2; 2,048-digit windows; front/back separated; 10 distinct tickets per model |
| GitHub repository access | VERIFIED | Public repository; default branch main; write permission available |
| GitHub Actions CI | NOT VERIFIED | Base CI and new power workflow exist; latest runs/logs for the expanded test suite have not been independently inspected |
| Official history snapshot | MISSING | Downloader, cutoff-safe snapshotting and raw-page auditor implemented; no real official snapshot has yet been retrieved and audited |
| Power simulation | PRELIMINARY | 100,000-replicate-per-scenario parametric reference report published; actual model-specific covariance and final inferential method remain open |
| Seed anti-reroll control | IMPLEMENTED WITH RESIDUAL TRUST | One-time seed ceremony, persistent fail-closed lock, generator and ledger checks implemented; external timestamp authenticity remains manually verified |
| Commit–reveal integration | NOT VERIFIED | Code exists; clean round-trip and public independent-anchor test remain outstanding |

## Important implementation reconciliation

The approved design is 600,000 digits, not 1,000,000. The default in src/pi_digits.py and the forecast generator / ledger instructions has been aligned to 600,000. The actual code uses a deterministic per-draw/per-zone SHA-256 window selector; A/B1/B2 share the same windows and differ only by the declared digit transform. Documentation must continue to describe this implementation, not the earlier fixed-offset table.

The implemented C/D random stream is SHA-256 counter mode with rejection-based randbelow, not Python random.Random. The model registry and parameter record have been updated accordingly.

## Blocking defects / controls before activation

1. Independently verify the public seed commitment anchor (full commit SHA and timestamp) against GitHub and a second timestamp service. The local scripts validate supplied anchor fields but do not query the external service themselves.
2. Calibrate the power simulation using a verified 200-payload portfolio panel and the exact 4×4 exposure covariance matrix; freeze the final confirmatory test and confidence-interval method. The current reference power result is not a power certification.
3. Add integration tests for complete 50-ticket generation, invalid payload rejection, duplicate commits, cutoff enforcement, commit/reveal verification and tamper detection.
4. Execute CI on the declared Python versions and inspect successful logs.
5. Retrieve a fresh official history snapshot into a timestamped directory, require the raw-page audit to PASS, and reconcile candidate issue gaps against the official draw calendar. Cross-snapshot corrections still require review.
6. Freeze exact Python patch version, runner image, code hashes, data hashes and analysis-plan hash.
7. Independently timestamp the activation record and every forecast commitment before the official draw cutoff.

No claim of predictive edge, adequate power, official history completeness, or experiment activation is made.


## Addendum — verification after this audit (2026-11-21)

- GitHub Actions run #20: SUCCESS. Both `unit-tests (3.11)` and `unit-tests (3.12)` completed successfully. Run: https://github.com/wxgzlj/-dlt-pi-200/actions/runs/44915210201
- The passing suite currently contains six basic unit tests across `tests/test_generator.py` and `tests/test_pi_digits.py`. This does not establish full integration correctness, seed anti-reroll, commit/reveal tamper resistance, historical data completeness, or statistical power.
- The 600,000-digit π manifest is present. It records an independent reproduction in CPython 3.13.5, not a clean run of the repository generator; local regeneration and SHA-256 comparison remain required.
- `src/README.md` contained an obsolete 1,000,000-digit command; it is being corrected to the approved 600,000-digit value.
- Seed-shopping prevention and the power/inference implementation remain CRITICAL blockers. Confirmatory cohort remains 0/200.


## Addendum — seed governance implementation (2026-11-21)

Implemented in commits:
- \`c278d197a7f3e6898562361e059874dbbc983839\`: one-time seed ceremony.
- \`847eb80ff4319d2ba26de43043ef349c9183053b\`: generator requires private seed, matching public commitment and a pre-cutoff anchor attestation.
- \`5af77db3dab8c8c1c97221e1ddaaad5c212d1752\`: documented procedure.
- \`444cb49cda0b9efb0d48d3836fdd1814c498e49b\`: anti-reroll source tests.

The ceremony uses exclusive file creation for one seed path per draw. The generator no longer creates a seed internally; it verifies SHA-256(private seed) against the public commitment and checks that the supplied anchor attestation names the same hash and predates the draw cutoff.

Residual limitation: the generator validates the anchor-attestation JSON fields but does not independently query GitHub or a trusted timestamp authority. An operator could still lie about the timestamp or manipulate an unanchored local copy. Verify the anchor URL, full commit SHA and commit time independently before generation; preserve a second timestamp receipt where feasible. The process materially narrows seed-shopping opportunities but is not a cryptographic trustless enforcement system.

CI runs #25 and #26 completed successfully on the generator/seed-ceremony commits; run #27 completed successfully on the new seed source tests. Run #28 for the documentation update was still in progress at the time of this addendum.


## Addendum — fail-closed seed ceremony and integration coverage (2026-11-21)

- Commit `16419008f2daecc0e7018d0f4cfad15b49c3a140` adds a persistent per-draw ceremony lock created with exclusive file creation before requesting entropy. The lock is intentionally retained after any interruption; a partial ceremony cannot be silently retried with a replacement seed.
- Commit `dec8f8f12f02d2cb7330119c4b15f739f32f4eda` adds subprocess integration tests for seed/commitment hash agreement, restrictive file permissions, duplicate invocation rejection, pre-existing public commitment rejection, and timezone-aware cutoff enforcement.
- CI workflow uses unittest discovery, so the new integration test module is included automatically. The new commits' CI result must be inspected before marking the integration suite PASS.
- Residual trust boundary remains: the generator checks anchor-attestation fields but does not independently verify GitHub's commit object or a trusted timestamp receipt. The seed ceremony is stronger against accidental/ordinary rerolls, not trustless against a malicious operator.
- Confirmatory cohort remains **0/200**. No forecast has been committed or independently anchored for the confirmatory cohort.


## Addendum — seed provenance enforced by the ledger (2026-11-21)

- Commit `2f99df63130eca6c2618671bf97417f631d9a351` adds a dedicated seed-provenance validator at the commit boundary; commit `e61d726f293ea091c4c9b3e23d2d46d849a6f103` removes duplicated legacy checks after consolidation.
- The ledger now rejects payloads missing the 32-byte root seed, commitment hash, seed-anchor attestation or timezone-aware creation time. It verifies SHA-256(root seed), anchor hash binding, a full 40-character Git commit SHA, and the ordering: anchor timestamp < forecast creation timestamp < draw cutoff.
- Commit `4f359da1b03db3110f39ef9425033034f213c90a` adds unit tests for valid provenance, seed-hash mismatch, late anchor, naive timestamp and abbreviated commit SHA.
- Important boundary: these checks establish internal consistency and chronology in supplied fields; they do **not** fetch GitHub's commit object or prove the timestamp independently. Human/external anchor verification remains mandatory.
- CI result for these latest commits has not yet been independently confirmed. Do not label the new tests as passing until the corresponding GitHub Actions run is inspected.

## Addendum — ledger-boundary enforcement and power-analysis specification (2026-11-21)

- Commit `32936e018d55f6b52e4486d2660aaf2f95588cae` adds defense-in-depth validation in `prospective.py`: the commit layer now independently checks the 32-byte root seed, SHA-256 commitment, matching seed-anchor hash, required anchor URL/full commit SHA, timezone-aware pre-cutoff anchor time, and forecast creation time after the anchor and before cutoff. A hand-built payload can no longer bypass the generator's seed-governance checks.
- Commits `7f2136c8a16d5df569bd42a21a48bbf960fd8e9c` and `83b1264b33a370938ae24ece1a4a86d62b82cd32` add focused commit-layer tests for valid anchored commit, missing anchor, seed-hash mismatch, and late anchor. The tests use temporary paths and do not touch the live ledger.
- Commit `98697ea73d758cf5042f0471f97c098ff739f63e` adds rollback of partial seed/public-file writes while preserving the persistent one-attempt lock. A crash or failed ceremony remains a protocol deviation; it must not trigger a replacement seed.
- Commit `8e13d226dced5e02668b9e9ae2d3bb294a3263da` adds `POWER_ANALYSIS_SPEC.md`, a proposed draw-cluster Monte Carlo specification. It defines a single-focal exponential-tilt alternative calibrated to +0.10 front hits/ticket, Holm-adjusted paired tests, null calibration, and Monte Carlo error. This is a specification only: no simulation has run, no power estimate exists, and the proposed inferential details are not yet frozen.
- Documentation now marks seed governance as implemented with manual external-anchor verification; the experiment remains inactive.
- CI result for the newest commits has not yet been independently inspected. Do not mark the new test suite PASS until both Python matrix jobs are confirmed successful.
- Remaining critical blockers: execute and audit the 100,000+ simulation power study; retrieve and continuity-audit official history; run complete generator/commit/reveal/verify and tamper integration tests; independently verify timestamp anchors; freeze runtime; and publish a separately anchored activation record.

Confirmatory cohort remains **0/200**; no forecast has been committed for the confirmatory cohort.

## Addendum — preliminary Monte Carlo power engine (2026-11-21)

- Added `src/power_analysis.py`, `tests/test_power_analysis.py`, `POWER_ANALYSIS_PLAN.md`, and `results/power_analysis_preliminary.json`.
- The simulation ran **100,000 replicates per scenario** (five effect levels plus three noise-inflation scenarios; 800,000 experiments total), CPython 3.13.5, `random.Random` MT19937, base seed `2026112101`.
- Reference variance is derived from Hypergeometric(35,5,5), with a finite-population correction for ten distinct tickets sampled from the 324,632 legal front-zone combinations. Under independent uniform candidate/D portfolio assumptions, paired draw-level SD = 0.3286942.
- At the registered +0.10 MDE, estimated target-comparison power is 96.213% (95% Wilson Monte Carlo interval 96.093%–96.330%). Simulated null family rejection rate is 4.347% (95% Wilson interval 4.222%–4.475%).
- Sensitivity: at 1.25×, 1.50× and 2.00× reference SD, MDE power is 82.291%, 63.642% and 35.911%, respectively.
- Local power-engine tests: 5/5 passed on CPython 3.13.5. GitHub Actions execution for the new workflow/test combination has not yet been independently inspected; do not mark CI PASS.
- Provenance: source SHA-256 `2983612aa9b810a04c52b4ba47d4ddf1aa7fc1b2b286ce5f5ed22be40af6080a`; power-plan SHA-256 `8c2fbc79bb9047fa8805b7d45e00dbb3f1abbe46d03fb3b9adb19a1fc75fe465`; preregistration reference commit `d64002531a9a6661c533cb47acdc48d8a89e2ead`.
- Critical limitations: this is a parametric location-shift planning model, not a physical lottery alternative or backtest. It assumes independent candidate residual vectors; it does not calibrate A/B1/B2 dependence induced by shared π windows or actual C/D portfolio exposure. Final confirmatory test and CI method remain unfrozen. **Power adequacy remains NOT CERTIFIED; cohort remains 0/200.**


## Addendum — exact portfolio exposure covariance module (2026-11-21)

- Added `src/portfolio_covariance.py`, `tests/test_portfolio_covariance.py`, and `PORTFOLIO_COVARIANCE.md`.
- For each fixed ten-ticket portfolio, the module converts tickets into 35-number exposure counts and computes the exact covariance of model mean-hit scores under a uniform 5-of-35 winning draw. It then constructs the full 4×4 covariance matrix for A-D, B1-D, B2-D and C-D, including shared-control and cross-model overlap effects.
- For a 200-payload panel it requires exactly 200 distinct non-empty draw IDs and reports average per-draw covariance plus covariance of the 200-draw mean. It rejects duplicate tickets and invalid front-zone values.
- The analytic covariance formula was checked against exhaustive enumeration on a smaller finite population. Six local tests passed on CPython 3.13.5, including duplicate draw-ID rejection and the identical-portfolio zero-variance invariant.
- This closes an important mathematical tooling gap but does **not** yet produce a real model-specific power estimate: no verified 200-payload panel exists, the verified C-history snapshot is still missing, and the power engine has not yet been integrated with this covariance matrix. Power adequacy remains NOT CERTIFIED; confirmatory cohort remains 0/200.


## Addendum — history snapshot timestamp and pagination controls (2026-11-21)

- `src/fetch_history.py` now assigns `snapshot_retrieved_at_utc` only after all pages have been fetched, rather than timestamping rows at retrieval start. This closes a cutoff-crossing leakage window in which a long pagination run could otherwise include a later page after the cutoff while retaining an earlier timestamp.
- It re-fetches page 1 after pagination and compares issue/date/result signatures to detect new-head insertion that can shift page-number pagination. A changed first page causes the snapshot to fail closed.
- It refuses to overwrite an existing snapshot directory's manifest/CSV/raw page files; use a new timestamped output directory. It records retrieval start, completion time, raw page hashes and a source bundle.
- `src/generate_forecast.py` now requires the explicit `snapshot_retrieved_at_utc` field, requires all rows to share one completion timestamp, checks that timestamp strictly precedes cutoff, and enforces chronological date ordering. Forecast payload labels this as a snapshot-completion availability proxy, not an original publication timestamp.
- A new `tests/test_history_snapshot.py` covers cutoff enforcement, mixed snapshot rejection, old ambiguous column rejection, chronology, and official API normalization. CI result remains to be inspected.
- Limitation: page-1 recheck detects a shifting head but does not prove that older pages were not corrected during the fetch. Raw pages and hashes are preserved for audit; full page-by-page historical revision reconciliation remains open.


## Addendum — raw history snapshot auditor (2026-11-21)

- Added `src/audit_history.py` and `tests/test_audit_history.py`. The auditor is read-only and verifies the official endpoint/game identifier, manifest and source-bundle consistency, CSV SHA-256, raw-page SHA-256/byte counts, API page error codes, issue-ID reconciliation between raw pages and normalized CSV, row counts, chronological order, shared snapshot-completion time, and optional forecast-cutoff eligibility.
- Candidate numeric issue gaps and duplicate draw dates are reported as warnings requiring the official draw calendar; they are not silently classified as missing draws.
- Four local synthetic-fixture audit tests passed on CPython 3.13.5, including detection of CSV tampering, raw-page tampering and post-cutoff snapshots. The six history-schema tests also passed locally. GitHub Actions results remain unverified.
- The auditor does not fetch or independently certify the official draw calendar, and a single snapshot cannot reveal all historical corrections. Cross-snapshot comparison remains open.


## Addendum — history audit bound into generation and commit (2026-11-21)

- `generate_forecast.py` now requires `--history-audit` and rejects any audit report not exactly `PASS`, any warnings/errors, or mismatches in CSV SHA-256, row count, or snapshot-completion timestamp. The audit report and its canonical SHA-256 are embedded in the forecast payload.
- `prospective.py` independently revalidates the embedded audit report at the commit boundary: canonical report hash, PASS status, no warnings/errors, exact history CSV hash, draw count, and snapshot completion timestamp must all match. A hand-built payload cannot bypass the history audit gate.
- Added `tests/test_history_audit_gate.py` for generator and commit-layer acceptance/rejection cases. CI result remains to be independently inspected.
- Updated `SEED_CEREMONY.md` and `LEDGER_SCHEMA.md` examples to require the audit report and seed provenance inputs.
- Activation remains blocked until a real official snapshot is fetched into a fresh timestamped directory, audited with no unresolved warnings, and the audit-bound generator/commit/reveal path passes end-to-end tests. Confirmatory cohort remains 0/200.


## Addendum — covariance-aware power simulation mode (2026-11-21)

- `src/power_analysis.py` now accepts `--portfolio-covariance` from the 200-payload output of `src/portfolio_covariance.py` and `--target-model A|B1|B2|C` to run model-specific focal comparisons.
- Added a positive-semidefinite Cholesky factorization and Bartlett/Wishart multivariate-t simulation so the supplied 4×4 covariance matrix informs both numerator dependence and studentized variance. The simulation uses average per-draw covariance as a common covariance; draw-to-draw heteroskedasticity remains an approximation.
- Added tests for Cholesky reconstruction, non-PSD rejection, and deterministic covariance-aware simulation. Local isolated tests passed; GitHub Actions results remain unverified.
- No real 200-payload panel has been generated because a verified history snapshot for C is still missing. The committed JSON is the reference-only baseline generated by the current covariance-capable engine without a portfolio panel; it is not a model-specific covariance-calibrated power report. Power adequacy remains NOT CERTIFIED; cohort remains 0/200.


## Addendum — independent draw-calendar attestation gate (2026-11-21)

- `audit_history.py` now returns full `PASS` only when a separate calendar-attestation JSON is supplied. It requires `status=VERIFIED`, a source URL on the official `sporttery.cn` domain, a timezone-aware retrieval timestamp before the forecast cutoff, and an exact match of every `draw_id` / `draw_date` pair against the snapshot.
- Without this attestation, a technically intact snapshot is only `PASS_WITH_WARNINGS`; the forecast generator and commit ledger reject it. Candidate issue gaps and duplicate draw dates are not guessed away; they must be reconciled against the official calendar.
- Added tests for absent attestation, exact match, mismatched issue list and late calendar retrieval. The fetch-history integration fixture now supplies a synthetic official-calendar attestation for deterministic testing; this is test data only, not a real production calendar verification.
- Activation now requires a real official calendar record, not merely a self-consistent API snapshot. This deliberately keeps the experiment inactive until independent continuity evidence exists.


## Addendum — calendar attestation raw-source binding (2026-11-21)

- The official calendar attestation now also requires a preserved raw source document inside the snapshot directory and its SHA-256. The auditor rejects path traversal, missing source documents, and source-document hash mismatches.
- The audit report carries both the attestation JSON hash and raw calendar document hash; the forecast generator embeds the report and the commit layer rechecks its canonical hash and verified-continuity status.
- Test fixtures use synthetic calendar source bytes only to exercise the pipeline; they are not evidence of an actual official calendar reconciliation.


## Addendum — public history-evidence availability remains open (2026-11-21)

- The local history audit now verifies raw API pages, normalized CSV, official calendar attestation, preserved calendar source bytes and hashes. The generator/commit layer requires a PASS report with verified calendar continuity.
- Residual reproducibility gap: the snapshot directory is currently local/ignored and the generator does not yet require a public GitHub commit anchoring the CSV, raw pages, calendar source document, attestation and audit report. Their hashes are embedded in the forecast payload, but a public reviewer may not be able to retrieve the underlying evidence bundle.
- Before activation, publish the evidence bundle (or a durable public artifact) and independently timestamp its manifest before forecast generation. The forecast payload should bind the evidence-manifest hash and public commit SHA. This remains an explicit activation blocker, not a completed control.


## Addendum — calendar attestation semantic verification boundary (2026-11-21)

- The auditor checks the attestation's official-domain HTTPS URL, timezone-aware retrieval time, preserved source-document bytes/hash, and exact issue/date-set equality between the supplied `draw_records` and CSV.
- It does not parse the HTML/PDF to prove that the supplied `draw_records` were transcribed correctly from the source. The operator must manually inspect the preserved official calendar document. This is a human-verified provenance assertion, not an automated independent extraction or cryptographic proof.


## Addendum — isolated local validation after provenance hardening (2026-11-21)

- Local isolated harness results: 8/8 history-auditor tests, 9/9 covariance-aware power tests, and 7/7 exact portfolio-covariance tests passed. The separate six-case history-schema harness also passed earlier.
- These are targeted local checks of the revised algorithms/fixtures, not a substitute for running the repository's full Python 3.11/3.12 GitHub Actions workflow. The latest repository CI result remains **NOT VERIFIED**.
- The fetch-history mocked integration test and full generator→commit→reveal→verify round-trip still require repository CI and end-to-end execution.
