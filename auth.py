"""Google identity token Bearer auth for Cloud Run."""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

_bearer = HTTPBearer(auto_error=False)

# Audience used by `gcloud auth print-identity-token` for user (human) accounts.
# `--audiences=<Cloud Run URL>` only works for service accounts.
_GCLOUD_SDK_AUDIENCE = "32555940559.apps.googleusercontent.com"


@dataclass(frozen=True)
class AuthenticatedUser:
    email: str


def _auth_disabled() -> bool:
    return os.getenv("AUTH_DISABLED", "false").lower() in {"1", "true", "yes"}


def _token_audiences() -> list[str]:
    audiences: list[str] = []
    configured = os.getenv("TOKEN_AUDIENCE", "").rstrip("/")
    if configured:
        audiences.append(configured)
    audiences.append(_GCLOUD_SDK_AUDIENCE)
    return audiences


def verify_google_identity_token(token: str) -> AuthenticatedUser:
    request = google_requests.Request()
    last_error: Exception | None = None

    for audience in _token_audiences():
        try:
            claims = id_token.verify_oauth2_token(token, request, audience=audience)
            break
        except ValueError as exc:
            last_error = exc
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid identity token: {last_error}",
        )

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

    return verify_google_identity_token(credentials.credentials)
