"""Check this curated subset, not the larger private run or its scientific claims."""
import hashlib
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    record = json.loads((root / 'publication.json').read_text(encoding='utf-8'))
    actual = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Linked public artifact: {path.name}')
        if path.is_file() and path != root / 'publication.json':
            content = path.read_bytes()
            actual[path.relative_to(root).as_posix()] = {
                'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)}
    if actual != record['public_files']:
        changed = [p for p in set(actual) | set(record['public_files'])
                   if actual.get(p) != record['public_files'].get(p)]
        raise ValueError('Public file inventory differs: ' + ', '.join(sorted(changed)))
    encoded = json.dumps(actual, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    if hashlib.sha256(encoded).hexdigest() != record['public_inventory_sha256']:
        raise ValueError('Public inventory digest differs')
    print(f'Verified {len(actual)} public files. This is not a signature, a full local run, or scientific validation.')


if __name__ == '__main__':
    main()
