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


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [2, 7])
async def test_batch_dispatches_twitch_clips_up_to_limit(monkeypatch, count):
    from types import SimpleNamespace
    from unittest.mock import call

    from handlers import media_download

    first = "https://clips.twitch.tv/Clip-0"
    urls = [first, *[f"https://m.twitch.tv/davyjones/clip/Clip-{index}?x=1" for index in range(1, count)]]
    message = SimpleNamespace(
        text="\n".join(urls),
        chat=SimpleNamespace(id=-1, type="supergroup"),
        from_user=SimpleNamespace(id=1),
        answer=AsyncMock(),
    )
    delegate = AsyncMock()
    monkeypatch.setattr(universal, "process_universal_link", delegate)
    monkeypatch.setattr(media_download.db, "get_language", AsyncMock(return_value="pt"))
    monkeypatch.setattr(media_download, "_MAX_BATCH_LINKS", 6)
    monkeypatch.setattr(media_download, "_resolve_batch_concurrency", lambda: 1)
    for name in ("update_info", "send_analytics", "safe_delete_message"):
        monkeypatch.setattr(media_download, name, AsyncMock())
    monkeypatch.setattr(media_download.asyncio, "sleep", AsyncMock())

    assert media_download._has_multiple_supported_links(message)
    await media_download.process_batch_links(message)

    assert delegate.await_args_list == [call(message, direct_url=url) for url in urls[:6]]
