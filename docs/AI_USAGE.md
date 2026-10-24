# AI use and evidence

SciNet has two review paths. `scinet panel` gives several requested models the same original material and runs reproduction only after all reviews are frozen. The earlier Datasaurus `run --ai` path gives one model selected questions and already-computed results. They answer different experimental questions; records from one must not be described as the other.

**Human scientific validation remains pending (`human_validation_pending`).** Neither the number of models nor the software tests establish scientific-review accuracy, expert endorsement or readiness to make publication decisions.

## Experimental panels

See [panel commands and records](PANELS.md) and the [powerlaw example](../examples/powerlaw/README.md). Install and authenticate Codex CLI separately. Model IDs must be explicitly selected and available to the account; examples do not imply entitlement to a model or service allowance.

Every reviewer receives the same frozen, model-visible UTF-8 text packet: original paper text, author code, data and source metadata selected in the inventory. The generic instructions do not suggest particular defects, supply earlier reviews or provide calculated results. Each requested model gets a fresh session, and all original responses are frozen before the selected reproduction script runs.

A separate synthesis call receives the original reviews and selected text computation artifacts after reproduction. It groups related opinions and classifies their relationship to the evidence. This step does not rewrite the original answers. Agreement, explicit disagreement, different scope, singly raised topics and untested findings remain distinguishable. A missing comment is not a negative vote. Supporting a reviewer's concern is not the same as confirming the paper's underlying claim.

Synthesis includes all supported computation text artifacts by default. An explicit `--evidence-list` JSON array can instead select existing text paths under `checks/artifacts/`. The original model-visible sources, every original review and the computation execution record are still supplied. Selected files are sent in full; excluded file contents are not sent to that call, but their paths, byte counts and hashes are disclosed in `synthesis_selection.json` and to the model. All original files remain in the local bundle. This is an explicit evidence subset, not silent truncation; it may limit which findings can be assessed. See [selection and continuation commands](PANELS.md#choose-computation-evidence-for-synthesis).

The current transport uses the same provider through Codex CLI for every requested model. Separate contexts and different model IDs do not prove independent training, independent errors or freedom from familiarity with a paper. The powerlaw packet discloses prior SciNet case history; its directed reproduction checks were developed in an earlier case. The new reviewer packet excludes those checks and old results, but the coordinating operator is not blind to them.

## What is sent and kept

Model calls need network access and use the account's service allowance. All selected reviewer text is sent to the model service; the synthesis call additionally sends original reviews and selected computation artifacts. Use only material you are authorized to send through that service. Binary PDF files can be archived without being model-visible; the powerlaw example supplies extracted text, not rendered figures.

The local panel bundle keeps:

- The exact source inventory, input files, prompt, response schema and frozen packet hashes.
- Each requested model, actual CLI version, requested configuration, timings, response, raw event stream and stderr.
- The complete review freeze before reproduction, the selected script, environment, execution logs and actual outputs.
- The separate synthesis inputs, included/excluded artifact inventory and response, original opinions in the report, local event records and a final file commitment.
- For a synthesis continuation, the complete archived parent attempt, unchanged reused evidence, parent commitment, continuation record and new implementation snapshot.

A requested model ID is not proof of the resolved backend. If the service does not independently report the backend or effective settings, they remain unknown. A model naming itself in its answer is not a provider attestation. Never assign a guessed identity to an old call.

The panel disables known CLI tools and repository instruction discovery, checks the event stream, and rejects observed tool calls or incomplete calls. It does not prove the absence of provider-side instructions, training memories, automatic retries or prompt-injection effects. The recorded settings target a particular CLI version; unsupported isolation settings are failures, not silently weakened guarantees.

Authentication failures, launch errors, timeouts, invalid structures and protocol failures are preserved as failed attempts. They are not successful reviews, and SciNet does not substitute canned answers. A failed reviewer blocks reproduction; use a new run to retry. Model-suggested commands are never automatically executed.

A synthesis failure after completed reviews and reproduction can be continued with `scinet panel continue-synthesis` into a new directory. This verifies and archives the source, reuses its frozen reviews and computation, and makes only a new synthesis call. It does not rewrite the failed attempt, rerun the reviewers or rerun the calculations. Records explicitly distinguish reused phases from the new interpretation. Continuation is allowed only from `checks_completed` or `synthesis_failed`; it cannot bypass failed review or reproduction. A client input-limit failure remains a failure even when a later selected-evidence continuation succeeds.

## Reading the results

Synthesis labels and groups are model interpretations. Structural validation checks required fields, allowed references and finding coverage; it does not prove that a cited page or code path supports a judgment. People must check those relationships. The original opinions and evidence remain available to challenge a mistaken synthesis.

A reproduction script covers selected computations. A timeout is not a sandbox, and passing a numerical check does not validate all assumptions, novelty or scientific importance. State missing checks and unavailable evidence directly. Do not convert untested findings into agreement or calculate a review-accuracy rate without an appropriate reference standard.

The local commitment and event chain are unsigned. Hash verification can compare files to a separately saved reference; it cannot establish author identity, trusted chronology or scientific truth. Signatures, blockchain anchoring and governance are still planned. See the [panel guide](PANELS.md#preparing-for-later-signatures-or-blockchain-records).

Full local bundles may contain licensed full text, private paths and account metadata in raw logs. A public case should be a separately reviewed subset with its own inventory and omissions listed. It must not be described as the full replay bundle unless it actually is one.

## Completed panel case

The [24 October 2026 powerlaw case](cases/2026-10-24-powerlaw-panel/README.md) contains 20 unchanged findings from separate calls requesting `gpt-6.1-sol`, `gpt-6-astra` and `gpt-6-sol`. All three received an identical neutral prompt before computation. A later `gpt-6.1-sol` call synthesized the frozen opinions with selected evidence. Requested identifiers, unresolved backend versions, usage, source hashes, failed attempts and evidence selection are disclosed. The example confirms a functioning workflow, not measured review accuracy or provider independence.

## Legacy Datasaurus demo

The default `scinet --workspace demo run` does local numerical work without calling a model. Its optional guided review is explicit:

```sh
python scripts/acquire.py --workspace demo
scinet --workspace demo run --ai --model MODEL_ID
```

Replace `MODEL_ID` with an available model. An existing unreviewed run with acquired inputs can be reviewed using `scinet --workspace demo review RUN_DIR --model MODEL_ID`.

This path sends paper text, project-page text, author source, selected claims, computed statistics and author-function results to the model service. Its prompt directs attention to standard-deviation definitions, rounding conventions and webpage/paper differences. It tests guided auditing, not independent discovery in a review-before-computation panel. The original local demonstration did not capture its model identity; that identity remains unknown.

The [24 October 2026 published Datasaurus case](cases/2026-10-24-datasaurus-live-review/README.md) records a fresh call requesting `gpt-6-astra` through Codex CLI `0.163.0-alpha.11.2`. It returned four assessments in 70.434398 seconds. Its resolved backend and effective reasoning setting remain unknown. The unchanged structured answer, numerical results, instruction prefix, input hashes, source map and path-redacted call summary are public; complete prompts, paper/page text and raw event logs remain local. This is an inventoried public subset, not a complete replay bundle or provider attestation.

The coordinating assistant and a separate automated subagent checked that case's findings, including selected PDF pages. This is automated follow-up, not human domain-expert validation, a multi-model panel or measured accuracy. Publishing that historical case did not involve another model call.

## Development assistance

Codex assisted with implementation, tests, documentation and release preparation. The project is attributed collectively to SciNet contributors; AI tools are not listed as authors or assigned human qualifications. Development tests and automated code inspection are not a person's scientific review.

For later human validation, record who performed it with their consent, what they checked, the version and materials, and unresolved disagreements. Do not infer credentials or endorsement.
