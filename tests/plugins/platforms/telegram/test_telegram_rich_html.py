"""Tests for the Markdown -> Telegram Rich HTML renderer (telegram_rich_html).

Bot API 10.1 ``sendRichMessage``'s ``html`` field is the accepted, mobile-confirmed shape for
native list rendering (see the module docstring for the rejected ``blocks``-field defect this
avoids). These tests pin the exact HTML each construct renders to, independent of the adapter.
"""

from plugins.platforms.telegram.telegram_rich_html import markdown_to_rich_html as R


class TestHeadingsParagraphsLists:
    def test_heading_two_paragraphs_and_bullet_list(self):
        content = "#### Results\n\nFirst paragraph.\n\nSecond paragraph.\n\n- alpha\n- beta\n- gamma"
        assert R(content) == (
            "<h4>Results</h4>"
            "<p>First paragraph.</p>"
            "<p>Second paragraph.</p>"
            "<ul><li>alpha</li><li>beta</li><li>gamma</li></ul>")

    def test_bullet_list_items_are_not_wrapped_in_p(self):
        """The rejected 'direct-block' shape put marker + text on separate lines because the
        item's text was wrapped in a block (paragraph). <li> must hold inline content directly."""
        html = R("- one\n- two")
        assert "<p>" not in html
        assert html == "<ul><li>one</li><li>two</li></ul>"

    def test_long_wrapping_bullet_has_no_manual_breaks_or_padding(self):
        """Telegram owns wrapping/indentation — the renderer must not inject <br> or padding
        spaces into one long list-item line."""
        long_text = " ".join(["word"] * 60)
        html = R(f"- {long_text}")
        assert html == f"<ul><li>{long_text}</li></ul>"
        assert "<br>" not in html

    def test_ordered_list_with_explicit_start(self):
        html = R("3. third\n4. fourth")
        assert html == '<ol start="3"><li>third</li><li>fourth</li></ol>'

    def test_ordered_list_default_start_omits_attribute(self):
        html = R("1. first\n2. second")
        assert html == "<ol><li>first</li><li>second</li></ol>"

    def test_nested_unordered_list(self):
        html = R("- top\n  - nested one\n  - nested two")
        assert html == "<ul><li>top<ul><li>nested one</li><li>nested two</li></ul></li></ul>"

    def test_nested_ordered_inside_unordered(self):
        html = R("- top\n  1. a\n  2. b")
        assert html == "<ul><li>top<ol><li>a</li><li>b</li></ol></li></ul>"

    def test_task_list_checked_and_unchecked(self):
        html = R("- [ ] todo\n- [x] done")
        assert html == (
            '<ul><li><input type="checkbox">todo</li>'
            '<li><input type="checkbox" checked>done</li></ul>')


class TestEmphasisLinksCode:
    def test_bold_italic_strikethrough_code_link(self):
        content = "This is **bold** and *italic* and ~~gone~~ and `code` and [a link](https://example.com)."
        assert R(content) == (
            '<p>This is <b>bold</b> and <i>italic</i> and <s>gone</s> and <code>code</code> '
            'and <a href="https://example.com">a link</a>.</p>')

    def test_bold_italic_combo(self):
        assert R("***both***") == "<p><b><i>both</i></b></p>"

    def test_angle_brackets_in_plain_text_are_escaped(self):
        assert R("a < b & b > c") == "<p>a &lt; b &amp; b &gt; c</p>"


class TestCodeBlocks:
    def test_fenced_code_with_language(self):
        html = R("```python\nprint('hi')\n```")
        assert html == '<pre><code class="language-python">print(\'hi\')</code></pre>'

    def test_fenced_code_without_language(self):
        html = R("```\nplain\n```")
        assert html == "<pre><code>plain</code></pre>"


class TestTables:
    def test_simple_table(self):
        html = R("| A | B |\n|---|---|\n| 1 | 2 |")
        assert html == "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"

    def test_table_cells_get_inline_formatting(self):
        # A single-column table has no *internal* pipe in its separator row, so it isn't
        # recognized as a table (matches the shared TABLE_SEPARATOR_RE convention used
        # elsewhere in the codebase) — use two columns.
        html = R("| A | B |\n|---|---|\n| **bold** | plain |")
        assert html == "<table><tr><th>A</th><th>B</th></tr><tr><td><b>bold</b></td><td>plain</td></tr></table>"


class TestDetails:
    def test_details_with_summary_and_list_body(self):
        content = "<details><summary>Notes</summary>\n\n- one\n- two\n</details>"
        assert R(content) == (
            "<details><summary>Notes</summary><ul><li>one</li><li>two</li></ul></details>")

    def test_details_open_attribute_preserved(self):
        content = "<details open><summary>Title</summary>\n\nBody text.\n</details>"
        html = R(content)
        assert html.startswith("<details open>")
        assert "<p>Body text.</p>" in html


class TestMath:
    def test_block_math_dollar_sign(self):
        assert R("$$x^2+y^2$$") == "<tg-math-block>x^2+y^2</tg-math-block>"

    def test_inline_math_dollar_and_paren(self):
        html = R("Inline $a+b$ and \\(c+d\\).")
        assert "<tg-math>a+b</tg-math>" in html
        assert "<tg-math>c+d</tg-math>" in html

    def test_math_inside_details(self):
        content = "<details><summary>Proof</summary>\n\n$$E=mc^2$$\n</details>"
        assert R(content) == (
            "<details><summary>Proof</summary><tg-math-block>E=mc^2</tg-math-block></details>")


class TestFallbackSafety:
    def test_empty_content_returns_empty_string(self):
        assert R("") == ""

    def test_renderer_never_raises_on_pathological_input(self):
        # Unbalanced/garbage markup must degrade, never throw, so a renderer bug can't take
        # down message delivery.
        pathological = "<details><summary>" + ("*" * 500) + "\n\n[[[" * 50
        html = R(pathological)
        assert isinstance(html, str)
