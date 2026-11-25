import json
import sys
from functools import lru_cache
from html import escape
from pathlib import Path

try:
    from i18n import catalog, effective_locale, t
except ImportError:
    catalog = effective_locale = t = None

HELP_SECTIONS = ("downloads", "audio", "usage", "commands")

_ICONS = {
    "Instagram": ("5233671414023753035", "📷"),
    "Threads": ("5370693953236539466", "🧵"),
    "TikTok": ("5233597424622144804", "🎵"),
    "YouTube": ("5233311027612913110", "▶️"),
    "X / Twitter": ("5231309843435919433", "🐦"),
    "Pinterest": ("5233210422298974231", "📌"),
    "Facebook": ("5355254460635428635", "🌐"),
    "Kwai": ("4916102249417017903", "🤩"),
    "LinkedIn": ("5357053089859772828", "🌐"),
    "Reddit": ("5330321861949539755", "📱"),
    "SoundCloud": ("5233448977667492819", "🎧"),
    "Spotify": ("5391001065418172193", "🟢"),
    "Deezer": ("4985999144192574149", "📺"),
    "MediaFire": ("6161355483484523163", "💳"),
    "MEGA": ("5075640012217780006", "🤩"),
    "Google Drive": ("5352736961259913125", "💿"),
}
_VIDEO = ("Instagram", "Threads", "TikTok", "YouTube", "X / Twitter", "Pinterest", "Facebook", "Kwai")
_AUDIO = ("SoundCloud", "Spotify", "Deezer")
_FILES = ("MediaFire", "MEGA", "Google Drive")
def _registered(module: str) -> bool:
    handler = sys.modules.get(f"handlers.{module}")
    router = getattr(handler, "router", None)
    return getattr(router, "parent_router", None) is not None


def _icon(name: str) -> str:
    if name == "Audible":
        return "🎧"
    emoji_id, fallback = _ICONS[name]
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def _platform_list(title: str, names: tuple[str, ...]) -> str:
    return "\n".join([f"<b>{title}</b>", *(f"{_icon(name)} {name}" for name in names)])


def _block(title: str, body: str) -> str:
    return f"<blockquote expandable><b>{title}</b>\n{body}</blockquote>"


@lru_cache(maxsize=1)
def _menu_catalogs() -> dict[str, dict[str, str]]:
    return json.loads(Path(__file__).with_name("help_menu_locales.json").read_text(encoding="utf-8"))


def _menu_translation(key: str, lang: str | None) -> str:
    key = "help_menu." + key
    if effective_locale is not None:
        locale = effective_locale(lang)
        if key in catalog(locale) or key in catalog("en"):
            return t(key, lang)
    else:
        locale = (lang or "pt").lower().replace("_", "-").split("-", 1)[0]
    menus = _menu_catalogs()
    return menus.get(locale, menus["en"])[key]


def help_copy(lang: str | None) -> dict[str, str | tuple[str, str]]:
    copy = {
        key: _menu_translation(key, lang)
        for key in ("start", "help", "audible", "back", "help_button")
    }
    copy.update({
        section: (
            _menu_translation(section + ".title", lang),
            _menu_translation(section + ".body", lang),
        )
        for section in HELP_SECTIONS
    })
    return copy


def help_text(page: str, lang: str | None, username: str | None, limit: int, *, audible: bool = False) -> str:
    copy = help_copy(lang)
    platform_text = {
        key: _menu_translation("platforms." + key, lang)
        for key in ("platforms", "video", "audio", "files", "file_note", "deezer_note", "linkedin_note", "reddit_note", "footer")
    }
    audible = audible or _registered("audible")
    optional = tuple(name for name in ("LinkedIn", "Reddit") if _registered(name.lower()))

    if page == "start":
        intro = copy["start"].format(limit=limit).replace(
            "</b>", ' <tg-emoji emoji-id="5420141555233071341">❤️</tg-emoji></b>', 1
        )
        return "\n\n".join((
            intro, f"<b>{platform_text['platforms']}</b>", _platform_list(platform_text["video"], _VIDEO + optional),
            _platform_list(platform_text["audio"], _AUDIO + (("Audible",) if audible else ())),
            _platform_list(platform_text["files"], _FILES), platform_text["footer"],
        ))
    if page == "help":
        return copy[page]

    title, body = copy[page]
    if page in {"downloads", "audio", "usage"}:
        blocks = []
        for line in body.splitlines():
            if line.startswith("• <b>") and "</b> — " in line:
                heading, _, detail = line.removeprefix("• <b>").partition("</b> — ")
                blocks.append(_block(heading, detail))
            elif line:
                blocks.append(line)
        if page == "downloads":
            notes = {"LinkedIn": platform_text["linkedin_note"], "Reddit": platform_text["reddit_note"]}
            blocks.extend(_block(f"{_icon(name)} {name}", notes[name]) for name in optional)
            blocks.append(_block(platform_text["files"], "\n".join(
                [*(f"{_icon(name)} {name}" for name in _FILES), "", platform_text["file_note"]]
            )))
        if page == "audio":
            blocks.append(_block(f"{_icon('Deezer')} Deezer", platform_text["deezer_note"]))
            if audible:
                blocks.append(_block("🎧 Audible", copy["audible"].removeprefix("\n")))
        body = "\n\n".join(blocks)
    return f"<b>{title}</b>\n\n" + body.format(
        username=escape(username or "SaveVidDLBot"), limit=limit
    )
