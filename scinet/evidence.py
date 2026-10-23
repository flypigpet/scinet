"""Content-integrity checks; these hashes are not digital signatures."""
import hashlib
import json
from pathlib import Path

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def safe_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError(f'Unsafe evidence path: {relative}')
    return path

def seal(root):
    root = Path(root)
    files = {p.relative_to(root).as_posix(): digest(p) for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'manifest.json'}
    write_json(root/'manifest.json', {'algorithm':'SHA-256','scope':'File integrity only; no trusted signature, blockchain or external timestamp.', 'files':files})

def verify(root):
    root = Path(root); errors = []
    try: manifest = read_json(root/'manifest.json')
    except (OSError, ValueError) as e: return [f'Manifest unavailable: {e}']
    for name, expected in manifest['files'].items():
        try:
            path = safe_path(root, name)
            if not path.is_file(): errors.append(f'Missing: {name}')
            elif digest(path) != expected: errors.append(f'Hash mismatch: {name}')
        except ValueError as e: errors.append(str(e))
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    for name in sorted(actual - set(manifest['files'])): errors.append(f'Unrecorded: {name}')
    return errors

def validate_review(review, root, inputs):
    if not isinstance(review, dict): raise ValueError('AI review must be an object')
    if not isinstance(review.get('summary'), str) or not review['summary'].strip(): raise ValueError('Empty AI summary')
    if not review.get('limitations') or not all(isinstance(x,str) and x.strip() for x in review['limitations']): raise ValueError('Missing limitations')
    for name, expected in inputs.items():
        path = safe_path(root, name)
        if not path.is_file() or digest(path) != expected: raise ValueError(f'Stale AI input: {name}')
    if not review.get('findings'): raise ValueError('No findings')
    seen = set()
    for f in review['findings']:
        for field in ('id','claim_id','title','status','explanation'):
            if not isinstance(f.get(field), str) or not f[field].strip(): raise ValueError(f'Missing {field}')
        if f['id'] in seen: raise ValueError('Duplicate finding ID')
        seen.add(f['id'])
        if f['claim_id'] not in ('C1','C2','C3','C4'): raise ValueError('Unknown claim')
        if f['status'] not in ('supported','qualified','unsupported','not_tested'): raise ValueError('Invalid finding status')
        if not f.get('evidence'): raise ValueError('Finding has no evidence')
        for e in f['evidence']:
            if e.get('path') not in inputs: raise ValueError(f'Unprovided evidence: {e.get("path")}')
            if not isinstance(e.get('locator'),str) or not e['locator'].strip(): raise ValueError('Missing evidence locator')
            if not safe_path(root, e['path']).is_file(): raise ValueError('Missing evidence file')
    if {f['claim_id'] for f in review['findings']} != {'C1','C2','C3','C4'}:
        raise ValueError('AI review must address all four claims C1-C4')
