"""Continuation checks use fake reviews and a mocked computation process only."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_panel as fixtures
from scinet import panel
from scinet.evidence import read_json, write_json
from scinet.panel_record import append_event, commit, inventory, load_events, object_hash

try:
    from scinet.panel_resume import fork_for_synthesis, verify_continuation
except ImportError:
    fork_for_synthesis = verify_continuation = None


class PanelResumeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(fork_for_synthesis, 'continuation implementation is required')
        self.fixture = fixtures.PanelTests('test_empty_findings_are_valid_but_fabricated_evidence_is_not')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root

    def source(self, state='checks_completed'):
        run = self.fixture.create()
        if state == 'prepared':
            return run
        panel.run_reviews(run, runner=fixtures.fake_model)
        if state == 'reviews_frozen':
            return run
        script = self.root / 'mock_check.py'
        script.write_text('# mocked transport only; never executed\n', encoding='utf-8')

        def computed(args, **kwargs):
            output = Path(args[-1])
            output.mkdir()
            write_json(output / 'result.json', {'fixture': True})
            return SimpleNamespace(returncode=0)

        with patch('scinet.panel.subprocess.run', side_effect=computed):
            panel.run_checks(run, script)
        if state == 'synthesis_failed':
            def failed(**kwargs):
                output = kwargs['output_dir']
                output.mkdir()
                write_json(output / 'call.json', {'status': 'cli_failed', 'error': 'fixture input limit'})
                (output / 'stderr.log').write_text('fixture input limit', encoding='utf-8')
                (output / 'events.jsonl').write_text('', encoding='utf-8')
                raise RuntimeError('fixture input limit')
            with self.assertRaises(RuntimeError):
                panel.synthesize(run, model='model-a', runner=failed)
        self.assertEqual(panel.verify_panel(run), [])
        return run

    def test_fork_keeps_source_and_complete_failed_parent_archive_unchanged(self):
        source = self.source('synthesis_failed')
        (source / 'empty_diagnostics').mkdir()
        (source / 'report.html').write_text('original failed-run report', encoding='utf-8')
        commit(source)
        before = inventory(source)
        root = read_json(source / 'commitment.json')['root_sha256']
        target = self.root / 'continuation'
        self.assertEqual(fork_for_synthesis(source, target), target)
        self.assertEqual(inventory(source), before)
        self.assertEqual(inventory(target / 'parent_bundle'), before)
        self.assertTrue((target / 'parent_bundle/empty_diagnostics').is_dir())
        self.assertEqual((target / 'parent_bundle/commitment.json').read_bytes(),
                         (source / 'commitment.json').read_bytes())
        self.assertTrue((target / 'parent_bundle/synthesis/stderr.log').is_file())
        for name in ['synthesis', 'report.html', 'synthesis_prompt.txt', 'synthesis_schema.json', 'synthesis_inputs.json']:
            self.assertFalse((target / name).exists(), name)
        meta = read_json(target / 'panel.json')
        self.assertEqual(meta['state'], 'checks_completed')
        self.assertNotIn('error', meta)
        self.assertTrue(meta['continuation'])
        record = read_json(target / 'continuation.json')
        self.assertEqual(record['parent_root_sha256'], root)
        self.assertEqual(record['parent_state'], 'synthesis_failed')
        self.assertIn('reuse', record['purpose'])
        self.assertTrue(record['implementation'])
        self.assertEqual(verify_continuation(target), [])
        self.assertEqual(panel.verify_panel(target), [])

    def test_rejects_incomplete_prerequisites_and_existing_or_nested_output(self):
        source = self.source('prepared')
        target = self.root / 'new'
        with self.assertRaises(ValueError):
            fork_for_synthesis(source, target)
        self.assertFalse(target.exists())
        panel.run_reviews(source, runner=fixtures.fake_model)
        with self.assertRaises(ValueError):
            fork_for_synthesis(source, target)
        self.assertFalse(target.exists())
        existing = self.root / 'existing'; existing.mkdir()
        (existing / 'sentinel.txt').write_text('keep')
        with self.assertRaises((ValueError, FileExistsError)):
            fork_for_synthesis(source, existing)
        with self.assertRaises(ValueError):
            fork_for_synthesis(source, source / 'nested')
        self.assertEqual((existing / 'sentinel.txt').read_text(), 'keep')

    def test_source_integrity_failure_is_rejected_without_creating_output(self):
        source = self.source()
        (source / 'reviews/r1/response.json').write_text('{}', encoding='utf-8')
        target = self.root / 'bad'
        with self.assertRaises(ValueError):
            fork_for_synthesis(source, target)
        self.assertFalse(target.exists())

    def test_parent_tampering_is_detected_even_after_parent_and_outer_recommit(self):
        target = fork_for_synthesis(self.source('synthesis_failed'), self.root / 'new')
        archived = target / 'parent_bundle'
        (archived / 'synthesis/stderr.log').write_text('rewritten failed attempt', encoding='utf-8')
        commit(archived); commit(target)
        self.assertTrue(verify_continuation(target))

    def test_changed_original_response_or_freeze_cannot_be_resealed(self):
        target = fork_for_synthesis(self.source(), self.root / 'new')
        path = target / 'reviews/r1/response.json'
        path.write_text('{}', encoding='utf-8')
        commit(target)
        self.assertTrue(verify_continuation(target))
        path.write_bytes((target / 'parent_bundle/reviews/r1/response.json').read_bytes())
        freeze = target / 'checks_freeze.json'
        record = read_json(freeze); record['frozen_at_utc'] = '2000-01-01T00:00:00+00:00'
        write_json(freeze, record); commit(target)
        self.assertTrue(verify_continuation(target))

    def test_current_implementation_and_continuation_event_are_bound(self):
        target = fork_for_synthesis(self.source(), self.root / 'new')
        path = target / 'continuation_implementation/panel_resume.py'
        original = path.read_bytes()
        path.write_bytes(original + b'\n# changed\n'); commit(target)
        self.assertTrue(verify_continuation(target))
        path.write_bytes(original)
        events = load_events(target)
        events[-1]['data']['parent_root_sha256'] = '0' * 64
        events[-1]['event_hash'] = object_hash({k: v for k, v in events[-1].items() if k != 'event_hash'})
        (target / 'timeline.jsonl').write_text('\n'.join(json.dumps(e) for e in events) + '\n', encoding='utf-8')
        commit(target)
        self.assertTrue(verify_continuation(target))

    def test_parent_timeline_is_exact_prefix_and_continuation_is_immediate(self):
        source = self.source('synthesis_failed')
        target = fork_for_synthesis(source, self.root / 'new')
        before = (source / 'timeline.jsonl').read_bytes()
        self.assertTrue((target / 'timeline.jsonl').read_bytes().startswith(before))
        parent_events = load_events(source)
        self.assertEqual(load_events(target)[:len(parent_events)], parent_events)
        self.assertEqual(load_events(target)[len(parent_events)]['event'], 'synthesis_continuation')
        append_event(target, 'synthesis_started', {'model': 'fixture'})
        commit(target)
        self.assertEqual(verify_continuation(target), [])
        events = load_events(target)
        events[len(parent_events)]['event'], events[-1]['event'] = events[-1]['event'], events[len(parent_events)]['event']
        previous = None
        for event in events:
            event['previous_hash'] = previous
            event['event_hash'] = object_hash({k: v for k, v in event.items() if k != 'event_hash'})
            previous = event['event_hash']
        (target / 'timeline.jsonl').write_text('\n'.join(json.dumps(e) for e in events) + '\n', encoding='utf-8')
        commit(target)
        self.assertTrue(verify_continuation(target))

    def test_noncontinuation_needs_no_parent_and_original_responses_are_reused(self):
        source = self.source()
        self.assertEqual(verify_continuation(source), [])
        target = fork_for_synthesis(source, self.root / 'new')
        for member in ('r1', 'r2'):
            self.assertEqual((target / f'reviews/{member}/response.json').read_bytes(),
                             (source / f'reviews/{member}/response.json').read_bytes())
        self.assertEqual(inventory(target / 'reviews'), inventory(source / 'reviews'))
        self.assertEqual(inventory(target / 'checks'), inventory(source / 'checks'))

    def test_continuation_cannot_hide_its_relationship_by_removing_the_record(self):
        target = fork_for_synthesis(self.source(), self.root / 'new')
        (target / 'continuation.json').unlink()
        commit(target)
        self.assertTrue(verify_continuation(target))


if __name__ == '__main__':
    unittest.main()
