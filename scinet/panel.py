"""Review first, freeze every member, then compute and compare evidence."""
import importlib.metadata
from datetime import datetime
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time

from .evidence import digest, read_json, write_json
from .panel_record import (append_event, artifact_path, commit, inventory, load_events,
                           now, verify_commitment, verify_events)
from .panel_schema import (REVIEW_SCHEMA, SYNTHESIS_SCHEMA, REVIEW_INSTRUCTIONS,
                           SYNTHESIS_INSTRUCTIONS, validate_review, validate_synthesis)


MAX_PROMPT_BYTES = 2_000_000
MAX_PROMPT_CHARS = 1_048_576
TEXT_SUFFIXES = {'.json', '.txt', '.csv', '.tsv', '.log', '.diff', '.py'}
ROLES = {'paper', 'code', 'data', 'readme', 'license'}


def validate_call(output_dir, prompt_path, schema_path):
    from .panel_model import validate_call as validate
    return validate(output_dir, prompt_path, schema_path)


def environment():
    packages = {}
    for name in ('numpy', 'scipy', 'pandas', 'matplotlib', 'pypdf', 'mpmath'):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {'python': sys.version, 'platform': platform.platform(), 'packages': packages}


def _prompt(prefix, paper, materials):
    text = prefix + '\nEvery string field must contain text; use an explicit unknown or not-applicable explanation where needed.\n'
    text += json.dumps({'paper': paper, 'materials': materials}, ensure_ascii=False, indent=2)
    if len(text) > MAX_PROMPT_CHARS:
        raise ValueError('Model input exceeds the CLI character limit; select explicit evidence files, never silently truncate')
    if len(text.encode('utf-8')) > MAX_PROMPT_BYTES:
        raise ValueError('Model input exceeds 2 MB; select an explicit smaller packet, never silently truncate')
    return text


def _snapshot(root, paths):
    return {name: {'sha256': digest(artifact_path(root, name)), 'bytes': artifact_path(root, name).stat().st_size}
            for name in sorted(paths)}


def _check_snapshot(root, snapshot):
    errors = []
    for name, expected in snapshot.items():
        path = artifact_path(root, name)
        if not path.is_file() or digest(path) != expected['sha256'] or path.stat().st_size != expected['bytes']:
            errors.append(f'Frozen artifact changed or missing: {name}')
    return errors


def create_panel(bundle_path, output, models):
    bundle_path = Path(bundle_path).expanduser().resolve(); output = Path(output).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f'Preserve existing evidence; use a new run directory: {output}')
    if (not 2 <= len(models) <= 8 or len(set(models)) != len(models)
            or any(not isinstance(m, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,120}', m) for m in models)):
        raise ValueError('Use 2 to 8 distinct explicit model identifiers')
    bundle = read_json(bundle_path)
    paper = {key: bundle['paper'][key] for key in ('title', 'doi')}
    if not all(isinstance(value, str) and value.strip() for value in paper.values()):
        raise ValueError('Paper title and DOI/source identifier are required')
    files, materials, copies, seen = [], [], [], set()
    for entry in bundle['files']:
        name = entry['path']; source = artifact_path(bundle_path.parent, name)
        if name in seen or name.casefold() in {n.casefold() for n in seen}:
            raise ValueError(f'Duplicate source path: {name}')
        seen.add(name)
        if (entry['role'] not in ROLES or type(entry['include_in_review']) is not bool
                or not isinstance(entry['source_url'], str) or not entry['source_url'].strip()):
            raise ValueError(f'Invalid source metadata: {name}')
        if not source.is_file() or digest(source) != entry['sha256']:
            raise ValueError(f'Source hash mismatch: {name}')
        raw = source.read_bytes(); logical = 'inputs/' + name
        record = {key: entry[key] for key in ('role', 'source_url', 'include_in_review', 'sha256')}
        record.update(path=logical, bytes=len(raw))
        files.append(record); copies.append((logical, raw))
        if record['include_in_review']:
            materials.append({**record, 'content': raw.decode('utf-8-sig')})
    if not any(f['role'] == 'paper' and f['include_in_review'] for f in files):
        raise ValueError('At least one model-visible paper text is required')
    prompt = _prompt(REVIEW_INSTRUCTIONS, paper, materials)
    output.mkdir(parents=True)
    for name, raw in copies:
        target = artifact_path(output, name); target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    shutil.copy2(bundle_path, output / 'source_inventory_original.json')
    write_json(output / 'packet.json', {'format': 'scinet.paper-packet.v1', 'paper': paper, 'files': files})
    (output / 'prompt.txt').write_text(prompt, encoding='utf-8')
    write_json(output / 'schema.json', REVIEW_SCHEMA)
    reviewers = [{'id': f'r{i + 1}', 'model': model, 'provider': 'Codex CLI'} for i, model in enumerate(models)]
    protocol = {'format': 'scinet.panel.v1', 'created_at_utc': now(), 'paper': paper,
        'reviewers': reviewers, 'review_mode': 'issue-uncued, isolated contexts, identical source packet',
        'sequence': ['packet_frozen', 'reviews_frozen', 'checks_started', 'checks_completed', 'synthesis_completed'],
        'selection_disclosure': bundle.get('selection_disclosure', 'Operator did not supply a selection disclosure.'),
        'independence_limit': 'Distinct requested models and isolated sessions do not establish independent training, providers or errors.',
        'security_limit': 'Known CLI tools are disabled and tool events rejected; this is not a proof of hidden provider context isolation.',
        'input_limit': 'Only explicitly selected UTF-8 files are visible to reviewers; binary files are archived but not rendered to them.',
        'environment': environment()}
    write_json(output / 'protocol.json', protocol)
    implementation = output / 'implementation'; implementation.mkdir()
    for path in Path(__file__).parent.glob('*.py'):
        shutil.copy2(path, implementation / path.name)
    frozen_paths = list(inventory(output))
    write_json(output / 'input_freeze.json', {'frozen_at_utc': now(), 'files': _snapshot(output, frozen_paths)})
    write_json(output / 'panel.json', {'paper': paper, 'state': 'prepared', 'reviewers': reviewers,
        'created_at_utc': protocol['created_at_utc'],
        'limitations': [protocol['independence_limit'], protocol['input_limit'],
                        protocol['selection_disclosure'], 'No human domain-expert validation; no signature, blockchain or trusted timestamp.']})
    append_event(output, 'packet_frozen', {'input_freeze_sha256': digest(output / 'input_freeze.json')})
    commit(output)
    return output


def _state(run, state, **fields):
    meta = read_json(run / 'panel.json'); meta.update(state=state, **fields)
    write_json(run / 'panel.json', meta)


def _require(run, state):
    errors = verify_panel(run)
    if errors:
        raise ValueError('; '.join(errors))
    if read_json(run / 'panel.json')['state'] != state:
        raise ValueError(f'Expected panel state {state}; create a new run to repeat a completed or failed phase')


def run_reviews(run, *, runner=None, timeout=600):
    run = Path(run).resolve(); _require(run, 'prepared')
    if runner is None:
        from .panel_model import run_model
        runner = run_model
    meta = read_json(run / 'panel.json'); _state(run, 'reviewing')
    threads = set()
    try:
        for reviewer in meta['reviewers']:
            member = reviewer['id']; destination = run / 'reviews' / member
            destination.parent.mkdir(exist_ok=True)
            append_event(run, 'review_started', {'reviewer_id': member, 'model': reviewer['model'],
                                                'prompt_sha256': digest(run / 'prompt.txt')})
            runner(model=reviewer['model'], prompt_path=run / 'prompt.txt', schema_path=run / 'schema.json',
                   output_dir=destination, timeout=timeout)
            errors = validate_call(destination, run / 'prompt.txt', run / 'schema.json')
            if errors:
                raise ValueError('; '.join(errors))
            call = read_json(destination / 'call.json')
            if call['model_requested'] != reviewer['model']:
                raise ValueError('Recorded model differs from the requested panel member')
            thread = call.get('thread_id')
            if not isinstance(thread, str) or not thread or thread in threads:
                raise ValueError('Every reviewer must have a distinct recorded session')
            threads.add(thread)
            validate_review(read_json(destination / 'response.json'), read_json(run / 'packet.json'))
            errors = _check_snapshot(run, read_json(run / 'input_freeze.json')['files'])
            if errors:
                raise ValueError('; '.join(errors))
            append_event(run, 'review_completed', {'reviewer_id': member, 'response_sha256': digest(destination / 'response.json')})
        reviewers = {r['id']: {'model': r['model'], 'response_sha256': digest(run / 'reviews' / r['id'] / 'response.json')}
                     for r in meta['reviewers']}
        paths = ['reviews/' + p for p in inventory(run / 'reviews')]
        write_json(run / 'reviews_freeze.json', {'frozen_at_utc': now(), 'reviewers': reviewers,
            'input_freeze_sha256': digest(run / 'input_freeze.json'), 'files': _snapshot(run, paths)})
        append_event(run, 'reviews_frozen', {'reviews_freeze_sha256': digest(run / 'reviews_freeze.json')})
        _state(run, 'reviews_frozen')
    except BaseException as error:
        _state(run, 'review_failed', error=f'{type(error).__name__}: {error}')
        append_event(run, 'review_failed', {'error': f'{type(error).__name__}: {error}'})
        raise
    finally:
        commit(run)


def run_checks(run, script, *, timeout=300):
    run = Path(run).resolve(); _require(run, 'reviews_frozen')
    script = Path(script).expanduser().resolve()
    if not script.is_file() or script.suffix != '.py':
        raise ValueError('Choose an inspected local Python reproduction script')
    checks = run / 'checks'; checks.mkdir()
    runner_dir = checks / 'runner'; runner_dir.mkdir()
    saved = runner_dir / 'recompute.py'; shutil.copy2(script, saved)
    args = [sys.executable, '-B', str(saved), str(run / 'inputs'), str(checks / 'artifacts')]
    record = {'status': 'started', 'started_at_utc': now(), 'command': args,
        'script_sha256': digest(saved), 'reviews_freeze_sha256': digest(run / 'reviews_freeze.json'),
        'timeout_seconds': timeout, 'environment': environment(),
        'scope': 'Operator-selected trusted local script; no model-generated command execution; not a security sandbox.'}
    _state(run, 'checking'); append_event(run, 'checks_started', {'script_sha256': record['script_sha256'],
                                                               'reviews_freeze_sha256': record['reviews_freeze_sha256']})
    write_json(checks / 'execution.json', record); started = time.monotonic()
    try:
        with (checks / 'stdout.log').open('wb') as stdout, (checks / 'stderr.log').open('wb') as stderr:
            result = subprocess.run(args, cwd=checks, stdout=stdout, stderr=stderr, timeout=timeout)
        record['exit_code'] = result.returncode
        if result.returncode:
            raise RuntimeError(f'Reproduction exited {result.returncode}; inspect checks/stderr.log')
        if not (checks / 'artifacts').is_dir() or not inventory(checks / 'artifacts'):
            raise ValueError('Reproduction returned no evidence artifacts')
        errors = _check_snapshot(run, read_json(run / 'input_freeze.json')['files'])
        errors += _check_snapshot(run, read_json(run / 'reviews_freeze.json')['files'])
        if errors:
            raise ValueError('; '.join(errors))
        record['status'] = 'completed'; _state(run, 'checks_completed')
    except BaseException as error:
        record.update(status='failed', error=f'{type(error).__name__}: {error}')
        _state(run, 'checks_failed', error=record['error'])
        raise
    finally:
        record.update(finished_at_utc=now(), elapsed_seconds=time.monotonic() - started)
        write_json(checks / 'execution.json', record)
        if record['status'] == 'completed':
            paths = ['checks/' + p for p in inventory(checks)]
            write_json(run / 'checks_freeze.json', {'frozen_at_utc': now(), 'files': _snapshot(run, paths)})
        evidence = {'execution_sha256': digest(checks / 'execution.json')}
        if record['status'] == 'completed':
            evidence['checks_freeze_sha256'] = digest(run / 'checks_freeze.json')
        append_event(run, 'checks_completed' if record['status'] == 'completed' else 'checks_failed', evidence)
        commit(run)


def synthesize(run, *, model, runner=None, timeout=600, evidence_paths=None):
    run = Path(run).resolve(); _require(run, 'checks_completed')
    if not isinstance(model, str) or not model.strip():
        raise ValueError('Synthesis requires an explicit model')
    if runner is None:
        from .panel_model import run_model
        runner = run_model
    packet = read_json(run / 'packet.json')
    paths = [f['path'] for f in packet['files'] if f['include_in_review']]
    paths += ['reviews/' + r['id'] + '/response.json' for r in read_json(run / 'panel.json')['reviewers']]
    paths += ['checks/execution.json']
    artifacts = {'checks/artifacts/' + p: entry for p, entry in inventory(run / 'checks/artifacts').items()}
    readable = {p for p in artifacts if Path(p).suffix.lower() in TEXT_SUFFIXES}
    if evidence_paths is None:
        selected = sorted(readable)
    else:
        if (not isinstance(evidence_paths, list) or not evidence_paths
                or any(not isinstance(p, str) for p in evidence_paths)
                or len(set(evidence_paths)) != len(evidence_paths) or not set(evidence_paths) <= readable):
            raise ValueError('Evidence list must contain unique existing text paths under checks/artifacts/')
        selected = list(evidence_paths)
    paths += selected
    selection = {'mode': 'all_readable_artifacts' if evidence_paths is None else 'explicit_selection',
        'included': {p: artifacts[p] for p in selected},
        'excluded': {p: entry for p, entry in artifacts.items() if p not in selected},
        'scope': 'Excluded artifacts remain unchanged in the evidence bundle but their contents are not supplied to this synthesis.'}
    materials = [{'path': name, 'sha256': digest(artifact_path(run, name)),
                  'content': artifact_path(run, name).read_text(encoding='utf-8-sig')} for name in paths]
    prefix = SYNTHESIS_INSTRUCTIONS + '\nComputation evidence selection:\n' + json.dumps(selection, ensure_ascii=False) + '\n'
    prompt = _prompt(prefix, packet['paper'], materials)
    (run / 'synthesis_prompt.txt').write_text(prompt, encoding='utf-8')
    write_json(run / 'synthesis_schema.json', SYNTHESIS_SCHEMA)
    write_json(run / 'synthesis_selection.json', selection)
    write_json(run / 'synthesis_inputs.json', {'files': _snapshot(run, paths), 'model_requested': model})
    _state(run, 'synthesizing'); append_event(run, 'synthesis_started', {'model': model,
        'prompt_sha256': digest(run / 'synthesis_prompt.txt'), 'selection_sha256': digest(run / 'synthesis_selection.json')})
    try:
        runner(model=model, prompt_path=run / 'synthesis_prompt.txt', schema_path=run / 'synthesis_schema.json',
               output_dir=run / 'synthesis', timeout=timeout)
        errors = validate_call(run / 'synthesis', run / 'synthesis_prompt.txt', run / 'synthesis_schema.json')
        if errors:
            raise ValueError('; '.join(errors))
        call = read_json(run / 'synthesis/call.json')
        if call['model_requested'] != model:
            raise ValueError('Synthesis model does not match request')
        if call.get('thread_id') in {read_json(run / 'reviews' / r['id'] / 'call.json')['thread_id']
                                     for r in read_json(run / 'panel.json')['reviewers']}:
            raise ValueError('Synthesis must use a fresh session')
        validate_synthesis(read_json(run / 'synthesis/response.json'), run, set(paths))
        errors = _check_snapshot(run, read_json(run / 'synthesis_inputs.json')['files'])
        if errors:
            raise ValueError('; '.join(errors))
        append_event(run, 'synthesis_completed', {'response_sha256': digest(run / 'synthesis/response.json')})
        _state(run, 'complete')
    except BaseException as error:
        _state(run, 'synthesis_failed', error=f'{type(error).__name__}: {error}')
        append_event(run, 'synthesis_failed', {'error': f'{type(error).__name__}: {error}'})
        raise
    finally:
        commit(run)


def verify_panel(run, *, expected_root=None):
    run = Path(run); errors = verify_commitment(run, expected_root=expected_root) + verify_events(run)
    from .panel_resume import verify_continuation
    errors += verify_continuation(run)
    try:
        meta = read_json(run / 'panel.json'); protocol = read_json(run / 'protocol.json')
        if meta['reviewers'] != protocol['reviewers'] or meta['paper'] != protocol['paper']:
            errors.append('Panel identity differs from frozen protocol')
        errors += _check_snapshot(run, read_json(run / 'input_freeze.json')['files'])
        events = load_events(run); event_names = [e['event'] for e in events]
        if not events or events[0]['data']['input_freeze_sha256'] != digest(run / 'input_freeze.json'):
            errors.append('Input freeze does not match initial event')
        freeze_path = run / 'reviews_freeze.json'
        needs_freeze = meta['state'] in {'reviews_frozen', 'checking', 'checks_completed', 'checks_failed', 'synthesizing', 'complete', 'synthesis_failed'}
        if needs_freeze and not freeze_path.exists():
            errors.append('Missing completed review freeze')
        if freeze_path.exists():
            frozen = read_json(freeze_path)
            if set(frozen['reviewers']) != {r['id'] for r in protocol['reviewers']}:
                errors.append('Review freeze omits a required member')
            if frozen['input_freeze_sha256'] != digest(run / 'input_freeze.json'):
                errors.append('Review freeze refers to different inputs')
            errors += _check_snapshot(run, frozen['files'])
            threads = set()
            for reviewer in protocol['reviewers']:
                member = run / 'reviews' / reviewer['id']
                errors += validate_call(member, run / 'prompt.txt', run / 'schema.json')
                call = read_json(member / 'call.json')
                if call['model_requested'] != reviewer['model']:
                    errors.append('Reviewer model mismatch')
                thread = call.get('thread_id')
                if not isinstance(thread, str) or not thread or thread in threads:
                    errors.append('Reviewers do not have distinct recorded sessions')
                threads.add(thread)
                validate_review(read_json(member / 'response.json'), read_json(run / 'packet.json'))
                if frozen['reviewers'][reviewer['id']]['response_sha256'] != digest(member / 'response.json'):
                    errors.append('Original reviewer response changed')
            matching = [e for e in events if e['event'] == 'reviews_frozen']
            if len(matching) != 1 or matching[0]['data']['reviews_freeze_sha256'] != digest(freeze_path):
                errors.append('Review freeze event mismatch')
            for reviewer in protocol['reviewers']:
                member = reviewer['id']
                starts = [e for e in events if e['event'] == 'review_started' and e['data'].get('reviewer_id') == member]
                ends = [e for e in events if e['event'] == 'review_completed' and e['data'].get('reviewer_id') == member]
                if len(starts) != 1 or len(ends) != 1:
                    errors.append('Missing or duplicated review lifecycle event: ' + member)
                    continue
                if (starts[0]['data']['model'] != reviewer['model']
                        or starts[0]['data']['prompt_sha256'] != digest(run / 'prompt.txt')
                        or ends[0]['data']['response_sha256'] != digest(run / 'reviews' / member / 'response.json')):
                    errors.append('Review event does not match frozen member: ' + member)
                if matching and not starts[0]['sequence'] < ends[0]['sequence'] < matching[0]['sequence']:
                    errors.append('Review lifecycle violates freeze barrier: ' + member)
                call = read_json(run / 'reviews' / member / 'call.json')
                input_time = datetime.fromisoformat(read_json(run / 'input_freeze.json')['frozen_at_utc'])
                if not (input_time <= datetime.fromisoformat(call['started_at_utc'])
                        <= datetime.fromisoformat(call['finished_at_utc']) <= datetime.fromisoformat(frozen['frozen_at_utc'])):
                    errors.append('Reviewer call timestamps violate input/review freeze ordering: ' + member)
        if (run / 'checks').exists():
            if not freeze_path.exists() or 'reviews_frozen' not in event_names or 'checks_started' not in event_names:
                errors.append('Computation has no preceding review freeze')
            elif event_names.index('checks_started') <= event_names.index('reviews_frozen'):
                errors.append('Computation preceded review freeze')
            execution = read_json(run / 'checks/execution.json')
            starts = [e for e in events if e['event'] == 'checks_started']
            ends = [e for e in events if e['event'] in {'checks_completed', 'checks_failed'}]
            if (len(starts) != 1 or starts[0]['data']['script_sha256'] != execution['script_sha256']
                    or execution['script_sha256'] != digest(run / 'checks/runner/recompute.py')
                    or starts[0]['data']['reviews_freeze_sha256'] != digest(freeze_path)):
                errors.append('Computation start event does not match its script and review freeze')
            if execution['status'] in {'completed', 'failed'}:
                if (len(ends) != 1 or ends[0]['data']['execution_sha256'] != digest(run / 'checks/execution.json')
                        or len(starts) != 1 or ends[0]['sequence'] <= starts[0]['sequence']):
                    errors.append('Computation completion event mismatch')
            if execution['reviews_freeze_sha256'] != digest(freeze_path):
                errors.append('Computation is attached to different reviews')
            if execution['started_at_utc'] < read_json(freeze_path)['frozen_at_utc']:
                errors.append('Computation timestamp precedes frozen reviews')
            if meta['state'] in {'checks_completed', 'synthesizing', 'complete', 'synthesis_failed'}:
                if execution['status'] != 'completed' or execution.get('exit_code') != 0:
                    errors.append('Computation did not complete successfully')
                errors += _check_snapshot(run, read_json(run / 'checks_freeze.json')['files'])
                if (len(ends) != 1 or ends[0]['event'] != 'checks_completed'
                        or ends[0]['data'].get('checks_freeze_sha256') != digest(run / 'checks_freeze.json')):
                    errors.append('Computation freeze event mismatch')
        elif meta['state'] in {'checks_completed', 'synthesizing', 'complete', 'synthesis_failed'}:
            errors.append('Missing computations')
        if meta['state'] == 'complete':
            inputs = read_json(run / 'synthesis_inputs.json')
            errors += _check_snapshot(run, inputs['files'])
            errors += validate_call(run / 'synthesis', run / 'synthesis_prompt.txt', run / 'synthesis_schema.json')
            call = read_json(run / 'synthesis/call.json')
            if call['model_requested'] != inputs['model_requested']:
                errors.append('Synthesis model mismatch')
            if call.get('thread_id') in threads:
                errors.append('Synthesis reused a reviewer session')
            validate_synthesis(read_json(run / 'synthesis/response.json'), run, set(inputs['files']))
            starts = [e for e in events if e['event'] == 'synthesis_started']
            if (not starts or starts[-1]['data']['model'] != inputs['model_requested']
                    or starts[-1]['data']['prompt_sha256'] != digest(run / 'synthesis_prompt.txt')
                    or starts[-1]['data'].get('selection_sha256') != digest(run / 'synthesis_selection.json')):
                errors.append('Synthesis start event mismatch')
            selection = read_json(run / 'synthesis_selection.json')
            artifacts = {'checks/artifacts/' + p: entry for p, entry in inventory(run / 'checks/artifacts').items()}
            if (set(selection['included']) & set(selection['excluded'])
                    or {**selection['included'], **selection['excluded']} != artifacts
                    or set(selection['included']) != {p for p in inputs['files'] if p.startswith('checks/artifacts/')}):
                errors.append('Synthesis evidence selection does not match the frozen artifacts')
            if event_names.index('synthesis_started') <= event_names.index('checks_completed'):
                errors.append('Synthesis preceded computation completion')
            completed = [e for e in events if e['event'] == 'synthesis_completed']
            if (len(completed) != 1 or completed[0]['data']['response_sha256'] != digest(run / 'synthesis/response.json')
                    or not starts or completed[0]['sequence'] <= starts[-1]['sequence']):
                errors.append('Synthesis completion event mismatch')
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError) as error:
        errors.append(f'Invalid panel evidence: {error}')
    return errors


def render_report(run):
    run = Path(run)
    errors = verify_panel(run)
    if errors:
        raise ValueError('; '.join(errors))
    from .panel_report import render_panel
    path = render_panel(run); commit(run)
    return path
