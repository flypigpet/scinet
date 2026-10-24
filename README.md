# SciNet

**Recompute paper results. Inspect the AI review and the evidence behind it.**

[![Checks](https://github.com/flypigpet/scinet/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/flypigpet/scinet/actions/workflows/ci.yml)
[![Release](https://img.shields.io/badge/release-0.1.0a1-orange)](https://github.com/flypigpet/scinet/releases/tag/v0.1.0a1)
[![MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[Quick start](#quick-start) · [Example review](#example-review) · [Docs](#documentation) · [中文](README.zh-CN.md)

SciNet runs numerical checks and selected author code, then puts the results, source references and an optional AI review in a local HTML report. You can inspect the calculations and follow a finding back to its evidence.

The current alpha includes one runnable example: **Same Stats, Different Graphs (Datasaurus)**. Once installed, the demo runs offline without an AI account.

- **Check the numbers.** Recompute 65 statistics across 13 datasets with two implementations.
- **Run the code.** Exercise selected author functions with a fixed seed and recorded compatibility changes.
- **Keep the record.** Save inputs, outputs and file hashes; AI runs also save the prompt, response and model request.

## Quick start

Requires Git and Python **3.12+**. Tested on Windows and Ubuntu with Python 3.12. Install from source:

```sh
git clone https://github.com/flypigpet/scinet.git
cd scinet
python -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

On Linux/macOS, use `source .venv/bin/activate` instead. Then run:

```sh
python -m pip install .
scinet init --workspace demo
scinet --workspace demo run
scinet --workspace demo verify latest
```

Open the printed `REPORT=` path in your browser. The report includes all 13 scatterplots, the calculated values, author-code results and links to the saved evidence. Reports are currently in Chinese.

Each run gets its own folder under `demo/output/`. `verify latest` checks the most recent run's recorded files and evidence references. SciNet is not yet on PyPI.

## Example review

[Read a real run, including the unchanged AI response →](docs/cases/2026-10-24-datasaurus-live-review/README.md)

The Datasaurus case shows what these checks can catch:

- The datasets agree under some two-decimal conventions, but differ under ordinary rounding.
- A captured project-page caption gives a positive correlation; the data and paper give a negative one.
- The paper's prose reverses a temperature comparison used in its pseudocode and author code.

The case links each observation to its source and records the model request, results and remaining questions. These are specific checks, not a full reproduction of the paper.

## Add an AI review

Install and sign in to the Codex CLI separately. From the cloned repository, download the paper inputs and start a new run:

```sh
python scripts/acquire.py --workspace demo
scinet --workspace demo run --ai --model MODEL_ID
```

Replace `MODEL_ID` with a model available to your account. This step needs network access and uses your account's service allowance. Paper text, webpage text, author code, selected claims and calculation results are sent to the model service. See [what is sent and recorded](docs/AI_USAGE.md).

## Current scope

The CLI is built around the bundled Datasaurus example; adding another paper requires its own checks and execution setup. The AI receives selected questions and computed results. This is a guided review, and its scientific judgments have not been independently validated by domain experts.

Only selected author functions run. The process has a timeout, **not a sandbox for arbitrary code**. File hashes help detect changes; they do not certify a paper's conclusions or provide a trusted timestamp. No blockchain is implemented.

## Documentation

| Guide | Contents |
| --- | --- |
| [Reproduce a run](docs/REPRODUCIBILITY.md) | Commands, output files and calculation details |
| [AI review](docs/AI_USAGE.md) | Inputs, model records and limitations |
| [Validation](docs/VALIDATION.md) | Recorded installation, test and CI results |
| [Sources and licenses](docs/ASSETS.md) | Dataset, code and paper provenance |

## Contributing

Good places to help: add a paper with public data and code, improve a reproduction check, or review a finding against its source. See [CONTRIBUTING.md](CONTRIBUTING.md) and [security guidance](SECURITY.md).

## License

SciNet is [MIT licensed](LICENSE). Bundled data and author code retain their original MIT notice; papers and webpages keep their own licenses. See the [asset register](docs/ASSETS.md), [changelog](CHANGELOG.md) and [citation metadata](CITATION.cff).
