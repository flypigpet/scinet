# Public source and transformation map

All source paths below are relative to the original `panel-powerlaw-20261024-v3` run. This mapping documents the original-review and computation subset; it is not a publication manifest, an assertion of a complete replay bundle, or a root commitment. The final synthesis and publication metadata are maintained separately.

## Unchanged original bytes

| Public evidence file | Original relative path | Original SHA-256 |
|---|---|---|
| [packet.json](packet.json) | `packet.json` | `b877a3b83f02e1bbcb52620c92027eef7166a7c02a40bede76022fa4c41e49dc` |
| [protocol.json](protocol.json) | `protocol.json` | `96db02535948e11b3c58ebb0d91027258ad1be3fb0216129329d908cb507e9de` |
| [schema.json](schema.json) | `schema.json` | `c63e9e0c268b0c73ee571d38cf07b7caa64901653ad87cd0ef2120f0468d3c20` |
| [freezes/input_freeze.json](freezes/input_freeze.json) | `input_freeze.json` | `5a535be2506a8979fa87382b5bcae9b57bcf7d5846c6cc7e549f045f05ed5781` |
| [freezes/reviews_freeze.json](freezes/reviews_freeze.json) | `reviews_freeze.json` | `ed352d882543161f24c3b7c7ff6bbb126bcbc05a9a2f6af63a03420887208895` |
| [freezes/checks_freeze.json](freezes/checks_freeze.json) | `checks_freeze.json` | `8202e53d581f69db526e91f569a286d03d0e2f3c62c919bca500db435a350ac3` |
| [freezes/computation_inventory.json](freezes/computation_inventory.json) | `checks/artifacts/manifest.json` | `13eca74d9e11744e00fc859d7ff1190a288670ba76be6e1574ec2e1afce83f22` |
| [reviews/r1/response.json](reviews/r1/response.json) | `reviews/r1/response.json` | `1eed6ff3a51187d97580031a1af881cea31db6af2e3b8237f5e9171269b49036` |
| [reviews/r2/response.json](reviews/r2/response.json) | `reviews/r2/response.json` | `1323fcc60c495cdf5f40261098f068086fe9c37263f3b7d7f47850b10f3ac5c1` |
| [reviews/r3/response.json](reviews/r3/response.json) | `reviews/r3/response.json` | `57f862d77f35311b4c02fba808b7d967983e8ea01061efb3189843e4833ccd28` |

## Derived records

Computed JSON is parsed and placed under `result`, with provenance under `publication`. Call summaries retain selected original fields under `summary`. Each wrapper records its original path and original-byte SHA-256. The listed JSON pointers identify omitted fields; retained values are unchanged. No original observation arrays or local absolute paths are intentionally distributed.

| Public evidence file | Original relative path | Transformation |
|---|---|---|
| [computations/author_results.json](computations/author_results.json) | `checks/artifacts/verification/author_results.json` | Wrap; omit `/blackouts_xmin_candidates`. |
| [computations/blackouts_discrete_auto.json](computations/blackouts_discrete_auto.json) | `checks/artifacts/verification/blackouts_discrete_auto.json` | Wrap only; no source fields omitted. |
| [computations/compatibility.json](computations/compatibility.json) | `checks/artifacts/verification/runtime/compatibility.json` | Wrap only; no source fields omitted. |
| [computations/concern_checks.json](computations/concern_checks.json) | `checks/artifacts/verification/concern_checks.json` | Wrap; omit `/checks/1/empirical_points`, `/checks/1/empirical_left_cdf`, `/checks/2/counts/original_persons/noninteger_values`, `/checks/2/counts/scaled_thousands/noninteger_values`, `/checks/2/counts/rounded_thousands/noninteger_values`, `/checks/3/data`, `/checks/3/loglikelihoods`. |
| [computations/execution.json](computations/execution.json) | `checks/execution.json` | Wrap; omit `/command`. |
| [computations/exponential_precision.json](computations/exponential_precision.json) | `checks/artifacts/verification/exponential_precision.json` | Wrap; omit `/author/pointwise_loglikelihoods`. |
| [computations/extended_execution.json](computations/extended_execution.json) | `checks/artifacts/verification/extended_execution.json` | Wrap only; no source fields omitted. |
| [computations/independent_comparison.json](computations/independent_comparison.json) | `checks/artifacts/verification/independent_comparison.json` | Wrap only; no source fields omitted. |
| [computations/independent_continuous.json](computations/independent_continuous.json) | `checks/artifacts/verification/independent_continuous.json` | Wrap; omit `/provenance/input_path`, `/provenance/script_path`, `/provenance/executable`, `/candidate_scan`. |
| [computations/runner_execution.json](computations/runner_execution.json) | `checks/artifacts/execution.json` | Wrap; omit `/input_directory`, `/output_directory`, `/environment/executable`, `/stages/0/command`, `/stages/1/command`, `/stages/2/command`, `/stages/3/command`. |
| [computations/words_lognormal.json](computations/words_lognormal.json) | `checks/artifacts/verification/words_lognormal.json` | Wrap; omit `/comparison/pointwise_loglikelihoods`. |
| [computations/worm_comparisons.json](computations/worm_comparisons.json) | `checks/artifacts/verification/worm_comparisons.json` | Wrap; omit `/power_vs_exponential/pointwise_loglikelihoods`, `/power_vs_truncated/pointwise_loglikelihoods`. |
| [reviews/r1/call_summary.json](reviews/r1/call_summary.json) | `reviews/r1/call.json` | Selected call fields only; remove invocation, local paths, environment context names and session identifier. |
| [reviews/r2/call_summary.json](reviews/r2/call_summary.json) | `reviews/r2/call.json` | Selected call fields only; remove invocation, local paths, environment context names and session identifier. |
| [reviews/r3/call_summary.json](reviews/r3/call_summary.json) | `reviews/r3/call.json` | Selected call fields only; remove invocation, local paths, environment context names and session identifier. |

The [instruction prefix](review_instructions_prefix.txt) is extracted from `prompt.txt` up to the line before the JSON source packet; a final newline is added. [Its provenance](review_instructions_prefix.provenance.json) records the SHA-256 of the full original prompt, not the shortened file. No source-bearing prompt body is included.

The two case README files are newly written editorial descriptions. They are not model responses; they summarize both the source checks and the separately preserved accepted synthesis.

The full source bundle also contains the paper, datasets, author code, prompts and raw logs; those files are deliberately absent. Freeze manifests describe that larger bundle with relative paths. Their entries must not be interpreted as a claim that all referenced content is published here.

## Accepted synthesis continuation

The following unchanged files come from `panel-powerlaw-20261024-v3-synthesis3`. Synthesis call metadata is separately reduced to selected fields as documented within its wrapper. `attempt_history.json` is an editorial index of preserved local attempts.

| Public path | Original path | Original SHA-256 |
|---|---|---|
| `evidence/synthesis/response.json` | `synthesis/response.json` | `71b40f33cc98a985d78e547d365fa2dcc3564e390c0dcd67d0e0569acbdc3312` |
| `evidence/synthesis/schema.json` | `synthesis_schema.json` | `b9ccea7da8236938ec1c7591d72a2ea0f3f52e204d47293f824a2160f94bad76` |
| `evidence/synthesis/selection.json` | `synthesis_selection.json` | `b37176fa502e124595a1c0912f459a08129711859e653e212e4bd6ee350c0122` |
| `evidence/timeline.jsonl` | `timeline.jsonl` | `93d2a132dfca68a42bb92fb7b33c176be463af37df35f8866bfabcec48ceaeda` |
| `evidence/local_commitment.json` | `commitment.json` | `0b9ad1121730f78bbb2a40ab075c2d20adeae4273ae1ffbd45cee8fe060aa13b` |
