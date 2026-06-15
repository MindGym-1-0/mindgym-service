import asyncio
import logging
from typing import Any, Optional

from supabase_auth.errors import AuthApiError

from src.lib.supabase_client import get_supabase_admin_client, get_supabase_client, create_fresh_supabase_client

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised for invalid user credentials."""


class EmailNotConfirmedError(Exception):
    """Raised when Supabase accepts credentials but withholds a session until email is confirmed."""


class UpstreamAuthServiceError(Exception):
    """Raised when Supabase authentication is unavailable."""


class UserAlreadyExistsError(Exception):
    """Raised when signup is attempted for an existing user."""


class InvalidSignupInputError(Exception):
    """Raised when signup payload is rejected by Supabase validation rules."""


class SignupDisabledError(Exception):
    """Raised when email/password signup is disabled in Supabase settings."""


class AuthRateLimitError(Exception):
    """Raised when auth endpoints are rate limited."""


def _exc_status(exc: Exception) -> int | None:
    value = getattr(exc, "status", None)
    return value if isinstance(value, int) else None


def _exc_code(exc: Exception) -> str:
    value = getattr(exc, "code", "")
    return value.lower() if isinstance(value, str) else ""


def _normalize_user(user: Any) -> dict[str, Any]:
    metadata = user.user_metadata or {}
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "first_name": metadata.get("first_name", ""),
        "last_name": metadata.get("last_name", ""),
        "app_metadata": user.app_metadata,
        "user_metadata": user.user_metadata,
    }


def _normalize_session(session: Any) -> dict[str, Any] | None:
    if session is None:
        return None

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_in": session.expires_in,
    }


def _build_auth_payload(response: Any) -> dict[str, Any]:
    session = getattr(response, "session", None)
    user = getattr(response, "user", None)

    return {
        "authenticated": session is not None,
        "session": _normalize_session(session),
        "user": _normalize_user(user) if user is not None else None,
    }


def _user_is_email_confirmed(user: Any) -> bool:
    return bool(
        getattr(user, "email_confirmed_at", None) or getattr(user, "confirmed_at", None)
    )


def _map_supabase_auth_exception(exc: Exception, email: str) -> Exception:
    """Translate Supabase Auth errors into domain-specific exceptions."""

    if isinstance(exc, AuthApiError):
        code = (exc.code or "").lower()
        message = (exc.message or str(exc)).lower()
        if code == "email_not_confirmed" or "email not confirmed" in message:
            logger.info("Login blocked for email=%s because email is not confirmed", email)
            return EmailNotConfirmedError("Email address is not confirmed")
        if code == "invalid_credentials" or "invalid login credentials" in message:
            logger.info("Login failed for email=%s due to invalid credentials", email)
            return AuthenticationError("Invalid email or password")

    message = str(exc).lower()
    if "invalid login credentials" in message or "invalid_credentials" in message:
        logger.info("Login failed for email=%s due to invalid credentials", email)
        return AuthenticationError("Invalid email or password")

    logger.exception("Supabase authentication request failed for email=%s", email)
    return UpstreamAuthServiceError("Authentication provider unavailable")


def _validate_login_response(response: Any, email: str) -> None:
    """Ensure Supabase returned a usable session after a successful token exchange."""

    session = getattr(response, "session", None)
    user = getattr(response, "user", None)

    if session is not None and user is not None:
        return

    if user is not None and session is None:
        confirmed = _user_is_email_confirmed(user)
        logger.warning(
            "Supabase token exchange returned user without session for email=%s "
            "(email_confirmed=%s)",
            email,
            confirmed,
        )
        if not confirmed:
            raise EmailNotConfirmedError("Email address is not confirmed")
        raise UpstreamAuthServiceError(
            "Authentication provider returned an incomplete session"
        )

    logger.warning(
        "Supabase token exchange returned no session and no user for email=%s", email
    )
    raise AuthenticationError("Invalid email or password")


async def login_with_email_password(email: str, password: str) -> dict[str, Any]:
    """Authenticate user credentials against Supabase Auth."""

    client = get_supabase_client()

    try:
        response = await asyncio.to_thread(
            client.auth.sign_in_with_password,
            {"email": email, "password": password},
        )
    except Exception as exc:
        raise _map_supabase_auth_exception(exc, email) from exc

    _validate_login_response(response, email)
    return _build_auth_payload(response)


async def login_with_google_id_token(id_token: str) -> dict[str, Any]:
    """Authenticate a Google ID token with Supabase and normalize the session payload.

    On a user's first Google sign-in, no row exists yet in the `users` profile
    table (unlike email/password signup, which creates one immediately). We
    detect that case here, create the profile row the same way signup does,
    and flag the result as `is_new_user` so the caller can route the person
    through onboarding.
    """

    client = get_supabase_client()

    try:
        response = await asyncio.to_thread(
            client.auth.sign_in_with_id_token,
            {"provider": "google", "token": id_token},
        )
    except Exception as exc:
        logger.exception("Supabase Google token sign-in failed")
        raise UpstreamAuthServiceError("Google authentication failed") from exc

    _validate_login_response(response, "google_oauth")

    user = getattr(response, "user", None)
    is_new_user = False

    if user is not None:
        admin_client = get_supabase_admin_client()
        if admin_client:
            try:
                existing = await asyncio.to_thread(
                    lambda: admin_client.table("users")
                    .select("id")
                    .eq("id", str(user.id))
                    .execute()
                )
                if not existing.data:
                    is_new_user = True
                    await asyncio.to_thread(
                        lambda: admin_client.table("users").upsert({
                            "id": str(user.id),
                            "goal": "",
                            "stage": "exploring",
                            "anxiety_level": 5,
                        }).execute()
                    )
                    logger.info("Created profile for Google user_id=%s", user.id)
            except Exception:
                logger.warning(
                    "Failed to check/create profile for Google user_id=%s — "
                    "onboarding status may be incorrect",
                    user.id,
                )

    payload = _build_auth_payload(response)
    payload["is_new_user"] = is_new_user
    return payload


async def signup_with_email_password(
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
) -> dict[str, Any]:
    """Create a new Supabase Auth user."""

    client = get_supabase_client()

    try:
        response = await asyncio.to_thread(
            client.auth.sign_up,
            {
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "first_name": first_name,
                        "last_name": last_name,
                    },
                },
            },
        )
    except Exception as exc:
        message = str(exc).lower()
        status = _exc_status(exc)
        code = _exc_code(exc)

        if status == 429 or "rate limit" in message or "too many requests" in message:
            logger.warning("Signup rate-limited for email=%s", email)
            raise AuthRateLimitError("Too many signup attempts") from exc
        if "over_email_send_rate_limit" in code:
            logger.warning("Signup email send rate-limited for email=%s", email)
            raise AuthRateLimitError("Too many signup attempts") from exc
        if (
            "already registered" in message
            or "user already exists" in message
            or "already exists" in message
        ):
            logger.info(
                "Signup failed for email=%s because the user already exists", email
            )
            raise UserAlreadyExistsError("User already exists") from exc
        if status == 409:
            logger.info(
                "Signup failed for email=%s because user already exists (status=409)",
                email,
            )
            raise UserAlreadyExistsError("User already exists") from exc
        if (
            "password should be at least" in message
            or "invalid email" in message
            or "email address is invalid" in message
            or ("email address" in message and "is invalid" in message)
            or "weak password" in message
            or "validation failed" in message
        ):
            logger.info("Signup rejected by validation rules for email=%s", email)
            raise InvalidSignupInputError("Invalid signup input") from exc
        if status in (400, 422):
            logger.info(
                "Signup rejected by Supabase validation for email=%s (status=%s)",
                email,
                status,
            )
            raise InvalidSignupInputError("Invalid signup input") from exc
        if "signups not allowed" in message or "signup is disabled" in message:
            logger.info("Signup rejected because email/password signup is disabled")
            raise SignupDisabledError("Signup is disabled") from exc
        if status == 403:
            logger.info(
                "Signup rejected because email/password signup is forbidden (status=403)"
            )
            raise SignupDisabledError("Signup is disabled") from exc

        logger.exception("Supabase signup request failed for email=%s", email)
        raise UpstreamAuthServiceError("Authentication provider unavailable") from exc

    user = getattr(response, "user", None)
    if user is None:
        logger.exception("Supabase signup response missing user for email=%s", email)
        raise UpstreamAuthServiceError("Authentication provider unavailable")

    admin_client = get_supabase_admin_client()
    if admin_client and user:
        try:
            await asyncio.to_thread(
                lambda: admin_client.table("users").upsert({
                    "id": str(user.id),
                    "goal": "",
                    "stage": "exploring",
                    "anxiety_level": 5,
                }).execute()
            )
            logger.info("Created profile for user_id=%s", user.id)
        except Exception:
            logger.warning(
                "Failed to create profile for user_id=%s — session start may fail",
                user.id,
            )

    return _build_auth_payload(response)


async def fetch_authenticated_user(access_token: str) -> Optional[dict[str, Any]]:
    """Validate token against Supabase and return normalized user data."""

    client = get_supabase_client()

    try:
        response = await asyncio.to_thread(client.auth.get_user, access_token)
    except Exception:
        logger.exception("Supabase user fetch failed during token validation")
        return None

    user = getattr(response, "user", None)
    if user is None:
        return None

    return _normalize_user(user)


async def refresh_session_with_refresh_token(refresh_token: str) -> dict[str, Any]:
    """Refresh an auth session using a refresh token."""
    client = create_fresh_supabase_client()

    try:
        response = await asyncio.to_thread(client.auth.refresh_session, refresh_token)
    except Exception as exc:
        message = str(exc).lower()
        if (
            "invalid refresh token" in message
            or "refresh token not found" in message
            or "expired" in message
            or "invalid grant" in message
        ):
            raise AuthenticationError("Invalid or expired refresh token") from exc
        logger.exception("Supabase refresh session request failed")
        raise UpstreamAuthServiceError("Authentication provider unavailable") from exc

    session = getattr(response, "session", None)
    user = getattr(response, "user", None)
    if session is None or user is None:
        raise AuthenticationError("Invalid or expired refresh token")

    return _build_auth_payload(response)


async def revoke_auth_session(
    access_token: str | None, refresh_token: str | None = None
) -> bool:
    """Best-effort token revocation for logout; returns True when a revoke call succeeds."""

    if not access_token:
        return False

    admin_client = get_supabase_admin_client()
    if admin_client is not None:
        try:
            await asyncio.to_thread(
                admin_client.auth.admin.sign_out, access_token, "global"
            )
            return True
        except Exception:
            logger.exception("Failed admin-level Supabase sign out during logout")

    if refresh_token:
        try:
            client = create_fresh_supabase_client()
            await asyncio.to_thread(
                client.auth.set_session, access_token, refresh_token
            )
            await asyncio.to_thread(client.auth.sign_out)
            return True
        except Exception:
            logger.exception("Failed session-level Supabase sign out during logout")

    return False
