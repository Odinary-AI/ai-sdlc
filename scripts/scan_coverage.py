#!/usr/bin/env python3
"""Check declared scan coverage, not the truth or quality of the investigation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

REFERENCES = Path(__file__).resolve().parents[1] / 'references'
SPECIALTIES = {
    'TR': 'terminology-review.md', 'DC': 'delivery-conformance.md',
    'DS': 'design-conformance.md', 'CH': 'code-health.md',
    'VH': 'validation-health.md', 'ER': 'experiment-review.md',
    'UX': 'ux-review.md', 'SC': 'security-review.md',
}
BASIC = {'TR', 'DC', 'DS', 'CH', 'VH'}
BLOCK = re.compile(r'^```harness-scan\s*\n(.*?)\n```\s*$', re.M | re.S)
MARKER = re.compile(r'^```harness-scan\b', re.M)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def catalog(references=REFERENCES):
    result = {}
    for key, name in SPECIALTIES.items():
        data = (references / name).read_bytes()
        ids = re.findall(r'^\| (' + key + r'-\d+)\b', data.decode('utf-8'), re.M)
        if not ids or len(ids) != len(set(ids)):
            raise ValueError(f'{name}: 条目目录为空或重复')
        result[key] = {'reference': name, 'ids': ids, 'sha256': sha(data)}
    return result


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f'重复字段: {key}')
        obj[key] = value
    return obj


def evaluate(root, task_path, references=REFERENCES):
    """Absence is compatible; the caller decides whether a scan was required."""
    root, task_path = Path(root).resolve(), Path(task_path).resolve()
    text = task_path.read_text(encoding='utf-8') if task_path.exists() else ''
    if not MARKER.search(text):
        return {'present': False, 'gaps': [], 'fingerprint': None}
    gaps, files, rules = [], {}, {}
    blocks = BLOCK.findall(text)
    identity = {'record': sha(text.encode()), 'files': files, 'rules': rules}
    result = {'present': True, 'gaps': gaps, 'fingerprint': identity,
              'note': '只核对声明覆盖、引用与结论一致性；不证明调查真实、依据充分或人工验收。'}

    def require(ok, message):
        if not ok:
            raise ValueError(message)

    def meaningful(value, label):
        require(isinstance(value, str) and bool(value.strip()) and '[待填写]' not in value,
                f'{label}: 缺少具体内容')

    def evidence(paths, label):
        require(isinstance(paths, list) and bool(paths), f'{label}: 缺少证据引用')
        for rel in paths:
            meaningful(rel, label)
            p = Path(rel)
            require(not p.is_absolute() and '..' not in p.parts, f'{label}: 证据路径越界 {rel}')
            try:
                target = (root / p).resolve()
            except RuntimeError as exc:
                raise ValueError(f'{label}: 证据路径无法解析 {rel}: {exc}') from exc
            require(target.is_relative_to(root) and target != task_path,
                    f'{label}: 证据越界或自引用 {rel}')
            require(target.is_file(), f'{label}: 证据文件不存在 {rel}')
            data = target.read_bytes()
            require(bool(data.strip()), f'{label}: 证据文件为空 {rel}')
            files[rel] = sha(data)

    try:
        require(len(blocks) == 1 and len(MARKER.findall(text)) == 1,
                '扫描任务必须有且仅有一个完整 harness-scan 块')
        record = json.loads(blocks[0], object_pairs_hook=unique_object)
        # Hash only scan content; lifecycle writes must not invalidate themselves.
        identity['record'] = sha(json.dumps(record, sort_keys=True, ensure_ascii=False).encode())
        require(isinstance(record, dict) and type(record.get('schema_version')) is int
                and record['schema_version'] == 1, '扫描记录需要 schema_version=1')
        meaningful(record.get('scope'), 'scope')
        require(record.get('level') in ('full', 'local'), 'level 必须为 full 或 local')
        require(record.get('claim') in ('scan_complete', 'healthy', 'partial'), 'claim 无效')
        selected = record.get('selection')
        require(isinstance(selected, dict) and bool(selected), 'selection 不能为空')
        require(set(selected) <= SPECIALTIES.keys(), 'selection 包含未知专项')
        directory = catalog(references)
        active, expected = set(), set()
        for key, choice in selected.items():
            require(isinstance(choice, dict) and type(choice.get('applicable')) is bool,
                    f'{key}: applicable 必须为布尔值')
            meaningful(choice.get('reason'), f'{key} 选择依据')
            rules[key] = directory[key]['sha256']
            if choice['applicable']:
                active.add(key)
                expected.update(directory[key]['ids'])
        require(bool(active), '至少选择一个适用专项')
        if record['level'] == 'full':
            require(set(selected) == set(SPECIALTIES), '完整扫描须判断全部八类专项')
            require(BASIC <= active, '完整扫描不能省略五类基础专项')
        items, findings = record.get('items'), record.get('findings', {})
        require(isinstance(items, dict), 'items 必须为按条目ID索引的对象')
        require(isinstance(findings, dict), 'findings 必须为按发现ID索引的对象')
        for missing in sorted(expected - items.keys()):
            gaps.append(f'{missing}: 必需条目未记录')
        additional = set()
        common = {iid for specialty in directory.values() for iid in specialty['ids']}
        for extra in sorted(items.keys() - expected):
            try:
                require(extra not in common, f'{extra}: 非所选专项的共同条目')
                item = items[extra]
                require(isinstance(item, dict) and item.get('additional') is True,
                        f'{extra}: 未知ID；项目附加项需显式additional=true')
                meaningful(item.get('basis'), f'{extra} 项目附加依据')
                additional.add(extra)
            except ValueError as exc:
                gaps.append(str(exc))
        used_findings = set()
        for iid in sorted((expected & items.keys()) | additional):
            try:
                item = items[iid]
                require(isinstance(item, dict), f'{iid}: 条目应为对象')
                require(iid not in common or not item.get('additional'), f'{iid}: 共同条目不能改为附加项')
                meaningful(item.get('coverage'), f'{iid} 检查对象与覆盖')
                status = item.get('status')
                require(status in ('ok', 'finding', 'not_applicable', 'incomplete'), f'{iid}: status 无效')
                if status == 'incomplete':
                    meaningful(item.get('reason'), f'{iid} 未完成原因')
                    meaningful(item.get('next_action'), f'{iid} 下一动作')
                    gaps.append(f'{iid}: 未完成，{item["reason"]}')
                elif status == 'not_applicable':
                    meaningful(item.get('reason'), f'{iid} 不适用依据')
                    if item.get('evidence'):
                        evidence(item['evidence'], iid)
                else:
                    evidence(item.get('evidence'), iid)
                links = item.get('findings', [])
                require(isinstance(links, list) and all(isinstance(x, str) for x in links),
                        f'{iid}: findings 必须为ID数组')
                require((status == 'finding') == bool(links), f'{iid}: 发现状态与关联ID不一致')
                used_findings.update(links)
                require(set(links) <= findings.keys(), f'{iid}: 引用了未记录的发现')
            except (ValueError, OSError) as exc:
                gaps.append(str(exc))
        for fid, finding in findings.items():
            try:
                require(fid in used_findings, f'{fid}: 发现没有关联条目')
                require(isinstance(finding, dict), f'{fid}: 发现应为对象')
                meaningful(finding.get('summary'), f'{fid} 事实与影响')
                require(finding.get('priority') in ('blocking', 'required', 'optional'), f'{fid}: priority 无效')
                require(finding.get('status') in ('open', 'resolved'), f'{fid}: status 无效')
                if finding['status'] == 'open':
                    meaningful(finding.get('owner'), f'{fid} 后续归属')
                    meaningful(finding.get('next_action'), f'{fid} 后续动作')
                    if record['claim'] == 'healthy' and finding['priority'] != 'optional':
                        gaps.append(f'{fid}: 必需问题未处理，不能声明健康通过')
                else:
                    evidence(finding.get('resolution_evidence'), f'{fid} 修复复验证据')
            except (ValueError, OSError) as exc:
                gaps.append(str(exc))
        if record['claim'] == 'partial':
            gaps.append('当前只交付部分扫描结果，保留任务未完成')
    except (ValueError, OSError, TypeError) as exc:
        gaps.append(str(exc))
    result['conditions_met'] = not gaps
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', default='.')
    p.add_argument('--catalog', action='store_true', help='读取当前八类专项的条目ID')
    p.add_argument('task', nargs='?', help='项目内任务Markdown相对路径')
    args = p.parse_args()
    try:
        if args.catalog:
            result, code = catalog(), 0
        else:
            root = Path(args.root).resolve()
            if not args.task:
                p.error('需要 task 或 --catalog')
            path = (root / args.task).resolve()
            if Path(args.task).is_absolute() or not path.is_relative_to(root):
                raise ValueError('任务路径超出项目')
            result = evaluate(root, path)
            if not result['present']:
                raise ValueError('指定扫描任务没有 harness-scan 块')
            code = 0 if result['conditions_met'] else 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
