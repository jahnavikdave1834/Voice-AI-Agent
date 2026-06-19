"""Exotel Voicebot WebSocket transport.

The appointment agent already owns STT, dialogue, booking, and TTS. This module
only adapts Exotel's raw PCM WebSocket protocol to that agent interface.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import math
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from pydub import AudioSegment
from starlette.websockets import WebSocket, WebSocketDisconnect

from config.settings import Settings
from phone_calling.sessions import ConversationSessionStore

logger = logging.getLogger(__name__)

EXOTEL_SAMPLE_WIDTH_BYTES = 2
EXOTEL_CHANNELS = 1
EXOTEL_MIN_CHUNK_BYTES = 3200
EXOTEL_CHUNK_MULTIPLE_BYTES = 320
WHISPER_SAMPLE_RATE = 16000


@dataclass
class ExotelTurnBuffer:
    sample_rate: int
    silence_threshold_db: float
    silence_duration_ms: int
    max_recording_seconds: int
    chunks: list[bytes] = field(default_factory=list)
    started: bool = False
    last_speech_ms: int = 0
    buffered_ms: int = 0

    def add_chunk(self, chunk: bytes) -> bytes | None:
        """Add an Exotel raw PCM chunk and return a complete utterance if ready."""
        if not chunk:
            return None

        chunk_ms = _raw_duration_ms(chunk, self.sample_rate)
        chunk_dbfs = _raw_dbfs(chunk, self.sample_rate)
        has_speech = chunk_dbfs > self.silence_threshold_db

        if has_speech:
            self.started = True
            self.last_speech_ms = self.buffered_ms + chunk_ms

        if self.started:
            self.chunks.append(chunk)
            self.buffered_ms += chunk_ms

        if not self.started:
            return None

        silence_ms = max(0, self.buffered_ms - self.last_speech_ms)
        max_ms = self.max_recording_seconds * 1000

        if silence_ms >= self.silence_duration_ms or self.buffered_ms >= max_ms:
            return self.pop()

        return None

    def pop(self) -> bytes | None:
        if not self.chunks:
            self.reset()
            return None
        raw_audio = b"".join(self.chunks)
        self.reset()
        return raw_audio

    def reset(self) -> None:
        self.chunks.clear()
        self.started = False
        self.last_speech_ms = 0
        self.buffered_ms = 0


def _raw_duration_ms(raw_audio: bytes, sample_rate: int) -> int:
    bytes_per_second = sample_rate * EXOTEL_SAMPLE_WIDTH_BYTES * EXOTEL_CHANNELS
    return int(len(raw_audio) / bytes_per_second * 1000)


def _raw_dbfs(raw_audio: bytes, sample_rate: int) -> float:
    if not raw_audio:
        return -math.inf
    audio = AudioSegment(
        data=raw_audio,
        sample_width=EXOTEL_SAMPLE_WIDTH_BYTES,
        frame_rate=sample_rate,
        channels=EXOTEL_CHANNELS,
    )
    return audio.dBFS if audio.rms else -math.inf


def exotel_raw_to_wav_bytes(raw_audio: bytes, sample_rate: int) -> bytes:
    """Wrap Exotel raw/slin PCM as a 16 kHz mono WAV for Whisper."""
    audio = AudioSegment(
        data=raw_audio,
        sample_width=EXOTEL_SAMPLE_WIDTH_BYTES,
        frame_rate=sample_rate,
        channels=EXOTEL_CHANNELS,
    )
    audio = audio.set_frame_rate(WHISPER_SAMPLE_RATE).set_channels(1).set_sample_width(2)
    output = BytesIO()
    audio.export(output, format="wav")
    return output.getvalue()


def tts_audio_to_exotel_raw(audio_bytes: bytes, sample_rate: int) -> bytes:
    """Convert gTTS MP3 bytes to Exotel raw/slin PCM."""
    audio = AudioSegment.from_file(BytesIO(audio_bytes), format="mp3")
    audio = audio.set_frame_rate(sample_rate).set_channels(1).set_sample_width(2)
    return audio.raw_data


def _chunk_for_exotel(raw_audio: bytes) -> list[bytes]:
    """Split outbound raw PCM into Exotel-compliant chunks."""
    chunks = []
    offset = 0
    while offset < len(raw_audio):
        chunk = raw_audio[offset : offset + EXOTEL_MIN_CHUNK_BYTES]
        offset += EXOTEL_MIN_CHUNK_BYTES
        remainder = len(chunk) % EXOTEL_CHUNK_MULTIPLE_BYTES
        if remainder:
            chunk += b"\x00" * (EXOTEL_CHUNK_MULTIPLE_BYTES - remainder)
        if len(chunk) < EXOTEL_MIN_CHUNK_BYTES:
            chunk += b"\x00" * (EXOTEL_MIN_CHUNK_BYTES - len(chunk))
        chunks.append(chunk)
    return chunks


def _event_payload(raw_message: str | bytes) -> dict[str, Any] | None:
    if isinstance(raw_message, bytes):
        raw_message = raw_message.decode("utf-8", errors="ignore")
    try:
        payload = json.loads(raw_message)
    except json.JSONDecodeError:
        logger.warning("Ignoring non-JSON Exotel websocket message: %r", raw_message)
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _call_sid_from_start(start: dict[str, Any]) -> str:
    return (
        start.get("call_sid")
        or start.get("callSid")
        or start.get("CallSid")
        or "exotel-local-call"
    )


def _handoff_from_start(start: dict[str, Any]) -> str | None:
    params = start.get("custom_parameters") or start.get("customParameters") or {}
    if not isinstance(params, dict):
        return None
    return params.get("handoff_code") or params.get("handoffCode")


async def _send_json(websocket: WebSocket, send_lock: asyncio.Lock, payload: dict[str, Any]) -> None:
    async with send_lock:
        await websocket.send_text(json.dumps(payload))


async def _send_exotel_audio(
    websocket: WebSocket,
    send_lock: asyncio.Lock,
    *,
    stream_sid: str,
    raw_audio: bytes,
    mark_name: str,
) -> None:
    for chunk in _chunk_for_exotel(raw_audio):
        await _send_json(
            websocket,
            send_lock,
            {
                "event": "media",
                "stream_sid": stream_sid,
                "media": {
                    "payload": base64.b64encode(chunk).decode("ascii"),
                },
            },
        )

    await _send_json(
        websocket,
        send_lock,
        {
            "event": "mark",
            "stream_sid": stream_sid,
            "mark": {"name": mark_name},
        },
    )


async def _speak_text(
    websocket: WebSocket,
    send_lock: asyncio.Lock,
    *,
    session,
    stream_sid: str,
    text: str,
    sample_rate: int,
    mark_name: str,
) -> None:
    cleaned = " ".join(text.split())
    if not cleaned:
        return

    tts_bytes = await asyncio.to_thread(session.agent.get_tts_audio, cleaned)
    if not tts_bytes:
        logger.warning("TTS produced no audio for stream %s", stream_sid)
        return

    exotel_raw = await asyncio.to_thread(tts_audio_to_exotel_raw, tts_bytes, sample_rate)
    await _send_exotel_audio(
        websocket,
        send_lock,
        stream_sid=stream_sid,
        raw_audio=exotel_raw,
        mark_name=mark_name,
    )


async def _process_utterance(
    websocket: WebSocket,
    send_lock: asyncio.Lock,
    *,
    session,
    stream_sid: str,
    raw_audio: bytes,
    sample_rate: int,
) -> bool:
    wav_bytes = await asyncio.to_thread(exotel_raw_to_wav_bytes, raw_audio, sample_rate)
    try:
        user_text, response_text = await asyncio.to_thread(
            session.agent.process_audio_input,
            wav_bytes,
        )
    except Exception:
        logger.exception("Failed to process Exotel audio for call %s", session.call_sid)
        user_text = ""
        response_text = "I'm sorry, I had trouble understanding that. Please say it again."

    if user_text:
        logger.info("Exotel call %s user said: %s", session.call_sid, user_text)

    await _speak_text(
        websocket,
        send_lock,
        session=session,
        stream_sid=stream_sid,
        text=response_text,
        sample_rate=sample_rate,
        mark_name="assistant-response",
    )

    return bool(session.agent.dialogue_manager.booking_state.confirmed)


async def handle_exotel_stream(
    websocket: WebSocket,
    session_store: ConversationSessionStore,
    settings: Settings,
) -> None:
    """Handle one Exotel bidirectional Voicebot WebSocket connection."""
    await websocket.accept()
    logger.info("Exotel Voicebot WebSocket connected")

    send_lock = asyncio.Lock()
    stream_sid = ""
    session = None
    busy = False
    sample_rate = int(getattr(settings, "EXOTEL_WS_SAMPLE_RATE", 8000))
    turn_buffer = ExotelTurnBuffer(
        sample_rate=sample_rate,
        silence_threshold_db=float(getattr(settings, "SILENCE_THRESHOLD_DB", -40.0)),
        silence_duration_ms=int(getattr(settings, "SILENCE_DURATION_MS", 1500)),
        max_recording_seconds=int(getattr(settings, "MAX_RECORDING_SECONDS", 30)),
    )

    try:
        while True:
            raw_message = await websocket.receive_text()
            message = _event_payload(raw_message)
            if not message:
                continue

            event = message.get("event")

            if event == "connected":
                logger.info("Exotel connected event received")
                continue

            if event == "start":
                start = message.get("start") or {}
                stream_sid = message.get("stream_sid") or start.get("stream_sid") or ""
                media_format = start.get("media_format") or {}
                if media_format.get("sample_rate"):
                    sample_rate = int(media_format["sample_rate"])
                    turn_buffer.sample_rate = sample_rate

                call_sid = _call_sid_from_start(start)
                session, _created = session_store.get_or_create_call(
                    call_sid,
                    handoff_code=_handoff_from_start(start),
                    enable_audio=True,
                )
                logger.info("Exotel stream started: call_sid=%s stream_sid=%s", call_sid, stream_sid)

                if not session.agent.transcript:
                    busy = True
                    greeting = session.agent.get_greeting()
                    await _speak_text(
                        websocket,
                        send_lock,
                        session=session,
                        stream_sid=stream_sid,
                        text=greeting,
                        sample_rate=sample_rate,
                        mark_name="assistant-greeting",
                    )
                    busy = False
                continue

            if event == "media":
                if not session or not stream_sid or busy:
                    continue

                payload = (message.get("media") or {}).get("payload", "")
                if not payload:
                    continue

                try:
                    chunk = base64.b64decode(payload)
                except ValueError:
                    logger.warning("Invalid base64 media payload on stream %s", stream_sid)
                    continue

                utterance = turn_buffer.add_chunk(chunk)
                if not utterance:
                    continue

                busy = True
                confirmed = await _process_utterance(
                    websocket,
                    send_lock,
                    session=session,
                    stream_sid=stream_sid,
                    raw_audio=utterance,
                    sample_rate=sample_rate,
                )
                busy = False

                if confirmed:
                    session_store.remove_call(session.call_sid)
                    await websocket.close(code=1000)
                    return

                continue

            if event == "dtmf":
                logger.info("Exotel DTMF event on stream %s: %s", stream_sid, message.get("dtmf"))
                continue

            if event == "mark":
                logger.info("Exotel mark event on stream %s: %s", stream_sid, message.get("mark"))
                continue

            if event == "stop":
                logger.info("Exotel stop event on stream %s: %s", stream_sid, message.get("stop"))
                final_audio = turn_buffer.pop()
                if session and stream_sid and final_audio:
                    await _process_utterance(
                        websocket,
                        send_lock,
                        session=session,
                        stream_sid=stream_sid,
                        raw_audio=final_audio,
                        sample_rate=sample_rate,
                    )
                if session and session.call_sid:
                    session_store.remove_call(session.call_sid)
                return

            logger.debug("Ignoring Exotel event %r on stream %s", event, stream_sid)

    except WebSocketDisconnect:
        logger.info("Exotel Voicebot WebSocket disconnected: stream_sid=%s", stream_sid)
    except Exception:
        logger.exception("Exotel Voicebot WebSocket failed: stream_sid=%s", stream_sid)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        if session and session.call_sid:
            session_store.remove_call(session.call_sid)
