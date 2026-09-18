"""Tests for rich-message line-break rendering (issue #46070).

Standard Markdown treats a lone ``\\n`` as a soft line break (renders as whitespace). Bot API
10.1 ``sendRichMessage`` needs an explicit line-break signal or multi-line content collapses
into one run of text. ``_rich_message_payload`` renders content through
``telegram_rich_html.markdown_to_rich_html`` (the ``html`` field), which turns a lone ``\\n``
into an explicit ``<br>`` within the same ``<p>``, and a blank line (``\\n\\n``) into a new
``<p>``. Fenced code blocks and pipe tables render as ``<pre>``/``<table>`` and keep their
internal newlines as real line/row breaks rather than ``<br>``.

The ``telegram`` package is mocked by ``tests/gateway/conftest.py``, so these tests construct a
real ``TelegramAdapter``.
"""

from plugins.platforms.telegram.adapter import TelegramAdapter


class TestRichMessageLineBreaks:
    """Verify _rich_message_payload's html rendering of single vs. double newlines."""

    def test_single_newlines_become_br(self):
        """A lone \\n must render as an explicit <br> inside one paragraph."""
        adapter = object.__new__(TelegramAdapter)
        payload = adapter._rich_message_payload("Line 1\nLine 2\nLine 3")
        assert payload["html"] == "<p>Line 1<br>Line 2<br>Line 3</p>"

    def test_paragraph_breaks_become_separate_p_tags(self):
        """Double newlines (paragraph breaks) start a new <p>, not a <br>."""
        adapter = object.__new__(TelegramAdapter)
        payload = adapter._rich_message_payload("Paragraph 1\n\nParagraph 2")
        assert payload["html"] == "<p>Paragraph 1</p><p>Paragraph 2</p>"

    def test_mixed_single_and_double_newlines(self):
        """Content with both list items and paragraph breaks must be handled correctly."""
        adapter = object.__new__(TelegramAdapter)
        content = (
            "Header\n\n"
            "`/new` -- Start\n"
            "`/model` -- Switch\n"
            "`/reset` -- Reset\n\n"
            "Footer"
        )
        html = adapter._rich_message_payload(content)["html"]
        assert html == (
            "<p>Header</p>"
            "<p><code>/new</code> -- Start<br><code>/model</code> -- Switch<br>"
            "<code>/reset</code> -- Reset</p>"
            "<p>Footer</p>")


class TestRichMessageTableProtection:
    """Table/fenced-code newlines render as native structure, never a stray <br>."""

    def test_table_rows_render_as_table_not_br(self):
        content = "| Col A | Col B |\n|-------|-------|\n| 1 | 2 |\n| 3 | 4 |"
        html = object.__new__(TelegramAdapter)._rich_message_payload(content)["html"]
        assert "<br>" not in html
        assert html == (
            "<table><tr><th>Col A</th><th>Col B</th></tr>"
            "<tr><td>1</td><td>2</td></tr><tr><td>3</td><td>4</td></tr></table>")

    def test_fenced_code_keeps_bare_newlines(self):
        content = "```\nline one\nline two\n```"
        html = object.__new__(TelegramAdapter)._rich_message_payload(content)["html"]
        assert "<br>" not in html
        assert html == "<pre><code>line one\nline two</code></pre>"
