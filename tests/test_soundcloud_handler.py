from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from conftest import FakeYoutubeDL
from handlers import soundcloud
from services.platforms import soundcloud_media
from utils.download_manager import DownloadMetrics


def test_strip_soundcloud_url_strips_tracking():
    url = "https://soundcloud.com/artist/track-name?si=abc123&utm_source=clipboard#frag"
    assert soundcloud.strip_soundcloud_url(url) == "https://soundcloud.com/artist/track-name"


@pytest.mark.asyncio
async def test_soundcloud_service_extracts_metadata_from_short_link(monkeypatch, tmp_path):
    url = "https://on.soundcloud.com/s5ZquEqx9nmtTyJPPh"
    extract_info = Mock(
        return_value={
            "title": "Track Title",
            "artists": ["Artist Name"],
            "thumbnail": "https://cdn.example.com/cover.jpg",
            "duration": 123.6,
        }
    )
    ydl = FakeYoutubeDL({})
    ydl.extract_info = extract_info
    monkeypatch.setattr(soundcloud_media, "YoutubeDL", lambda _opts: ydl)

    track = await soundcloud.SoundCloudService(str(tmp_path)).fetch_track(url)

    extract_info.assert_called_once_with(url, download=False)
    assert track.source_url == url
    assert track.title == "Track Title"
    assert track.artist == "Artist Name"
    assert track.thumbnail_url == "https://cdn.example.com/cover.jpg"
    assert track.duration_seconds == 124


@pytest.mark.asyncio
async def test_soundcloud_service_downloads_mp3_from_short_link(monkeypatch, tmp_path):
    url = "https://on.soundcloud.com/s5ZquEqx9nmtTyJPPh"
    downloads = []

    def build_downloader(options):
        ydl = FakeYoutubeDL(options, ext="mp3")
        downloads.append(ydl)
        return ydl

    async def run_queued(runner, **_kwargs):
        return await runner()

    queue = SimpleNamespace(submit=AsyncMock(side_effect=run_queued))
    monkeypatch.setattr(soundcloud_media, "get_download_queue", lambda: queue)
    monkeypatch.setattr(soundcloud_media, "YoutubeDL", build_downloader)

    service = soundcloud.SoundCloudService(str(tmp_path))
    metrics = await service.download_media(url, user_id=42, request_id="request")

    assert metrics is not None
    assert metrics.url == url
    assert downloads[0].urls == [url]
    assert downloads[0].options["postprocessors"][0]["preferredcodec"] == "mp3"
    assert [path.name for path in tmp_path.iterdir()] == [metrics.path.rsplit("/", 1)[-1]]
    assert queue.submit.await_args.kwargs["source"] == "soundcloud"


@pytest.mark.asyncio
async def test_inline_soundcloud_uses_bot_avatar_thumbnail(monkeypatch, tmp_path):
    settings = {
        "captions": "on",
        "delete_message": "off",
        "info_buttons": "on",
        "url_button": "on",
        "audio_button": "on",
    }
    token = soundcloud.create_inline_video_request(
        "soundcloud",
        "https://soundcloud.com/artist/track",
        42,
        settings,
    )
    result = SimpleNamespace(
        result_id=f"soundcloud_inline:{token}",
        inline_message_id="inline-message-1",
        from_user=SimpleNamespace(id=42, full_name="Inline User"),
    )
    audio_path = tmp_path / "track.mp3"
    audio_path.write_bytes(b"audio")
    metrics = DownloadMetrics(
        url="https://cdn.example.com/audio.mp3",
        path=str(audio_path),
        size=audio_path.stat().st_size,
        elapsed=0.1,
        used_multipart=False,
        resumed=False,
    )
    bot_avatar = object()

    monkeypatch.setattr(
        soundcloud.soundcloud_service,
        "fetch_track",
        AsyncMock(
            return_value=soundcloud.SoundCloudTrack(
                source_url="https://soundcloud.com/artist/track",
                title="Track Title",
                artist="Artist Name",
                thumbnail_url="https://cdn.example.com/cover.jpg",
                duration_seconds=199,
            )
        ),
    )
    monkeypatch.setattr(
        soundcloud.soundcloud_service,
        "download_media",
        AsyncMock(return_value=metrics),
    )
    monkeypatch.setattr(soundcloud.db, "get_language", AsyncMock(return_value="pt"))
    monkeypatch.setattr(soundcloud.db, "get_file_id", AsyncMock(return_value=None))
    monkeypatch.setattr(soundcloud.db, "add_file", AsyncMock())
    monkeypatch.setattr(soundcloud, "get_bot_url", AsyncMock(return_value="https://t.me/maxloadbot"))
    monkeypatch.setattr(soundcloud, "get_bot_avatar_thumbnail", AsyncMock(return_value=bot_avatar))
    prepared_metadata = SimpleNamespace(thumbnail_path=None, cleanup=Mock())
    monkeypatch.setattr(
        soundcloud,
        "prepare_mp3_metadata",
        AsyncMock(return_value=prepared_metadata),
    )
    monkeypatch.setattr(soundcloud, "safe_edit_inline_text", AsyncMock(return_value=True))
    monkeypatch.setattr(soundcloud, "safe_edit_inline_media", AsyncMock(return_value=True))
    monkeypatch.setattr(soundcloud, "remove_file", AsyncMock())
    monkeypatch.setattr(
        soundcloud.bot,
        "send_audio",
        AsyncMock(return_value=SimpleNamespace(audio=SimpleNamespace(file_id="cached-file-id"))),
    )

    await soundcloud.chosen_inline_soundcloud_result(result)

    send_kwargs = soundcloud.bot.send_audio.await_args.kwargs
    assert send_kwargs["thumbnail"] is bot_avatar
    assert send_kwargs["performer"] == "Artist Name"
    assert send_kwargs["duration"] == 199
    assert soundcloud.soundcloud_service.download_media.await_count == 1
    prepared_metadata.cleanup.assert_called_once_with()


@pytest.mark.asyncio
async def test_inline_soundcloud_query_prefers_track_thumbnail(monkeypatch):
    settings = {
        "captions": "on",
        "delete_message": "off",
        "info_buttons": "on",
        "url_button": "on",
        "audio_button": "on",
    }
    query = SimpleNamespace(
        from_user=SimpleNamespace(id=42),
        chat_type="inline",
        query="https://soundcloud.com/artist/track",
        answer=AsyncMock(),
    )
    track = soundcloud.SoundCloudTrack(
        source_url="https://soundcloud.com/artist/track",
        title="Track Title",
        artist="Artist Name",
        thumbnail_url="https://cdn.example.com/cover.jpg",
    )

    monkeypatch.setattr(soundcloud, "CHANNEL_ID", -1001234567890)
    monkeypatch.setattr(soundcloud, "send_analytics", AsyncMock())
    monkeypatch.setattr(soundcloud.db, "get_language", AsyncMock(return_value="pt"))
    monkeypatch.setattr(soundcloud.db, "user_settings", AsyncMock(return_value=settings))
    monkeypatch.setattr(soundcloud.soundcloud_service, "fetch_track", AsyncMock(return_value=track))

    await soundcloud.inline_soundcloud_query(query)

    results = query.answer.await_args.args[0]
    assert len(results) == 1
    assert results[0].thumbnail_url == "https://cdn.example.com/cover.jpg"
