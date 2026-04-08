"""
Kokoro TTS HTTP Server — CPU-only ONNX inference.

Provides a simple REST API for text-to-speech synthesis.
Runs entirely on CPU using ONNX runtime — no GPU needed.

Endpoints:
  POST /synthesize  — synthesize text to audio
  GET  /voices      — list available voices
  GET  /health      — health check
"""

import io
import os

import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI(title="Kokoro TTS Server")

# Global model instance (loaded once on startup)
_kokoro = None


def get_kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro

        model_dir = os.environ.get("KOKORO_MODEL_DIR", "/app/models")
        model_path = os.path.join(model_dir, "kokoro-v1.0.onnx")
        voices_path = os.path.join(model_dir, "voices-v1.0.bin")

        # Download if not present
        if not os.path.exists(model_path):
            import urllib.request

            os.makedirs(model_dir, exist_ok=True)
            print("Downloading Kokoro model...")
            urllib.request.urlretrieve(
                "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
                model_path,
            )
            urllib.request.urlretrieve(
                "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
                voices_path,
            )
            print("Download complete.")

        _kokoro = Kokoro(model_path, voices_path)
    return _kokoro


AVAILABLE_VOICES = [
    {"id": "af_heart", "name": "Heart", "accent": "American", "gender": "Female"},
    {"id": "af_bella", "name": "Bella", "accent": "American", "gender": "Female"},
    {"id": "af_sarah", "name": "Sarah", "accent": "American", "gender": "Female"},
    {"id": "am_adam", "name": "Adam", "accent": "American", "gender": "Male"},
    {"id": "am_michael", "name": "Michael", "accent": "American", "gender": "Male"},
    {"id": "bf_emma", "name": "Emma", "accent": "British", "gender": "Female"},
    {"id": "bm_george", "name": "George", "accent": "British", "gender": "Male"},
]


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "bf_emma"
    speed: float = 1.0


@app.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    """Synthesize text to audio (WAV)."""
    if not req.text.strip():
        raise HTTPException(400, "Text is required.")

    kokoro = get_kokoro()

    try:
        samples, sample_rate = kokoro.create(
            req.text,
            voice=req.voice,
            speed=req.speed,
        )
    except Exception as e:
        raise HTTPException(500, f"TTS synthesis failed: {str(e)}") from e

    # Convert to WAV bytes
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV")
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="audio/wav",
        headers={"X-Sample-Rate": str(sample_rate)},
    )


@app.get("/voices")
async def list_voices():
    """List available TTS voices."""
    return {"voices": AVAILABLE_VOICES}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "kokoro-tts"}
