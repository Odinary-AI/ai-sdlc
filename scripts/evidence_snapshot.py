#!/usr/bin/env python3
"""Optional Git input inventory. Does not execute checks or decide acceptance."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import shutil
import os
import tempfile


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


def fresh_target(path):
    """Reject link aliases and require an existing parent, without creating it."""
    path = path.absolute()
    if '..' in path.parts or any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('Target must not contain symlinks or parent traversal')
    if path.exists():
        raise ValueError('Output exists; choose a new path')
    if not path.parent.is_dir():
        raise ValueError('Output parent must be an existing directory')
    return path


def export_snapshot(root, result, destination):
    """Materialize only regular blobs from the already fixed object, never run them."""
    if result['source'] == 'worktree':
        raise ValueError('Export supports only fixed index or commit sources')
    if result['unmatched_paths']:
        raise ValueError('Export selection has unmatched paths')
    destination = fresh_target(destination)
    if destination.is_relative_to(root.resolve()):
        raise ValueError('Export must be outside the original repository')
    blobs = {}
    for row in git(root, 'ls-tree', '-rz', result['identity']).split(b'\0'):
        if not row:
            continue
        meta, raw_name = row.split(b'\t', 1)
        name = raw_name.decode()
        if name not in result['files']:
            continue
        p = PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or any(part.lower() == '.git' for part in p.parts):
            raise ValueError('Unsafe Git path: ' + name)
        mode, kind, blob = meta.decode().split()
        if kind != 'blob' or mode not in ('100644', '100755'):
            raise ValueError('Only regular files are supported: ' + name)
        blobs[name] = blob
    if set(blobs) != set(result['files']):
        raise ValueError('Fixed object file set differs from inventory')
    # Exclusive mkdir reserves the destination; existing directories are never replaced.
    destination.mkdir()
    try:
        for name, blob in blobs.items():
            data = git(root, 'cat-file', 'blob', blob)
            if hashlib.sha256(data).hexdigest() != result['files'][name]['sha256']:
                raise ValueError('Blob differs from inventory: ' + name)
            p = destination / name
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('xb') as stream:
                stream.write(data)
            p.chmod(int(result['files'][name]['mode'], 8))
        return destination
    except BaseException:
        shutil.rmtree(destination)
        raise


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
            # write-tree refreshes cache-tree metadata; isolate even those index writes.
            index = Path(git(root, 'rev-parse', '--git-path', 'index').decode().strip())
            if not index.is_absolute():
                index = root / index
            with tempfile.TemporaryDirectory() as temp:
                copied = Path(temp) / 'index'
                shutil.copyfile(index, copied)
                identity = subprocess.check_output(
                    ['git', '-C', str(root), 'write-tree'],
                    env={**os.environ, 'GIT_INDEX_FILE': str(copied)}).decode().strip()
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
    parser.add_argument('--export-dir', type=Path,
                        help='Optional fresh directory outside repository; index/commit only')
    args = parser.parse_args()
    try:
        if args.ref and args.source != 'commit':
            raise ValueError('--ref is only valid for commit source')
        paths = selection(args.path)
        output = args.output.absolute()
        if output.exists() or output.is_symlink():
            raise ValueError('Output exists; choose a new path')
        if args.export_dir:
            destination = fresh_target(args.export_dir)
            if output.resolve() == destination or output.resolve().is_relative_to(destination):
                raise ValueError('Report must be outside export directory')
        try:
            relative = output.resolve().relative_to(args.root.resolve()).as_posix()
        except ValueError:
            relative = None
        if relative is not None and selected(relative, paths):
            raise ValueError('Output must be outside selected inputs')
        started = datetime.now(timezone.utc).isoformat()
        result = snapshot(args.root, args.source, paths, args.ref)
        if args.export_dir:
            result['export_directory'] = str(export_snapshot(args.root, result, destination))
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
