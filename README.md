# SciNet

**Building open research evaluation with AI review panels and blockchain.**

[![Checks](https://github.com/flypigpet/scinet/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/flypigpet/scinet/actions/workflows/ci.yml)
[![Release](https://img.shields.io/badge/release-0.1.0a1-orange)](https://github.com/flypigpet/scinet/releases/tag/v0.1.0a1)
[![MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[Quick start](#quick-start) · [How it works](#how-it-works) · [Examples](#examples) · [Roadmap](#roadmap) · [中文](README.zh-CN.md)

SciNet gives several AI models the same paper, keeps their separate reviews, then checks their findings against data and code. You can read each original opinion, see where reviewers disagree, and follow a judgment back to its evidence.

The goal is to replace journal-controlled evaluation with an open alternative: public criteria, checkable reviews and a way to challenge decisions. AI panels do the reviewing; reproducible checks test their claims; blockchain is planned for a shared, verifiable review history.

**The experimental panel has completed a real run: three models, 20 original findings, and evidence for each judgment.** [Read the case](docs/cases/2026-10-24-powerlaw-panel/README.md). Signatures, blockchain anchoring and community governance are still planned. Install from the development branch below; the `v0.1.0a1` release predates this workflow.

## How it works

1. **Give every reviewer the same sources.** Paper text, author code and data go into one hashed packet. Generic instructions do not suggest specific defects or provide earlier reviews and computed results.
2. **Keep the reviews separate.** Each requested model gets a fresh session. All original responses are frozen before reproduction starts.
3. **Run the checks.** An inspected script recomputes selected results and records its inputs, compatibility edits, environment and outputs.
4. **Show the differences.** A separate synthesis call compares opinions with the evidence. Original reviews stay intact. Agreement, disagreement, different scope and untested findings remain visible.

Every run keeps its prompts, responses, raw client records, sources and file hashes. The final evidence commitment provides a digest for later signing or anchoring. It is currently a local record, without a blockchain transaction or trusted timestamp.

## Quick start

Use Git and **Python 3.12** for the powerlaw example. Install and sign in to Codex CLI separately. Model calls need network access and use your account's allowance.

```sh
git clone --branch codex/ai-review-panel https://github.com/flypigpet/scinet.git
cd scinet
python -m venv .venv
```

Activate the environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

On Linux/macOS, use `source .venv/bin/activate`. Then install and download the example's original materials:

```sh
python -m pip install ".[powerlaw]"
python examples/powerlaw/acquire.py --output work/powerlaw-inputs
```

Replace `MODEL_A`, `MODEL_B` and `SYNTHESIS_MODEL` with model IDs available to your account. Use at least two distinct reviewer IDs:

```sh
scinet panel review --bundle work/powerlaw-inputs/bundle.json --output work/panel-01 --model MODEL_A --model MODEL_B
scinet panel recompute work/panel-01 --script examples/powerlaw/recompute.py
scinet panel synthesize work/panel-01 --model SYNTHESIS_MODEL --evidence-list examples/powerlaw/synthesis-evidence.json
scinet panel verify work/panel-01
```

Open the printed `REPORT=` path in your browser. Each stage preserves its own records; a failed review blocks computation. Use a new output directory when retrying.

The supplied [powerlaw evidence list](examples/powerlaw/synthesis-evidence.json) includes every computation JSON file, the compatibility diff and verification scripts. Duplicate input/source copies and raw logs stay out of the synthesis prompt; all original files remain saved locally. Another paper needs its own evidence list.

See the [powerlaw example](examples/powerlaw/README.md) for input versions, check coverage and limits, or the [panel guide](docs/PANELS.md) for the one-command workflow and your own paper packets. SciNet is not yet on PyPI.

## Examples

| Example | What it exercises |
| --- | --- |
| [Three-model live review](docs/cases/2026-10-24-powerlaw-panel/README.md) | 20 original findings, three bounded numerical confirmations, mismatched numbers and untested questions |
| [powerlaw](examples/powerlaw/README.md) | Original paper, published code and public data; separate model reviews followed by bounded reproduction |
| [Datasaurus live review](docs/cases/2026-10-24-datasaurus-live-review/README.md) | Earlier guided, single-model review with published observations and evidence |

For an offline numerical demo without an AI account:

```sh
scinet init --workspace demo
scinet --workspace demo run
scinet --workspace demo verify latest
```

This bundled Datasaurus demo recomputes 65 statistics across 13 datasets and runs selected author functions. Its optional `--ai` path supplies selected questions and computed results to one model. It remains available as a **legacy guided demo**; use `scinet panel` for review-before-computation experiments.

## Current scope

- **Separate contexts, one provider.** The panel currently calls requested models through Codex CLI. Different IDs do not prove independent training or independent errors. The backend remains unknown unless the service reports it.
- **Preserved evidence, fallible judgments.** Synthesis labels and disagreement groups are model interpretations. Reference checks cannot establish that a passage supports an opinion. Human scientific validation remains pending.
- **Selected checks.** Each paper needs its own inspected reproduction script. The powerlaw example tests historical code and selected results, not every experiment or the current package.
- **Local integrity.** Hashes detect changes against a saved reference. They do not establish authorship, scientific truth or a trusted timestamp. Subprocess timeouts are not a sandbox for arbitrary code.

Read [what the AI receives and records](docs/AI_USAGE.md) before submitting your own materials. Full local evidence may contain licensed text and private paths; a public case needs a separately reviewed publishing subset.

## Roadmap

- **Broaden the panel.** Add provider diversity and repeated runs; work with domain experts to measure missed issues, false alarms and useful disagreement.
- **Expand reproduction.** Add papers and check adapters, with explicit coverage and remaining questions.
- **Share verifiable history.** Add signed identities and test blockchain anchoring for paper versions, reviews, challenges and corrections. Keep full evidence off-chain.
- **Open the yardstick.** Make evaluation criteria and their changes public, with appeals, reviewer reputation and defenses against collusion and duplicate identities.

AI agreement should not settle a scientific question, and token holdings should not determine scientific merit. No chain or token scheme has been selected. Replacing journal evaluation and lowering publishing costs remain goals to test.

## Documentation

| Guide | Contents |
| --- | --- |
| [AI panels](docs/PANELS.md) | Commands, evidence format, disagreements and integrity checks |
| [powerlaw example](examples/powerlaw/README.md) | Source acquisition and bounded reproduction |
| [AI usage](docs/AI_USAGE.md) | Inputs, model records and limitations |
| [Datasaurus reproduction](docs/REPRODUCIBILITY.md) | Earlier demo commands and calculation details |
| [Validation](docs/VALIDATION.md) | Recorded installation, test and CI results |
| [Sources and licenses](docs/ASSETS.md) | Bundled dataset, code and paper provenance |

## Contributing

Add a paper with public data and code, check a review against its sources, compare models, or help design signed records and appeals. See [CONTRIBUTING.md](CONTRIBUTING.md) and [security guidance](SECURITY.md).

## License

SciNet is [MIT licensed](LICENSE). Third-party data, code and papers retain their own notices and rights. See the [asset register](docs/ASSETS.md), [changelog](CHANGELOG.md) and [citation metadata](CITATION.cff).
