"""Unit tests for the ElevenLabs TTS service."""
from __future__ import annotations

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.lib.elevenlabs_service import (
    ElevenLabsError,
    prepare_tts_text,
    stream_phase_audio,
)

_PHASE_TEXT = "Close your eyes and take a slow breath in."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_settings(
    *,
    api_key: str | None = "test-key",
    voice_id: str | None = "test-voice",
) -> MagicMock:
    m = MagicMock()
    m.elevenlabs_api_key = api_key
    m.elevenlabs_voice_id = voice_id
    return m


def _make_httpx_stream_mock(
    status: int = 200,
    chunks: list[bytes] | None = None,
) -> MagicMock:
    """Build nested async context manager mocks for httpx.AsyncClient.stream()."""
    if chunks is None:
        chunks = [b"mp3bytes"]

    async def _aiter() -> AsyncIterator[bytes]:
        for chunk in chunks:
            yield chunk

    mock_response = MagicMock()
    mock_response.status_code = status
    mock_response.aiter_bytes = MagicMock(return_value=_aiter())
    mock_response.aread = AsyncMock(return_value=b"error body")

    stream_ctx = AsyncMock()
    stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    stream_ctx.__aexit__ = AsyncMock(return_value=False)

    client = MagicMock()
    client.stream = MagicMock(return_value=stream_ctx)

    client_ctx = AsyncMock()
    client_ctx.__aenter__ = AsyncMock(return_value=client)
    client_ctx.__aexit__ = AsyncMock(return_value=False)

    return client_ctx


async def _collect(gen) -> list[bytes]:
    """Drain an async generator into a list."""
    return [chunk async for chunk in gen]


# ---------------------------------------------------------------------------
# prepare_tts_text
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_prepare_tts_text_collapses_internal_whitespace() -> None:
    assert prepare_tts_text("hello   world") == "hello world"


@pytest.mark.unit
def test_prepare_tts_text_strips_outer_whitespace() -> None:
    assert prepare_tts_text("  hello world  ") == "hello world"


@pytest.mark.unit
def test_prepare_tts_text_returns_empty_string_for_whitespace_only() -> None:
    assert prepare_tts_text("   ") == ""


# ---------------------------------------------------------------------------
# stream_phase_audio — validation (fires before any HTTP call)
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_stream_phase_audio_raises_on_empty_text() -> None:
    with pytest.raises(ElevenLabsError, match="empty"):
        await _collect(stream_phase_audio(""))


@pytest.mark.unit
async def test_stream_phase_audio_raises_when_api_key_is_none() -> None:
    with patch(
        "src.lib.elevenlabs_service.get_settings",
        return_value=_mock_settings(api_key=None),
    ):
        with pytest.raises(ElevenLabsError, match="not configured"):
            await _collect(stream_phase_audio(_PHASE_TEXT))


@pytest.mark.unit
async def test_stream_phase_audio_raises_when_voice_id_is_none() -> None:
    with patch(
        "src.lib.elevenlabs_service.get_settings",
        return_value=_mock_settings(voice_id=None),
    ):
        with pytest.raises(ElevenLabsError, match="not configured"):
            await _collect(stream_phase_audio(_PHASE_TEXT))


# ---------------------------------------------------------------------------
# stream_phase_audio — HTTP behaviour
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_stream_phase_audio_raises_on_non_200_response() -> None:
    with (
        patch(
            "src.lib.elevenlabs_service.httpx.AsyncClient",
            return_value=_make_httpx_stream_mock(status=401),
        ),
        patch(
            "src.lib.elevenlabs_service.get_settings",
            return_value=_mock_settings(),
        ),
    ):
        with pytest.raises(ElevenLabsError, match="401"):
            await _collect(stream_phase_audio(_PHASE_TEXT))


@pytest.mark.unit
async def test_stream_phase_audio_raises_elevenlabs_error_on_timeout() -> None:
    stream_ctx = AsyncMock()
    stream_ctx.__aenter__ = AsyncMock(
        side_effect=httpx.TimeoutException("connect timed out")
    )
    stream_ctx.__aexit__ = AsyncMock(return_value=False)

    client = MagicMock()
    client.stream = MagicMock(return_value=stream_ctx)

    client_ctx = AsyncMock()
    client_ctx.__aenter__ = AsyncMock(return_value=client)
    client_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "src.lib.elevenlabs_service.httpx.AsyncClient",
            return_value=client_ctx,
        ),
        patch(
            "src.lib.elevenlabs_service.get_settings",
            return_value=_mock_settings(),
        ),
    ):
        with pytest.raises(ElevenLabsError, match="timed out"):
            await _collect(stream_phase_audio(_PHASE_TEXT))


@pytest.mark.unit
async def test_stream_phase_audio_yields_bytes_on_success() -> None:
    chunks = [b"hello", b"world"]
    with (
        patch(
            "src.lib.elevenlabs_service.httpx.AsyncClient",
            return_value=_make_httpx_stream_mock(chunks=chunks),
        ),
        patch(
            "src.lib.elevenlabs_service.get_settings",
            return_value=_mock_settings(),
        ),
    ):
        result = await _collect(stream_phase_audio(_PHASE_TEXT))

    assert result == chunks
