#!/usr/bin/env python3
"""Read-only closeout checks over explicitly selected original project sources."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

# Do not leave caches in a consumer project or an installed package.
sys.dont_write_bytecode = True
import harness as h


def verdict(status, **details):
    return {'status': status, **details}


def identity(status_path, text, task_path, prefixes):
    if task_path is None or not prefixes or any(not p.strip() for p in prefixes):
        return verdict('unknown', reason='缺少明确任务来源或当前入口前缀；不按任务编号猜测。')
    cleaned = h.markdown_structure(text, preserve_inline=True)
    # Reuse the common parser for both inline and single-line reference definitions.
    definitions = '\n'.join(line for line in cleaned.splitlines()
                            if re.match(r'^ {0,3}\[[^\]]+\]:', line))
    entries, missing, ambiguous = [], [], []
    for prefix in dict.fromkeys(prefixes):
        matches = [(i, line) for i, line in enumerate(cleaned.splitlines(), 1)
                   if line.lstrip().startswith(prefix)]
        if not matches:
            missing.append(prefix)
        for number, line in matches:
            targets = []
            for target, image in h.markdown_targets(line + '\n\n' + definitions):
                local = h.local_markdown_target(status_path, target)
                if not image and local is not None:
                    targets.append(local.resolve())
            if len(targets) != 1:
                ambiguous.append(number)
            else:
                entries.append({'line': number, 'matches_task': targets[0] == task_path.resolve()})
    if any(not entry['matches_task'] for entry in entries):
        return verdict('failed', entries=entries, missing_prefixes=missing, ambiguous_lines=ambiguous)
    return verdict('unknown' if missing or ambiguous else 'passed', entries=entries,
                   missing_prefixes=missing, ambiguous_lines=ambiguous)


def checklist(task_path, sections, claim):
    if task_path is None or not sections:
        return verdict('unknown', reason='未映射原始必需复选清单；由AI按原始依据核对，不补建状态台账。')
    opened, checked, unknown = [], [], []
    for section in dict.fromkeys(sections):
        try:
            body = h.rule_sections(task_path, [section]).decode('utf-8')
        except h.HarnessError as exc:
            unknown.append(str(exc))
            continue
        if re.search(r'^(?: {4,}|\t)[ \t]*(?:[-+*]|\d+[.)])\s+\[', body, re.M):
            unknown.append(f'{section}: 缩进复选项可能是嵌套义务或代码示例，须人工核对')
        found = False
        for line in h.markdown_structure(body, preserve_inline=True).splitlines():
            match = re.match(r'^\s*(?:[-+*]|\d+[.)])\s+\[([^\]]*)\][ \t]*(.*)$', line)
            if not match:
                continue
            found = True
            item = {'section': section, 'text': match[2]}
            if not match[2].strip():
                unknown.append(f'{section}: 复选项缺少对象')
            elif match[1] == ' ':
                opened.append(item)
            elif match[1] in ('x', 'X'):
                checked.append(item)
            else:
                unknown.append(f'{section}: 无法识别的复选状态 [{match[1]}]')
        if not found:
            unknown.append(f'{section}: 没有可识别的原始必需复选项')
    state = 'failed' if opened and claim == 'complete' else ('unknown' if unknown else 'passed')
    return verdict(state, claim=claim, open_items=opened, checked_items=checked, unknown=unknown,
                   boundary='只核对所选清单与拟声明的矛盾；勾选不证明实施或证据真实，清单覆盖及暂缓授权由AI核对。')


def inspect(args):
    root = Path(args.root).resolve(strict=True)
    h.require(root.is_dir(), '项目根必须为目录')
    status_path = h.safe(root, args.status)
    h.require(status_path.is_file(), '状态来源缺失或非文件')
    task_path = h.safe(root, args.task) if args.task else None
    if args.harness_task:
        h.require(not args.task and not args.required_section,
                  '--harness-task复用原任务，不与--task或--required-section混用')
        h.identifier(args.harness_task, 'harness task')
        task_path = h.task_path(root, args.harness_task)
    if task_path is not None:
        h.require(task_path.is_file(), '指定的原始任务来源不存在或非文件')
    sources = [status_path, *([task_path] if task_path else []),
               *(h.safe(root, path) for path in args.document)]
    snapshots, broken = {}, []
    for source in dict.fromkeys(sources):
        h.require(source.is_file(), f'来源不是文件: {source}')
        data = source.read_bytes()
        text = data.decode('utf-8')
        name = str(source.relative_to(root))
        snapshots[name] = hashlib.sha256(data).hexdigest()
        for target, _ in h.markdown_targets(text):
            try:
                local = h.local_markdown_target(source, target)
                if local is not None and not local.exists():
                    broken.append({'source': name, 'target': target, 'reason': '本地目标不存在'})
            except (h.HarnessError, OSError, ValueError) as exc:
                broken.append({'source': name, 'target': target, 'reason': str(exc)})
    checks = {'links': verdict('failed' if broken else 'passed', broken=broken),
              'identity': identity(status_path, status_path.read_text(), task_path, args.entry_prefix)}
    if args.harness_task:
        t, _ = h.read_task(root, args.harness_task)
        # This does not run checks or write close receipts/status. Existing evidence rules own the verdict.
        assessment = h.assess(root, h.config(root, h.task_check_ids(t)), t)
        checks['completion'] = verdict(
            'passed' if assessment['conditions_met'] or args.claim == 'partial' else 'failed',
            claim=args.claim, conditions_met=assessment['conditions_met'], gaps=assessment['gaps'],
            boundary='复用assess的当前证据判定；partial仅表示未声称完成，缺口仍保留。')
    else:
        checks['completion'] = checklist(task_path, args.required_section, args.claim)
    states = [check['status'] for check in checks.values()]
    state = 'failed' if 'failed' in states else ('unknown' if 'unknown' in states else 'passed')
    return {'mechanical_status': state, 'claim': args.claim, 'checks': checks, 'sources_sha256': snapshots,
            'semantic_review_required': True,
            'boundary': '只核对显式选择的来源/入口/必需项；不递归发现遗漏、解析任意状态文字或批准产品/发布。须从发现到处置/后续入口及从入口到原始依据双向核对。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--status', required=True, help='项目内原状态入口路径')
    parser.add_argument('--task', help='文档模式原任务路径；不要求特定文件名')
    parser.add_argument('--harness-task', help='脚本模式明确任务ID，复用只读assess')
    parser.add_argument('--entry-prefix', action='append', default=[], help='当前入口所在行的明确字面前缀，可重复；逐行核对唯一的本地链接')
    parser.add_argument('--required-section', action='append', default=[], help='文档模式已存在的必需复选清单标题，可重复；不包括暂缓/范围外清单')
    parser.add_argument('--document', action='append', default=[], help='额外核对本地链接的原始文档')
    parser.add_argument('--claim', choices=('complete', 'partial'), required=True, help='本次拟作出的声明；不从正文猜测')
    args = parser.parse_args()
    try:
        report = inspect(args)
    except (h.HarnessError, OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        report = {'mechanical_status': 'unknown', 'error': str(exc), 'semantic_review_required': True}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return {'passed': 0, 'failed': 1, 'unknown': 2}[report['mechanical_status']]


if __name__ == '__main__':
    sys.exit(main())
