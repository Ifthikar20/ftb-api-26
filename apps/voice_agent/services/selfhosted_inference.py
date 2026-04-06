"""
Self-hosted inference service — complete privacy, no external API calls.

Connects to locally-running services:
  - vLLM (Qwen2.5-7B or fine-tuned model) for conversation + extraction
  - Faster-Whisper for speech-to-text
  - Kokoro TTS for text-to-speech

All data stays on your infrastructure. Zero data leaves your network.

Required env vars:
  SELFHOSTED_LLM_URL=http://localhost:8000/v1       (vLLM OpenAI-compatible)
  SELFHOSTED_STT_URL=http://localhost:8001/v1        (Faster-Whisper server)
  SELFHOSTED_TTS_URL=http://localhost:8002            (Kokoro TTS server)
  SELFHOSTED_LLM_MODEL=Qwen/Qwen2.5-7B-Instruct-AWQ (or your fine-tuned model)
"""

import json
import logging
import time

import httpx
from django.conf import settings

logger = logging.getLogger("apps")


def _llm_url():
    return getattr(settings, "SELFHOSTED_LLM_URL", "http://localhost:8000/v1")


def _stt_url():
    return getattr(settings, "SELFHOSTED_STT_URL", "http://localhost:8001/v1")


def _tts_url():
    return getattr(settings, "SELFHOSTED_TTS_URL", "http://localhost:8002")


def _llm_model():
    return getattr(settings, "SELFHOSTED_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct-AWQ")


class SelfHostedLLM:
    """Interface to the self-hosted vLLM server (OpenAI-compatible API)."""

    @staticmethod
    def chat(messages, *, tools=None, temperature=0.7, max_tokens=1024, guided_json=None):
        """
        Send a chat completion request to the self-hosted LLM.
        Supports function calling and guided JSON decoding.
        """
        payload = {
            "model": _llm_model(),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        if tools:
            payload["tools"] = tools

        if guided_json:
            payload["extra_body"] = {"guided_json": guided_json}

        start = time.monotonic()
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{_llm_url()}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()

        elapsed_ms = int((time.monotonic() - start) * 1000)
        data = resp.json()

        choice = data["choices"][0]
        result = {
            "content": choice["message"].get("content", ""),
            "tool_calls": choice["message"].get("tool_calls", []),
            "finish_reason": choice.get("finish_reason", ""),
            "model": data.get("model", ""),
            "usage": data.get("usage", {}),
            "latency_ms": elapsed_ms,
        }

        logger.info(
            "selfhosted_llm_call",
            extra={
                "model": result["model"],
                "latency_ms": elapsed_ms,
                "tokens": result["usage"],
            },
        )

        return result

    @staticmethod
    def extract_json(prompt, json_schema):
        """
        Call the LLM with guided JSON decoding — guarantees valid structured output.
        Uses vLLM's outlines integration for constrained generation.
        """
        payload = {
            "model": _llm_model(),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 2048,
            "stream": False,
            "extra_body": {"guided_json": json_schema},
        }

        start = time.monotonic()
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{_llm_url()}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()

        elapsed_ms = int((time.monotonic() - start) * 1000)
        data = resp.json()
        content = data["choices"][0]["message"].get("content", "{}")

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("selfhosted_llm_json_parse_failed", extra={"content": content[:500]})
            parsed = {}

        return {
            "data": parsed,
            "model": data.get("model", ""),
            "latency_ms": elapsed_ms,
        }


class SelfHostedSTT:
    """Interface to the self-hosted Faster-Whisper server."""

    @staticmethod
    def transcribe(audio_bytes, *, language="en", format="wav"):
        """
        Transcribe audio bytes using the self-hosted Whisper server.
        Returns the transcript text and segments.
        """
        start = time.monotonic()
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{_stt_url()}/audio/transcriptions",
                files={"file": (f"audio.{format}", audio_bytes, f"audio/{format}")},
                data={
                    "model": "Systran/faster-whisper-large-v3",
                    "language": language,
                    "response_format": "verbose_json",
                },
            )
            resp.raise_for_status()

        elapsed_ms = int((time.monotonic() - start) * 1000)
        data = resp.json()

        logger.info(
            "selfhosted_stt_transcribe",
            extra={"latency_ms": elapsed_ms, "duration": data.get("duration", 0)},
        )

        return {
            "text": data.get("text", ""),
            "segments": data.get("segments", []),
            "language": data.get("language", language),
            "duration": data.get("duration", 0),
            "latency_ms": elapsed_ms,
        }


class SelfHostedTTS:
    """Interface to the self-hosted Kokoro TTS server."""

    @staticmethod
    def synthesize(text, *, voice="bf_emma", speed=1.0):
        """
        Synthesize text to audio using the self-hosted Kokoro TTS.
        Returns audio bytes (WAV format).
        """
        start = time.monotonic()
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{_tts_url()}/synthesize",
                json={
                    "text": text,
                    "voice": voice,
                    "speed": speed,
                },
            )
            resp.raise_for_status()

        elapsed_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "selfhosted_tts_synthesize",
            extra={"latency_ms": elapsed_ms, "text_len": len(text), "voice": voice},
        )

        return {
            "audio": resp.content,
            "content_type": resp.headers.get("content-type", "audio/wav"),
            "latency_ms": elapsed_ms,
        }

    @staticmethod
    def list_voices():
        """List available TTS voices."""
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(f"{_tts_url()}/voices")
                resp.raise_for_status()
                return resp.json()
        except Exception:
            return {
                "voices": [
                    {"id": "af_heart", "name": "Heart (American Female)"},
                    {"id": "af_bella", "name": "Bella (American Female)"},
                    {"id": "am_adam", "name": "Adam (American Male)"},
                    {"id": "am_michael", "name": "Michael (American Male)"},
                    {"id": "bf_emma", "name": "Emma (British Female)"},
                    {"id": "bm_george", "name": "George (British Male)"},
                ]
            }
