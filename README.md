# SciNet

**Building open research evaluation with AI review panels and blockchain.**

[![Checks](https://github.com/flypigpet/scinet/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/flypigpet/scinet/actions/workflows/ci.yml)
[![Release](https://img.shields.io/badge/release-0.1.0a1-orange)](https://github.com/flypigpet/scinet/releases/tag/v0.1.0a1)
[![MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[How it fits together](#how-it-fits-together) · [Quick start](#quick-start) · [Example review](#example-review) · [Roadmap](#roadmap) · [中文](README.zh-CN.md)

SciNet aims to let researchers evaluate a paper through its evidence and public review record, without relying on a journal's name as a proxy for quality. The goal is a decentralized alternative to journal-controlled evaluation: open criteria, reviews that can be checked, and decisions that can be challenged.

**Status: early prototype.** Today you can run numerical checks and an optional single-model review. AI review panels, blockchain records and community governance are planned; they are not implemented yet.

## How it fits together

- **AI review panels examine the work.** The planned panel has reviewers assess a paper separately, cite their evidence and retain disagreements. Model choice, instructions and evaluation criteria should be visible.
- **Reproducible checks test the claims.** Data, code and recorded runs let others check whether a finding holds up. This is the part the current prototype exercises.
- **Blockchain records the history.** The planned shared record links paper versions, signed reviews and challenges through content hashes. Full evidence stays off-chain. Recording a judgment does not make it correct.

The aim is to make the yardstick itself open: people should be able to inspect the criteria, propose alternatives and appeal a judgment. AI agreement alone should not settle scientific questions, and token holdings should not determine scientific merit.

## Try the first piece

The current alpha includes one runnable example: **Same Stats, Different Graphs (Datasaurus)**. It recomputes 65 statistics across 13 datasets, runs selected author functions, and saves the results and source references in a local HTML report. An optional AI review also saves the prompt, response and requested model.

Once installed, the numerical demo runs offline without an AI account. It is the evidence component of the larger project.

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

Only selected author functions run. The process has a timeout, **not a sandbox for arbitrary code**. File hashes help detect changes; they do not certify a paper's conclusions or provide a trusted timestamp. The prototype does not yet implement an AI review panel, blockchain or decentralized governance.

## Roadmap

1. **Evidence that others can rerun.** Extend the current checks to more papers. Have AI reviewers assess the material before seeing computed results or suggested defects, then check their findings against the evidence.
2. **Reviewers that can disagree.** Add separate reviews across models, retain their original assessments, and measure missed issues, false alarms and repeatability with domain-expert input. Multiple calls alone do not establish independence.
3. **A shared review history.** Define a signed record format and test blockchain anchoring for paper versions, review records and challenges. Keep licensed source material off-chain and provide a way to verify records independently.
4. **Open evaluation rules.** Make criteria and their changes public. Develop appeals, reviewer reputation and protections against collusion and duplicate identities. Test these before using the system for consequential decisions.

These are development directions, not shipped features. No chain or token scheme has been selected. The project has not demonstrated that it can replace journal evaluation or lower publishing costs.

## Documentation

| Guide | Contents |
| --- | --- |
| [Reproduce a run](docs/REPRODUCIBILITY.md) | Commands, output files and calculation details |
| [AI review](docs/AI_USAGE.md) | Inputs, model records and limitations |
| [Validation](docs/VALIDATION.md) | Recorded installation, test and CI results |
| [Sources and licenses](docs/ASSETS.md) | Dataset, code and paper provenance |

## Contributing

Good places to help: add a paper with public data and code, test an AI review against its sources, design panel comparisons, or work through the signed-record and appeal mechanisms. See [CONTRIBUTING.md](CONTRIBUTING.md) and [security guidance](SECURITY.md).

## License

SciNet is [MIT licensed](LICENSE). Bundled data and author code retain their original MIT notice; papers and webpages keep their own licenses. See the [asset register](docs/ASSETS.md), [changelog](CHANGELOG.md) and [citation metadata](CITATION.cff).
