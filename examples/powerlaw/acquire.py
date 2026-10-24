"""Download the pinned public powerlaw packet; never execute its author code.

Usage: python examples/powerlaw/acquire.py --output NEW_DIRECTORY
Install the project's pinned dependencies first (pypdf==6.14.2 is required).
Downloaded paper, author code and data stay in the selected local directory.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import urllib.request


TITLE = 'powerlaw: A Python Package for Analysis of Heavy-Tailed Distributions'
DOI = '10.1371/journal.pone.0085777'
DATA_COMMIT = 'd2b563a7a08bad96b4085fa69f351e9d9a20b1e7'
PYPDF_VERSION = '6.14.2'
PAPER_TEXT_SHA256 = '83b2ec926d17aa4eae8e47a336d0781fd6bb2775a0fd061cdcad32d7ff3647ef'
PLOS = 'https://journals.plos.org/plosone/article/file?id='
REPOSITORY = 'https://raw.githubusercontent.com/powerlaw-devs/powerlaw/' + DATA_COMMIT + '/'
SOURCES = (
    {'path': 'paper.pdf', 'role': 'paper', 'include_in_review': False,
     'source_url': PLOS + DOI + '&type=printable',
     'sha256': '578d1c7bfa991141f00575acea8a243cbf534608c6e1cb497705a7064bb54799'},
    {'path': 'author_powerlaw.py', 'role': 'code', 'include_in_review': True,
     'source_url': PLOS + DOI + '.s001&type=supplementary',
     'sha256': '547c0e2d33b09ca8078e8d2abde686412ea1f548bb1a8e5b4d019006d929a105'},
    {'path': 'author_figures.py', 'role': 'code', 'include_in_review': True,
     'source_url': PLOS + DOI + '.s002&type=supplementary',
     'sha256': '809d7a28227ede36ea90e1b611ef56a2575c3cd630b0c6894dd001e8554c3bdb'},
    {'path': 'blackouts.txt', 'role': 'data', 'include_in_review': True,
     'source_url': REPOSITORY + 'manuscript/blackouts.txt',
     'sha256': '8187543b5700a75974661dd8349e172a83ce2d0972e79a81a7fcc06eafb96728'},
    {'path': 'words.txt', 'role': 'data', 'include_in_review': True,
     'source_url': REPOSITORY + 'manuscript/words.txt',
     'sha256': 'cef3521f0f1d817df43cf35ef1f717e6f72d71f549646a51ba04acdc45a9b160'},
    {'path': 'worm.txt', 'role': 'data', 'include_in_review': True,
     'source_url': REPOSITORY + 'manuscript/worm.txt',
     'sha256': '8754d06905e1d2318e19ba3e8b936f653657893b9ff8ce9fbc51ad9b26f992ac'},
    {'path': 'AUTHOR_LICENSE.txt', 'role': 'license', 'include_in_review': True,
     'source_url': REPOSITORY + 'LICENSE',
     'sha256': 'ec7e397e8ae8c4e0cf1571f61f435fbdec8f28080fce4befc96fd13554a726ef'},
)
RIGHTS = ('Publisher identifies the paper as CC0; Code S1 includes an MIT notice. '
          'Dataset source references are in the paper; no new data relicensing is asserted. '
          'The repository license file is retained as a source artifact, not a blanket license for every input.')
CODE_VERSION = 'Exact PLOS Code S1 and S2 attached to the 2014 manuscript, not the modern package'
SELECTION = ('Convenience demonstration selected for public original code, accessible small datasets '
             'and CPU feasibility; not a random paper sample. This paper has prior SciNet case history. '
             'The packet contains only original sources and extracted paper text, with no prior reviews '
             'or SciNet computation results.')


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))


def acquire(output):
    output = Path(output).expanduser().resolve()
    # Even an empty existing directory is refused: an attempted run is immutable.
    output.mkdir(parents=True, exist_ok=False)
    record = {'format': 'scinet.powerlaw-acquisition.v1', 'status': 'started',
              'started_at_utc': now(), 'paper': {'title': TITLE, 'doi': DOI},
              'paper_year': 2014, 'author_code_version': CODE_VERSION,
              'data_repository_commit': DATA_COMMIT, 'rights': RIGHTS,
              'extraction': 'pypdf ' + PYPDF_VERSION, 'files': []}
    write_json(output / 'acquisition.json', record)
    current = None
    try:
        import pypdf
        if pypdf.__version__ != PYPDF_VERSION:
            raise RuntimeError(f'Exact paper text extraction requires pypdf=={PYPDF_VERSION}; found {pypdf.__version__}')
        entries = []
        for source in SOURCES:
            current = {**source, 'expected_sha256': source['sha256'], 'status': 'downloading',
                       'started_at_utc': now()}
            current.pop('sha256')
            record['files'].append(current)
            record['status'] = 'downloading'
            write_json(output / 'acquisition.json', record)
            request = urllib.request.Request(source['source_url'],
                                             headers={'User-Agent': 'SciNet pinned public-source acquisition'})
            path = output / source['path']
            with path.open('xb') as stream, urllib.request.urlopen(request, timeout=60) as response:
                current['resolved_url'] = (response.geturl() if hasattr(response, 'geturl')
                                           else source['source_url'])
                total = 0
                while chunk := response.read(65536):
                    total += len(chunk)
                    if total > 32 * 1024 * 1024:
                        raise ValueError('Source exceeds the 32 MB acquisition limit: ' + source['path'])
                    stream.write(chunk)
            current.update(bytes=path.stat().st_size, sha256=sha256(path), acquired_at_utc=now())
            if current['sha256'] != source['sha256']:
                current['status'] = 'hash_mismatch'
                raise ValueError('Source hash mismatch: ' + source['path'] + '; rejected bytes retained, expected source not replaced')
            current['status'] = 'verified'
            entries.append({**source, 'bytes': current['bytes'], 'acquired_at_utc': current['acquired_at_utc']})
            write_json(output / 'acquisition.json', record)

        record['status'] = 'extracting'
        current = {'path': 'paper.txt', 'derived_from': 'paper.pdf',
                   'extraction': 'pypdf ' + PYPDF_VERSION, 'expected_sha256': PAPER_TEXT_SHA256,
                   'status': 'extracting', 'started_at_utc': now()}
        record['files'].append(current)
        write_json(output / 'acquisition.json', record)
        pdf = pypdf.PdfReader(output / 'paper.pdf')
        text = '\n\n'.join(f'=== PDF PAGE {i} ===\n' + (page.extract_text() or '')
                           for i, page in enumerate(pdf.pages, 1))
        with (output / 'paper.txt').open('xb') as stream:
            stream.write(text.encode('utf-8'))
        current.update(bytes=(output / 'paper.txt').stat().st_size,
                       sha256=sha256(output / 'paper.txt'), acquired_at_utc=now())
        if current['sha256'] != PAPER_TEXT_SHA256:
            current['status'] = 'hash_mismatch'
            raise ValueError('Derived paper.txt hash mismatch; extracted bytes retained, bundle not published')
        current['status'] = 'verified'
        entries.append({'path': 'paper.txt', 'role': 'paper', 'include_in_review': True,
                        'source_url': SOURCES[0]['source_url'], 'sha256': current['sha256'],
                        'bytes': current['bytes'], 'acquired_at_utc': current['acquired_at_utc'],
                        'derived_from': 'paper.pdf', 'extraction': 'pypdf ' + PYPDF_VERSION})
        bundle = {'paper': record['paper'], 'selection_disclosure': SELECTION,
                  'paper_year': 2014, 'author_code_version': CODE_VERSION,
                  'data_repository_commit': DATA_COMMIT, 'rights': RIGHTS,
                  'acquired_at_utc': now(), 'files': entries}
        bundle_path = output / 'bundle.json'
        with bundle_path.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(bundle, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        record.update(status='completed', bundle_sha256=sha256(bundle_path), finished_at_utc=now())
        write_json(output / 'acquisition.json', record)
        return bundle_path
    except BaseException as error:
        if current is not None and current['status'] not in ('verified', 'hash_mismatch'):
            current['status'] = 'failed'
            path = output / current['path']
            if path.is_file():
                current.update(bytes=path.stat().st_size, sha256=sha256(path))
        record.update(status='failed', error=f'{type(error).__name__}: {error}', finished_at_utc=now())
        write_json(output / 'acquisition.json', record)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description='Acquire a hash-pinned, local-only powerlaw source packet; requires pypdf==6.14.2.')
    parser.add_argument('--output', required=True, type=Path, help='New directory; existing directories are never overwritten')
    args = parser.parse_args(argv)
    try:
        bundle = acquire(args.output)
    except KeyboardInterrupt:
        print('Acquisition interrupted; downloaded evidence and status are retained.', file=sys.stderr)
        return 130
    except Exception as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1
    print('BUNDLE=' + str(bundle))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
