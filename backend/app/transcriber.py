import os
import logging
from typing import Optional, Union
import numpy as np

logger = logging.getLogger("auralis.transcriber")

MODEL_NAME = os.environ.get("WHISPER_MODEL", "openai/whisper-tiny")
SAMPLE_RATE = 16000

class WhisperTranscriber:
    _instance: Optional["WhisperTranscriber"] = None

    def __init__(self):
        self.pipeline = None
        self.mock_mode = os.environ.get("MOCK_WHISPER", "false").lower() in ("true", "1", "yes")

    @classmethod
    def get_instance(cls) -> "WhisperTranscriber":
        if cls._instance is None:
            cls._instance = WhisperTranscriber()
        return cls._instance

    def load_model(self):
        if self.mock_mode or self.pipeline is not None:
            return

        from transformers import pipeline
        import torch

        device = "cuda:0" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
        pipeline_kwargs = {"model": MODEL_NAME, "device": device, "chunk_length_s": 30}

        # Try a fully offline load first (no huggingface.co calls) so a warm cache
        # doesn't pay for network round-trips on every container start; fall back
        # to a normal online load if the cache doesn't have the model yet.
        previous_offline_flag = os.environ.get("HF_HUB_OFFLINE")
        def restore_offline_flag():
            if previous_offline_flag is None:
                os.environ.pop("HF_HUB_OFFLINE", None)
            else:
                os.environ["HF_HUB_OFFLINE"] = previous_offline_flag

        try:
            os.environ["HF_HUB_OFFLINE"] = "1"
            logger.info(f"Loading Whisper model '{MODEL_NAME}' from local cache (no network)...")
            self.pipeline = pipeline("automatic-speech-recognition", **pipeline_kwargs)
        except Exception:
            restore_offline_flag()
            logger.info(f"Local cache miss, downloading '{MODEL_NAME}' from Hugging Face Hub...")
            self.pipeline = pipeline("automatic-speech-recognition", **pipeline_kwargs)
        finally:
            restore_offline_flag()
        logger.info("Whisper model loaded successfully.")

    def preprocess_audio(self, audio_path: str) -> np.ndarray:
        """
        Audio preprocessing:
        1. Loads audio from disk via soundfile.
        2. Converts multi-channel (stereo) to single-channel (mono).
        3. Resamples audio to 16,000 Hz (standard required by Whisper) using scipy.
        4. Normalizes amplitude to float32.
        """
        try:
            import soundfile as sf
            data, sr = sf.read(audio_path)
            # Convert to mono if multi-channel
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            # Resample if needed
            if sr != SAMPLE_RATE:
                from scipy import signal
                num_samples = int(len(data) * float(SAMPLE_RATE) / sr)
                data = signal.resample(data, num_samples)
            return data.astype(np.float32)
        except Exception as e:
            logger.warning(f"soundfile load failed ({e}), attempting fallback with librosa...")
            import librosa
            waveform, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
            return waveform

    def transcribe(self, audio_path: str) -> str:
        """
        Preprocesses audio and runs transcription using openai/whisper-tiny.
        """
        if self.mock_mode:
            logger.info(f"[MOCK] Transcribing {audio_path}")
            return f"Transcribed text for {os.path.basename(audio_path)}"

        if self.pipeline is None:
            self.load_model()

        # Run preprocessing
        preprocessed_waveform = self.preprocess_audio(audio_path)

        # Transcribe via Hugging Face pipeline
        result = self.pipeline(
            {"raw": preprocessed_waveform, "sampling_rate": SAMPLE_RATE},
            generate_kwargs={"task": "transcribe"}
        )

        text = result.get("text", "").strip()
        return text

def get_transcriber() -> WhisperTranscriber:
    return WhisperTranscriber.get_instance()
