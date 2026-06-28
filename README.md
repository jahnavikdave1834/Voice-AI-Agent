# 🎙️ Voice AI Appointment Booking Agent

> An autonomous AI receptionist that understands voice requests, manages appointment scheduling, checks calendar availability, and sends booking confirmations without human intervention.

---

# Problem Statement

Appointment-driven businesses such as clinics, salons, consultancies, and service centers often lose revenue due to missed calls, scheduling conflicts, delayed responses, and manual booking processes. Traditional receptionist workflows do not scale efficiently and are prone to human error.

This project addresses these challenges by building a Voice AI Agent capable of handling natural conversations, collecting booking information, checking real-time availability, scheduling appointments, and sending confirmations automatically.

---

# Features
s
### Voice Processing

* Speech-to-Text using OpenAI Whisper (Local)
* Text-to-Speech using gTTS
* Voice and text-based interaction support

### Conversational AI

* Multi-turn dialogue management
* Context-aware conversation memory
* Intelligent slot-filling workflow
* Structured information extraction
* Booking confirmation workflow

### Appointment Management

* Real-time calendar availability checking
* Alternative slot suggestions
* Automated appointment creation
* Booking validation before confirmation

### Notifications

* Email confirmations via Gmail SMTP
* Webhook notifications for external systems

### User Experience

* Live conversation transcript
* Booking progress tracker
* Interactive web interface
* Audio playback of AI responses

### Reliability & Validation

* Date, email, and phone validation
* Ambiguous date handling
* Out-of-hours detection
* Fully-booked schedule handling
* Retry mechanisms for failed interactions

---

# Tech Stack

| Layer               | Technology                      |
| ------------------- | ------------------------------- |
| Frontend            | Streamlit / Gradio              |
| Speech-to-Text      | OpenAI Whisper                  |
| Text-to-Speech      | gTTS                            |
| LLM Engine          | Gemini 1.5 Flash / Groq Llama 3 |
| Conversation Memory | LangChain                       |
| Calendar Service    | Google Calendar API             |
| Notifications       | Gmail SMTP, Webhooks            |
| Audio Processing    | SoundDevice, Scipy              |
| Testing             | Pytest                          |
| Configuration       | Python Dotenv                   |
| Version Control     | Git & GitHub                    |

---

# System Architecture

The application follows a four-layer architecture:

```text
┌───────────────────────────────┐
│ Layer 1: Voice Interface      │
│ Whisper + gTTS               │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Layer 2: Dialogue Management  │
│ LLM + LangChain Memory       │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Layer 3: Booking Engine       │
│ Calendar Availability Check   │
│ Appointment Creation          │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Layer 4: Notifications        │
│ Email + Webhooks              │
└───────────────────────────────┘
```

Architecture Diagram:

```text
docs/architecture.png
```

---

# Project Structure

```text
voice-booking-agent/
│
├── app.py
├── requirements.txt
├── README.md
├── .env.example
│
├── src/
│   ├── voice/
│   │   ├── stt.py
│   │   └── tts.py
│   │
│   ├── dialogue/
│   │   ├── agent.py
│   │   ├── state.py
│   │   ├── prompts.py
│   │   └── slot_extractor.py
│   │
│   ├── calendar_service/
│   │   ├── availability.py
│   │   ├── booking.py
│   │   └── mock_calendar.py
│   │
│   ├── notifications/
│   │   ├── email_sender.py
│   │   └── webhook_client.py
│   │
│   └── utils/
│       ├── validators.py
│       ├── date_parser.py
│       └── logger.py
│
├── tests/
│
└── docs/
    ├── architecture.png
    ├── report.pdf
    └── demo_screenshot.png
```

---

# Installation & Setup

## 1. Clone Repository

```bash
git clone https://github.com/your-username/voice-booking-agent.git

cd voice-booking-agent
```

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv

venv\Scripts\activate
```

### Linux / macOS

```bash
python -m venv venv

source venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create a `.env` file:

```env
GEMINI_API_KEY=

GOOGLE_CALENDAR_CREDS_JSON=

GMAIL_USER=

GMAIL_APP_PASSWORD=
```

## 5. Configure Google Calendar API

1. Create a Google Cloud Project
2. Enable Google Calendar API
3. Create a Service Account
4. Download the JSON credentials file
5. Share your calendar with the service account email
6. Update `.env` with the credentials path

---

# Running the Application

```bash
streamlit run app.py
```

After launching:

* Open the local Streamlit URL
* Speak into the microphone or upload audio
* Allow the AI assistant to collect booking details
* Confirm the appointment
* Receive email confirmation

---

# Running as a Phone Call

The same booking agent can answer real phone calls through Twilio Voice, or run
in a browser over WebSockets. Both channels share one backend session store, so
a caller can start on the web and continue on the phone with a six-digit handoff
code.

Twilio handles phone speech recognition and phone audio playback. The browser
client uses WebSockets for real-time text and microphone audio, while this
project reuses the existing `VoiceAgent` conversation and calendar workflow.

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

## 2. Start the transport server

```bash
uvicorn phone_calling.server:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

## 3. Expose the webhook publicly

For local development, use a tunnel such as ngrok:

```bash
ngrok http 8000
```

Add the public HTTPS URL to `.env`:

```env
PUBLIC_BASE_URL=https://your-ngrok-domain.ngrok-free.app
TWILIO_VOICE=alice
TWILIO_LANGUAGE=en-US
TWILIO_PHONE_NUMBER=+1234567890
BACKEND_URL=http://127.0.0.1:8000
```

## 4. Exotel Configuration

Configure the Exotel Voicebot (or AgentStream) Applet with your backend endpoint.

* **Voicebot/AgentStream WebSocket URL:** `wss://your-domain/exotel/stream`
* **Fallback Webhook (if applicable):** `https://your-domain/voice`
* **HTTP Method:** `POST`
* **Call Status Webhook:** `https://your-domain/voice/status`
* **Status Callback Method:** `POST`

When a customer calls the Exotel number, the call is routed to the configured Voicebot/AgentStream applet, which streams the caller's audio to the AI backend. The backend processes the conversation, checks Google Calendar availability, books appointments, and responds with synthesized voice in real time.


## 5. Call to Book

* Configure your Exotel Voicebot/AgentStream applet to point to your AI backend.
* Ensure your backend is publicly accessible (e.g., via ngrok or a deployed server).
* Call your Exotel virtual number from any phone.
* Speak naturally with the AI assistant—no browser interaction or typing is required.
* The assistant collects appointment details, checks Google Calendar for availability, books the appointment, sends a confirmation email, and ends the call upon successful booking.

Once the Exotel number is configured, every incoming call is automatically routed to the AI backend for real-time voice interaction and appointment scheduling.


---

## Screenshots

<img width="4000" height="3000" alt="mix" src="https://github.com/user-attachments/assets/a78c0943-720b-4812-8224-f55e49d56089" />


Run all tests:

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

Coverage includes:

* Booking state validation
* Slot extraction
* Calendar integration
* Notification services
* Edge-case handling

---

# Future Improvements

* WhatsApp Voice Notes
* Multi-language Support
* Appointment Cancellation
* Appointment Rescheduling
* SMS Reminders
* CRM Integration
* Admin Dashboard
* Analytics & Reporting

---

# Security Considerations

* No API keys stored in source code
* Environment variable based configuration
* Credentials excluded through `.gitignore`
* Input validation before booking creation
* Confirmation gate before calendar write

---
