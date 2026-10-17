# Reel Studio

Turn a long video into (1) a full explanation, (2) a ~60-second point-wise reel with **captions + voice**, and (3) an editable reel with transitions, **live captions**, custom **fonts/colours** and a **logo**.

```
reel-studio/
├── backend/    Python API (Starlette + ffmpeg + Whisper + edge-tts, optional Claude)
└── frontend/   React app (your original UI, now wired to the backend)
```

## What it does

| Feature | How |
|---|---|
| Long video → speech transcript | faster-whisper (local, free), word-level timestamps. English, Hindi, Hinglish |
| Explain the whole video | Summary, TL;DR, chapters, key moments, takeaways, glossary, FAQ, quotes, stats, file info. Written by Claude if `ANTHROPIC_API_KEY` is set, otherwise a free local analyser |
| 60-second point-wise reel | Picks the key points, AI voice-over (edge-tts, 10 voices), animated captions, point titles, progress bar |
| Edit options | Reorder / trim / rewrite / disable points · 20 transitions (per point or global) · 9 colour looks · 4 aspect ratios · framing (blur-fit / crop+zoom / bars) · zoom motion · speed · voice mode (AI / original / none) · draft/720p/1080p |
| **Live captions** | Captions appear word-by-word over the player in real time with the exact final look. Download `.srt` / `.vtt`, or burn them into the *entire* original video |
| Caption font & colour | 9 built-in fonts, **upload your own .ttf/.otf**, text / highlight / outline colours, UPPERCASE, background box, 6 presets, position, size |
| Logo | Upload PNG/JPG/WebP, choose corner or centre, size, opacity; applied to reels and the captioned full video |
| AI explainer | Type or paste any text → full written explanation → optional **Make a reel** button (script → code slides → voice → 45s vertical video). Needs `ANTHROPIC_API_KEY` |

## Setup

Requirements: **Python 3.10+**, **Node 18+**, **ffmpeg 5+** on your PATH (`ffmpeg -version`).

```bash
# 1. backend
cd backend
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # optional: add ANTHROPIC_API_KEY
uvicorn app.main:app --port 8000

# 2. frontend (new terminal)
cd frontend
npm install
npm start                                            # http://localhost:3000
```

First upload downloads the Whisper model once (`small` ≈ 460 MB). Use `WHISPER_MODEL=base` for a faster, lighter start, `medium` for better Hinglish.

Single-server mode: `cd frontend && npm run build`, then just run the backend; it serves the built app at http://localhost:8000.

## Using it

1. **Upload** a video (pick the spoken language). Processing shows live progress.
2. Open the project. **Video explained** tab = full explanation. Click any timestamp to jump the player.
3. **Reel studio** tab: a 60 s reel is planned and rendered automatically. Edit anything, then *Apply changes & re-render*. Use **Draft** quality for quick tests.
4. **Live captions** tab: play the source video and tune font/colour/position live; save the style to your reel, download SRT/VTT, or burn into the full video.

## Notes and limits

* AI voice uses Microsoft's free neural voices via `edge-tts`, so it needs internet. Without it, the reel falls back to the original audio (a notice is shown).
* Live captions are timed from the Whisper transcript (not live microphone input).
* Without an Anthropic key, summaries are extractive (selected real sentences), good but less polished; glossary/FAQ stay empty.
* Hindi captions need a Devanagari-capable font (choose **FreeSans** or upload e.g. Noto Sans Devanagari).
* Data (uploads, outputs, SQLite) lives in `backend/data/`.

## Tests

`python backend/tests/e2e_test.py sample.mp4` runs the whole API against real ffmpeg, with Whisper/TTS replaced by stand-ins.
