"""Create an explicitly labelled synthesis continuation without rerunning reviews.

The parent is archived verbatim, including its original commitment and any
failed synthesis attempt. New evidence is sealed separately; this is a local
integrity relationship, not a fresh review, signature, or trusted timestamp.
"""
from datetime import datetime
from pathlib import Path
import shutil

from .evidence import digest, read_json, write_json
from .panel_record import (append_event, artifact_path, commit, inventory,
                           load_events, now, verify_commitment, verify_events)


_STATES = {'checks_completed', 'synthesis_failed'}
_FREEZES = ('input_freeze.json', 'reviews_freeze.json', 'checks_freeze.json')
_EXCLUDED_FILES = {'commitment.json', 'report.html', 'panel.json',
                   'synthesis_prompt.txt', 'synthesis_schema.json', 'synthesis_inputs.json', 'synthesis_selection.json',
                   'continuation.json'}
_EXCLUDED_DIRS = {'synthesis', 'parent_bundle', 'continuation_implementation'}
_PURPOSE = ('Synthesis-only continuation: reuse the parent frozen reviews and computations; '
            'no new review or computation call is claimed. The failed parent attempt remains archived.')


def _copy_file(source, destination, name):
    original = artifact_path(source, name)
    target = artifact_path(destination, name)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, target)


def fork_for_synthesis(source: Path, output: Path) -> Path:
    """Archive a verified parent and prepare a new synthesis-only run directory."""
    # Keep the dependency local: panel.verify_panel calls verify_continuation.
    from .panel import verify_panel

    source = Path(source).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f'Preserve existing evidence; output must not exist: {output}')
    if output.is_relative_to(source):
        raise ValueError('Continuation output must be outside the source directory')
    errors = verify_panel(source)
    if errors:
        raise ValueError('Parent evidence is invalid: ' + '; '.join(errors))
    meta = read_json(source / 'panel.json')
    if meta['state'] not in _STATES:
        raise ValueError('Continuation requires completed reviews and computations')
    root = read_json(source / 'commitment.json')['root_sha256']
    source_files = inventory(source)
    output.mkdir(parents=True)
    parent = output / 'parent_bundle'
    parent.mkdir()
    for path in source.rglob('*'):
        name = path.relative_to(source).as_posix()
        if artifact_path(source, name).is_dir():
            artifact_path(parent, name).mkdir(parents=True, exist_ok=True)
    for name in source_files:
        _copy_file(source, parent, name)
    # Recheck the archived bytes before using them, in case the source changed
    # while copying. All subsequent reused evidence comes from this archive.
    errors = verify_commitment(parent, expected_root=root)
    if errors:
        raise ValueError('Parent changed during archival: ' + '; '.join(errors))
    for name in source_files:
        if name in _EXCLUDED_FILES or name.split('/', 1)[0] in _EXCLUDED_DIRS:
            continue
        _copy_file(parent, output, name)
    implementation = output / 'continuation_implementation'
    implementation.mkdir()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        shutil.copy2(path, implementation / path.name)
    implementation_files = {'continuation_implementation/' + name: record
                            for name, record in inventory(implementation).items()}
    record = {'format': 'scinet.synthesis-continuation.v1', 'parent_root_sha256': root,
              'parent_state': meta['state'], 'created_at': now(),
              'implementation': implementation_files, 'purpose': _PURPOSE}
    write_json(output / 'continuation.json', record)
    meta.update(state='checks_completed', continuation={
        'parent_root_sha256': root, 'purpose': _PURPOSE,
        'reused_phases': ['reviews', 'checks'], 'fresh_reviews': False, 'fresh_computation': False})
    meta.pop('error', None)
    write_json(output / 'panel.json', meta)
    append_event(output, 'synthesis_continuation', {
        'continuation_sha256': digest(output / 'continuation.json'), 'parent_root_sha256': root})
    commit(output)
    errors = verify_continuation(output)
    if errors:
        raise ValueError('Invalid continuation: ' + '; '.join(errors))
    return output


def verify_continuation(run: Path) -> list[str]:
    """Check the parent relationship without recursively verifying parent panels."""
    run = Path(run)
    if not (run / 'continuation.json').exists():
        # A deleted relationship record must not downgrade an existing
        # continuation into an ordinary run after someone reseals its files.
        if (run / 'parent_bundle').exists() or (run / 'continuation_implementation').exists():
            return ['Missing continuation record for archived parent evidence']
        try:
            if (run / 'panel.json').is_file() and read_json(run / 'panel.json').get('continuation'):
                return ['Missing continuation record for declared panel continuation']
        except (OSError, ValueError, TypeError, AttributeError) as error:
            return ['Invalid continuation metadata: ' + str(error)]
        return []
    errors = []
    try:
        record = read_json(artifact_path(run, 'continuation.json'))
        if record['format'] != 'scinet.synthesis-continuation.v1':
            raise ValueError('Unsupported continuation format')
        if not isinstance(record['purpose'], str) or not record['purpose'].strip():
            raise ValueError('Missing continuation purpose')
        datetime.fromisoformat(record['created_at'])
        parent = artifact_path(run, 'parent_bundle')
        errors += ['Parent archive: ' + error for error in
                   verify_commitment(parent, expected_root=record['parent_root_sha256'])]
        parent_meta = read_json(artifact_path(parent, 'panel.json'))
        if parent_meta['state'] not in _STATES or parent_meta['state'] != record['parent_state']:
            errors.append('Parent state does not permit this synthesis continuation')
        meta = read_json(artifact_path(run, 'panel.json'))
        marker = meta.get('continuation', {})
        if (not isinstance(marker, dict)
                or marker.get('parent_root_sha256') != record['parent_root_sha256']
                or marker.get('reused_phases') != ['reviews', 'checks']
                or marker.get('fresh_reviews') is not False
                or marker.get('fresh_computation') is not False):
            errors.append('Panel does not disclose reuse of the parent review and computation')
        for key in ('paper', 'reviewers', 'created_at_utc', 'limitations'):
            if meta.get(key) != parent_meta.get(key):
                errors.append('Continuation changed inherited panel metadata: ' + key)
        for name in _FREEZES:
            parent_path = artifact_path(parent, name)
            current_path = artifact_path(run, name)
            if parent_path.read_bytes() != current_path.read_bytes():
                errors.append('Continuation changed a parent freeze: ' + name)
            frozen = read_json(parent_path)
            for relative, expected in frozen['files'].items():
                path = artifact_path(run, relative)
                if (not path.is_file() or digest(path) != expected['sha256']
                        or path.stat().st_size != expected['bytes']):
                    errors.append('Reused frozen artifact differs from parent: ' + relative)
        for directory in ('inputs', 'reviews', 'checks', 'implementation'):
            if inventory(artifact_path(run, directory)) != inventory(artifact_path(parent, directory)):
                errors.append('Reused evidence directory differs from parent: ' + directory)
        expected = record['implementation']
        if not isinstance(expected, dict) or not expected:
            raise ValueError('Missing continuation implementation snapshot')
        for name in expected:
            if not name.startswith('continuation_implementation/'):
                raise ValueError('Implementation snapshot points outside its directory')
            artifact_path(run, name)
        actual = {'continuation_implementation/' + name: entry for name, entry in
                  inventory(artifact_path(run, 'continuation_implementation')).items()}
        if actual != expected:
            errors.append('Continuation implementation snapshot differs from its record')
        errors += verify_events(run)
        errors += ['Parent timeline: ' + error for error in verify_events(parent)]
        parent_timeline = artifact_path(parent, 'timeline.jsonl').read_bytes()
        timeline = artifact_path(run, 'timeline.jsonl').read_bytes()
        parent_events, events = load_events(parent), load_events(run)
        if not parent_timeline or not timeline.startswith(parent_timeline):
            errors.append('Parent timeline is not the exact byte prefix of this continuation')
        boundary = len(parent_events)
        if events[:boundary] != parent_events:
            errors.append('Parent events are not the prefix of this continuation')
        if len(events) <= boundary:
            errors.append('Missing immediate synthesis continuation event')
        else:
            event = events[boundary]
            if (event['event'] != 'synthesis_continuation'
                    or event['data'].get('continuation_sha256') != digest(run / 'continuation.json')
                    or event['data'].get('parent_root_sha256') != record['parent_root_sha256']):
                errors.append('Immediate continuation event does not bind its record and parent')
            if sum(event['event'] == 'synthesis_continuation' for event in events[boundary:]) != 1:
                errors.append('Duplicated synthesis continuation event after the parent timeline')
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError) as error:
        errors.append('Invalid continuation evidence: ' + str(error))
    return errors
