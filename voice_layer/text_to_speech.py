"""
Voice Layer — Text-to-Speech using gTTS.

Synthesizes agent response text into MP3 files for playback via Streamlit.
"""

import logging
import os
import tempfile
from pathlib import Path

from gtts import gTTS

logger = logging.getLogger(__name__)


class TextToSpeech:
    """Text-to-Speech engine using Google Translate TTS (gTTS)."""

    DEFAULT_LANG = "en"
    OUTPUT_DIR = Path(tempfile.gettempdir()) / "voice_ai_tts"

    def __init__(self, lang: str = DEFAULT_LANG):
        self.lang = lang

        self.OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        logger.info(
            f"TextToSpeech initialized "
            f"(lang={lang}, dir={self.OUTPUT_DIR})."
        )

    def synthesize(
        self,
        text: str,
        filename: str = "response.mp3"
    ) -> str:
        """
        Convert text to an MP3 audio file.
        """

        if not text or not text.strip():
            raise ValueError(
                "Cannot synthesize empty text."
            )

        output_path = str(
            self.OUTPUT_DIR / filename
        )

        try:
            tts = gTTS(
                text=text,
                lang=self.lang,
                slow=False
            )

            tts.save(output_path)

            logger.info(
                f"TTS saved to: {output_path}"
            )

            return output_path

        except Exception as e:

            logger.error(
                f"TTS synthesis failed: {e}"
            )

            raise RuntimeError(
                f"Text-to-speech synthesis failed: {e}"
            ) from e

    def synthesize_to_bytes(
        self,
        text: str
    ) -> bytes:
        """
        Convert text directly into MP3 bytes.
        """

        if not text or not text.strip():
            raise ValueError(
                "Cannot synthesize empty text."
            )

        try:
            tts = gTTS(
                text=text,
                lang=self.lang,
                slow=False
            )

            output_path = (
                self.OUTPUT_DIR /
                "temp_response.mp3"
            )

            tts.save(str(output_path))

            with open(output_path, "rb") as f:
                audio_bytes = f.read()

            logger.info(
                f"TTS synthesized "
                f"{len(audio_bytes)} bytes"
            )

            return audio_bytes

        except Exception as e:

            logger.error(
                f"TTS byte synthesis failed: {e}"
            )

            raise RuntimeError(
                f"Text-to-speech synthesis failed: {e}"
            ) from e
        

    # =====================================================
    # COMPATIBILITY METHOD
    # =====================================================

    def synthesize_speech(
        self,
        text: str
    ) -> bytes:

        """
        Compatibility wrapper used by agent.py
        """

        return self.synthesize_to_bytes(text)