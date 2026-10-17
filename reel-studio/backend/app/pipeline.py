"""Video processing pipeline: probe -> thumbnail -> transcribe -> analyse -> default reel."""
import json
import re
from pathlib import Path

from . import analyze, config, jobs, media, reels, store, transcribe


def _title_from_name(name: str) -> str:
    stem = re.sub(r"[_\-.]+", " ", Path(name).stem).strip()
    return stem.title() if stem else "Untitled video"


def _set(video_id: str, progress: int, message: str, **extra):
    store.update("videos", video_id, status="processing", progress=progress, message=message, **extra)


def process_video(video_id: str) -> None:
    video = store.get("videos", video_id)
    src = Path(video["path"])
    work = config.WORK_DIR / video_id
    work.mkdir(parents=True, exist_ok=True)

    _set(video_id, 3, "Reading video")
    meta = media.probe(src)
    if not meta["hasVideo"]:
        raise RuntimeError("This file has no video stream.")
    if not meta["hasAudio"]:
        raise RuntimeError("This video has no audio track, so there is nothing to transcribe.")
    thumb = config.WORK_DIR / video_id / "thumb.jpg"
    media.make_thumbnail(src, thumb, at=min(5.0, meta["duration"] / 4))
    _set(video_id, 6, "Extracting audio", duration=meta["duration"], meta=meta,
         thumbnailUrl=f"/api/videos/{video_id}/thumbnail")

    audio = work / "audio.flac"
    media.extract_audio(src, audio)

    _set(video_id, 10, "Transcribing speech (this is the slow part)")
    tr = transcribe.transcribe(
        audio, meta["duration"], video.get("language"),
        on_progress=lambda f: _set(video_id, int(10 + 60 * f), f"Transcribing speech… {int(f * 100)}%"))
    reels.transcript_path(video_id).write_text(json.dumps(tr), encoding="utf-8")
    audio.unlink(missing_ok=True)
    if len(tr["words"]) < 5:
        raise RuntimeError("Almost no speech was detected in this video.")

    _set(video_id, 72, "Understanding the video (summary, chapters, key points)")
    analysis = analyze.analyze(tr, meta["duration"], _title_from_name(video["originalName"]))
    analysis["videoId"] = video_id
    store.put("analysis", video_id, analysis)

    _set(video_id, 92, "Planning your 60-second reel")
    reel = reels.create_reel(video_id, target=60)
    store.update("videos", video_id, status="ready", progress=100, message="Ready", defaultReelId=reel["id"])
    reels.start_render(reel["id"])  # first reel renders automatically in the background
