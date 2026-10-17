# Reel Studio backend image (ffmpeg + Whisper + edge-tts). Build context: reel-studio/backend
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/app/data

# ffmpeg/ffprobe render the videos; libgomp1 is needed by the Whisper runtime (ctranslate2/onnxruntime)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN mkdir -p /app/data

# Hosts like Render inject $PORT; default to 8000 for local `docker run -p 8000:8000`.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
