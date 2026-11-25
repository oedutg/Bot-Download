"""Route Twitch clips through the shared media delivery workflow."""

from aiogram import F, Router, types

from handlers.universal import process_universal_link
from handlers.utils import get_message_text
from services.links.detection import TWITCH_CLIP_URL, canonicalize_supported_url

router = Router(name=__name__)


@router.message(
    F.chat.type.in_({"private", "group", "supergroup"}),
    ~F.is_automatic_forward,
    ~F.text.startswith("/"),
    F.text.regexp(TWITCH_CLIP_URL, mode="search") | F.caption.regexp(TWITCH_CLIP_URL, mode="search"),
)
async def process_twitch_clip(message: types.Message) -> None:
    match = TWITCH_CLIP_URL.search(get_message_text(message))
    if match:
        await process_universal_link(message, direct_url=canonicalize_supported_url("twitch", match[0]))
