from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from handlers import bluesky
from services.platforms.bluesky_media import BlueskyPost, extract_post_url, parse_post


def test_only_canonical_bluesky_post_links_are_accepted():
    assert extract_post_url("Veja https://bsky.app/profile/edu.bsky.social/post/abc?ref=1") == (
        "https://bsky.app/profile/edu.bsky.social/post/abc"
    )
    assert extract_post_url("https://bsky.app/profile/edu.bsky.social") is None
    assert extract_post_url("https://bsky.app.evil.example/profile/edu.bsky.social/post/abc") is None


def test_gallery_and_quoted_video_keep_the_original_text():
    photo = "https://cdn.bsky.app/img/feed_fullsize/plain/photo"
    video = "https://video.bsky.app/watch/test/playlist.m3u8"
    post = parse_post({
        "record": {"text": "Original < &"},
        "embed": {
            "$type": "app.bsky.embed.recordWithMedia#view",
            "media": {
                "$type": "app.bsky.embed.gallery#view",
                "items": [{"fullsize": photo}, {"fullsize": "https://example.org/file"}],
            },
            "record": {
                "$type": "app.bsky.embed.record#view",
                "record": {
                    "$type": "app.bsky.embed.record#viewRecord",
                    "author": {"handle": "quoted.bsky.social"},
                    "value": {"text": "Quoted"},
                    "embeds": [{"$type": "app.bsky.embed.video#view", "playlist": video}],
                },
            },
        },
    })
    assert post.text == "Original < &\n\n↪ @quoted.bsky.social\nQuoted"
    assert [(entry.kind, entry.url) for entry in post.media] == [("photo", photo), ("video", video)]


@pytest.mark.asyncio
async def test_text_only_post_is_sent_even_with_captions_disabled(monkeypatch):
    msg = SimpleNamespace(
        text="https://bsky.app/profile/edu.bsky.social/post/abc",
        chat=SimpleNamespace(id=1), from_user=SimpleNamespace(id=1),
        answer=AsyncMock(),
    )
    lease = Mock()
    monkeypatch.setattr(bluesky, "is_banned", AsyncMock(return_value=False))
    monkeypatch.setattr(bluesky, "claim_message_request", AsyncMock(return_value=lease))
    monkeypatch.setattr(bluesky, "load_user_settings", AsyncMock(return_value={"captions": "off"}))
    monkeypatch.setattr(bluesky, "get_bot_url", AsyncMock(return_value="https://t.me/TestBot"))
    monkeypatch.setattr(bluesky, "fetch_post", AsyncMock(return_value=BlueskyPost("Original < &", ())))
    monkeypatch.setattr(bluesky, "download_media", AsyncMock())
    monkeypatch.setattr(bluesky, "handle_download_error", AsyncMock())

    await bluesky.process_bluesky_post(msg)

    assert "Original &lt; &amp;" in msg.answer.await_args.args[0]
    bluesky.download_media.assert_not_awaited()
    lease.mark_success.assert_called_once()
    lease.finish.assert_called_once()


@pytest.mark.asyncio
async def test_album_keeps_caption_once_and_sends_single_item_remainder(monkeypatch, tmp_path):
    from services.platforms.bluesky_media import BlueskyMedia

    msg = SimpleNamespace(
        text="https://bsky.app/profile/edu.bsky.social/post/abc",
        chat=SimpleNamespace(id=1), from_user=SimpleNamespace(id=1),
    )
    monkeypatch.setattr(bluesky, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(bluesky, "is_banned", AsyncMock(return_value=False))
    monkeypatch.setattr(bluesky, "claim_message_request", AsyncMock(return_value=Mock()))
    monkeypatch.setattr(bluesky, "load_user_settings", AsyncMock(return_value={"captions": "on"}))
    monkeypatch.setattr(bluesky, "get_bot_url", AsyncMock(return_value="https://t.me/TestBot"))
    media = tuple(BlueskyMedia("photo", f"https://cdn.bsky.app/{index}") for index in range(11))
    monkeypatch.setattr(bluesky, "fetch_post", AsyncMock(return_value=BlueskyPost("Original", media)))
    monkeypatch.setattr(bluesky, "download_media", AsyncMock(return_value=tmp_path / "image.jpg"))
    send = AsyncMock()
    monkeypatch.setattr(bluesky, "send_cached_media_entries", send)

    await bluesky.process_bluesky_post(msg)

    first, second = send.await_args_list
    assert len(first.args[1]) == 10
    assert "Original" in first.kwargs["caption"]
    assert len(second.args[1]) == 1
    assert second.kwargs["caption"] is None
    assert not list(tmp_path.iterdir())
