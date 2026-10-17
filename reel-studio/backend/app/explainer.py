"""Topic explainer: topic -> script (Claude) -> animated code slides -> voice-over -> captions -> 9:16 video."""
import re
import shutil
from pathlib import Path
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFont

from . import captions, config, jobs, llm, media, options, render, reels, store, tts

W, H = 1080, 1920
SYSTEM = """You write scripts for 45-second vertical tech explainer videos for developers.
Reply with ONE JSON object only:
{"title":"", "language":"en|hi",
 "scenes":[ {"heading":"max 6 words", "bullets":["max 3 short bullets, max 8 words each"],
             "code":"optional code snippet, max 9 lines, max 30 chars per line, else empty string",
             "narration":"what the voice says, 14-22 words, conversational"} ]}
Use exactly 6 scenes: 1 hook (a surprising question), 2-5 explain with examples (use code when it helps), 6 takeaway.
Total narration 105-130 words. Be technically accurate. Write narration in the user's language (Hinglish stays in Latin script)."""

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


def run(job_id: str) -> None:
    job = store.get("explainers", job_id)
    topic = job["topic"]
    if not llm.available():
        raise RuntimeError("The topic explainer needs an Anthropic API key. Set ANTHROPIC_API_KEY in backend/.env and restart.")
    store.update("explainers", job_id, status="processing", progress=5, message="Writing the script")
    script = llm.complete_json(SYSTEM, f"Topic: {topic}", max_tokens=3000)
    scenes_raw = [s for s in script.get("scenes", []) if s.get("narration")][:8]
    if not scenes_raw:
        raise RuntimeError("The model did not return a usable script. Try rephrasing the topic.")

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
        store.update("explainers", job_id, progress=int(10 + 30 * i / len(scenes_raw)), message=f"Voice-over {i + 1}/{len(scenes_raw)}")
        png = work / f"slide_{i}.png"
        render_slide(sc, i, len(scenes_raw), png)
        audio = tts.synthesize(sc["narration"], voice, 0, work / "tts")
        dur = media.duration_of(audio)
        scenes.append({
            "kind": "image", "src": png, "duration": lead + dur + tail, "narration": audio, "lead": lead,
            "words": captions.spread_words(sc["narration"], lead, lead + dur), "has_audio": False,
        })
    out = config.OUTPUT_DIR / f"explainer_{job_id}.mp4"
    store.update("explainers", job_id, progress=45, message="Rendering video")
    render.render(scenes, settings, out, work / "r", lambda f, m: store.update("explainers", job_id, progress=int(45 + 54 * f), message=m))
    shutil.rmtree(work, ignore_errors=True)
    store.update("explainers", job_id, status="ready", progress=100, message="Done", title=script.get("title", topic),
                 outputUrl=f"/api/explainer/{job_id}/video?v={int(out.stat().st_mtime)}",
                 downloadUrl=f"/api/explainer/{job_id}/video?download=1")


def start(topic: str) -> Dict:
    job_id = reels.new_id()
    doc = {"id": job_id, "topic": topic, "status": "processing", "progress": 0, "message": "Queued", "createdAt": jobs.now_iso()}
    store.put("explainers", job_id, doc)
    jobs.submit(run, job_id, kind="explainers", doc_id=job_id)
    return doc

