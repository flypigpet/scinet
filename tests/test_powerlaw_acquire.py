"""Pinned acquisition contract; network and PDF extraction are mocked."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import URLError


SCRIPT = Path(__file__).resolve().parents[1] / 'examples/powerlaw/acquire.py'
EXTRACTED = b'=== PDF PAGE 1 ===\nFirst source page\n\n=== PDF PAGE 2 ===\n'


class PowerlawAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'Powerlaw source acquisition entry point is missing')
        spec = importlib.util.spec_from_file_location('powerlaw_acquire_test', SCRIPT)
        self.acquire = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.acquire)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'packet'
        self.fixture_bytes = {source['path']: ('fixture:' + source['path']).encode()
                              for source in self.acquire.SOURCES}
        self.sources = [{**source, 'sha256': hashlib.sha256(self.fixture_bytes[source['path']]).hexdigest()}
                        for source in self.acquire.SOURCES]
        self.by_url = {source['source_url']: self.fixture_bytes[source['path']] for source in self.sources}
        self.network = patch.object(self.acquire.urllib.request, 'urlopen',
                                    side_effect=lambda request, **kwargs: io.BytesIO(self.by_url[request.full_url]))
        self.urlopen = self.network.start()
        self.addCleanup(self.network.stop)
        self.pdf = patch('pypdf.PdfReader', return_value=SimpleNamespace(pages=[
            SimpleNamespace(extract_text=lambda: 'First source page'),
            SimpleNamespace(extract_text=lambda: None)]))
        self.pdf.start(); self.addCleanup(self.pdf.stop)

    def invoke(self):
        with patch.object(self.acquire, 'SOURCES', self.sources), \
                patch.object(self.acquire, 'PAPER_TEXT_SHA256', hashlib.sha256(EXTRACTED).hexdigest()), \
                patch('pypdf.__version__', '6.14.2'):
            return self.acquire.acquire(self.output)

    def read(self, name):
        return json.loads((self.output / name).read_text(encoding='utf-8'))

    def test_success_writes_original_material_packet_without_review_or_computation(self):
        bundle_path = self.invoke()
        self.assertEqual(bundle_path, self.output / 'bundle.json')
        bundle = self.read('bundle.json')
        self.assertEqual(bundle['paper']['doi'], '10.1371/journal.pone.0085777')
        self.assertEqual(len(bundle['files']), 8)
        self.assertEqual((self.output / 'paper.txt').read_bytes(), EXTRACTED)
        entries = {entry['path']: entry for entry in bundle['files']}
        self.assertFalse(entries['paper.pdf']['include_in_review'])
        for name, entry in entries.items():
            self.assertEqual(entry['sha256'], hashlib.sha256((self.output / name).read_bytes()).hexdigest())
            self.assertTrue(entry['source_url'].startswith('https://'))
            self.assertIn(entry['role'], {'paper', 'code', 'data', 'license'})
            if name != 'paper.pdf':
                self.assertTrue(entry['include_in_review'])
        self.assertEqual(self.read('acquisition.json')['status'], 'completed')
        self.assertIn('rights', bundle)
        self.assertIn('author_code_version', bundle)
        self.assertIn('data_repository_commit', bundle)
        self.assertEqual(set(p.name for p in self.output.iterdir()),
                         set(entries) | {'bundle.json', 'acquisition.json'})
        self.assertEqual(self.urlopen.call_count, 7)

    def test_fixed_original_hashes_and_derived_hash_are_preserved(self):
        expected = {
            'paper.pdf': '578d1c7bfa991141f00575acea8a243cbf534608c6e1cb497705a7064bb54799',
            'author_powerlaw.py': '547c0e2d33b09ca8078e8d2abde686412ea1f548bb1a8e5b4d019006d929a105',
            'author_figures.py': '809d7a28227ede36ea90e1b611ef56a2575c3cd630b0c6894dd001e8554c3bdb',
            'blackouts.txt': '8187543b5700a75974661dd8349e172a83ce2d0972e79a81a7fcc06eafb96728',
            'words.txt': 'cef3521f0f1d817df43cf35ef1f717e6f72d71f549646a51ba04acdc45a9b160',
            'worm.txt': '8754d06905e1d2318e19ba3e8b936f653657893b9ff8ce9fbc51ad9b26f992ac',
            'AUTHOR_LICENSE.txt': 'ec7e397e8ae8c4e0cf1571f61f435fbdec8f28080fce4befc96fd13554a726ef',
        }
        self.assertEqual({s['path']: s['sha256'] for s in self.acquire.SOURCES}, expected)
        self.assertEqual(self.acquire.PAPER_TEXT_SHA256,
                         '83b2ec926d17aa4eae8e47a336d0781fd6bb2775a0fd061cdcad32d7ff3647ef')

    def test_existing_directory_even_empty_is_never_reused(self):
        self.output.mkdir()
        with self.assertRaises(FileExistsError):
            self.invoke()
        self.assertEqual(list(self.output.iterdir()), [])
        self.urlopen.assert_not_called()

    def test_hash_mismatch_keeps_rejected_bytes_without_publishing_bundle(self):
        self.by_url[self.sources[0]['source_url']] = b'upstream changed'
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.invoke()
        self.assertEqual((self.output / 'paper.pdf').read_bytes(), b'upstream changed')
        record = self.read('acquisition.json')
        self.assertEqual(record['status'], 'failed')
        self.assertEqual(record['files'][0]['status'], 'hash_mismatch')
        self.assertFalse((self.output / 'bundle.json').exists())
        self.assertEqual(self.urlopen.call_count, 1)

    def test_network_failure_keeps_previous_downloads_and_failure_record(self):
        self.urlopen.side_effect = [io.BytesIO(self.fixture_bytes['paper.pdf']), URLError('offline')]
        with self.assertRaises(URLError):
            self.invoke()
        self.assertEqual((self.output / 'paper.pdf').read_bytes(), self.fixture_bytes['paper.pdf'])
        record = self.read('acquisition.json')
        self.assertEqual(record['status'], 'failed')
        self.assertIn('offline', record['error'])
        self.assertIn('finished_at_utc', record)
        self.assertFalse((self.output / 'bundle.json').exists())

    def test_changed_extraction_is_rejected_after_preserving_all_sources(self):
        with patch('pypdf.PdfReader', return_value=SimpleNamespace(pages=[
                SimpleNamespace(extract_text=lambda: 'Different extraction')])):
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                self.invoke()
        self.assertEqual(self.urlopen.call_count, 7)
        self.assertTrue((self.output / 'paper.txt').is_file())
        self.assertEqual(self.read('acquisition.json')['status'], 'failed')
        self.assertFalse((self.output / 'bundle.json').exists())

    def test_wrong_pypdf_version_fails_before_network_and_keeps_status(self):
        with patch('pypdf.__version__', '0.0.0'):
            with self.assertRaisesRegex(RuntimeError, '6.14.2'):
                self.acquire.acquire(self.output)
        self.urlopen.assert_not_called()
        self.assertEqual(self.read('acquisition.json')['status'], 'failed')

    def test_cli_reports_failures_without_overwriting(self):
        self.output.mkdir()
        stderr = io.StringIO()
        with redirect_stderr(stderr), redirect_stdout(io.StringIO()):
            self.assertEqual(self.acquire.main(['--output', str(self.output)]), 1)
        self.assertTrue(stderr.getvalue())
        self.urlopen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
