import math
import wave
from io import BytesIO

from phone_calling.exotel_stream import (
    EXOTEL_MIN_CHUNK_BYTES,
    EXOTEL_CHUNK_MULTIPLE_BYTES,
    ExotelTurnBuffer,
    _chunk_for_exotel,
    exotel_raw_to_wav_bytes,
)


def _pcm_tone(sample_rate=8000, duration_ms=300, amplitude=12000):
    frames = int(sample_rate * duration_ms / 1000)
    data = bytearray()
    for index in range(frames):
        sample = int(amplitude * math.sin(2 * math.pi * 440 * index / sample_rate))
        data.extend(sample.to_bytes(2, byteorder="little", signed=True))
    return bytes(data)


def test_exotel_raw_to_wav_bytes_outputs_whisper_ready_wav():
    wav_bytes = exotel_raw_to_wav_bytes(_pcm_tone(), sample_rate=8000)

    with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 16000


def test_turn_buffer_flushes_after_silence():
    buffer = ExotelTurnBuffer(
        sample_rate=8000,
        silence_threshold_db=-40,
        silence_duration_ms=300,
        max_recording_seconds=30,
    )

    assert buffer.add_chunk(_pcm_tone(duration_ms=300)) is None
    completed = buffer.add_chunk(b"\x00" * 8000)

    assert completed is not None
    assert len(completed) > 0
    assert buffer.started is False


def test_exotel_outbound_chunks_meet_size_constraints():
    chunks = _chunk_for_exotel(b"\x01" * 3500)

    assert chunks
    assert all(len(chunk) >= EXOTEL_MIN_CHUNK_BYTES for chunk in chunks)
    assert all(len(chunk) % EXOTEL_CHUNK_MULTIPLE_BYTES == 0 for chunk in chunks)
