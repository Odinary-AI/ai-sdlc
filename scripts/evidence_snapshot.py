#!/usr/bin/env python3
"""Optional Git input inventory. Does not execute checks or decide acceptance."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def selection(paths):
    result = set()
    for value in paths:
        p = PurePosixPath(value)
        if p.is_absolute() or '..' in p.parts or not p.parts or str(p) == '.':
            raise ValueError('Select explicit repository-relative files or directories')
        result.add(p.as_posix())
    return sorted(result)


def selected(name, paths):
    return any(name == p or name.startswith(p + '/') for p in paths)


def snapshot(root, source, paths, ref=None):
    root = root.resolve()
    if Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root:
        raise ValueError('--root must be the Git worktree root')
    paths = selection(paths)
    identity = None
    entries = {}
    if source == 'worktree':
        names = set(git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').decode().split('\0'))
        for name in sorted(n for n in names if n and selected(n, paths)):
            p = root / name
            # Do not follow even an in-repository link: keep the declared boundary simple.
            if any(parent.is_symlink() for parent in [p, *p.parents] if parent != root and root in parent.parents):
                raise ValueError('Symlink input is unsupported: ' + name)
            if not p.exists():
                entries[name] = {'missing': True}
                continue
            mode = p.stat().st_mode
            if not stat.S_ISREG(mode):
                raise ValueError('Only regular files are supported: ' + name)
            entries[name] = {'mode': '100755' if mode & 0o111 else '100644',
                             'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    else:
        if source == 'index':
            identity = git(root, 'write-tree').decode().strip()
        else:
            if not ref:
                raise ValueError('--ref is required for commit source')
            identity = git(root, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}').decode().strip()
        for row in git(root, 'ls-tree', '-rz', identity).split(b'\0'):
            if not row:
                continue
            meta, raw_name = row.split(b'\t', 1)
            name = raw_name.decode()
            if not selected(name, paths):
                continue
            mode, kind, blob = meta.decode().split()
            if kind != 'blob' or mode not in ('100644', '100755'):
                raise ValueError('Only regular files are supported: ' + name)
            entries[name] = {'mode': mode, 'sha256': hashlib.sha256(git(root, 'cat-file', 'blob', blob)).hexdigest()}
    # An empty selection is an observable gap, not a successful empty scan.
    if not entries:
        raise ValueError('No files selected in this source')
    body = json.dumps(entries, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()
    return {'source': source, 'identity': identity, 'paths': paths, 'files': entries,
            'files_sha256': hashlib.sha256(body).hexdigest(),
            'unmatched_paths': [p for p in paths if not any(selected(n, [p]) for n in entries)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--source', choices=['worktree', 'index', 'commit'], required=True)
    parser.add_argument('--ref')
    parser.add_argument('--path', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.ref and args.source != 'commit':
            raise ValueError('--ref is only valid for commit source')
        paths = selection(args.path)
        output = args.output.absolute()
        if output.exists() or output.is_symlink():
            raise ValueError('Output exists; choose a new path')
        try:
            relative = output.resolve().relative_to(args.root.resolve()).as_posix()
        except ValueError:
            relative = None
        if relative is not None and selected(relative, paths):
            raise ValueError('Output must be outside selected inputs')
        started = datetime.now(timezone.utc).isoformat()
        result = snapshot(args.root, args.source, paths, args.ref)
        result.update(started_at=started, finished_at=datetime.now(timezone.utc).isoformat())
        # Exclusive creation protects earlier results, including concurrent writers.
        with output.open('x') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        print(json.dumps({'output': str(output), 'files': len(result['files']),
                          'files_sha256': result['files_sha256']}))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
