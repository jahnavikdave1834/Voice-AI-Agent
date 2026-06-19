"""WebSocket transport for the browser booking client."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time

from starlette.websockets import WebSocket, WebSocketDisconnect

from phone_calling.channels import Channel
from phone_calling.protocol import booking_snapshot, session_snapshot
from phone_calling.sessions import ConversationSessionStore

logger = logging.getLogger(__name__)


def _assistant_payload(
    session,
    *,
    content: str,
    user_text: str | None = None,
    include_handoff: bool = False,
) -> dict:
    payload = {
        "type": "assistant",
        "content": content,
        "channel": session.channel.value,
        "transcript": list(session.agent.transcript),
        "booking": booking_snapshot(session.agent),
    }
    if user_text is not None:
        payload["user_text"] = user_text
    if include_handoff:
        payload["handoff_code"] = session.handoff_code
    return payload


async def _send_json(websocket: WebSocket, payload: dict) -> None:
    await websocket.send_text(json.dumps(payload))


async def _process_text(session, text: str) -> tuple[str, str | None]:
    cleaned = text.strip()
    if not cleaned:
        return "I could not hear that clearly. Please try again.", None

    response = await asyncio.to_thread(session.agent.process_text_input, cleaned)
    return response, cleaned


async def _process_audio(session, audio_bytes: bytes) -> tuple[str, str | None]:
    user_text, response = await asyncio.to_thread(
        session.agent.process_audio_input,
        audio_bytes,
    )
    return response, user_text or None


async def handle_websocket(
    websocket: WebSocket,
    session_id: str,
    session_store: ConversationSessionStore,
    *,
    phone_number: str = "",
) -> None:
    await websocket.accept()

    session = session_store.get(session_id)
    if not session:
        await _send_json(
            websocket,
            {"type": "error", "message": "Session not found."},
        )
        await websocket.close()
        return

    session.channel = Channel.WEB
    session.last_seen = time.time()

    greeting = session.agent.get_greeting() if not session.agent.transcript else (
        "Welcome back. Let's continue your booking."
    )
    if not session.agent.transcript:
        session.agent.transcript.append({"role": "assistant", "text": greeting})

    await _send_json(
        websocket,
        {
            "type": "connected",
            **session_snapshot(
                session_id,
                session.agent,
                channel=session.channel,
                handoff_code=session.handoff_code,
            ),
            "greeting": greeting,
            "phone_number": phone_number,
        },
    )

    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            message_type = message.get("type")

            if message_type == "ping":
                await _send_json(websocket, {"type": "pong"})
                continue

            if message_type == "switch_channel":
                target = message.get("channel", Channel.PHONE.value)
                if target != Channel.PHONE.value:
                    await _send_json(
                        websocket,
                        {"type": "error", "message": "Only phone switching is supported."},
                    )
                    continue

                updated = session_store.switch_channel(session_id, Channel.PHONE)
                if not updated:
                    await _send_json(
                        websocket,
                        {"type": "error", "message": "Unable to switch channel."},
                    )
                    continue

                await _send_json(
                    websocket,
                    {
                        "type": "channel_ready",
                        "channel": Channel.PHONE.value,
                        "handoff_code": updated.handoff_code,
                        "phone_number": phone_number,
                        "message": (
                            "Call the number below and say your six-digit code "
                            "when Aria answers to continue this booking on the phone."
                        ),
                    },
                )
                continue

            if message_type == "text":
                response, user_text = await _process_text(session, message.get("content", ""))
            elif message_type == "audio":
                audio_data = message.get("data", "")
                if not audio_data:
                    await _send_json(
                        websocket,
                        {"type": "error", "message": "Missing audio payload."},
                    )
                    continue
                audio_bytes = base64.b64decode(audio_data)
                response, user_text = await _process_audio(session, audio_bytes)
            else:
                await _send_json(
                    websocket,
                    {"type": "error", "message": f"Unknown message type: {message_type}"},
                )
                continue

            confirmed = session.agent.dialogue_manager.booking_state.confirmed
            payload = _assistant_payload(session, content=response, user_text=user_text)
            payload["type"] = "confirmed" if confirmed else "assistant"
            await _send_json(websocket, payload)

            if confirmed:
                session_store.remove(session_id)
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    except json.JSONDecodeError:
        await _send_json(websocket, {"type": "error", "message": "Invalid JSON message."})
    except Exception as exc:
        logger.exception("WebSocket error for session %s", session_id)
        await _send_json(websocket, {"type": "error", "message": str(exc)})
