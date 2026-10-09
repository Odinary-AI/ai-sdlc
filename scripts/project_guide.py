#!/usr/bin/env python3
"""Optional local guide renderer and authored-relation reader; Python stdlib only."""
import argparse
import datetime
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata
from urllib.parse import quote, urlsplit

PACKAGE = Path(__file__).resolve().parents[1]
SHELL = PACKAGE / 'assets/project-guide.html'
ID = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{0,79}$')
ALLOWED = set('p a b strong em i code pre br hr div span h3 h4 h5 h6 ul ol li '
              'table thead tbody tr th td details summary figure figcaption '
              'svg title desc defs marker path g rect text tspan line polyline polygon circle '
              'button noscript footer section'.split())
ATTRS = set('id class role title href target rel aria-label aria-labelledby aria-describedby '
            'aria-controls aria-pressed aria-live aria-atomic tabindex type viewbox '
            'width height x y x1 y1 x2 y2 rx ry cx cy r d points fill stroke stroke-width '
            'marker-end markerwidth markerheight refx refy orient text-anchor font-size '
            'xmlns preserveaspectratio open'.split())


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def local_path(root, value):
    p = Path(value)
    if p.is_absolute() or '..' in p.parts or not p.parts:
        raise ValueError('来源必须是项目根内相对路径: ' + str(value))
    resolved = (root / p).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError('来源缺失或越界: ' + str(value))
    if resolved.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('来源超过16MiB核对上限: ' + str(value))
    return resolved


def safe_url(value):
    parts = urlsplit(value)
    if parts.scheme.lower() not in ('', 'https', 'http', 'mailto') or value.startswith('//'):
        raise ValueError('不支持的链接: ' + value)
    return value


class TrustedMarkup(HTMLParser):
    """A small presentation vocabulary, never scripts, event handlers or embeds."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED:
            raise ValueError('不支持的HTML元素: ' + tag)
        for key, value in attrs:
            if key not in ATTRS and not key.startswith('data-'):
                raise ValueError('不支持的HTML属性: ' + key)
            if key == 'href':
                safe_url(value or '')
            if value and 'url(' in value.lower() and not re.fullmatch(r'url\(#[a-zA-Z][a-zA-Z0-9_-]*\)', value):
                raise ValueError('展示属性不能加载外部URL')
        # Preserve the authored casing of SVG attributes (viewBox/refX etc.).
        self.parts.append(self.get_starttag_text())
        if tag not in ('br', 'hr'):
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in ('br', 'hr'):
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag not in ALLOWED:
            raise ValueError('不支持的HTML元素: ' + tag)
        if not self.stack or self.stack.pop() != tag:
            raise ValueError('HTML闭合关系不一致: ' + tag)
        self.parts.append('</' + tag + '>')

    def handle_data(self, data):
        self.parts.append(html.escape(data))

    def handle_entityref(self, name):
        self.parts.append('&' + name + ';')

    def handle_charref(self, name):
        self.parts.append('&#' + name + ';')

    def handle_comment(self, data):
        self.parts.append('<!--' + data + '-->')


def inline(text):
    parts, cursor = [], 0
    for match in re.finditer(r'\[([^\]]+)\]\(([^\s)]+)\)', text):
        parts.append(html.escape(text[cursor:match.start()]))
        target = safe_url(match.group(2))
        parts.append('<a href="' + html.escape(target, quote=True) + '">' + html.escape(match.group(1)) + '</a>')
        cursor = match.end()
    parts.append(html.escape(text[cursor:]))
    return ''.join(parts)


def require_text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('缺少非空文字: ' + where)
    return value


def read_source(root, value, manifest, output):
    p = local_path(root, value)
    if p == output or (output.exists() and os.path.samefile(p, output)):
        raise ValueError('输出不能作为自身输入: ' + value)
    data = p.read_bytes()
    manifest[value] = digest(data)
    return p, data


def parse_graph(value, root, manifest, output):
    if not isinstance(value, dict) or value.get('kind') not in ('collaboration', 'architecture', 'workflow', 'dataflow', 'lifecycle'):
        raise ValueError('engineering-map需要合法kind及对象结构')
    nodes, edges = value.get('nodes'), value.get('edges')
    if not isinstance(nodes, list) or not nodes or len(nodes) > 200 or not isinstance(edges, list) or len(edges) > 1000:
        raise ValueError('关系图需要1–200节点和0–1000关系')
    require_text(value.get('title'), 'map.title')
    ids, sources = set(), {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get('id'), str) or not ID.fullmatch(node['id']) or node['id'] in ids:
            raise ValueError('节点ID非法或重复')
        ids.add(node['id'])
        require_text(node.get('label'), 'node.label')
        if node.get('basis', 'observed') not in ('observed', 'inferred', 'unknown'):
            raise ValueError('basis必须为observed/inferred/unknown')
        for field in ('description', 'summary'):
            if field in node and not isinstance(node[field], str):
                raise ValueError('节点'+field+'必须为文字')
        refs = node.get('sources', [])
        if not isinstance(refs, list):
            raise ValueError('sources必须为数组')
        resolved = []
        for source in refs:
            if not isinstance(source, dict):
                raise ValueError('来源必须为对象')
            name = require_text(source.get('path'), 'source.path')
            p, data = read_source(root, name, manifest, output)
            start, end = source.get('line'), source.get('end_line', source.get('line'))
            if start is not None and (type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(data.decode('utf-8').splitlines())):
                raise ValueError('来源行号越界: ' + name)
            if start is None and end is not None:
                raise ValueError('end_line需要line')
            href = quote(os.path.relpath(p, output.parent), safe='/')
            resolved.append({'path': name, 'href': href, 'sha256': manifest[name],
                             **({'line': start, 'end_line': end} if start is not None else {})})
        sources[node['id']] = resolved
    positions = []
    for i, node in enumerate(nodes):
        pos = node.get('position', {'column': i % 3, 'row': i // 3})
        if not isinstance(pos, dict) or any(type(pos.get(key)) is not int or not 0 <= pos[key] <= 100 for key in ('column', 'row')):
            raise ValueError('节点position需要0–100整数column/row')
        cell = (pos['column'], pos['row'])
        if cell in positions:
            raise ValueError('节点布局位置重叠')
        positions.append(cell)
        if node.get('role', 'component') not in ('component', 'actor', 'rule', 'template', 'core', 'data', 'helper', 'process', 'optional', 'result'):
            raise ValueError('节点role非法')
    groups = value.get('groups', [])
    if not isinstance(groups, list):
        raise ValueError('groups必须为数组')
    group_ids, members = set(), set()
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get('id'), str) or not ID.fullmatch(group['id']) or group['id'] in group_ids:
            raise ValueError('分组ID非法或重复')
        group_ids.add(group['id']); require_text(group.get('label'), 'group.label')
        listed = group.get('members')
        if not isinstance(listed, list) or not listed or any(member not in ids or member in members for member in listed) or len(set(listed)) != len(listed):
            raise ValueError('分组成员缺失、重复或跨组重叠')
        members.update(listed)
    for edge in edges:
        if not isinstance(edge, dict) or edge.get('from') not in ids or edge.get('to') not in ids:
            raise ValueError('关系端点不存在')
        require_text(edge.get('label'), 'edge.label')
        if edge.get('category', 'primary') not in ('primary', 'conditional', 'optional', 'feedback', 'reference'):
            raise ValueError('关系category非法')
        if 'short_label' in edge:
            require_text(edge['short_label'], 'edge.short_label')
        if edge.get('basis', 'observed') not in ('observed', 'inferred', 'unknown'):
            raise ValueError('关系basis非法')
    return {**value, 'sources': sources}


def text_width(text, size=14):
    return sum(1 if unicodedata.east_asian_width(c) in ('W', 'F') else .57 for c in text) * size


def wrapped(label, limit=14):
    lines, line = [], ''
    for token in re.findall(r'[A-Za-z0-9_]+|.', label):
        if text_width(token, 1) > limit:
            tokens = list(token)
        else:
            tokens = [token]
        for part in tokens:
            if line and text_width(line + part, 1) > limit:
                lines.append(line); line = ''
            line += part
    if line:
        lines.append(line)
    return lines or ['']


def intersects(a, b, pad=0):
    return a[0] < b[0]+b[2]+pad and a[0]+a[2]+pad > b[0] and a[1] < b[1]+b[3]+pad and a[1]+a[3]+pad > b[1]


def graph_html(graph, index):
    nodes, edges = graph['nodes'], graph['edges']
    cells = {node['id']: node.get('position', {'column': i % 3, 'row': i // 3}) for i, node in enumerate(nodes)}
    positions = {key: (40 + pos['column'] * 310, 60 + pos['row'] * 195) for key, pos in cells.items()}
    width = max(x for x,y in positions.values()) + 330
    height = max(y for x,y in positions.values()) + 160
    rectangles = {key: (x,y,250,112) for key,(x,y) in positions.items()}
    incoming = {node['id']: [i for i,e in enumerate(edges) if e['to']==node['id']] for node in nodes}
    outgoing = {node['id']: [i for i,e in enumerate(edges) if e['from']==node['id']] for node in nodes}
    kind = graph['kind']
    title_id = ('collaboration-title' if kind == 'collaboration' else 'architecture-title' if kind == 'architecture' else 'map-title') + '-' + str(index)
    parts = ['<figure class="map" data-map="' + str(index) + '"><figcaption id="' + title_id + '">' + html.escape(graph['title']) + '</figcaption>',
             '<p class="map-hint">选择节点查看详情；聚焦仅沿已列关系。实线为主要关系，虚线为条件关系或反馈，点线为引用；是否必须依文字条件判断，推断/待核实另有文字标记。</p>',
             '<div class="map-controls"><label>查找节点 <input type="search" aria-label="查找图中节点" data-search></label>'
             '<button type="button" data-direction="all">全图</button><button type="button" data-direction="upstream">上游</button><button type="button" data-direction="downstream">下游</button>'
             '<label>路径终点 <select data-route-target aria-label="选择路径终点"><option value="">请选择</option>' +
             ''.join('<option value="' + node['id'] + '">' + html.escape(node['label']) + '</option>' for node in nodes) +
             '</select></label><button type="button" data-route>显示路径</button></div>',
             '<p class="map-hint search-summary" role="status">未筛选节点。</p>',
             '<div class="map-scroll"><svg viewBox="0 0 ' + str(width) + ' ' + str(height) + '" role="group" aria-labelledby="' + title_id + '">',
             '<defs><marker id="arrow-' + str(index) + '" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="currentColor"/></marker></defs>']
    occupied = list(rectangles.values())
    for group in graph.get('groups', []):
        members = [rectangles[key] for key in group['members']]
        x,y = min(r[0] for r in members)-18, min(r[1] for r in members)-35
        right,bottom = max(r[0]+r[2] for r in members)+18, max(r[1]+r[3] for r in members)+18
        bounds = (x,y,right-x,bottom-y)
        if any(key not in group['members'] and intersects(bounds,rect) for key,rect in rectangles.items()):
            raise ValueError('分组边界包含非成员节点，调整布局或分组')
        occupied.append((x,y,right-x,26))
        parts.append(f'<g class="map-group"><rect x="{x}" y="{y}" width="{right-x}" height="{bottom-y}" rx="12"/><text x="{x+14}" y="{y+22}">' + html.escape(group['label']) + '</text></g>')
    label_boxes = []
    for i, edge in enumerate(edges):
        x1,y1 = positions[edge['from']]; x2,y2 = positions[edge['to']]
        out_port = 22 + 206*(outgoing[edge['from']].index(i)+1)/(len(outgoing[edge['from']])+1)
        in_port = 22 + 206*(incoming[edge['to']].index(i)+1)/(len(incoming[edge['to']])+1)
        if y1 == y2:
            start=(x1+(250 if x2>x1 else 0),y1+56); end=(x2+(0 if x2>x1 else 250),y2+56)
            points=[start,end]
            if abs(x2-x1)>310:
                points=[(x1+out_port,y1),(x1+out_port,y1-22-i%2*8),(x2+in_port,y1-22-i%2*8),(x2+in_port,y2)]
        else:
            down=y2>y1
            start=(x1+out_port,y1+(112 if down else 0)); end=(x2+in_port,y2+(0 if down else 112))
            middle=(start[1]+end[1])/2
            points=[start,(start[0],middle),(end[0],middle),end]
            obstacles=[r for key,r in rectangles.items() if key not in (edge['from'],edge['to'])]
            blocked=any(intersects((min(a[0],b[0]),min(a[1],b[1]),max(abs(a[0]-b[0]),1),max(abs(a[1]-b[1]),1)),r,8) for a,b in zip(points,points[1:]) for r in obstacles)
            if blocked or edge.get('category')=='feedback':
                gap1=start[1]+(24 if down else -24); gap2=end[1]+(-24 if down else 24)
                points=[start,(start[0],gap1),(width-22-i%3*8,gap1),(width-22-i%3*8,gap2),(end[0],gap2),end]
        if edge.get('category')=='feedback' and edge['from']!=edge['to']:
            start=(x1+out_port,y1+112)
            if x2==40:
                points=[start,(start[0],start[1]+22),(18,start[1]+22),(18,y2+56),(x2,y2+56)]
            else:
                points=[start,(start[0],start[1]+22),(18,start[1]+22),(18,14),(x2+in_port,14),(x2+in_port,y2)]
        if edge['from']==edge['to']:
            points=[(x1+250,y1+56),(x1+276,y1+56),(x1+276,y1-22),(x1+out_port,y1-22),(x1+out_port,y1)]
        route='M'+ 'L'.join(f'{x:.1f} {y:.1f}' for x,y in points)
        category=edge.get('category','primary')
        uncertain=edge.get('basis','observed')!='observed'
        parts.append('<path class="edge ' + category + (' uncertain' if uncertain else '') + '" data-edge="' + str(i) + '" d="' + route + '" marker-end="url(#arrow-' + str(index) + ')"><title>' + html.escape(edge['label']) + '</title></path>')
        label=edge.get('short_label',edge['label']) + (' · 推断/待核实' if uncertain else '')
        lw=min(text_width(label,12)+16,250); lh=24
        segments=sorted(zip(points,points[1:]),key=lambda s:abs(s[0][0]-s[1][0])+abs(s[0][1]-s[1][1]),reverse=True)
        location=None
        for a,b in segments:
            for fraction in (.5,.3,.7):
                cx=a[0]+(b[0]-a[0])*fraction; cy=a[1]+(b[1]-a[1])*fraction
                for dx,dy in ((0,-17),(0,17),(-lw/2-8,0),(lw/2+8,0)):
                    box=(cx+dx-lw/2,cy+dy-lh/2,lw,lh)
                    if box[0]>=10 and box[1]>=10 and box[0]+lw<=width-10 and box[1]+lh<=height-10 and not any(intersects(box,r,4) for r in occupied+label_boxes):
                        location=box;break
                if location:break
            if location:break
        if location:
            label_boxes.append(location); x,y,lw,lh=location
            parts.append(f'<g class="edge-label" data-for-edge="{i}"><rect x="{x:.1f}" y="{y:.1f}" width="{lw:.1f}" height="{lh}" rx="4"/><text x="{x+lw/2:.1f}" y="{y+16:.1f}" text-anchor="middle">' + html.escape(label) + '</text></g>')
    role_names={'component':'组件','actor':'参与者','rule':'规则依据','template':'模板资源','core':'执行核心','data':'项目数据','helper':'辅助工具','process':'处理步骤','optional':'可选能力','result':'结果与审阅'}
    for node in nodes:
        x,y=positions[node['id']]; role=node.get('role','component'); refs=graph['sources'][node['id']]
        parts.append('<g class="node ' + role + '" role="button" tabindex="0" aria-label="' + html.escape(node['label'],quote=True) + '" data-node="' + node['id'] + f'"><rect x="{x}" y="{y}" width="250" height="112" rx="9"/><text class="node-role" x="{x+16}" y="{y+22}">' + role_names[role] + '</text>')
        title_lines=wrapped(node['label'])
        for j,line in enumerate(title_lines[:2]):
            if j==1 and len(title_lines)>2:
                line=line[:-1]+'…'
            parts.append(f'<text class="node-title" x="{x+16}" y="{y+48+j*22}">' + html.escape(line) + '</text>')
        summary=str(node.get('summary',''))
        if summary:
            parts.append(f'<text class="node-summary" x="{x+16}" y="{y+87}">' + html.escape(wrapped(summary,17)[0] + ('…' if len(wrapped(summary,17))>1 else '')) + '</text>')
        basis=node.get('basis','observed'); badge='来源 '+str(len(refs)) if basis=='observed' else {'inferred':'推断','unknown':'待核实'}[basis]
        parts.append(f'<text class="basis" x="{x+233}" y="{y+23}" text-anchor="end">' + badge + '</text></g>')
    parts.append('</svg></div><p class="map-hint">图中短标签用于快速阅读；完整关系、条件和来源见节点详情或下方列表。</p><div class="node-detail" aria-live="polite"><p>选择节点查看完整说明、关系及来源。</p></div>')
    parts.append('<details><summary>全部节点、关系及来源</summary>')
    for node in nodes:
        parts.append('<h4>'+html.escape(node['label'])+'</h4><p>'+html.escape(node.get('summary',''))+'</p><p>'+html.escape(str(node.get('description','')))+'</p>')
        for ref in graph['sources'][node['id']]:
            parts.append('<p><a href="'+ref['href']+'">'+html.escape(ref['path'])+'</a>'+(' · 行 '+str(ref['line'])+'–'+str(ref['end_line']) if 'line' in ref else '')+'</p>')
    parts.append('<ul>'+''.join('<li>'+html.escape(edge['from']+' → '+edge['to']+'：'+edge['label'])+('（推断/待核实）' if edge.get('basis','observed')!='observed' else '')+'</li>' for edge in edges)+'</ul></details></figure>')
    return '\n'.join(parts)


def render(root, source, output):
    source_path = local_path(root, source)
    for protected in (Path(__file__).resolve(), SHELL.resolve()):
        if output == protected or (output.exists() and os.path.samefile(output, protected)):
            raise ValueError('输出不能覆盖生成器或展示资产')
    if source_path == output or (output.exists() and os.path.samefile(source_path, output)):
        raise ValueError('输出不能覆盖内容源')
    raw = source_path.read_text(encoding='utf-8')
    meta_match = re.match(r'<!-- guide-meta\s*\n(.*?)\n-->\s*\n', raw, re.S)
    if not meta_match:
        raise ValueError('缺少guide-meta快照身份')
    meta = json.loads(meta_match.group(1))
    if not isinstance(meta, dict):
        raise ValueError('guide-meta必须为对象')
    for key in ('date', 'version', 'identity', 'scope', 'title'):
        require_text(meta.get(key), 'guide-meta.' + key)
    datetime.date.fromisoformat(meta['date'])
    if any(re.fullmatch(r'\[.*\]', meta[key]) for key in ('version', 'identity', 'scope', 'title')):
        raise ValueError('guide-meta仍有未填写模板字段')
    if not isinstance(meta.get('sources', []), list):
        raise ValueError('guide-meta.sources必须为数组')
    manifest = {source: digest(raw.encode('utf-8')), '$renderer': digest(Path(__file__).read_bytes()), '$shell': digest(SHELL.read_bytes())}
    for ref in meta.get('sources', []):
        read_source(root, require_text(ref, 'guide-meta.sources'), manifest, output)
    body, nav, graphs, headings = [], [], [], set()
    lines = raw[meta_match.end():].splitlines()
    i, title_count, section = 0, 0, False
    while i < len(lines):
        line = lines[i]; i += 1
        if line.startswith('```'):
            language = line[3:].strip(); block = []
            while i < len(lines) and lines[i] != '```':
                block.append(lines[i]); i += 1
            if i == len(lines):
                raise ValueError('围栏未关闭')
            i += 1
            value = '\n'.join(block)
            if language == 'engineering-map':
                graph = parse_graph(json.loads(value), root, manifest, output)
                graphs.append(graph); body.append(graph_html(graph, len(graphs)-1))
            elif language == 'html':
                parser = TrustedMarkup(); parser.feed(value); parser.close()
                if parser.stack:
                    raise ValueError('HTML元素未关闭')
                body.append(''.join(parser.parts))
            else:
                body.append('<pre><code>' + html.escape(value) + '</code></pre>')
        elif line.startswith('# '):
            title_count += 1
            if title_count != 1 or nav:
                raise ValueError('主标题必须唯一并位于板块之前')
        elif line.startswith('## '):
            match = re.fullmatch(r'## (.+?)(?: \{#([a-zA-Z][a-zA-Z0-9_-]*)\})?', line)
            title, identity = match.groups(); identity = identity or 'section-' + str(len(nav)+1)
            if identity in headings:
                raise ValueError('板块ID重复')
            headings.add(identity)
            if section:
                body.append('</section>')
            section = True
            nav.append('<a href="#' + identity + '">' + html.escape(title.split('｜')[0]) + '</a>')
            body.append('<section id="' + identity + '"><h2>' + html.escape(title) + '</h2>')
        elif line.startswith('### '):
            body.append('<h3>' + html.escape(line[4:]) + '</h3>')
        elif line.startswith('- '):
            body.append('<ul><li>' + inline(line[2:]) + '</li></ul>')
        elif line.strip() and line != '---':
            body.append('<p>' + inline(line) + '</p>')
    if title_count != 1 or not nav:
        raise ValueError('需要唯一主标题和内容板块')
    if section:
        body.append('</section>')
    kinds = {graph['kind'] for graph in graphs}
    # Legacy authored SVG remains supported; newly authored maps use their kinds.
    content = '\n'.join(body)
    required = meta.get('required_views', ['collaboration', 'architecture'])
    if not isinstance(required, list) or any(kind not in ('collaboration', 'architecture', 'workflow', 'dataflow', 'lifecycle') for kind in required):
        raise ValueError('required_views非法')
    if not {'collaboration', 'architecture'}.issubset(set(required)):
        raise ValueError('工程导览不能省略使用/协作与内部架构基础视角')
    for kind in required:
        legacy = {'collaboration': 'collaboration-title', 'architecture': 'architecture-title'}.get(kind)
        if kind not in kinds and not (legacy and 'id="' + legacy + '"' in content):
            raise ValueError('缺少基础图解源: ' + kind)
    payload = packed({'graphs': graphs, 'inputs': manifest}).replace('<', '\\u003c').replace('&', '\\u0026')
    values = {'TITLE': html.escape(meta['title']), 'SNAPSHOT': html.escape(meta['date'] + ' · ' + meta['version'] + ' · ' + meta['identity']),
              'SCOPE': html.escape(meta['scope']), 'NAV': ''.join(nav), 'CONTENT': content, 'DATA': payload}
    shell = SHELL.read_text(encoding='utf-8')
    result = re.sub(r'\{\{([A-Z]+)\}\}', lambda match: values[match.group(1)], shell)
    return result, graphs, manifest


def reachable(graph, seed, direction):
    if seed not in {node['id'] for node in graph['nodes']}:
        raise ValueError('节点不存在: ' + seed)
    visited, queue = {seed}, [seed]
    while queue:
        current = queue.pop(0)
        for edge in graph['edges']:
            a, b = (edge['to'], edge['from']) if direction == 'upstream' else (edge['from'], edge['to'])
            if a == current and b not in visited:
                visited.add(b); queue.append(b)
    return visited


def authored_path(graph, seed, target):
    ids = {node['id'] for node in graph['nodes']}
    if seed not in ids or target not in ids:
        raise ValueError('路径节点不存在')
    queue, seen = [(seed, [seed], [])], {seed}
    while queue:
        current, nodes, edges = queue.pop(0)
        if current == target:
            return nodes, edges
        for index, edge in enumerate(graph['edges']):
            if edge['from'] == current and edge['to'] not in seen:
                seen.add(edge['to'])
                queue.append((edge['to'], nodes + [edge['to']], edges + [index]))
    return None, []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'check', 'inspect'])
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--source', default='docs/project-guide.md')
    parser.add_argument('--output', default='docs/project-guide.html')
    parser.add_argument('--node')
    parser.add_argument('--target', help='只读查询到该节点的已列有向路径')
    parser.add_argument('--view', type=int, default=0)
    parser.add_argument('--direction', choices=['upstream', 'downstream'], default='downstream')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    output_arg = Path(args.output)
    if output_arg.suffix.lower() not in ('.html', '.htm'):
        raise ValueError('展示输出必须为.html或.htm文件')
    if output_arg.is_absolute() or '..' in output_arg.parts:
        raise ValueError('输出必须位于项目根内')
    output_raw = root / output_arg; output = output_raw.resolve()
    if output_raw.is_symlink() or not output.is_relative_to(root):
        raise ValueError('输出不能为符号链接或越界')
    result, graphs, manifest = render(root, args.source, output)
    if args.action == 'inspect':
        if not args.node or not 0 <= args.view < len(graphs):
            raise ValueError('inspect需要合法view和node')
        graph = graphs[args.view]
        path_nodes, path_edges = None, []
        if args.target:
            if args.direction != 'downstream':
                raise ValueError('target路径查询沿from→to，不与upstream组合')
            path_nodes, path_edges = authored_path(graph, args.node, args.target)
            found = set(path_nodes or [])
        else:
            found = reachable(graph, args.node, args.direction)
        print(packed({'direction': args.direction, **({'path': path_nodes} if args.target else {}), 'nodes': [node for node in graph['nodes'] if node['id'] in found],
                      'edges': [edge for index, edge in enumerate(graph['edges']) if (index in path_edges if args.target else edge['from'] in found and edge['to'] in found)],
                      'sources': {key: value for key, value in graph['sources'].items() if key in found},
                      'boundary': '仅本图已有关系及明确来源；不是完整运行影响或验收判定。'}))
    elif args.action == 'check':
        if not output.is_file() or output.read_text(encoding='utf-8') != result:
            raise ValueError('导览与当前源、明确来源身份或展示工具不一致；核对变化后重新生成')
        print('同源导览及明确来源身份一致；不代替关系语义、浏览器或验收核对。')
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.' + output.name + '-', dir=output.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(result)
            os.replace(temporary, output)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        print('已生成同源工程导览: ' + str(output))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SystemExit(str(exc))
