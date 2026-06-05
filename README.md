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

# Sample Booking Flow

### User

> I need a dental appointment next Tuesday at 3 PM.

### AI Agent

> Sure. May I know your name?

### User

> Jahnavi Dave.

### AI Agent

> Thank you. Could you share your contact number?

### User

> 9876543210

### AI Agent

> Your appointment is available on Tuesday at 3 PM. Shall I confirm the booking?

### User

> Yes.

### AI Agent

> Your appointment has been successfully booked. A confirmation email has been sent.

---


# Testing

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

* Twilio Voice Calling Integration
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
