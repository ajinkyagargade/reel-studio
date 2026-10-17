"""AI explainer in two steps.

1. explain(text)      -> a full written explanation of whatever the user typed (Claude).
2. start_reel(id)     -> on request, condense that explanation into a 6-scene script, then
                         animated slides -> voice-over -> captions -> 9:16 video.
"""
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageDraw, ImageFont

from . import captions, config, jobs, llm, media, options, render, reels, store, tts

W, H = 1080, 1920
MAX_INPUT_CHARS = 6000

EXPLAIN_SYSTEM = """You are an expert teacher. The user gives you some text: a topic, a question, a concept, or a passage they
want to understand. Give a complete, accurate, easy-to-follow explanation of it.
Reply with ONE JSON object only:
{"title":"short title",
 "language":"en|hi|hinglish|...",
 "tldr":"1-2 sentence gist",
 "sections":[ {"heading":"short heading",
               "body":"clear explanation, 2-5 sentences, plain text, paragraphs separated by \\n\\n",
               "code":"optional code or formula example, max 12 lines, else empty string"} ],
 "takeaways":["3-6 short takeaways"]}
Use 4-7 sections that build on each other: what it is, why it matters, how it works, a concrete example, common mistakes
or edge cases, and when to use it. If the user pasted a passage, explain what it says and what it means rather than only
repeating it. Be technically accurate and never invent facts. Write in the user's language (Hinglish stays in Latin script)."""

SYSTEM = """You turn a written explanation into the script of a 45-second vertical explainer video.
Reply with ONE JSON object only:
{"title":"", "language":"en|hi",
 "scenes":[ {"heading":"max 6 words", "bullets":["max 3 short bullets, max 8 words each"],
             "code":"optional code snippet, max 9 lines, max 30 chars per line, else empty string",
             "narration":"what the voice says, 14-22 words, conversational"} ]}
Use exactly 6 scenes: 1 hook (a surprising question), 2-5 explain the most important ideas of the given explanation
(use its examples and code when it helps), 6 takeaway.
Total narration 105-130 words. Stay faithful to the explanation and never add facts that are not in it.
Write narration in the same language as the explanation (Hinglish stays in Latin script)."""

KW = {"const", "let", "var", "function", "return", "if", "else", "for", "while", "import", "from", "class", "def", "async",
      "await", "new", "true", "false", "null", "None", "True", "False", "in", "of", "export", "default", "try", "catch", "print"}


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(config.FONTS_DIR / name), size)


def _wrap(draw, text, font, max_w) -> List[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _code_segments(line: str):
    pos = 0
    for m in re.finditer(r"(//.*|#.*)|(\"[^\"]*\"|'[^']*')|(\b\d+\b)|([A-Za-z_]\w*)", line):
        if m.start() > pos:
            yield line[pos:m.start()], "#E6EDF3"
        tok = m.group(0)
        color = "#7D8590" if m.group(1) else "#A5D6FF" if m.group(2) else "#FFA657" if m.group(3) else \
            ("#FF7B72" if tok in KW else "#E6EDF3")
        yield tok, color
        pos = m.end()
    if pos < len(line):
        yield line[pos:], "#E6EDF3"


def render_slide(scene: Dict, idx: int, total: int, out: Path) -> None:
    img = Image.new("RGB", (W, H), "#0B1020")
    d = ImageDraw.Draw(img)
    for y in range(H):  # vertical gradient
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(11 + 22 * t), int(16 + 10 * t), int(32 + 48 * t)))
    d.rounded_rectangle([70, 150, 70 + 150, 160], radius=5, fill="#818CF8")
    d.text((70, 110), f"{idx + 1:02d} / {total:02d}", font=_font("Inter-Bold.otf", 34), fill="#A5B4FC")
    head_font = _font("Poppins-Bold.ttf", 82)
    y = 200
    for ln in _wrap(d, scene["heading"], head_font, W - 140)[:3]:
        d.text((70, y), ln, font=head_font, fill="#FFFFFF")
        y += 105
    y += 40
    code = (scene.get("code") or "").strip("\n")
    if code:
        lines = code.split("\n")[:9]
        mono = _font("DejaVuSansMono.ttf", 40)
        box_h = 115 + 62 * len(lines)
        d.rounded_rectangle([60, y, W - 60, y + box_h], radius=28, fill="#0D1117", outline="#30363D", width=3)
        for i, c in enumerate(("#FF5F56", "#FFBD2E", "#27C93F")):
            d.ellipse([95 + i * 42, y + 26, 115 + i * 42, y + 46], fill=c)
        cy = y + 80
        for ln in lines:
            x = 100
            for seg, col in _code_segments(ln[:32]):
                d.text((x, cy), seg, font=mono, fill=col)
                x += d.textlength(seg, font=mono)
            cy += 62
        y += box_h + 40
    bf = _font("Inter-Bold.otf", 52)
    for b in scene.get("bullets", [])[:3]:
        d.ellipse([78, y + 22, 98, y + 42], fill="#818CF8")
        for ln in _wrap(d, b, bf, W - 220)[:2]:
            d.text((125, y), ln, font=bf, fill="#E2E8F0")
            y += 70
        y += 24
    img.save(out)


# ---------------------------------------------------------------- step 1: the explanation
def _clean_explanation(data: Any, fallback_title: str) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise RuntimeError("The model did not return a usable explanation. Try rephrasing your text.")
    sections = []
    for s in data.get("sections") or []:
        if not isinstance(s, dict):
            continue
        body = str(s.get("body") or "").strip()
        if not body:
            continue
        sections.append({
            "heading": str(s.get("heading") or "").strip()[:120],
            "body": body,
            "code": str(s.get("code") or "").strip("\n"),
        })
    if not sections:
        raise RuntimeError("The model did not return a usable explanation. Try rephrasing your text.")
    return {
        "title": str(data.get("title") or fallback_title).strip()[:120],
        "language": str(data.get("language") or "en"),
        "tldr": str(data.get("tldr") or "").strip(),
        "sections": sections,
        "takeaways": [str(t).strip() for t in (data.get("takeaways") or []) if str(t).strip()][:8],
    }


def explain(text: str) -> Dict[str, Any]:
    """Write the full explanation for the user's text and store it. Raises RuntimeError with a readable message."""
    if not llm.available():
        raise RuntimeError("The AI explainer needs an Anthropic API key. Set ANTHROPIC_API_KEY in backend/.env and restart.")
    text = text.strip()[:MAX_INPUT_CHARS]
    data = llm.complete_json(EXPLAIN_SYSTEM, f"Text to explain:\n\n{text}", max_tokens=4000)
    explanation = _clean_explanation(data, fallback_title=text[:60])
    doc = {
        "id": reels.new_id(), "topic": text, "status": "ready", "createdAt": jobs.now_iso(),
        "explanation": explanation, "reel": None,
    }
    return store.put("explainers", doc["id"], doc)


# ---------------------------------------------------------------- step 2: the reel (only when asked)
def _explanation_as_text(e: Dict[str, Any]) -> str:
    parts = [f"Title: {e['title']}", f"Summary: {e.get('tldr', '')}"]
    for s in e["sections"]:
        parts.append(f"## {s['heading']}\n{s['body']}" + (f"\nExample:\n{s['code']}" if s.get("code") else ""))
    if e.get("takeaways"):
        parts.append("Takeaways: " + "; ".join(e["takeaways"]))
    return "\n\n".join(parts)


def _reel_update(job_id: str, **fields: Any) -> None:
    doc = store.get("explainers", job_id)
    if doc is not None:
        store.update("explainers", job_id, reel={**(doc.get("reel") or {}), **fields})


def run_reel(job_id: str) -> None:
    try:
        _run_reel(job_id)
    except Exception as e:  # noqa: BLE001 - surface the reason in the UI instead of a silent hang
        jobs.log.error("explainer reel failed: %s", e)
        _reel_update(job_id, status="failed", progress=0, message=str(e)[:400])


def _run_reel(job_id: str) -> None:
    job = store.get("explainers", job_id)
    explanation = job["explanation"]
    _reel_update(job_id, status="processing", progress=5, message="Writing the reel script")
    script = llm.complete_json(SYSTEM, _explanation_as_text(explanation), max_tokens=3000)
    scenes_raw = [s for s in script.get("scenes", []) if s.get("narration")][:8]
    if not scenes_raw:
        raise RuntimeError("The model did not return a usable reel script. Please try again.")

    topic = explanation["title"]
    work = config.WORK_DIR / f"explainer_{job_id}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    settings = options.normalize_settings({
        "voice": "ai", "aspect": "9:16", "quality": "720p", "framing": "crop", "motion": "zoom_in",
        "transition": "slideleft", "showTitles": False, "targetSeconds": 45, "originalVolume": 0,
        "captions": {"style": "pop", "position": "bottom"},
    })
    lang = script.get("language", "en")
    voice = tts.resolve_voice("auto", lang)
    scenes: List[Dict] = []
    lead, tail = 0.2, 0.6
    for i, sc in enumerate(scenes_raw):
        _reel_update(job_id, progress=int(10 + 30 * i / len(scenes_raw)), message=f"Voice-over {i + 1}/{len(scenes_raw)}")
        png = work / f"slide_{i}.png"
        render_slide(sc, i, len(scenes_raw), png)
        audio = tts.synthesize(sc["narration"], voice, 0, work / "tts")
        dur = media.duration_of(audio)
        scenes.append({
            "kind": "image", "src": png, "duration": lead + dur + tail, "narration": audio, "lead": lead,
            "words": captions.spread_words(sc["narration"], lead, lead + dur), "has_audio": False,
        })
    out = config.OUTPUT_DIR / f"explainer_{job_id}.mp4"
    _reel_update(job_id, progress=45, message="Rendering video")
    render.render(scenes, settings, out, work / "r", lambda f, m: _reel_update(job_id, progress=int(45 + 54 * f), message=m))
    shutil.rmtree(work, ignore_errors=True)
    _reel_update(job_id, status="ready", progress=100, message="Done",
                 outputUrl=f"/api/explainer/{job_id}/video?v={int(out.stat().st_mtime)}",
                 downloadUrl=f"/api/explainer/{job_id}/video?download=1")


def start_reel(job_id: str) -> Dict:
    """Queue the reel for an existing explanation. Raises LookupError / RuntimeError for the API to turn into HTTP errors."""
    doc = store.get("explainers", job_id)
    if not doc or not doc.get("explanation"):
        raise LookupError("Explainer not found")
    if (doc.get("reel") or {}).get("status") == "processing":
        raise RuntimeError("The reel is already being made")
    if not llm.available():
        raise RuntimeError("Making a reel needs ANTHROPIC_API_KEY set in backend/.env")
    (config.OUTPUT_DIR / f"explainer_{job_id}.mp4").unlink(missing_ok=True)  # a re-run must not serve the old video
    doc = store.update("explainers", job_id, reel={"status": "processing", "progress": 0, "message": "Queued",
                                                    "outputUrl": None, "downloadUrl": None})
    jobs.submit(run_reel, job_id)
    return doc

