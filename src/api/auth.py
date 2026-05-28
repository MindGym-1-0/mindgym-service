import logging

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status

from src.lib.auth_dependencies import (
    _extract_bearer_token,
    _extract_cookie_token,
    get_current_user,
)
from src.lib.auth_service import (
    AuthRateLimitError,
    AuthenticationError,
    InvalidSignupInputError,
    SignupDisabledError,
    UpstreamAuthServiceError,
    UserAlreadyExistsError,
    revoke_auth_session,
    login_with_email_password,
    signup_with_email_password,
)
from src.lib.config import get_settings
from src.types.auth import AuthResponse, LoginRequest, LogoutResponse, SignupRequest

router = APIRouter(prefix="/auth", tags=["auth"])
v1_router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _cookie_config() -> dict:
    settings = get_settings()
    return {
        "httponly": True,
        "secure": settings.resolved_auth_cookie_secure,
        "samesite": settings.resolved_auth_cookie_samesite,
        "path": "/",
        "domain": settings.auth_cookie_domain,
    }


def _set_auth_cookies(response: Response, auth_result: dict) -> None:
    cookie_cfg = _cookie_config()
    session = auth_result.get("session") or {}
    response.set_cookie(
        key="access_token",
        value=session.get("access_token", ""),
        max_age=session.get("expires_in") or 3600,
        **cookie_cfg,
    )

    refresh_token = session.get("refresh_token")
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=60 * 60 * 24,
            **cookie_cfg,
        )


def _clear_auth_cookies(response: Response) -> None:
    cookie_cfg = _cookie_config()
    response.delete_cookie(
        key="access_token", path="/", domain=cookie_cfg.get("domain")
    )
    response.delete_cookie(
        key="refresh_token", path="/", domain=cookie_cfg.get("domain")
    )


def _as_auth_response(auth_result: dict, message: str | None = None) -> AuthResponse:
    return AuthResponse.model_validate(
        {
            "authenticated": bool(auth_result.get("authenticated")),
            "user": auth_result.get("user"),
            "message": message,
        }
    )


@router.post(
    "/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def signup(payload: SignupRequest, response: Response) -> AuthResponse:
    """Create a Supabase Auth user and persist the session when available."""

    try:
        auth_result = await signup_with_email_password(
            payload.email, 
            payload.password,
            payload.first_name,
            payload.last_name
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        ) from exc
    except InvalidSignupInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or password format",
        ) from exc
    except SignupDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Signup is currently disabled",
        ) from exc
    except AuthRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many signup attempts. Please try again later.",
        ) from exc
    except UpstreamAuthServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected signup error for email=%s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected signup error",
        ) from exc

    if auth_result.get("authenticated"):
        _set_auth_cookies(response, auth_result)

    logger.info("User signup successful for email=%s", payload.email)
    return _as_auth_response(auth_result, message="Signup successful")


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, response: Response) -> AuthResponse:
    """Authenticate with Supabase and set secure HTTP-only cookies."""

    try:
        auth_result = await login_with_email_password(payload.email, payload.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc
    except UpstreamAuthServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected login error for email=%s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected login error",
        ) from exc

    _set_auth_cookies(response, auth_result)
    logger.info("User login successful for email=%s", payload.email)
    return _as_auth_response(auth_result, message="Login successful")


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    authorization: str | None = Header(default=None),
    access_token: str | None = Cookie(default=None),
    refresh_token: str | None = Cookie(default=None),
) -> LogoutResponse:
    """Clear cookies and revoke the current Supabase session when possible."""

    token = _extract_bearer_token(authorization) or _extract_cookie_token(access_token)
    revoked = False
    try:
        revoked = await revoke_auth_session(token, refresh_token)
    except Exception:
        logger.exception("Unexpected logout error")

    _clear_auth_cookies(response)
    if not token:
        logger.info("Logout request without active session token")
        return LogoutResponse(message="No active session")
    if revoked:
        logger.info("Logout completed with remote session revocation")
        return LogoutResponse(message="Signed out")

    logger.info(
        "Logout completed locally; remote session revocation skipped or unavailable"
    )
    return LogoutResponse(message="Signed out locally")


@router.get("/me", response_model=AuthResponse)
async def read_me(current_user: dict = Depends(get_current_user)) -> AuthResponse:
    """Return the authenticated user profile."""

    return AuthResponse(authenticated=True, user=current_user)


@v1_router.get("/me", response_model=AuthResponse)
async def read_me_v1(current_user: dict = Depends(get_current_user)) -> AuthResponse:
    """Example protected endpoint for downstream feature teams."""

    return AuthResponse(authenticated=True, user=current_user)
