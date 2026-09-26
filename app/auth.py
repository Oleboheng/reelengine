import re
from fastapi import Depends, HTTPException, Request, status
from pwdlib import PasswordHash

from . import db

password_hash = PasswordHash.recommended()
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_name(value: str, field_name: str) -> str:
    value = " ".join(value.strip().split())

    if not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required",
        )

    if len(value) > 80:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is too long",
        )

    if any(ord(char) < 32 for char in value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} contains invalid characters",
        )

    return value


def validate_email(email: str) -> str:
    normalized = db.normalize_email(email)
    if len(normalized) > 254 or not EMAIL_RE.fullmatch(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter a valid email address",
        )
    return normalized


def validate_password(password: str) -> None:
    if len(password) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 10 characters",
        )
    if len(password) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too long",
        )


def register(email: str, password: str, first_name: str, last_name: str):
    email = validate_email(email)
    validate_password(password)
    first_name = validate_name(first_name, "First name")
    last_name = validate_name(last_name, "Last name")

    if db.get_user_by_email(email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        )

    user_id = db.create_user(
        email,
        password_hash.hash(password),
        first_name,
        last_name,
    )
    return db.get_user(user_id)


def authenticate(email: str, password: str):
    email = validate_email(email)
    row = db.get_user_by_email(email)

    if not row or not row["password_hash"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not password_hash.verify(password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return row


def create_app_session(user_id: str) -> str:
    return db.create_session(user_id)


def get_current_user(request: Request):
    token = request.cookies.get("reelengine_session")
    user = db.get_user_by_session(token) if token else None

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return user


CurrentUser = Depends(get_current_user)
