# Reproducing the numerical example

The reference is *Same Stats, Different Graphs* (CHI 2017), [DOI](https://doi.org/10.1145/3025453.3025912). SciNet uses author-repository commit `b4d82f3a2ff8ef5849fecbdfab6dccafccbc1370`. The package includes the numerical fixtures and original MIT notice, not the paper or a historical model response.

## Environment and commands

Follow the [README installation steps](../README.md). Use Python 3.12+; Python 3.12 was tested on Windows and Ubuntu in the [initial release CI run](https://github.com/flypigpet/scinet/actions/runs/39979804184). Other Python versions are not yet tested. `requirements-lock.txt` records the original Windows environment's dependency versions, not a verified lock for every operating system. See the [validation record](VALIDATION.md) for the checked commit and scope.

After installation and environment activation:

```sh
scinet init --workspace demo
scinet --workspace demo run
```

The numerical run is offline and makes no AI call. Installation itself may need network access for dependencies. Use the `RUN_DIR` printed by the command to verify the result:

```sh
scinet verify RUN_DIR
```

Replace `RUN_DIR` with the actual directory. In PowerShell, `scinet verify (Get-Content -LiteralPath demo/output/latest.txt)` selects the latest successful run. Open its `report.html` in a browser; keep the run's other files beside it so evidence links work.

For an optional fresh AI run, from the source checkout:

```sh
python scripts/acquire.py --workspace demo
scinet --workspace demo run --ai --model MODEL_ID
```

The downloader requires internet access; replace `MODEL_ID` with an available model for an authenticated Codex CLI account. Reacquiring a webpage can change its contents and hash. Compare recorded provenance instead of assuming that a later download is byte-identical. The [AI disclosure](AI_USAGE.md) describes data transmission and validation limits.

## Numerical scope

The dataset contains 13 named groups with 142 points each. SciNet calculates mean x, mean y, sample standard deviation x, sample standard deviation y, and Pearson correlation: 65 values total.

One path uses `csv` and Python `statistics`; another separately reads the TSV with pandas and calculates with NumPy. Their maximum absolute difference is checked against `1e-10`. These two implementations are a cross-check, not two independent scientific studies.

Standard deviations use denominator `n - 1` (`ddof=1`). The output separates three conventions:

| Name | Definition |
| --- | --- |
| `floor_2dp` | `floor(v * 100) / 100`, toward negative infinity; the author acceptance convention |
| `truncate_2dp` | `trunc(v * 100) / 100`, toward zero |
| `round_2dp` | Decimal rounding to the nearest hundredth, with exact ties away from zero (`ROUND_HALF_UP`) |

A difference under one convention must not be reported as a failure under every convention, or as a refutation of the whole paper. The paper and the project webpage are distinct evidence sources.

## Bounded author-function execution

SciNet accepts the specifically reviewed author-source SHA-256 and seed digest. Seed checking normalizes CRLF to LF only for its canonical digest, while preserving the original input bytes in the run.

It extracts named functions and `LINE_SHAPES`, omitting package setup, plotting and upstream command-line code. Two pandas chained assignments are changed to `.loc` for compatibility and recorded separately; the original fixture is preserved. The adapter runs 1,000 proposals toward a circle with NumPy seed `20261023`, the author's acceptance criterion and temperature schedule, and a 30-second process timeout. Numerical-library thread counts are limited to one.

Checks cover finite coordinates, actual movement, consistency of initial statistics and preservation of the author's constraint. Visible convergence to a circle is not a pass criterion. This is not a full package, figure, animation, runtime benchmark or convergence reproduction. A fixed seed can reproduce a trajectory in a recorded environment; it does not guarantee the same trajectory across library versions or systems. The subprocess is not a security sandbox.

## Inspecting a run

| File or directory | What to inspect |
| --- | --- |
| `run.json` | Environment, scope and AI status |
| `provenance.json` | Source links, commit and hashes |
| `metrics.json` | Both calculation paths, errors and precision conventions |
| `author_smoke.json`, `author_smoke/` | Original source/seed, adapter, changes, generated coordinates and execution logs |
| `claims.json` | Four predeclared claims, including an explicit scope-control claim |
| `prototype_code/` | Implementation snapshot used for the run |
| `report.html` | Human-readable Chinese evidence report |
| `manifest.json` | SHA-256 file-integrity manifest |
| `review.json` | Structured AI assessment, when requested |
| `review_prompt.txt`, `review_input_hashes.json` | Actual model input and its hashes |
| `review_provenance.json`, `ai_events.jsonl`, `ai_stderr.log` | Call provenance and raw CLI records, when a call is attempted |

Offline runs do not contain an AI review. Paper materials are present only if acquired separately. A completed AI review must correspond to its recorded inputs. An unsuccessful call is not evidence of a completed review.

`verify` checks content integrity and applicable computation/review records. A successful check does not certify the accuracy of natural-language locators or scientific judgments. Hashes have no trusted signing authority and do not prevent joint replacement of files and their manifest.

## Validation and sharing

The original local prototype had a 21-test software suite and a guided model demonstration. Those records are historical implementation evidence, not a measure of scientific-review validity. Current checks should be run against the exact checkout under review:

```sh
python -m unittest discover -s tests -v
```

Do not report CI as passed unless the relevant workflow completed successfully. Human scientific validation remains pending (`human_validation_pending`), including checking citations and assessing whether the scope and conclusions are appropriate.

Run directories can contain third-party full text, local paths and raw model logs. They are not public release artifacts. Do not redistribute the old full-evidence ZIP. Share only material whose rights and sensitive content you have checked, and distinguish the project MIT license from the paper/page rights described in [ASSETS.md](ASSETS.md).

The [24 October 2026 public case](cases/2026-10-24-datasaurus-live-review/README.md) demonstrates this selection process. It publishes unchanged numerical results and the model answer alongside explicitly path-redacted metadata, original input hashes and a separate public-file manifest. Its instructions distinguish checking the public subset from reproducing the numerical run or making a new model call. Withheld full text and logs mean the subset alone cannot reproduce the exact historical prompt.
