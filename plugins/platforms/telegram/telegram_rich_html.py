"""Markdown -> Telegram Rich HTML (Bot API 10.1/10.2 ``sendRichMessage`` ``html`` field).

The ``markdown``-field path (raw agent Markdown handed straight to Telegram's own parser)
mishandled plain bullet/numbered lists: a live ``sendRichMessage`` comparison showed the
``blocks``-field ("direct-block") shape rendering list markers on their own line, above the
item text, while the same content sent through the ``html`` field with real ``<ul>/<ol>/<li>``
tags rendered natively and correctly (mobile-confirmed). This module renders our own semantic
HTML for the ``html`` field so every reply — not just tables/task-lists/details/math — gets
native heading/paragraph/list structure, matching the accepted shape and avoiding the rejected
one. Reference: https://core.telegram.org/bots/api#rich-html-style (the exact tag allowlist
below is transcribed from that section).

Deliberately not CommonMark-complete: it covers the constructs Hermes agents actually produce
(headings, paragraphs, lists incl. nested/task, emphasis, links, inline/fenced code, tables,
blockquotes, math, and literal ``<details>`` passthrough) and falls back to a single escaped
paragraph on any internal error rather than ever raising into the send path.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from gateway.platforms.helpers import TABLE_SEPARATOR_RE, split_markdown_table_row

__all__ = ["markdown_to_rich_html"]

# Block-level raw passthrough: the agent sometimes emits literal <details><summary>...</summary>
# ...</details> HTML directly (GFM extension). Telegram's own Markdown parser only recurses into
# <details> (not other block tags), so we do the same: render the inside recursively, keep the
# wrapper tags. (Matched inline, non-anchored, by _DETAILS_RE below — a details block need not
# be the whole message.)
_DETAILS_RE = re.compile(
    r'<details(?P<open>\s+open\b[^>]*)?>\s*(?:<summary>(?P<summary>.*?)</summary>)?(?P<body>.*?)</details>',
    re.IGNORECASE | re.DOTALL)

_FENCE_RE = re.compile(r'^(`{3,}|~{3,})\s*([\w+-]*)\s*$')
_ATX_HEADING_RE = re.compile(r'^(#{1,6})\s+(.*?)\s*$')
_THEMATIC_BREAK_RE = re.compile(r'^ {0,3}([-*_])(?: *\1){2,} *$')
_UL_MARKER_RE = re.compile(r'^(\s*)([-*+])\s+(.*)$')
_OL_MARKER_RE = re.compile(r'^(\s*)(\d{1,9})[.)]\s+(.*)$')
_TASK_RE = re.compile(r'^\[( |x|X)\]\s+(.*)$')
_BLOCKQUOTE_RE = re.compile(r'^ {0,3}>\s?(.*)$')
_BLANK_RE = re.compile(r'^\s*$')

_BLOCK_MATH_RE = re.compile(
    r'(?P<dollars>\$\$(?P<dollars_body>.+?)\$\$)|(?P<brackets>\\\[(?P<brackets_body>.+?)\\\])', re.DOTALL)

_MAX_NESTING_DEPTH = 16  # Telegram Rich Message limit (nested formatting/blocks).


def _esc(text: str) -> str:
    """Escape the three HTML metacharacters Telegram's rich HTML parser requires escaped."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Inline rendering
# ---------------------------------------------------------------------------

# Ordered so higher-precedence spans (code, math) are pulled out before emphasis scanning, mirroring
# how a real parser would tokenize: code/math spans are opaque to further inline parsing.
_INLINE_TOKEN_RE = re.compile(
    r'(?P<code>`+)(?P<code_body>.+?)(?P=code)'
    r'|(?P<mathparen>\\\((?P<mathparen_body>.+?)\\\))'
    r'|(?P<mathdollar>(?<!\$)\$(?!\$)(?P<mathdollar_body>[^$\n]+?)(?<!\$)\$(?!\$))'
    r'|(?P<link>\[(?P<link_text>[^\]]*)\]\((?P<link_url>[^\s)]+)\))'
    r'|(?P<bolditalic>(\*\*\*|___)(?P<bolditalic_body>.+?)(\*\*\*|___))'
    r'|(?P<bold>(\*\*|__)(?P<bold_body>.+?)(\*\*|__))'
    r'|(?P<italic>(\*|_)(?P<italic_body>.+?)(\*|_))'
    r'|(?P<strike>~~(?P<strike_body>.+?)~~)',
    re.DOTALL)


def _render_inline(text: str, *, depth: int = 0) -> str:
    """Render one run of inline Markdown to Telegram Rich HTML inline tags."""
    if not text:
        return ""
    if depth >= _MAX_NESTING_DEPTH:
        return _esc(text)
    out: List[str] = []
    pos = 0
    for m in _INLINE_TOKEN_RE.finditer(text):
        out.append(_esc(text[pos:m.start()]))
        pos = m.end()
        if m.group("code") is not None:
            out.append(f"<code>{_esc(m.group('code_body'))}</code>")
        elif m.group("mathparen") is not None:
            out.append(f"<tg-math>{_esc(m.group('mathparen_body').strip())}</tg-math>")
        elif m.group("mathdollar") is not None:
            out.append(f"<tg-math>{_esc(m.group('mathdollar_body').strip())}</tg-math>")
        elif m.group("link") is not None:
            url = m.group("link_url")
            inner = _render_inline(m.group("link_text"), depth=depth + 1)
            out.append(f'<a href="{_esc(url)}">{inner}</a>')
        elif m.group("bolditalic") is not None:
            inner = _render_inline(m.group("bolditalic_body"), depth=depth + 1)
            out.append(f"<b><i>{inner}</i></b>")
        elif m.group("bold") is not None:
            inner = _render_inline(m.group("bold_body"), depth=depth + 1)
            out.append(f"<b>{inner}</b>")
        elif m.group("italic") is not None:
            inner = _render_inline(m.group("italic_body"), depth=depth + 1)
            out.append(f"<i>{inner}</i>")
        elif m.group("strike") is not None:
            inner = _render_inline(m.group("strike_body"), depth=depth + 1)
            out.append(f"<s>{inner}</s>")
    out.append(_esc(text[pos:]))
    return "".join(out)


def _render_inline_lines(lines: List[str], *, depth: int = 0) -> str:
    """Join already-split lines with ``<br>`` — the caller owns paragraph/line semantics."""
    return "<br>".join(_render_inline(line, depth=depth) for line in lines)


# ---------------------------------------------------------------------------
# Block rendering
# ---------------------------------------------------------------------------


def _consume_fence(lines: List[str], start: int) -> Tuple[str, str, int]:
    """From a fence opener at ``lines[start]``, return ``(language, code_text, next_index)``."""
    marker_m = _FENCE_RE.match(lines[start])
    fence_char = marker_m.group(1)[0]
    language = marker_m.group(2) or ""
    body: List[str] = []
    i = start + 1
    close_re = re.compile(rf'^{re.escape(fence_char)}{{3,}}\s*$')
    while i < len(lines) and not close_re.match(lines[i]):
        body.append(lines[i])
        i += 1
    return language, "\n".join(body), min(i + 1, len(lines))


def _render_table(rows: List[str], *, depth: int) -> str:
    header_cells = split_markdown_table_row(rows[0])
    body_rows = [split_markdown_table_row(r) for r in rows[2:] if r.strip()]
    out = ["<table>", "<tr>"]
    for cell in header_cells:
        out.append(f"<th>{_render_inline(cell.strip(), depth=depth + 1)}</th>")
    out.append("</tr>")
    for row in body_rows:
        out.append("<tr>")
        for cell in row:
            out.append(f"<td>{_render_inline(cell.strip(), depth=depth + 1)}</td>")
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)


def _leading_ws(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _render_list_item_body(body_lines: List[str], *, depth: int) -> str:
    """Render one list item's content lines (the marker's own line plus any indented
    continuation/nested-list lines already stripped of the marker prefix)."""
    if not body_lines:
        return ""
    nested_start = None
    for idx in range(1, len(body_lines)):
        if _UL_MARKER_RE.match(body_lines[idx]) or _OL_MARKER_RE.match(body_lines[idx]):
            nested_start = idx
            break
    text_lines = body_lines if nested_start is None else body_lines[:nested_start]
    # No <p> wrapper around the item's own text — wrapping list-item text in a block pushes the
    # bullet/number marker onto its own line in Telegram's renderer (the defect the "direct-block"
    # test hit). Plain inline content directly inside <li> is the accepted, correctly-rendered shape.
    html = _render_inline_lines([l for l in text_lines if l.strip()], depth=depth)
    if nested_start is not None:
        html += _render_blocks(body_lines[nested_start:], depth=depth + 1)
    return html


def _render_list(lines: List[str], start: int, *, depth: int) -> Tuple[str, int]:
    first = lines[start]
    is_ordered = bool(_OL_MARKER_RE.match(first))
    marker_re = _OL_MARKER_RE if is_ordered else _UL_MARKER_RE
    base_indent = len(marker_re.match(first).group(1))
    items: List[List[str]] = []
    i = start
    while i < len(lines):
        line = lines[i]
        if _BLANK_RE.match(line):
            i += 1
            continue
        m = marker_re.match(line)
        if m and _leading_ws(line) == base_indent:
            items.append([m.group(3)])
            i += 1
            continue
        if items and _leading_ws(line) > base_indent:
            # Continuation / nested content for the current item, dedented by the parent
            # marker's own indent so a nested marker's indent is measured from zero again.
            items[-1].append(line[base_indent:])
            i += 1
            continue
        break  # same/lower indent that isn't this list's marker — list ends here
    tag = "ol" if is_ordered else "ul"
    start_attr = ""
    if is_ordered:
        first_num_m = re.match(r'^\s*(\d+)', lines[start])
        first_num = int(first_num_m.group(1)) if first_num_m else 1
        if first_num != 1:
            start_attr = f' start="{first_num}"'
    parts = [f"<{tag}{start_attr}>"]
    for item_lines in items:
        task_m = _TASK_RE.match(item_lines[0]) if item_lines else None
        if task_m:
            checked = task_m.group(1).lower() == "x"
            rest_lines = [task_m.group(2)] + item_lines[1:]
            checkbox = '<input type="checkbox" checked>' if checked else '<input type="checkbox">'
            parts.append(f"<li>{checkbox}{_render_list_item_body(rest_lines, depth=depth)}</li>")
        else:
            parts.append(f"<li>{_render_list_item_body(item_lines, depth=depth)}</li>")
    parts.append(f"</{tag}>")
    return "".join(parts), i


def _render_blockquote(lines: List[str], start: int, *, depth: int) -> Tuple[str, int]:
    inner: List[str] = []
    i = start
    while i < len(lines):
        m = _BLOCKQUOTE_RE.match(lines[i])
        if not m:
            break
        inner.append(m.group(1))
        i += 1
    return f"<blockquote>{_render_blocks(inner, depth=depth + 1)}</blockquote>", i


def _render_blocks(lines: List[str], *, depth: int = 0) -> str:
    if depth >= _MAX_NESTING_DEPTH:
        return _esc("\n".join(lines))
    out: List[str] = []
    i = 0
    para_buf: List[str] = []

    def flush_paragraph() -> None:
        if para_buf:
            out.append(f"<p>{_render_inline_lines(para_buf, depth=depth)}</p>")
            para_buf.clear()

    while i < len(lines):
        line = lines[i]
        if _BLANK_RE.match(line):
            flush_paragraph()
            i += 1
            continue
        fence_m = _FENCE_RE.match(line)
        if fence_m:
            flush_paragraph()
            language, code_text, i = _consume_fence(lines, i)
            if language.lower() in ("math", "latex"):
                out.append(f"<tg-math-block>{_esc(code_text.strip())}</tg-math-block>")
            else:
                lang_attr = f' class="language-{_esc(language)}"' if language else ""
                out.append(f"<pre><code{lang_attr}>{_esc(code_text)}</code></pre>")
            continue
        if _THEMATIC_BREAK_RE.match(line) and not _UL_MARKER_RE.match(line):
            flush_paragraph()
            out.append("<hr/>")
            i += 1
            continue
        heading_m = _ATX_HEADING_RE.match(line)
        if heading_m:
            flush_paragraph()
            size = len(heading_m.group(1))
            out.append(f"<h{size}>{_render_inline(heading_m.group(2), depth=depth)}</h{size}>")
            i += 1
            continue
        if (_UL_MARKER_RE.match(line) or _OL_MARKER_RE.match(line)):
            flush_paragraph()
            rendered, i = _render_list(lines, i, depth=depth + 1)
            out.append(rendered)
            continue
        if _BLOCKQUOTE_RE.match(line):
            flush_paragraph()
            rendered, i = _render_blockquote(lines, i, depth=depth + 1)
            out.append(rendered)
            continue
        if "|" in line and i + 1 < len(lines) and TABLE_SEPARATOR_RE.match(lines[i + 1]):
            flush_paragraph()
            table_rows = [line, lines[i + 1]]
            j = i + 2
            while j < len(lines) and "|" in lines[j] and not _BLANK_RE.match(lines[j]):
                table_rows.append(lines[j])
                j += 1
            out.append(_render_table(table_rows, depth=depth))
            i = j
            continue
        para_buf.append(line)
        i += 1
    flush_paragraph()
    return "".join(out)


def _render_block_math(text: str) -> str:
    """Pull out ``$$...$$`` / ``\\[...\\]`` block-math atoms as their own blocks so they don't
    get swallowed into a surrounding paragraph."""
    parts: List[str] = []
    pos = 0
    for m in _BLOCK_MATH_RE.finditer(text):
        before = text[pos:m.start()]
        if before.strip():
            parts.append(_render_blocks(before.split("\n")))
        body = m.group("dollars_body") if m.group("dollars") else m.group("brackets_body")
        parts.append(f"<tg-math-block>{_esc(body.strip())}</tg-math-block>")
        pos = m.end()
    remainder = text[pos:]
    if remainder.strip() or not parts:
        parts.append(_render_blocks(remainder.split("\n")))
    return "".join(parts)


def _render_details_and_rest(text: str) -> str:
    """Split ``text`` on top-level ``<details>...</details>`` blocks, rendering the surrounding
    markdown normally and recursing into each block's body/summary."""
    parts: List[str] = []
    pos = 0
    for m in _DETAILS_RE.finditer(text):
        before = text[pos:m.start()]
        if before.strip():
            parts.append(_render_block_math(before))
        open_attr = " open" if m.group("open") else ""
        summary_html = _render_inline(m.group("summary") or "", depth=0)
        body_html = _render_block_math(m.group("body") or "")
        summary_tag = f"<summary>{summary_html}</summary>" if m.group("summary") is not None else ""
        parts.append(f"<details{open_attr}>{summary_tag}{body_html}</details>")
        pos = m.end()
    remainder = text[pos:]
    if remainder.strip() or not parts:
        parts.append(_render_block_math(remainder))
    return "".join(parts)


def markdown_to_rich_html(text: str) -> str:
    """Render Hermes-agent Markdown to Telegram Rich HTML (the ``html`` field of
    ``InputRichMessage``). Never raises: any internal failure degrades to a single escaped
    paragraph so a renderer bug can't take down message delivery."""
    if not text:
        return ""
    try:
        return _render_details_and_rest(text)
    except Exception:
        return f"<p>{_esc(text)}</p>"
