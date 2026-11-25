"""Route Twitch clips through the shared media delivery workflow."""

import re

from aiogram import F, Router, types

from handlers.universal import process_universal_link
from handlers.utils import get_message_text

router = Router(name=__name__)

_CLIP_URL = re.compile(
    r"(?<![\w/])https?://(?:clips\.twitch\.tv/|"
    r"(?:(?:www|m)\.)?twitch\.tv/[a-z0-9_]+/clip/)"
    r"[a-z0-9_-]+/?(?:[?#][^\s<>]*)?(?=$|[\s<>.,;!\])}])",
    re.IGNORECASE,
)


@router.message(
    F.chat.type.in_({"private", "group", "supergroup"}),
    ~F.is_automatic_forward,
    ~F.text.startswith("/"),
    F.text.regexp(_CLIP_URL, mode="search") | F.caption.regexp(_CLIP_URL, mode="search"),
)
async def process_twitch_clip(message: types.Message) -> None:
    match = _CLIP_URL.search(get_message_text(message))
    if match:
        await process_universal_link(message, direct_url=match[0].rstrip(".,;!])}"))
