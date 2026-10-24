# Initial release validation

Version: **0.1.0a1**. Checked implementation commit: [`3f36a22fb506283cc5206ea7735ea9738853c783`](https://github.com/flypigpet/scinet/commit/3f36a22fb506283cc5206ea7735ea9738853c783).

[GitHub Actions run 39979804184](https://github.com/flypigpet/scinet/actions/runs/39979804184) completed successfully on both **Windows and Ubuntu with Python 3.12**. Each job installed the package, initialized a fresh offline workspace, ran the 40-test suite, performed the numerical audit and verified the resulting evidence. Follow-up documentation changes do not change that implementation.

The local release check additionally installed the built package in a new Windows/Python 3.12.14 virtual environment with system packages disabled. Its command ran from outside the source checkout. Observed results:

| Check | Result |
| --- | --- |
| Dataset dimensions | 13 groups, 142 observations each, 1,846 rows total |
| Numerical cross-check | 65 values; maximum absolute difference `7.105427357601002e-15`, below `1e-10` |
| Author-function smoke run | 1,000 proposals; 687 accepted; 142 points moved; statistical acceptance constraint passed |
| Offline evidence verification | Passed |
| Package dependency consistency | Passed (`pip check`) |

These counts describe this specific run. A fixed seed does not guarantee identical trajectories across all future library versions or platforms.

The optional AI protocol is tested with explicitly mocked responses and failure cases. **No fresh live AI review was run as part of release validation**, and CI does not use model credentials. The earlier local guided review is not included in the public release and did not capture its model identity. Human scientific validation remains pending; these software checks do not establish scientific-review quality.

## Subsequent live-review case

After release validation, a separate run on 24 October 2026 explicitly requested `gpt-6-astra` and completed successfully. The [public case](cases/2026-10-24-datasaurus-live-review/README.md) records its model-identity limits, unchanged response, numerical evidence and automated follow-up. It does not alter the historical release-validation statement above. Public file integrity can be checked using the command in that case; the curated subset intentionally excludes full text and raw logs and is not a complete SciNet run. Human scientific validation remains pending.
