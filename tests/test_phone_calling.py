from xml.etree import ElementTree

import pytest
from starlette.testclient import TestClient

from config.settings import Settings
from phone_calling.channels import Channel
from phone_calling.sessions import ConversationSessionStore, PhoneCallSessionStore
from phone_calling.twiml import gather_response, hangup_response


class FakeAgent:
    def __init__(self, settings, enable_audio=True):
        self.settings = settings
        self.enable_audio = enable_audio
        self.transcript = []
        self.dialogue_manager = type(
            "DialogueManager",
            (),
            {"booking_state": type("BookingState", (), {"confirmed": False})()},
        )()

    def get_greeting(self):
        greeting = "Hello from phone."
        self.transcript.append({"role": "assistant", "text": greeting})
        return greeting

    def process_text_input(self, text):
        self.transcript.append({"role": "user", "text": text})
        return f"You said {text}."


def test_gather_response_builds_twilio_speech_prompt():
    xml = gather_response(
        "Hello & welcome",
        "https://example.com/voice/input",
        voice="alice",
        language="en-US",
    )

    root = ElementTree.fromstring(xml)
    gather = root.find("Gather")

    assert root.tag == "Response"
    assert gather is not None
    assert gather.attrib["input"] == "speech"
    assert gather.attrib["action"] == "https://example.com/voice/input"
    assert gather.find("Say").text == "Hello & welcome"


def test_hangup_response_speaks_then_hangs_up():
    root = ElementTree.fromstring(
        hangup_response("Booked. Goodbye.", voice="alice")
    )

    assert root.find("Say").text == "Booked. Goodbye."
    assert root.find("Hangup") is not None


def test_phone_sessions_reuse_agent_and_disable_local_audio():
    store = PhoneCallSessionStore(
        Settings(_env_file=None),
        agent_factory=FakeAgent,
    )

    first_session, first_created = store.get_or_create_call("CA123")
    second_session, second_created = store.get_or_create_call("CA123")

    assert first_created is True
    assert second_created is False
    assert first_session is second_session
    assert first_session.agent.enable_audio is False


def test_create_web_session_enables_audio():
    store = ConversationSessionStore(
        Settings(_env_file=None),
        agent_factory=FakeAgent,
    )

    session = store.create(channel=Channel.WEB)

    assert session.channel == Channel.WEB
    assert session.agent.enable_audio is True
    assert session.handoff_code.isdigit()
    assert len(session.handoff_code) == 6


def test_switch_channel_generates_new_handoff_code():
    store = ConversationSessionStore(
        Settings(_env_file=None),
        agent_factory=FakeAgent,
    )
    session = store.create(channel=Channel.WEB)
    original_code = session.handoff_code

    updated = store.switch_channel(session.session_id, Channel.PHONE)

    assert updated is not None
    assert updated.channel == Channel.PHONE
    assert updated.handoff_code != original_code


def test_link_call_to_handoff_reuses_web_session():
    store = ConversationSessionStore(
        Settings(_env_file=None),
        agent_factory=FakeAgent,
    )
    web_session = store.create(channel=Channel.WEB)
    web_session.agent.process_text_input("I need a dental appointment")

    linked = store.link_call_to_handoff("CA999", web_session.handoff_code)

    assert linked is not None
    assert linked.session_id == web_session.session_id
    assert linked.agent is web_session.agent
    assert store.get_by_call_sid("CA999") is linked


def test_voice_endpoint_returns_twiml(monkeypatch):
    from phone_calling import server

    store = PhoneCallSessionStore(
        Settings(_env_file=None),
        agent_factory=FakeAgent,
    )
    monkeypatch.setattr(server, "session_store", store)

    client = TestClient(server.app)
    response = client.post("/voice", data={"CallSid": "CA123"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert ElementTree.fromstring(response.text).find("Gather") is not None


def test_phone_config_api():
    from phone_calling import server

    store = ConversationSessionStore(
        Settings(_env_file=None),
        agent_factory=FakeAgent,
    )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(server, "session_store", store)
    monkeypatch.setattr(server.settings, "TWILIO_PHONE_NUMBER", "+15551234567")

    client = TestClient(server.app)
    response = client.get("/api/phone-config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["phone_number"] == "+15551234567"
    assert "message" in payload

    monkeypatch.undo()


def test_create_session_api_returns_snapshot():
    from phone_calling import server

    store = ConversationSessionStore(
        Settings(_env_file=None),
        agent_factory=FakeAgent,
    )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(server, "session_store", store)

    client = TestClient(server.app)
    response = client.post("/api/sessions", json={"channel": "web"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"].startswith("sess_")
    assert payload["channel"] == "web"
    assert payload["handoff_code"]

    monkeypatch.undo()


def test_switch_session_channel_api():
    from phone_calling import server

    store = ConversationSessionStore(
        Settings(_env_file=None),
        agent_factory=FakeAgent,
    )
    session = store.create(channel=Channel.WEB)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(server, "session_store", store)

    client = TestClient(server.app)
    response = client.post(
        f"/api/sessions/{session.session_id}/switch",
        json={"channel": "phone"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["channel"] == "phone"
    assert payload["handoff_code"]

    monkeypatch.undo()
