"""Catalogue of everything the user can edit on a reel (served to the UI at /api/options)."""
import copy
from typing import Any, Dict

from . import assets, tts

# id -> ffmpeg xfade transition. "cut" is a hard cut.
TRANSITIONS = [
    {"id": "cut", "label": "Hard cut", "xfade": "fade", "group": "Basic"},
    {"id": "fade", "label": "Cross fade", "xfade": "fade", "group": "Basic"},
    {"id": "dissolve", "label": "Dissolve", "xfade": "dissolve", "group": "Basic"},
    {"id": "fadeblack", "label": "Dip to black", "xfade": "fadeblack", "group": "Basic"},
    {"id": "fadewhite", "label": "Dip to white", "xfade": "fadewhite", "group": "Basic"},
    {"id": "wipeleft", "label": "Wipe left", "xfade": "wipeleft", "group": "Wipe"},
    {"id": "wiperight", "label": "Wipe right", "xfade": "wiperight", "group": "Wipe"},
    {"id": "diagtl", "label": "Diagonal wipe", "xfade": "diagtl", "group": "Wipe"},
    {"id": "slideleft", "label": "Slide left", "xfade": "slideleft", "group": "Slide"},
    {"id": "slideright", "label": "Slide right", "xfade": "slideright", "group": "Slide"},
    {"id": "slideup", "label": "Slide up", "xfade": "slideup", "group": "Slide"},
    {"id": "slidedown", "label": "Slide down", "xfade": "slidedown", "group": "Slide"},
    {"id": "smoothleft", "label": "Smooth push", "xfade": "smoothleft", "group": "Slide"},
    {"id": "circleopen", "label": "Circle open", "xfade": "circleopen", "group": "Shape"},
    {"id": "circleclose", "label": "Circle close", "xfade": "circleclose", "group": "Shape"},
    {"id": "radial", "label": "Radial sweep", "xfade": "radial", "group": "Shape"},
    {"id": "zoomin", "label": "Zoom in", "xfade": "zoomin", "group": "Effect"},
    {"id": "pixelize", "label": "Pixelize", "xfade": "pixelize", "group": "Effect"},
    {"id": "hblur", "label": "Blur", "xfade": "hblur", "group": "Effect"},
    {"id": "squeezeh", "label": "Squeeze", "xfade": "squeezeh", "group": "Effect"},
]

FILTERS = [
    {"id": "none", "label": "Original", "vf": ""},
    {"id": "vivid", "label": "Vivid", "vf": "eq=saturation=1.35:contrast=1.08"},
    {"id": "sharp", "label": "Crisp (best for screen recordings)", "vf": "unsharp=5:5:1.0:5:5:0.0,eq=contrast=1.05"},
    {"id": "bright", "label": "Bright", "vf": "eq=brightness=0.06:contrast=1.05:saturation=1.05"},
    {"id": "warm", "label": "Warm", "vf": "colorbalance=rs=.08:gs=.02:bs=-.08:rm=.06:bm=-.06,eq=saturation=1.1"},
    {"id": "cool", "label": "Cool", "vf": "colorbalance=rs=-.06:bs=.10:bm=.06,eq=saturation=1.05"},
    {"id": "cinematic", "label": "Cinematic", "vf": "eq=contrast=1.12:saturation=0.9:gamma=0.95,colorbalance=rs=.05:bs=-.03:bh=.05:rh=.04,vignette=PI/5"},
    {"id": "bw", "label": "Black & white", "vf": "hue=s=0,eq=contrast=1.1"},
    {"id": "sepia", "label": "Sepia", "vf": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131"},
]

# colours are #RRGGBB. size is multiplied with min(width, height) * 0.075
CAPTION_STYLES = [
    {"id": "pop", "label": "Pop (word highlight)", "font": "Poppins", "bold": True, "upper": True, "mode": "word",
     "color": "#FFFFFF", "highlight": "#FFE14D", "outline": "#000000", "outlineWidth": 5, "box": False, "maxWords": 3},
    {"id": "karaoke", "label": "Karaoke sweep", "font": "Inter", "bold": True, "upper": False, "mode": "karaoke",
     "color": "#FFFFFF", "highlight": "#38BDF8", "outline": "#000000", "outlineWidth": 4, "box": False, "maxWords": 4},
    {"id": "classic", "label": "Classic", "font": "Inter", "bold": True, "upper": False, "mode": "none",
     "color": "#FFFFFF", "highlight": "#FFFFFF", "outline": "#000000", "outlineWidth": 4, "box": False, "maxWords": 6},
    {"id": "boxed", "label": "Boxed", "font": "Inter", "bold": True, "upper": False, "mode": "none",
     "color": "#FFFFFF", "highlight": "#FFFFFF", "outline": "#000000", "outlineWidth": 14, "box": True, "maxWords": 5},
    {"id": "neon", "label": "Neon", "font": "Poppins", "bold": True, "upper": True, "mode": "word",
     "color": "#FFFFFF", "highlight": "#7CFFEA", "outline": "#B517FF", "outlineWidth": 5, "box": False, "maxWords": 3},
    {"id": "minimal", "label": "Minimal", "font": "Inter", "bold": True, "upper": False, "mode": "none",
     "color": "#FFFFFF", "highlight": "#FFFFFF", "outline": "#000000", "outlineWidth": 2, "box": False, "maxWords": 7},
]

LOGO_POSITIONS = ["top-left", "top-right", "bottom-left", "bottom-right", "center"]
ASPECTS = {"9:16": (1080, 1920), "4:5": (1080, 1350), "1:1": (1080, 1080), "16:9": (1920, 1080)}
FRAMINGS = [
    {"id": "blur", "label": "Fit + blurred background", "hint": "Whole screen visible - safest for screen recordings"},
    {"id": "crop", "label": "Fill frame (crop)", "hint": "Zooms into a region; use focus/zoom to pick it"},
    {"id": "fit", "label": "Fit with black bars", "hint": "Original framing"},
]
MOTIONS = [{"id": "none", "label": "None"}, {"id": "zoom_in", "label": "Slow zoom in"}, {"id": "zoom_out", "label": "Slow zoom out"}]
QUALITIES = [
    {"id": "draft", "label": "Draft (fast preview)", "scale": 0.5, "preset": "ultrafast", "crf": 28},
    {"id": "720p", "label": "HD 720p", "scale": 2 / 3, "preset": "veryfast", "crf": 22},
    {"id": "1080p", "label": "Full HD 1080p", "scale": 1.0, "preset": "medium", "crf": 20},
]
VOICE_MODES = [
    {"id": "ai", "label": "AI voice-over", "hint": "Narrates each point; original audio is lowered"},
    {"id": "original", "label": "Original speaker", "hint": "Keeps the real audio of each moment"},
    {"id": "none", "label": "No voice", "hint": "Silent (captions only)"},
]

DEFAULT_SETTINGS: Dict[str, Any] = {
    "targetSeconds": 60,
    "voice": "ai",
    "ttsVoice": "auto",
    "ttsRate": 0,
    "originalVolume": 0.1,
    "aspect": "9:16",
    "quality": "720p",
    "framing": "blur",
    "zoom": 1.0,
    "focusX": 0.5,
    "focusY": 0.5,
    "motion": "none",
    "filter": "none",
    "speed": 1.0,
    "transition": "fade",
    "transitionDuration": 0.5,
    "captions": {"enabled": True, "style": "pop", "position": "bottom", "size": 1.0, "color": None, "highlightColor": None,
                 "font": None, "outlineColor": None, "uppercase": None, "box": None},
    "logo": {"id": None, "position": "top-right", "size": 0.18, "opacity": 1.0},
    "showTitles": True,
    "progressBar": True,
    "fitToTarget": True,
}


def catalog() -> Dict[str, Any]:
    return {
        "transitions": [{k: v for k, v in t.items() if k != "xfade"} for t in TRANSITIONS],
        "filters": [{"id": f["id"], "label": f["label"]} for f in FILTERS],
        "captionStyles": CAPTION_STYLES,
        "logoPositions": LOGO_POSITIONS,
        "captionPositions": ["top", "middle", "bottom"],
        "fonts": assets.list_fonts(),
        "logos": assets.list_logos(),
        "aspects": list(ASPECTS),
        "framings": FRAMINGS,
        "motions": MOTIONS,
        "qualities": [{"id": q["id"], "label": q["label"]} for q in QUALITIES],
        "voiceModes": VOICE_MODES,
        "voices": tts.VOICES,
        "defaults": DEFAULT_SETTINGS,
    }


def _num(v, lo, hi, default):
    try:
        return min(hi, max(lo, float(v)))
    except (TypeError, ValueError):
        return default


def _enum(v, allowed, default):
    return v if v in allowed else default


def normalize_settings(user: Dict[str, Any] | None, base: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Merge user settings over base/defaults and clamp every value to a safe range."""
    s = copy.deepcopy(base or DEFAULT_SETTINGS)
    u = user or {}
    for k, v in u.items():
        if k in ("captions", "logo") and isinstance(v, dict):
            s[k].update(v)
        elif k in DEFAULT_SETTINGS:
            s[k] = v
    d = DEFAULT_SETTINGS
    s["targetSeconds"] = _num(s["targetSeconds"], 10, 180, d["targetSeconds"])
    s["voice"] = _enum(s["voice"], [m["id"] for m in VOICE_MODES], d["voice"])
    s["ttsVoice"] = _enum(s["ttsVoice"], [v["id"] for v in tts.VOICES], d["ttsVoice"])
    s["ttsRate"] = int(_num(s["ttsRate"], -40, 60, 0))
    s["originalVolume"] = _num(s["originalVolume"], 0, 1, d["originalVolume"])
    s["aspect"] = _enum(s["aspect"], list(ASPECTS), d["aspect"])
    s["quality"] = _enum(s["quality"], [q["id"] for q in QUALITIES], d["quality"])
    s["framing"] = _enum(s["framing"], [f["id"] for f in FRAMINGS], d["framing"])
    s["zoom"] = _num(s["zoom"], 1, 3, 1)
    s["focusX"] = _num(s["focusX"], 0, 1, 0.5)
    s["focusY"] = _num(s["focusY"], 0, 1, 0.5)
    s["motion"] = _enum(s["motion"], [m["id"] for m in MOTIONS], "none")
    s["filter"] = _enum(s["filter"], [f["id"] for f in FILTERS], "none")
    s["speed"] = _num(s["speed"], 0.5, 2.0, 1.0)
    s["transition"] = _enum(s["transition"], [t["id"] for t in TRANSITIONS], d["transition"])
    s["transitionDuration"] = _num(s["transitionDuration"], 0.2, 1.5, 0.5)
    c = s["captions"]
    c["enabled"] = bool(c.get("enabled", True))
    c["style"] = _enum(c.get("style"), [x["id"] for x in CAPTION_STYLES], "pop")
    c["position"] = _enum(c.get("position"), ["top", "middle", "bottom"], "bottom")
    c["size"] = _num(c.get("size"), 0.6, 1.6, 1.0)
    c["font"] = c.get("font") if c.get("font") in assets.font_families() else None
    for key in ("uppercase", "box"):
        c[key] = None if c.get(key) is None else bool(c[key])
    for key in ("color", "highlightColor", "outlineColor"):
        val = c.get(key)
        c[key] = val if isinstance(val, str) and len(val) == 7 and val.startswith("#") else None
    lg = s["logo"]
    lg["id"] = lg.get("id") if assets.logo_path(lg.get("id")) else None
    lg["position"] = _enum(lg.get("position"), LOGO_POSITIONS, "top-right")
    lg["size"] = _num(lg.get("size"), 0.05, 0.6, 0.18)
    lg["opacity"] = _num(lg.get("opacity"), 0.1, 1.0, 1.0)
    for key in ("showTitles", "progressBar", "fitToTarget"):
        s[key] = bool(s[key])
    return s


def transition_xfade(tid: str) -> str:
    return next((t["xfade"] for t in TRANSITIONS if t["id"] == tid), "fade")
