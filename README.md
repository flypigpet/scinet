# SciNet

**An alpha prototype for evidence-based auditing of one scientific paper.** SciNet recomputes selected numerical claims, runs selected author functions, and produces a local HTML evidence report. An optional Codex review interprets those recorded results.

[中文说明](README.zh-CN.md) · [Reproducibility](docs/REPRODUCIBILITY.md) · [AI disclosure](docs/AI_USAGE.md) · [Asset provenance](docs/ASSETS.md)

Version **0.1.0a1** is a research software preview. Human scientific validation is **pending** (`human_validation_pending`). It does not establish that AI peer review is reliable and does not make publication or acceptance decisions.

## What it covers

The single reference case is Matejka and Fitzmaurice's *Same Stats, Different Graphs* (CHI 2017): [paper/project page](https://www.research.autodesk.com/publications/same-stats-different-graphs/), [DOI](https://doi.org/10.1145/3025453.3025912), [pinned author repository](https://github.com/jmatejka/same-stats-different-graphs/tree/b4d82f3a2ff8ef5849fecbdfab6dccafccbc1370).

- Recompute five statistics for each of 13 datasets with 142 points: 65 values, using Python's standard library and a separate pandas/NumPy path.
- Compare floor, truncation and rounding conventions explicitly; standard deviations use `ddof=1`.
- Run selected, hash-checked author functions for 1,000 proposals with a recorded seed and documented compatibility edits.
- Save input provenance, numerical results, a Chinese HTML report and a SHA-256 manifest. AI review is optional.

This covers neither the full paper nor its animations, original random trajectories, convergence or performance claims. A passing numerical check or test suite concerns the implementation, not scientific-review quality. The selected author-code process has a timeout; **it is not a security sandbox for arbitrary code**.

## Install and run the offline demo

Use Python **3.12 or later** and Git. Windows with Python 3.12 is the locally validated platform; Linux support awaits a successful CI run. Installation may download dependencies. Once installed, the numerical demo needs no network access or AI account.

```sh
git clone https://github.com/flypigpet/scinet.git
cd scinet
python -m venv .venv
```

Activate the environment in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On a POSIX shell, use `source .venv/bin/activate` instead. Then:

```sh
python -m pip install .
scinet init --workspace demo
scinet --workspace demo run
```

SciNet prints the new run directory and report path. Open its `report.html` in a browser. Each run gets a new directory; the offline report states that AI review was not run. In PowerShell, verify the latest run with:

```powershell
$run = Get-Content -LiteralPath demo/output/latest.txt
scinet verify $run
```

You can also pass the printed directory directly: `scinet verify demo/output/run-<timestamp>-<id>` (replace the example name). Verification checks recorded files and evidence references; it cannot certify scientific correctness, authorship or an independently trusted timestamp.

This preview is installed from source. It is **not published on PyPI**.

## Optional AI review

Use a separately installed, authenticated Codex CLI. Choose a model identifier available to your account; `MODEL_ID` below is a placeholder, not a recommended or verified model. The call uses your account's service allowance.

From the cloned repository, download the official paper and project page into the local workspace, then make a fresh run:

```sh
python scripts/acquire.py --workspace demo
scinet --workspace demo run --ai --model MODEL_ID
```

The acquisition step requires internet access. The paper, webpage text, author code, claims and calculation results are sent to the model service for review. Read [AI usage and limitations](docs/AI_USAGE.md) before using private material. Missing authentication, failed calls and timeouts do not produce a fabricated review.

To review an existing, unreviewed run that already contains the downloaded paper inputs, use `scinet --workspace demo review RUN_DIR --model MODEL_ID`, replacing both placeholders. A completed review is preserved; create another run for another review.

## Evidence and limitations

Each run records `metrics.json`, `author_smoke.json`, input provenance, an implementation snapshot and `manifest.json`. AI runs additionally record the prompt, input hashes, structured review and call provenance. See [reproduction details](docs/REPRODUCIBILITY.md) for how to inspect them.

The review prompt already directs attention to precision conventions and the distinction between paper and webpage claims. This is a **guided, single-paper demonstration with one AI reviewer**, not a blinded benchmark. Familiarity with this well-known example may affect the model. Human checks of citations and scientific judgments remain pending; no independent domain-expert review is claimed. Historical local calls with an unreported model remain recorded as unknown.

Hashes detect changes relative to a manifest. A person who replaces both files and their manifest can evade that check; this project has no trusted signatures, blockchain or external timestamp service.

## Contributing and licensing

See [contribution guidance](CONTRIBUTING.md), [security guidance](SECURITY.md), [changes](CHANGELOG.md) and [citation metadata](CITATION.cff). Automated checks can support code review but cannot establish scientific validity. No CI result is claimed before its workflow has run successfully.

SciNet's original code and documentation are [MIT licensed](LICENSE). Bundled numerical fixtures and author code retain their original MIT notice. The paper and project webpage have separate rights and are downloaded locally; SciNet's license does not relicense them. Public source and package releases exclude paper full text, website snapshots, local runs and raw AI logs. See the [asset register](docs/ASSETS.md).
