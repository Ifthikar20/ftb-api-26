# Kokoro TTS — CPU-only ONNX server
# Runs text-to-speech entirely on CPU, freeing GPU for STT + LLM

FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    kokoro-onnx \
    fastapi \
    uvicorn \
    soundfile \
    numpy

COPY server.py .

# Download model on first run (cached in volume)
ENV KOKORO_MODEL_DIR=/app/models

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
