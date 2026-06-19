import json
import logging
import re
import os
import requests
import xml.etree.ElementTree as ET
from typing import Optional
from fastapi import FastAPI, Request, Form, Response, WebSocket
from fastapi.responses import PlainTextResponse
from config.settings import get_settings
from phone_calling.exotel_stream import handle_exotel_stream
from phone_calling.sessions import ConversationSessionStore

logger = logging.getLogger(__name__)

app = FastAPI(title="Aria Voice AI - Exotel Dynamic XML")

settings = get_settings()
session_store = ConversationSessionStore(settings)


def clean_for_phone(text: str) -> str:
    """Removes non-ASCII characters and collapses whitespace."""
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_action_url(request: Request, path: str = "/voice/input") -> str:
    """Constructs the absolute URL for the next webhook, preferring PUBLIC_BASE_URL."""
    if settings.PUBLIC_BASE_URL:
        return f"{settings.PUBLIC_BASE_URL.rstrip('/')}{path}"
    return str(request.url_for("voice_input"))


def exotel_say_and_record(text: str, action_url: str) -> Response:
    """
    Returns Exotel-compatible XML that:
      1. Reads `text` aloud to the caller.
      2. Records the caller's response and posts it to `action_url`.
    This drives the full conversational loop from the backend.
    """
    escaped = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Say>{escaped}</Say>"
        f'<Record action="{action_url}" method="POST" '
        'maxLength="30" playBeep="false" '
        'timeout="3" transcribe="false"/>'
        "</Response>"
    )
    return Response(content=xml, media_type="application/xml")


def exotel_say_and_hangup(text: str) -> Response:
    """Returns Exotel XML that reads the final message and hangs up."""
    escaped = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Say>{escaped}</Say>"
        "<Hangup/>"
        "</Response>"
    )
    return Response(content=xml, media_type="application/xml")


def fetch_exotel_recording(recording_url: str) -> Optional[bytes]:
    """Downloads the recording from Exotel using Basic Auth (API Key + Token)."""
    if not recording_url:
        return None
    try:
        auth = None
        if settings.EXOTEL_API_KEY and settings.EXOTEL_AUTH_TOKEN:
            auth = (settings.EXOTEL_API_KEY, settings.EXOTEL_AUTH_TOKEN)

        logger.info(f"Downloading Exotel recording from: {recording_url}")
        resp = requests.get(recording_url, auth=auth, timeout=15)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.error(f"Failed to fetch Exotel recording: {e}")
        return None


# ──────────────────────────────────────────────
# /voice  – Exotel calls this when a call arrives
# ──────────────────────────────────────────────
@app.get("/voice")
@app.post("/voice")
async def voice(request: Request):
    """
    Initial Exotel Passthru endpoint.
    Returns XML that speaks the greeting and starts recording the caller.
    """
    logger.info("=" * 50)
    logger.info("INITIAL EXOTEL CALL CONNECTED")

    prompt = (
        "Hello, I'm Aria, your appointment booking assistant. "
        "Tell me what appointment you'd like to book."
    )
    action_url = build_action_url(request, "/voice/input")
    return exotel_say_and_record(clean_for_phone(prompt), action_url)


# ──────────────────────────────────────────────
# /voice/input  – Exotel posts the RecordingUrl here
# ──────────────────────────────────────────────
@app.post("/voice/input")
async def voice_input(
    request: Request,
    CallSid: str = Form(default="local-call"),
    From: str = Form(default=""),
    RecordingUrl: str = Form(default=""),
):
    """
    Exotel posts the RecordingUrl of the caller's speech here.
    We download + transcribe it, run through Gemini, and return
    the next XML turn (Say + Record, or Say + Hangup).
    """
    logger.info("=" * 50)
    logger.info("EXOTEL RECORDING RECEIVED")
    logger.info(f"CallSid : {CallSid}")
    logger.info(f"From    : {From}")
    logger.info(f"RecordingUrl: {RecordingUrl}")

    form = await request.form()
    logger.info(f"Full payload: {dict(form)}")

    # ── Session ──────────────────────────────
    session = session_store.get_by_call_sid(CallSid)
    if not session:
        session, _ = session_store.get_or_create_call(CallSid)

    response_text = ""

    # ── Transcribe ───────────────────────────
    if RecordingUrl:
        audio_bytes = fetch_exotel_recording(RecordingUrl)
        if audio_bytes:
            try:
                transcribed_text, next_prompt = session.agent.process_audio_input(audio_bytes)
                logger.info(f"Whisper transcription: {transcribed_text}")
                response_text = next_prompt
            except Exception as e:
                logger.error(f"Audio processing error: {e}")
                response_text = "I'm sorry, I had trouble understanding that. Could you please repeat?"
        else:
            response_text = "I could not retrieve your audio. Please try again."
    else:
        response_text = "I did not receive any audio. Please speak clearly after the tone."

    cleaned = clean_for_phone(response_text)
    state = session.agent.dialogue_manager.booking_state
    action_url = build_action_url(request, "/voice/input")

    # ── Booking complete → hangup ─────────────
    if state.confirmed:
        final_record = {
            "name": state.name or "",
            "phone_number": state.contact or "",
            "email": state.email or "",
            "appointment_date": state.date or "",
            "appointment_time": state.time or "",
            "appointment_purpose": state.service_type or "",
            "notes": "",
        }
        logger.info("========================================")
        logger.info("FINAL STRUCTURED APPOINTMENT RECORD:")
        logger.info(json.dumps(final_record, indent=4))
        logger.info("========================================")

        session_store.remove_call(CallSid)
        return exotel_say_and_hangup(cleaned + " Thank you for calling. Goodbye.")

    # ── Continue conversation ─────────────────
    return exotel_say_and_record(cleaned, action_url)


# ──────────────────────────────────────────────
# /voice/status  – optional call status callback
# ──────────────────────────────────────────────
@app.post("/voice/status")
async def call_status(
    CallSid: str = Form(None),
    Status: str = Form(None),
):
    """Cleans up the session when Exotel reports a terminal call status."""
    if CallSid and Status in {"completed", "busy", "failed", "no-answer", "canceled", "terminal"}:
        session_store.remove_call(CallSid)
    return PlainTextResponse("ok")

@app.websocket("/exotel/stream")
async def exotel_stream(websocket: WebSocket):
    await handle_exotel_stream(websocket, session_store, settings)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8000, reload=True)
