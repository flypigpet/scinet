# Changelog

## Unreleased — experimental AI panels

- Add `scinet panel` commands for separate model reviews of one original packet, complete review freezing before reproduction, and a separate evidence-based synthesis.
- Preserve original opinions, disagreement, scope differences and untested findings alongside model requests, raw client records, source inventories and execution evidence.
- Add explicit synthesis evidence lists with hashes and byte counts for included and excluded computation artifacts. Preserve the full local evidence and send selected files without silent truncation.
- Add `panel continue-synthesis` for verified runs whose reviews and computation completed. Archive the full parent attempt and reuse frozen evidence in a new directory, recording a separate synthesis call without rerunning reviewers or calculations.
- Add local event records and deterministic evidence commitments, including verification against a hash saved separately. These are unsigned; no blockchain anchoring or trusted timestamp is claimed.
- Add powerlaw source acquisition and a portable, hash-pinned historical-code reproduction example. Python 3.12 and the `powerlaw` dependency extra are required for that example.
- Keep the original Datasaurus guided, single-model path as a legacy demo. Distinguish it from the new panel protocol throughout the documentation.
- Publish a three-model powerlaw case with 20 unchanged original findings, accepted synthesis, selected numerical evidence and a verifiable public inventory. Record mismatched printed values, untested observations, evidence selection and failed attempts.
- Document shared-provider limits, unknown resolved backends, reused targeted checks and pending human scientific validation. A completed live workflow is not a measurement of scientific-review accuracy.

These source changes do not update the existing `v0.1.0a1` tag.

## Documentation update — 24 October 2026

- Publish a bilingual case from the fresh `gpt-6-astra` review, including the unchanged structured response, numerical evidence, source links and limitations.
- Record the unknown resolved backend, guided text-only scope, automated follow-up and pending human scientific validation.
- Publish an inventoried evidence subset with path redactions and its own file manifest; keep full paper/page text, complete prompts and raw logs local.
- No application behavior, package version or existing release tag changed.

## 0.1.0a1 — alpha preview

- Package SciNet for installation from source with a `scinet` command and a separate local workspace.
- Include attributed MIT numerical fixtures for an offline, single-paper demo; acquire paper and webpage materials separately into the user's workspace.
- Recompute 65 statistics through two implementations and record precision conventions, a bounded author-function run, source hashes and a local HTML evidence report.
- Require explicit model selection for new optional Codex reviews and preserve honest call provenance. Historical calls whose model was not reported remain unknown.
- Add bilingual setup instructions, contribution and security guidance, collective citation metadata, and explicit AI, asset-rights and reproducibility disclosures.
- Prepare automated checks for the public repository. Their presence does not imply a successful CI run or scientific validation.

This preview retains the original single-paper, guided-review scope. Human scientific validation remains pending. Local historical runs, downloaded full text and the old full-evidence archive are not public release artifacts.
