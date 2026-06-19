"""Shared conversation sessions for web and phone channels."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable

from config.settings import Settings
from dialogue_management.agent import VoiceAgent
from phone_calling.channels import Channel


def _generate_session_id() -> str:
    return f"sess_{int(time.time() * 1000):x}"


def _generate_handoff_code() -> str:
    return f"{random.randint(0, 999999):06d}"


@dataclass
class ConversationSession:
    session_id: str
    agent: VoiceAgent
    channel: Channel
    last_seen: float
    handoff_code: str = field(default_factory=_generate_handoff_code)
    call_sid: str | None = None


class ConversationSessionStore:
    def __init__(
        self,
        settings: Settings,
        *,
        ttl_seconds: int = 60 * 60,
        agent_factory: Callable[..., VoiceAgent] = VoiceAgent,
    ):
        self.settings = settings
        self.ttl_seconds = ttl_seconds
        self.agent_factory = agent_factory
        self._sessions: dict[str, ConversationSession] = {}
        self._call_index: dict[str, str] = {}

    def create(
        self,
        *,
        channel: Channel = Channel.WEB,
        enable_audio: bool | None = None,
    ) -> ConversationSession:
        self.cleanup()
        session_id = _generate_session_id()
        audio_enabled = channel == Channel.WEB if enable_audio is None else enable_audio
        session = ConversationSession(
            session_id=session_id,
            agent=self.agent_factory(self.settings, enable_audio=audio_enabled),
            channel=channel,
            last_seen=time.time(),
        )
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> ConversationSession | None:
        self.cleanup()
        session = self._sessions.get(session_id)
        if session:
            session.last_seen = time.time()
        return session

    def get_by_call_sid(self, call_sid: str) -> ConversationSession | None:
        self.cleanup()
        session_id = self._call_index.get(call_sid)
        if not session_id:
            return None
        return self.get(session_id)

    def get_by_handoff_code(self, handoff_code: str) -> ConversationSession | None:
        self.cleanup()
        normalized = handoff_code.strip()
        for session in self._sessions.values():
            if session.handoff_code == normalized:
                session.last_seen = time.time()
                return session
        return None

    def get_or_create_call(
        self,
        call_sid: str,
        *,
        handoff_code: str | None = None,
        enable_audio: bool | None = None,
    ) -> tuple[ConversationSession, bool]:
        self.cleanup()

        existing = self.get_by_call_sid(call_sid)
        if existing:
            return existing, False

        if handoff_code:
            linked = self.link_call_to_handoff(call_sid, handoff_code)
            if linked:
                return linked, False

        session = self.create(channel=Channel.PHONE, enable_audio=enable_audio)
        session.call_sid = call_sid
        self._call_index[call_sid] = session.session_id
        return session, True

    def link_call_to_handoff(
        self,
        call_sid: str,
        handoff_code: str,
    ) -> ConversationSession | None:
        session = self.get_by_handoff_code(handoff_code)
        if not session:
            return None

        existing_session_id = self._call_index.get(call_sid)
        if existing_session_id and existing_session_id != session.session_id:
            self._sessions.pop(existing_session_id, None)

        previous_call_sid = session.call_sid
        if previous_call_sid and previous_call_sid in self._call_index:
            self._call_index.pop(previous_call_sid, None)

        session.call_sid = call_sid
        session.channel = Channel.PHONE
        session.last_seen = time.time()
        self._call_index[call_sid] = session.session_id
        return session

    def switch_channel(self, session_id: str, channel: Channel) -> ConversationSession | None:
        session = self.get(session_id)
        if not session:
            return None

        session.channel = channel
        session.handoff_code = _generate_handoff_code()
        session.last_seen = time.time()
        return session

    def remove(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session and session.call_sid:
            self._call_index.pop(session.call_sid, None)

    def remove_call(self, call_sid: str) -> None:
        session_id = self._call_index.pop(call_sid, None)
        if session_id:
            self._sessions.pop(session_id, None)

    def cleanup(self) -> None:
        expires_before = time.time() - self.ttl_seconds
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if session.last_seen < expires_before
        ]
        for session_id in expired:
            self.remove(session_id)


# Backward-compatible alias used by existing imports/tests.
PhoneCallSessionStore = ConversationSessionStore
