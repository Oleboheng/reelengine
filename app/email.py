from .config import settings


async def send_account_deletion_notification(
    *,
    request_id: str,
    account_email: str,
    reason_label: str,
    reason_detail: str | None,
    requested_at: str,
    completed_at: str,
) -> None:
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")

    import resend

    resend.api_key = settings.resend_api_key

    detail = reason_detail.strip() if reason_detail else ""

    body = f"""ReelEngine account deletion completed.

Request ID: {request_id}
Account email: {account_email}
Reason: {reason_label}
Requested at: {requested_at}
Completed at: {completed_at}
"""

    if detail:
        body += f"\nAdditional feedback:\n{detail}\n"

    await resend.Emails.send_async(
        {
            "from": settings.resend_from_email,
            "to": [settings.resend_admin_to],
            "subject": f"ReelEngine account deletion — {reason_label}",
            "text": body,
        },
        {"idempotency_key": f"account-deletion-{request_id}"},
    )
