"""Create an offline example workspace from the installed package's MIT assets."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib.resources import files
import json
from pathlib import Path


UPSTREAM_COMMIT = "b4d82f3a2ff8ef5849fecbdfab6dccafccbc1370"
DOI = "10.1145/3025453.3025912"
UPSTREAM_URL = "https://github.com/jmatejka/same-stats-different-graphs"

# Resource name, original upstream path, and optional evidence filename.
_ASSETS = (
    ("DatasaurusDozen.tsv", "samestats/datasets/generated/DatasaurusDozen.tsv", "DatasaurusDozen.tsv"),
    ("author_code.py", "samestats/samestats.py", "author_code.py"),
    ("Datasaurus_data.csv", "samestats/datasets/seed/Datasaurus_data.csv", None),
    ("AUTHOR_LICENSE.txt", "LICENSE", "AUTHOR_LICENSE.txt"),
    ("AUTHOR_README.md", "README.md", "AUTHOR_README.md"),
)


def init_workspace(path: str | Path) -> Path:
    """Materialize the redistributable example, without downloads or execution.

    Existing unrelated files are preserved. If any of ``sources``, ``vendor``,
    or ``output`` already exists (including a symlink), raise FileExistsError
    before writing anything. The returned path is absolute.
    """
    root = Path(path).expanduser().resolve()
    for name in ("sources", "vendor", "output"):
        target = root / name
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Workspace already contains {name}: {target}")

    # Read every installed resource before creating directories. Traversable's
    # read_bytes also works when the distribution is imported from a zip file.
    resources = files("scinet").joinpath("data")
    assets = [(upstream, source_name, resources.joinpath(resource).read_bytes())
              for resource, upstream, source_name in _ASSETS]
    root.mkdir(parents=True, exist_ok=True)
    for name in ("sources", "vendor", "output"):
        (root / name).mkdir()

    source_entries, vendor_entries = [], []
    for upstream, source_name, raw in assets:
        metadata = {
            "url": f"{UPSTREAM_URL}/blob/{UPSTREAM_COMMIT}/{upstream}",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
        vendor_path = Path("vendor") / "same-stats" / upstream
        destination = root / vendor_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        vendor_entries.append({"path": vendor_path.as_posix(), **metadata})
        if source_name is not None:
            (root / "sources" / source_name).write_bytes(raw)
            source_entries.append({"path": source_name, **metadata})

    provenance = {
        "initialized_at_utc": datetime.now(timezone.utc).isoformat(),
        "offline_seed": True,
        "doi": DOI,
        "upstream_commit": UPSTREAM_COMMIT,
        "upstream_repository": UPSTREAM_URL,
        "files": source_entries,
        "vendor_files": vendor_entries,
        "license_note": "Bundled code, data and README are from the MIT-licensed author repository; see AUTHOR_LICENSE.txt.",
        "scope_note": "Offline example only. No paper PDF, paper text, or author webpage is bundled. Initialization does not download sources or establish their authenticity.",
    }
    (root / "sources" / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return root
