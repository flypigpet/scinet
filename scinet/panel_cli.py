"""Command-line entry points for explicit, auditable panel phases."""
from pathlib import Path
import sys

from . import panel
from .evidence import read_json


def _read_evidence_list(path):
    if path is None:
        return None
    values = read_json(path)
    if (not isinstance(values, list) or not values
            or any(not isinstance(p, str) for p in values)):
        raise ValueError('Explicit evidence list must be a nonempty JSON array of paths')
    if len(set(values)) != len(values):
        raise ValueError('Explicit evidence list contains duplicate paths')
    for name in values:
        if (not name.startswith('checks/artifacts/') or '\\' in name or ':' in name
                or any(ord(c) < 32 for c in name)
                or any(p in ('', '.', '..') for p in name.split('/'))
                or Path(name).suffix.lower() not in panel.TEXT_SUFFIXES):
            raise ValueError('Evidence paths must be portable text files under checks/artifacts/')
    return values


def add_parser(subparsers):
    parser = subparsers.add_parser('panel', help='Independent-context multi-model review, then evidence checks')
    commands = parser.add_subparsers(dest='panel_command', required=True)
    for name in ('run', 'review'):
        command = commands.add_parser(name)
        command.add_argument('--bundle', type=Path, required=True, help='Source inventory with explicit hashes and model-visible text')
        command.add_argument('--output', type=Path, required=True, help='New evidence directory; existing runs are never overwritten')
        command.add_argument('--model', action='append', required=True, help='Repeat for at least two distinct model IDs')
        command.add_argument('--timeout', type=int, default=600, help='Seconds per model call')
        if name == 'run':
            command.add_argument('--script', type=Path, required=True, help='Inspected local reproduction script, executed only after review freeze')
            command.add_argument('--compute-timeout', type=int, default=300)
            command.add_argument('--synthesis-model', required=True)
            command.add_argument('--evidence-list', type=Path, help='JSON array of explicit computation text paths for synthesis')
    command = commands.add_parser('recompute')
    command.add_argument('run_dir', type=Path); command.add_argument('--script', type=Path, required=True)
    command.add_argument('--timeout', type=int, default=300)
    command = commands.add_parser('synthesize')
    command.add_argument('run_dir', type=Path); command.add_argument('--model', required=True)
    command.add_argument('--timeout', type=int, default=600)
    command.add_argument('--evidence-list', type=Path, help='JSON array of explicit computation text paths for synthesis')
    command = commands.add_parser('continue-synthesis', help='Preserve a completed-check run and its failed synthesis in a new continuation directory')
    command.add_argument('run_dir', type=Path); command.add_argument('--output', type=Path, required=True)
    command.add_argument('--model', required=True); command.add_argument('--timeout', type=int, default=600)
    command.add_argument('--evidence-list', type=Path)
    for name in ('verify', 'report'):
        command = commands.add_parser(name)
        command.add_argument('run_dir', type=Path)
        if name == 'verify':
            command.add_argument('--expected-root', help='Compare with a SHA-256 commitment saved independently')


def main(args):
    run = None
    try:
        for field in ('timeout', 'compute_timeout'):
            if hasattr(args, field) and getattr(args, field) <= 0:
                raise ValueError('Timeouts must be positive')
        command = args.panel_command
        evidence_paths = _read_evidence_list(getattr(args, 'evidence_list', None))
        if command in ('run', 'review'):
            run = panel.create_panel(args.bundle, args.output, args.model)
            print('PANEL_DIR=' + str(run), flush=True)
            print('Reviewing identical raw materials; recomputation has not started.', flush=True)
            panel.run_reviews(run, timeout=args.timeout)
            print('All original reviews are frozen.', flush=True)
            if command == 'run':
                panel.run_checks(run, args.script, timeout=args.compute_timeout)
                print('Recomputation completed; comparing the preserved reviews with its evidence.', flush=True)
                panel.synthesize(run, model=args.synthesis_model, timeout=args.timeout, evidence_paths=evidence_paths)
        else:
            run = args.run_dir.expanduser().resolve()
            if command == 'recompute':
                panel.run_checks(run, args.script, timeout=args.timeout)
            elif command == 'synthesize':
                panel.synthesize(run, model=args.model, timeout=args.timeout, evidence_paths=evidence_paths)
            elif command == 'continue-synthesis':
                from .panel_resume import fork_for_synthesis
                run = fork_for_synthesis(run, args.output)
                print('CONTINUATION_DIR=' + str(run), flush=True)
                panel.synthesize(run, model=args.model, timeout=args.timeout, evidence_paths=evidence_paths)
        errors = panel.verify_panel(run, expected_root=getattr(args, 'expected_root', None))
        if errors:
            print('\n'.join(errors), file=sys.stderr)
            return 1
        if command != 'verify':
            print('REPORT=' + str(panel.render_report(run)), flush=True)
        else:
            state = read_json(run / 'panel.json')['state']
            print(f'Panel evidence integrity verified; state={state}. This is not scientific validation or blockchain attestation.')
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f'Panel stopped: {error}', file=sys.stderr)
        if run and (run / 'panel.json').exists():
            print('PRESERVED_EVIDENCE=' + str(run), file=sys.stderr)
        return 1
