# Asset provenance and rights

SciNet's original code and documentation use the root [MIT license](../LICENSE), copyright 2026 SciNet contributors. That license does not replace notices for third-party material or grant rights to the paper and webpage.

## Numerical fixtures included in the package

The reference material comes from [jmatejka/same-stats-different-graphs](https://github.com/jmatejka/same-stats-different-graphs), pinned to commit `b4d82f3a2ff8ef5849fecbdfab6dccafccbc1370`. Its MIT license states `Copyright (c) 2017 jmatejka`; the original notice is retained as `scinet/data/AUTHOR_LICENSE.txt` alongside the fixtures.

| Upstream path | Purpose |
| --- | --- |
| `samestats/datasets/generated/DatasaurusDozen.tsv` | Thirteen groups of numerical coordinates for recomputing five summary statistics |
| `samestats/datasets/seed/Datasaurus_data.csv` | Author seed coordinates for the bounded function run |
| `samestats/samestats.py` | Original source used to extract the specifically reviewed functions |
| `LICENSE` | Original MIT copyright and permission notice |
| `README.md` | Original upstream context, retained as `AUTHOR_README.md`; its installation advice is historical |

The source is preserved as a fixture; SciNet generates a separate adapter. That adapter extracts selected functions, changes two pandas chained assignments to `.loc`, and supplies a bounded driver. These changes and the generated adapter are recorded in each run. The fixture does not imply that the original upstream package works unmodified in the current environment.

The numerical demo creates plots from the coordinates. It does not ship copied paper figures, screenshots, textures or 3D assets. Project dependencies retain their own licenses; the project MIT license does not replace them.

## Paper and project page: acquired locally

Reference: Matejka and Fitzmaurice, *Same Stats, Different Graphs* (CHI 2017), [DOI 10.1145/3025453.3025912](https://doi.org/10.1145/3025453.3025912).

`python scripts/acquire.py --workspace demo` fetches the paper and page from the [official Autodesk project page](https://www.research.autodesk.com/publications/same-stats-different-graphs/) and records the URLs, acquisition time and file hashes locally. The paper PDF retains its ACM notice. The page and its content retain their respective rights. Public availability is not a declaration that these materials are MIT licensed.

Extracted `paper.txt` and `author_page.txt` are derived from those materials and are treated the same way for release exclusion. Downloading them for a local run does not authorize unrestricted redistribution. Users are responsible for assessing the terms applicable to their use and any material they choose to share.

## Publication boundary

The public repository, source release and wheel exclude the local `sources/`, `output/` and `vendor/` directories, paper PDFs/full text, webpage snapshots, raw model prompts/events/logs and historical full-evidence ZIP archives. Only the explicitly registered numerical fixtures and their original MIT notice belong in the package.

### Curated public case, 24 October 2026

The repository additionally includes [a documented live-review case](cases/2026-10-24-datasaurus-live-review/README.md), with an explicit [publication inventory](cases/2026-10-24-datasaurus-live-review/publication.json). It contains the unchanged structured model answer, numerical results, claims, schema, provenance, hashes, an instruction-only prompt prefix, a path-redacted execution record, a call summary and editorial source checks. This is a curated exception for listed records, not publication of `output/` or its full archive. Case files are repository documentation, not added to wheel package data or the explicit source-distribution manifest.

The case also preserves the actual generated adapter, seed coordinates, final generated coordinates and numerical result JSON. The adapter is derived from the same pinned MIT author source: selected functions, two documented `.loc` edits and a bounded SciNet driver. The original [author MIT notice](cases/2026-10-24-datasaurus-live-review/evidence/author_smoke/AUTHOR_LICENSE.txt) is retained beside these artifacts. No copied paper figure or PDF screenshot is published. Paper/page evidence remains separately acquired and linked; the structured response uses limited short references, not redistributed full text. Original model-input hashes and public-file hashes are distinguished because path-redacted records have different bytes.

The local historical README copy (`docs/LOCAL_MVP_HISTORY.md`) is for preserving the original workstation record and is excluded from publication. Its links and instructions are historical, not release documentation.

### Curated multi-model panel case, 24 October 2026

The [powerlaw panel case](cases/2026-10-24-powerlaw-panel/README.md) publishes three unchanged original reviews, one unchanged synthesis response, selected numerical records, path-redacted call summaries, relative-path freeze inventories, a local commitment, and a separate public-file inventory. [Its source map](cases/2026-10-24-powerlaw-panel/evidence/SOURCES.md) identifies the original artifact hashes and all transformations. The full local commitment describes files beyond this public subset; it does not imply those files are redistributed.

The subject is Alstott, Bullmore and Plenz's 2014 paper, [DOI 10.1371/journal.pone.0085777](https://doi.org/10.1371/journal.pone.0085777), its publisher Code S1/S2, and public example data pinned to commit `d2b563a7a08bad96b4085fa69f351e9d9a20b1e7`. Original paper text, PDF, author source, data arrays, full prompts and raw client logs remain local. This case is repository documentation, excluded from wheel data and the source-distribution manifest. Source availability is not a blanket relicensing claim. The original supplement's MIT notice is retained with local acquisitions; SciNet's license does not replace upstream terms.

Before adding an asset, record its origin, exact version, license, modifications and permitted distribution scope. Prefer existing appropriately licensed material and preserve attribution.
