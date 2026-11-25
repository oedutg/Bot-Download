from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram import types

from handlers import commands, user
from messages.help_menu import HELP_SECTIONS, help_text


def test_start_keyboard_keeps_existing_actions_and_opens_help():
    keyboard = commands._help_keyboard("start", "SaveVidDLBot", "pt-BR")
    rows = keyboard.inline_keyboard
    assert rows[0][0].callback_data == "help_menu:help"
    assert rows[1][0].switch_inline_query_current_chat == ""
    assert rows[1][1].callback_data == "back_to_settings"
    assert all(button.url for button in rows[2])


def test_help_keyboard_lists_sections_and_links_back():
    keyboard = commands._help_keyboard("help", None, "es-MX")
    buttons = [button for row in keyboard.inline_keyboard for button in row]
    assert [button.callback_data for button in buttons] == [
        *(f"help_menu:{section}" for section in HELP_SECTIONS), "help_menu:start"
    ]
    assert buttons[-1].text == "⬅️ Volver"


def test_audible_help_uses_line_break_and_only_appears_when_available():
    assert "/audible" not in help_text("audio", "pt", None, 6)
    text = help_text("audio", "pt", None, 6, audible=True)
    assert "\n• <b>Audible</b>" in text
    assert "/audible_logout" in text
    assert r"\n" not in text


@pytest.mark.asyncio
async def test_help_callback_edits_existing_message(monkeypatch):
    message = types.Message.model_construct(chat=SimpleNamespace(id=42))
    call = SimpleNamespace(
        data="help_menu:usage", message=message,
        from_user=SimpleNamespace(id=3), answer=AsyncMock(),
    )
    edit = AsyncMock()
    monkeypatch.setattr(commands, "safe_edit_text", edit)
    monkeypatch.setattr(commands, "is_banned", AsyncMock(return_value=False))
    monkeypatch.setattr(commands, "get_bot_username", AsyncMock(return_value="MyBot"))
    monkeypatch.setattr(user.db, "get_language", AsyncMock(return_value="es-MX"))
    monkeypatch.setattr(user, "_MAX_BATCH_LINKS", 7)

    await commands.open_help_page(call)

    call.answer.assert_awaited_once()
    args, kwargs = edit.await_args
    assert args[0] is message
    assert "@MyBot [enlace]" in args[1]
    assert "7 enlaces" in args[1]
    assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data == "help_menu:help"
