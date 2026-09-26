import asyncio
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

from . import db
from .config import settings


ALLOWED_HOSTS = {
    "instagram.com",
    "www.instagram.com",
    "m.instagram.com",
}

DOWNLOAD_SEMAPHORE = asyncio.Semaphore(settings.max_concurrent_downloads)


def validate_instagram_url(url: str) -> str:
    value = url.strip()

    if len(value) > 2048:
        raise ValueError("URL is too long")

    parsed = urlparse(value)

    if parsed.scheme.lower() != "https":
        raise ValueError("Only HTTPS Instagram URLs are allowed")

    hostname = (parsed.hostname or "").lower().rstrip(".")

    if hostname not in ALLOWED_HOSTS:
        raise ValueError("Only Instagram URLs are supported")

    if not parsed.path or parsed.path == "/":
        raise ValueError("A specific Instagram post or reel URL is required")

    if any(part in parsed.path for part in ("..", "\\", "\x00")):
        raise ValueError("Invalid URL")

    if parsed.username or parsed.password:
        raise ValueError("Credentials in URLs are not allowed")

    return value


def user_dir(user_id: str) -> Path:
    root = Path(settings.download_dir).resolve()
    path = (root / user_id).resolve()

    if root not in path.parents:
        raise RuntimeError("Invalid storage path")

    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_error(exc: Exception) -> str:
    message = str(exc).strip().replace("\n", " ")
    return (message or "Download failed")[:500]


def classify_download_error(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        message = str(exc).lower()

        if "url" in message and "instagram" in message:
            return "INVALID_URL"

        if "duration" in message or "minute limit" in message:
            return "DURATION_TOO_LONG"

        if "file limit" in message or ("file" in message and "mb" in message):
            return "FILE_TOO_LARGE"

    message = str(exc).lower()

    if "private" in message or "login required" in message:
        return "PRIVATE_OR_UNAVAILABLE"

    if (
        "unsupported url" in message
        or "unsupported" in message
        or "not supported" in message
    ):
        return "UNSUPPORTED_CONTENT"

    if "timed out" in message or "timeout" in message:
        return "TIMEOUT"

    if "interrupted" in message:
        return "DOWNLOAD_INTERRUPTED"

    return "CONVERSION_FAILED"


def cookie_options() -> dict:
    if not settings.instagram_cookies_enabled:
        return {}

    cookie_file = Path(settings.instagram_cookie_file)

    if not cookie_file.is_file():
        raise RuntimeError(
            "Instagram cookie authentication is enabled but the cookie file is missing"
        )

    return {"cookiefile": str(cookie_file)}


def download_sync(download_id: str, user_id: str, url: str) -> None:
    directory = user_dir(user_id)
    output_template = str(directory / f"{download_id}.%(ext)s")

    options = {
        "outtmpl": output_template,
        "format": "best[ext=mp4]/best",
        "noplaylist": True,
        "max_filesize": settings.max_file_size_mb * 1024 * 1024,
        "restrictfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 2,
        "fragment_retries": 2,
    }

    options.update(cookie_options())

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

        duration = info.get("duration")
        if duration and duration > settings.max_duration_seconds:
            raise ValueError(
                f"Video exceeds the {settings.max_duration_seconds // 60}-minute limit"
            )

        estimated_size = info.get("filesize") or info.get("filesize_approx")
        if estimated_size and estimated_size > settings.max_file_size_mb * 1024 * 1024:
            raise ValueError(
                f"Video exceeds the {settings.max_file_size_mb} MB file limit"
            )

        ydl.download([url])

    matches = [
        path
        for path in directory.glob(f"{download_id}.*")
        if path.suffix.lower() not in {".part", ".ytdl"}
    ]

    if not matches:
        raise RuntimeError("Downloader completed without producing a file")

    filepath = matches[0]

    if filepath.stat().st_size > settings.max_file_size_mb * 1024 * 1024:
        filepath.unlink(missing_ok=True)
        raise ValueError(
            f"Downloaded file exceeds the {settings.max_file_size_mb} MB file limit"
        )

    title = info.get("title") or "Instagram Reel"

    db.set_download_completed(
        download_id,
        title,
        filepath.name,
        filepath.stat().st_size,
        duration,
    )


async def process_download(download_id: str, user_id: str, url: str) -> None:
    async with DOWNLOAD_SEMAPHORE:
        db.set_download_running(download_id)

        try:
            await asyncio.to_thread(
                download_sync,
                download_id,
                user_id,
                url,
            )
        except Exception as exc:
            try:
                directory = user_dir(user_id)
                for path in directory.glob(f"{download_id}.*"):
                    if path.is_file():
                        path.unlink(missing_ok=True)
            except Exception:
                pass

            db.set_download_failed(
                download_id,
                classify_download_error(exc),
                safe_error(exc),
            )

        try:
            removed = db.cleanup_old_downloads_for_user(user_id)
            for filename in removed:
                remove_user_file(filename, user_id)
        except Exception:
            pass


def remove_user_file(filename: str, user_id: str) -> None:
    if not filename:
        return

    directory = user_dir(user_id)
    candidate = (directory / filename).resolve()

    if directory.resolve() not in candidate.parents:
        raise RuntimeError("Invalid file path")

    if candidate.is_file():
        candidate.unlink(missing_ok=True)
