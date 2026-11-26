from aiogram.types import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)

_DESCRIPTIONS = {
    "en": {
        "start": "Open the main menu",
        "help": "Supported platforms and download help",
        "settings": "Personal settings",
        "group_settings": "Group settings",
        "lang": "Change language",
        "trad": "Translate text",
        "stats": "Bot statistics",
        "ping": "Check bot response time",
    },
    "pt": {
        "start": "Abrir o menu inicial",
        "help": "Plataformas e ajuda com downloads",
        "settings": "Configurações pessoais",
        "group_settings": "Configurações do grupo",
        "lang": "Alterar idioma",
        "trad": "Traduzir texto",
        "stats": "Estatísticas do bot",
        "ping": "Ver tempo de resposta",
    },
    "es": {
        "start": "Abrir el menú principal",
        "help": "Plataformas y ayuda con las descargas",
        "settings": "Configuración personal",
        "group_settings": "Configuración del grupo",
        "lang": "Cambiar idioma",
        "trad": "Traducir texto",
        "stats": "Estadísticas del bot",
        "ping": "Ver el tiempo de respuesta",
    },
}


def command_menus():
    private = ("start", "help", "settings", "lang", "trad", "stats", "ping")
    group = ("help", "trad", "stats", "ping")
    for scope, keys in (
        (BotCommandScopeAllPrivateChats(), private),
        (BotCommandScopeAllGroupChats(), group),
        (BotCommandScopeAllChatAdministrators(), ("help", "group_settings", *group[1:])),
    ):
        for lang, labels in _DESCRIPTIONS.items():
            commands = [
                BotCommand(
                    command="settings" if key == "group_settings" else key,
                    description=labels[key],
                )
                for key in keys
            ]
            yield scope, "" if lang == "en" else lang, commands
