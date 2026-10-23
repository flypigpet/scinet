"""Acquire local-only paper inputs after initializing the offline example."""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.request

from pypdf.errors import PdfReadError

PAGE = 'https://www.research.autodesk.com/publications/same-stats-different-graphs/'
PDF = 'https://research.autodesk.com/app/uploads/2023/03/same-stats-different-graphs.pdf_rec2hRjLLGgM7Cn2T.pdf'
FULLTEXT = ('paper.pdf', 'author_page.html', 'paper.txt', 'author_page.txt')


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip = 0; self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.skip += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.skip = max(0, self.skip - 1)
    def handle_data(self, data):
        if not self.skip and data.strip(): self.parts.append(data.strip())


def check_files(root, entries):
    for entry in entries:
        target = (root / entry['path']).resolve()
        if target == root or not target.is_relative_to(root):
            raise ValueError('Unsafe source path: ' + entry['path'])
        if hashlib.sha256(target.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Source hash mismatch: ' + entry['path'])


def acquire(root):
    root = root.expanduser().resolve()
    out = root / 'sources'
    manifest_path = out / 'provenance.json'
    if not manifest_path.is_file():
        raise ValueError('Initialize this workspace first with scinet init --workspace PATH.')
    for name in FULLTEXT:
        if (out / name).exists() or (out / name).is_symlink():
            raise FileExistsError('Existing local input will not be overwritten: ' + name)
    original = manifest_path.read_bytes()
    provenance = json.loads(original)
    check_files(out.resolve(), provenance['files'])
    check_files(root, provenance.get('vendor_files', []))

    # Keep downloads and extraction in memory until both succeed. Network and
    # PDF failures must leave the initialized numerical example untouched.
    payloads, entries = {}, []
    for name, url in [('paper.pdf', PDF), ('author_page.html', PAGE)]:
        request = urllib.request.Request(url, headers={'User-Agent': 'SciNet research reproduction prototype'})
        with urllib.request.urlopen(request, timeout=45) as response:
            payloads[name] = response.read()
        entries.append({'path': name, 'url': url})
    from pypdf import PdfReader
    pages = [f'=== PDF PAGE {i} ===\n{page.extract_text() or ""}'
             for i, page in enumerate(PdfReader(io.BytesIO(payloads['paper.pdf'])).pages, 1)]
    if not pages: raise ValueError('Paper PDF contains no pages.')
    payloads['paper.txt'] = '\n\n'.join(pages).encode('utf-8')
    parser = Text(); parser.feed(payloads['author_page.html'].decode('utf-8')); parser.close()
    if not parser.parts: raise ValueError('Author webpage contains no extractable text.')
    payloads['author_page.txt'] = '\n'.join(parser.parts).encode('utf-8')
    entries += [{'path': 'paper.txt', 'derived_from': 'paper.pdf'},
                {'path': 'author_page.txt', 'derived_from': 'author_page.html'}]
    for entry in entries:
        raw = payloads[entry['path']]
        entry.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    updated = {**provenance, 'files': provenance['files'] + entries,
               'acquired_at_utc': datetime.now(timezone.utc).isoformat(),
               'fulltext_local_only': True,
               'fulltext_rights_note': 'Paper and project page retain separate rights. Full text and derived text are excluded from public releases.'}

    if manifest_path.read_bytes() != original:
        raise ValueError('Workspace provenance changed during acquisition; retry in a fresh workspace.')
    check_files(out.resolve(), provenance['files'])
    check_files(root, provenance.get('vendor_files', []))
    created = []
    staged_manifest = None
    try:
        for name, raw in payloads.items():
            target = out / name
            with target.open('xb') as stream:
                created.append(target)
                stream.write(raw)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=out,
                                         prefix='.provenance-', suffix='.tmp', delete=False) as stream:
            staged_manifest = Path(stream.name)
            json.dump(updated, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(staged_manifest, manifest_path)
    except BaseException:
        for target in created: target.unlink(missing_ok=True)
        raise
    finally:
        if staged_manifest is not None: staged_manifest.unlink(missing_ok=True)
    return {'files': len(updated['files']), 'sources': str(out), 'fulltext_local_only': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Download local-only full text after scinet init. Paper and webpage inputs are excluded from public release artifacts.')
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = acquire(args.workspace)
    except (OSError, ValueError, KeyError, TypeError, PdfReadError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__': raise SystemExit(main())
