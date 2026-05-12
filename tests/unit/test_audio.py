from unittest.mock import MagicMock, patch

import numpy as np

from rex.config import AudioConfig
from rex.daemon.audio import AudioRecorder


def test_stop_before_start_returns_empty() -> None:
    recorder = AudioRecorder(AudioConfig())
    result = recorder.stop()
    assert result.shape == (0,)
    assert result.dtype == np.float32


def test_start_sets_recording_flag() -> None:
    recorder = AudioRecorder(AudioConfig())
    mock_stream = MagicMock()

    with patch("rex.daemon.audio.sd.InputStream", return_value=mock_stream):
        recorder.start()

    assert recorder._recording is True
    mock_stream.start.assert_called_once()


def test_stop_clears_buffer_and_closes_stream() -> None:
    recorder = AudioRecorder(AudioConfig())
    mock_stream = MagicMock()

    with patch("rex.daemon.audio.sd.InputStream", return_value=mock_stream):
        recorder.start()

    recorder._buffer = [np.ones((100, 1), dtype=np.float32)]
    result = recorder.stop()

    assert recorder._recording is False
    assert recorder._buffer == []
    mock_stream.stop.assert_called_once()
    mock_stream.close.assert_called_once()
    assert result.shape == (100,)


def test_stop_returns_concatenated_flattened_audio() -> None:
    recorder = AudioRecorder(AudioConfig())
    recorder._buffer = [
        np.ones((100, 1), dtype=np.float32),
        np.ones((200, 1), dtype=np.float32),
    ]
    result = recorder.stop()
    assert result.shape == (300,)
    assert result.ndim == 1


def test_callback_appends_copy_to_buffer() -> None:
    recorder = AudioRecorder(AudioConfig())
    indata = np.ones((64, 1), dtype=np.float32)
    recorder._callback(indata, 64, None, MagicMock())
    assert len(recorder._buffer) == 1
    assert not np.shares_memory(recorder._buffer[0], indata)
