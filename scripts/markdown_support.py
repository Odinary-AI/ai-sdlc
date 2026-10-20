"""Shared Markdown inspection helpers; no project state or execution dependencies."""
import html
import re
from urllib.parse import unquote, urlsplit


class MarkdownError(ValueError):
    """A requested Markdown target or section cannot be interpreted safely."""


def _require(condition, message):
    if not condition:
        raise MarkdownError(message)


def blank_markdown(value):
    return re.sub(r'[^\n]', ' ', value)


def markdown_structure(text, preserve_inline=False):
    """Mask examples/comments without letting their literals consume real text."""

    # Exclusions share source order: fences in comments and comments in code
    # cannot consume real Markdown following the enclosing construct.
    body = text
    cleaned, i = [], 0
    while i < len(body):
        if i == 0 or body[i-1] == '\n':
            line_end = body.find('\n', i)
            line_end = len(body) if line_end < 0 else line_end + 1
            line = body[i:line_end]
            marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line.rstrip('\r\n'))
            if marker and not (marker[1][0] == '`' and '`' in marker[2]):
                closing = re.compile(r'^ {0,3}' + re.escape(marker[1][0]) +
                                     '{' + str(len(marker[1])) + r',}[ \t]*\r?$', re.M)
                close = closing.search(body, line_end)
                end = close.end() if close else len(body)
                cleaned.append(blank_markdown(body[i:end])); i = end
                continue
            if line.startswith(('    ', '\t')):
                cleaned.append(blank_markdown(line)); i = line_end
                continue
        if body[i] == '\\' and i + 1 < len(body):
            cleaned.append(body[i:i+2]); i += 2
        elif body.startswith('<!--', i):
            end = body.find('-->', i + 4)
            end = len(body) if end < 0 else end + 3
            cleaned.append(blank_markdown(body[i:end])); i = end
        elif body[i] == '`':
            run = re.match(r'`+', body[i:])[0]
            close = re.search(r'(?<!`)' + run + r'(?!`)', body[i+len(run):])
            end = i + len(run) + close.end() if close else i + len(run)
            literal = body[i:end]
            keep = not close or (preserve_inline and '\n' not in literal)
            cleaned.append(literal if keep else blank_markdown(literal)); i = end
        else:
            cleaned.append(body[i]); i += 1
    return ''.join(cleaned)


def markdown_targets(text):
    """Extract common Markdown destinations and image flags, not render Markdown."""
    body = markdown_structure(text)

    def unescape(value):
        return html.unescape(re.sub(r'\\([!"#$%&\'()*+,\-./:;<=>?@\[\]\\^_`{|}~])', r'\1', value))

    def label(value):
        return ' '.join(value.split()).casefold()

    def destination(value, start, inline):
        """Return a raw destination and the first character after its suffix."""
        pos = start
        while pos < len(value) and value[pos].isspace(): pos += 1
        begin = pos
        if pos < len(value) and value[pos] == '<':
            pos += 1; begin = pos
            while pos < len(value) and value[pos] != '>':
                if value[pos] in '\n<': return None
                pos += 2 if value[pos] == '\\' and pos + 1 < len(value) else 1
            if pos >= len(value): return None
            raw = value[begin:pos]; pos += 1
        else:
            depth = 0
            while pos < len(value):
                char = value[pos]
                if char == '\\' and pos + 1 < len(value):
                    pos += 2; continue
                if char.isspace() or (char == ')' and depth == 0): break
                if char == '<': return None
                if char == '(': depth += 1
                if char == ')': depth -= 1
                pos += 1
            if depth: return None
            raw = value[begin:pos]
        space = pos
        while pos < len(value) and value[pos].isspace(): pos += 1
        if pos > space and pos < len(value) and value[pos] in '\"\'(':
            delimiter = ')' if value[pos] == '(' else value[pos]
            pos += 1
            while pos < len(value) and value[pos] != delimiter:
                pos += 2 if value[pos] == '\\' and pos + 1 < len(value) else 1
            if pos >= len(value): return None
            pos += 1
            while pos < len(value) and value[pos].isspace(): pos += 1
        if re.search(r'\n[ \t]*\n', value[start:pos]): return None
        if inline:
            return (unescape(raw), pos + 1) if pos < len(value) and value[pos] == ')' else None
        return (unescape(raw), pos) if raw and pos == len(value) else None

    definitions = {}
    pattern = r'^ {0,3}\[([^\]\n]+)\]:[ \t]*(.*)$'
    def definition(match):
        parsed = destination(match[2], 0, False)
        if parsed:
            definitions.setdefault(label(match[1]), parsed[0])
            return blank_markdown(match[0])
        return match[0]
    body = re.sub(pattern, definition, body, flags=re.M)
    def scan(body):
        targets, i = [], 0
        while i < len(body):
            if body[i] == '\\':
                i += 2; continue
            is_image = body.startswith('![', i)
            start = i + 1 if is_image else i
            if body[start] != '[':
                i += 1; continue
            pos, depth = start + 1, 1
            while pos < len(body) and depth:
                if body[pos] == '\\': pos += 2; continue
                if body[pos] == '[': depth += 1
                if body[pos] == ']': depth -= 1
                pos += 1
            if depth:
                i += 1; continue
            text_label = body[start+1:pos-1]
            parsed = destination(body, pos + 1, True) if body[pos:pos+1] == '(' else None
            if parsed:
                target, end = parsed
            elif body[pos:pos+1] == '[':
                end = body.find(']', pos + 1)
                key = label(body[pos+1:end] or text_label) if end >= 0 else ''
                target = definitions.get(key); end += 1
            else:
                target = definitions.get(label(text_label)); end = pos
            if target is not None:
                if not is_image:
                    targets.extend(item for item in scan(text_label) if item[1])
                targets.append((target, is_image)); i = end
            else:
                i = start + 1
        return targets
    return scan(body)


def local_markdown_target(source, target):
    """Resolve URI paths once; never fetch external resources or check anchors."""
    if target.startswith('#'):
        return None
    try:
        uri = urlsplit(target)
        if uri.scheme or uri.netloc:
            return None
        path = unquote(uri.path)
    except ValueError:
        raise MarkdownError(f'Markdown目标无法解析: {target}')
    _require('\x00' not in path, f'Markdown目标包含无效路径字符: {target}')
    return source.parent / path if path else source


def rule_sections(path, titles):
    """Select exact ATX sections, retaining source bytes and rejecting ambiguity."""
    text = path.read_bytes().decode('utf-8')
    lines, headings = text.splitlines(keepends=True), []
    for i, line in enumerate(markdown_structure(text, preserve_inline=True).splitlines()):
        heading = re.fullmatch(r' {0,3}(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*', line)
        if heading:
            headings.append((i, len(heading[1]), heading[2].strip()))
    ranges = []
    for title in titles:
        matches = [h for h in headings if h[2] == title]
        _require(len(matches) == 1, f'规则章节缺失或重名: {path.name} / {title}')
        start, level, _ = matches[0]
        end = next((pos for pos, depth, _ in headings if pos > start and depth <= level), len(lines))
        ranges.append(''.join(lines[start:end]))
    return '\n'.join(ranges).encode()

