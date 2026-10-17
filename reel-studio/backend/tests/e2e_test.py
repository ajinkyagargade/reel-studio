"""End-to-end test of the real API + real ffmpeg rendering.

Whisper and edge-tts need network/model downloads, so they are replaced by stand-ins:
  - transcription returns a scripted lecture with word timestamps
  - TTS returns a generated tone whose length follows the text length
Everything else (upload, probe, analysis, planning, caption/transition rendering, API) is the real code.

Run:  python tests/e2e_test.py /path/to/sample.mp4
"""
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="reelstudio_test_")
os.environ.pop("ANTHROPIC_API_KEY", None)

import requests  # noqa: E402
import uvicorn  # noqa: E402

from app import config, transcribe, tts  # noqa: E402

LECTURE = """Today we are learning React hooks and why they changed how we write components.
Before hooks, you needed a class component whenever you wanted to keep state.
The useState hook lets a function component remember a value between renders.
You call useState with an initial value and it returns the value and a setter function.
Never mutate state directly, always call the setter so React knows to re-render the component.
Now let us talk about side effects, which is where the useEffect hook comes in.
useEffect runs after the component renders and is perfect for fetching data from an API.
The dependency array decides when the effect runs again, an empty array means run only once.
If you forget the dependency array your effect runs after every single render and can cause an infinite loop.
Cleanup functions returned from useEffect are used to cancel timers and unsubscribe from events.
Next, the useRef hook gives you a mutable box that survives renders without causing a re-render.
People often use useRef to focus an input field or to store the previous value of a prop.
For expensive calculations use useMemo so React only recomputes when the inputs change.
Similarly useCallback keeps the same function identity which helps child components avoid needless renders.
Custom hooks let you extract reusable logic, for example a useFetch hook that wraps loading and error state.
A custom hook is just a function whose name starts with use and that calls other hooks inside it.
The rules of hooks say only call hooks at the top level and only from React functions.
Breaking these rules leads to bugs that are very hard to track down, so install the ESLint hooks plugin.
To recap, useState stores data, useEffect handles side effects, and useRef holds mutable values.
Practice by building a small todo list and then refactor the logic into your own custom hook.""".split("\n")


def fake_transcribe(audio_path, duration, language=None, on_progress=None):
    words, segments, t = [], [], 3.0
    step = (duration - 6) / len(LECTURE)
    for line in LECTURE:
        toks = line.split()
        per = min(0.45, step * 0.85 / len(toks))
        s0 = t
        for tok in toks:
            words.append({"word": tok, "start": round(t, 2), "end": round(t + per * 0.9, 2)})
            t += per
        segments.append({"start": round(s0, 2), "end": round(t, 2), "text": line})
        t = s0 + step
        if on_progress:
            on_progress(t / duration)
    return {"language": "en", "words": words, "segments": segments, "fullText": " ".join(LECTURE)}


def fake_tts(text, voice, rate, cache_dir):
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"fake_{abs(hash((text, voice, rate)))}.wav"
    secs = max(1.5, len(text.split()) * 0.38)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=520:duration={secs}", str(out)], check=True)
    return out


transcribe.transcribe = fake_transcribe
transcribe.available = lambda: True
tts.synthesize = fake_tts

from app.main import app  # noqa: E402

BASE = "http://127.0.0.1:8765/api"


def wait(url, done, label, timeout=600):
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        d = requests.get(BASE + url).json()
        msg = (d.get("status"), d.get("progress"), d.get("message"))
        if msg != last:
            print(f"  [{label}] {msg}")
            last = msg
        if d["status"] in done:
            return d
        time.sleep(1)
    raise TimeoutError(label)


def main(sample: str):
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        try:
            requests.get(BASE + "/health", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    print("health:", requests.get(BASE + "/health").json())
    opts = requests.get(BASE + "/options").json()
    print("options:", {k: len(v) for k, v in opts.items() if isinstance(v, list)})

    with open(sample, "rb") as f:
        r = requests.post(BASE + "/upload", files={"file": ("react_hooks_class.mp4", f, "video/mp4")}, data={"language": "en"})
    print("upload:", r.status_code, r.json())
    vid = r.json()["id"]
    v = wait(f"/videos/{vid}", {"ready", "failed"}, "video")
    assert v["status"] == "ready", v
    a = requests.get(f"{BASE}/videos/{vid}/analysis").json()
    print("analysis source:", a["source"], "| title:", a["title"], "| keyPoints:", len(a["keyPoints"]), "| chapters:", len(a["chapters"]))
    print("tldr:", a["tldr"])
    print("stats:", a["stats"])
    assert len(a["keyPoints"]) >= 4 and a["summary"]

    reels = requests.get(f"{BASE}/videos/{vid}/reels").json()
    assert len(reels) == 1
    rid = reels[0]["id"]
    print("default reel points:", [(p["title"], p["start"], p["end"]) for p in reels[0]["points"]])
    reel = wait(f"/reels/{rid}", {"ready", "failed"}, "reel")
    assert reel["status"] == "ready", reel
    print("reel:", reel["duration"], "s", reel["width"], "x", reel["height"], reel.get("notes"))
    assert 30 <= reel["duration"] <= 75, reel["duration"]

    # video file is range-streamable
    rr = requests.get(BASE.replace("/api", "") + reel["outputUrl"], headers={"Range": "bytes=0-99"})
    print("range:", rr.status_code, rr.headers.get("content-range"))
    assert rr.status_code == 206

    # edit: other transition + caption style + original voice + 1:1 + filter + drop a point, then re-render
    pts = reel["points"]
    pts[0]["transition"] = "circleopen"
    pts[1]["enabled"] = False
    body = {"points": pts, "settings": {"voice": "original", "aspect": "1:1", "quality": "draft", "filter": "cinematic",
                                         "transition": "wipeleft", "motion": "zoom_in", "framing": "crop", "zoom": 1.4,
                                         "captions": {"style": "karaoke", "position": "middle", "size": 1.2}}}
    r = requests.post(f"{BASE}/reels/{rid}/render", json=body)
    print("re-render:", r.status_code, r.json()["status"])
    reel2 = wait(f"/reels/{rid}", {"ready", "failed"}, "reel2")
    assert reel2["status"] == "ready", reel2
    print("reel2:", reel2["duration"], "s", reel2["width"], "x", reel2["height"], reel2["settings"]["captions"]["style"])
    assert reel2["width"] == reel2["height"]
    out = Path(config.OUTPUT_DIR / f"reel_{rid}.mp4")
    print("output file:", out, out.stat().st_size // 1024, "KB")

    # ---- custom font + logo + live-caption options
    from PIL import Image
    import io
    img = Image.new("RGBA", (300, 120), (255, 80, 0, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    logo = requests.post(BASE + "/logos", files={"file": ("my logo.png", buf.getvalue(), "image/png")}).json()
    print("logo:", logo)
    font_bytes = (config.FONTS_DIR / "LiberationSerif-Bold.ttf").read_bytes()
    font = requests.post(BASE + "/fonts", files={"file": ("MyBrand.ttf", font_bytes, "font/ttf")}).json()
    print("font:", font["family"], font["builtin"])
    assert any(f["family"] == font["family"] for f in requests.get(BASE + "/fonts").json())
    assert requests.get(BASE.replace("/api", "") + font["url"]).status_code == 200
    assert requests.post(BASE + "/logos", files={"file": ("x.png", b"nope", "image/png")}).status_code == 400
    cap = {"style": "pop", "font": "Caladea", "color": "#00FF88", "highlightColor": "#FF3366", "outlineColor": "#220044",
           "uppercase": False, "position": "top", "size": 1.3}
    lg = {"id": logo["id"], "position": "bottom-right", "size": 0.25, "opacity": 0.8}
    r = requests.post(f"{BASE}/reels/{rid}/render", json={"settings": {"quality": "draft", "aspect": "9:16", "voice": "ai",
                      "captions": cap, "logo": lg}, "points": [dict(p, enabled=True) for p in pts]})
    reel3 = wait(f"/reels/{rid}", {"ready", "failed"}, "reel3")
    assert reel3["status"] == "ready", reel3
    assert reel3["settings"]["logo"]["id"] == logo["id"] and reel3["settings"]["captions"]["font"] == "Caladea"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "4", "-i", str(out), "-frames:v", "1", "/tmp/reel3.png"], check=True)

    srt = requests.get(f"{BASE}/videos/{vid}/captions/srt").text
    vtt = requests.get(f"{BASE}/videos/{vid}/captions/vtt").text
    assert srt.startswith("1\n00:00:") and vtt.startswith("WEBVTT"), srt[:80]
    print("srt sample:", srt.split("\n\n")[0].replace("\n", " | "))

    r = requests.post(f"{BASE}/videos/{vid}/captioned", json={"settings": {"captions": cap, "logo": lg, "quality": "draft"}})
    print("burn:", r.status_code)
    cdoc = wait(f"/videos/{vid}/captioned", {"ready", "failed"}, "burn")
    assert cdoc["status"] == "ready", cdoc
    cout = Path(config.OUTPUT_DIR / f"captioned_{vid}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "25", "-i", str(cout), "-frames:v", "1", "/tmp/burn.png"], check=True)
    print("captioned full video:", cout.stat().st_size // 1024, "KB")

    # bad input handling
    assert requests.post(BASE + "/upload", files={"file": ("x.txt", b"hello", "text/plain")}).status_code == 400
    assert requests.get(BASE + "/reels/nope").status_code == 404
    assert requests.post(BASE + "/explainer", json={"topic": "JSON"}).status_code == 503  # no API key here
    print("ALL OK. Output kept at", out)


if __name__ == "__main__":
    main(sys.argv[1])
