import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scinet.evidence import digest, read_json, write_json
from scinet.panel_record import commit, inventory, now, object_hash
try:
    from scinet import panel
except ImportError:
    panel = None


def original_review(assessment='concern'):
    return {'summary': 'Original independent review', 'findings': [{
        'id': 'F1', 'title': 'An independently selected observation',
        'assessment': assessment, 'explanation': 'Interpretation of original material',
        'evidence': [{'path': 'inputs/paper.txt', 'locator': 'line 1'}],
        'proposed_check': 'Compute the reported statistic'}],
        'reproduction_targets': [], 'limitations': ['Test fixture; no real model call']}


def save_mock_response(response, **kwargs):
    out = kwargs['output_dir']; out.mkdir(exist_ok=True)
    started = now()
    write_json(out / 'response.json', response)
    thread_id = 'test-' + kwargs['output_dir'].name + '-' + kwargs['model']
    events = [{'type': 'thread.started', 'thread_id': thread_id},
              {'type': 'turn.started'},
              {'type': 'item.completed', 'item': {'id': '1', 'type': 'agent_message', 'text': json.dumps(response)}},
              {'type': 'turn.completed', 'usage': {'input_tokens': 1, 'output_tokens': 1}}]
    (out / 'events.jsonl').write_text('\n'.join(json.dumps(e) for e in events) + '\n', encoding='utf-8')
    (out / 'stderr.log').write_text('', encoding='utf-8')
    record = {'status': 'completed', 'exit_code': 0, 'model_requested': kwargs['model'],
              'model_resolved': None, 'tool_calls_observed': False,
              'prompt_sha256': digest(kwargs['prompt_path']), 'schema_sha256': digest(kwargs['schema_path']),
              'response_sha256': digest(out / 'response.json'), 'events_sha256': digest(out / 'events.jsonl'),
              'stderr_sha256': digest(out / 'stderr.log'),
              'usage': [{'input_tokens': 1, 'output_tokens': 1}], 'thread_id': thread_id,
              'turn_completed_count': 1, 'item_types': ['agent_message'],
              'started_at_utc': started, 'finished_at_utc': now()}
    from scinet.panel_model import REQUEST_CONFIG
    record['request_config'] = dict(REQUEST_CONFIG)
    write_json(out / 'call.json', record)
    return record


def fake_model(**kwargs):
    return save_mock_response(original_review('concern' if kwargs['model'] == 'model-a' else 'supported'), **kwargs)


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(panel, 'panel implementation required')
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = self.root / 'source'; source.mkdir()
        (source / 'paper.txt').write_text('A reported result with raw supporting data.', encoding='utf-8')
        (source / 'data.txt').write_text('1\n2\n3\n', encoding='utf-8')
        self.bundle = source / 'bundle.json'
        write_json(self.bundle, {'paper': {'title': 'Example paper', 'doi': 'test'},
            'selection_disclosure': 'Coordinator has seen an earlier review.',
            'files': [{'path': p, 'role': role, 'sha256': digest(source / p),
                       'source_url': 'https://example.org/' + p, 'include_in_review': True}
                      for p, role in [('paper.txt', 'paper'), ('data.txt', 'data')]]})

    def create(self):
        return panel.create_panel(self.bundle, self.root / 'run', ['model-a', 'model-b'])

    def review(self, run):
        # The transport has its own raw-event tests. This fixture is not a live call.
        with patch('scinet.panel.validate_call', return_value=[]):
            panel.run_reviews(run, runner=fake_model)

    def test_common_prompt_has_original_sources_without_issue_cues_or_old_results(self):
        run = self.create()
        text = (run / 'prompt.txt').read_text(encoding='utf-8')
        self.assertIn('A reported result with raw supporting data.', text)
        for withheld in ('Coordinator has seen', 'claims.json', 'metrics.json', 'rounding', 'sigma_threshold'):
            self.assertNotIn(withheld, text)
        seen = []
        def record(**kw):
            seen.append(kw['prompt_path'].read_bytes())
            self.assertFalse((run / 'checks').exists())
            return fake_model(**kw)
        with patch('scinet.panel.validate_call', return_value=[]):
            panel.run_reviews(run, runner=record)
        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[0], seen[1])
        self.assertEqual(read_json(run / 'panel.json')['state'], 'reviews_frozen')
        frozen = read_json(run / 'reviews_freeze.json')
        self.assertEqual(set(frozen['reviewers']), {'r1', 'r2'})

    def test_duplicate_models_and_wrong_source_hash_fail_before_output(self):
        for models in (['same', 'same'], ['single']):
            with self.assertRaises(ValueError):
                panel.create_panel(self.bundle, self.root / 'bad', models)
        (self.bundle.parent / 'paper.txt').write_text('changed')
        with self.assertRaises(ValueError):
            panel.create_panel(self.bundle, self.root / 'bad', ['a', 'b'])
        self.assertFalse((self.root / 'bad').exists())

    def test_failed_reviewer_preserves_other_response_and_blocks_computation(self):
        run = self.create()
        def fail_second(**kw):
            if kw['model'] == 'model-b':
                raise RuntimeError('provider unavailable')
            return fake_model(**kw)
        with patch('scinet.panel.validate_call', return_value=[]), self.assertRaises(RuntimeError):
            panel.run_reviews(run, runner=fail_second)
        self.assertTrue((run / 'reviews/r1/response.json').exists())
        self.assertFalse((run / 'reviews_freeze.json').exists())
        self.assertEqual(read_json(run / 'panel.json')['state'], 'review_failed')
        with self.assertRaises(ValueError):
            panel.run_checks(run, self.root / 'missing.py')
        self.assertFalse((run / 'checks').exists())

    def test_stale_input_is_rejected_before_any_model_call(self):
        run = self.create()
        (run / 'inputs/paper.txt').write_text('changed')
        with self.assertRaises(ValueError):
            panel.run_reviews(run, runner=lambda **kw: self.fail('Model must not be called'))

    def test_cannot_overwrite_or_repeat_reviews(self):
        run = self.create()
        with self.assertRaises(FileExistsError):
            self.create()
        self.review(run)
        before = inventory(run / 'reviews')
        with self.assertRaises(ValueError):
            panel.run_reviews(run, runner=fake_model)
        self.assertEqual(before, inventory(run / 'reviews'))

    def test_empty_findings_are_valid_but_fabricated_evidence_is_not(self):
        run = self.create()
        review = original_review(); review['findings'] = []
        panel.validate_review(review, read_json(run / 'packet.json'))
        review = original_review(); review['findings'][0]['evidence'][0]['path'] = 'old_review.json'
        with self.assertRaises(ValueError):
            panel.validate_review(review, read_json(run / 'packet.json'))

    def test_recompute_starts_after_freeze_and_keeps_original_reviews(self):
        run = self.create(); self.review(run)
        before = inventory(run / 'reviews')
        script = self.root / 'check.py'
        script.write_text("import json,sys\nfrom pathlib import Path\np=Path(sys.argv[2]);p.mkdir(exist_ok=True)\n(p/'result.json').write_text(json.dumps({'mean':2.0}))\n", encoding='utf-8')
        with patch('scinet.panel.validate_call', return_value=[]):
            panel.run_checks(run, script)
            self.assertEqual(panel.verify_panel(run), [])
        execution = read_json(run / 'checks/execution.json')
        frozen = read_json(run / 'reviews_freeze.json')
        self.assertGreaterEqual(execution['started_at_utc'], frozen['frozen_at_utc'])
        self.assertEqual(before, inventory(run / 'reviews'))
        self.assertEqual(read_json(run / 'panel.json')['state'], 'checks_completed')

    def test_changed_review_blocks_recompute_even_with_new_outer_commitment(self):
        run = self.create(); self.review(run)
        (run / 'reviews/r1/response.json').write_text('{}')
        commit(run)
        with patch('scinet.panel.validate_call', return_value=[]), self.assertRaises(ValueError):
            panel.run_checks(run, self.root / 'absent.py')

    def test_synthesis_requires_exact_finding_coverage_and_explicit_multireviewer_disagreement(self):
        run = self.create(); self.review(run)
        pos = {'reviewer_id': 'r1', 'finding_id': 'F1', 'verdict': 'unresolved',
               'verification_basis': 'insufficient_evidence',
               'rationale': 'No decisive computation',
               'evidence': [{'path': 'inputs/paper.txt', 'locator': 'line 1'}]}
        result = {'summary': 'test', 'groups': [{'id': 'G1', 'title': 'topic',
            'relationship': 'disagreement', 'explanation': 'Different views', 'positions': [pos]}],
            'limitations': ['Automated synthesis']}
        with self.assertRaises(ValueError):
            panel.validate_synthesis(result, run, {'inputs/paper.txt'})
        result['groups'][0]['positions'].append({**pos, 'reviewer_id': 'r2'})
        panel.validate_synthesis(result, run, {'inputs/paper.txt'})
        result['groups'][0]['positions'].append(pos)
        with self.assertRaises(ValueError):
            panel.validate_synthesis(result, run, {'inputs/paper.txt'})

    def test_complete_protocol_uses_raw_event_validation_and_keeps_both_positions(self):
        run = self.create()
        panel.run_reviews(run, runner=fake_model)
        script = self.root / 'check.py'
        script.write_text("import sys,json\nfrom pathlib import Path\np=Path(sys.argv[2]);p.mkdir()\n(p/'result.json').write_text(json.dumps({'value':42}))\nfor suffix in ('csv','tsv'): (p/('result.'+suffix)).write_text('value\\n42\\n')\n(p/'unselected.log').write_text('EXCLUDED_LOG_CONTENT')\n", encoding='utf-8')
        panel.run_checks(run, script)
        before = inventory(run / 'reviews')
        def synth(**kw):
            supplied = kw['prompt_path'].read_text(encoding='utf-8')
            self.assertIn('checks/artifacts/result.csv', supplied)
            self.assertIn('checks/artifacts/result.tsv', supplied)
            self.assertNotIn('EXCLUDED_LOG_CONTENT', supplied)
            self.assertIn('explicit_selection', supplied)
            result = {'summary': 'Evidence leaves the different original views unresolved',
                'groups': [{'id': 'G1', 'title': 'Different readings', 'relationship': 'disagreement',
                    'explanation': 'The raw views differ; the check does not decide their interpretation',
                    'positions': [{'reviewer_id': r, 'finding_id': 'F1', 'verdict': 'not_tested',
                        'verification_basis': 'insufficient_evidence',
                        'rationale': 'The numerical output does not test this interpretation',
                        'evidence': [{'path': 'checks/artifacts/result.json', 'locator': 'value'}]}
                        for r in ('r1', 'r2')]}], 'limitations': ['Mock fixture, not scientific evidence']}
            return save_mock_response(result, **kw)
        selection = ['checks/artifacts/result.' + suffix for suffix in ('json', 'csv', 'tsv')]
        panel.synthesize(run, model='model-a', runner=synth, evidence_paths=selection)
        self.assertEqual(read_json(run / 'panel.json')['state'], 'complete')
        self.assertEqual(panel.verify_panel(run), [])
        self.assertEqual(inventory(run / 'reviews'), before)
        self.assertTrue((run / 'checks/artifacts/unselected.log').exists())
        selected = read_json(run / 'synthesis_selection.json')
        self.assertEqual(set(selected['included']), set(selection))
        self.assertIn('checks/artifacts/unselected.log', selected['excluded'])

    def test_prompt_character_limit_fails_before_call(self):
        with patch('scinet.panel.MAX_PROMPT_CHARS', 32), self.assertRaisesRegex(ValueError, 'character'):
            panel._prompt('review', {'title': 'paper'}, [{'content': 'x' * 33}])

    def test_failed_computation_is_retained_and_cannot_be_synthesized(self):
        run = self.create(); self.review(run)
        script = self.root / 'fail.py'; script.write_text("print('failure evidence')\nraise SystemExit(3)\n")
        with self.assertRaises(RuntimeError):
            panel.run_checks(run, script)
        self.assertEqual(read_json(run / 'panel.json')['state'], 'checks_failed')
        self.assertIn('failure evidence', (run / 'checks/stdout.log').read_text())
        with self.assertRaises(ValueError):
            panel.synthesize(run, model='model-a', runner=fake_model)

    def test_synthesis_cannot_treat_another_review_as_verification_evidence(self):
        run = self.create(); self.review(run)
        response = {'summary': 'claim', 'groups': [{'id': 'G1', 'title': 'group',
            'relationship': 'agreement', 'explanation': 'Both say so', 'positions': [
                {'reviewer_id': r, 'finding_id': 'F1', 'verdict': 'supported', 'rationale': 'Other model agrees',
                 'verification_basis': 'insufficient_evidence',
                 'evidence': [{'path': 'reviews/r1/response.json', 'locator': 'findings[0]'}]}
                for r in ('r1', 'r2')]}], 'limitations': ['test']}
        with self.assertRaisesRegex(ValueError, 'source|computation'):
            panel.validate_synthesis(response, run, {'reviews/r1/response.json'})

    def test_offline_verifier_checks_event_meaning_even_when_chain_is_rehashed(self):
        run = self.create(); self.review(run)
        path = run / 'timeline.jsonl'
        events = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        for event in events:
            if event['event'] == 'review_started':
                event['data']['model'] = 'wrong-model'
                break
        previous = None
        for event in events:
            event['previous_hash'] = previous
            event['event_hash'] = object_hash({k: v for k, v in event.items() if k != 'event_hash'})
            previous = event['event_hash']
        path.write_text('\n'.join(json.dumps(e) for e in events) + '\n', encoding='utf-8')
        commit(run)
        with patch('scinet.panel.validate_call', return_value=[]):
            self.assertTrue(panel.verify_panel(run))

    def test_reused_thread_id_cannot_be_frozen_as_independent_reviews(self):
        run = self.create()
        def reused(**kw):
            record = fake_model(**kw)
            record['thread_id'] = 'reused-thread'
            write_json(kw['output_dir'] / 'call.json', record)
            return record
        with patch('scinet.panel.validate_call', return_value=[]), self.assertRaises(ValueError):
            panel.run_reviews(run, runner=reused)
        self.assertFalse((run / 'reviews_freeze.json').exists())

    def test_checks_freeze_is_bound_to_event_log(self):
        run = self.create(); self.review(run)
        script = self.root / 'check.py'
        script.write_text("import sys\nfrom pathlib import Path\np=Path(sys.argv[2]);p.mkdir()\n(p/'result.txt').write_text('42')\n")
        panel.run_checks(run, script)
        (run / 'checks/artifacts/result.txt').write_text('999999')
        freeze = read_json(run / 'checks_freeze.json')
        freeze['files']['checks/artifacts/result.txt'] = {'sha256': digest(run / 'checks/artifacts/result.txt'), 'bytes': 6}
        write_json(run / 'checks_freeze.json', freeze); commit(run)
        self.assertTrue(panel.verify_panel(run))


if __name__ == '__main__':
    unittest.main()
