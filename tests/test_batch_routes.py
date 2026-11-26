from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from aiogram import F, Router, types

from app_context import bot
from handlers import media_download, router
from handlers.batch_routes import resolve_batch
from handlers.telegram_ui_utils import maybe_delete_user_message


def make_message(text, kind="supergroup", *, forwarded=False):
    return types.Message(
        message_id=42,
        date=datetime.now(timezone.utc),
        chat=types.Chat(id=-12, type=kind),
        from_user=types.User(id=123, first_name="Test", is_bot=False),
        text=text,
        is_automatic_forward=forwarded,
    )


@pytest.mark.asyncio
async def test_batch_uses_registered_handlers_and_preserves_group_rules():
    twitch = "https://clips.twitch.tv/Clip-ID"
    drive = "https://drive.google.com/file/d/ExampleId/view"
    mega = "https://mega.nz/file/ExampleId#key"
    bluesky = "https://bsky.app/profile/edu.bsky.social/post/abc"
    other = "https://example.org/video.mp4"
    text = "\n".join((twitch, drive, mega, bluesky, other))
    group, total = await resolve_batch(make_message(text), {"bot": bot}, limit=6)
    assert total == 4
    assert [item.service for item in group] == ["twitch", "google_drive", "mega", "bluesky"]
    assert [item.message.text for item in group] == [twitch, drive, mega, bluesky]
    private, total = await resolve_batch(make_message(text, "private"), {"bot": bot}, limit=6)
    assert total == 5
    assert [item.service for item in private][-2:] == ["bluesky", "universal"]
    assert await resolve_batch(make_message(text, forwarded=True), {}, limit=6) == ([], 0)


@pytest.mark.asyncio
async def test_added_router_works_in_batch_and_deletion_waits(monkeypatch):
    extra = Router()
    seen = []
    delete = AsyncMock()
    status = AsyncMock()
    monkeypatch.setattr(types.Message, "delete", delete)
    monkeypatch.setattr(types.Message, "answer", status)
    monkeypatch.setattr(media_download, "_resolve_batch_concurrency", lambda: 2)
    monkeypatch.setattr(media_download.db, "get_language", AsyncMock(return_value="pt"))
    for name in ("update_info", "send_analytics", "safe_edit_text", "safe_delete_message"):
        monkeypatch.setattr(media_download, name, AsyncMock())

    monkeypatch.setattr(media_download, "_BATCH_STATUS_DELETE_DELAY", 0)

    @extra.message(F.text.startswith("https://downloads.example/"))
    async def handle_link(message: types.Message):
        seen.append((message.message_id, message.text))
        await maybe_delete_user_message(message, "on")
        delete.assert_not_awaited()

    monkeypatch.setattr(extra, "_parent_router", router)
    monkeypatch.setattr(router, "sub_routers", [*router.sub_routers, extra])
    urls = [f"https://downloads.example/{i}" for i in range(7)]
    update = make_message("\n".join(urls))
    monkeypatch.setattr(media_download, "_MAX_BATCH_LINKS", 6)
    batch = await media_download._has_multiple_supported_links(update, bot=bot)
    assert batch["batch_total"] == 7
    await router.propagate_event(update_type="message", event=update, bot=bot)

    assert seen == [(42, url) for url in urls[:6]]
    delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_long_batch_edits_processing_before_finished(monkeypatch):
    import asyncio
    from types import SimpleNamespace

    original = make_message("https://clips.twitch.tv/Clip-ID")
    status = object()
    answer = AsyncMock(return_value=status)
    progress = asyncio.Event()
    edits = []
    actions = []

    async def sleep(delay):
        actions.append(("sleep", delay))

    async def delete(message):
        actions.append(("delete", message))

    async def edit(message, text, **kwargs):
        assert message is status
        assert kwargs["parse_mode"] == "HTML"
        edits.append(text)
        actions.append(("edit", message))
        if 'emoji-id="5260491539167073671"' in text:
            progress.set()

    async def deliver(data):
        await asyncio.wait_for(progress.wait(), timeout=1)

    monkeypatch.setattr(types.Message, "answer", answer)
    monkeypatch.setattr(media_download, "safe_edit_text", edit)
    monkeypatch.setattr(media_download, "safe_delete_message", delete)
    monkeypatch.setattr(media_download.asyncio, "sleep", sleep)
    monkeypatch.setattr(media_download, "_BATCH_PROCESSING_DELAY", 0)
    monkeypatch.setattr(media_download, "_resolve_batch_concurrency", lambda: 2)
    monkeypatch.setattr(media_download.db, "get_language", AsyncMock(return_value="pt"))
    monkeypatch.setattr(media_download, "update_info", AsyncMock())
    monkeypatch.setattr(media_download, "send_analytics", AsyncMock())
    item = SimpleNamespace(deliver=deliver)

    await media_download.process_batch_links(original, batch_items=[item, item], batch_total=2)

    answer.assert_awaited_once()
    assert 'emoji-id="6323328338123293863"' in answer.await_args.args[0]
    assert len(edits) == 2
    assert 'emoji-id="5260491539167073671"' in edits[0]
    assert 'emoji-id="5866355487255039002"' in edits[1]
    assert actions == [("edit", status), ("edit", status), ("sleep", 2.0), ("delete", status)]
