"""Reel projects: plan points from the analysis, edit them, and render."""
import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import analyze, captions, config, jobs, media, options, render, store, tts


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def transcript_path(video_id: str) -> Path:
    return config.WORK_DIR / video_id / "transcript.json"


def load_transcript(video_id: str) -> Dict:
    p = transcript_path(video_id)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"words": [], "segments": [], "fullText": ""}


# ------------------------------------------------------------------ planning
def plan_points(analysis: Dict, duration: float, target: float, num_points: Optional[int] = None) -> List[Dict]:
    cands = [dict(c) for c in analysis.get("keyPoints", [])]
    if not cands:
        raise RuntimeError("No key points were found in this video, so a reel cannot be planned.")
    n = int(num_points or max(3, min(8, round(target / 10))))
    n = max(1, min(n, len(cands)))
    chosen: List[Dict] = []
    for c in sorted(cands, key=lambda x: x["importance"], reverse=True):
        if all(c["start"] >= o["end"] - 0.5 or c["end"] <= o["start"] + 0.5 for o in chosen):
            chosen.append(c)
        if len(chosen) == n:
            break
    chosen.sort(key=lambda x: x["start"])
    word_budget = max(8, int(target / n * 2.4))
    points = []
    for c in chosen:
        text = (c.get("narration") or c.get("summary") or "").strip()
        points.append({
            "id": new_id(), "title": c["title"], "text": analyze._clip_words(text, word_budget),
            "start": round(c["start"], 2), "end": round(min(c["end"], duration), 2),
            "enabled": True, "transition": None, "customText": False,
        })
    return points


def create_reel(video_id: str, target: float = 60, num_points: Optional[int] = None,
                settings: Optional[Dict] = None) -> Dict:
    video = store.get("videos", video_id)
    analysis = store.get("analysis", video_id)
    if not video or not analysis:
        raise LookupError("Video has not been analysed yet.")
    s = options.normalize_settings({**(settings or {}), "targetSeconds": target})
    reel = {
        "id": new_id(), "videoId": video_id, "status": "draft", "progress": 0, "message": "Ready to render",
        "settings": s, "points": plan_points(analysis, video["duration"], s["targetSeconds"], num_points),
        "createdAt": jobs.now_iso(), "outputUrl": None, "downloadUrl": None, "duration": None,
        "stale": False, "notes": [],
    }
    return store.put("reels", reel["id"], reel)


def clean_points(raw: List[Dict], duration: float) -> List[Dict]:
    out = []
    for p in raw:
        try:
            s = min(max(float(p["start"]), 0), max(duration - 1, 0))
            e = min(max(float(p["end"]), s + 1), duration)
        except (KeyError, TypeError, ValueError):
            continue
        tid = p.get("transition")
        item = {
            "id": str(p.get("id") or new_id()), "title": str(p.get("title") or "Point")[:80],
            "text": str(p.get("text") or "").strip()[:600], "start": round(s, 2), "end": round(e, 2),
            "enabled": bool(p.get("enabled", True)),
            "transition": tid if tid in [t["id"] for t in options.TRANSITIONS] else None,
            "customText": bool(p.get("customText", False)),
        }
        for key, lo, hi in (("focusX", 0, 1), ("focusY", 0, 1), ("zoom", 1, 3)):
            if p.get(key) is not None:
                try:
                    item[key] = min(hi, max(lo, float(p[key])))
                except (TypeError, ValueError):
                    pass
        out.append(item)
    return out


def update_reel(reel_id: str, body: Dict) -> Dict:
    reel = store.get("reels", reel_id)
    if not reel:
        raise LookupError("Reel not found")
    video = store.get("videos", reel["videoId"])
    fields: Dict[str, Any] = {"stale": True}
    if "settings" in body:
        fields["settings"] = options.normalize_settings(body["settings"], base=reel["settings"])
    if "points" in body:
        fields["points"] = clean_points(body["points"], video["duration"])
        if not fields["points"]:
            raise ValueError("A reel needs at least one point.")
    if reel["status"] == "ready":
        fields["message"] = "You have unrendered changes"
    return store.update("reels", reel_id, **fields)


# ------------------------------------------------------------------ rendering
def _set(reel_id: str, **fields):
    store.update("reels", reel_id, **fields)


def build_scenes(reel: Dict, video: Dict, analysis: Dict, transcript: Dict, notes: List[str]) -> List[Dict]:
    s = reel["settings"]
    pts = [p for p in reel["points"] if p.get("enabled", True)]
    if not pts:
        raise RuntimeError("All points are disabled - enable at least one.")
    n, target, speed = len(pts), s["targetSeconds"], s["speed"]
    vdur = video["duration"]
    has_audio = video["meta"].get("hasAudio", True)
    mode = s["voice"]
    td = s["transitionDuration"]
    n_words = transcript.get("words", [])

    narr: List[Optional[Path]] = [None] * n
    if mode == "ai":
        voice = tts.resolve_voice(s["ttsVoice"], analysis.get("language", "en"))
        cache = config.WORK_DIR / reel["videoId"] / "tts"
        try:
            narr = [tts.synthesize(p["text"] or p["title"], voice, s["ttsRate"], cache) for p in pts]
        except tts.TTSUnavailable as e:
            notes.append(f"AI voice unavailable ({str(e)[:140]}). Used the original audio instead.")
            mode = "original"

    scenes: List[Dict] = []
    if mode == "ai":
        lead, tail = 0.2, max(0.35, td + 0.1)
        durs = [media.duration_of(p) for p in narr]  # type: ignore[arg-type]
        nt = 1.0
        if s["fitToTarget"]:
            room = target - n * (lead + tail) + (n - 1) * td
            nt = min(1.35, max(1.0, sum(durs) / room)) if room > 1 else 1.35
        for p, a, d in zip(pts, narr, durs):
            speech = d / nt
            D = lead + speech + tail
            scenes.append({
                "kind": "video", "src": video["path"], "start": p["start"], "duration": D, "speed": speed,
                "original_volume": s["originalVolume"], "narration": a, "narration_tempo": nt, "lead": lead,
                "words": captions.spread_words(p["text"] or p["title"], lead, lead + speech), "has_audio": has_audio,
            })
    else:
        cap_src = target / n * speed if s["fitToTarget"] else 1e9
        for p in pts:
            length = min(p["end"] - p["start"], cap_src, vdur - p["start"])
            D = length / speed
            if p.get("customText") and p["text"]:
                words = captions.spread_words(p["text"], 0.1, D - 0.1)
            else:
                words = [{"w": w["word"], "s": max(0.0, (w["start"] - p["start"]) / speed), "e": (w["end"] - p["start"]) / speed}
                         for w in n_words if p["start"] <= w["start"] < p["start"] + length]
            scenes.append({
                "kind": "video", "src": video["path"], "start": p["start"], "duration": D, "speed": speed,
                "original_volume": 1.0 if mode == "original" else 0.0, "narration": None, "words": words,
                "has_audio": has_audio,
            })
    for i, (sc, p) in enumerate(zip(scenes, pts)):
        sc["title"] = f"{i + 1}. {p['title']}"
        sc["transition"] = p.get("transition")
        for key in ("focusX", "focusY", "zoom"):
            if key in p:
                sc[key] = p[key]
    return scenes


def render_job(reel_id: str) -> None:
    reel = store.get("reels", reel_id)
    video = store.get("videos", reel["videoId"])
    analysis = store.get("analysis", reel["videoId"]) or {}
    notes: List[str] = []
    _set(reel_id, status="rendering", progress=1, message="Preparing voice-over")
    scenes = build_scenes(reel, video, analysis, load_transcript(reel["videoId"]), notes)
    work = config.WORK_DIR / reel["videoId"] / f"reel_{reel_id}"
    shutil.rmtree(work, ignore_errors=True)
    out = config.OUTPUT_DIR / f"reel_{reel_id}.mp4"

    def progress(frac: float, msg: str):
        _set(reel_id, progress=int(5 + 94 * frac), message=msg)

    info = render.render(scenes, reel["settings"], out, work, progress)
    shutil.rmtree(work, ignore_errors=True)
    stamp = int(out.stat().st_mtime)
    _set(reel_id, status="ready", progress=100, message="Reel is ready", duration=info["duration"], notes=notes,
         outputUrl=f"/api/reels/{reel_id}/video?v={stamp}", downloadUrl=f"/api/reels/{reel_id}/video?download=1",
         stale=False, size=out.stat().st_size, width=info["width"], height=info["height"])


def start_render(reel_id: str) -> Dict:
    reel = store.get("reels", reel_id)
    if not reel:
        raise LookupError("Reel not found")
    if reel["status"] == "rendering":
        raise RuntimeError("This reel is already rendering.")
    _set(reel_id, status="rendering", progress=0, message="Queued")
    jobs.submit(render_job, reel_id, kind="reels", doc_id=reel_id)
    return store.get("reels", reel_id)


def delete_reel(reel_id: str) -> None:
    (config.OUTPUT_DIR / f"reel_{reel_id}.mp4").unlink(missing_ok=True)
    store.delete("reels", reel_id)
