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
| GitHub Actions CI | NOT VERIFIED | Workflow exists, but passing run/logs have not yet been inspected |
| Official history snapshot | MISSING | No committed raw snapshot/manifest or continuity audit yet |
| Power simulation | MISSING | MDE and target power approved; simulation/test implementation not yet published |
| Seed anti-reroll control | MISSING | Current generator creates a fresh OS seed on each invocation; one-seed-per-draw commitment must be implemented before activation |
| Commit–reveal integration | NOT VERIFIED | Code exists; clean round-trip and public independent-anchor test remain outstanding |

## Important implementation reconciliation

The approved design is 600,000 digits, not 1,000,000. The default in src/pi_digits.py and the forecast generator / ledger instructions has been aligned to 600,000. The actual code uses a deterministic per-draw/per-zone SHA-256 window selector; A/B1/B2 share the same windows and differ only by the declared digit transform. Documentation must continue to describe this implementation, not the earlier fixed-offset table.

The implemented C/D random stream is SHA-256 counter mode with rejection-based randbelow, not Python random.Random. The model registry and parameter record have been updated accordingly.

## Blocking defects / controls before activation

1. Prevent seed shopping. A single root seed must be committed to an independent public timestamp before generation. A second seed commitment for the same draw must be rejected. A failed generation must be recorded as a technical failure, not rerun with a replacement seed.
2. Complete the simulation-based power analysis. It must define the alternative-generation mechanism for a +0.10 front-hit MDE, draw-level paired test, confidence intervals, Holm correction and Monte Carlo error. Publish fixed seed and at least 100,000 simulations.
3. Add integration tests for complete 50-ticket generation, invalid payload rejection, duplicate commits, cutoff enforcement, commit/reveal verification and tamper detection.
4. Execute CI on the declared Python versions and inspect successful logs.
5. Retrieve the official history snapshot and audit draw IDs, dates, missing issues, duplicates, corrections, valid ranges and source hashes. Snapshot retrieval time must not be backdated.
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
