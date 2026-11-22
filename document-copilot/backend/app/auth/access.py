from app.auth.dependencies import CurrentUser
from app.config import settings


def has_full_access(user: CurrentUser) -> bool:
    """True only for a confirmed address on the FULL_ACCESS_EMAILS list.

    Everyone else is in demo mode (recorded examples, no model call). The check uses the
    email Supabase verified from the login token, never anything the browser sends, and it
    ignores unconfirmed accounts so someone cannot sign up with another person's address.
    """
    return user.email_confirmed and user.email.lower() in settings.full_access_emails
