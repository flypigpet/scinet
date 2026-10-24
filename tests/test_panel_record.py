from pathlib import Path
import json
import tempfile
import unittest

try:
    from scinet import panel_record as records
except ImportError:
    records = None


class PanelRecordTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(records, 'panel record implementation is required')

    def test_commitment_is_portable_and_detects_changes_missing_and_extra_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'paper.txt').write_text('原始材料', encoding='utf-8')
            first = records.commit(root)
            self.assertEqual(records.verify_commitment(root), [])
            self.assertEqual(records.commit(root)['root_sha256'], first['root_sha256'])
            (root / 'paper.txt').write_text('changed', encoding='utf-8')
            self.assertTrue(records.verify_commitment(root))
            (root / 'paper.txt').unlink()
            self.assertTrue(records.verify_commitment(root))
            (root / 'extra.txt').write_text('unrecorded')
            self.assertTrue(records.verify_commitment(root))

    def test_nested_manifest_files_are_included(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / 'inputs').mkdir()
            (root / 'inputs/manifest.json').write_text('{}')
            record = records.commit(root)
            self.assertIn('inputs/manifest.json', record['payload']['files'])

    def test_external_root_detects_rewritten_self_consistent_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / 'paper.txt').write_text('original')
            pinned = records.commit(root)['root_sha256']
            (root / 'paper.txt').write_text('rewritten'); records.commit(root)
            self.assertEqual(records.verify_commitment(root), [])
            self.assertTrue(records.verify_commitment(root, expected_root=pinned))

    def test_commitment_rejects_path_escape_and_forged_root(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / 'file').write_text('data')
            record = records.commit(root)
            record['payload']['files']['../outside'] = {'sha256': '0' * 64, 'bytes': 0}
            (root / 'commitment.json').write_text(json.dumps(record))
            self.assertTrue(records.verify_commitment(root))

    def test_event_chain_records_sequence_and_detects_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            records.append_event(root, 'packet_frozen', {'prompt_sha256': 'a'})
            records.append_event(root, 'reviews_frozen', {'review_count': 2})
            self.assertEqual(records.verify_events(root), [])
            path = root / 'timeline.jsonl'
            events = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(events[1]['previous_hash'], events[0]['event_hash'])
            events[0]['data']['prompt_sha256'] = 'changed'
            path.write_text('\n'.join(json.dumps(e) for e in events))
            self.assertTrue(records.verify_events(root))

    def test_nonfinite_numbers_and_absolute_paths_rejected(self):
        with self.assertRaises(ValueError):
            records.canonical_bytes({'value': float('nan')})
        with tempfile.TemporaryDirectory() as d:
            for path in ('../x', '/x', 'C:/x', 'a\\b', ''):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    records.artifact_path(Path(d), path)


if __name__ == '__main__':
    unittest.main()
