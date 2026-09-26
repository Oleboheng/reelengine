import asyncio
import shutil
from pathlib import Path

from . import db
from .config import settings
from .email import send_account_deletion_notification


REASON_LABELS = {
    "NO_LONGER_NEEDED": "I don't need ReelEngine anymore",
    "TECHNICAL_PROBLEMS": "I had technical problems",
    "NOT_SATISFIED": "ReelEngine wasn't what I expected",
    "LOW_USAGE": "I don't use it often enough",
    "CREATED_BY_MISTAKE": "I created my account by mistake",
    "PRIVACY_CONCERN": "I'm concerned about privacy",
    "OTHER": "Other",
}


async def process_account_deletion(request_id: str) -> None:
    request_row = db.claim_account_deletion(request_id)

    if not request_row:
        return

    user_id = request_row["user_id"]

    if not user_id:
        return

    while db.has_active_downloads(user_id):
        await asyncio.sleep(1)

    user = db.get_user(user_id)

    if not user:
        completed_at = db.utcnow()
        db.complete_account_deletion_request(request_id, completed_at)
        return

    user_root = Path(settings.download_dir).resolve()
    account_dir = (user_root / user_id).resolve()

    if user_root not in account_dir.parents:
        raise RuntimeError("Invalid account storage path")

    if account_dir.exists():
        if not account_dir.is_dir():
            raise RuntimeError("Account storage path is not a directory")
        shutil.rmtree(account_dir)

    completed_at = db.utcnow()

    db.delete_user_and_complete_request(
        request_id=request_id,
        user_id=user_id,
        completed_at=completed_at,
    )

    try:
        await send_account_deletion_notification(
            request_id=request_id,
            account_email=user["email"],
            reason_label=REASON_LABELS.get(
                request_row["reason_code"],
                request_row["reason_code"],
            ),
            reason_detail=request_row["reason_detail"],
            requested_at=request_row["requested_at"],
            completed_at=completed_at,
        )
    except Exception:
        # Account deletion is authoritative. Notification failure must
        # never restore or block the deleted account.
        pass


def validate_reason(reason_code: str) -> str:
    value = reason_code.strip().upper()

    if value not in REASON_LABELS:
        raise ValueError("Invalid deletion reason")

    return value
