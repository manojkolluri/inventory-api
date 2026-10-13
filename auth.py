"""Google identity token Bearer auth for Cloud Run."""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    email: str


def _auth_disabled() -> bool:
    return os.getenv("AUTH_DISABLED", "false").lower() in {"1", "true", "yes"}


def _token_audience() -> str:
    # Must match the Cloud Run service URL used with --audiences=...
    return os.getenv("TOKEN_AUDIENCE", "").rstrip("/")


def verify_google_identity_token(token: str, audience: str) -> AuthenticatedUser:
    if not audience:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TOKEN_AUDIENCE is not set on the server",
        )
    try:
        claims = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            audience=audience,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid identity token: {exc}",
        ) from exc

    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has no email claim",
        )
    return AuthenticatedUser(email=email)


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    if _auth_disabled():
        return AuthenticatedUser(email="local-dev@example.com")

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer <identity-token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_google_identity_token(credentials.credentials, _token_audience())
