from contextlib import ExitStack, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scinet import pipeline


class PanelCliTests(unittest.TestCase):
    def _patched_cli(self, argv, run):
        """Exercise real argument parsing without paid or computation calls."""
        stack = ExitStack()
        self.addCleanup(stack.close)
        calls = {name: stack.enter_context(patch('scinet.panel.' + name))
                 for name in ('create_panel', 'run_reviews', 'run_checks', 'synthesize',
                              'verify_panel', 'render_report')}
        calls['create_panel'].return_value = run
        calls['verify_panel'].return_value = []
        calls['render_report'].return_value = run / 'report.html'
        calls['fork'] = stack.enter_context(patch('scinet.panel_resume.fork_for_synthesis', return_value=run))
        stack.enter_context(patch('sys.argv', argv))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = pipeline.main()
        stack.close()
        return result, calls

    def test_panel_cli_runs_review_before_computation_and_synthesis(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d)
            calls = []
            with patch('scinet.panel.create_panel', return_value=run), \
                    patch('scinet.panel.run_reviews', side_effect=lambda *a, **k: calls.append('review')), \
                    patch('scinet.panel.run_checks', side_effect=lambda *a, **k: calls.append('compute')), \
                    patch('scinet.panel.synthesize', side_effect=lambda *a, **k: calls.append('synthesis')), \
                    patch('scinet.panel.verify_panel', return_value=[]), \
                    patch('scinet.panel.render_report', return_value=run / 'report.html'), \
                    patch('sys.argv', ['scinet', 'panel', 'run', '--bundle', 'bundle.json', '--output', d,
                        '--model', 'a', '--model', 'b', '--script', 'checked.py', '--synthesis-model', 'a']):
                self.assertEqual(pipeline.main(), 0)
            self.assertEqual(calls, ['review', 'compute', 'synthesis'])

    def test_panel_verify_returns_nonzero_for_changed_evidence(self):
        with patch('scinet.panel.verify_panel', return_value=['changed evidence']), \
                patch('sys.argv', ['scinet', 'panel', 'verify', 'run']):
            self.assertEqual(pipeline.main(), 1)

    def test_continue_synthesis_only_forks_and_synthesizes_with_recorded_selection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); run = root / 'continued'; parent = root / 'parent'
            selected = ['checks/artifacts/result.json']
            evidence_list = root / 'selection.json'
            evidence_list.write_text(json.dumps(selected), encoding='utf-8')
            result, calls = self._patched_cli(['scinet', 'panel', 'continue-synthesis', str(parent),
                '--output', str(run), '--model', 'judge', '--evidence-list', str(evidence_list)], run)
            self.assertEqual(result, 0)
            calls['fork'].assert_called_once_with(parent.resolve(), run)
            calls['synthesize'].assert_called_once_with(run, model='judge', timeout=600,
                                                       evidence_paths=selected)
            for name in ('create_panel', 'run_reviews', 'run_checks'):
                calls[name].assert_not_called()

    def test_bad_json_selection_fails_before_fork_or_paid_work(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); evidence_list = root / 'selection.json'
            evidence_list.write_text('{not JSON', encoding='utf-8')
            result, calls = self._patched_cli(['scinet', 'panel', 'continue-synthesis', str(root / 'parent'),
                '--output', str(root / 'continued'), '--model', 'judge',
                '--evidence-list', str(evidence_list)], root / 'continued')
            self.assertEqual(result, 1)
            for name in ('fork', 'create_panel', 'run_reviews', 'run_checks', 'synthesize'):
                calls[name].assert_not_called()

    def test_invalid_explicit_selection_fails_before_first_review(self):
        cases = (None, {}, [], ['checks/artifacts/result.json'] * 2, [123],
                 ['../secret.json'], ['inputs/paper.txt'], ['checks/artifacts/../result.json'],
                 ['checks/artifacts/chart.png'])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); evidence_list = root / 'selection.json'
            for selected in cases:
                with self.subTest(selected=selected):
                    evidence_list.write_text(json.dumps(selected), encoding='utf-8')
                    result, calls = self._patched_cli(['scinet', 'panel', 'run', '--bundle', 'bundle.json',
                        '--output', str(root / 'run'), '--model', 'a', '--model', 'b', '--script', 'checked.py',
                        '--synthesis-model', 'judge', '--evidence-list', str(evidence_list)], root / 'run')
                    self.assertEqual(result, 1)
                    for name in ('fork', 'create_panel', 'run_reviews', 'run_checks', 'synthesize'):
                        calls[name].assert_not_called()

    def test_full_run_forwards_valid_selection_without_expecting_files_before_computation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); run = root / 'run'; evidence_list = root / 'selection.json'
            selected = ['checks/artifacts/result.json']
            evidence_list.write_text(json.dumps(selected), encoding='utf-8')
            result, calls = self._patched_cli(['scinet', 'panel', 'run', '--bundle', 'bundle.json',
                '--output', str(run), '--model', 'a', '--model', 'b', '--script', 'checked.py',
                '--synthesis-model', 'judge', '--evidence-list', str(evidence_list)], run)
            self.assertEqual(result, 0)
            calls['run_reviews'].assert_called_once()
            calls['run_checks'].assert_called_once()
            calls['synthesize'].assert_called_once_with(run, model='judge', timeout=600,
                                                       evidence_paths=selected)


if __name__ == '__main__':
    unittest.main()
