"""ElevenLabs TTS service — synthesizes Maya's session phase scripts into audio."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import httpx

from src.lib.config import get_settings

logger = logging.getLogger(__name__)

MAYA_VOICE_SETTINGS: dict[str, object] = {
    "stability": 0.65,
    "similarity_boost": 0.75,
    "style": 0.1,
    "use_speaker_boost": True,
}

ELEVENLABS_MODEL = "eleven_multilingual_v2"
ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"
_ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"


class ElevenLabsError(RuntimeError):
    """Raised when ElevenLabs TTS fails, times out, or is not configured."""


def prepare_tts_text(text: str) -> str:
    """Collapse whitespace in phase text before sending to TTS."""
    return " ".join(text.strip().split())


async def stream_phase_audio(text: str) -> AsyncIterator[bytes]:
    """Stream raw MP3 bytes from ElevenLabs for the given phase text.

    Validates text and config before any HTTP call. Yields audio chunks as they
    arrive — does not buffer the full MP3 in server memory. Raises ElevenLabsError
    on any failure before or during streaming.
    """
    if not text:
        raise ElevenLabsError("Cannot synthesize empty phase text")

    settings = get_settings()
    if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
        raise ElevenLabsError("ElevenLabs is not configured")

    url = f"{_ELEVENLABS_BASE_URL}/text-to-speech/{settings.elevenlabs_voice_id}/stream"

    payload = {
        "text": text,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": MAYA_VOICE_SETTINGS,
    }

    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }

    params = {"output_format": ELEVENLABS_OUTPUT_FORMAT}

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            async with client.stream(
                "POST", url, headers=headers, json=payload, params=params
            ) as response:
                if response.status_code >= 400:
                    await response.aread()
                    logger.error(
                        "ElevenLabs TTS failed status=%d", response.status_code
                    )
                    raise ElevenLabsError(
                        f"ElevenLabs TTS failed with status {response.status_code}"
                    )

                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk
    except ElevenLabsError:
        raise
    except httpx.TimeoutException as exc:
        logger.error("ElevenLabs TTS timed out: %s", exc)
        raise ElevenLabsError("ElevenLabs TTS request timed out") from exc
    except httpx.HTTPError as exc:
        logger.error("ElevenLabs HTTP error: %s", exc)
        raise ElevenLabsError(f"ElevenLabs HTTP error: {exc}") from exc
