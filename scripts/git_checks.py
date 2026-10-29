#!/usr/bin/env python3
"""Read-only Git whitespace checks and explicit path-based check suggestions."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

sys.dont_write_bytecode = True


def relative(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or '..' in path.parts or not path.parts or '.git' in path.parts:
        raise ValueError('必须选择明确的项目相对路径: ' + value)
    return path.as_posix()


def matches(name, paths):
    return any(name == path or name.startswith(path.rstrip('/') + '/') for path in paths)


def git(root, *args, check=True):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    index = os.environ.get('GIT_INDEX_FILE')
    if index:
        # Native partial commits use next-index-* / index.lock, not the ordinary index.
        # Preserve that selection only in this worktree's actual Git directory.
        located = subprocess.run(['git', '-C', str(root), 'rev-parse', '--absolute-git-dir'],
                                 capture_output=True, env=env, timeout=30)
        if located.returncode:
            raise ValueError('无法定位当前工作树Git目录')
        git_dir = Path(os.fsdecode(located.stdout).strip()).resolve()
        candidate = Path(index)
        if not candidate.is_absolute():
            candidate = root / candidate
        if candidate.is_symlink() or candidate.resolve().parent != git_dir:
            raise ValueError('GIT_INDEX_FILE不属于当前工作树Git目录；不猜测或改用普通索引')
        env['GIT_INDEX_FILE'] = str(candidate.resolve())
    result = subprocess.run(['git', '--literal-pathspecs', '-C', str(root), *args],
                            capture_output=True, env=env, timeout=30)
    if check and result.returncode:
        raise ValueError(result.stderr.decode(errors='replace').strip() or 'Git读取失败')
    return result


def names(data):
    return set(os.fsdecode(name) for name in data.split(b'\0') if name)


def changed(root, source, base=None):
    actual = git(root, 'rev-parse', '--show-toplevel').stdout.decode().strip()
    if Path(actual).resolve() != root:
        raise ValueError('--root须为Git工作树根目录')
    revision = git(root, 'rev-parse', '--verify', '--end-of-options', (base or 'HEAD')+'^{commit}', check=False)
    if revision.returncode and base:
        raise ValueError('基线提交无法解析')
    fixed = revision.stdout.decode().strip() if revision.returncode == 0 else None
    comparison = (['--cached'] if source == 'index' else []) + ([fixed] if fixed else [])
    if source == 'worktree' and fixed is None:
        tracked = names(git(root, 'ls-files', '-z', '--cached').stdout)
    else:
        tracked = names(git(root, 'diff', '--name-only', '-z', '--no-renames', *comparison, '--').stdout)
    untracked = names(git(root, 'ls-files', '-z', '--others', '--exclude-standard').stdout) if source == 'worktree' else set()
    return fixed, comparison, tracked, untracked


def format_check(root, source, paths=(), excludes=(), reason=None, base=None):
    if excludes and not reason:
        raise ValueError('排除原始材料须提供--exclude-reason')
    paths, excludes = [relative(p) for p in paths], [relative(p) for p in excludes]
    fixed, comparison, tracked, untracked = changed(root, source, base)
    selected = {p for p in tracked | untracked if not paths or matches(p, paths)}
    excluded = sorted(p for p in selected if matches(p, excludes))
    selected -= set(excluded)
    errors = []
    # With no HEAD, every worktree file is new. Index diff already supports unborn HEAD.
    new = selected if source == 'worktree' and fixed is None else selected & untracked
    existing = sorted(selected - new)
    if existing:
        result = git(root, 'diff', '--no-ext-diff', '--no-textconv', '--check',
                     *comparison, '--', *existing, check=False)
        if result.returncode:
            if result.stderr or not result.stdout:
                raise ValueError(result.stderr.decode(errors='replace') or 'Git格式检查无法判定')
            errors.append(result.stdout.decode(errors='replace'))
    for name in sorted(new):
        path = root / name
        # New links are not ordinary file contents. Do not silently count them as checked.
        if path.is_symlink():
            raise ValueError('未跟踪符号链接的格式未判定，须核对链接对象或显式排除: ' + name)
        if not path.is_file():
            raise ValueError('待检查的新文件已变化或不可读取: ' + name)
        result = git(root, 'diff', '--no-ext-diff', '--no-textconv', '--no-index', '--check',
                     '--', '/dev/null', str(path), check=False)
        if result.stderr or result.returncode not in (0, 1, 2, 3):
            raise ValueError(result.stderr.decode(errors='replace') or '新文件格式检查无法判定: '+name)
        if result.returncode in (2, 3):
            if not result.stdout:
                raise ValueError('新文件格式检查无法判定: ' + name)
            errors.append(result.stdout.decode(errors='replace'))
    return {'status': 'failed' if errors else 'passed', 'source': source, 'base_commit': fixed,
            'files': sorted(selected), 'excluded': excluded, 'exclude_reason': reason,
            'diagnostics': errors, 'boundary': '仅核对所选Git对象的空白错误；不暂存、不修改文件，不证明语义或并发冻结。'}


def suggest(root, source, task=None, base=None):
    fixed, _, tracked, untracked = changed(root, source, base)
    config = json.loads((root/'.harness/project.json').read_text())
    if not isinstance(config, dict):
        raise ValueError('项目配置须为对象')
    rules = config.get('check_suggestions', [])
    if not isinstance(rules, list) or not isinstance(config.get('checks'), dict):
        raise ValueError('check_suggestions须为数组且checks须为对象')
    selected = None
    if task is not None:
        import harness as h
        try:
            h.identifier(task, 'task')
            selected = h.task_check_ids(h.read_task(root, task)[0])
        except h.HarnessError as exc:
            raise ValueError(str(exc)) from exc
    files = tracked | untracked
    matched, covered, proposed, missing = [], set(), set(), set()
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) - {'paths', 'checks', 'satisfied_by', 'reason'}:
            raise ValueError('建议映射包含无效字段')
        for key in ('paths', 'checks'):
            if not isinstance(rule.get(key), list) or not rule[key] or not all(isinstance(x, str) and x for x in rule[key]):
                raise ValueError('建议映射缺少非空'+key)
        alternatives = rule.get('satisfied_by', [])
        if not isinstance(alternatives, list) or not all(isinstance(x, str) for x in alternatives):
            raise ValueError('satisfied_by须为检查ID数组')
        if any(cid not in config['checks'] for cid in rule['checks'] + alternatives):
            raise ValueError('建议映射引用未知检查')
        if not isinstance(rule.get('reason'), str) or not rule['reason'].strip():
            raise ValueError('建议映射缺少reason')
        paths = [relative(p) for p in rule['paths']]
        affected = sorted(p for p in files if matches(p, paths))
        if affected:
            covered.update(affected); proposed.update(rule['checks'])
            absent = sorted(set(rule['checks']) - selected) if selected is not None and not selected.intersection(alternatives) else []
            missing.update(absent)
            matched.append({'files': affected, 'checks': rule['checks'], 'reason': rule['reason'],
                            'satisfied_by': alternatives, 'missing_checks': absent})
    return {'source': source, 'base_commit': fixed, 'task': task, 'files': sorted(files),
            'suggested_checks': sorted(proposed), 'missing_checks': sorted(missing),
            'unmapped': sorted(files-covered), 'matches': matched,
            'boundary': '只读建议，不执行检查或修改验收；未映射不等于无需验证，已有组合覆盖仅按显式satisfied_by判断。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('format', 'suggest'):
        p = sub.add_parser(name)
        p.add_argument('--root', required=True)
        p.add_argument('--source', choices=('worktree', 'index'), required=True)
        p.add_argument('--base', help='明确对照提交；默认HEAD，支持尚无提交的新仓库')
        if name == 'format':
            p.add_argument('--path', action='append', default=[])
            p.add_argument('--exclude', action='append', default=[])
            p.add_argument('--exclude-reason')
        else:
            p.add_argument('--task', help='可选比较原任务已选检查，不改任务')
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve(strict=True)
        result = (format_check(root, args.source, args.path, args.exclude, args.exclude_reason, args.base)
                  if args.command == 'format' else suggest(root, args.source, args.task, args.base))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('status') == 'failed' else 0
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'unknown', 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__': sys.exit(main())
