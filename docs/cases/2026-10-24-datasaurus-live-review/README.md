# Public case: a live AI audit of *Same Stats, Different Graphs*

[中文案例](README.zh-CN.md) · [Project](../../../README.md) · [Publication inventory](publication.json)

On **24 October 2026 (Asia/Shanghai)**, SciNet completed a fresh model call after recomputing selected results from Matejka and Fitzmaurice's CHI 2017 paper. The model returned four evidence-linked assessments: **two qualified, one supported, and one not tested**. It also identified a temperature-comparison wording inconsistency, subsequently checked against the original PDF and author code by automated inspection.

This is a **guided, text-only audit of one known paper by one model**. It is a worked example of a traceable process, not a measured peer-review accuracy result. **Human scientific validation remains pending.** The full model response is published unchanged in Chinese; the English findings below are an editorial summary.

## Model and execution record

| Item | Recorded value |
| --- | --- |
| Requested model | `gpt-6-astra` (GPT-6-Astra) |
| Resolved backend / immutable snapshot | **Unknown**; not returned in the captured client events |
| Reviewer | One fresh Codex CLI model call; no independent-model ensemble |
| CLI | `codex-cli 0.163.0-alpha.11.2` |
| Start → finish, UTC | `2026-10-23T23:55:37.497224+00:00` → `2026-10-23T23:56:47.931622+00:00` |
| Local time | 24 October 2026, 07:55:37–07:56:47, UTC+08:00 |
| Call duration / exit | 70.434398 seconds / exit code 0 |
| Client-reported usage | 36,678 input tokens; 2,039 output tokens; 93 reasoning output tokens; 0 cached input tokens |
| Reasoning setting | Not explicitly set; effective runtime setting unknown |
| Implementation | SciNet `v0.1.0a1`, commit [`e6db99d`](https://github.com/flypigpet/scinet/tree/e6db99da565473785632096471ea3e8d2f53648b) |
| Numerical environment | Windows 11, Python 3.12.14, NumPy 2.3.5, pandas 3.0.1; complete package list in the call record |

The [call record](evidence/call-record.json) contains the normalized invocation, timings, package versions and hashes. The [original call provenance](evidence/review_provenance.json) is byte-for-byte preserved. `--ignore-user-config` was used; the machine's configured reasoning preference must not be assumed to have applied. A cached model default is not evidence of the effective runtime setting. Temporary model/plugin catalog refresh warnings occurred before a successful completion; raw warnings remain local.

These are captured **client records**, not a provider-signed attestation of the backend model. No monetary cost was returned, so token usage is not converted into a price.

## What the model actually received

The pipeline first computed the statistics and ran selected author functions. It then supplied six text inputs: extracted paper text, extracted project-page text, original author code, four predeclared claims, `metrics.json`, and `author_smoke.json`.

The [instruction prefix](prompt-instructions.txt) is exact, not a reconstruction. It explicitly cues standard-deviation conventions, floor/truncation/rounding, paper-versus-webpage distinctions and the limited reproduction scope. The complete prompt also contained the source texts; it is not redistributed. Its SHA-256 and all six original input hashes are published in the [call record](evidence/call-record.json) and [input hash record](evidence/review_input_hashes.json). The original [output schema](evidence/review_schema.json) is included.

The model did **not** call tools, recompute the numbers, inspect the individual coordinate files, or see figures, animations or the later PDF renders. Client events contained one agent-message item, and that message matched the saved response. The prompt assembly can be inspected in the [pinned pipeline](https://github.com/flypigpet/scinet/blob/e6db99da565473785632096471ea3e8d2f53648b/scinet/pipeline.py#L87-L128).

## Outcomes and their evidence

| Claim | Model assessment | Observed result and boundary |
| --- | --- | --- |
| C1: five statistics agree to two decimal places | Qualified | 13 datasets × 142 points = 1,846 rows. Floor and truncation each produce agreement, but ordinary nearest rounding (`ROUND_HALF_UP`) differs across datasets for all five statistics. |
| C2: the project webpage gives a positive correlation | Supported | The acquired Fig 5 caption gives `R=0.06`, with no literal plus sign. All computed correlations are negative; paper Figure 6 gives a negative value, −0.06. This is a webpage-caption issue. |
| C3: author functions can move points while maintaining their statistical constraint | Qualified | 1,000 proposals, 687 accepted, 313 rejected; all 142 points moved; coordinates remained finite and the floor-based statistical constraint passed. Only selected functions and an adapted driver were exercised. |
| C4: all experiments, animations, original trajectories and performance were reproduced | Not tested | This was a scope-control claim, not a success claim made by SciNet. The available work does not establish full-paper reproduction. |

See the unchanged [model response](evidence/review.json), [predeclared claims](evidence/claims.json), [numerical results](evidence/metrics.json), and [path-redacted execution record](evidence/author_smoke.json).

For C1, in the order mean x, mean y, sample SD x, sample SD y, Pearson r:

- Floor to two decimals: `[54.26, 47.83, 16.76, 26.93, -0.07]`.
- Truncation toward zero: `[54.26, 47.83, 16.76, 26.93, -0.06]`.
- The paper's Figure 6 display is consistent with truncation; the display alone does not establish how the authors generated it.
- Standard deviations use `n−1`. The maximum difference between the standard-library and pandas/NumPy computation paths was `7.105427357601002e-15`, below `1e-10`. These are two calculations on the same data, not independent scientific studies.

C2's original claim uses `+0.06` as shorthand for a positive value; the response correctly notes that the page has no explicit `+` glyph. The website snapshot was acquired on **23 October 2026 at 10:08:51 UTC**. The live page may subsequently change.

For C3, two pandas assignments were adapted to `.loc`; package loading, plotting and the original CLI entry point were omitted. Mean distance from the circle target decreased from `9.626466015989623` to `9.455052975996075`. This small change does not establish circular convergence. The 1.462-second smoke run is not comparable to the paper's full experiment runtime. The exact [adapter](evidence/author_smoke/adapter.py), [seed](evidence/author_smoke/seed-original.csv), [generated coordinates](evidence/author_smoke/generated.csv), and [raw numerical result JSON](evidence/author_smoke/smoke-result.json) are included with the original MIT notice. The author-code subprocess has a timeout, not an arbitrary-code security sandbox.

## Additional observation: temperature comparison

Within F3, the model identified a discrepancy that was not specifically named in the instruction prefix:

| Location | Comparison described or implemented |
| --- | --- |
| Original PDF, page 3, first paragraph | Temperature less than the random value |
| Original PDF, page 2, pseudocode line 10 | Temperature greater than the random value |
| Author `perturb`, [line 398](https://github.com/jmatejka/same-stats-different-graphs/blob/b4d82f3a2ff8ef5849fecbdfab6dccafccbc1370/samestats/samestats.py#L398) | Random value less than temperature |

The coordinating assistant and a separate automated subagent checked the source. After the review, PDF pages 2 and 3 were rendered and inspected to rule out an extraction artifact. The [post-review assessment](evidence/evidence_assessment.json) records this check separately from the untouched model answer.

This supports a **wording/pseudocode/implementation inconsistency**. Other bounds and the outer statistical acceptance condition still apply. It does not establish algorithm failure, refute the paper or establish that this observation is novel. This follow-up is not human expert validation or an independent-model voting result.

## Evidence sources and public access

| Source | Version / location |
| --- | --- |
| Paper | Justin Matejka and George Fitzmaurice, *Same Stats, Different Graphs*, CHI 2017, [DOI 10.1145/3025453.3025912](https://doi.org/10.1145/3025453.3025912); [official PDF](https://research.autodesk.com/app/uploads/2023/03/same-stats-different-graphs.pdf_rec2hRjLLGgM7Cn2T.pdf) |
| Project webpage | [Official Autodesk page](https://www.research.autodesk.com/publications/same-stats-different-graphs/), Fig 5 caption in the dated local snapshot |
| Author code and datasets | [Repository pinned to `b4d82f3`](https://github.com/jmatejka/same-stats-different-graphs/tree/b4d82f3a2ff8ef5849fecbdfab6dccafccbc1370); original MIT notice preserved |
| Acquisition record | [Original URLs, timestamps and SHA-256 digests](evidence/provenance.json) |
| Evidence-name resolution | [Source map](evidence/source-map.json), including sources that must be acquired separately |

The public case is an explicitly selected subset, **not the full local evidence archive**. The model response and the unchanged records are listed in [publication.json](publication.json). Only workstation path values in `author_smoke.json` were replaced, with JSON reserialization; its numerical values and limitations were preserved. `call-record.json` is a new summary with paths and the session identifier removed.

The paper, webpage copies, extracted full texts, full prompt, raw CLI logs, original HTML report, PDF screenshots and full-evidence ZIP remain local. Their omission prevents complete public replay of the exact historical input bytes. Source links, hashes and locators support comparison after separate acquisition; a hash alone does not disclose or authenticate withheld content. The paper and page are not relicensed under MIT.

## Checking and reproducing

From a clone containing this case, with SciNet installed, check the **public subset's** file integrity:

```sh
python -c "from scinet.evidence import verify; errors = verify('docs/cases/2026-10-24-datasaurus-live-review'); print(errors or 'Public case hashes OK'); raise SystemExit(bool(errors))"
```

`manifest.json` covers published bytes; `review_input_hashes.json` covers original model inputs. The redacted execution record intentionally has a different hash from its original input. Do not use full-run `scinet verify` on this subset: it intentionally lacks full-text inputs and raw logs. Neither manifest is a trusted signature, blockchain proof or external timestamp.

One historical metadata detail is preserved explicitly: `author_smoke.json.adapter_sha256` hashes the generated adapter's in-memory text **before Windows newline conversion**, not its on-disk bytes. A single CRLF-to-LF replacement on the stored file reproduces that recorded hash. The [call record's `adapter_hash_note`](evidence/call-record.json) gives both digests; the public manifest uses the actual file-byte digest. No original hash was silently rewritten.

To repeat the computation, use a separate checkout of implementation commit `e6db99da565473785632096471ea3e8d2f53648b` and the [installation instructions](../../../README.md). Then:

```sh
scinet init --workspace case-replay
scinet --workspace case-replay run
scinet --workspace case-replay verify latest
```

For a **new** AI review, acquire the sources and explicitly select an account-available model:

```sh
python scripts/acquire.py --workspace case-replay
scinet --workspace case-replay run --ai --model MODEL_ID
```

This creates a new run and may consume service allowance. Model availability, a fixed backend, identical outputs and byte-identical future webpage downloads are not guaranteed. Match the environment and compare the original input hashes before claiming exact replay. The public adapter is an artifact for inspection; the SciNet command is the bounded execution path.

## What this case does and does not show

The observed model response distinguishes precision conventions, a webpage sign issue and untested reproduction scope, and supplies a further source-level inconsistency for checking. Automated follow-up did not identify an unsupported numerical assertion or fabricated locator in these four findings. That limited check is **not an accuracy percentage**.

The prompt already guides several checks; prior training familiarity with this famous example cannot be excluded. There is one paper, one model call, no blinded reference set, no human domain-expert assessment and no measurement of false positives, missed defects or stability across repeated reviews. Computation was supplied to the model, not independently performed by it. Provider-hidden context and internal reasoning are unavailable. These results do not establish replacement of peer review, publication decisions, decentralized governance or resistance to adversarial submissions.
