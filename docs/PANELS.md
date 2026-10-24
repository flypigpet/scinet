# Independent-context AI review panels

SciNet's experimental panel workflow gives several requested models the same original paper materials, freezes all their reviews, and only then runs a selected reproduction script. A separate model call compares the preserved opinions with the resulting evidence. The original opinions remain visible, including disagreement and untested claims.

This is an evaluation experiment, not an automated publication decision. Different model IDs do not establish independent training or independent errors. The current transport uses one provider through the authenticated Codex CLI.

## Run a panel

Install from the repository using Python 3.12. The historical powerlaw reproduction example additionally needs `python -m pip install ".[powerlaw]"`. Install and authenticate Codex CLI separately; this transport targets CLI `0.163.0-alpha.11.2` and fails if its isolation settings are unsupported.

Prepare a local source directory and a `bundle.json` inventory. Every file has an original source URL, SHA-256 digest, role and explicit model-visibility flag. A file marked visible must be UTF-8 text. Binary PDFs can be archived with visibility disabled; figures are then not visible to the reviewers. No content is silently truncated.

For a ready source packet, follow the [powerlaw example](../examples/powerlaw/README.md). Its acquisition command downloads pinned original materials and builds the inventory without running author code or any model. Network, source-hash or extraction failures are retained and do not produce a usable packet.

```json
{
  "paper": {"title": "Paper title", "doi": "Paper DOI or source identifier"},
  "selection_disclosure": "Describe why this paper was selected and any prior knowledge of its findings.",
  "files": [
    {
      "path": "paper.txt",
      "role": "paper",
      "sha256": "REPLACE_WITH_SHA256_OF_THE_ACTUAL_FILE",
      "source_url": "https://example.org/original-paper",
      "include_in_review": true
    }
  ]
}
```

Paths are relative to the inventory directory. Allowed roles are `paper`, `code`, `data`, `readme` and `license`. Include original data and code as additional entries. Do not mark previous reviews, selected defects or calculated results as original inputs. SciNet can check the file inventory and protocol; it cannot establish from a filename that a source has never been edited or that an operator has no prior knowledge.

Replace the model placeholders with distinct identifiers available to your account:

```sh
scinet panel review --bundle work/inputs/bundle.json --output work/panel-01 --model MODEL_A --model MODEL_B
scinet panel recompute work/panel-01 --script examples/powerlaw/recompute.py
scinet panel synthesize work/panel-01 --model SYNTHESIS_MODEL --evidence-list examples/powerlaw/synthesis-evidence.json
scinet panel verify work/panel-01
```

The powerlaw script applies only to the specific historical source/data hashes it recognizes. For another paper, select an appropriate inspected reproduction script. The script receives `INPUT_DIRECTORY OUTPUT_DIRECTORY`; the output directory must not exist yet. It must write actual results and return a nonzero exit code on execution failure. Its contents, command, outputs, errors and environment are recorded. Model-suggested shell commands are never executed automatically. The timeout is not a sandbox for arbitrary uploads.

The same sequence can run in one command:

```sh
scinet panel run --bundle work/inputs/bundle.json --output work/panel-01 --model MODEL_A --model MODEL_B --script examples/powerlaw/recompute.py --synthesis-model SYNTHESIS_MODEL --evidence-list examples/powerlaw/synthesis-evidence.json
```

Model calls require network access and use the account's allowance. Every reviewer receives the complete selected text packet. The synthesis model additionally receives original reviews and selected text computation artifacts. Use only materials you are authorized to send to that service.

## Choose computation evidence for synthesis

By default, synthesis includes every computation artifact with a supported text extension under `checks/artifacts/`. A large run can exceed the model client's input limit. SciNet does not silently cut files, shorten reviews or discard evidence to make the call fit.

The powerlaw commands above use the checked-in [17-file selection](../examples/powerlaw/synthesis-evidence.json): all computation JSON files, the compatibility diff and verification scripts. It excludes duplicate input/source copies and raw logs from the prompt while retaining all original files in the local evidence bundle. The selection follows artifact types and coverage, not whether a numerical result favors a review. Other papers need their own lists matched to their reproduction scripts.

To choose the computation files explicitly, save a JSON array such as `work/synthesis-evidence.json`:

```json
[
  "checks/artifacts/verification/author_results.json",
  "checks/artifacts/verification/independent_comparison.json",
  "checks/artifacts/verification/concern_checks.json"
]
```

These are logical paths relative to the panel run, not paths relative to the JSON file. Each entry must name a unique existing text artifact under `checks/artifacts/`, and the array must not be empty. The short list above illustrates the format; select enough evidence for the actual questions, including execution and compatibility records where needed.

```sh
scinet panel synthesize work/custom-panel --model SYNTHESIS_MODEL --evidence-list work/synthesis-evidence.json
```

`scinet panel run` accepts the same `--evidence-list` option. It resolves the listed artifact paths after reproduction. Original model-visible source materials, every original review and `checks/execution.json` are always supplied; this option selects only additional computation artifacts.

`synthesis_selection.json` records the included and excluded artifact paths, byte counts and hashes. The model sees that inventory and the full contents of selected files. Excluded files remain unchanged in the local bundle, but their contents are not supplied to that synthesis call. No selected file is truncated. A list still too large can fail; a list too narrow can leave findings unresolved or not tested. Record the reason for selection when documenting a case, and do not describe a subset as the complete computation evidence seen by the model.

## Continue after a synthesis failure

A failed review blocks computation. A failed reproduction is also incomplete; neither can be repaired by the synthesis continuation command. Preserve that attempt and start a new panel when new reviews or computation are needed.

If all reviews and reproduction completed but synthesis failed, keep the source run intact and continue only synthesis in a new directory:

```sh
scinet panel continue-synthesis work/panel-01 --output work/panel-01-synthesis-02 --model SYNTHESIS_MODEL --evidence-list examples/powerlaw/synthesis-evidence.json
scinet panel verify work/panel-01-synthesis-02
```

The source must pass verification and have state `checks_completed` or `synthesis_failed`. The destination must not exist and must be outside the source directory. The command archives the complete source run under the destination's `parent_bundle/`, including any failed synthesis, and reuses its frozen inputs, original reviews and computation records without changing them. It snapshots the continuation implementation, records the parent commitment, and appends a continuation event to the inherited timeline.

Only a new synthesis call is made. Reviewers and reproduction are not run again, and the source directory is never changed. `continuation.json` makes that reuse explicit; verification checks the archived parent and the inherited frozen evidence. A continuation is not a fresh panel experiment. If that synthesis also fails, preserve its directory and use another new continuation destination.

## What is kept

| Record | Purpose |
| --- | --- |
| `packet.json`, `inputs/`, `source_inventory_original.json` | Exact submitted material, source metadata and model-visible subset |
| `prompt.txt`, `schema.json`, `input_freeze.json` | Identical neutral instructions and frozen inputs for all reviewers |
| `protocol.json`, `implementation/` | Protocol, disclosure, environment and source snapshot |
| `reviews/rN/` | Unmodified response, raw events, stderr and call metadata for each member |
| `reviews_freeze.json` | The complete review set fixed before computation |
| `checks/`, `checks_freeze.json` | Selected script, runtime, logs, outputs and frozen computation evidence |
| `synthesis_prompt.txt`, `synthesis_inputs.json`, `synthesis/` | Separate post-computation interpretation with exact finding coverage |
| `synthesis_selection.json` | Included and excluded computation artifacts, their byte counts and hashes, without deleting excluded evidence |
| `continuation.json`, `parent_bundle/`, `continuation_implementation/` | When continuing synthesis: parent identity, complete archived attempt, reused evidence and current implementation snapshot |
| `timeline.jsonl` | Hash-linked local stage records |
| `report.html` | Original positions and subsequent verification shown separately |
| `commitment.json` | Deterministic commitment over the complete local artifact inventory |

Calls record the requested model, actual CLI version, requested configuration, raw outputs and timing. The resolved backend remains unknown unless independently reported by the service; a model mentioning its own name is not an attestation. Known CLI tools and repository instructions are disabled, and calls with tool events or incomplete streams are rejected. This does not prove absence of hidden provider instructions, prior training familiarity or prompt-injection effects.

A failed attempt remains recorded. It cannot silently become a completed review or proceed to computation. Review or reproduction failures require a new panel attempt; a synthesis failure can use the explicitly recorded continuation above. Original reviews cannot be rewritten by either synthesis path.

## Reading disagreement and verification

Groups distinguish agreement, explicit disagreement, different scope and a topic mentioned by only one reviewer. Absence is not a vote. Each finding separately records whether its opinion is supported, refuted, partly supported, unresolved or not tested, with a basis of computation, source inspection or insufficient evidence. Confirming a reviewer's concern supports that concern; it does not validate the paper's underlying claim.

These labels and groups are generated by the synthesis model. Structural validation checks references and complete coverage; it does not prove that a cited passage supports a judgment. The report preserves the originals so people can challenge the grouping or interpretation. No accuracy rate, consensus truth or expert validation is inferred from the number of models.

## Preparing for later signatures or blockchain records

The commitment hashes a canonical JSON payload listing every file's relative path, byte count and SHA-256 digest. It includes nested manifests and excludes only the root `commitment.json` itself. The format defines its own serialization; it is not RFC 8785 or a Merkle proof.

Save the `root_sha256` independently, then verify against it:

```sh
scinet panel verify work/panel-01 --expected-root SHA256_SAVED_ELSEWHERE
```

This detects replacement of an otherwise self-consistent local bundle. Without an external reference, a person able to rewrite every file can also regenerate its hashes. Signatures, identity verification, trusted timestamps, external storage availability and blockchain anchoring are not implemented. The record format provides bytes that those later systems can sign or anchor; it does not claim they have already done so.

Full inputs and raw logs are kept locally. Publishing a case requires checking source licenses and redacting private paths or account metadata into a separate public subset, with its own inventory. A public subset must never be described as the full replay bundle.
