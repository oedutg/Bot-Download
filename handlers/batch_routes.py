"""Split one Telegram update into deliveries through its registered downloaders."""

import re
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from aiogram import Router, types

_URL = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
_TRAILING = ".,;:!?)]}>\"'"

# Parallel tasks share the same list, but unrelated updates have their own context.
deferred_source_deletes: ContextVar[list[tuple[int, int]] | None] = ContextVar(
    "deferred_source_deletes", default=None
)


@dataclass
class BatchItem:
    service: str
    message: types.Message
    router: Router

    async def deliver(self, data: dict[str, Any]) -> None:
        await self.router.propagate_event(update_type="message", event=self.message, **data)


async def resolve_batch(
    message: types.Message, data: dict[str, Any], *, limit: int
) -> tuple[list[BatchItem], int]:
    from handlers import admin, guest, music, universal, user

    if not message.from_user or message.is_automatic_forward or data.get("raw_state"):
        return [], 0
    text = message.text or message.caption or ""
    if text.lstrip().startswith("/"):
        return [], 0
    urls = list(dict.fromkeys(match[0].rstrip(_TRAILING) for match in _URL.finditer(text)))
    if len(urls) < 2 or user.router.parent_router is None:
        return [], 0

    excluded = {admin.router, guest.router, music.router, user.router}
    if message.chat.type != "private":
        excluded.add(universal.router)
    routers = [
        route for route in user.router.parent_router.sub_routers
        if route not in excluded and route.message.handlers
    ]

    items = []
    total = 0
    for url in urls:
        isolated = message.model_copy(update={
            "text": url if message.text else None,
            "caption": url if not message.text else None,
            "entities": None,
            "caption_entities": None,
        })
        for route in routers:
            context = {**data, "event_router": route}
            accepted, route_data = await route.message.check_root_filters(isolated, **context)
            if not accepted:
                continue
            for handler in route.message.handlers:
                matched, _ = await handler.check(isolated, **{**context, **route_data, "handler": handler})
                if matched:
                    total += 1
                    if len(items) < limit:
                        service = handler.callback.__module__.split(".")[-1]
                        items.append(BatchItem(service, isolated, route))
                    break
            else:
                continue
            break
    return items, total
