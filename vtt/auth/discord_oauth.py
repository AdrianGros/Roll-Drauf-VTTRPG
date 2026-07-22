"""Discord OAuth2 helpers and bot verification client."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import time
from urllib.parse import urlencode

import requests
from flask import current_app


class DiscordAuthError(RuntimeError):
    """Raised when Discord auth or bot verification fails."""


def discord_login_enabled() -> bool:
    return bool(current_app.config.get("DISCORD_LOGIN_ENABLED"))


def _required_config_value(key: str) -> str:
    value = current_app.config.get(key)
    if not value:
        raise DiscordAuthError(f"Missing Discord configuration: {key}")
    return str(value)


def _request_timeout() -> float:
    timeout = current_app.config.get("DISCORD_REQUEST_TIMEOUT_SECONDS", 10.0)
    try:
        return float(timeout)
    except (TypeError, ValueError):
        return 10.0


def _normalize_scopes() -> list[str]:
    scopes = current_app.config.get("DISCORD_OAUTH_SCOPES") or ["identify", "email"]
    if isinstance(scopes, str):
        scopes = [scope.strip() for scope in scopes.split(",") if scope.strip()]
    normalized = [scope.strip() for scope in scopes if str(scope).strip()]
    if "identify" not in normalized:
        normalized.insert(0, "identify")
    if "email" not in normalized:
        normalized.append("email")
    return normalized


def build_discord_authorize_url(state: str, redirect_uri: str, remember_me: bool = False) -> str:
    authorization_base = current_app.config.get(
        "DISCORD_AUTHORIZATION_BASE_URL", "https://discord.com/oauth2/authorize"
    )
    client_id = _required_config_value("DISCORD_CLIENT_ID")
    scopes = " ".join(_normalize_scopes())
    params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": scopes,
        "redirect_uri": redirect_uri,
        "state": state,
        "prompt": "consent",
    }
    return f"{authorization_base}?{urlencode(params)}"


def exchange_discord_code(code: str, redirect_uri: str) -> dict:
    token_url = current_app.config.get("DISCORD_TOKEN_URL", "https://discord.com/api/oauth2/token")
    client_id = _required_config_value("DISCORD_CLIENT_ID")
    client_secret = _required_config_value("DISCORD_CLIENT_SECRET")
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    response = requests.post(
        token_url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        auth=(client_id, client_secret),
        timeout=_request_timeout(),
    )
    if response.status_code >= 400:
        raise DiscordAuthError(f"Discord token exchange failed ({response.status_code})")
    return response.json()


def fetch_discord_profile(access_token: str) -> dict:
    api_base = current_app.config.get("DISCORD_API_BASE_URL", "https://discord.com/api/v10")
    response = requests.get(
        f"{api_base}/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=_request_timeout(),
    )
    if response.status_code >= 400:
        raise DiscordAuthError(f"Discord profile fetch failed ({response.status_code})")
    return response.json()


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def sign_bot_verification_payload(payload: dict, timestamp: str, nonce: str) -> str:
    secret = _required_config_value("DISCORD_BOT_SHARED_SECRET")
    message = f"{timestamp}.{nonce}.{_canonical_json(payload)}"
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_discord_with_bot(payload: dict) -> dict:
    verify_url = _required_config_value("DISCORD_BOT_VERIFICATION_URL")
    timestamp = str(int(time.time()))
    nonce = secrets.token_urlsafe(18)
    signature = sign_bot_verification_payload(payload, timestamp, nonce)
    response = requests.post(
        verify_url,
        data=_canonical_json(payload),
        headers={
            "Content-Type": "application/json",
            "X-Request-Timestamp": timestamp,
            "X-Request-Nonce": nonce,
            "X-Signature": signature,
        },
        timeout=_request_timeout(),
    )
    if response.status_code >= 400:
        raise DiscordAuthError(f"Discord bot verification failed ({response.status_code})")
    return response.json()


def sanitize_discord_username(raw_name: str, discord_user_id: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "_", (raw_name or "").strip()).strip("_").lower()
    if not base:
        base = f"discord_{discord_user_id[-6:]}"
    if base[0].isdigit():
        base = f"d_{base}"
    return base[:32]


def build_unique_username(base_username: str, existing_checker, suffix_seed: str) -> str:
    candidate = base_username[:50]
    if not candidate:
        candidate = f"discord_{suffix_seed[-6:]}"
    if not existing_checker(candidate):
        return candidate

    for index in range(2, 100):
        suffix = f"_{index}"
        trimmed = candidate[: 50 - len(suffix)]
        if not trimmed:
            trimmed = f"discord_{suffix_seed[-6:]}"
        maybe = f"{trimmed}{suffix}"
        if not existing_checker(maybe):
            return maybe

    fallback = f"discord_{suffix_seed[-10:]}"
    return fallback[:50]
