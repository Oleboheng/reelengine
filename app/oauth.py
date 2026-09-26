import asyncio
import hashlib
import hmac
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse

from . import db
from .auth import create_app_session
from .config import settings


OAUTH_STATE_COOKIE = "reelengine_oauth_state"
OAUTH_LINK_STATE_COOKIE = "reelengine_oauth_link_state"
OAUTH_STATE_MAX_AGE = 600

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

FACEBOOK_AUTH_URL = (
    f"https://www.facebook.com/{settings.facebook_graph_version}/dialog/oauth"
)
FACEBOOK_TOKEN_URL = (
    f"https://graph.facebook.com/{settings.facebook_graph_version}/oauth/access_token"
)
FACEBOOK_USERINFO_URL = (
    f"https://graph.facebook.com/{settings.facebook_graph_version}/me"
)


def provider_enabled(provider: str) -> bool:
    if provider == "google":
        return bool(
            settings.google_client_id
            and settings.google_client_secret
        )

    if provider == "facebook":
        return bool(
            settings.facebook_client_id
            and settings.facebook_client_secret
        )

    return False


def redirect_uri(provider: str, mode: str = "login") -> str:
    if mode == "link":
        return f"{settings.public_base_url}/api/auth/{provider}/link/callback"

    return f"{settings.public_base_url}/api/auth/{provider}/callback"


def require_provider(provider: str) -> None:
    if not provider_enabled(provider):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authentication provider is not available.",
        )


def _sign_state(payload: str) -> str:
    signature = hmac.new(
        settings.session_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    return f"{payload}|{signature}"


def _create_state(provider: str) -> str:
    expires = int(__import__("time").time()) + OAUTH_STATE_MAX_AGE
    nonce = secrets.token_urlsafe(24)
    return _sign_state(f"{provider}|login|{expires}|{nonce}")


def _create_link_state(provider: str, user_id: str) -> str:
    expires = int(__import__("time").time()) + OAUTH_STATE_MAX_AGE
    nonce = secrets.token_urlsafe(24)
    return _sign_state(
        f"{provider}|link|{user_id}|{expires}|{nonce}"
    )


def _verify_state(
    provider: str,
    state: str,
    *,
    mode: str = "login",
    user_id: str | None = None,
) -> bool:
    parts = state.split("|")

    if mode == "login":
        if len(parts) != 5:
            return False

        state_provider, state_mode, expires_text, nonce, signature = parts

        if (
            state_provider != provider
            or state_mode != "login"
            or not nonce
        ):
            return False

        payload = f"{state_provider}|{state_mode}|{expires_text}|{nonce}"

    elif mode == "link":
        if len(parts) != 6:
            return False

        (
            state_provider,
            state_mode,
            state_user_id,
            expires_text,
            nonce,
            signature,
        ) = parts

        if (
            state_provider != provider
            or state_mode != "link"
            or not state_user_id
            or not user_id
            or state_user_id != user_id
            or not nonce
        ):
            return False

        payload = (
            f"{state_provider}|{state_mode}|{state_user_id}|"
            f"{expires_text}|{nonce}"
        )

    else:
        return False

    try:
        expires = int(expires_text)
    except ValueError:
        return False

    if expires < int(__import__("time").time()):
        return False

    expected = hmac.new(
        settings.session_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    return secrets.compare_digest(signature, expected)


def begin_oauth(provider: str) -> RedirectResponse:
    require_provider(provider)

    state = _create_state(provider)
    uri = redirect_uri(provider, "login")

    if provider == "google":
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }

        authorization_url = (
            GOOGLE_AUTH_URL
            + "?"
            + urllib.parse.urlencode(params)
        )
    else:
        params = {
            "client_id": settings.facebook_client_id,
            "redirect_uri": uri,
            "response_type": "code",
            "scope": "public_profile,email",
            "state": state,
        }

        authorization_url = (
            FACEBOOK_AUTH_URL
            + "?"
            + urllib.parse.urlencode(params)
        )

    response = RedirectResponse(
        authorization_url,
        status_code=302,
    )

    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        max_age=OAUTH_STATE_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )

    return response


def begin_oauth_link(
    provider: str,
    user_id: str,
) -> RedirectResponse:
    require_provider(provider)

    state = _create_link_state(provider, user_id)
    uri = redirect_uri(provider, "link")

    if provider == "google":
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }

        authorization_url = (
            GOOGLE_AUTH_URL
            + "?"
            + urllib.parse.urlencode(params)
        )
    else:
        params = {
            "client_id": settings.facebook_client_id,
            "redirect_uri": uri,
            "response_type": "code",
            "scope": "public_profile,email",
            "state": state,
        }

        authorization_url = (
            FACEBOOK_AUTH_URL
            + "?"
            + urllib.parse.urlencode(params)
        )

    response = RedirectResponse(
        authorization_url,
        status_code=302,
    )

    response.set_cookie(
        OAUTH_LINK_STATE_COOKIE,
        state,
        max_age=OAUTH_STATE_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )

    return response


def _request_json(
    url: str,
    *,
    method: str = "GET",
    data: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    body = None

    request_headers = {
        "Accept": "application/json",
        "User-Agent": "Soflas-ReelEngine/2.0",
    }

    if headers:
        request_headers.update(headers)

    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        request_headers["Content-Type"] = (
            "application/x-www-form-urlencoded"
        )

    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode())
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        ValueError,
    ):
        raise HTTPException(
            status_code=502,
            detail="The authentication provider could not be reached.",
        )


async def _google_profile(code: str) -> dict:
    token_response = await asyncio.to_thread(
        _request_json,
        GOOGLE_TOKEN_URL,
        method="POST",
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri("google"),
        },
    )

    access_token = token_response.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=502,
            detail="Google authentication could not be completed.",
        )

    profile = await asyncio.to_thread(
        _request_json,
        GOOGLE_USERINFO_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    return {
        "subject": profile.get("sub"),
        "email": profile.get("email"),
        "email_verified": profile.get("email_verified") is True,
        "first_name": profile.get("given_name"),
        "last_name": profile.get("family_name"),
    }


async def _facebook_profile(code: str) -> dict:
    token_response = await asyncio.to_thread(
        _request_json,
        FACEBOOK_TOKEN_URL
        + "?"
        + urllib.parse.urlencode(
            {
                "client_id": settings.facebook_client_id,
                "client_secret": settings.facebook_client_secret,
                "redirect_uri": redirect_uri("facebook"),
                "code": code,
            }
        ),
    )

    access_token = token_response.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=502,
            detail="Facebook authentication could not be completed.",
        )

    appsecret_proof = hmac.new(
        settings.facebook_client_secret.encode(),
        access_token.encode(),
        hashlib.sha256,
    ).hexdigest()

    profile_url = (
        FACEBOOK_USERINFO_URL
        + "?"
        + urllib.parse.urlencode(
            {
                "fields": "id,email,name",
                "access_token": access_token,
                "appsecret_proof": appsecret_proof,
            }
        )
    )

    profile = await asyncio.to_thread(
        _request_json,
        profile_url,
    )

    return {
        "subject": profile.get("id"),
        "email": profile.get("email"),
        "email_verified": bool(profile.get("email")),
    }


async def complete_oauth(
    request: Request,
    provider: str,
) -> RedirectResponse:
    require_provider(provider)

    state = request.query_params.get("state")
    saved_state = request.cookies.get(OAUTH_STATE_COOKIE)
    code = request.query_params.get("code")

    if request.query_params.get("error"):
        return _oauth_error("Authentication was cancelled.")

    if (
        not state
        or not saved_state
        or not secrets.compare_digest(state, saved_state)
        or not _verify_state(provider, state)
    ):
        return _oauth_error(
            "The authentication request expired. Please try again."
        )

    if not code:
        return _oauth_error(
            "The authentication provider did not return a valid authorization code."
        )

    if provider == "google":
        profile = await _google_profile(code)
    else:
        profile = await _facebook_profile(code)

    subject = str(profile.get("subject") or "").strip()
    email = str(profile.get("email") or "").strip().lower()
    email_verified = bool(profile.get("email_verified"))
    first_name = str(profile.get("first_name") or "").strip() or None
    last_name = str(profile.get("last_name") or "").strip() or None

    if not subject or not email or not email_verified:
        return _oauth_error(
            "The authentication provider did not provide an email address that ReelEngine can use."
        )

    user = db.get_user_by_identity(provider, subject)

    if not user:
        user = db.get_user_by_email(email)

        if user:
            linked = db.create_auth_identity(
                user["id"],
                provider,
                subject,
            )

            if not linked:
                user = db.get_user_by_identity(
                    provider,
                    subject,
                )

                if not user:
                    return _oauth_error(
                        "This account could not be linked."
                    )
        else:
            new_user = db.create_oauth_user(
                email,
                first_name,
                last_name,
            )

            if not db.create_auth_identity(
                new_user["id"],
                provider,
                subject,
            ):
                user = db.get_user_by_identity(
                    provider,
                    subject,
                )

                if not user:
                    return _oauth_error(
                        "This account could not be created."
                    )
            else:
                user = new_user

    if provider == "google":
        db.fill_missing_user_names(
            user["id"],
            first_name,
            last_name,
        )
        user = db.get_user(user["id"])

    token = create_app_session(user["id"])

    response = RedirectResponse(
        settings.public_base_url + "/app",
        status_code=302,
    )

    response.set_cookie(
        "reelengine_session",
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )

    response.delete_cookie(
        OAUTH_STATE_COOKIE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )

    return response


async def complete_oauth_link(
    request: Request,
    provider: str,
) -> RedirectResponse:
    require_provider(provider)

    session_token = request.cookies.get("reelengine_session")
    current_user = (
        db.get_user_by_session(session_token)
        if session_token
        else None
    )

    if not current_user:
        return _oauth_link_error(
            "Your session expired. Please sign in again."
        )

    state = request.query_params.get("state")
    saved_state = request.cookies.get(OAUTH_LINK_STATE_COOKIE)
    code = request.query_params.get("code")

    if request.query_params.get("error"):
        return _oauth_link_error(
            "Connecting Facebook was cancelled."
        )

    if (
        not state
        or not saved_state
        or not secrets.compare_digest(state, saved_state)
        or not _verify_state(
            provider,
            state,
            mode="link",
            user_id=current_user["id"],
        )
    ):
        return _oauth_link_error(
            "The connection request expired. Please try again."
        )

    if not code:
        return _oauth_link_error(
            "The authentication provider did not return a valid authorization code."
        )

    if provider == "google":
        profile = await _google_profile(code)
    else:
        profile = await _facebook_profile(code)

    subject = str(profile.get("subject") or "").strip()
    email = str(profile.get("email") or "").strip().lower()
    email_verified = bool(profile.get("email_verified"))
    first_name = str(profile.get("first_name") or "").strip() or None
    last_name = str(profile.get("last_name") or "").strip() or None

    if not subject or not email or not email_verified:
        return _oauth_link_error(
            "The authentication provider did not provide a verified email address."
        )

    existing_identity = db.get_user_by_identity(
        provider,
        subject,
    )

    if existing_identity:
        if existing_identity["id"] != current_user["id"]:
            return _oauth_link_error(
                "This Facebook account is already connected to another ReelEngine account."
            )

        db.fill_missing_user_names(
            current_user["id"],
            first_name,
            last_name,
        )

        return _oauth_link_success(
            "This Facebook account is already connected."
        )

    existing_email_user = db.get_user_by_email(email)

    if existing_email_user and existing_email_user["id"] != current_user["id"]:
        return _oauth_link_error(
            "That Facebook email is already associated with another ReelEngine account. Sign in to that account instead."
        )

    if not db.create_auth_identity(
        current_user["id"],
        provider,
        subject,
    ):
        existing_identity = db.get_user_by_identity(
            provider,
            subject,
        )

        if not existing_identity:
            return _oauth_link_error(
                "This Facebook account could not be connected."
            )

        if existing_identity["id"] != current_user["id"]:
            return _oauth_link_error(
                "This Facebook account is already connected to another ReelEngine account."
            )

    db.fill_missing_user_names(
        current_user["id"],
        first_name,
        last_name,
    )

    return _oauth_link_success(
        "Facebook is now connected to your ReelEngine account."
    )


def _oauth_link_success(message: str) -> RedirectResponse:
    params = urllib.parse.urlencode({
        "oauth_success": message,
    })

    response = RedirectResponse(
        f"{settings.public_base_url}/app?{params}",
        status_code=302,
    )

    response.delete_cookie(
        OAUTH_LINK_STATE_COOKIE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )

    return response


def _oauth_link_error(message: str) -> RedirectResponse:
    params = urllib.parse.urlencode({
        "oauth_error": message,
    })

    response = RedirectResponse(
        f"{settings.public_base_url}/app?{params}",
        status_code=302,
    )

    response.delete_cookie(
        OAUTH_LINK_STATE_COOKIE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )

    return response


def _oauth_error(message: str) -> RedirectResponse:
    params = urllib.parse.urlencode(
        {"oauth_error": message}
    )

    response = RedirectResponse(
        f"{settings.public_base_url}/auth/sign-in?{params}",
        status_code=302,
    )

    response.delete_cookie(
        OAUTH_STATE_COOKIE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )

    return response
