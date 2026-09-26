import hashlib
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .config import settings


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def connect() -> sqlite3.Connection:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def init_db() -> None:
    conn = connect()
    try:
        legacy_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='history'"
        ).fetchone()

        new_downloads_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='downloads'"
        ).fetchone()

        if legacy_exists and not new_downloads_exists:
            conn.execute("ALTER TABLE history RENAME TO legacy_history")

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_identities (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                provider TEXT NOT NULL,
                provider_subject TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(provider, provider_subject)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS downloads (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                url TEXT NOT NULL,
                title TEXT,
                filename TEXT,
                filesize INTEGER,
                duration INTEGER,
                status TEXT NOT NULL,
                error_code TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS usage (
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                usage_date TEXT NOT NULL,
                accepted_downloads INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(user_id, usage_date)
            );

            CREATE TABLE IF NOT EXISTS account_deletion_requests (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                reason_code TEXT NOT NULL,
                reason_detail TEXT,
                status TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_account_deletion_active
                ON account_deletion_requests(user_id)
                WHERE status IN ('PENDING', 'PROCESSING');

            CREATE INDEX IF NOT EXISTS idx_account_deletion_user
                ON account_deletion_requests(user_id);

            CREATE INDEX IF NOT EXISTS idx_sessions_token_hash
                ON sessions(token_hash);

            CREATE INDEX IF NOT EXISTS idx_downloads_user_created
                ON downloads(user_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_usage_date
                ON usage(usage_date);
            """
        )

        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }

        if "first_name" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN first_name TEXT")

        if "last_name" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN last_name TEXT")

        download_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(downloads)").fetchall()
        }

        if "error_code" not in download_columns:
            conn.execute("ALTER TABLE downloads ADD COLUMN error_code TEXT")

        conn.commit()
    finally:
        conn.close()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def create_user(
    email: str,
    password_hash: Optional[str],
    first_name: str,
    last_name: str,
) -> str:
    user_id = str(uuid.uuid4())
    now = utcnow()

    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO users(
                id, email, password_hash, first_name, last_name,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                normalize_email(email),
                password_hash,
                first_name,
                last_name,
                now,
                now,
            ),
        )
        conn.commit()
        return user_id
    finally:
        conn.close()


def get_user_by_email(email: str):
    conn = connect()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (normalize_email(email),),
        ).fetchone()
    finally:
        conn.close()


def get_user(user_id: str):
    conn = connect()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()


def create_session(user_id: str) -> str:
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    session_id = str(uuid.uuid4())
    created = datetime.now(timezone.utc)
    expires = created + timedelta(hours=settings.session_ttl_hours)

    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO sessions(id, user_id, token_hash, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                user_id,
                token_hash,
                created.isoformat(),
                expires.isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return raw_token


def get_user_by_session(raw_token: str):
    if not raw_token:
        return None

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = utcnow()

    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT u.*
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
              AND s.expires_at > ?
            """,
            (token_hash, now),
        ).fetchone()

        if row:
            return row

        conn.execute(
            "DELETE FROM sessions WHERE token_hash = ?",
            (token_hash,),
        )
        conn.commit()
        return None
    finally:
        conn.close()


def delete_session(raw_token: str) -> None:
    if not raw_token:
        return

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    conn = connect()
    try:
        conn.execute(
            "DELETE FROM sessions WHERE token_hash = ?",
            (token_hash,),
        )
        conn.commit()
    finally:
        conn.close()


def cleanup_expired_sessions() -> None:
    conn = connect()
    try:
        conn.execute(
            "DELETE FROM sessions WHERE expires_at <= ?",
            (utcnow(),),
        )
        conn.commit()
    finally:
        conn.close()


def reserve_download(user_id: str, url: str):
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")

        deletion = conn.execute(
            """
            SELECT 1
            FROM account_deletion_requests
            WHERE user_id=?
              AND status IN ('PENDING', 'PROCESSING')
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

        if deletion:
            conn.rollback()
            return None

        date = today_utc()
        usage_row = conn.execute(
            """
            SELECT accepted_downloads
            FROM usage
            WHERE user_id = ? AND usage_date = ?
            """,
            (user_id, date),
        ).fetchone()

        current = usage_row["accepted_downloads"] if usage_row else 0

        if current >= settings.daily_download_limit:
            conn.rollback()
            return None

        if usage_row:
            conn.execute(
                """
                UPDATE usage
                SET accepted_downloads = accepted_downloads + 1
                WHERE user_id = ? AND usage_date = ?
                """,
                (user_id, date),
            )
        else:
            conn.execute(
                """
                INSERT INTO usage(user_id, usage_date, accepted_downloads)
                VALUES (?, ?, 1)
                """,
                (user_id, date),
            )

        download_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO downloads(
                id, user_id, url, status, created_at
            )
            VALUES (?, ?, ?, 'queued', ?)
            """,
            (download_id, user_id, url, utcnow()),
        )

        conn.commit()
        return download_id
    finally:
        conn.close()


def set_download_running(download_id: str) -> None:
    conn = connect()
    try:
        conn.execute(
            "UPDATE downloads SET status='running' WHERE id=?",
            (download_id,),
        )
        conn.commit()
    finally:
        conn.close()


def set_download_completed(
    download_id: str,
    title: str,
    filename: str,
    filesize: int,
    duration: Optional[int],
) -> None:
    conn = connect()
    try:
        conn.execute(
            """
            UPDATE downloads
            SET status='completed',
                title=?,
                filename=?,
                filesize=?,
                duration=?,
                completed_at=?
            WHERE id=?
            """,
            (title, filename, filesize, duration, utcnow(), download_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_download_failed(
    download_id: str,
    error_code: str,
    message: str,
) -> None:
    conn = connect()
    try:
        conn.execute(
            """
            UPDATE downloads
            SET status='failed',
                error_code=?,
                error_message=?,
                completed_at=?
            WHERE id=?
            """,
            (error_code, message[:500], utcnow(), download_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_download_for_user(download_id: str, user_id: str):
    conn = connect()
    try:
        return conn.execute(
            """
            SELECT *
            FROM downloads
            WHERE id=? AND user_id=?
            """,
            (download_id, user_id),
        ).fetchone()
    finally:
        conn.close()


def list_downloads(user_id: str):
    conn = connect()
    try:
        return conn.execute(
            """
            SELECT *
            FROM downloads
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, settings.history_limit),
        ).fetchall()
    finally:
        conn.close()


def delete_download(download_id: str, user_id: str):
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT filename
            FROM downloads
            WHERE id=? AND user_id=?
            """,
            (download_id, user_id),
        ).fetchone()

        if not row:
            return None

        conn.execute(
            "DELETE FROM downloads WHERE id=? AND user_id=?",
            (download_id, user_id),
        )
        conn.commit()
        return row["filename"]
    finally:
        conn.close()


def get_usage(user_id: str):
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT accepted_downloads
            FROM usage
            WHERE user_id=? AND usage_date=?
            """,
            (user_id, today_utc()),
        ).fetchone()

        return row["accepted_downloads"] if row else 0
    finally:
        conn.close()


def create_oauth_user(
    email: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
):
    user_id = str(uuid.uuid4())
    now = utcnow()

    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO users(
                id, email, password_hash, first_name, last_name,
                created_at, updated_at
            )
            VALUES (?, ?, NULL, ?, ?, ?, ?)
            """,
            (
                user_id,
                normalize_email(email),
                first_name,
                last_name,
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return get_user(user_id)


def fill_missing_user_names(
    user_id: str,
    first_name: Optional[str],
    last_name: Optional[str],
) -> None:
    conn = connect()
    try:
        conn.execute(
            """
            UPDATE users
            SET
                first_name = CASE
                    WHEN first_name IS NULL OR TRIM(first_name) = ''
                    THEN ?
                    ELSE first_name
                END,
                last_name = CASE
                    WHEN last_name IS NULL OR TRIM(last_name) = ''
                    THEN ?
                    ELSE last_name
                END,
                updated_at = ?
            WHERE id = ?
            """,
            (
                first_name,
                last_name,
                utcnow(),
                user_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def create_auth_identity(user_id: str, provider: str, subject: str) -> bool:
    try:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO auth_identities(
                    id, user_id, provider, provider_subject, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), user_id, provider, subject, utcnow()),
            )
            conn.commit()
            return True
        finally:
            conn.close()
    except sqlite3.IntegrityError:
        return False


def get_user_by_identity(provider: str, subject: str):
    conn = connect()
    try:
        return conn.execute(
            """
            SELECT u.*
            FROM auth_identities a
            JOIN users u ON u.id=a.user_id
            WHERE a.provider=? AND a.provider_subject=?
            """,
            (provider, subject),
        ).fetchone()
    finally:
        conn.close()


def list_auth_identities(user_id: str):
    conn = connect()
    try:
        return conn.execute(
            """
            SELECT provider, created_at
            FROM auth_identities
            WHERE user_id=?
            ORDER BY created_at ASC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()


def cleanup_old_downloads_for_user(user_id: str) -> list[str]:
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT id, filename
            FROM downloads
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT -1 OFFSET ?
            """,
            (user_id, settings.history_limit),
        ).fetchall()

        filenames = [
            row["filename"]
            for row in rows
            if row["filename"]
        ]

        for row in rows:
            conn.execute(
                "DELETE FROM downloads WHERE id=? AND user_id=?",
                (row["id"], user_id),
            )

        conn.commit()
        return filenames
    finally:
        conn.close()




def has_active_downloads(user_id: str) -> bool:
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT 1
            FROM downloads
            WHERE user_id=?
              AND status IN ('queued', 'running')
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def create_account_deletion_request(
    user_id: str,
    reason_code: str,
    reason_detail: str | None,
) -> str | None:
    request_id = str(uuid.uuid4())

    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO account_deletion_requests(
                id, user_id, reason_code, reason_detail,
                status, requested_at
            )
            VALUES (?, ?, ?, ?, 'PENDING', ?)
            """,
            (
                request_id,
                user_id,
                reason_code,
                reason_detail,
                utcnow(),
            ),
        )
        conn.commit()
        return request_id
    except sqlite3.IntegrityError:
        conn.rollback()
        return None
    finally:
        conn.close()


def get_account_deletion_request(request_id: str):
    conn = connect()
    try:
        return conn.execute(
            """
            SELECT *
            FROM account_deletion_requests
            WHERE id=?
            """,
            (request_id,),
        ).fetchone()
    finally:
        conn.close()


def get_active_account_deletion_request(user_id: str):
    conn = connect()
    try:
        return conn.execute(
            """
            SELECT *
            FROM account_deletion_requests
            WHERE user_id=?
              AND status IN ('PENDING', 'PROCESSING')
            ORDER BY requested_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    finally:
        conn.close()


def claim_account_deletion(request_id: str):
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute(
            """
            SELECT *
            FROM account_deletion_requests
            WHERE id=?
              AND status='PENDING'
            """,
            (request_id,),
        ).fetchone()

        if not row:
            conn.rollback()
            return None

        conn.execute(
            """
            UPDATE account_deletion_requests
            SET status='PROCESSING'
            WHERE id=? AND status='PENDING'
            """,
            (request_id,),
        )

        conn.commit()
        return row
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def complete_account_deletion_request(
    request_id: str,
    completed_at: str,
) -> None:
    conn = connect()
    try:
        conn.execute(
            """
            UPDATE account_deletion_requests
            SET status='COMPLETED',
                user_id=NULL,
                reason_detail=NULL,
                completed_at=?
            WHERE id=?
            """,
            (completed_at, request_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_user_and_complete_request(
    request_id: str,
    user_id: str,
    completed_at: str,
) -> None:
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute(
            "DELETE FROM users WHERE id=?",
            (user_id,),
        )

        conn.execute(
            """
            UPDATE account_deletion_requests
            SET status='COMPLETED',
                user_id=NULL,
                reason_detail=NULL,
                completed_at=?
            WHERE id=?
            """,
            (completed_at, request_id),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_incomplete_account_deletions():
    conn = connect()
    try:
        return conn.execute(
            """
            SELECT id
            FROM account_deletion_requests
            WHERE status IN ('PENDING', 'PROCESSING')
            ORDER BY requested_at ASC
            """
        ).fetchall()
    finally:
        conn.close()

def mark_interrupted_downloads_failed() -> None:
    conn = connect()
    try:
        conn.execute(
            """
            UPDATE downloads
            SET status='failed',
                error_message='Server restarted while this conversion was running',
                completed_at=?
            WHERE status IN ('queued', 'running')
            """,
            (utcnow(),),
        )
        conn.commit()
    finally:
        conn.close()
