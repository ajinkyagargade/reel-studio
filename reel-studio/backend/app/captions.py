"""Build an ASS subtitle file: animated word-by-word captions, point titles and a progress bar."""
from typing import Any, Dict, List

from . import assets, options

ALIGN = {"bottom": 2, "middle": 5, "top": 8}


def _ass_color(hex_color: str, alpha: int = 0) -> str:
    h = hex_color.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def _t(sec: float) -> str:
    sec = max(0.0, sec)
    cs = int(round(sec * 100))
    return f"{cs // 360000}:{(cs // 6000) % 60:02d}:{(cs // 100) % 60:02d}.{cs % 100:02d}"


def _esc(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def spread_words(text: str, start: float, end: float) -> List[Dict[str, Any]]:
    """Give every word of `text` a timing inside [start, end], proportional to its length."""
    words = text.split()
    if not words or end <= start:
        return []
    weights = [len(w) + 2 for w in words]
    total = float(sum(weights))
    out, t = [], start
    for w, wt in zip(words, weights):
        dur = (end - start) * wt / total
        out.append({"w": w, "s": t, "e": t + dur})
        t += dur
    return out


def _group(words: List[Dict], max_words: int, max_chars: int, max_gap: float = 0.7) -> List[List[Dict]]:
    groups: List[List[Dict]] = []
    cur: List[Dict] = []
    for w in words:
        chars = sum(len(x["w"]) + 1 for x in cur) + len(w["w"])
        gap = w["s"] - cur[-1]["e"] if cur else 0
        if cur and (len(cur) >= max_words or chars > max_chars or gap > max_gap):
            groups.append(cur)
            cur = []
        cur.append(w)
        if w["w"].rstrip()[-1:] in ".?!" and len(cur) >= 2:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def build_ass(width: int, height: int, caption_words: List[Dict], titles: List[Dict],
              total: float, cfg: Dict[str, Any], progress_bar: bool) -> str:
    """caption_words: [{w,s,e}] in absolute timeline seconds. titles: [{text,start,end}]."""
    preset = next(s for s in options.CAPTION_STYLES if s["id"] == cfg["style"])
    font = cfg.get("font") or preset["font"]
    color = cfg.get("color") or preset["color"]
    hl = cfg.get("highlightColor") or preset["highlight"]
    upper = preset["upper"] if cfg.get("uppercase") is None else cfg["uppercase"]
    box = preset["box"] if cfg.get("box") is None else cfg["box"]
    outline_hex = cfg.get("outlineColor") or preset["outline"]
    base = min(width, height)
    fs = int(base * 0.075 * cfg.get("size", 1.0))
    portrait = height > width
    margin_v = int(height * (0.20 if portrait else 0.08)) if cfg["position"] == "bottom" else int(height * 0.12 if cfg["position"] == "top" else 0)
    margin_lr = int(width * 0.07)
    outline = max(1, round((14 if box else min(preset["outlineWidth"], 6)) * base / 1080))
    border_style = 3 if box else 1
    back = _ass_color(outline_hex if cfg.get("outlineColor") else "#000000", 0x70) if box else _ass_color("#000000", 0x80)
    out_col = back if box else _ass_color(outline_hex)
    bold = -1 if (preset["bold"] and assets.is_builtin(font)) else 0
    # karaoke: Primary = already-sung colour, Secondary = not-yet-sung
    prim, sec = (_ass_color(hl), _ass_color(color)) if preset["mode"] == "karaoke" else (_ass_color(color), _ass_color(color))

    title_fs = int(base * 0.042)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}", "WrapStyle: 0",
        "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Cap,{font},{fs},{prim},{sec},{out_col},{back},{bold},0,0,0,100,100,0,0,{border_style},{outline},1,{ALIGN[cfg['position']]},{margin_lr},{margin_lr},{margin_v},1",
        f"Style: Title,Poppins,{title_fs},{_ass_color('#FFFFFF')},{_ass_color('#FFFFFF')},{_ass_color('#000000')},{_ass_color('#4F46E5', 0x10)},-1,0,0,0,100,100,1,0,3,{int(title_fs * 0.45)},0,8,{margin_lr},{margin_lr},{int(height * 0.075)},1",
        f"Style: Bar,Poppins,20,{_ass_color('#818CF8')},{_ass_color('#818CF8')},{_ass_color('#818CF8')},{_ass_color('#818CF8')},0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    if cfg.get("enabled", True) and caption_words:
        max_chars = max(12, int(2 * (width - 2 * margin_lr) / (fs * 0.62)))
        words = sorted(caption_words, key=lambda x: x["s"])
        groups = _group(words, preset["maxWords"], max_chars)
        for gi, g in enumerate(groups):
            disp = [(_esc(w["w"]).upper() if upper else _esc(w["w"])) for w in g]
            g_start, g_end = g[0]["s"], min(g[-1]["e"] + 0.25, total)
            if gi + 1 < len(groups):  # never overlap the next caption
                g_end = min(g_end, groups[gi + 1][0]["s"])
            if preset["mode"] == "word":
                for i, w in enumerate(g):
                    s = w["s"] if i else g_start
                    e = g[i + 1]["s"] if i + 1 < len(g) else g_end
                    if e <= s:
                        continue
                    text = " ".join(
                        (f"{{\\c{_ass_color(hl)}\\fscx115\\fscy115}}{d}{{\\c{_ass_color(color)}\\fscx100\\fscy100}}" if j == i else d)
                        for j, d in enumerate(disp))
                    lines.append(f"Dialogue: 1,{_t(s)},{_t(e)},Cap,,0,0,0,,{text}")
            elif preset["mode"] == "karaoke":
                parts = []
                for i, (w, d) in enumerate(zip(g, disp)):
                    end_i = g[i + 1]["s"] if i + 1 < len(g) else max(w["e"], w["s"] + 0.1)
                    parts.append(f"{{\\kf{max(1, int((end_i - w['s']) * 100))}}}{d}")
                lines.append(f"Dialogue: 1,{_t(g_start)},{_t(g_end)},Cap,,0,0,0,,{' '.join(parts)}")
            else:
                lines.append(f"Dialogue: 1,{_t(g_start)},{_t(g_end)},Cap,,0,0,0,,{' '.join(disp)}")

    for t in titles:
        lines.append(f"Dialogue: 2,{_t(t['start'])},{_t(t['end'])},Title,,0,0,0,,{{\\fad(250,250)}}{_esc(t['text'])}")

    if progress_bar and total > 0:
        bar_h = max(6, int(height * 0.006))
        lines.append(
            f"Dialogue: 3,{_t(0)},{_t(total)},Bar,,0,0,0,,{{\\an7\\pos(0,{height - bar_h})\\p1\\fscx1\\fscy{bar_h * 100}"
            f"\\t(0,{int(total * 1000)},\\fscx{width * 100})}}m 0 0 l 1 0 1 1 0 1{{\\p0}}")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ plain subtitle files
def _stamp(sec: float, comma: bool) -> str:
    ms = int(round(max(0.0, sec) * 1000))
    return f"{ms // 3600000:02d}:{(ms // 60000) % 60:02d}:{(ms // 1000) % 60:02d}{',' if comma else '.'}{ms % 1000:03d}"


def subtitle_file(words: List[Dict[str, Any]], fmt: str, max_words: int = 7, max_chars: int = 42) -> str:
    """words: [{word,start,end}] from the transcript -> SRT or WebVTT text."""
    ws = [{"w": w["word"], "s": w["start"], "e": w["end"]} for w in words]
    groups = _group(ws, max_words, max_chars, max_gap=1.0)
    out = ["WEBVTT", ""] if fmt == "vtt" else []
    for i, g in enumerate(groups, 1):
        end = g[-1]["e"]
        if i < len(groups):
            end = min(end + 0.3, groups[i][0]["s"])
        if fmt == "srt":
            out.append(str(i))
        out.append(f"{_stamp(g[0]['s'], fmt == 'srt')} --> {_stamp(end, fmt == 'srt')}")
        out.append(" ".join(w["w"] for w in g))
        out.append("")
    return "\n".join(out)
