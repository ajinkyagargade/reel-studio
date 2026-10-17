"""Generic scene renderer: scenes -> framed/graded clips -> transitions -> captions -> final mp4.

A scene is a dict:
  kind: "video" | "image"
  src: path to source file             start: seek position in source (video only)
  duration: output duration in seconds (already includes speed changes and lead/tail padding)
  speed: playback speed of the video (1.0)
  original_volume: 0..1 volume of the source audio (0 = mute)
  narration: optional audio path       narration_tempo: speed-up factor for narration (>=1)
  lead: seconds of silence before narration starts
  words: [{w,s,e}] caption words relative to the scene start (output time)
  title: optional text shown at the beginning
  framing/zoom/focusX/focusY: optional per-scene overrides
  transition: transition id used when going INTO the next scene (None = global default)
"""
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import assets, captions, media, options

FPS = 30


def target_size(aspect: str, quality: str):
    w, h = options.ASPECTS[aspect]
    q = next(x for x in options.QUALITIES if x["id"] == quality)
    sw, sh = int(w * q["scale"]) // 2 * 2, int(h * q["scale"]) // 2 * 2
    return sw, sh, q


def _logo_graph(logo: Dict, input_idx: int, W: int, H: int, src: str, dst: str) -> str:
    """Overlay the logo image (input `input_idx`) onto label `src`, output label `dst`."""
    lw = max(16, int(W * logo["size"]) // 2 * 2)
    m = int(min(W, H) * 0.04)
    bottom_pad = int(H * 0.06) if H > W else m
    pos = {
        "top-left": (f"{m}", f"{m}"),
        "top-right": (f"main_w-overlay_w-{m}", f"{m}"),
        "bottom-left": (f"{m}", f"main_h-overlay_h-{bottom_pad}"),
        "bottom-right": (f"main_w-overlay_w-{m}", f"main_h-overlay_h-{bottom_pad}"),
        "center": ("(main_w-overlay_w)/2", "(main_h-overlay_h)/2"),
    }[logo["position"]]
    return (f"[{input_idx}:v]scale={lw}:-2,format=rgba,colorchannelmixer=aa={logo['opacity']:.2f}[lg];"
            f"[{src}][lg]overlay=x={pos[0]}:y={pos[1]}[{dst}]")


def burn_captions(src: Path, words: List[Dict], settings: Dict, out_path: Path, work: Path, meta: Dict,
                  on_progress: Optional[Callable[[float, str], None]] = None) -> None:
    """Burn live-style captions (+ optional logo) into the WHOLE source video, keeping its aspect ratio."""
    work.mkdir(parents=True, exist_ok=True)
    q = next(x for x in options.QUALITIES if x["id"] == settings["quality"])
    target_h = {"draft": 480, "720p": 720, "1080p": 1080}[q["id"]]
    H = min(meta["height"], target_h) // 2 * 2
    W = int(meta["width"] * H / meta["height"]) // 2 * 2
    cap_words = [{"w": w["word"], "s": w["start"], "e": w["end"]} for w in words]
    (work / "captions.ass").write_text(
        captions.build_ass(W, H, cap_words, [], meta["duration"], settings["captions"], False), encoding="utf-8")
    assets.font_dir_for_render(work)
    logo_file = assets.logo_path(settings["logo"]["id"])
    graph = f"[0:v]scale={W}:{H},setsar=1,ass=captions.ass:fontsdir=fonts[vsub]"
    graph += ";" + (_logo_graph(settings["logo"], 1, W, H, "vsub", "vout") if logo_file else "[vsub]null[vout]")
    args = ["-i", str(src)] + (["-i", str(logo_file)] if logo_file else [])
    tmp = out_path.with_suffix(".part.mp4")
    media.run_ffmpeg(
        [*args, "-filter_complex", graph, "-map", "[vout]", "-map", "0:a?", "-c:v", "libx264", "-preset", q["preset"],
         "-crf", str(q["crf"]), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(tmp)],
        total_duration=meta["duration"], on_progress=lambda f: on_progress and on_progress(f, "Burning captions into the video"),
        cwd=work)
    tmp.replace(out_path)


def _video_graph(scene: Dict, W: int, H: int, settings: Dict, D: float) -> str:
    framing = scene.get("framing") or settings["framing"]
    zoom = float(scene.get("zoom") or settings["zoom"])
    fx = scene.get("focusX", settings["focusX"])
    fy = scene.get("focusY", settings["focusY"])
    speed = scene.get("speed", 1.0)
    pre = f"setpts=PTS/{speed:.4f},tpad=stop_mode=clone:stop_duration={D:.2f},"
    if scene["kind"] == "image" or framing == "crop":
        zw, zh = int(W * zoom) // 2 * 2, int(H * zoom) // 2 * 2
        frame = (f"[0:v]{pre}scale={zw}:{zh}:force_original_aspect_ratio=increase,"
                 f"crop={W}:{H}:x='(iw-{W})*{fx:.3f}':y='(ih-{H})*{fy:.3f}'[v0]")
    elif framing == "fit":
        frame = f"[0:v]{pre}scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black[v0]"
    else:  # blur background
        frame = (f"[0:v]{pre}split=2[a][b];"
                 f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20:2,eq=brightness=-0.12[bg];"
                 f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v0]")
    chain, last = [frame], "v0"
    motion = scene.get("motion") or settings["motion"]
    if motion in ("zoom_in", "zoom_out"):
        m = 0.10
        expr = f"(1+{m}*t/{D:.2f})" if motion == "zoom_in" else f"(1+{m}*(1-t/{D:.2f}))"
        chain.append(f"[{last}]scale=w='trunc({W}*{expr}/2)*2':h='trunc({H}*{expr}/2)*2':eval=frame,crop={W}:{H}[v1]")
        last = "v1"
    vf = next(f["vf"] for f in options.FILTERS if f["id"] == settings["filter"])
    tail = f"fps={FPS},format=yuv420p,setsar=1"
    chain.append(f"[{last}]{vf + ',' if vf else ''}{tail}[vout]")
    return ";".join(chain)


def _render_scene(scene: Dict, idx: int, W: int, H: int, settings: Dict, q: Dict, work: Path,
                  fade_in: float, fade_out: float, has_audio: bool) -> Path:
    D = scene["duration"]
    out = work / f"scene_{idx:02d}.mp4"
    args: List[str] = []
    speed = scene.get("speed", 1.0)
    window = D * speed
    if scene["kind"] == "video":
        start = scene.get("start", 0.0)
        args += ["-ss", f"{start:.3f}", "-t", f"{window:.3f}", "-i", str(scene["src"])]
    else:
        args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{D:.3f}", "-i", str(scene["src"])]
    n_idx = None
    if scene.get("narration"):
        args += ["-i", str(scene["narration"])]
        n_idx = 1
    video = _video_graph(scene, W, H, settings, D)

    parts, labels = [], []
    ov = scene.get("original_volume", 0.0)
    if scene["kind"] == "video" and has_audio and ov > 0:
        atempo = f"atempo={speed:.4f}," if abs(speed - 1) > 1e-3 else ""
        fi, fo = max(0.03, fade_in), max(0.03, fade_out)
        parts.append(f"[0:a]{atempo}volume={ov:.3f},afade=t=in:d={fi:.2f},afade=t=out:st={max(0, D - fo):.2f}:d={fo:.2f}[oa]")
        labels.append("oa")
    if n_idx is not None:
        nt = scene.get("narration_tempo", 1.0)
        lead_ms = int(scene.get("lead", 0.2) * 1000)
        t = f"atempo={nt:.4f}," if abs(nt - 1) > 1e-3 else ""
        parts.append(f"[{n_idx}:a]{t}adelay={lead_ms}|{lead_ms}[na]")
        labels.append("na")
    if not labels:
        args += ["-f", "lavfi", "-t", f"{D:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        silent_idx = 1 if n_idx is None else 2
        parts.append(f"[{silent_idx}:a]anull[sa]")
        labels.append("sa")
    mix = f"[{labels[0]}]" if len(labels) == 1 else "".join(f"[{l}]" for l in labels) + f"amix=inputs={len(labels)}:duration=longest:normalize=0,"
    parts.append(f"{mix}aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad=whole_dur={D:.3f}[aout]")

    graph = video + ";" + ";".join(parts)
    media.run_ffmpeg(
        [*args, "-filter_complex", graph, "-map", "[vout]", "-map", "[aout]", "-t", f"{D:.3f}",
         "-c:v", "libx264", "-preset", "ultrafast" if q["id"] == "draft" else "veryfast", "-crf", str(max(18, q["crf"] - 3)),
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(out)])
    return out


def render(scenes: List[Dict], settings: Dict, out_path: Path, work: Path,
           on_progress: Optional[Callable[[float, str], None]] = None) -> Dict[str, Any]:
    if not scenes:
        raise RuntimeError("Nothing to render - the reel has no points.")
    work.mkdir(parents=True, exist_ok=True)
    W, H, q = target_size(settings["aspect"], settings["quality"])
    n = len(scenes)

    def report(frac, msg):
        if on_progress:
            on_progress(max(0.0, min(1.0, frac)), msg)

    # ---- transition plan (transition i goes from scene i to scene i+1)
    base_td = settings["transitionDuration"]
    trans: List[Dict[str, Any]] = []
    for i in range(n - 1):
        tid = scenes[i].get("transition") or settings["transition"]
        td = 0.04 if tid == "cut" else base_td
        td = min(td, 0.45 * min(scenes[i]["duration"], scenes[i + 1]["duration"]))
        trans.append({"id": tid, "x": options.transition_xfade(tid), "d": max(0.04, td)})

    # ---- 1. render each scene
    paths, real = [], []
    for i, sc in enumerate(scenes):
        report(0.62 * i / n, f"Rendering scene {i + 1}/{n}")
        fade_in = trans[i - 1]["d"] if i > 0 else 0.03
        fade_out = trans[i]["d"] if i < n - 1 else 0.03
        has_audio = bool(sc.get("has_audio", True))
        p = _render_scene(sc, i, W, H, settings, q, work, fade_in, fade_out, has_audio)
        paths.append(p)
        real.append(min(sc["duration"], media.duration_of(p)))
    report(0.62, "Joining scenes with transitions")

    # ---- 2. timeline positions
    starts = [0.0]
    for i in range(n - 1):
        starts.append(starts[i] + real[i] - trans[i]["d"])
    total = starts[-1] + real[-1]

    # ---- 3. captions / titles / progress bar (absolute timeline)
    cap_words, titles = [], []
    for i, sc in enumerate(scenes):
        off = starts[i]
        for w in sc.get("words", []):
            cap_words.append({"w": w["w"], "s": off + w["s"], "e": off + w["e"]})
        if sc.get("title") and settings["showTitles"]:
            titles.append({"text": sc["title"], "start": off + 0.15, "end": off + min(2.6, real[i] - 0.2)})
    ass_text = captions.build_ass(W, H, cap_words, titles, total, settings["captions"], settings["progressBar"])
    (work / "captions.ass").write_text(ass_text, encoding="utf-8")
    assets.font_dir_for_render(work)
    logo_file = assets.logo_path(settings["logo"]["id"])

    # ---- 4. final filter graph
    g: List[str] = []
    prev = "0:v"
    for i in range(n - 1):
        lab = f"x{i + 1}"
        g.append(f"[{prev}][{i + 1}:v]xfade=transition={trans[i]['x']}:duration={trans[i]['d']:.3f}:offset={starts[i + 1]:.3f}[{lab}]")
        prev = lab
    if logo_file:
        g.append(f"[{prev}]ass=captions.ass:fontsdir=fonts[vsub]")
        g.append(_logo_graph(settings["logo"], n, W, H, "vsub", "vout"))
    else:
        g.append(f"[{prev}]ass=captions.ass:fontsdir=fonts[vout]")
    a_labels = []
    for i in range(n):
        ms = int(starts[i] * 1000)
        g.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]" if ms else f"[{i}:a]anull[a{i}]")
        a_labels.append(f"[a{i}]")
    g.append("".join(a_labels) + (f"amix=inputs={n}:duration=longest:normalize=0," if n > 1 else "")
             + "loudnorm=I=-16:TP=-1.5:LRA=11[aout]")

    args: List[str] = []
    for p in paths:
        args += ["-i", str(p)]
    if logo_file:
        args += ["-i", str(logo_file)]
    tmp_out = out_path.with_suffix(".part.mp4")
    media.run_ffmpeg(
        [*args, "-filter_complex", ";".join(g), "-map", "[vout]", "-map", "[aout]",
         "-c:v", "libx264", "-preset", q["preset"], "-crf", str(q["crf"]), "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(tmp_out)],
        total_duration=total, on_progress=lambda f: report(0.62 + 0.38 * f, "Adding captions & mixing audio"), cwd=work)
    tmp_out.replace(out_path)
    report(1.0, "Done")
    return {"duration": round(total, 2), "width": W, "height": H, "starts": [round(s, 2) for s in starts]}
