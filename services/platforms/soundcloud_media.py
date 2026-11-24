import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Optional
from uuid import uuid4

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as YtDlpError

from services.download.queue import (
    QueueBackpressureError,
    QueueRateLimitError,
    get_download_queue,
)
from services.logger import logger as logging
from services.media.artist_names import normalize_artist_names
from services.platforms import strip_url_query
from services.platforms.ytdlp_helpers import mp3_extract_postprocessors, run_ytdlp_download
from utils.download_manager import (
    DownloadMetrics,
    DownloadProgress,
    DownloadQueueBusyError,
    DownloadRateLimitError,
    ProgressCallback,
    ResilientDownloader,
)

logging = logging.bind(service="soundcloud_media")
strip_soundcloud_url = strip_url_query


@dataclass
class SoundCloudTrack:
    source_url: str
    title: str
    artist: str
    thumbnail_url: Optional[str] = None
    duration_seconds: int = 0


class SoundCloudMediaService:
    def __init__(self, output_dir: str) -> None:
        self._output_dir = Path(output_dir).resolve()

    @staticmethod
    def _extract_track(url: str) -> Optional[SoundCloudTrack]:
        with YoutubeDL({
            "quiet": True,
            "socket_timeout": 15,
            "noplaylist": True,
            "extract_flat": "in_playlist",
        }) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info or info.get("_type") in {"playlist", "multi_video"}:
            return None
        return SoundCloudTrack(
            source_url=url,
            title=info.get("track") or info.get("title") or "SoundCloud Audio",
            artist=normalize_artist_names(info.get("artists") or info.get("artist") or info.get("uploader")) or "",
            thumbnail_url=info.get("thumbnail"),
            duration_seconds=round(info.get("duration") or 0),
        )

    async def fetch_track(self, url: str) -> Optional[SoundCloudTrack]:
        try:
            return await asyncio.to_thread(self._extract_track, url)
        except YtDlpError as exc:
            logging.error("yt-dlp SoundCloud metadata failed: error=%s", exc)
            return None

    def _download_mp3(
        self,
        url: str,
        path: Path,
        on_progress: Optional[Callable[[DownloadProgress], None]],
    ) -> DownloadMetrics:
        started_at = time.monotonic()
        last_update = started_at - 1

        def report_progress(data):
            nonlocal last_update
            now = time.monotonic()
            if on_progress is None or data["status"] != "downloading" or now - last_update < 0.8:
                return
            last_update = now
            on_progress(DownloadProgress(
                downloaded_bytes=data.get("downloaded_bytes") or 0,
                total_bytes=data.get("total_bytes") or data.get("total_bytes_estimate") or 0,
                elapsed=now - started_at,
                speed_bps=data.get("speed") or 0,
                eta_seconds=data.get("eta"),
                done=False,
            ))

        self._output_dir.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix="soundcloud-", dir=self._output_dir) as temp_dir:
            work_dir = Path(temp_dir)
            run_ytdlp_download(
                YoutubeDL,
                url,
                {
                    "format": "bestaudio/best",
                    "outtmpl": str(work_dir / "audio.%(ext)s"),
                    "postprocessors": mp3_extract_postprocessors(),
                    "quiet": True,
                    "noplaylist": True,
                    "playlist_items": "1",
                    "progress_hooks": [report_progress] if on_progress else [],
                    "socket_timeout": 15,
                },
            )
            mp3 = work_dir / "audio.mp3"
            size = mp3.stat().st_size
            mp3.replace(path)
        return DownloadMetrics(
            url=url,
            path=str(path),
            size=size,
            elapsed=time.monotonic() - started_at,
            used_multipart=False,
            resumed=False,
        )

    async def download_media(
        self,
        url: str,
        *,
        user_id: int,
        request_id: str,
        chat_id: Optional[int] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Optional[DownloadMetrics]:
        path = self._output_dir / f"soundcloud-{uuid4().hex}.mp3"
        cancelled = False
        progress_bridge = ResilientDownloader._build_progress_bridge(
            asyncio.get_running_loop(), on_progress
        )

        async def download():
            if cancelled:
                return None
            try:
                return await asyncio.to_thread(self._download_mp3, url, path, progress_bridge)
            except (YtDlpError, OSError) as exc:
                logging.error("yt-dlp SoundCloud download failed: error=%s", exc)
                return None
            finally:
                if cancelled:
                    path.unlink(missing_ok=True)

        try:
            return await get_download_queue().submit(
                download,
                source="soundcloud",
                priority=40,
                user_id=user_id,
                chat_id=chat_id,
                request_id=request_id,
            )
        except QueueRateLimitError as exc:
            raise DownloadRateLimitError(exc.retry_after) from exc
        except QueueBackpressureError as exc:
            raise DownloadQueueBusyError(exc.position) from exc
        except asyncio.CancelledError:
            cancelled = True
            path.unlink(missing_ok=True)
            raise
