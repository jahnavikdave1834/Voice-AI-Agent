import json

import pytest
from starlette.testclient import TestClient

from config.settings import Settings
from phone_calling.sessions import ConversationSessionStore


class FakeAgent:
    confirmed = False

    def __init__(self, settings, enable_audio=True):
        self.settings = settings
        self.enable_audio = enable_audio
        self.transcript = []
        self.dialogue_manager = self

    @property
    def booking_state(self):
        return self

    def get_greeting(self):
        greeting = "Hello from websocket."
        self.transcript.append({"role": "assistant", "text": greeting})
        return greeting

    def process_text_input(self, text):
        self.transcript.append({"role": "user", "text": text})
        return f"Echo: {text}"


def test_websocket_text_roundtrip():
    from phone_calling import server

    store = ConversationSessionStore(
        Settings(_env_file=None),
        agent_factory=FakeAgent,
    )
    session = store.create()
    session.agent.get_greeting()

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(server, "session_store", store)

    client = TestClient(server.app)
    with client.websocket_connect(f"/ws/{session.session_id}") as websocket:
        connected = json.loads(websocket.receive_text())
        assert connected["type"] == "connected"
        assert connected["session_id"] == session.session_id

        websocket.send_text(json.dumps({"type": "text", "content": "Book a checkup"}))
        reply = json.loads(websocket.receive_text())

        assert reply["type"] == "assistant"
        assert reply["user_text"] == "Book a checkup"
        assert "Echo: Book a checkup" in reply["content"]

    monkeypatch.undo()


def test_websocket_switch_to_phone():
    from phone_calling import server

    store = ConversationSessionStore(
        Settings(_env_file=None),
        agent_factory=FakeAgent,
    )
    session = store.create()

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(server, "session_store", store)

    client = TestClient(server.app)
    with client.websocket_connect(f"/ws/{session.session_id}") as websocket:
        json.loads(websocket.receive_text())
        websocket.send_text(json.dumps({"type": "switch_channel", "channel": "phone"}))
        reply = json.loads(websocket.receive_text())

        assert reply["type"] == "channel_ready"
        assert reply["channel"] == "phone"
        assert reply["handoff_code"]

    monkeypatch.undo()
