import asyncio
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import db
from app.auth import authenticate, create_app_session, get_current_user, register
from app.config import settings
from app.downloads import process_download, remove_user_file, validate_instagram_url
from app.oauth import begin_oauth, complete_oauth, provider_enabled, complete_oauth_link, begin_oauth_link
from app.deletion import REASON_LABELS, process_account_deletion, validate_reason


class AuthRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)


class DownloadRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class AccountDeletionRequest(BaseModel):
    reason_code: str = Field(min_length=1, max_length=40)
    reason_detail: str | None = Field(default=None, max_length=1000)


RATE_BUCKETS = defaultdict(deque)
RATE_LOCK = asyncio.Lock()


async def rate_limit(request: Request, limit: int, bucket: str) -> None:
    now = time.monotonic()
    key = f"{bucket}:{request.client.host if request.client else 'unknown'}"

    async with RATE_LOCK:
        events = RATE_BUCKETS[key]

        while events and now - events[0] >= 60:
            events.popleft()

        if len(events) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again shortly.",
                headers={"Retry-After": "60"},
            )

        events.append(now)


def session_cookie(response: JSONResponse, token: str) -> None:
    response.set_cookie(
        "reelengine_session",
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


def clear_session_cookie(response: JSONResponse) -> None:
    response.delete_cookie(
        "reelengine_session",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    db.cleanup_expired_sessions()
    db.mark_interrupted_downloads_failed()

    for row in db.list_incomplete_account_deletions():
        asyncio.create_task(process_account_deletion(row["id"]))

    yield


app = FastAPI(
    title="Soflas ReelEngine",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.mount("/app/web", StaticFiles(directory="/app/app/web"), name="web")
app.mount(
    "/assets",
    StaticFiles(directory="/app/app/web/public/assets"),
    name="assets",
)

MAX_REQUEST_BODY_BYTES = 64 * 1024


@app.middleware("http")
async def request_size_limit(request: Request, call_next):
    content_length = request.headers.get("content-length")

    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    {"detail": "Request body is too large."},
                    status_code=413,
                )
        except ValueError:
            return JSONResponse(
                {"detail": "Invalid Content-Length header."},
                status_code=400,
            )

    if request.method in {"POST", "PUT", "PATCH"}:
        body = await request.body()
        if len(body) > MAX_REQUEST_BODY_BYTES:
            return JSONResponse(
                {"detail": "Request body is too large."},
                status_code=413,
            )

    return await call_next(request)


@app.middleware("http")
async def global_api_rate_limit(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        try:
            await rate_limit(
                request,
                settings.rate_limit_per_minute,
                "api",
            )
        except HTTPException as exc:
            return JSONResponse(
                {"detail": exc.detail},
                status_code=exc.status_code,
                headers=exc.headers,
            )

    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )

    if settings.cookie_secure:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    return "User-agent: *\nDisallow: /\n"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/auth/providers")
async def auth_providers():
    return {
        "email": True,
        "google": provider_enabled("google"),
        "facebook": provider_enabled("facebook"),
    }


@app.get("/api/auth/google/start")
async def google_oauth_start(request: Request):
    await rate_limit(
        request,
        settings.login_rate_limit_per_minute,
        "oauth-google-start",
    )
    return begin_oauth("google")


@app.get("/api/auth/google/callback")
async def google_oauth_callback(request: Request):
    return await complete_oauth(request, "google")


@app.get("/api/auth/facebook/start")
async def facebook_oauth_start(request: Request):
    await rate_limit(
        request,
        settings.login_rate_limit_per_minute,
        "oauth-facebook-start",
    )
    return begin_oauth("facebook")


@app.get("/api/auth/facebook/callback")
async def facebook_oauth_callback(request: Request):
    return await complete_oauth(request, "facebook")


@app.get("/api/auth/facebook/link/start")
async def facebook_oauth_link_start(request: Request):
    await rate_limit(
        request,
        settings.login_rate_limit_per_minute,
        "oauth-facebook-link-start",
    )

    user = get_current_user(request)

    return begin_oauth_link(
        "facebook",
        user["id"],
    )


@app.get("/api/auth/facebook/link/callback")
async def facebook_oauth_link_callback(request: Request):
    return await complete_oauth_link(
        request,
        "facebook",
    )


@app.post("/api/auth/register")
async def api_register(request: Request, payload: AuthRequest):
    await rate_limit(
        request,
        settings.login_rate_limit_per_minute,
        "register",
    )

    user = register(
        payload.email,
        payload.password,
        payload.first_name or "",
        payload.last_name or "",
    )

    return JSONResponse(
        {
            "status": "created",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
            },
        },
        status_code=201,
    )


@app.post("/api/auth/login")
async def api_login(request: Request, payload: AuthRequest):
    await rate_limit(
        request,
        settings.login_rate_limit_per_minute,
        "login",
    )

    user = authenticate(payload.email, payload.password)
    token = create_app_session(user["id"])

    response = JSONResponse(
        {
            "status": "authenticated",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
            },
        }
    )

    session_cookie(response, token)
    return response


@app.post("/api/auth/logout")
async def api_logout(request: Request):
    token = request.cookies.get("reelengine_session")
    db.delete_session(token)

    response = JSONResponse({"status": "logged_out"})
    clear_session_cookie(response)
    return response


@app.get("/api/auth/me")
async def api_me(request: Request):
    token = request.cookies.get("reelengine_session")
    user = db.get_user_by_session(token) if token else None

    if not user:
        return {
            "authenticated": False,
            "user": None,
            "usage": None,
        }

    return {
        "authenticated": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "has_password": bool(user["password_hash"]),
        },
        "usage": {
            "accepted_today": db.get_usage(user["id"]),
            "daily_limit": settings.daily_download_limit,
        },
        "identities": [
            {
                "provider": row["provider"],
                "created_at": row["created_at"],
            }
            for row in db.list_auth_identities(user["id"])
        ],
    }


@app.post("/api/download")
async def start_download(request: Request, payload: DownloadRequest):
    await rate_limit(
        request,
        settings.rate_limit_per_minute,
        "download",
    )

    user = get_current_user(request)

    active_deletion = db.get_active_account_deletion_request(user["id"])

    if active_deletion:
        raise HTTPException(
            status_code=409,
            detail="Account deletion is in progress. New conversions are disabled.",
        )

    try:
        url = validate_instagram_url(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    download_id = db.reserve_download(user["id"], url)

    if not download_id:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily download limit reached "
                f"({settings.daily_download_limit} accepted conversions)."
            ),
        )

    asyncio.create_task(
        process_download(
            download_id,
            user["id"],
            url,
        )
    )

    return {
        "status": "queued",
        "download_id": download_id,
    }


@app.post("/api/account/deletion")
async def request_account_deletion(
    request: Request,
    payload: AccountDeletionRequest,
):
    await rate_limit(
        request,
        settings.login_rate_limit_per_minute,
        "account-deletion",
    )

    user = get_current_user(request)

    try:
        reason_code = validate_reason(payload.reason_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    reason_detail = (
        payload.reason_detail.strip()
        if payload.reason_detail
        else None
    )

    if reason_detail and len(reason_detail) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Additional feedback is too long",
        )

    existing = db.get_active_account_deletion_request(user["id"])

    if existing:
        return JSONResponse(
            {
                "status": "processing",
                "request_id": existing["id"],
            },
            status_code=202,
        )

    request_id = db.create_account_deletion_request(
        user["id"],
        reason_code,
        reason_detail,
    )

    if not request_id:
        existing = db.get_active_account_deletion_request(user["id"])

        if not existing:
            raise HTTPException(
                status_code=409,
                detail="Unable to create the deletion request",
            )

        request_id = existing["id"]

    asyncio.create_task(process_account_deletion(request_id))

    return JSONResponse(
        {
            "status": "processing",
            "request_id": request_id,
        },
        status_code=202,
    )


@app.get("/api/account/deletion/reasons")
async def account_deletion_reasons():
    return {
        "reasons": [
            {"code": code, "label": label}
            for code, label in REASON_LABELS.items()
        ]
    }


@app.get("/api/history")
async def history(request: Request):
    user = get_current_user(request)
    rows = db.list_downloads(user["id"])

    return [
        {
            "id": row["id"],
            "url": row["url"],
            "title": row["title"],
            "filesize": row["filesize"],
            "duration": row["duration"],
            "status": row["status"],
            "error_code": row["error_code"],
            "error_message": row["error_message"],
            "created_at": row["created_at"],
            "completed_at": row["completed_at"],
        }
        for row in rows
    ]


@app.get("/api/download/{download_id}")
async def download_status(request: Request, download_id: str):
    user = get_current_user(request)

    row = db.get_download_for_user(download_id, user["id"])

    if not row:
        raise HTTPException(status_code=404, detail="Download not found")

    return {
        "id": row["id"],
        "status": row["status"],
        "title": row["title"],
        "filesize": row["filesize"],
        "duration": row["duration"],
        "error_code": row["error_code"],
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
    }


def _parse_video_range(range_header: str | None, file_size: int) -> tuple[int, int] | None:
    if not range_header:
        return None

    invalid_headers = {
        "Content-Range": f"bytes */{file_size}",
    }

    if not range_header.startswith("bytes="):
        raise HTTPException(
            status_code=416,
            detail="Invalid range",
            headers=invalid_headers,
        )

    value = range_header[6:].strip()

    if not value or "," in value:
        raise HTTPException(
            status_code=416,
            detail="Invalid range",
            headers=invalid_headers,
        )

    start_text, separator, end_text = value.partition("-")

    if not separator:
        raise HTTPException(
            status_code=416,
            detail="Invalid range",
            headers=invalid_headers,
        )

    try:
        if start_text:
            start = int(start_text)
            if start < 0:
                raise ValueError

            if start >= file_size:
                raise HTTPException(
                    status_code=416,
                    detail="Range not satisfiable",
                    headers=invalid_headers,
                )

            if end_text:
                end = int(end_text)
                if end < start:
                    raise HTTPException(
                        status_code=416,
                        detail="Range not satisfiable",
                        headers=invalid_headers,
                    )
                end = min(end, file_size - 1)
            else:
                end = file_size - 1
        else:
            suffix_length = int(end_text)
            if suffix_length <= 0:
                raise ValueError

            if file_size == 0:
                raise HTTPException(
                    status_code=416,
                    detail="Range not satisfiable",
                    headers=invalid_headers,
                )

            start = max(file_size - suffix_length, 0)
            end = file_size - 1
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=416,
            detail="Invalid range",
            headers=invalid_headers,
        )

    return start, end


def _private_video_response(request: Request, filepath: Path) -> StreamingResponse:
    file_size = filepath.stat().st_size
    requested_range = _parse_video_range(
        request.headers.get("range"),
        file_size,
    )

    if requested_range is None:
        start = 0
        end = file_size - 1
        status_code = 200
    else:
        start, end = requested_range
        status_code = 206

    content_length = max(0, end - start + 1)

    async def stream():
        remaining = content_length

        with filepath.open("rb") as file:
            file.seek(start)

            while remaining:
                chunk = file.read(min(1024 * 1024, remaining))
                if not chunk:
                    break

                remaining -= len(chunk)
                yield chunk

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": f'inline; filename="{filepath.name}"',
    }

    if status_code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    return StreamingResponse(
        stream(),
        status_code=status_code,
        media_type="video/mp4",
        headers=headers,
    )


@app.get("/api/file/{download_id}")
async def get_file(request: Request, download_id: str):
    user = get_current_user(request)

    row = db.get_download_for_user(download_id, user["id"])

    if not row or row["status"] != "completed" or not row["filename"]:
        raise HTTPException(status_code=404, detail="File not found")

    user_root = Path(settings.download_dir, user["id"]).resolve()
    filepath = (user_root / row["filename"]).resolve()

    if user_root not in filepath.parents:
        raise HTTPException(status_code=404, detail="File not found")

    if not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return _private_video_response(request, filepath)


@app.delete("/api/history/{download_id}")
async def delete_history(request: Request, download_id: str):
    user = get_current_user(request)

    filename = db.delete_download(download_id, user["id"])

    if filename is None:
        raise HTTPException(status_code=404, detail="Download not found")

    remove_user_file(filename, user["id"])

    return {"status": "deleted"}


@app.get("/", response_class=HTMLResponse)
@app.get("/auth/sign-in", response_class=HTMLResponse)
@app.get("/auth/create-account", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
async def serve_ui():
    return Path("/app/index.html").read_text(encoding="utf-8")


@app.get("/privacy", response_class=HTMLResponse)
async def serve_privacy():
    return Path("/app/app/web/public/privacy.html").read_text(encoding="utf-8")


@app.get("/data-deletion", response_class=HTMLResponse)
async def serve_data_deletion():
    return Path("/app/app/web/public/data-deletion.html").read_text(encoding="utf-8")
