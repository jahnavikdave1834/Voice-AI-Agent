import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parent
    ),
)

import logging

import streamlit as st

from utilities.streamlit_compat import install_shutdown_guard

install_shutdown_guard()

from config.settings import get_settings

from dialogue_management.agent import (
    VoiceAgent,
)

from dialogue_management.booking_state import (
    FIELD_LABELS,
    REQUIRED_FIELDS,
)

# =========================================================
# LOGGER
# =========================================================

logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(

    page_title="Aria Voice AI",

    page_icon="🎙️",

    layout="wide",

    initial_sidebar_state="collapsed",
)

# =========================================================
# GLOBAL CSS
# =========================================================

st.markdown(
    """
<style>

/* =====================================================
GLOBAL
===================================================== */

.stApp {

background:
radial-gradient(circle at top left,
#7c3aed 0%,
transparent 25%),

radial-gradient(circle at bottom right,
#2563eb 0%,
transparent 25%),

#050816;

color: white;
}

section[data-testid="stSidebar"] {

display: none;
}

header {

visibility: hidden;
}

footer {

visibility: hidden;
}

.block-container {

padding-top: 1rem;
padding-bottom: 1rem;

max-width: 1500px;
}

/* =====================================================
HEADER
===================================================== */

.main-title {

font-size: 46px;

font-weight: 700;

background:
linear-gradient(
90deg,
#c084fc,
#60a5fa
);

-webkit-background-clip: text;
-webkit-text-fill-color: transparent;

text-align: center;

margin-bottom: 0.3rem;
}

.subtitle {

text-align: center;

color: #94a3b8;

font-size: 18px;

margin-bottom: 2rem;
}

/* =====================================================
GLASS CARD
===================================================== */

.glass {

background:
rgba(255,255,255,0.05);

backdrop-filter: blur(20px);

border:
1px solid rgba(255,255,255,0.08);

border-radius: 28px;

padding: 24px;
}

/* =====================================================
VOICE PANEL
===================================================== */

.voice-panel {

text-align: center;

padding-top: 15px;

padding-bottom: 15px;
}

/* =====================================================
MIC ANIMATION
===================================================== */

.mic-circle {

width: 140px;

height: 140px;

margin: auto;

border-radius: 50%;

display: flex;

align-items: center;

justify-content: center;

font-size: 62px;

background:
linear-gradient(
135deg,
#7c3aed,
#2563eb
);

box-shadow:
0 0 40px rgba(124,58,237,0.5);

animation: pulse 2s infinite;
}

@keyframes pulse {

0% {
transform: scale(1);
}

50% {
transform: scale(1.05);
}

100% {
transform: scale(1);
}
}

/* =====================================================
TRANSCRIPT
===================================================== */

.transcript-box {

background:
rgba(255,255,255,0.06);

padding: 18px;

border-radius: 18px;

margin-top: 22px;

font-size: 17px;

color: white;
}

/* =====================================================
ASSISTANT MESSAGE
===================================================== */

.assistant-box {

background:
linear-gradient(
135deg,
#7c3aed,
#4f46e5
);

padding: 18px;

border-radius: 18px;

margin-top: 18px;

font-size: 17px;

color: white;
}

/* =====================================================
BOOKING CARD
===================================================== */

.booking-card {

background:
rgba(255,255,255,0.05);

padding: 18px;

border-radius: 18px;

margin-bottom: 14px;
}

.booking-title {

font-size: 15px;

font-weight: 600;

margin-bottom: 8px;

color: #cbd5e1;
}

.booking-value {

font-size: 16px;

font-weight: 600;

color: #22c55e;
}

.booking-missing {

font-size: 15px;

color: #f59e0b;
}

/* =====================================================
PROGRESS
===================================================== */

.progress-pill {

display: inline-block;

padding: 10px 18px;

border-radius: 999px;

background:
linear-gradient(
90deg,
#7c3aed,
#2563eb
);

font-weight: 600;

margin-bottom: 18px;
}

.stProgress > div > div {

background:
linear-gradient(
90deg,
#7c3aed,
#2563eb
);
}

/* =====================================================
CONVERSATION HISTORY
===================================================== */

.history-user {

background:
rgba(255,255,255,0.06);

padding: 14px;

border-radius: 16px;

margin-bottom: 12px;
}

.history-assistant {

background:
linear-gradient(
135deg,
#7c3aed,
#4f46e5
);

padding: 14px;

border-radius: 16px;

margin-bottom: 12px;
}

/* =====================================================
BUTTON
===================================================== */

.stButton button {

background:
linear-gradient(
90deg,
#7c3aed,
#2563eb
);

color: white;

border: none;

border-radius: 14px;

height: 50px;

font-weight: 600;
}

</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# SESSION STATE
# =========================================================

def init_session_state():

    if "agent" not in st.session_state:

        settings = get_settings()

        st.session_state.agent = (
            VoiceAgent(settings)
        )

        st.session_state.transcript = []

        st.session_state.last_audio_hash = None

        st.session_state.latest_user_text = ""

        st.session_state.latest_response = ""

        st.session_state.greeting_done = False

        st.session_state.use_phone_mode = True

        logger.info(
            "Session initialized."
        )

# =========================================================
# HEADER
# =========================================================

def render_header():

    st.markdown(
        """
<div class="main-title">
Aria — Voice AI Receptionist
</div>

<div class="subtitle">
Conversational AI Appointment Booking Assistant
</div>
""",
        unsafe_allow_html=True,
    )

# =========================================================
# BOOKING PROGRESS
# =========================================================

def render_booking_progress(agent):

    state = (
        agent.dialogue_manager.booking_state
    )

    filled = sum(

        1

        for field in REQUIRED_FIELDS

        if getattr(
            state,
            field,
            None,
        )
    )

    total = len(REQUIRED_FIELDS)

    progress = filled / total

    st.markdown(
        f"""
<div class="progress-pill">
📋 Collecting Information ({filled}/{total})
</div>
""",
        unsafe_allow_html=True,
    )

    st.progress(progress)

    st.markdown("<br>", unsafe_allow_html=True)

    for field in REQUIRED_FIELDS:

        label = FIELD_LABELS[field]

        value = getattr(
            state,
            field,
            None,
        )

        if value:

            value_html = (
                f"""
<div class="booking-value">
{value}
</div>
"""
            )

        else:

            value_html = (
                """
<div class="booking-missing">
Not provided yet
</div>
"""
            )

        st.markdown(
            f"""
<div class="booking-card">

<div class="booking-title">
{label}
</div>

{value_html}

</div>
""",
            unsafe_allow_html=True,
        )

# =========================================================
# CONVERSATION HISTORY
# =========================================================

def render_history(messages):

    st.markdown("### Conversation History")

    history = st.container(
        height=350
    )

    with history:

        for msg in messages[-8:]:

            if msg["role"] == "user":

                st.markdown(
                    f"""
<div class="history-user">
🎤 {msg["text"]}
</div>
""",
                    unsafe_allow_html=True,
                )

            else:

                st.markdown(
                    f"""
<div class="history-assistant">
🤖 {msg["text"]}
</div>
""",
                    unsafe_allow_html=True,
                )

# =========================================================
# LIVE CHANNEL SWITCH
# =========================================================

def render_channel_switch(settings):

    st.markdown("### Book by Phone")

    backend_url = settings.BACKEND_URL.rstrip("/")
    phone_number = getattr(settings, "EXOTEL_PHONE_NUMBER", "") or ""
    phone_display = phone_number or "Set EXOTEL_PHONE_NUMBER in .env"

    st.info(
        "Call Aria directly on your phone using Exotel. No typing or browser microphone needed."
    )

    st.markdown(f"**Exotel number:** `{phone_display}`")

    if phone_number:
        st.link_button(
            "Call Aria Now",
            f"tel:{phone_number.replace(' ', '')}",
            use_container_width=True,
        )

    st.link_button(
        "Open Call Page",
        backend_url,
        use_container_width=True,
    )

    st.caption(f"Webhook: `{backend_url}/voice`")

    if not phone_number:
        st.warning(
            "Add `EXOTEL_PHONE_NUMBER=09513886363` to your `.env` file and restart the server."
        )


def render_phone_panel(settings):
    phone_number = getattr(settings, "EXOTEL_PHONE_NUMBER", "") or ""

    st.markdown(
        """
<div class="mic-circle">
📞
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if phone_number:
        st.markdown(
            f"""
<div class="assistant-box">

📞 **Call to book**

<br><br>

Dial **{phone_number}** and speak with Aria to schedule your appointment.

</div>
""",
            unsafe_allow_html=True,
        )

        st.link_button(
            "Call Aria Now",
            f"tel:{phone_number.replace(' ', '')}",
            use_container_width=True,
        )
    else:
        st.warning(
            "Set `EXOTEL_PHONE_NUMBER` in `.env`, restart the server, then call that number."
        )

    st.markdown(
        """
<div class="transcript-box">

1. Call the number above<br>
2. Tell Aria what you need<br>
3. Answer her questions<br>
4. Receive email confirmation

</div>
""",
        unsafe_allow_html=True,
    )

# =========================================================
# MAIN
# =========================================================

def main():

    init_session_state()

    render_header()

    agent = st.session_state.agent

    left, right = st.columns(
        [2.2, 1]
    )

    # =====================================================
    # LEFT
    # =====================================================

    with left:

        st.markdown(
            """
<div class="glass voice-panel">
""",
            unsafe_allow_html=True,
        )

        settings = get_settings()
        render_phone_panel(settings)

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<br>",
            unsafe_allow_html=True,
        )

        if st.session_state.get("transcript"):
            render_history(
                st.session_state.transcript
            )

    with right:

        render_channel_switch(get_settings())

        st.markdown("---")

        render_booking_progress(
            agent
        )

        st.markdown("---")

        if st.button(
            "🔄 Start New Booking",
            use_container_width=True,
        ):

            agent.reset()

            st.session_state.transcript = []

            st.session_state.last_audio_hash = None

            st.session_state.latest_user_text = ""

            st.session_state.latest_response = ""

            st.session_state.greeting_done = False

            st.rerun()

# =========================================================
# ENTRY
# =========================================================

if __name__ == "__main__":

    main()
