# Review powerlaw, then recompute

This example gives several requested models the same original paper, code and data. Each model reviews the packet in a separate session. SciNet freezes every original review before running the numerical checks, then records which opinions the evidence supports and where the reviewers differ.

The paper is [Alstott, Bullmore and Plenz (2014), *powerlaw: A Python Package for Analysis of Heavy-Tailed Distributions*](https://doi.org/10.1371/journal.pone.0085777). The runner uses the paper's original **Code S1 and Code S2**, not today's powerlaw package.

## Run it

From a cloned SciNet repository, use **Python 3.12** and an activated virtual environment. This historical-code conversion requires `lib2to3`, which is absent from newer Python releases. Install and authenticate Codex CLI separately.

```sh
python -m pip install ".[powerlaw]"
python examples/powerlaw/acquire.py --output work/powerlaw-inputs
```

The downloader saves the original PDF, a page-marked text extraction, two author scripts, three data files and the upstream license. It checks each accepted hash and writes `bundle.json` only after the inputs are verified. Existing output directories are refused; a failed download remains available for inspection. Downloads do not execute author code.

Replace the model placeholders with IDs available to your account, using at least two distinct reviewer IDs:

```sh
scinet panel review --bundle work/powerlaw-inputs/bundle.json --output work/panel-01 --model MODEL_A --model MODEL_B
scinet panel recompute work/panel-01 --script examples/powerlaw/recompute.py
scinet panel synthesize work/panel-01 --model SYNTHESIS_MODEL --evidence-list examples/powerlaw/synthesis-evidence.json
scinet panel verify work/panel-01
```

Open the printed `REPORT=` path. The [panel guide](../../docs/PANELS.md) describes each artifact and the one-command alternative. Calls send the selected text to the model service and use your account's allowance. A new attempt needs a new output directory.

## Select synthesis evidence or continue a failed synthesis

The complete computation bundle includes repeated input copies, generated scripts, detailed numerical arrays and logs. Sending all readable artifacts to synthesis can exceed the model client's input limit. Files are not automatically shortened. The commands here use [synthesis-evidence.json](synthesis-evidence.json), a checked-in list of 17 logical artifact paths.

The list includes every computation JSON file, the compatibility diff and the four verification scripts. It excludes duplicate input/source copies and raw logs from the synthesis prompt, while leaving every original file saved and hashed locally. It selects by artifact type and check coverage, without filtering numerical results according to whether they support a reviewer.

Original model-visible sources, every original review and the panel's `checks/execution.json` are supplied in addition to the list. Another paper or a changed reproduction script needs its own list. Apply this example's list before the first synthesis call with:

```sh
scinet panel synthesize work/panel-01 --model SYNTHESIS_MODEL --evidence-list examples/powerlaw/synthesis-evidence.json
```

If synthesis has already failed, preserve that directory and continue in a new one:

```sh
scinet panel continue-synthesis work/panel-01 --output work/panel-01-synthesis-02 --model SYNTHESIS_MODEL --evidence-list examples/powerlaw/synthesis-evidence.json
scinet panel verify work/panel-01-synthesis-02
```

Only the synthesis is called again. The source must pass verification and already have completed reviews and computation. The new directory archives the full original under `parent_bundle/` and retains the exact frozen reviews and results, with a continuation record and appended timeline event. It does not modify the old attempt or present reused work as new reviews or calculations.

The selection records every included and excluded computation artifact's hash and byte count. Excluded contents stay in the local evidence bundle but are not visible to that synthesis call; selected files are sent without truncation. Evidence selection can leave questions untested, and does not guarantee the call will fit or succeed. See the [panel guide](../../docs/PANELS.md#continue-after-a-synthesis-failure) for allowed states and verification details.

## Original inputs

| Material | Source and handling |
| --- | --- |
| Paper PDF | PLOS article DOI `10.1371/journal.pone.0085777`; archived locally, not an image input to the models |
| `paper.txt` | Extracted with `pypdf==6.14.2`, including page markers; accepted text hash is fixed |
| `author_powerlaw.py` | PLOS Code S1, `.s001` supplement; original Python 2 implementation |
| `author_figures.py` | PLOS Code S2, `.s002` supplement; preprocessing reference |
| `blackouts.txt`, `words.txt`, `worm.txt` | `powerlaw-devs/powerlaw`, commit `d2b563a7a08bad96b4085fa69f351e9d9a20b1e7`, under `manuscript/` |
| `AUTHOR_LICENSE.txt` | License file from that same repository commit |

Exact URLs, SHA-256 values and download times are retained in the local inventory. The scripts contain SciNet's own logic and accepted hashes; upstream full text and code are downloaded into the workspace, not included in this example directory.

PLOS identifies the paper as CC0, and Code S1 carries an MIT notice. Data references remain those of the paper. The saved repository license is not asserted to license every input; review the source rights before redistributing a bundle.

## What gets checked

- Nine selected fits using the historical author code, including fixed and selected thresholds, constrained fits and discrete examples.
- An independent standard-library calculation of selected continuous power-law fits and exponential comparisons. It does not import the author module or read any model answer.
- Four directed checks covering finite upper bounds, the requested fitting method, discrete support and an explicit model-comparison option.
- Four additional checks covering exponential fitting precision, worm model comparisons, word-count lognormal comparison and automatic discrete fits.

The directed and extended checks were developed for a **previous SciNet case**. Reusing them after the new reviews are frozen does not make them tests independently designed by the current panel. The acquisition inventory discloses prior case history. Reviewers receive original materials without a list of those checks or old results, but the coordinating operator is not blind to that history.

Each run retains original inputs, a Python 3 compatibility copy, its full diff and change list, generated drivers, environment versions, stdout/stderr, results and file hashes. The runner refuses inputs whose fixed hashes do not match. Missing dependencies, timeouts and execution failures remain failures; a measured discrepancy is retained as a result rather than hidden.

## Reproduction interface

The panel coordinator copies and records the selected runner, then invokes it with two arguments:

```text
python recompute.py INPUT_DIRECTORY NEW_OUTPUT_DIRECTORY
```

Required inputs are `paper.txt`, `author_powerlaw.py`, `author_figures.py`, `blackouts.txt`, `words.txt` and `worm.txt`. If the PDF or license is present, it is checked and archived too. The destination must not exist and must be outside the input directory. The standalone runner does not establish review order; use `scinet panel recompute` to enforce the review freeze first.

## Limits

This is a bounded historical-code reproduction, not every figure or simulation in the paper. The complete figure script is not executed. Compatibility changes do not reconstruct the original dependency environment, and the independent checker does not cover every discrete or lognormal fit.

Models see extracted text, code and data, not rendered PDF figures. Requested models currently share the Codex service; separate sessions do not prove independent training or errors. The resolved backend remains unknown unless the service reports it. Synthesis is another model interpretation and can misclassify agreement or evidence; original opinions and untested findings remain available to inspect.

This example documents a runnable workflow. It does not assert a successful live panel run, measured review accuracy or independent expert validation. A real case must link its own recorded calls and outputs. Blockchain anchoring and signatures are not implemented.
