"""Standalone (out-of-process) Telegram delivery uses the same semantic Rich Messages path.

``tools.send_message_senders._send_telegram`` backs both the ``send_message`` tool and the
Telegram ``standalone_sender_fn`` (cron/scheduled ``deliver=telegram`` jobs). Before this,
plain-text standalone sends only ever used ``bot.send_message`` with MarkdownV2/HTML — a
separate implementation from the gateway adapter's comprehensive ``sendRichMessage`` path.
``rich_extra`` opts a standalone send into the identical renderer (``telegram_rich_html``) and
eligibility rules (CJK/size guards, capability fallback) as a live reply.

The ``telegram`` package is mocked via ``tests/gateway/conftest.py``.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from plugins.platforms.telegram.telegram_rich_html import markdown_to_rich_html
from tools.send_message_senders import _send_telegram

RICH_TEXT = "#### Update\n\nFirst paragraph.\n\n- alpha\n- beta"


def _make_bot(monkeypatch):
    bot = MagicMock()
    bot.do_api_request = AsyncMock(return_value=SimpleNamespace(message_id=777))
    bot.send_message = AsyncMock(return_value=SimpleNamespace(message_id=1))
    monkeypatch.setattr("tools.send_message_senders._telegram_bot", lambda token: bot)
    return bot


@pytest.mark.asyncio
async def test_standalone_send_uses_rich_when_opted_in(monkeypatch):
    bot = _make_bot(monkeypatch)

    result = await _send_telegram(
        "tok", "123", RICH_TEXT, rich_extra={"rich_messages": True})

    assert result["success"] is True
    bot.do_api_request.assert_awaited_once()
    assert bot.do_api_request.await_args.args[0] == "sendRichMessage"
    api_kwargs = bot.do_api_request.await_args.kwargs["api_kwargs"]
    assert api_kwargs["rich_message"]["html"] == markdown_to_rich_html(RICH_TEXT)
    bot.send_message.assert_not_awaited()
    assert result["message_id"] == "777"


@pytest.mark.asyncio
async def test_standalone_send_stays_legacy_without_opt_in(monkeypatch):
    bot = _make_bot(monkeypatch)

    result = await _send_telegram("tok", "123", RICH_TEXT, rich_extra=None)

    assert result["success"] is True
    bot.do_api_request.assert_not_awaited()
    bot.send_message.assert_awaited()


@pytest.mark.asyncio
async def test_standalone_send_skips_rich_for_media(monkeypatch, tmp_path):
    bot = _make_bot(monkeypatch)
    bot.send_photo = AsyncMock(return_value=SimpleNamespace(message_id=2))
    img = tmp_path / "x.png"
    img.write_bytes(b"x")

    result = await _send_telegram(
        "tok", "123", "caption text", media_files=[(str(img), False)],
        rich_extra={"rich_messages": True})

    assert result["success"] is True
    # Media sends keep their existing caption/text behavior untouched by the rich path.
    bot.do_api_request.assert_not_awaited()


@pytest.mark.asyncio
async def test_standalone_rich_send_failure_falls_back_to_legacy(monkeypatch):
    bot = _make_bot(monkeypatch)
    bot.do_api_request = AsyncMock(side_effect=RuntimeError("Method not found"))

    result = await _send_telegram(
        "tok", "123", RICH_TEXT, rich_extra={"rich_messages": True})

    assert result["success"] is True
    bot.do_api_request.assert_awaited_once()
    bot.send_message.assert_awaited()


@pytest.mark.asyncio
async def test_standalone_send_skips_rich_when_message_already_has_html(monkeypatch):
    bot = _make_bot(monkeypatch)

    result = await _send_telegram(
        "tok", "123", "<b>already html</b>", rich_extra={"rich_messages": True})

    assert result["success"] is True
    bot.do_api_request.assert_not_awaited()
    bot.send_message.assert_awaited()
