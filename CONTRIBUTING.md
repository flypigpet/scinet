# Contributing

SciNet is building open research evaluation with AI review panels, reproducible evidence and blockchain records. The source tree includes an experimental review-before-computation panel and a legacy Datasaurus demo. Signatures, on-chain records and governance remain planned. See the [roadmap](README.md#roadmap), [panel guide](docs/PANELS.md) and [current scope](README.md#current-scope).

## Set up and check a change

Clone the repository, create and activate a Python 3.12 virtual environment, then run:

```sh
python -m pip install ".[powerlaw]"
python -m unittest discover -s tests -v
scinet init --workspace demo
scinet --workspace demo run
```

Verify the printed run directory with `scinet verify RUN_DIR`. Follow the [quickstart](README.md) for platform-specific activation and latest-run commands. A local numerical run does not need AI access. Automated tests must not require a paid model call or credentials.

For code changes, add checks that demonstrate the intended behavior and relevant failure cases. Describe the environment, commands and observed results in the pull request. Do not describe a test suite as proof that scientific judgments are correct. CI results should be reported only after the relevant run completes.

## Evidence and attribution

- Keep numerical computation separate from model interpretation. Record definitions, tolerances, adaptations and known limits.
- Preserve original third-party notices and record the upstream URL, commit, path and hash for every fixture. Review changes to executable third-party content before changing accepted hashes.
- A new paper needs original source URLs, fixed input hashes, acquisition and rights information, a selection disclosure and a bounded reproduction script. Give reviewers the same original packet; do not insert a defect list, old reviews or computed results into it. Adding a case is not a validation of general peer-review ability.
- Freeze every original review before executing reproduction. Preserve differences between reviewers and distinguish disagreement from a topic only one model mentions. Keep original opinions separate from later synthesis and computation.
- Define numerical expectations, tolerances and check coverage in the reproduction work. If tests or suspected issues come from an earlier case, disclose that provenance without leaking them into the reviewer packet. Record untested findings rather than forcing a result.
- Preserve historical evidence. Do not replace an unknown historical model with a guessed identity; new model calls must use an explicit model selection and honest provenance.
- Disclose substantial AI assistance in the pull-request description, including the tool and what a person actually checked. Do not list AI tools as authors or imply unperformed expert review.

## What belongs in a contribution

Keep source changes focused. Include reproducible commands and a small example when reporting a bug. Remove secrets, account details, machine-local paths and unpublished research from examples.

Do not commit `sources/`, `output/`, `vendor/`, `work/`, virtual environments, generated reports, downloaded paper full text, webpage snapshots or raw model logs. Do not upload historical full-evidence ZIP files. The packaged numerical fixtures are an intentional, documented exception for properly attributed MIT material; see [the asset register](docs/ASSETS.md). Publish a separately checked evidence subset when its rights and privacy allow it, with its own inventory and a clear statement of what was omitted.

Keep source acquisition and reproduction helpers in `examples/`; include their usage and limits. Source distributions include the powerlaw helpers and panel guide. The installed package exposes `scinet panel`; run example helpers from the cloned repository or extracted source distribution.

Contributions to SciNet's original code and documentation are submitted under the project's [MIT license](LICENSE). Only submit material you have permission to contribute; third-party material retains its own applicable notice and rights.

Use repository issues for ordinary bugs and feature discussion. For sensitive findings, follow [SECURITY.md](SECURITY.md).
