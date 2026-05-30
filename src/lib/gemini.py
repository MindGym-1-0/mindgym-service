from __future__ import annotations

import json
from typing import Any

import httpx

from src.lib.config import settings

_GEMINI_FLASH_MODEL = "gemini-2.5-flash"
_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiServiceError(Exception):
    """Base controlled error for Gemini integration failures."""


class GeminiMissingApiKeyError(GeminiServiceError):
    """Raised when GEMINI_API_KEY is not configured."""


class GeminiTimeoutError(GeminiServiceError):
    """Raised when Gemini does not respond within timeout."""


class GeminiNetworkError(GeminiServiceError):
    """Raised for transport-level connectivity failures."""


class GeminiApiError(GeminiServiceError):
    """Raised when Gemini returns a non-2xx response."""


class GeminiEmptyResponseError(GeminiServiceError):
    """Raised when Gemini response does not contain text content."""


class GeminiInvalidJsonError(GeminiServiceError):
    """Raised when Gemini output cannot be parsed as JSON."""


def _extract_text_from_gemini_response(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return ""

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content")
        if not isinstance(content, dict):
            continue
        parts = content.get("parts")
        if not isinstance(parts, list):
            continue

        chunks: list[str] = []
        for part in parts:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)

        if chunks:
            return "\n".join(chunks).strip()

    return ""


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def _parse_json_output(text: str) -> Any:
    cleaned = _strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiInvalidJsonError("Gemini returned invalid JSON.") from exc


async def generate_gemini_flash_json(
    prompt: str,
    *,
    timeout_seconds: float = 4.0,
    api_key: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> Any:
    """Call Gemini Flash and return parsed JSON output.

    The helper is intentionally route-agnostic and supports dependency injection
    of both API key and HTTP client for straightforward unit testing.
    """
    resolved_api_key = (api_key if api_key is not None else settings.gemini_api_key) or ""
    resolved_api_key = resolved_api_key.strip()
    if not resolved_api_key:
        raise GeminiMissingApiKeyError("GEMINI_API_KEY is not configured.")

    instruction = (
        "Return only valid JSON. Do not add markdown, backticks, comments, or any text outside the JSON."
    )
    full_prompt = f"{instruction}\n\n{prompt}"

    endpoint = f"{_GEMINI_API_BASE}/{_GEMINI_FLASH_MODEL}:generateContent"
    request_payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json"}
    params = {"key": resolved_api_key}

    owns_client = client is None
    http_client = client or httpx.AsyncClient(timeout=timeout_seconds)

    try:
        response = await http_client.post(
            endpoint,
            params=params,
            headers=headers,
            json=request_payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise GeminiTimeoutError(f"Gemini request timed out after {timeout_seconds} seconds.") from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        raise GeminiApiError(f"Gemini API error (status={status_code}).") from exc
    except httpx.RequestError as exc:
        raise GeminiNetworkError("Gemini network request failed.") from exc
    finally:
        if owns_client:
            await http_client.aclose()

    try:
        response_payload = response.json()
    except ValueError as exc:
        raise GeminiInvalidJsonError("Gemini API response was not valid JSON.") from exc

    text_output = _extract_text_from_gemini_response(response_payload)
    if not text_output:
        raise GeminiEmptyResponseError("Gemini response was empty.")

    return _parse_json_output(text_output)
