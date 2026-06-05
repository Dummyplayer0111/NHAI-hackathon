import base64
import hashlib
import hmac
import json
import secrets
from typing import Any, Dict, Optional

from fastapi import Header, HTTPException

from app.config import ADMIN_API_KEY


def generate_secret() -> str:
    return secrets.token_urlsafe(32)


def hash_secret(secret: str) -> str:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii")


def canonical_payload(payload: Dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sign_payload(payload: Dict[str, Any], secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        canonical_payload(payload),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii")


def verify_signature(payload: Dict[str, Any], secret: str, signature: str) -> bool:
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)


def require_admin_api_key(
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
) -> None:
    if not x_admin_api_key:
        raise HTTPException(status_code=401, detail="missing_admin_api_key")
    if not hmac.compare_digest(x_admin_api_key, ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="invalid_admin_api_key")
