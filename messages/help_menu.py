from html import escape

HELP_SECTIONS = ("downloads", "audio", "usage", "commands")

_COPY = {
    "pt": {
        "start": "<b>Bem-vindo ao Save Vídeo DL Bot!</b>\n\nEnvie um link para baixar vídeo, foto ou áudio. Para vários downloads, cole até {limit} links numa só mensagem.",
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
        "start": "<b>Welcome to Save Vídeo DL Bot!</b>\n\nSend a link to download video, photos, or audio. For multiple downloads, paste up to {limit} links in one message.",
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
        "start": "<b>¡Bienvenido a Save Vídeo DL Bot!</b>\n\nEnvía un enlace para descargar vídeo, fotos o audio. Para varias descargas, pega hasta {limit} enlaces en un solo mensaje.",
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


def help_copy(lang: str | None):
    code = (lang or "pt").lower().replace("_", "-").split("-", 1)[0]
    return _COPY.get(code, _COPY["en"])


def help_text(page: str, lang: str | None, username: str | None, limit: int, *, audible: bool = False) -> str:
    copy = help_copy(lang)
    if page in {"start", "help"}:
        return copy[page].format(limit=limit)

    title, body = copy[page]
    if page == "audio" and audible:
        body += copy["audible"]
    return f"<b>{title}</b>\n\n" + body.format(
        username=escape(username or "SaveVidDLBot"), limit=limit
    )
