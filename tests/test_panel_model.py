"""Protocol tests use a fake CLI transport, never paid model calls."""
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scinet.evidence import digest, read_json, write_json


class PanelModelTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.find_spec('scinet.panel_model')
        self.assertIsNotNone(spec, 'Independent panel model runner is not implemented')
        self.runner = importlib.import_module('scinet.panel_model')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prompt = self.root / 'source-prompt.txt'
        self.schema = self.root / 'source-schema.json'
        self.prompt.write_text('Review the supplied paper independently. 中文。', encoding='utf-8')
        write_json(self.schema, {'type': 'object'})
        self.cli = self.root / 'fake-codex.exe'
        self.cli.write_bytes(b'not an executable; patched transport only')
        self.output = self.root / 'reviewer'
        self.response = {'summary': 'Protocol test response, not scientific evidence.'}
        self.cwd_seen = None
        self.env_seen = None
        self.invocation_seen = None
        self.events = [
            {'type': 'thread.started', 'thread_id': 'test-thread'},
            {'type': 'turn.started'},
            {'type': 'item.completed', 'item': {'id': 'answer', 'type': 'agent_message',
                                             'text': json.dumps(self.response)}},
            {'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 5}},
        ]

    def transport(self, args, **kwargs):
        if '--version' in args:
            return SimpleNamespace(returncode=0, stdout=b'codex-cli test\n', stderr=b'')
        self.invocation_seen = args
        self.cwd_seen = Path(kwargs['cwd'])
        self.env_seen = kwargs['env']
        self.assertEqual(list(self.cwd_seen.iterdir()), [])
        self.assertFalse(self.cwd_seen.is_relative_to(Path.cwd()))
        self.assertFalse(self.cwd_seen.is_relative_to(self.output))
        self.assertEqual(kwargs['input'], self.prompt.read_bytes())
        write_json(Path(args[args.index('-o') + 1]), self.response)
        for event in self.events:
            kwargs['stdout'].write((json.dumps(event) + '\n').encode())
        kwargs['stderr'].write(b'fake transport diagnostic\n')
        return SimpleNamespace(returncode=0)

    def invoke(self, transport=None, **overrides):
        params = dict(model='test-model', prompt_path=self.prompt,
                      schema_path=self.schema, output_dir=self.output, timeout=30)
        params.update(overrides)
        with patch.dict('os.environ', {'CODEX_CLI_PATH': str(self.cli),
                                     'CODEX_THREAD_ID': 'must-not-inherit'}), \
                patch.object(self.runner.subprocess, 'run', side_effect=transport or self.transport):
            return self.runner.run_model(**params)

    def invoke_expected_success(self):
        try:
            return self.invoke()
        except RuntimeError as error:
            self.fail('Expected a completed call: ' + str(error))

    def test_success_preserves_raw_records_and_uses_external_empty_context(self):
        result = self.invoke_expected_success()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['model_requested'], 'test-model')
        self.assertIsNone(result['model_resolved'])
        self.assertEqual(result['backend_model_status'], 'unknown')
        self.assertEqual(result['cli_version'], 'codex-cli test')
        self.assertEqual(result['cli_executable_sha256'], digest(self.cli))
        self.assertEqual(result['prompt_sha256'], digest(self.prompt))
        self.assertEqual(result['schema_sha256'], digest(self.schema))
        self.assertFalse(result['tool_calls_observed'])
        self.assertEqual(result['usage'], [{'input_tokens': 10, 'output_tokens': 5}])
        self.assertEqual(result, read_json(self.output / 'call.json'))
        self.assertEqual(read_json(self.output / 'response.json'), self.response)
        self.assertEqual((self.output / 'stderr.log').read_bytes(), b'fake transport diagnostic\n')
        self.assertFalse(self.cwd_seen.exists())
        self.assertNotIn('CODEX_THREAD_ID', self.env_seen)
        for flag in ('--ephemeral', '--ignore-user-config', '--ignore-rules', '--strict-config'):
            self.assertIn(flag, self.invocation_seen)
        for option in ('features.shell_tool=false', 'web_search="disabled"',
                       'suppress_unstable_features_warning=true',
                       'project_doc_max_bytes=0', 'features.view_image=false', 'features.apps=false',
                       'features.plugins=false', 'features.hooks=false',
                       'features.multi_agent=false', 'features.memories=false'):
            self.assertIn(option, self.invocation_seen)

    def test_existing_evidence_is_never_overwritten(self):
        self.output.mkdir()
        existing = self.output / 'call.json'
        existing.write_text('preserve', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.invoke()
        self.assertEqual(existing.read_text(), 'preserve')

    def test_empty_existing_output_is_allowed(self):
        self.output.mkdir()
        self.assertEqual(self.invoke()['status'], 'completed')

    def test_tool_started_without_completion_is_rejected_and_preserved(self):
        self.events.insert(2, {'type': 'item.started', 'item': {
            'id': 'tool', 'type': 'command_execution', 'command': 'forbidden'}})
        with self.assertRaisesRegex(RuntimeError, 'tool'):
            self.invoke()
        call = read_json(self.output / 'call.json')
        self.assertTrue(call['tool_calls_observed'])
        self.assertEqual(call['status'], 'protocol_violation')
        self.assertIn(b'forbidden', (self.output / 'events.jsonl').read_bytes())

    def test_unknown_item_or_event_fails_closed(self):
        for event in ({'type': 'item.completed', 'item': {'type': 'new_tool_kind'}},
                      {'type': 'new_unrecognized_event'}):
            with self.subTest(event=event):
                self.output = self.root / ('unknown-' + str(len(list(self.root.iterdir()))))
                self.events.insert(2, event)
                with self.assertRaises(RuntimeError):
                    self.invoke()
                self.assertEqual(read_json(self.output / 'call.json')['status'], 'protocol_violation')
                self.events.pop(2)

    def test_completed_response_preserves_recognized_reconnection_diagnostics(self):
        diagnostics = [
            {'type': 'error', 'message': 'Reconnecting... 1/5 (stream disconnected before completion: connection reset)'},
            {'type': 'error', 'message': 'Reconnecting... 2/5 (stream disconnected before completion: IO error: peer closed connection without sending TLS close_notify: https://docs.rs/rustls/latest/rustls/manual/_03_howto/index.html#unexpected-eof)'},
        ]
        self.events[2:2] = diagnostics
        result = self.invoke_expected_success()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['transport_diagnostics'], diagnostics)
        self.assertEqual(result['turn_completed_count'], 1)
        self.assertFalse(result['tool_calls_observed'])
        self.assertEqual(self.runner.validate_call(self.output, self.prompt, self.schema), [])
        saved_events = [json.loads(line) for line in (self.output / 'events.jsonl').read_text().splitlines()]
        self.assertEqual(saved_events, self.events)

    def test_reconnection_diagnostic_does_not_override_other_protocol_failures(self):
        diagnostic = {'type': 'error', 'message': 'Reconnecting... 2/5 (stream disconnected before completion: connection reset)'}
        baseline = list(self.events)
        cases = {
            'unfinished': [*baseline[:-1], diagnostic],
            'turn_failed': [*baseline[:2], diagnostic, {'type': 'turn.failed', 'error': {'message': 'still failed'}}, *baseline[2:]],
            'unknown_error': [*baseline[:2], diagnostic, {'type': 'error', 'message': 'Authentication failed'}, *baseline[2:]],
            'second_thread': [*baseline[:2], diagnostic, baseline[0], *baseline[2:]],
            'tool_start': [*baseline[:2], diagnostic, {'type': 'item.started', 'item': {'type': 'command_execution'}}, *baseline[2:]],
        }
        for name, events in cases.items():
            with self.subTest(name=name):
                self.events, self.output = events, self.root / name
                with self.assertRaises(RuntimeError):
                    self.invoke()
                call = read_json(self.output / 'call.json')
                self.assertEqual(call['status'], 'protocol_violation')
                self.assertEqual(call.get('transport_diagnostics'), [diagnostic])

    def test_other_errors_and_reconnection_lookalikes_fail_closed(self):
        baseline = list(self.events)
        messages = [
            'Under-development features enabled: skip_host_skill_discovery',
            'Authentication failed',
            'Reconnecting... 2/5 (service rejected request)',
            'Reconnecting... 2/5 (stream disconnected before completion: )',
            'Reconnecting... 0/5 (stream disconnected before completion: failure)',
            'Reconnecting... 6/5 (stream disconnected before completion: failure)',
            'Reconnecting... 2/5 (stream disconnected before completion: failure) unexpected',
            'prefix Reconnecting... 2/5 (stream disconnected before completion: failure)',
            'Reconnecting... 2/5 (stream disconnected before completion: failure)\nextra error',
        ]
        for index, message in enumerate(messages):
            with self.subTest(message=message):
                self.output = self.root / f'error-{index}'
                self.events = [*baseline[:2], {'type': 'error', 'message': message}, *baseline[2:]]
                with self.assertRaises(RuntimeError):
                    self.invoke()

    def test_validate_call_checks_recorded_reconnection_diagnostics(self):
        diagnostic = {'type': 'error', 'message': 'Reconnecting... 2/5 (stream disconnected before completion: connection reset)'}
        self.events.insert(2, diagnostic)
        self.invoke_expected_success()
        original = read_json(self.output / 'call.json')
        for recorded in ([], [dict(diagnostic, message='changed')], None):
            with self.subTest(recorded=recorded):
                call = dict(original)
                if recorded is None:
                    call.pop('transport_diagnostics')
                else:
                    call['transport_diagnostics'] = recorded
                write_json(self.output / 'call.json', call)
                errors = self.runner.validate_call(self.output, self.prompt, self.schema)
                self.assertTrue(any('transport_diagnostics' in error for error in errors), errors)

    def test_validate_call_accepts_legacy_absent_diagnostics_only_when_raw_events_have_none(self):
        self.invoke()
        call = read_json(self.output / 'call.json')
        call.pop('transport_diagnostics', None)
        write_json(self.output / 'call.json', call)
        self.assertEqual(self.runner.validate_call(self.output, self.prompt, self.schema), [])

    def test_validate_call_never_relabels_historical_failed_status(self):
        self.events.insert(2, {'type': 'error', 'message': 'Reconnecting... 2/5 (stream disconnected before completion: connection reset)'})
        self.invoke_expected_success()
        call = read_json(self.output / 'call.json')
        call['status'] = 'protocol_violation'
        call.pop('transport_diagnostics', None)
        write_json(self.output / 'call.json', call)
        original_bytes = (self.output / 'call.json').read_bytes()
        errors = self.runner.validate_call(self.output, self.prompt, self.schema)
        self.assertIn('Model call is not completed', errors)
        self.assertEqual((self.output / 'call.json').read_bytes(), original_bytes)

    def test_missing_turn_completion_is_not_success(self):
        self.events.pop()
        with self.assertRaisesRegex(RuntimeError, 'turn.completed'):
            self.invoke()

    def test_only_one_complete_ordered_turn_is_accepted(self):
        thread, start, answer, completed = self.events
        diagnostic = {'type': 'error', 'message': 'Reconnecting... 1/5 (stream disconnected before completion: connection reset)'}
        cases = {
            'missing_turn_start': [thread, answer, completed],
            'duplicate_turn_start': [thread, start, start, answer, completed],
            'turn_before_thread': [start, thread, answer, completed],
            'answer_before_thread': [answer, thread, start, completed],
            'answer_before_turn': [thread, answer, start, completed],
            'completion_before_answer': [thread, start, completed, answer],
            'reconnect_before_thread': [diagnostic, thread, start, answer, completed],
            'reconnect_before_turn': [thread, diagnostic, start, answer, completed],
            'reconnect_after_completion': [thread, start, answer, completed, diagnostic],
            'second_turn_after_completion': [thread, start, answer, completed, start],
        }
        for name, events in cases.items():
            with self.subTest(name=name):
                self.events, self.output = events, self.root / name
                with self.assertRaises(RuntimeError):
                    self.invoke()
                call = read_json(self.output / 'call.json')
                self.assertEqual(call['status'], 'protocol_violation')
                saved = [json.loads(line) for line in (self.output / 'events.jsonl').read_text().splitlines()]
                self.assertEqual(saved, events)

    def test_offline_validation_rechecks_turn_order_without_rewriting_records(self):
        self.invoke_expected_success()
        events_path = self.output / 'events.jsonl'
        events = [event for event in self.events if event['type'] != 'turn.started']
        events_path.write_text('\n'.join(json.dumps(event) for event in events) + '\n', encoding='utf-8')
        call = read_json(self.output / 'call.json')
        call['events_sha256'] = digest(events_path)
        write_json(self.output / 'call.json', call)
        original = (self.output / 'call.json').read_bytes()
        errors = self.runner.validate_call(self.output, self.prompt, self.schema)
        self.assertTrue(any('turn' in error for error in errors), errors)
        self.assertEqual((self.output / 'call.json').read_bytes(), original)

    def test_exactly_one_nonempty_thread_identity_is_required(self):
        baseline = list(self.events)
        cases = {
            'missing': baseline[1:],
            'duplicate_same': [baseline[0], *baseline],
            'duplicate_different': [{'type': 'thread.started', 'thread_id': 'other-thread'}, *baseline],
            'empty': [{'type': 'thread.started', 'thread_id': ''}, *baseline[1:]],
            'whitespace': [{'type': 'thread.started', 'thread_id': '  '}, *baseline[1:]],
            'not_string': [{'type': 'thread.started', 'thread_id': 123}, *baseline[1:]],
        }
        for name, events in cases.items():
            with self.subTest(name=name):
                self.events = events
                self.output = self.root / name
                with self.assertRaisesRegex(RuntimeError, 'thread'):
                    self.invoke()
                self.assertEqual(read_json(self.output / 'call.json')['status'], 'protocol_violation')

    def test_last_message_must_equal_response_file(self):
        self.events[2]['item']['text'] = json.dumps({'summary': 'different'})
        with self.assertRaisesRegex(RuntimeError, 'match'):
            self.invoke()

    def test_duplicate_json_keys_are_rejected(self):
        self.events[2]['item']['text'] = '{"summary":"first","summary":"last"}'
        self.response = {'summary': 'last'}
        with self.assertRaisesRegex(RuntimeError, 'Duplicate'):
            self.invoke()

    def test_model_text_cannot_attest_backend_identity(self):
        self.response['model_resolved'] = 'a-model-claimed-in-generated-text'
        self.events[2]['item']['text'] = json.dumps(self.response)
        self.assertIsNone(self.invoke()['model_resolved'])

    def test_transport_does_not_claim_prompt_contains_no_reviews(self):
        result = self.invoke()
        self.assertNotIn('other_reviews_supplied', result)
        self.assertNotIn('prior_conversation_supplied', result)
        self.assertEqual(result['session_mode'], 'fresh_ephemeral_no_resume')

    def test_timeout_interruption_and_launch_failure_keep_partial_evidence(self):
        for error, status in ((subprocess.TimeoutExpired('cli', 30), 'timeout'),
                              (KeyboardInterrupt(), 'interrupted'),
                              (OSError('launch problem'), 'launch_failed')):
            with self.subTest(status=status):
                self.output = self.root / status
                def fail(args, **kwargs):
                    if '--version' in args:
                        return SimpleNamespace(returncode=0, stdout=b'codex-cli test', stderr=b'')
                    kwargs['stdout'].write(b'{"type":"turn.started"}\n')
                    kwargs['stderr'].write(b'partial failure')
                    raise error
                with self.assertRaises(RuntimeError):
                    self.invoke(fail)
                call = read_json(self.output / 'call.json')
                self.assertEqual(call['status'], status)
                self.assertIn('finished_at_utc', call)
                self.assertTrue((self.output / 'events.jsonl').read_bytes())
                self.assertEqual((self.output / 'stderr.log').read_bytes(), b'partial failure')

    def test_nonzero_exit_never_accepts_well_formed_response(self):
        def fail(args, **kwargs):
            result = self.transport(args, **kwargs)
            if '--version' not in args:
                result.returncode = 1
            return result
        with self.assertRaisesRegex(RuntimeError, 'exit'):
            self.invoke(fail)
        self.assertEqual(read_json(self.output / 'call.json')['status'], 'cli_failed')

    def test_missing_cli_records_failure_without_fabricating_response(self):
        with patch.dict('os.environ', {}, clear=True), patch('shutil.which', return_value=None):
            with self.assertRaises(RuntimeError):
                self.runner.run_model(model='test-model', prompt_path=self.prompt,
                                      schema_path=self.schema, output_dir=self.output)
        self.assertEqual(read_json(self.output / 'call.json')['status'], 'launch_failed')
        self.assertFalse((self.output / 'response.json').exists())

    def test_validate_call_checks_hashes_and_input_identity_offline(self):
        self.invoke()
        self.assertEqual(self.runner.validate_call(self.output, self.prompt, self.schema), [])
        self.prompt.write_text('changed source', encoding='utf-8')
        errors = self.runner.validate_call(self.output, self.prompt, self.schema)
        self.assertTrue(any('prompt' in error for error in errors))

    def test_validate_call_rechecks_raw_events_even_if_hash_was_replaced(self):
        self.invoke()
        events_path = self.output / 'events.jsonl'
        with events_path.open('ab') as stream:
            stream.write(b'{"type":"item.started","item":{"type":"mcp_tool_call"}}\n')
        call = read_json(self.output / 'call.json')
        call['events_sha256'] = digest(events_path)
        write_json(self.output / 'call.json', call)
        errors = self.runner.validate_call(self.output, self.prompt, self.schema)
        self.assertTrue(any('tool' in error for error in errors))

    def test_input_removed_during_call_still_leaves_failure_record(self):
        def remove_input(args, **kwargs):
            result = self.transport(args, **kwargs)
            if '--version' not in args:
                self.schema.unlink()
            return result
        with self.assertRaises(RuntimeError):
            self.invoke(remove_input)
        call = read_json(self.output / 'call.json')
        self.assertEqual(call['status'], 'protocol_violation')
        self.assertIn('finished_at_utc', call)

    def test_validate_call_requires_recorded_isolation_configuration(self):
        self.invoke()
        call = read_json(self.output / 'call.json')
        call['request_config']['features.shell_tool'] = True
        write_json(self.output / 'call.json', call)
        self.assertTrue(self.runner.validate_call(self.output, self.prompt, self.schema))


if __name__ == '__main__':
    unittest.main()
