import asyncio

from aiogram import types

import messages as bm
from app_context import bot, db, send_analytics
from config import (
    BATCH_LINKS_MAX_CONCURRENCY,
    BATCH_LINKS_MAX_ITEMS,
    BATCH_LINKS_MIN_CONCURRENCY,
    BATCH_LINKS_PARALLEL_ACTIVE_JOBS_THRESHOLD,
    BATCH_LINKS_PARALLEL_QUEUE_DEPTH_THRESHOLD,
)
from handlers.batch_routes import BatchItem, deferred_source_deletes, resolve_batch
from handlers.commands import open_help_page, update_info
from handlers.utils import get_message_text, maybe_delete_user_message, safe_edit_text
from services.download.queue import get_download_queue
from services.logger import logger as logging, summarize_url_for_log
from services.inline.album_links import get_inline_album_request
from services.links.detection import extract_supported_link

logging = logging.bind(service="media_download")

_MAX_BATCH_LINKS = max(1, int(BATCH_LINKS_MAX_ITEMS))
_BATCH_START_EMOJI = '<tg-emoji emoji-id="5854908544712707500">📦</tg-emoji>'
_BATCH_END_EMOJI = '<tg-emoji emoji-id="5866355487255039002">🚀</tg-emoji>'
_ALBUM_SERVICES = {"instagram", "threads", "tiktok", "pinterest", "twitter"}


async def _process_inline_album_deeplink(message: types.Message, payload: str) -> bool:
    user_lang = await db.get_language(message.from_user.id)
    if not payload.startswith("album_"):
        return False
    token = payload.removeprefix("album_").strip()
    if not token:
        return False

    request = get_inline_album_request(token)
    if not request:
        await message.answer(bm.inline_album_link_invalid(lang=user_lang))
        return True

    try:
        if request.service in _ALBUM_SERVICES:
            await _process_supported_link(message, request.service, request.url)
            return True
    except Exception:
        logging.exception(
            "Falha ao processar inline album deeplink: user_id=%s service=%s url=%s",
            message.from_user.id,
            request.service,
            summarize_url_for_log(request.url),
        )
        await message.answer(bm.something_went_wrong(lang=user_lang))
        return True

    await message.answer(bm.inline_album_link_invalid(lang=user_lang))
    return True


async def _process_pending_message(message: types.Message) -> None:
    text = get_message_text(message)
    detected = extract_supported_link(text)
    if not detected:
        return
    service, url = detected
    await _process_supported_link(message, service, url)


async def _process_supported_link(message: types.Message, service: str, url: str) -> None:
    if service == "tiktok":
        from handlers import tiktok
        await tiktok.process_tiktok(message, direct_url=url)
        return

    if service == "kwai":
        from handlers import kwai
        await kwai.process_kwai_link(message, direct_url=url)
        return

    if service == "twitch":
        from handlers.universal import process_universal_link
        await process_universal_link(message, direct_url=url)
        return

    if service == "instagram":
        from handlers import instagram
        await instagram.process_instagram_url(message, url=url)
        return

    if service == "threads":
        from handlers import threads
        await threads.process_threads_url(message, url=url)
        return

    if service == "soundcloud":
        from handlers import soundcloud
        await soundcloud.process_soundcloud_url(message, url=url)
        return

    if service == "spotify":
        from handlers import spotify
        await spotify.process_spotify_url(message, url=url)
        return

    if service == "pinterest":
        from handlers import pinterest
        await pinterest.process_pinterest_url(message, url=url)
        return

    if service == "youtube":
        from handlers import youtube
        if "music.youtube." in url.lower():
            await youtube.download_music(message, direct_url=url)
        else:
            await youtube.download_video(message, direct_url=url)
        return

    if service == "twitter":
        from handlers import twitter
        await twitter.handle_tweet_links(message, direct_url=url)


async def _has_multiple_supported_links(message: types.Message, **data):
    items, total = await resolve_batch(message, data, limit=_MAX_BATCH_LINKS)
    if total < 2:
        return False
    return {"batch_items": items, "batch_total": total}

def _resolve_batch_concurrency() -> int:
    min_concurrency = max(1, int(BATCH_LINKS_MIN_CONCURRENCY))
    max_concurrency = max(min_concurrency, int(BATCH_LINKS_MAX_CONCURRENCY))
    load = get_download_queue().load_snapshot()
    if (
        load.queued_jobs > int(BATCH_LINKS_PARALLEL_QUEUE_DEPTH_THRESHOLD)
        or load.active_jobs >= int(BATCH_LINKS_PARALLEL_ACTIVE_JOBS_THRESHOLD)
    ):
        return min_concurrency
    return max_concurrency


async def process_batch_links(
    message: types.Message,
    batch_items: list[BatchItem] | None = None,
    batch_total: int | None = None,
    **data,
):
    if batch_items is None:
        batch_items, batch_total = await resolve_batch(message, data, limit=_MAX_BATCH_LINKS)
    if batch_total is None or batch_total < 2:
        return

    user_lang = await db.get_language(message.from_user.id)
    await send_analytics(
        user_id=message.from_user.id,
        chat_type=message.chat.type,
        action_name="batch_links",
    )
    await update_info(message)

    concurrency = min(len(batch_items), _resolve_batch_concurrency())
    status = await message.answer(
        f"{_BATCH_START_EMOJI} " + bm.batch_links_started(len(batch_items), batch_total, lang=user_lang),
        parse_mode="HTML",
    )
    deletes = []
    token = deferred_source_deletes.set(deletes)
    try:
        await _process_batch_links_parallel(message, batch_items, concurrency, data)
        await safe_edit_text(
            status,
            f"{_BATCH_END_EMOJI} " + bm.batch_links_finished(len(batch_items), lang=user_lang),
            parse_mode="HTML",
        )
    finally:
        deferred_source_deletes.reset(token)
        if (message.chat.id, message.message_id) in deletes:
            await maybe_delete_user_message(message, "on")


async def _process_batch_links_parallel(
    message: types.Message,
    items: list[BatchItem],
    concurrency: int,
    data: dict,
) -> None:
    user_lang = await db.get_language(message.from_user.id)
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def run_one(item: BatchItem) -> None:
        async with semaphore:
            try:
                await item.deliver(data)
            except Exception:
                logging.exception("Batch link failed: service=%s", item.service)
                await message.answer(bm.something_went_wrong(lang=user_lang))

    await asyncio.gather(*(run_one(item) for item in items))


async def show_supported_sites(call: types.CallbackQuery):
    await open_help_page(call)
