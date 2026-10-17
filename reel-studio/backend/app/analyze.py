"""Video understanding: summary, chapters, key points, glossary, FAQ ...

Uses Claude when ANTHROPIC_API_KEY is set. Otherwise falls back to a local extractive
analyzer (TF-IDF) so the app still works with no paid API.
"""
import math
import re
from collections import Counter
from typing import Any, Dict, List

from . import llm

STOP = set("""a an the and or but if then so of to in on at for with from by as is are was were be been being am do does did
have has had having i you he she it we they me him her us them my your his its our their this that these those there here
what which who whom whose when where why how not no yes can could should would will shall may might must just very really
also too than about into over under again more most some any each other such only own same up down out off all both few
okay ok like right now let lets going gonna want see look know get got one two thing things way well actually basically
yeh ye hai hain ka ki ke ko se me mein pe par aur ya toh to bhi nahi nahin kya kyun kyu kaise kuch ye woh wo hum tum aap
mera meri tera teri uska uski iska iski hota hoti hote hua hui hue kar karna karte karo kiya raha rahi rahe tha thi the
chalo achha accha matlab jaise isliye lekin agar jab tab abhi phir yahan wahan bas sirf""".split())

TOKEN_RE = re.compile(r"[A-Za-zऀ-ॿ][A-Za-zऀ-ॿ0-9_']*")


def fmt_time(t: float) -> str:
    t = int(max(0, t))
    h, m, s = t // 3600, (t % 3600) // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _tokens(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOP and len(t) > 2]


def _clip_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    clipped = " ".join(words[:max_words])
    # prefer ending at a sentence boundary inside the clip
    m = list(re.finditer(r"[.!?]", clipped))
    if m and m[-1].end() > len(clipped) * 0.5:
        return clipped[: m[-1].end()]
    return clipped.rstrip(",;:") + "…"


# ---------------------------------------------------------------- stats
def compute_stats(transcript: Dict, duration: float) -> Dict[str, Any]:
    words = transcript.get("words", [])
    speaking = sum(max(0.0, w["end"] - w["start"]) for w in words)
    wc = len(words)
    return {
        "wordCount": wc,
        "sentenceCount": len(transcript.get("segments", [])),
        "wordsPerMinute": round(wc / (duration / 60), 1) if duration else 0,
        "speakingTimeSeconds": round(speaking, 1),
        "speakingPercent": round(100 * speaking / duration, 1) if duration else 0,
        "estimatedReadMinutes": round(wc / 220, 1),
    }


# ---------------------------------------------------------------- local analyzer
def _units(transcript: Dict) -> List[Dict]:
    """Merge very short segments so every unit is a meaningful sentence-ish chunk."""
    units: List[Dict] = []
    for s in transcript.get("segments", []):
        if units and len(units[-1]["text"].split()) < 6 and s["start"] - units[-1]["end"] < 1.5:
            units[-1]["text"] += " " + s["text"]
            units[-1]["end"] = s["end"]
        else:
            units.append(dict(s))
    return units


def _score_units(units: List[Dict]):
    n = len(units)
    toks = [_tokens(u["text"]) for u in units]
    df = Counter(t for tk in toks for t in set(tk))
    total = Counter(t for tk in toks for t in tk)
    idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
    scores = []
    for tk in toks:
        if len(tk) < 4:
            scores.append(0.0)
            continue
        s = sum(idf[t] * (1 + math.log(total[t])) for t in tk) / (len(tk) ** 0.7)
        scores.append(s)
    return toks, scores, idf, total


def _surface_forms(units: List[Dict]) -> Dict[str, str]:
    """lowercase token -> its most common original spelling (keeps useState, API, JSON...)."""
    forms: Dict[str, Counter] = {}
    for u in units:
        for t in TOKEN_RE.findall(u["text"]):
            forms.setdefault(t.lower(), Counter())[t] += 1
    return {k: c.most_common(1)[0][0] for k, c in forms.items()}


def _nice(word: str, surface: Dict[str, str]) -> str:
    w = surface.get(word, word)
    return w if (any(c.isupper() for c in w) or not w.isascii()) else w.capitalize()


def _keywords(tokens_list: List[List[str]], idf: Dict[str, float], k: int) -> List[str]:
    c = Counter(t for tk in tokens_list for t in tk)
    ranked = sorted(c, key=lambda t: c[t] * idf.get(t, 1), reverse=True)
    return ranked[:k]


def analyze_local(transcript: Dict, duration: float, fallback_title: str) -> Dict[str, Any]:
    units = _units(transcript)
    if not units:
        raise RuntimeError("Transcript is empty - no speech detected in this video.")
    toks, scores, idf, total = _score_units(units)
    n = len(units)
    top_scores = sorted(scores, reverse=True)
    hi = top_scores[0] or 1.0
    keywords = _keywords(toks, idf, 14)
    surface = _surface_forms(units)

    # key points: best unit in each time window (so they cover the whole video)
    k = max(6, min(14, int(duration // 120)))
    win = duration / k
    key_points = []
    for i in range(k):
        lo, up = i * win, (i + 1) * win
        idxs = [j for j, u in enumerate(units) if lo <= u["start"] < up]
        if not idxs:
            continue
        j = max(idxs, key=lambda x: scores[x])
        if scores[j] <= 0:
            continue
        start, end, text = units[j]["start"], units[j]["end"], units[j]["text"]
        nxt = j + 1
        while end - start < 8 and nxt < n:  # extend to >= 8s so the clip is watchable
            end = units[nxt]["end"]
            nxt += 1
        # topical title: words of this sentence that recur across the whole video
        topical = sorted({t for t in toks[j] if total[t] >= 2}, key=lambda t: total[t] * idf[t], reverse=True)
        kw = topical[:2] or sorted(set(toks[j]), key=len, reverse=True)[:1]
        title = " & ".join(_nice(w, surface) for w in kw) or "Key moment"
        key_points.append({
            "title": title, "summary": _clip_words(text, 40), "narration": _clip_words(text, 26),
            "start": round(start, 2), "end": round(min(end, duration), 2),
            "importance": round(1 + 9 * scores[j] / hi, 1),
        })

    # chapters: equal windows snapped to the longest pause nearby
    n_ch = max(3, min(12, round(duration / 240)))
    chapters = []
    bounds = [0.0]
    for i in range(1, n_ch):
        target = duration * i / n_ch
        near = [j for j in range(1, n) if abs(units[j]["start"] - target) < duration / (n_ch * 3)]
        if near:
            j = max(near, key=lambda x: units[x]["start"] - units[x - 1]["end"])
            bounds.append(units[j]["start"])
        else:
            bounds.append(target)
    bounds.append(duration)
    for a, b in zip(bounds, bounds[1:]):
        idxs = [j for j, u in enumerate(units) if a <= u["start"] < b]
        if not idxs:
            continue
        best = max(idxs, key=lambda x: scores[x])
        kw = _keywords([toks[j] for j in idxs], idf, 3)
        chapters.append({
            "title": " · ".join(_nice(w, surface) for w in kw) or "Chapter",
            "start": round(a, 2), "end": round(b, 2), "summary": _clip_words(units[best]["text"], 35),
        })

    order = sorted(range(n), key=lambda x: scores[x], reverse=True)
    summary_idx = sorted(order[: min(7, n)])
    summary = " ".join(units[j]["text"] for j in summary_idx)
    quotes = [{"text": units[j]["text"], "time": round(units[j]["start"], 1)}
              for j in order if 8 <= len(units[j]["text"].split()) <= 28][:3]

    return {
        "source": "local",
        "title": fallback_title,
        "language": transcript.get("language", "en"),
        "contentType": "video",
        "audience": "",
        "difficulty": "",
        "tldr": _clip_words(" ".join(units[j]["text"] for j in summary_idx[:2]), 45),
        "summary": summary,
        "keyTakeaways": [kp["summary"] for kp in key_points[:6]],
        "chapters": chapters,
        "keyPoints": key_points,
        "topics": [_nice(w, surface) for w in keywords[:6]],
        "keywords": [surface.get(w, w) for w in keywords],
        "glossary": [],
        "quotes": quotes,
        "actionItems": [],
        "faq": [],
    }


# ---------------------------------------------------------------- Claude analyzer
SYSTEM = """You are an expert video analyst and short-form video editor.
You receive a timestamped transcript ([m:ss] text) of a video, which may be a class recording,
tutorial, lecture or talk. It may mix English and Hindi (Hinglish). Respond with ONE JSON object only.

Write all text fields in the same language/script as the speaker (Hinglish stays Hinglish in Latin script).
Timestamps must be numbers of seconds taken from the transcript. Never invent facts that are not in the transcript.

JSON schema:
{
 "title": "short descriptive title",
 "language": "en|hi|hinglish|...",
 "contentType": "lecture|tutorial|talk|meeting|interview|other",
 "audience": "who this is for",
 "difficulty": "beginner|intermediate|advanced",
 "tldr": "1-2 sentence gist",
 "summary": "brief explanation of the whole video, 120-220 words, clear paragraphs separated by \\n\\n",
 "keyTakeaways": ["5-8 short takeaways"],
 "chapters": [{"title":"", "start":0, "end":0, "summary":"1-2 sentences"}],
 "keyPoints": [ 8-12 reel-worthy moments, each:
   {"title":"3-6 words", "summary":"1-2 sentences", "narration":"spoken line for a voiceover, 18-26 words, punchy, standalone, no timestamps, no 'in this video'",
    "start":0, "end":0, "importance":1-10} ],
 "topics": ["main topics"],
 "keywords": ["important terms"],
 "glossary": [{"term":"","definition":""}],
 "quotes": [{"text":"memorable line, verbatim","time":0}],
 "actionItems": ["things the viewer should do/practice"],
 "faq": [{"q":"","a":""}]
}
Rules for keyPoints: each is a single self-contained idea; start/end bound the exact moment it is explained (6-20 seconds);
cover the video from start to finish; no overlaps; importance 10 = must be in a 60-second reel.
chapters must cover the whole video in order. Empty lists are fine if nothing applies."""

MAX_CHARS = 250_000


def _lines(transcript: Dict) -> List[str]:
    return [f"[{fmt_time(s['start'])}] {s['text']}" for s in transcript.get("segments", [])]


def _windows(lines: List[str]) -> List[List[str]]:
    out, cur, size = [], [], 0
    for ln in lines:
        if size + len(ln) > MAX_CHARS and cur:
            out.append(cur)
            cur, size = [], 0
        cur.append(ln)
        size += len(ln) + 1
    if cur:
        out.append(cur)
    return out


def _normalize(data: Dict, duration: float, transcript: Dict, fallback_title: str) -> Dict[str, Any]:
    def num(v, default=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def clamp_span(item):
        s = min(max(num(item.get("start")), 0), duration)
        e = min(max(num(item.get("end"), s + 10), s + 1), duration)
        return round(s, 2), round(e, 2)

    kps = []
    for kp in data.get("keyPoints", []) or []:
        s, e = clamp_span(kp)
        if e - s < 4:
            e = min(duration, s + 8)
        if e <= s:
            continue
        text = str(kp.get("narration") or kp.get("summary") or "").strip()
        kps.append({
            "title": str(kp.get("title") or "Key point")[:80], "summary": str(kp.get("summary") or text),
            "narration": text, "start": s, "end": round(e, 2),
            "importance": min(10.0, max(1.0, num(kp.get("importance"), 5))),
        })
    kps.sort(key=lambda x: x["start"])
    chapters = []
    for ch in data.get("chapters", []) or []:
        s, e = clamp_span(ch)
        chapters.append({"title": str(ch.get("title") or "Chapter"), "start": s, "end": e, "summary": str(ch.get("summary") or "")})
    chapters.sort(key=lambda x: x["start"])

    def strs(key, limit=20):
        return [str(x) for x in (data.get(key) or []) if x][:limit]

    return {
        "source": "claude",
        "title": str(data.get("title") or fallback_title),
        "language": str(data.get("language") or transcript.get("language", "en")),
        "contentType": str(data.get("contentType") or "video"),
        "audience": str(data.get("audience") or ""),
        "difficulty": str(data.get("difficulty") or ""),
        "tldr": str(data.get("tldr") or ""),
        "summary": str(data.get("summary") or ""),
        "keyTakeaways": strs("keyTakeaways"),
        "chapters": chapters,
        "keyPoints": kps,
        "topics": strs("topics"),
        "keywords": strs("keywords"),
        "glossary": [{"term": str(g.get("term", "")), "definition": str(g.get("definition", ""))}
                     for g in (data.get("glossary") or []) if isinstance(g, dict) and g.get("term")][:20],
        "quotes": [{"text": str(q.get("text", "")), "time": round(num(q.get("time")), 1)}
                   for q in (data.get("quotes") or []) if isinstance(q, dict) and q.get("text")][:6],
        "actionItems": strs("actionItems"),
        "faq": [{"q": str(f.get("q", "")), "a": str(f.get("a", ""))}
                for f in (data.get("faq") or []) if isinstance(f, dict) and f.get("q")][:8],
    }


def analyze_claude(transcript: Dict, duration: float, fallback_title: str) -> Dict[str, Any]:
    wins = _windows(_lines(transcript))
    header = f"Video duration: {fmt_time(duration)} ({duration:.0f} seconds).\n\nTranscript:\n"
    if len(wins) == 1:
        data = llm.complete_json(SYSTEM, header + "\n".join(wins[0]), max_tokens=8000)
        return _normalize(data, duration, transcript, fallback_title)

    # very long video: analyse each window, then merge and write one overall summary
    parts = [llm.complete_json(SYSTEM, header + f"(Part {i + 1} of {len(wins)})\n" + "\n".join(w), 8000)
             for i, w in enumerate(wins)]
    merged: Dict[str, Any] = {"chapters": [], "keyPoints": [], "topics": [], "keywords": [], "glossary": [],
                              "quotes": [], "actionItems": [], "faq": [], "keyTakeaways": []}
    for p in parts:
        for key in merged:
            merged[key].extend(p.get(key) or [])
    overview = llm.complete_json(
        SYSTEM, "Below are summaries of consecutive parts of one long video. Produce the JSON with only these fields filled: "
        "title, language, contentType, audience, difficulty, tldr, summary, keyTakeaways (leave other lists empty).\n\n"
        + "\n\n".join(f"Part {i + 1}: {p.get('tldr', '')} {p.get('summary', '')}" for i, p in enumerate(parts)), 3000)
    merged.update({k: overview.get(k, "") for k in ("title", "language", "contentType", "audience", "difficulty", "tldr", "summary")})
    merged["keyTakeaways"] = overview.get("keyTakeaways") or merged["keyTakeaways"]
    return _normalize(merged, duration, transcript, fallback_title)


# ---------------------------------------------------------------- entry point
def analyze(transcript: Dict, duration: float, fallback_title: str) -> Dict[str, Any]:
    result, note = None, ""
    if llm.available():
        try:
            result = analyze_claude(transcript, duration, fallback_title)
        except Exception as e:  # network / quota / bad JSON -> degrade gracefully
            note = f"Claude analysis failed ({str(e)[:120]}); used local analysis instead."
    if result is None or not result["keyPoints"]:
        local = analyze_local(transcript, duration, fallback_title)
        if result:  # keep Claude's summary but borrow local key points
            result["keyPoints"] = local["keyPoints"]
        else:
            result = local
    if note:
        result["note"] = note
    result["stats"] = compute_stats(transcript, duration)
    return result
