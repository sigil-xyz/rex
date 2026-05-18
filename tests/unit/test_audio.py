from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from rex.config import AudioConfig, VadConfig
from rex.daemon.audio import SpeechSession


def _make_session(
    onset_frames: int = 3,
    silence_frames: int = 3,
    onset_timeout: float = 0.5,
    max_recording: float = 1.0,
    onset_rms_threshold: float = 0.01,
) -> SpeechSession:
    vad = VadConfig(
        onset_frames=onset_frames,
        silence_frames=silence_frames,
        onset_timeout=onset_timeout,
        max_recording=max_recording,
        onset_rms_threshold=onset_rms_threshold,
    )
    return SpeechSession(AudioConfig(), vad)


# --- _tail_rms ---


def test_tail_rms_empty_buffer_returns_zero() -> None:
    session = _make_session()
    assert session._tail_rms() == 0.0


def test_tail_rms_known_value() -> None:
    session = _make_session()
    session._last_frame = np.ones((320, 1), dtype=np.float32)
    assert abs(session._tail_rms() - 1.0) < 1e-6


def test_tail_rms_known_value_half() -> None:
    session = _make_session()
    val = 0.5
    session._last_frame = np.full((320, 1), val, dtype=np.float32)
    assert abs(session._tail_rms() - val) < 1e-6


# --- _collect ---


def test_collect_empty_buffer() -> None:
    session = _make_session()
    audio = session._collect()
    assert isinstance(audio, np.ndarray)
    assert len(audio) == 0


def test_collect_concatenates_frames() -> None:
    session = _make_session()
    session._buffer = [
        np.ones((320, 1), dtype=np.float32),
        np.ones((320, 1), dtype=np.float32),
    ]
    audio = session._collect()
    assert len(audio) == 640


# --- _callback ---


def test_callback_appends_copy_and_updates_last_frame() -> None:
    session = _make_session()
    indata = np.ones((64, 1), dtype=np.float32)
    session._callback(indata, 64, None, MagicMock())
    assert len(session._buffer) == 1
    assert not np.shares_memory(session._buffer[0], indata)
    assert not np.shares_memory(session._last_frame, indata)
    assert np.array_equal(session._last_frame, indata)


# --- run(): onset timeout ---


@pytest.mark.asyncio
async def test_run_onset_timeout_returns_none() -> None:
    # onset_timeout=0.04 / _FRAME_DURATION=0.02 → 2 ticks — never reaches onset_frames=5
    session = _make_session(onset_frames=5, onset_timeout=0.04)
    with (
        patch("rex.daemon.audio.sd.InputStream", return_value=MagicMock()),
        patch.object(session, "_tail_rms", return_value=0.0),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await session.run()
    assert result is None


# --- run(): stop before onset ---


@pytest.mark.asyncio
async def test_run_stop_before_onset_returns_none() -> None:
    session = _make_session(onset_timeout=1.0)
    call_count = 0

    async def _stop_on_first(*_: object) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            session.request_stop()

    with (
        patch("rex.daemon.audio.sd.InputStream", return_value=MagicMock()),
        patch.object(session, "_tail_rms", return_value=0.0),
        patch("asyncio.sleep", side_effect=_stop_on_first),
    ):
        result = await session.run()
    assert result is None


# --- run(): onset detected, end-of-speech stops recording ---


@pytest.mark.asyncio
async def test_run_returns_audio_after_end_of_speech() -> None:
    # onset_frames=2 → two loud frames confirm onset
    # silence_frames=2 → two quiet frames after speech end recording
    session = _make_session(onset_frames=2, silence_frames=2, onset_timeout=0.5, max_recording=1.0)
    rms_values = iter([0.05, 0.05, 0.05, 0.05, 0.0, 0.0] + [0.0] * 100)
    session._buffer = [np.ones((320, 1), dtype=np.float32)]  # pre-seed for _collect()

    with (
        patch("rex.daemon.audio.sd.InputStream", return_value=MagicMock()),
        patch.object(session, "_tail_rms", side_effect=rms_values),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await session.run()

    assert result is not None
    assert len(result) > 0


# --- run(): manual stop during recording returns partial audio ---


@pytest.mark.asyncio
async def test_run_manual_stop_during_recording_returns_audio() -> None:
    # onset_frames=1 → single loud frame confirms onset immediately
    session = _make_session(onset_frames=1, silence_frames=50, onset_timeout=0.5, max_recording=5.0)
    sleep_calls = 0

    async def _stop_after_recording_starts(*_: object) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 3:
            session.request_stop()

    session._buffer = [np.ones((320, 1), dtype=np.float32)]
    rms_values = iter([0.05] * 100)  # always loud

    with (
        patch("rex.daemon.audio.sd.InputStream", return_value=MagicMock()),
        patch.object(session, "_tail_rms", side_effect=rms_values),
        patch("asyncio.sleep", side_effect=_stop_after_recording_starts),
    ):
        result = await session.run()

    assert result is not None
    assert len(result) > 0


# --- run(): stream always closed in finally ---


@pytest.mark.asyncio
async def test_run_stream_closed_on_onset_timeout() -> None:
    session = _make_session(onset_frames=5, onset_timeout=0.04)
    mock_stream = MagicMock()
    with (
        patch("rex.daemon.audio.sd.InputStream", return_value=mock_stream),
        patch.object(session, "_tail_rms", return_value=0.0),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        await session.run()
    mock_stream.stop.assert_called_once()
    mock_stream.close.assert_called_once()
