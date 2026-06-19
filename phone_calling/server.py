"""Twilio-compatible phone-call and WebSocket transport server."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from urllib.parse import urljoin

from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket

from config.settings import get_settings
from phone_calling.channels import Channel
from phone_calling.protocol import session_snapshot
from phone_calling.sessions import ConversationSessionStore
from phone_calling.twiml import gather_response, hangup_response
from phone_calling.exotel_stream import handle_exotel_stream
from phone_calling.websocket_handler import handle_websocket

logger = logging.getLogger(__name__)

settings = get_settings()
session_store = ConversationSessionStore(settings)
STATIC_DIR = Path(__file__).resolve().parent / "static"

_HANDOFF_CODE_PATTERN = re.compile(r"\b(\d{6})\b")


def _clean_for_phone(text: str) -> str:
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _absolute_action_url(request) -> str:
    public_base_url = getattr(settings, "PUBLIC_BASE_URL", "")
    if public_base_url:
        return urljoin(public_base_url.rstrip("/") + "/", "voice/input")
    return str(request.url_for("voice_input"))


def _extract_handoff_code(text: str) -> str | None:
    match = _HANDOFF_CODE_PATTERN.search(text)
    return match.group(1) if match else None


async def health(_request):
    return PlainTextResponse("ok")


async def web_client(_request):
    index_path = STATIC_DIR / "index.html"
    return FileResponse(index_path)


async def create_session(request):
    payload = {}
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            payload = {}

    channel_name = payload.get("channel", Channel.WEB.value)
    channel = Channel.PHONE if channel_name == Channel.PHONE.value else Channel.WEB
    session = session_store.create(channel=channel)

    if not session.agent.transcript:
        session.agent.get_greeting()

    return JSONResponse(
        session_snapshot(
            session.session_id,
            session.agent,
            channel=session.channel,
            handoff_code=session.handoff_code,
        )
        | {
            "phone_number": settings.TWILIO_PHONE_NUMBER,
            "public_base_url": settings.PUBLIC_BASE_URL,
        }
    )


async def get_session(request):
    session_id = request.path_params["session_id"]
    session = session_store.get(session_id)
    if not session:
        return JSONResponse({"error": "Session not found."}, status_code=404)

    return JSONResponse(
        session_snapshot(
            session.session_id,
            session.agent,
            channel=session.channel,
            handoff_code=session.handoff_code,
        )
        | {"phone_number": settings.TWILIO_PHONE_NUMBER}
    )


async def switch_session_channel(request):
    session_id = request.path_params["session_id"]
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}

    channel_name = payload.get("channel", Channel.PHONE.value)
    if channel_name not in {Channel.WEB.value, Channel.PHONE.value}:
        return JSONResponse({"error": "Invalid channel."}, status_code=400)

    session = session_store.switch_channel(session_id, Channel(channel_name))
    if not session:
        return JSONResponse({"error": "Session not found."}, status_code=404)

    return JSONResponse(
        {
            "session_id": session.session_id,
            "channel": session.channel.value,
            "handoff_code": session.handoff_code,
            "phone_number": settings.TWILIO_PHONE_NUMBER,
            "message": (
                "Call the phone number and say your six-digit code when prompted."
                if session.channel == Channel.PHONE
                else "Reconnect in the browser to continue on web."
            ),
        }
    )


async def phone_config(_request):
    return JSONResponse(
        {
            "phone_number": settings.TWILIO_PHONE_NUMBER,
            "voice_webhook": f"{settings.PUBLIC_BASE_URL.rstrip('/')}/voice"
            if settings.PUBLIC_BASE_URL
            else "/voice",
            "message": "Call this number to book your appointment with Aria.",
        }
    )


async def websocket_endpoint(websocket: WebSocket):
    session_id = websocket.path_params["session_id"]
    await handle_websocket(
        websocket,
        session_id,
        session_store,
        phone_number=settings.TWILIO_PHONE_NUMBER,
    )


async def exotel_stream_endpoint(websocket: WebSocket):
    await handle_exotel_stream(websocket, session_store, settings)


async def voice(request):
    prompt = (
        "Hello, I'm Aria, your appointment booking assistant. "
        "Tell me what appointment you'd like to book."
    )

    return PlainTextResponse(
        gather_response(
            _clean_for_phone(prompt),
            _absolute_action_url(request),
            voice=settings.TWILIO_VOICE,
            language=settings.TWILIO_LANGUAGE,
        ),
        media_type="application/xml",
    )


async def voice_input(request):
    form = await request.form()
    call_sid = form.get("CallSid") or "local-call"
    speech_result = (form.get("SpeechResult") or "").strip()
    handoff_code = _extract_handoff_code(speech_result)

    session = session_store.get_by_call_sid(call_sid)
    response_text = ""

    if handoff_code:
        linked = session_store.link_call_to_handoff(call_sid, handoff_code)
        if linked:
            session = linked
            response_text = (
                "Thanks, I've connected your booking. "
                "Let's continue where you left off."
            )
        elif not session:
            session, _created = session_store.get_or_create_call(call_sid)
            response_text = (
                "I couldn't find that code. "
                "Please try again or tell me what appointment you'd like to book."
            )
        else:
            logger.info("Call %s user said: %s", call_sid, speech_result)
            response_text = session.agent.process_text_input(speech_result)
    elif not speech_result:
        if not session:
            session, _created = session_store.get_or_create_call(call_sid)
        response_text = "I could not hear that clearly. Please say it again."
    else:
        if not session:
            session, _created = session_store.get_or_create_call(call_sid)
        logger.info("Call %s user said: %s", call_sid, speech_result)
        response_text = session.agent.process_text_input(speech_result)

    cleaned_response = _clean_for_phone(response_text)
    state = session.agent.dialogue_manager.booking_state

    if state.confirmed:
        session_store.remove_call(call_sid)
        return PlainTextResponse(
            hangup_response(
                cleaned_response + " Thank you for calling. Goodbye.",
                voice=settings.TWILIO_VOICE,
            ),
            media_type="application/xml",
        )

    return PlainTextResponse(
        gather_response(
            cleaned_response,
            _absolute_action_url(request),
            voice=settings.TWILIO_VOICE,
            language=settings.TWILIO_LANGUAGE,
        ),
        media_type="application/xml",
    )


async def call_status(request):
    form = await request.form()
    call_sid = form.get("CallSid")
    call_status_value = form.get("CallStatus")

    if call_sid and call_status_value in {"completed", "busy", "failed", "no-answer", "canceled"}:
        session_store.remove_call(call_sid)

    return PlainTextResponse("ok")


app = Starlette(
    debug=settings.DEBUG,
    routes=[
        Route("/", web_client, methods=["GET"], name="web_client"),
        Route("/health", health, methods=["GET"]),
        Route("/api/phone-config", phone_config, methods=["GET"]),
        Route("/api/sessions", create_session, methods=["POST"]),
        Route("/api/sessions/{session_id}", get_session, methods=["GET"]),
        Route("/api/sessions/{session_id}/switch", switch_session_channel, methods=["POST"]),
        WebSocketRoute("/ws/{session_id}", websocket_endpoint, name="websocket"),
        WebSocketRoute("/exotel/stream", exotel_stream_endpoint, name="exotel_stream"),
        Route("/voice", voice, methods=["GET", "POST"], name="voice"),
        Route("/voice/input", voice_input, methods=["POST"], name="voice_input"),
        Route("/voice/status", call_status, methods=["POST"], name="call_status"),
    ],
)
