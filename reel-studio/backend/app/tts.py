"""Text-to-speech. Primary: edge-tts (free neural voices, needs internet).
Fallback: pyttsx3 (offline, robotic). Returns an audio file path."""
import asyncio
import hashlib
from pathlib import Path
from typing import Dict, List

from . import config

VOICES: List[Dict[str, str]] = [
    {"id": "auto", "label": "Auto (match video language)", "lang": "auto"},
    {"id": "en-US-AriaNeural", "label": "Aria · US English · female", "lang": "en"},
    {"id": "en-US-GuyNeural", "label": "Guy · US English · male", "lang": "en"},
    {"id": "en-US-AndrewNeural", "label": "Andrew · US English · male", "lang": "en"},
    {"id": "en-IN-NeerjaNeural", "label": "Neerja · Indian English · female", "lang": "en"},
    {"id": "en-IN-PrabhatNeural", "label": "Prabhat · Indian English · male", "lang": "en"},
    {"id": "en-GB-SoniaNeural", "label": "Sonia · British English · female", "lang": "en"},
    {"id": "en-GB-RyanNeural", "label": "Ryan · British English · male", "lang": "en"},
    {"id": "hi-IN-SwaraNeural", "label": "Swara · Hindi · female", "lang": "hi"},
    {"id": "hi-IN-MadhurNeural", "label": "Madhur · Hindi · male", "lang": "hi"},
]


class TTSUnavailable(RuntimeError):
    pass


def resolve_voice(voice: str, language: str) -> str:
    if voice and voice != "auto":
        return voice
    return "hi-IN-SwaraNeural" if (language or "").startswith("hi") else "en-US-AriaNeural"


def _edge(text: str, voice: str, rate: int, out: Path) -> None:
    import edge_tts

    async def go():
        await edge_tts.Communicate(text, voice, rate=f"{rate:+d}%").save(str(out))

    asyncio.run(go())


def _pyttsx3(text: str, out: Path) -> None:
    import pyttsx3
    engine = pyttsx3.init()
    engine.save_to_file(text, str(out))
    engine.runAndWait()


def synthesize(text: str, voice: str, rate: int, cache_dir: Path) -> Path:
    """rate: percent offset, e.g. -10 .. +30. Cached by content hash."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest()[:16]
    mp3, wav = cache_dir / f"tts_{key}.mp3", cache_dir / f"tts_{key}.wav"
    for cached in (mp3, wav):
        if cached.exists() and cached.stat().st_size > 1000:
            return cached
    errors = []
    for attempt in range(3):
        try:
            _edge(text, voice, rate, mp3)
            if mp3.exists() and mp3.stat().st_size > 1000:
                return mp3
        except Exception as e:  # network / missing package
            errors.append(f"edge-tts: {e}")
    try:
        _pyttsx3(text, wav)
        if wav.exists() and wav.stat().st_size > 1000:
            return wav
    except Exception as e:
        errors.append(f"pyttsx3: {e}")
    raise TTSUnavailable("; ".join(errors[-2:]) or "no TTS engine produced audio")
