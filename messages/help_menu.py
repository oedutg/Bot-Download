import sys
from html import escape

HELP_SECTIONS = ("downloads", "audio", "usage", "commands")

_COPY = {
    "pt": {
        "start": "<b>Bem-vindo ao Save Vídeo DL Bot!</b>\n\nEnvie um link para baixar vídeo, foto, áudio ou arquivo. Para vários downloads, cole até {limit} links numa só mensagem.",
        "help": "<b>📖 Central de ajuda</b>\n\nEscolha um assunto abaixo.",
        "downloads": ("🎬 Vídeos e fotos",
            "• <b>Instagram, Threads e TikTok</b> — vídeos e carrosséis.\n"
            "• <b>YouTube</b> — vídeos e Shorts. Se aparecer a seleção, escolha Vídeo ou Áudio.\n"
            "• <b>X / Twitter e Pinterest</b> — vídeos e imagens; GIFs no X.\n"
            "• <b>Facebook e Kwai</b> — envie o link da publicação ou do vídeo.\n\n"
            "Copie o link da publicação em Compartilhar → Copiar link e envie ao bot."),
        "audio": ("🎧 Áudio e música",
            "• <b>SoundCloud</b> — envie o link da faixa.\n"
            "• <b>YouTube e YouTube Music</b> — envie o link e escolha Áudio quando a opção aparecer.\n"
            "• <b>Spotify</b> — o link identifica a música. O bot procura uma versão no YouTube, que pode ser diferente da gravação original."),
        "audible": "\n• <b>Audible</b> — no privado, use /audible para conectar sua conta e envie o link de um livro da sua biblioteca. Use /audible_logout para desconectar.",
        "usage": ("⚡ Inline e lote",
            "• <b>Inline</b> — digite <code>@{username} [link]</code> no campo de mensagem de um chat e escolha o resultado.\n"
            "• <b>Em lote</b> — envie até {limit} links em uma única mensagem."),
        "commands": ("⌨️ Comandos",
            "<b>Guia</b>\n/start — início\n/help — central de ajuda\n\n"
            "<b>Preferências</b>\n/settings — opções de envio e aparência\n/lang — idioma\n\n"
            "<b>Ferramentas</b>\n/trad — traduzir texto\n/stats — estatísticas\n/ping — tempo de resposta"),
        "back": "⬅️ Voltar",
        "help_button": "📖 Ajuda e comandos",
    },
    "en": {
        "start": "<b>Welcome to Save Vídeo DL Bot!</b>\n\nSend a link to download video, photos, audio, or files. For multiple downloads, paste up to {limit} links in one message.",
        "help": "<b>📖 Help center</b>\n\nChoose a topic below.",
        "downloads": ("🎬 Videos and photos",
            "• <b>Instagram, Threads, and TikTok</b> — videos and carousels.\n"
            "• <b>YouTube</b> — videos and Shorts. Choose Video or Audio when prompted.\n"
            "• <b>X / Twitter and Pinterest</b> — videos and images; GIFs on X.\n"
            "• <b>Facebook and Kwai</b> — send the post or video link.\n\n"
            "Use Share → Copy link on the post, then send the link to the bot."),
        "audio": ("🎧 Audio and music",
            "• <b>SoundCloud</b> — send the track link.\n"
            "• <b>YouTube and YouTube Music</b> — send the link and choose Audio when prompted.\n"
            "• <b>Spotify</b> — the link identifies the song. The bot looks for a version on YouTube, which may differ from the original recording."),
        "audible": "\n• <b>Audible</b> — in a private chat, use /audible to connect your account and send a link to a book in your library. Use /audible_logout to disconnect.",
        "usage": ("⚡ Inline and batch",
            "• <b>Inline</b> — type <code>@{username} [link]</code> in a chat’s message field and choose a result.\n"
            "• <b>Batch</b> — send up to {limit} links in one message."),
        "commands": ("⌨️ Commands",
            "<b>Guide</b>\n/start — home\n/help — help center\n\n"
            "<b>Preferences</b>\n/settings — delivery and appearance\n/lang — language\n\n"
            "<b>Tools</b>\n/trad — translate text\n/stats — statistics\n/ping — response time"),
        "back": "⬅️ Back",
        "help_button": "📖 Help and commands",
    },
    "es": {
        "start": "<b>¡Bienvenido a Save Vídeo DL Bot!</b>\n\nEnvía un enlace para descargar vídeo, fotos, audio o archivos. Para varias descargas, pega hasta {limit} enlaces en un solo mensaje.",
        "help": "<b>📖 Centro de ayuda</b>\n\nElige un tema.",
        "downloads": ("🎬 Vídeos y fotos",
            "• <b>Instagram, Threads y TikTok</b> — vídeos y carruseles.\n"
            "• <b>YouTube</b> — vídeos y Shorts. Elige Vídeo o Audio cuando aparezca la opción.\n"
            "• <b>X / Twitter y Pinterest</b> — vídeos e imágenes; GIF en X.\n"
            "• <b>Facebook y Kwai</b> — envía el enlace de la publicación o del vídeo.\n\n"
            "Copia el enlace de la publicación en Compartir → Copiar enlace y envíalo al bot."),
        "audio": ("🎧 Audio y música",
            "• <b>SoundCloud</b> — envía el enlace de la canción.\n"
            "• <b>YouTube y YouTube Music</b> — envía el enlace y elige Audio cuando aparezca la opción.\n"
            "• <b>Spotify</b> — el enlace identifica la canción. El bot busca una versión en YouTube, que puede ser distinta de la grabación original."),
        "audible": "\n• <b>Audible</b> — en privado, usa /audible para conectar tu cuenta y envía el enlace de un libro de tu biblioteca. Usa /audible_logout para desconectar.",
        "usage": ("⚡ Inline y por lotes",
            "• <b>Inline</b> — escribe <code>@{username} [enlace]</code> en un chat y elige un resultado.\n"
            "• <b>Por lotes</b> — envía hasta {limit} enlaces en un mensaje."),
        "commands": ("⌨️ Comandos",
            "<b>Guía</b>\n/start — inicio\n/help — centro de ayuda\n\n"
            "<b>Preferencias</b>\n/settings — opciones de envío y apariencia\n/lang — idioma\n\n"
            "<b>Herramientas</b>\n/trad — traducir texto\n/stats — estadísticas\n/ping — tiempo de respuesta"),
        "back": "⬅️ Volver",
        "help_button": "📖 Ayuda y comandos",
    },
}


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
_PLATFORM_COPY = {
    "pt": (
        "Plataformas suportadas", "Vídeos e fotos", "Música e audiolivros", "Arquivos",
        "Envie o link de MediaFire, MEGA ou Google Drive. Você também pode enviar um link direto de mídia compatível.",
        "Envie o link da faixa.", "Envie o link da publicação ou um link curto compatível.",
        "Envie o link do post para receber o texto ou a mídia disponível.",
        "Use os botões para abrir a ajuda, testar o modo inline ou ajustar as configurações.",
    ),
    "en": (
        "Supported platforms", "Videos and photos", "Music and audiobooks", "Files",
        "Send a MediaFire, MEGA, or Google Drive link. You can also send a supported direct media link.",
        "Send the track link.", "Send the post or a supported short link.",
        "Send the post link to receive the available text or media.",
        "Use the buttons to open help, try inline mode, or adjust settings.",
    ),
    "es": (
        "Plataformas compatibles", "Vídeos y fotos", "Música y audiolibros", "Archivos",
        "Envía un enlace de MediaFire, MEGA o Google Drive. También puedes enviar un enlace directo compatible.",
        "Envía el enlace de la canción.", "Envía el enlace de la publicación o un enlace corto compatible.",
        "Envía el enlace de la publicación para recibir el texto o el contenido disponible.",
        "Usa los botones para abrir la ayuda, probar el modo inline o ajustar la configuración.",
    ),
}


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


def help_copy(lang: str | None):
    return _COPY[_locale(lang)]


def _locale(lang: str | None) -> str:
    code = (lang or "pt").lower().replace("_", "-").split("-", 1)[0]
    return code if code in _COPY else "en"


def help_text(page: str, lang: str | None, username: str | None, limit: int, *, audible: bool = False) -> str:
    locale = _locale(lang)
    copy = _COPY[locale]
    platforms, video, audio, files, file_note, deezer_note, linkedin_note, reddit_note, footer = _PLATFORM_COPY[locale]
    audible = audible or _registered("audible")
    optional = tuple(name for name in ("LinkedIn", "Reddit") if _registered(name.lower()))

    if page == "start":
        intro = copy["start"].format(limit=limit).replace(
            "</b>", ' <tg-emoji emoji-id="5420141555233071341">❤️</tg-emoji></b>', 1
        )
        return "\n\n".join((
            intro, f"<b>{platforms}</b>", _platform_list(video, _VIDEO + optional),
            _platform_list(audio, _AUDIO + (("Audible",) if audible else ())),
            _platform_list(files, _FILES), footer,
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
            notes = {"LinkedIn": linkedin_note, "Reddit": reddit_note}
            blocks.extend(_block(f"{_icon(name)} {name}", notes[name]) for name in optional)
            blocks.append(_block(files, "\n".join(
                [*(f"{_icon(name)} {name}" for name in _FILES), "", file_note]
            )))
        if page == "audio":
            blocks.append(_block(f"{_icon('Deezer')} Deezer", deezer_note))
            if audible:
                blocks.append(_block("🎧 Audible", copy["audible"].removeprefix("\n")))
        body = "\n\n".join(blocks)
    return f"<b>{title}</b>\n\n" + body.format(
        username=escape(username or "SaveVidDLBot"), limit=limit
    )
