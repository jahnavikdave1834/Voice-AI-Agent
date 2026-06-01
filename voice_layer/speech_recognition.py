import logging
import os
import tempfile
import time

import whisper

from pydub import AudioSegment

logger = logging.getLogger(__name__)


class SpeechRecognizer:

    MAX_RETRIES = 3

    MIN_AUDIO_BYTES = 1000

    # =====================================================
    # INIT
    # =====================================================

    def __init__(
        self,
        model_size="medium"
    ):

        self.whisper_model_size = model_size

        self.whisper_model = None

        logger.info(
            f"SpeechRecognizer initialized "
            f"(model={model_size})."
        )

    # =====================================================
    # LOAD MODEL
    # =====================================================

    def _load_model(self):

        if self.whisper_model is None:

            logger.info(
                f"Loading Whisper model: "
                f"'{self.whisper_model_size}' ..."
            )

            self.whisper_model = (
                whisper.load_model(
                    self.whisper_model_size
                )
            )

            logger.info(
                "Whisper model loaded successfully."
            )

    # =====================================================
    # TRANSCRIBE FILE
    # =====================================================

    def transcribe_from_file(
        self,
        audio_path: str
    ) -> str:

        self._load_model()

        logger.info(
            f"Transcribing file: "
            f"{audio_path}"
        )

        for attempt in range(
            1,
            self.MAX_RETRIES + 1
        ):

            try:

                logger.info(
                    f"STT file attempt "
                    f"{attempt}/"
                    f"{self.MAX_RETRIES}"
                )

                result = (
                    self.whisper_model.transcribe(
                        audio_path,
                        fp16=False,
                    )
                )

                logger.info(
                    f"Raw Whisper file result: "
                    f"{result}"
                )

                text = (
                    result.get(
                        "text",
                        ""
                    ).strip()
                )

                if text:

                    return text

                logger.warning(
                    f"Empty transcription "
                    f"(attempt {attempt})"
                )

            except Exception as e:

                logger.error(
                    f"STT file error "
                    f"(attempt {attempt}): "
                    f"{e}"
                )

            time.sleep(1)

        return ""

    # =====================================================
    # TRANSCRIBE AUDIO BYTES
    # =====================================================

    def transcribe_from_bytes(
        self,
        audio_bytes: bytes
    ) -> str:

        if not audio_bytes:

            raise RuntimeError(
                "No audio data received."
            )

        if len(audio_bytes) < self.MIN_AUDIO_BYTES:

            raise RuntimeError(
                "Audio too short or empty."
            )

        logger.info(
            f"Received audio bytes: "
            f"{len(audio_bytes)}"
        )

        # =================================================
        # SAVE TEMP AUDIO
        # =================================================

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        ) as raw_tmp:

            raw_tmp.write(audio_bytes)

            raw_path = raw_tmp.name

        logger.info(
            f"Raw audio temp file: "
            f"{raw_path}"
        )

        converted_path = raw_path.replace(
            ".wav",
            "_converted.wav"
        )

        try:

            audio = AudioSegment.from_file(
                raw_path
            )

            # =============================================
            # SILENCE DETECTION
            # =============================================

            if audio.dBFS < -45:

                raise RuntimeError(
                    "Audio too silent."
                )

            # =============================================
            # STANDARDIZE AUDIO
            # =============================================

            audio = (
                audio
                .set_frame_rate(16000)
                .set_channels(1)
            )

            audio.export(
                converted_path,
                format="wav"
            )

            logger.info(
                f"Converted audio file: "
                f"{converted_path}"
            )

            # =============================================
            # TRANSCRIBE
            # =============================================

            text = (
                self.transcribe_from_file(
                    converted_path
                )
            )

            if not text.strip():

                raise RuntimeError(
                    "No speech detected."
                )

            logger.info(
                f"Final transcription: "
                f"{text}"
            )

            return text.strip()

        finally:

            # =============================================
            # CLEANUP
            # =============================================

            for path in [
                raw_path,
                converted_path
            ]:

                try:

                    if os.path.exists(path):

                        os.unlink(path)

                except Exception:

                    pass