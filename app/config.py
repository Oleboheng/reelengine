import os
from dataclasses import dataclass


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "production")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    session_secret: str = os.getenv("SESSION_SECRET", "")
    session_ttl_hours: int = int(os.getenv("SESSION_TTL_HOURS", "168"))
    cookie_secure: bool = env_bool("COOKIE_SECURE", True)

    daily_download_limit: int = int(os.getenv("DAILY_DOWNLOAD_LIMIT", "10"))
    history_limit: int = int(os.getenv("HISTORY_LIMIT", "10"))
    max_concurrent_downloads: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "2"))
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "200"))
    max_duration_seconds: int = int(os.getenv("MAX_DURATION_SECONDS", "600"))

    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
    login_rate_limit_per_minute: int = int(os.getenv("LOGIN_RATE_LIMIT_PER_MINUTE", "8"))

    instagram_cookies_enabled: bool = env_bool("INSTAGRAM_COOKIES_ENABLED", False)
    instagram_cookie_file: str = os.getenv(
        "INSTAGRAM_COOKIE_FILE",
        "/run/secrets/instagram_cookies",
    )

    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

    facebook_client_id: str = os.getenv("FACEBOOK_CLIENT_ID", "")
    facebook_client_secret: str = os.getenv("FACEBOOK_CLIENT_SECRET", "")
    facebook_graph_version: str = os.getenv(
        "FACEBOOK_GRAPH_VERSION",
        "v26.0",
    )

    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    resend_from_email: str = os.getenv(
        "RESEND_FROM_EMAIL",
        "ReelEngine <admin@soflasdevelopments.co.za>",
    )
    resend_admin_to: str = os.getenv(
        "RESEND_ADMIN_TO",
        "admin@soflasdevelopments.co.za",
    )

    db_path: str = os.getenv("DB_PATH", "/app/data/history.db")
    download_dir: str = os.getenv("DOWNLOAD_DIR", "/app/downloads")


settings = Settings()

if len(settings.session_secret) < 32:
    raise RuntimeError("SESSION_SECRET must be at least 32 characters")
