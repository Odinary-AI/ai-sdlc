#!/usr/bin/env python3
"""Read-only checks for a deliberately small current-requirements trace table."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

# Do not leave caches in a consumer project or an installed package.
sys.dont_write_bytecode = True
import markdown_support as md


COLUMNS = ['ID', '当前要求', '设计/接口', '实现/方法', '代表验证']
ID_PATTERN = re.compile(r'[A-Z][A-Z0-9]*-\d{2,}\Z')
BOUNDARY = ('只核对所选表格中的稳定ID、本地链接、目标存在性及受限片段；'
            '不判断需求语义完整、链接关系正确或测试选择充分，也不执行测试。')


class TraceError(ValueError):
    """The selected source cannot be interpreted safely."""


def split_row(line):
    """Split a simple pipe-table row while preserving escaped pipes."""
    text = line.strip()
    if not text.startswith('|'):
        return None
    cells, current, escaped = [], [], False
    for char in text:
        if escaped:
            current.extend(('\\', char))
            escaped = False
        elif char == '\\':
            escaped = True
        elif char == '|':
            cells.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
    if escaped:
        current.append('\\')
    cells.append(''.join(current).strip())
    if len(cells) < 2 or cells[0] or cells[-1]:
        return None
    return cells[1:-1]


def divider(cells):
    return bool(cells) and all(re.fullmatch(r':?-{3,}:?', cell.replace(' ', ''))
                               for cell in cells)


def table_blocks(section_text):
    """Locate tables from masked structure but retain original cell contents."""
    original = section_text.splitlines()
    masked = md.markdown_structure(section_text, preserve_inline=True).splitlines()
    blocks, index = [], 0
    while index + 1 < len(original):
        header = split_row(masked[index])
        separator = split_row(masked[index + 1])
        if header is None or not divider(separator):
            index += 1
            continue
        end = index + 2
        invalid_rows = []
        while end < len(original):
            if split_row(masked[end]) is not None:
                end += 1
                continue
            if masked[end].lstrip().startswith('|'):
                # A damaged row is not a clean table boundary; keep later rows visible.
                invalid_rows.append(end + 1)
                end += 1
                continue
            break
        blocks.append({'header': split_row(masked[index]),
                       'separator': split_row(masked[index + 1]),
                       'rows': [(number + 1, split_row(masked[number]))
                                for number in range(index + 2, end)
                                if number + 1 not in invalid_rows],
                       'invalid_rows': invalid_rows,
                       'line': index + 1})
        index = end
    return blocks


def definitions(text):
    cleaned = md.markdown_structure(text, preserve_inline=True)
    return '\n'.join(line for line in cleaned.splitlines()
                     if re.match(r'^ {0,3}\[[^\]]+\]:', line))


def issue(items, reason, rid=None, relation=None):
    entry = {'reason': reason}
    if rid is not None:
        entry['requirement'] = rid
    if relation is not None:
        entry['relation'] = relation
    items.append(entry)


def inspect_link(source, root, target, relation, rid, violations, unknown):
    record = {'relation': relation, 'target': target}
    try:
        local = md.local_markdown_target(source, target)
        if local is None and not target.startswith('#'):
            issue(violations, '追踪关系只接受项目内本地Markdown链接', rid, relation)
            record['status'] = 'failed'
            return record
        resolved = (local or source).resolve()
        if not resolved.is_relative_to(root):
            issue(violations, '链接目标越过项目根边界', rid, relation)
            record['status'] = 'failed'
            return record
        record['target_path'] = resolved.relative_to(root).as_posix()
        if not resolved.exists():
            issue(violations, '本地链接目标不存在', rid, relation)
            record['status'] = 'failed'
            return record
        fragment = md.local_markdown_fragment(source, target, root=root, rule='simple-atx-v1')
        if fragment is not None:
            record['fragment'] = fragment
            if fragment['status'] == 'failed':
                issue(violations, '受限标题规则下片段不存在: ' + fragment.get('reason', ''), rid, relation)
            elif fragment['status'] == 'unknown':
                issue(unknown, '片段无法由受限规则判定: ' + fragment.get('reason', ''), rid, relation)
        record['status'] = fragment['status'] if fragment is not None else 'passed'
    except md.MarkdownError as exc:
        issue(violations, str(exc), rid, relation)
        record['status'] = 'failed'
    except (OSError, RuntimeError) as exc:
        issue(unknown, str(exc), rid, relation)
        record['status'] = 'unknown'
    return record


def inspect(args):
    root = Path(args.root).resolve(strict=True)
    if not root.is_dir():
        raise TraceError('项目根必须为目录')
    candidate = Path(args.source)
    source = (candidate if candidate.is_absolute() else root / candidate).resolve(strict=True)
    if not source.is_relative_to(root) or not source.is_file():
        raise TraceError('--source必须选择项目根内的普通文件')
    if not args.section.strip():
        raise TraceError('--section不能为空')

    source_data = source.read_bytes()
    section_data = md.rule_sections(source, [args.section])
    if source_data != source.read_bytes():
        raise TraceError('来源在读取期间变化，无法确定检查对象')
    text = source_data.decode('utf-8')
    section_text = section_data.decode('utf-8')
    blocks = table_blocks(section_text)
    violations, unknown, requirements, all_links = [], [], [], []

    if len(blocks) != 1:
        if len(blocks) > 1:
            issue(unknown, '所选章节含多张表，无法确定唯一追踪表')
        else:
            issue(violations, '所选章节缺少追踪表')
    else:
        block = blocks[0]
        if block['header'] != COLUMNS or len(block['separator']) != len(COLUMNS):
            issue(violations, '追踪表必须依次包含五列: ' + '、'.join(COLUMNS))
        for line in block['invalid_rows']:
            issue(violations, f'表格第{line}行格式不完整；后续合法行仍已检查')
        if not block['rows']:
            issue(violations, '追踪表至少需要一个当前能力或质量场景')
        seen = set()
        refs = definitions(text)
        for line, cells in block['rows']:
            rid = cells[0].strip() if cells else ''
            entry = {'id': rid, 'line': line, 'links': []}
            requirements.append(entry)
            if not ID_PATTERN.fullmatch(rid):
                issue(violations, 'ID须匹配[A-Z][A-Z0-9]*-后接至少两位数字', rid or None)
            if rid in seen:
                issue(violations, 'ID重复', rid)
            seen.add(rid)
            if len(cells) != len(COLUMNS):
                issue(violations, '数据行必须恰好包含五列', rid or None)
                continue
            for relation, cell in zip(COLUMNS[1:], cells[1:]):
                links = [(target, image) for target, image in
                         md.markdown_targets(cell + '\n\n' + refs) if not image]
                if not links:
                    issue(violations, '该关系至少需要一个本地Markdown链接', rid, relation)
                for target, _ in links:
                    record = inspect_link(source, root, target, relation, rid, violations, unknown)
                    entry['links'].append(record)
                    all_links.append(record)

    status = 'failed' if violations else ('unknown' if unknown else 'passed')
    return {
        'status': status,
        'source': source.relative_to(root).as_posix(),
        'source_sha256': hashlib.sha256(source_data).hexdigest(),
        'section': args.section,
        'requirement_count': len(requirements),
        'link_count': len(all_links),
        'requirements': requirements,
        'violations': violations,
        'unknown': unknown,
        'semantic_review_required': True,
        'tests_executed': False,
        'boundary': BOUNDARY,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--section', required=True)
    args = parser.parse_args(argv)
    try:
        result = inspect(args)
    except (OSError, UnicodeError, RuntimeError, md.MarkdownError, TraceError) as exc:
        result = {'status': 'unknown', 'source': args.source, 'section': args.section,
                  'requirement_count': 0, 'link_count': 0, 'unknown': [{'reason': str(exc)}],
                  'semantic_review_required': True, 'tests_executed': False, 'boundary': BOUNDARY}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return {'passed': 0, 'failed': 1, 'unknown': 2}[result['status']]


if __name__ == '__main__':
    sys.exit(main())
