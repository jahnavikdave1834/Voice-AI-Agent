"""Shared JSON payloads for WebSocket and REST clients."""

from __future__ import annotations

from dialogue_management.booking_state import FIELD_LABELS, REQUIRED_FIELDS
from dialogue_management.agent import VoiceAgent
from phone_calling.channels import Channel


def booking_snapshot(agent: VoiceAgent) -> dict:
    state = agent.dialogue_manager.booking_state
    fields = {
        field: getattr(state, field, None)
        for field in REQUIRED_FIELDS
    }
    filled = sum(1 for value in fields.values() if value)
    return {
        "fields": fields,
        "labels": FIELD_LABELS,
        "filled": filled,
        "total": len(REQUIRED_FIELDS),
        "confirmed": state.confirmed,
    }


def session_snapshot(
    session_id: str,
    agent: VoiceAgent,
    *,
    channel: Channel,
    handoff_code: str | None = None,
) -> dict:
    payload = {
        "session_id": session_id,
        "channel": channel.value,
        "transcript": list(agent.transcript),
        "booking": booking_snapshot(agent),
    }
    if handoff_code:
        payload["handoff_code"] = handoff_code
    return payload
