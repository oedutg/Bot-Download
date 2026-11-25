"""Read public Bluesky posts through the Bluesky AppView."""

import asyncio
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import aiohttp

POST_URL = re.compile(
    r"https?://(?:www\.)?bsky\.app/profile/"
    r"(?P<actor>[a-zA-Z0-9.:%_-]+)/post/(?P<key>[a-zA-Z0-9_-]+)"
    r"(?=$|[^a-zA-Z0-9_/%-])",
    re.IGNORECASE,
)
_ACTOR = re.compile(r"(?:[a-z0-9-]+\.)+[a-z0-9-]+|did:[a-z0-9]+:[a-z0-9.:%_-]+", re.I)
_APPVIEW = "https://public.api.bsky.app/xrpc"


class BlueskyPostUnavailable(Exception):
    """The AppView could not return this public post."""


class BlueskyMediaTooLarge(Exception):
    """The downloaded media exceeds the configured upload size."""


@dataclass(frozen=True)
class BlueskyMedia:
    kind: str
    url: str


@dataclass(frozen=True)
class BlueskyPost:
    text: str
    media: tuple[BlueskyMedia, ...]


def extract_post_url(text: str) -> str | None:
    match = POST_URL.search(text)
    if not match:
        return None
    actor, key = match.group("actor", "key")
    if not _ACTOR.fullmatch(actor):
        return None
    return f"https://bsky.app/profile/{actor}/post/{key}"


def _https_host(value: str, host: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme == "https" and parsed.netloc.lower() == host


def _embed_content(embed: dict, *, allow_quote: bool) -> tuple[list[str], list[BlueskyMedia]]:
    kind = embed.get("$type")
    if kind in {"app.bsky.embed.images#view", "app.bsky.embed.gallery#view"}:
        images = embed.get("items", []) if kind.endswith("gallery#view") else embed.get("images", [])
        return [], [
            BlueskyMedia("photo", image["fullsize"])
            for image in images
            if _https_host(image.get("fullsize") or "", "cdn.bsky.app")
        ]
    if kind == "app.bsky.embed.video#view":
        url = embed.get("playlist") or ""
        return [], [BlueskyMedia("video", url)] if _https_host(url, "video.bsky.app") else []
    if kind == "app.bsky.embed.external#view":
        link = embed.get("external") or {}
        return [text for text in (link.get("title"), link.get("uri")) if text], []
    if allow_quote and kind == "app.bsky.embed.recordWithMedia#view":
        text, media = _embed_content(embed.get("media") or {}, allow_quote=False)
        quote_text, quote_media = _embed_content(embed.get("record") or {}, allow_quote=True)
        return text + quote_text, media + quote_media
    if allow_quote and kind == "app.bsky.embed.record#view":
        quote = embed.get("record") or {}
        if quote.get("$type") != "app.bsky.embed.record#viewRecord":
            return [quote["displayName"]] if quote.get("displayName") else [], []
        author = quote.get("author") or {}
        handle = author.get("handle")
        text = (quote.get("value") or {}).get("text") or ""
        lines = [f"↪ @{handle}\n{text}".strip() if handle else text] if text or handle else []
        media = []
        for item in quote.get("embeds") or []:
            nested_lines, nested_media = _embed_content(item, allow_quote=False)
            lines.extend(nested_lines)
            media.extend(nested_media)
        return lines, media
    return [], []


def parse_post(post: dict) -> BlueskyPost:
    text = (post.get("record") or {}).get("text") or ""
    extra, media = _embed_content(post.get("embed") or {}, allow_quote=True)
    return BlueskyPost("\n\n".join(part for part in (text, *extra) if part), tuple(dict.fromkeys(media)))


async def fetch_post(session: aiohttp.ClientSession, url: str) -> BlueskyPost:
    match = POST_URL.fullmatch(url)
    if not match:
        raise BlueskyPostUnavailable
    actor, key = match.group("actor", "key")
    try:
        if not actor.lower().startswith("did:"):
            async with session.get(
                f"{_APPVIEW}/com.atproto.identity.resolveHandle",
                params={"handle": actor},
            ) as response:
                response.raise_for_status()
                actor = (await response.json())["did"]
        if not _ACTOR.fullmatch(actor) or not actor.lower().startswith("did:"):
            raise BlueskyPostUnavailable
        uri = f"at://{actor}/app.bsky.feed.post/{key}"
        async with session.get(
            f"{_APPVIEW}/app.bsky.feed.getPosts", params={"uris": uri}
        ) as response:
            response.raise_for_status()
            posts = (await response.json())["posts"]
    except (aiohttp.ClientError, TimeoutError, KeyError, ValueError) as exc:
        raise BlueskyPostUnavailable from exc
    for post in posts:
        if post.get("uri") == uri:
            return parse_post(post)
    raise BlueskyPostUnavailable


async def download_media(
    session: aiohttp.ClientSession,
    media: BlueskyMedia,
    directory: Path,
    index: int,
    max_size: int,
) -> Path:
    if media.kind == "photo":
        path = directory / f"photo-{index}.jpg"
        async with session.get(media.url, allow_redirects=False) as response:
            response.raise_for_status()
            if response.status != 200 or not response.content_type.startswith("image/"):
                raise BlueskyPostUnavailable
            size = 0
            with path.open("wb") as output:
                async for chunk in response.content.iter_chunked(65536):
                    size += len(chunk)
                    if size > max_size:
                        raise BlueskyMediaTooLarge
                    output.write(chunk)
        return path

    path = directory / f"video-{index}.mp4"
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "yt_dlp", "--ignore-config", "--quiet",
        "--no-playlist", "--socket-timeout", "15", "--retries", "1",
        "--fragment-retries", "1", "--max-filesize", str(max_size), "--remux-video", "mp4",
        "-o", str(path), "--", media.url,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        status = await asyncio.wait_for(proc.wait(), timeout=180)
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
    if status or not path.is_file() or path.stat().st_size == 0:
        raise BlueskyPostUnavailable
    if path.stat().st_size > max_size:
        raise BlueskyMediaTooLarge
    return path
