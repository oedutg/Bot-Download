"""Private-chat delivery of public Bluesky posts."""

from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory

import aiohttp
from aiogram import F, Router, types

import messages as bm
from app_context import bot, db
from config import MAX_FILE_SIZE, OUTPUT_DIR
from handlers.commands import is_banned
from handlers.request_dedupe import claim_message_request
from handlers.utils import (
    get_bot_url,
    get_message_text,
    handle_download_error,
    handle_video_too_large,
    load_user_settings,
    maybe_delete_user_message,
)
from services.logger import logger
from services.media.delivery import send_cached_media_entries
from services.platforms.bluesky_media import (
    POST_URL,
    BlueskyMediaTooLarge,
    BlueskyPostUnavailable,
    download_media,
    extract_post_url,
    fetch_post,
)

router = Router(name=__name__)
logging = logger.bind(service="bluesky")


def _source_button(url: str, settings: dict) -> types.InlineKeyboardMarkup | None:
    if settings.get("url_button") != "on":
        return None
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔗 URL", url=url)]
    ])


async def _send_text(message: types.Message, text: str, bot_url: str, markup=None) -> None:
    # Keep the original text intact, including long quote chains and HTML characters.
    parts = [text[index:index + 650] for index in range(0, len(text), 650)]
    for index, part in enumerate(parts):
        last = index == len(parts) - 1
        await message.answer(
            bm.captions("on", part, bot_url, limit=4096) if last else escape(part),
            parse_mode="HTML",
            link_preview_options=types.LinkPreviewOptions(is_disabled=True),
            reply_markup=markup if last else None,
        )


@router.message(
    F.chat.type == "private",
    F.text.regexp(POST_URL, mode="search") | F.caption.regexp(POST_URL, mode="search"),
)
async def process_bluesky_post(message: types.Message) -> None:
    url = extract_post_url(get_message_text(message))
    if not url or not message.from_user:
        return
    if await is_banned(message.from_user.id, message.chat.id):
        return
    lease = await claim_message_request(message, service="bluesky", url=url)
    if lease is None:
        return

    try:
        settings = await load_user_settings(db, message)
        bot_url = await get_bot_url(bot)
        markup = _source_button(url, settings)
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            post = await fetch_post(session, url)
            if not post.media:
                if not post.text:
                    raise BlueskyPostUnavailable
                await _send_text(message, post.text, bot_url, markup)
            else:
                output = Path(OUTPUT_DIR)
                output.mkdir(parents=True, exist_ok=True)
                with TemporaryDirectory(prefix="bluesky-", dir=output) as temporary:
                    entries = []
                    for index, media in enumerate(post.media):
                        path = await download_media(session, media, Path(temporary), index, MAX_FILE_SIZE)
                        entries.append({"kind": media.kind, "path": path, "cached": True})

                    captions_on = settings.get("captions", "on")
                    caption = bm.captions(captions_on, post.text, bot_url)
                    full = bm.captions(captions_on, post.text, bot_url, limit=65536)
                    for offset in range(0, len(entries), 10):
                        await send_cached_media_entries(
                            message,
                            entries[offset:offset + 10],
                            db_service=db,
                            caption=(
                                (caption if caption == full else bm.captions("off", None, bot_url))
                                if offset == 0 else None
                            ),
                            reply_markup=markup,
                            as_document=settings.get("as_document") == "on",
                        )
                    if caption != full:
                        await _send_text(message, post.text, bot_url, markup)
        lease.mark_success()
        await maybe_delete_user_message(message, settings.get("delete_message"))
    except BlueskyMediaTooLarge:
        await handle_video_too_large(message)
    except Exception:
        logging.exception("Could not deliver Bluesky post")
        await handle_download_error(message)
    finally:
        lease.finish()
