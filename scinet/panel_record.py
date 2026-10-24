"""Portable, unsigned evidence commitments and a local hash-linked event log.

This format is deliberately not advertised as RFC 8785, a signature, a trusted
timestamp or blockchain anchoring. Its exact canonical JSON encoding is below.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from .evidence import read_json, write_json


FORMAT = 'scinet.commitment.v1'
ENCODING = 'UTF-8; sorted JSON keys; compact separators; literal Unicode; no NaN'


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def object_hash(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def artifact_path(root, name):
    if (not isinstance(name, str) or not name or '\\' in name or ':' in name
            or '\x00' in name or name.startswith('/')
            or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError(f'Unsafe artifact path: {name!r}')
    root = Path(root).resolve()
    path = root.joinpath(*PurePosixPath(name).parts)
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise ValueError(f'Linked artifact is not allowed: {name}')
    if not path.resolve().is_relative_to(root):
        raise ValueError(f'Artifact escaped root: {name}')
    return path


def inventory(root, *, exclude=()):
    root = Path(root).resolve()
    result = {}
    for candidate in sorted(root.rglob('*')):
        name = candidate.relative_to(root).as_posix()
        path = artifact_path(root, name)
        if path.is_file() and name not in exclude:
            raw = path.read_bytes()
            result[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    return result


def commit(root):
    root = Path(root)
    if (root / 'timeline.jsonl').exists():
        errors = verify_events(root)
        if errors:
            raise ValueError('; '.join(errors))
    payload = {'format': FORMAT, 'files': inventory(root, exclude=('commitment.json',))}
    record = {'format': FORMAT, 'algorithm': 'sha256', 'canonicalization': ENCODING,
              'root_sha256': object_hash(payload), 'payload': payload,
              'scope': 'Unsigned local integrity record; no trusted identity, time or blockchain proof.'}
    write_json(root / 'commitment.json', record)
    return record


def verify_commitment(root, *, expected_root=None):
    errors = []
    try:
        root = Path(root)
        record = read_json(root / 'commitment.json')
        if expected_root is not None:
            if not isinstance(expected_root, str) or not re.fullmatch('[0-9a-f]{64}', expected_root):
                raise ValueError('External root must be a lowercase SHA-256 digest')
            if record.get('root_sha256') != expected_root:
                errors.append('Commitment differs from externally supplied root')
        if (record['format'] != FORMAT or record['algorithm'] != 'sha256'
                or record['canonicalization'] != ENCODING or record['payload']['format'] != FORMAT):
            raise ValueError('Unsupported commitment format')
        if object_hash(record['payload']) != record['root_sha256']:
            errors.append('Commitment root mismatch')
        expected = record['payload']['files']
        if not isinstance(expected, dict) or 'commitment.json' in expected:
            raise ValueError('Invalid commitment file inventory')
        for name, entry in expected.items():
            artifact_path(root, name)
            if (not isinstance(entry, dict) or not re.fullmatch('[0-9a-f]{64}', entry.get('sha256', ''))
                    or type(entry.get('bytes')) is not int or entry['bytes'] < 0):
                raise ValueError(f'Invalid file entry: {name}')
        actual = inventory(root, exclude=('commitment.json',))
        for name in sorted(set(expected) | set(actual)):
            if name not in actual:
                errors.append(f'Missing artifact: {name}')
            elif name not in expected:
                errors.append(f'Unrecorded artifact: {name}')
            elif actual[name] != expected[name]:
                errors.append(f'Changed artifact: {name}')
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        errors.append(f'Invalid commitment: {error}')
    return errors


def load_events(root):
    path = Path(root) / 'timeline.jsonl'
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []


def verify_events(root):
    errors = []
    try:
        previous = None
        for i, entry in enumerate(load_events(root)):
            body = {k: v for k, v in entry.items() if k != 'event_hash'}
            if (body.get('sequence') != i or body.get('previous_hash') != previous
                    or entry.get('event_hash') != object_hash(body)):
                errors.append(f'Broken event chain at entry {i}')
            if not isinstance(body.get('event'), str) or not isinstance(body.get('data'), dict):
                errors.append(f'Invalid event at entry {i}')
            datetime.fromisoformat(body['at_utc'])
            previous = entry['event_hash']
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        errors.append(f'Invalid event log: {error}')
    return errors


def append_event(root, event, data):
    errors = verify_events(root)
    if errors:
        raise ValueError('; '.join(errors))
    entries = load_events(root)
    body = {'sequence': len(entries), 'previous_hash': entries[-1]['event_hash'] if entries else None,
            'at_utc': now(), 'event': event, 'data': data}
    record = {**body, 'event_hash': object_hash(body)}
    with (Path(root) / 'timeline.jsonl').open('ab') as stream:
        stream.write(canonical_bytes(record) + b'\n')
    return record
