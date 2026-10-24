# Three models, 20 preserved observations, bounded numerical checks

**Case date: 2026-10-24. Subject: the original 2014 `powerlaw` paper supplements, not the current `powerlaw` package.**

[中文](README.zh-CN.md) · [Paper and original supplements](https://doi.org/10.1371/journal.pone.0085777)

Three requested models reviewed the same source packet in separate fresh sessions, without a supplied defect list, earlier reviews, or computed results. All **20 original observations** remain available, unchanged. After their responses were frozen, selected calculations supported three implementation concerns within the tested historical paths. Some printed numbers were not reproduced exactly; several other observations were not tested numerically.

**The full workflow completed.** The accepted [synthesis response](evidence/synthesis/response.json) covers all 20 original findings without rewriting them. It requested `gpt-6.1-sol` and took 355.13 seconds; its [call summary](evidence/synthesis/call_summary.json) records configuration, usage, hashes and the unresolved backend identity. The summary below is maintained editorially; the original model outputs are separate artifacts.

## What actually ran

| Reviewer | Requested model | Original observations | Call duration | Raw response |
|---|---|---:|---:|---|
| r1 | `gpt-6.1-sol` | 8 | 83.83 s | [Unchanged JSON](evidence/reviews/r1/response.json) |
| r2 | `gpt-6-astra` | 7 | 146.58 s | [Unchanged JSON](evidence/reviews/r2/response.json) |
| r3 | `gpt-6-sol` | 5 | 62.74 s | [Unchanged JSON](evidence/reviews/r3/response.json) |

All three call records report `completed`, exit code 0, and no observed tool calls. Their full prompts have the same SHA-256, `86dc6133079ca501f13ba6a9464a46961bcc1bcc4464d09cd11132efc07834fa`. The [instruction prefix](evidence/review_instructions_prefix.txt) is public; the full source-bearing prompt is not.

These are **requested identifiers**. The immutable backend model was not resolved (`model_resolved: null`); the report does not infer one from generated text. The [r1](evidence/reviews/r1/call_summary.json), [r2](evidence/reviews/r2/call_summary.json), and [r3](evidence/reviews/r3/call_summary.json) summaries retain CLI version, timings, usage, input hashes and observed-tool status. Separate sessions do not establish independent training, providers, errors or absence of prior familiarity.

The [reviews froze](evidence/freezes/reviews_freeze.json) at **03:45:54 UTC**. [Computation](evidence/computations/execution.json) began at **03:47:45 UTC**, finished at **03:48:14 UTC**, and exited 0. The [runner record](evidence/computations/runner_execution.json) reports nine selected author fits, independent continuous calculations, four directed checks and four extended checks. Execution completion is distinct from scientific correctness.

## Three concerns with bounded numerical support

| Original observations | This run measured | What remains outside the result |
|---|---|---|
| Finite upper-bound normalization: r1/F2, r2/F2, r3/F3 | For fixed continuous `Power_Law` parameters `xmin=1`, `xmax=10`, `alpha=2`, the PDF integrates to **0.9**, while the CDF reaches **1**. The discrete PMF sums to 1 but its left cumulative mass at 10 is **0.993547**, while the code returns 1. | Other subclasses, the finite-bound word-frequency figure, the `round` branch and effects on published fitted values were not numerically checked. |
| Ignored KS fitting option: r1/F3, r2/F3 | For the fixed continuous blackout tail, both requested fitting methods return `alpha=2.272637`, `D=0.060674`. Independent minimization of the same stated distance gives `alpha=2.203524`, `D=0.040363`. | This does not reject default maximum-likelihood fitting. Discrete KS branches and outer threshold selection were not tested by this check. |
| Explicit `nested=False` overridden: r1/F4, r2/F4 | In one argument order, the object interface returns **p=0.382195**, matching the nested formula; passing False directly gives **p=0.532438**. Reversing the order preserves False. | Both values exceed 0.05 in this example. This is an option-handling check, not calibration of the nested statistical test or a claim about all scientific conclusions. |

Evidence: [C1–C4 numerical records](evidence/computations/concern_checks.json), under `result.checks`. C1's retained English scope sentence is ambiguous: the intended interpretation is that these finite-bound checks **do not invalidate default fits without `xmax`**. It is not a finding that all default fits are affected.

The runner's C3 also measures sensitivity to noninteger inputs in a discrete model. It was a reused check; none of this panel's 20 original observations explicitly raised that issue. It must not be counted as a new discovery by this panel.

## What reproduced, and what did not

The [independent continuous implementation](evidence/computations/independent_continuous.json) and the adapted historical author implementation agree within an absolute **1e-12** for five selected fits and the candidate scan. This establishes numerical agreement for the disclosed formulas and inputs; it does not validate every statistical definition or the whole paper. [Comparison record](evidence/computations/independent_comparison.json)

| Quantity | Printed paper | Current bounded run |
|---|---:|---:|
| Default blackout exponent | 2.273 | 2.272637 |
| Default blackout `xmin` and distance | 230; 0.061 | 230; 0.060674 |
| Default blackout standard error | **0.167** | **0.165683**, rounding to 0.166 |
| Blackouts: power law vs exponential `(R, p)` | (12.755, 0.152) | (12.754563, 0.152293) |
| Words: power law vs lognormal `(R, p)` | (0.928, 0.426) | (0.928018, 0.425846) |
| Worm: power law vs exponential `(R, p)` | (16.384, 0.024) | (16.384325, 0.024184) |
| Worm: power law vs truncated power law `(R, p)` | **(-0.081, 0.687)** | **(-0.070652, 0.706989)** |

Sources: [author fits](evidence/computations/author_results.json), [word comparison](evidence/computations/words_lognormal.json), [worm comparisons](evidence/computations/worm_comparisons.json). The two highlighted mismatches remain disclosed. Their cause has not been isolated. The latter comparison remains nonsignificant at 0.05 in both versions; this does not establish model equivalence. The historical optimizer's convergence flag is not retained by its implementation.

## Untested observations and apparent disagreement

- r1/F5 and r2/F5 identify replacement of a valid zero log density. The published runner did not execute the proposed `Lambda=1` boundary case. Its [exponential precision check](evidence/computations/exponential_precision.json) uses a different fitted rate and is not that test.
- r1/F6 and r3/F5 identify an ignored plot-axis argument; no two-axis plotting test was executed.
- r3/F2 identifies a lower-bound comparison involving `None`. It was not executed here. Python 3 changed cross-type ordering, so a modern-environment error would not by itself establish failure in the original Python 2 environment. [Python's migration documentation](https://docs.python.org/3/whatsnew/3.0.html#ordering-comparisons)
- r3/F4 identifies `gamma: None` in the object-oriented supported-distribution map. This is a source-inspection observation; neither that entry point nor the separate functional gamma implementation was run by these checks.
- Full Figure S1 simulation, dependence-aware inference, absolute goodness-of-fit and statistical calibration remain untested.

r1/F8 is labelled `supported`, while r2/F7 is labelled `concern`, but their substantive explanations agree: the paper discusses independence limitations, and failure to distinguish two distributions does not prove equivalence or adequate absolute fit. Different labels and emphasis are not evidence of a scientific disagreement. Silence by a third reviewer is not agreement or disagreement.

## Selection, adaptation and public evidence boundaries

This was a purposively selected software-paper case already known to the coordinator. **Selection and check design were informed by the earlier case; the experiment was not double blind.** The source packet withheld previous reviews and computations from the reviewers. Directed and extended checks were reused after freezing the new reviews, not independently designed by these models. The [protocol](evidence/protocol.json) and [runner record](evidence/computations/runner_execution.json) disclose this. This one case is not a model-accuracy benchmark.

The subject is PLOS's original 2014 Code S1/S2, with data pinned to commit `d2b563a7a08bad96b4085fa69f351e9d9a20b1e7`. A [compatibility record](evidence/computations/compatibility.json) discloses Python 2 conversion, modern array comparisons, mask inversion and an API relocation. The original environment was not reconstructed. In particular, the historical behavior of the original NumPy mask expression was not established. Results make no claim about the current package.

The public subset contains:

- All three original review responses, byte for byte; [packet](evidence/packet.json), [protocol](evidence/protocol.json) and [review schema](evidence/schema.json).
- The instruction prefix and its source hash; selected call summaries with local paths, invocation, environment-context names and session identifiers removed.
- Original relative-path [input](evidence/freezes/input_freeze.json), [review](evidence/freezes/reviews_freeze.json) and [check](evidence/freezes/checks_freeze.json) freeze inventories, plus the [computation inventory](evidence/freezes/computation_inventory.json).
- Selected computed JSON, with `publication` provenance and the retained record under `result`. Each wrapper declares its original SHA-256 and omitted fields. Local paths and observation-level arrays are removed; retained numerical values are not changed.

Paper text/PDF, datasets, author source, full prompts and raw logs are withheld. The freeze inventories describe the full local bundle, including files absent from this public subset; they do not make this subset a complete replay bundle. Hashes identify bytes and local changes, not author identity, trusted execution time, scientific truth or blockchain attestation. There was no human domain-expert validation.

## Synthesis and integrity records

The accepted synthesis groups the findings into 10 topics: 8 compatible groups and 2 raised by a single reviewer, with no explicit disagreement identified. It labels 11 findings `supported`, 8 `partly_supported`, and 1 `unresolved`. These labels concern **evidence for a reviewer's observation**, not acceptance votes for the paper or measured model accuracy. Twelve positions use computation as their basis; eight use source inspection and must not be represented as executed tests.

Synthesis received an [explicit selection of 17 computation files](evidence/synthesis/selection.json), original readable sources, and all three original reviews. Excluded files remain inventoried by path, size and hash. The first synthesis exceeded a client input limit; another returned a response but was rejected for a recovered connection diagnostic. Both remain failed attempts. The accepted continuation made only a new synthesis call, reusing the exact original reviews and computation. Two earlier startup failures are also disclosed. [Attempt history](evidence/attempt_history.json) · [Workflow event chain](evidence/timeline.jsonl)

The [full local commitment](evidence/local_commitment.json) is `75da6b7b5a05564ac37489328ef0a4eb0685373efd6bae998e864a570913c1f8`. It covers the complete local files and two archived predecessors, many of which are not public. The curated public subset has a separate [file inventory](publication.json); these scopes are not interchangeable. See the [source and transformation map](evidence/SOURCES.md). These references can support later signing and blockchain anchoring; no signature, trusted timestamp or blockchain transaction exists yet.

Verify the public files from the repository root:

```sh
python docs/cases/2026-10-24-powerlaw-panel/verify.py
```
