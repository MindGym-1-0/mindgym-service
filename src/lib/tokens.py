"""Extract Supabase access tokens from inbound requests."""

from __future__ import annotations

import json
import re
from collections import defaultdict

_COOKIE_ACCESS_RE = re.compile(
    r"^(?P<base>sb-[a-zA-Z0-9]+-(?:access-token))(?:\.(?P<chunk>\d+))?$",
)
_COOKIE_AUTH_JSON_RE = re.compile(
    r"^(?P<base>sb-[a-zA-Z0-9]+-(?:auth-token))(?:\.(?P<chunk>\d+))?$",
)


def _looks_like_jwt(value: str) -> bool:
    parts = value.split(".")
    return len(parts) == 3 and all(parts)


def _decode_supabase_cookie_value(raw: str) -> str | None:
    stripped = raw.strip()
    if _looks_like_jwt(stripped):
        return stripped
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        tok = data.get("access_token")
        if isinstance(tok, str):
            return tok
    return None


def assemble_chunked_sb_cookie(
    cookie_map: dict[str, str], pattern: re.Pattern[str]
) -> str | None:
    """Reassemble chunked `sb-<ref>-access-token{.N}` or `sb-<ref>-auth-token{.N}` values."""
    base_to_parts: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)
    single: dict[str, str] = {}

    for name, raw in cookie_map.items():
        m = pattern.match(name)
        if not m:
            continue
        base = str(m.group("base"))
        chunk = m.group("chunk")
        if chunk is None:
            single[base] = raw
        else:
            base_to_parts[base].append((int(chunk), raw))

    for base in sorted(set(single) | set(base_to_parts)):
        if base in single:
            decoded = _decode_supabase_cookie_value(single[base])
            if decoded:
                return decoded
        parts = sorted(base_to_parts.get(base, []), key=lambda t: t[0])
        if parts:
            merged = "".join(p[1] for p in parts)
            decoded = _decode_supabase_cookie_value(merged)
            if decoded:
                return decoded
    return None


def bearer_from_authorization(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def extract_access_token_from_request(
    auth_header: str | None, cookies: dict[str, str]
) -> str | None:
    bearer = bearer_from_authorization(auth_header)
    if bearer:
        return bearer

    jwt_access = assemble_chunked_sb_cookie(cookies, _COOKIE_ACCESS_RE)
    if jwt_access:
        return jwt_access

    jwt_from_auth_cookie = assemble_chunked_sb_cookie(cookies, _COOKIE_AUTH_JSON_RE)
    return jwt_from_auth_cookie or None
