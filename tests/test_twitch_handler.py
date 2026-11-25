from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from aiogram import types

from handlers import router, twitch, universal


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("chat_type", "field", "link"),
    [
        ("private", "text", "https://clips.twitch.tv/MoralUnsightlyHerringAMPEnergy-Jg6z_aeiGSEounNW"),
        ("group", "text", "https://www.twitch.tv/davyjones/clip/Clip-ID"),
        ("supergroup", "caption", "https://m.twitch.tv/davyjones/clip/Clip-ID?desktop-redirect=true"),
    ],
)
async def test_twitch_clips_are_delegated_before_universal(monkeypatch, chat_type, field, link):
    delegate = AsyncMock()
    monkeypatch.setattr(twitch, "process_universal_link", delegate)
    message = types.Message(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=types.Chat(id=1, type=chat_type),
        **{field: f"Vídeo: {link}"},
    )
    assert router.sub_routers.index(twitch.router) < router.sub_routers.index(universal.router)
    handler = twitch.router.message.handlers[0]
    assert (await handler.check(message))[0]
    await twitch.process_twitch_clip(message)
    delegate.assert_awaited_once_with(message, direct_url=link)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "forwarded"),
    [
        ("https://twitch.tv/davyjones", False),
        ("https://twitch.tv/videos/12345", False),
        ("https://clips.twitch.tv.example.com/Clip-ID", False),
        ("https://clips.twitch.tv/Clip-ID", True),
    ],
)
async def test_twitch_route_does_not_match_other_links_or_automatic_forwards(url, forwarded):
    message = types.Message(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=types.Chat(id=1, type="supergroup"),
        text=url,
        is_automatic_forward=forwarded,
    )
    assert not (await twitch.router.message.handlers[0].check(message))[0]
