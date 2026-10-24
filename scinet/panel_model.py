"""Isolated Codex transport and offline validation for independent panel reviews.

Isolation here controls supplied context and disables known tool surfaces. It is
not an attestation of model training independence or a general security sandbox.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from .evidence import digest, write_json


# These keys are supported by Codex CLI 0.163.0-alpha.11.2. Strict config makes
# unsupported settings an error instead of silently weakening the protocol.
REQUEST_CONFIG = {
    'suppress_unstable_features_warning': True,
    'model_reasoning_effort': 'medium',
    'project_doc_max_bytes': 0,
    'web_search': 'disabled',
    'features.view_image': False,
    'features.shell_tool': False,
    'features.apps': False,
    'features.plugins': False,
    'features.hooks': False,
    'features.multi_agent': False,
    'features.memories': False,
    'features.browser_use': False,
    'features.computer_use': False,
    'features.image_generation': False,
    'features.goals': False,
    'features.sleep_tool': False,
    'features.tool_suggest': False,
    'features.workspace_dependencies': False,
    'features.worktrees': False,
    'features.skip_host_skill_discovery': True,
}

_RECONNECT_DIAGNOSTIC = re.compile(
    r'Reconnecting\.\.\. ([1-9][0-9]*)/([1-9][0-9]*) '
    r'\(stream disconnected before completion: ([^\r\n]+)\)'
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result

    def constant(value):
        raise ValueError('Non-finite JSON number: ' + value)

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def _audit_raw(output_dir):
    """Re-read every event; tool starts count even when no completion exists."""
    errors = []
    audit = {'tool_calls_observed': False, 'usage': [], 'thread_id': None,
             'item_types': [], 'turn_completed_count': 0, 'transport_diagnostics': []}
    messages = []
    thread_started_count = 0
    turn_started_count = 0
    phase = 'awaiting_thread'
    try:
        lines = (output_dir / 'events.jsonl').read_text(encoding='utf-8').splitlines()
        for number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            event = _strict_json(line)
            if not isinstance(event, dict):
                raise ValueError(f'Event {number} is not an object')
            kind = event.get('type')
            if phase == 'completed':
                errors.append(f'Event after turn.completed at event {number}: {kind}')
            if kind in ('item.started', 'item.updated', 'item.completed'):
                if phase != 'in_turn':
                    errors.append(f'Item outside the single active turn at event {number}: {kind}')
                item = event.get('item')
                if not isinstance(item, dict):
                    raise ValueError(f'Event {number} has no item object')
                item_type = item.get('type')
                audit['item_types'].append(item_type)
                if item_type not in ('agent_message', 'reasoning'):
                    audit['tool_calls_observed'] = True
                    errors.append(f'Forbidden tool or unknown item at event {number}: {item_type}')
                elif kind == 'item.completed' and item_type == 'agent_message':
                    messages.append(item.get('text'))
            elif kind == 'thread.started':
                thread_started_count += 1
                if phase != 'awaiting_thread' or thread_started_count != 1:
                    errors.append(f'thread.started must be the first and only thread event: {number}')
                else:
                    phase = 'awaiting_turn'
                thread_id = event.get('thread_id')
                if not isinstance(thread_id, str) or not thread_id.strip():
                    errors.append(f'Invalid thread_id at event {number}: expected nonempty text')
                if thread_started_count == 1:
                    audit['thread_id'] = thread_id
            elif kind == 'turn.completed':
                audit['turn_completed_count'] += 1
                if phase != 'in_turn':
                    errors.append(f'turn.completed has no single active turn at event {number}')
                if not messages:
                    errors.append(f'turn.completed precedes a completed agent_message at event {number}')
                phase = 'completed'
                if isinstance(event.get('usage'), dict):
                    audit['usage'].append(event['usage'])
            elif kind == 'turn.started':
                turn_started_count += 1
                if phase != 'awaiting_turn' or turn_started_count != 1:
                    errors.append(f'turn.started must occur once immediately after thread.started: {number}')
                else:
                    phase = 'in_turn'
            elif kind == 'error':
                if phase != 'in_turn':
                    errors.append(f'Diagnostic outside the single active turn at event {number}')
                message = event.get('message')
                reconnect = (_RECONNECT_DIAGNOSTIC.fullmatch(message)
                             if isinstance(message, str) else None)
                if (reconnect and int(reconnect[1]) <= int(reconnect[2])
                        and reconnect[3].strip()):
                    # A CLI retry notice is not a completed response. Retain it
                    # verbatim and still require every normal completion check.
                    audit['transport_diagnostics'].append(event)
                else:
                    errors.append(f'Unknown or unsuccessful event {number}: {kind}')
            else:
                errors.append(f'Unknown or unsuccessful event {number}: {kind}')
        if thread_started_count != 1:
            errors.append('Expected exactly one thread.started event')
        if turn_started_count != 1:
            errors.append('Expected exactly one turn.started event')
        if audit['turn_completed_count'] != 1:
            errors.append('Expected exactly one turn.completed event')
        if not messages or not isinstance(messages[-1], str):
            errors.append('No final completed agent_message')
        else:
            message = _strict_json(messages[-1])
            response = _strict_json((output_dir / 'response.json').read_text(encoding='utf-8-sig'))
            if not isinstance(response, dict):
                errors.append('Response must be a JSON object')
            if message != response:
                errors.append('Final agent_message does not match response.json')
    except (OSError, ValueError, TypeError) as error:
        errors.append(str(error))
    return audit, errors


def validate_call(output_dir: Path, prompt_path: Path, schema_path: Path) -> list[str]:
    """Validate transport evidence without a CLI, model request or network access."""
    output_dir = Path(output_dir)
    errors = []
    try:
        call = _strict_json((output_dir / 'call.json').read_text(encoding='utf-8-sig'))
        if not isinstance(call, dict):
            raise ValueError('call.json must be an object')
        if call.get('status') != 'completed':
            errors.append('Model call is not completed')
        if call.get('exit_code') != 0:
            errors.append('Model call has no successful exit code')
        if not isinstance(call.get('model_requested'), str) or not call['model_requested'].strip():
            errors.append('Missing model_requested')
        if call.get('request_config') != REQUEST_CONFIG:
            errors.append('Recorded request_config does not match the isolation protocol')
        paths = {'prompt_sha256': Path(prompt_path), 'schema_sha256': Path(schema_path),
                 'response_sha256': output_dir / 'response.json',
                 'events_sha256': output_dir / 'events.jsonl',
                 'stderr_sha256': output_dir / 'stderr.log'}
        for field, path in paths.items():
            try:
                if call.get(field) != digest(path):
                    errors.append('Hash mismatch: ' + field)
            except OSError as error:
                errors.append(f'Missing evidence for {field}: {error}')
        audit, raw_errors = _audit_raw(output_dir)
        errors.extend(raw_errors)
        for field in ('tool_calls_observed', 'usage', 'thread_id', 'turn_completed_count', 'item_types'):
            if call.get(field) != audit[field]:
                errors.append('Raw events do not match call field: ' + field)
        # Earlier successful calls did not have this field; absence only means
        # an empty list when the raw event stream also has no retry notices.
        if call.get('transport_diagnostics', []) != audit['transport_diagnostics']:
            errors.append('Raw events do not match call field: transport_diagnostics')
        if call.get('tool_calls_observed') is not False:
            errors.append('Call does not establish absence of observed tool calls')
    except (OSError, ValueError, TypeError) as error:
        errors.append(str(error))
    return errors


def run_model(*, model: str, prompt_path: Path, schema_path: Path,
              output_dir: Path, timeout: int = 600) -> dict:
    """Make one fresh review call, retaining evidence even if it cannot be accepted."""
    if not isinstance(model, str) or not model.strip():
        raise ValueError('An explicit model is required')
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise ValueError('timeout must be a positive integer')
    prompt_path, schema_path = Path(prompt_path).resolve(), Path(schema_path).resolve()
    prompt = prompt_path.read_bytes()
    schema_bytes = schema_path.read_bytes()
    _strict_json(schema_bytes.decode('utf-8-sig'))
    output_dir = Path(output_dir).resolve()
    if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
        raise ValueError('output_dir must be absent or empty; existing evidence is never overwritten')
    output_dir.mkdir(parents=True, exist_ok=True)
    record = {
        'protocol_version': 1, 'engine': 'Codex CLI', 'model_requested': model.strip(),
        'model_resolved': None, 'backend_model_status': 'unknown',
        'model_resolution_note': 'Requested identifiers may be aliases. CLI events do not attest an immutable backend model version.',
        'request_config': dict(REQUEST_CONFIG), 'timeout_seconds': timeout,
        'cli_version': None, 'cli_executable_sha256': None, 'invocation': [],
        'prompt_sha256': hashlib.sha256(prompt).hexdigest(),
        'schema_sha256': hashlib.sha256(schema_bytes).hexdigest(),
        'started_at_utc': _now(), 'status': 'starting', 'exit_code': None,
        'tool_calls_observed': None, 'usage': [], 'fresh_call': False,
        'session_mode': 'fresh_ephemeral_no_resume',
        'isolation_limit': 'Fresh external empty cwd; known tools disabled by configuration and tool events rejected. Not a security sandbox or proof of absent backend instructions, training familiarity, or caching.',
    }
    write_json(output_dir / 'call.json', record)
    started = time.perf_counter()
    failure = None
    # Create raw streams before CLI discovery so failed attempts remain inspectable.
    with (output_dir / 'events.jsonl').open('wb') as stdout, \
            (output_dir / 'stderr.log').open('wb') as stderr:
        try:
            cli = os.environ.get('CODEX_CLI_PATH') or shutil.which('codex')
            if not cli:
                raise OSError('Authenticated Codex CLI not found')
            cli = str(Path(cli).resolve())
            record['cli_executable_sha256'] = digest(cli)
            version = subprocess.run([cli, '--version'], capture_output=True, timeout=10)
            if version.returncode:
                raise OSError('Could not read Codex CLI version')
            record['cli_version'] = version.stdout.decode('utf-8', errors='replace').strip()
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith('CODEX_') or key in
                   {'CODEX_HOME', 'CODEX_API_KEY', 'CODEX_CA_CERTIFICATE'}}
            record['removed_context_environment_names'] = sorted(set(os.environ) - set(env))
            # The default OS temporary location is outside the paper/review tree.
            with tempfile.TemporaryDirectory(prefix='scinet-panel-') as temporary:
                cwd = Path(temporary).resolve()
                project = Path(__file__).resolve().parent.parent
                if cwd.is_relative_to(project) or cwd.is_relative_to(output_dir.parent):
                    raise OSError('Temporary review directory must be outside the project and evidence tree')
                args = [cli, '--no-daemon', 'exec', '--ephemeral', '--ignore-user-config',
                        '--ignore-rules', '--strict-config', '--sandbox', 'read-only',
                        '--skip-git-repo-check', '--color', 'never', '--json',
                        '--model', model.strip()]
                for key, value in REQUEST_CONFIG.items():
                    args.extend(['-c', key + '=' + json.dumps(value, separators=(',', ':'))])
                args.extend(['--output-schema', str(schema_path), '-o',
                             str(output_dir / 'response.json'), '-'])
                record.update(invocation=args, cwd=str(cwd), status='running', fresh_call=True)
                write_json(output_dir / 'call.json', record)
                result = subprocess.run(args, input=prompt, stdout=stdout, stderr=stderr,
                                        cwd=cwd, env=env, timeout=timeout)
                record['exit_code'] = result.returncode
                record['status'] = 'cli_failed' if result.returncode else 'validating'
                if result.returncode:
                    failure = RuntimeError(f'Codex CLI exited with exit code {result.returncode}')
        except KeyboardInterrupt as error:
            record['status'], failure = 'interrupted', error
        except subprocess.TimeoutExpired as error:
            record['status'], failure = 'timeout', error
        except (OSError, ValueError) as error:
            record['status'], failure = 'launch_failed', error
    audit, errors = _audit_raw(output_dir)
    record.update(audit)
    record['validation_errors'] = errors
    if failure is None and errors:
        record['status'] = 'protocol_violation'
        failure = RuntimeError('; '.join(errors))
    if failure is None:
        # Inputs may have changed while the service was running; never relabel them.
        try:
            inputs_unchanged = (digest(prompt_path) == record['prompt_sha256'] and
                                digest(schema_path) == record['schema_sha256'])
        except OSError:
            inputs_unchanged = False
        if not inputs_unchanged:
            record['status'] = 'protocol_violation'
            failure = RuntimeError('Prompt or schema changed or disappeared during the call')
        else:
            record['status'] = 'completed'
    for name, field in (('response.json', 'response_sha256'), ('events.jsonl', 'events_sha256'),
                        ('stderr.log', 'stderr_sha256')):
        path = output_dir / name
        record[field] = digest(path) if path.is_file() else None
    record.update(finished_at_utc=_now(), elapsed_seconds=time.perf_counter() - started)
    if failure is not None:
        record['error'] = type(failure).__name__ + ': ' + str(failure)
    write_json(output_dir / 'call.json', record)
    if failure is not None:
        raise RuntimeError('Model review failed: ' + record['error']) from failure
    return record
