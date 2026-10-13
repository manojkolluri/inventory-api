"""Google identity token Bearer auth for Cloud Run."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)

_GOOGLE_ISSUERS = {
    "https://accounts.google.com",
    "accounts.google.com",
}


@dataclass(frozen=True)
class AuthenticatedUser:
    email: str


def _auth_disabled() -> bool:
    return os.getenv("AUTH_DISABLED", "false").lower() in {"1", "true", "yes"}


def _jwt_claims(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("not a JWT")
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth-v3: Bearer value is not a JWT identity token",
        ) from exc


def verify_google_identity_token(token: str) -> AuthenticatedUser:
    """
    Extract caller email from a Google identity token.

    On Cloud Run with "Require authentication", Google IAM already verified the
    token before the request reached this app. User accounts cannot mint tokens
    with --audiences=<service-url>, so we trust IAM and validate JWT shape/claims.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth-v3: empty bearer token",
        )
    if token.startswith("ya29."):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth-v3: use print-identity-token, not print-access-token",
        )

    claims = _jwt_claims(token)
    iss = claims.get("iss")
    email = claims.get("email")

    if iss not in _GOOGLE_ISSUERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"auth-v3: unexpected token issuer: {iss}",
        )
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth-v3: token has no email claim",
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
            detail="auth-v3: Missing Authorization: Bearer <identity-token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_google_identity_token(credentials.credentials)
