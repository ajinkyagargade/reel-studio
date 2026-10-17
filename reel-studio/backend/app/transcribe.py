"""Speech-to-text with faster-whisper (local, free). Returns word-level timestamps."""
from pathlib import Path
from typing import Callable, Dict, Optional

from . import config

_model = None

HINGLISH_PROMPT = (
    "Yeh ek Hinglish lecture hai. Technical terms English mein likho: React, API, JSON, useEffect, database, server."
)


def available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(config.WHISPER_MODEL, device=config.WHISPER_DEVICE, compute_type=config.WHISPER_COMPUTE)
    return _model


def transcribe(audio_path: Path, duration: float, language: Optional[str] = None,
               on_progress: Optional[Callable[[float], None]] = None) -> Dict:
    """language: None/'auto' = detect, 'en', 'hi', or 'hinglish' (English script + Hinglish prompt)."""
    if not available():
        raise RuntimeError("faster-whisper is not installed. Run: pip install faster-whisper")
    prompt = None
    if language == "hinglish":
        language, prompt = "en", HINGLISH_PROMPT
    elif language in (None, "", "auto"):
        language = None

    model = _get_model()
    segments_iter, info = model.transcribe(
        str(audio_path), language=language, initial_prompt=prompt, word_timestamps=True,
        vad_filter=True, beam_size=5, condition_on_previous_text=False,
    )
    words, segments = [], []
    for seg in segments_iter:
        text = seg.text.strip()
        if text:
            segments.append({"start": round(seg.start, 2), "end": round(seg.end, 2), "text": text})
        for w in (seg.words or []):
            token = w.word.strip()
            if token:
                words.append({"word": token, "start": round(w.start, 2), "end": round(w.end, 2)})
        if on_progress and duration:
            on_progress(min(1.0, seg.end / duration))
    return {
        "language": info.language,
        "words": words,
        "segments": segments,
        "fullText": " ".join(s["text"] for s in segments),
    }
