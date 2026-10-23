from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from scinet.evidence import read_json, seal, verify, write_json
from scinet import pipeline


class PipelineFailureTests(unittest.TestCase):
    def make_run(self, root, failed=False):
        run = root / 'output' / 'run-test'
        run.mkdir(parents=True)
        write_json(run / 'metrics.json', {'crosscheck': {'passed': not failed}})
        write_json(run / 'author_smoke.json', {'status': 'timeout' if failed else 'passed'})
        write_json(run / 'run.json', {'ai_review_status': 'not_run'})
        for name in ('paper.txt', 'author_page.txt', 'author_code.py', 'claims.json'):
            (run / name).write_text('example', encoding='utf-8')
        seal(run)
        return run

    def test_failed_computation_does_not_get_ai_or_publish_latest(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); run = self.make_run(root, failed=True)
            with patch.object(pipeline, 'ROOT', root), patch.object(pipeline, 'prepare_run', return_value=run), \
                    patch.object(pipeline, 'review_run') as ai, patch.object(pipeline, 'report_run'), \
                    patch('sys.argv', ['scinet', 'run', '--ai', '--model', 'test-model']):
                self.assertEqual(pipeline.main(), 1)
            ai.assert_not_called()
            self.assertFalse((root / 'output' / 'latest.txt').exists())
            self.assertTrue(pipeline.verify_run(run))

    def test_missing_cli_keeps_evidence_valid_and_retryable(self):
        with tempfile.TemporaryDirectory() as d:
            run = self.make_run(Path(d))
            with patch.dict('os.environ', {}, clear=True), patch('shutil.which', return_value=None):
                with self.assertRaises(RuntimeError): pipeline.review_run(run, model='test-model')
            self.assertEqual(verify(run), [])
            self.assertFalse((run / 'review.json').exists())

    def test_completed_ai_status_requires_actual_review(self):
        with tempfile.TemporaryDirectory() as d:
            run = self.make_run(Path(d))
            write_json(run / 'run.json', {'ai_review_status': 'fresh_completed'})
            seal(run)
            self.assertTrue(pipeline.verify_run(run))

    def test_cancelled_ai_preserves_verifiable_compute_results(self):
        with tempfile.TemporaryDirectory() as d:
            run = self.make_run(Path(d))
            with patch.dict('os.environ', {'CODEX_CLI_PATH':'test-cli'}), \
                    patch.object(pipeline, 'cli_version', return_value='test-cli 1.0'), \
                    patch.object(pipeline.subprocess, 'run', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt): pipeline.review_run(run, model='test-model')
            self.assertEqual(verify(run), [])
            self.assertEqual(read_json(run/'review_provenance.json')['status'], 'interrupted')
            self.assertEqual(read_json(run/'run.json')['ai_review_status'], 'not_run')

    def test_review_requires_explicit_model_without_modifying_run(self):
        with tempfile.TemporaryDirectory() as d:
            run = self.make_run(Path(d))
            before = (run/'manifest.json').read_bytes()
            with self.assertRaisesRegex(ValueError, 'model'):
                pipeline.review_run(run, model=' ')
            self.assertEqual(before, (run/'manifest.json').read_bytes())

    def test_missing_paper_is_detected_before_review_files_are_written(self):
        with tempfile.TemporaryDirectory() as d:
            run = self.make_run(Path(d))
            (run/'paper.txt').unlink(); seal(run)
            with self.assertRaisesRegex(ValueError, 'paper.txt'):
                pipeline.review_run(run, model='test-model')
            self.assertEqual(verify(run), [])
            self.assertFalse((run/'review_input_hashes.json').exists())

    def test_success_records_requested_model_without_claiming_resolved_version(self):
        with tempfile.TemporaryDirectory() as d:
            run = self.make_run(Path(d))
            def respond(args, **kwargs):
                self.assertEqual(args[args.index('--model')+1], 'test-model')
                self.assertIn('--ignore-user-config', args)
                write_json(run/'review.json', {
                    'summary':'Mock response for protocol testing, not scientific evidence.',
                    'findings':[{'id':str(i),'claim_id':f'C{i}','status':'not_tested',
                        'title':'Mock','explanation':'Test only',
                        'evidence':[{'path':'claims.json','locator':f'C{i}'}]} for i in range(1,5)],
                    'limitations':['Mocked model response.']})
                return SimpleNamespace(returncode=0)
            with patch.dict('os.environ', {'CODEX_CLI_PATH':'test-cli'}), \
                    patch.object(pipeline, 'cli_version', return_value='test-cli 1.0'), \
                    patch.object(pipeline.subprocess, 'run', side_effect=respond):
                pipeline.review_run(run, model='test-model')
            prov = read_json(run/'review_provenance.json')
            self.assertEqual(prov['model_requested'], 'test-model')
            self.assertIsNone(prov['model_resolved'])
            self.assertEqual(prov['cli_version'], 'test-cli 1.0')
            self.assertEqual(pipeline.verify_run(run), [])

    def test_explicit_workspace_is_passed_to_run_and_latest_resolves(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); run=self.make_run(root)
            with patch.object(pipeline, 'prepare_run', return_value=run) as prepare, \
                    patch.object(pipeline, 'report_run'), \
                    patch('sys.argv', ['scinet','--workspace',str(root),'run']):
                self.assertEqual(pipeline.main(),0)
            prepare.assert_called_once_with(root.resolve())
            with patch('sys.argv', ['scinet','--workspace',str(root),'verify','latest']):
                self.assertEqual(pipeline.main(),0)


if __name__ == '__main__': unittest.main()
