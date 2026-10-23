"""Local source acquisition preserves the initialized numerical example."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import URLError

from scinet.workspace import init_workspace
from scripts import acquire


FULLTEXT = {"paper.pdf", "paper.txt", "author_page.html", "author_page.txt"}
PDF_BYTES = b"%PDF-test fixture; extraction is mocked"
HTML_BYTES = b"<html><style>hidden css</style><h1>Same Stats</h1><script>hidden js</script><p>Author evidence</p></html>"


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = init_workspace(Path(self.temp.name) / "demo")
        self.sources = self.root / "sources"
        self.manifest = self.sources / "provenance.json"
        self.original = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.network = patch.object(acquire.urllib.request, "urlopen",
                                    side_effect=AssertionError("Unexpected network call"))
        self.urlopen = self.network.start()
        self.addCleanup(self.network.stop)

    def invoke(self, *args):
        self.stdout, self.stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(self.stdout), redirect_stderr(self.stderr):
            try:
                return acquire.main(["--workspace", str(self.root), *args])
            except TypeError as error:
                self.fail(f"Acquisition does not yet support the workspace CLI: {error}")

    def mock_success(self):
        def download(request, **kwargs):
            return io.BytesIO({acquire.PDF: PDF_BYTES, acquire.PAGE: HTML_BYTES}[request.full_url])
        self.urlopen.side_effect = download
        reader = patch("pypdf.PdfReader", return_value=SimpleNamespace(pages=[
            SimpleNamespace(extract_text=lambda: "Page one scientific evidence"),
            SimpleNamespace(extract_text=lambda: "Page two scientific evidence"),
        ]))
        reader.start()
        self.addCleanup(reader.stop)

    def snapshot(self):
        return {path.relative_to(self.root).as_posix():
                path.read_bytes() if path.is_file() else None
                for path in self.root.rglob("*")}

    def test_workspace_acquisition_preserves_fixtures_and_extends_provenance(self):
        self.mock_success()
        before = self.snapshot()
        started = datetime.now(timezone.utc)
        self.assertEqual(self.invoke(), 0, self.stderr.getvalue())
        after = self.snapshot()
        for path, content in before.items():
            if path != "sources/provenance.json":
                self.assertEqual(after[path], content, path)
        self.assertEqual(set(after) - set(before), {"sources/" + name for name in FULLTEXT})
        self.assertFalse((self.root / "vendor" / "same-stats" / ".git").exists())
        self.assertEqual((self.sources / "paper.pdf").read_bytes(), PDF_BYTES)
        self.assertEqual((self.sources / "author_page.html").read_bytes(), HTML_BYTES)
        self.assertEqual((self.sources / "paper.txt").read_text(encoding="utf-8"),
                         "=== PDF PAGE 1 ===\nPage one scientific evidence\n\n"
                         "=== PDF PAGE 2 ===\nPage two scientific evidence")
        self.assertEqual((self.sources / "author_page.txt").read_text(encoding="utf-8"),
                         "Same Stats\nAuthor evidence")
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        for key, value in self.original.items():
            if key != "files":
                self.assertEqual(manifest[key], value, key)
        self.assertEqual(manifest["files"][:len(self.original["files"])], self.original["files"])
        acquired = datetime.fromisoformat(manifest["acquired_at_utc"])
        self.assertGreaterEqual(acquired, started)
        self.assertLessEqual(acquired, datetime.now(timezone.utc))
        self.assertTrue(manifest["fulltext_local_only"])
        entries = {entry["path"]: entry for entry in manifest["files"]}
        self.assertEqual(set(entries) - {entry["path"] for entry in self.original["files"]}, FULLTEXT)
        self.assertEqual(entries["paper.pdf"]["url"], acquire.PDF)
        self.assertEqual(entries["author_page.html"]["url"], acquire.PAGE)
        self.assertEqual(entries["paper.txt"]["derived_from"], "paper.pdf")
        self.assertEqual(entries["author_page.txt"]["derived_from"], "author_page.html")
        for name in FULLTEXT:
            raw = (self.sources / name).read_bytes()
            self.assertEqual(entries[name]["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(entries[name]["bytes"], len(raw))

    def test_existing_fulltext_is_never_overwritten_or_downloaded_again(self):
        for name in sorted(FULLTEXT):
            with self.subTest(name=name):
                target = self.sources / name
                target.write_bytes(b"local content to preserve")
                before = self.snapshot()
                self.assertEqual(self.invoke(), 1)
                self.assertIn(name, self.stderr.getvalue())
                self.assertEqual(self.snapshot(), before)
                self.urlopen.assert_not_called()
                target.unlink()

    def test_second_download_failure_leaves_no_partial_files_or_staging_directory(self):
        self.urlopen.side_effect = [io.BytesIO(PDF_BYTES), URLError("network unavailable")]
        before = self.snapshot()
        self.assertEqual(self.invoke(), 1)
        self.assertIn("network unavailable", self.stderr.getvalue())
        self.assertEqual(self.snapshot(), before)

    def test_pdf_parse_failure_leaves_workspace_unchanged(self):
        self.mock_success()
        before = self.snapshot()
        with patch("pypdf.PdfReader", side_effect=ValueError("invalid PDF")):
            self.assertEqual(self.invoke(), 1)
        self.assertIn("invalid PDF", self.stderr.getvalue())
        self.assertEqual(self.snapshot(), before)

    def test_partial_pdf_extraction_failure_leaves_workspace_unchanged(self):
        self.mock_success()
        before = self.snapshot()
        def fail_extraction():
            raise ValueError("unreadable PDF page")
        with patch("pypdf.PdfReader", return_value=SimpleNamespace(pages=[
                SimpleNamespace(extract_text=lambda: "First page"),
                SimpleNamespace(extract_text=fail_extraction)])):
            self.assertEqual(self.invoke(), 1)
        self.assertIn("unreadable PDF page", self.stderr.getvalue())
        self.assertEqual(self.snapshot(), before)

    def test_source_hash_mismatch_is_rejected_before_download(self):
        (self.sources / "DatasaurusDozen.tsv").write_bytes(b"edited numerical data")
        before = self.snapshot()
        self.assertEqual(self.invoke(), 1)
        self.assertIn("DatasaurusDozen.tsv", self.stderr.getvalue())
        self.assertIn("hash", self.stderr.getvalue().lower())
        self.assertEqual(self.snapshot(), before)
        self.urlopen.assert_not_called()

    def test_vendor_hash_mismatch_is_rejected_before_download(self):
        vendor_file = self.root / self.original["vendor_files"][0]["path"]
        vendor_file.write_bytes(b"edited vendor data")
        before = self.snapshot()
        self.assertEqual(self.invoke(), 1)
        self.assertIn(vendor_file.name, self.stderr.getvalue())
        self.assertIn("hash", self.stderr.getvalue().lower())
        self.assertEqual(self.snapshot(), before)
        self.urlopen.assert_not_called()

    def test_workspace_must_be_initialized_before_acquisition(self):
        missing = Path(self.temp.name) / "uninitialized"
        self.root = missing
        self.assertEqual(self.invoke(), 1)
        self.assertIn("scinet init", self.stderr.getvalue())
        self.assertFalse(missing.exists())
        self.urlopen.assert_not_called()

    def test_help_explains_local_only_fulltext_excluded_from_release(self):
        with self.assertRaises(SystemExit) as result:
            self.invoke("--help")
        self.assertEqual(result.exception.code, 0)
        help_text = self.stdout.getvalue().lower()
        self.assertIn("local-only", help_text)
        self.assertIn("excluded from", help_text)
        self.assertIn("release", help_text)
        self.assertIn("scinet init", help_text)
        self.urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
