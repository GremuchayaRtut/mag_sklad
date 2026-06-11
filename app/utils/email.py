# TODO: replace with real email sending (SendGrid or SMTP)


async def send_invite_email(
    to_email: str,
    invite_token: str,
    inviter_name: str,
    business_name: str,
) -> None:
    print(
        f"[EMAIL] Invite sent to {to_email}, token: {invite_token} "
        f"(invited by {inviter_name}, business: {business_name})"
    )
