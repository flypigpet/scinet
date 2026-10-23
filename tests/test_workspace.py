"""The redistributable example is self-contained and never overwrites a workspace."""

from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


COMMIT = "b4d82f3a2ff8ef5849fecbdfab6dccafccbc1370"
SOURCE_NAMES = {"DatasaurusDozen.tsv", "author_code.py", "AUTHOR_LICENSE.txt",
                "AUTHOR_README.md", "provenance.json"}


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        try:
            self.module = importlib.import_module("scinet.workspace")
        except ImportError as error:
            self.fail(f"Offline workspace initialization is not implemented: {error}")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"

    def test_initialization_materializes_only_redistributable_sources(self):
        before = datetime.now(timezone.utc)
        self.assertEqual(self.module.init_workspace(self.root), self.root.resolve())
        source = self.root / "sources"
        self.assertEqual({p.name for p in source.iterdir()}, SOURCE_NAMES)
        self.assertTrue((self.root / "output").is_dir())
        self.assertEqual(list((self.root / "output").iterdir()), [])
        self.assertIn("MIT License", (source / "AUTHOR_LICENSE.txt").read_text())
        provenance = json.loads((source / "provenance.json").read_text())
        self.assertEqual(provenance["doi"], "10.1145/3025453.3025912")
        self.assertEqual(provenance["upstream_commit"], COMMIT)
        self.assertTrue(provenance["offline_seed"])
        initialized = datetime.fromisoformat(provenance["initialized_at_utc"])
        self.assertGreaterEqual(initialized, before)
        self.assertLessEqual(initialized, datetime.now(timezone.utc))
        self.assertEqual({entry["path"] for entry in provenance["files"]},
                         SOURCE_NAMES - {"provenance.json"})
        for entry in provenance["files"]:
            with self.subTest(path=entry["path"]):
                raw = (source / entry["path"]).read_bytes()
                self.assertEqual(entry["sha256"], hashlib.sha256(raw).hexdigest())
                self.assertEqual(entry["bytes"], len(raw))
                self.assertIn(COMMIT, entry["url"])

    def test_vendor_has_the_reviewed_source_and_seed_required_by_compute(self):
        from scinet.compute import REVIEWED_AUTHOR_SHA256, REVIEWED_SEED_CANONICAL_SHA256, compute

        self.module.init_workspace(self.root)
        repo = self.root / "vendor" / "same-stats"
        source = repo / "samestats" / "samestats.py"
        seed = repo / "samestats" / "datasets" / "seed" / "Datasaurus_data.csv"
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), REVIEWED_AUTHOR_SHA256)
        self.assertEqual(hashlib.sha256(seed.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                         REVIEWED_SEED_CANONICAL_SHA256)
        self.assertEqual(source.read_bytes(), (self.root / "sources" / "author_code.py").read_bytes())
        self.assertEqual((repo / "LICENSE").read_bytes(),
                         (self.root / "sources" / "AUTHOR_LICENSE.txt").read_bytes())
        result = compute(self.root / "sources" / "DatasaurusDozen.tsv")
        self.assertEqual((result["dataset_count"], result["rows"]), (13, 1846))
        provenance = json.loads((self.root / "sources" / "provenance.json").read_text())
        entries = provenance["vendor_files"]
        actual = {p.relative_to(self.root).as_posix() for p in repo.rglob("*") if p.is_file()}
        self.assertEqual({entry["path"] for entry in entries}, actual)
        for entry in entries:
            raw = (self.root / entry["path"]).read_bytes()
            self.assertEqual(entry["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(entry["bytes"], len(raw))

    def test_existing_workspace_content_is_rejected_without_mutation(self):
        for name in ("sources", "vendor", "output"):
            for directory in (False, True):
                with self.subTest(name=name, directory=directory):
                    root = self.root / f"{name}-{directory}"
                    root.mkdir(parents=True)
                    target = root / name
                    if directory:
                        target.mkdir()
                        preserved = target / "keep.txt"
                    else:
                        preserved = target
                    preserved.write_text("keep this", encoding="utf-8")
                    with self.assertRaisesRegex(FileExistsError, name):
                        self.module.init_workspace(root)
                    self.assertEqual(preserved.read_text(), "keep this")
                    self.assertEqual({p.name for p in root.iterdir()}, {name})

    def test_existing_unrelated_files_are_preserved(self):
        self.root.mkdir()
        marker = self.root / "notes.txt"
        marker.write_text("local notes", encoding="utf-8")
        self.module.init_workspace(str(self.root))
        self.assertEqual(marker.read_text(), "local notes")

    def test_existing_file_cannot_be_used_as_workspace_root(self):
        self.root.write_text("keep this", encoding="utf-8")
        with self.assertRaises((FileExistsError, NotADirectoryError)):
            self.module.init_workspace(self.root)
        self.assertEqual(self.root.read_text(), "keep this")

    def test_package_resources_work_without_a_source_checkout(self):
        # A zipped import exercises Traversable resources without filesystem paths.
        package = Path(self.module.__file__).parent
        archive = Path(self.temp.name) / "installed.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            for path in (package / "__init__.py", package / "workspace.py"):
                bundle.write(path, f"scinet/{path.name}")
            for path in (package / "data").rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts:
                    bundle.write(path, path.relative_to(package.parent).as_posix())
        env = dict(os.environ, PYTHONPATH=str(archive))
        result = subprocess.run([sys.executable, "-c",
            "from scinet.workspace import init_workspace; init_workspace('offline')"],
            cwd=self.temp.name, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((Path(self.temp.name) / "offline" / "sources" / "DatasaurusDozen.tsv").is_file())


if __name__ == "__main__":
    unittest.main()
