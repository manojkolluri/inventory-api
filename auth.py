"""Google identity token Bearer auth for Cloud Run."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

_bearer = HTTPBearer(auto_error=False)

# Audience used by `gcloud auth print-identity-token` for user accounts.
_GCLOUD_SDK_AUDIENCE = "32555940559.apps.googleusercontent.com"
_GOOGLE_ISSUERS = {
    "https://accounts.google.com",
    "accounts.google.com",
}


@dataclass(frozen=True)
class AuthenticatedUser:
    email: str


def _auth_disabled() -> bool:
    return os.getenv("AUTH_DISABLED", "false").lower() in {"1", "true", "yes"}


def _on_cloud_run() -> bool:
    return bool(os.getenv("K_SERVICE"))


def _token_audiences() -> list[str]:
    audiences: list[str] = []
    configured = os.getenv("TOKEN_AUDIENCE", "").rstrip("/")
    if configured:
        audiences.append(configured)
    audiences.append(_GCLOUD_SDK_AUDIENCE)
    return audiences


def _unverified_claims(token: str) -> dict:
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization Bearer value is not a valid JWT identity token",
        ) from exc


def _user_from_claims(claims: dict) -> AuthenticatedUser:
    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has no email claim",
        )
    return AuthenticatedUser(email=email)


def verify_google_identity_token(token: str) -> AuthenticatedUser:
    if not token or token.startswith("ya29."):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Expected an identity token from "
                "`gcloud auth print-identity-token` "
                "(not an access token from print-access-token)"
            ),
        )

    request = google_requests.Request()
    last_error: Exception | None = None

    for audience in _token_audiences():
        try:
            claims = id_token.verify_oauth2_token(
                token,
                request,
                audience=audience,
                clock_skew_in_seconds=60,
            )
            return _user_from_claims(claims)
        except TypeError:
            # Older google-auth without clock_skew_in_seconds
            try:
                claims = id_token.verify_oauth2_token(token, request, audience=audience)
                return _user_from_claims(claims)
            except ValueError as exc:
                last_error = exc
        except ValueError as exc:
            last_error = exc

    # On Cloud Run with "Require authentication", Google already validated the
    # caller at the IAM layer. Accept Google-issued JWTs and read the email.
    if _on_cloud_run():
        claims = _unverified_claims(token)
        if claims.get("iss") in _GOOGLE_ISSUERS and claims.get("email"):
            return _user_from_claims(claims)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Invalid identity token: {last_error}",
    )


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
